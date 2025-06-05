"""
Loan Inquiry Agent for LendenClub
=================================

Handles questions about loan products, eligibility checks, and EMI calculations.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base import BaseAgent
from data.lending_knowledge import (
    LOAN_PRODUCTS, LENDING_FAQS, get_loan_product_info,
    calculate_emi, check_basic_eligibility, get_estimated_rate,
    search_faqs
)

logger = logging.getLogger(__name__)


# Tool Input Models
class EligibilityCheckInput(BaseModel):
    """Input for eligibility check tool"""
    loan_type: str = Field(..., description="Type of loan: personal_loan, business_loan, or education_loan")
    age: int = Field(..., ge=18, le=80, description="Age of the applicant")
    monthly_income: int = Field(..., ge=10000, description="Monthly income in INR")
    credit_score: int = Field(..., ge=300, le=900, description="Credit score")


class EMICalculationInput(BaseModel):
    """Input for EMI calculation tool"""
    loan_amount: float = Field(..., ge=10000, le=10000000, description="Loan amount in INR")
    interest_rate: float = Field(..., ge=5.0, le=35.0, description="Annual interest rate in percentage")
    tenure_months: int = Field(..., ge=6, le=360, description="Loan tenure in months")


class ProductComparisonInput(BaseModel):
    """Input for loan product comparison"""
    loan_types: List[str] = Field(..., description="List of loan types to compare")
    user_profile: Optional[Dict[str, Any]] = Field(default=None, description="User profile for personalized comparison")


class LoanInquiryAgent(BaseAgent):
    """
    AI Agent specialized in handling loan inquiries for LendenClub.
    Provides information about loan products, eligibility, rates, and calculations.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None):
        system_prompt = """You are a knowledgeable and helpful loan specialist for LendenClub, India's largest peer-to-peer lending platform. 

Your expertise includes:
- All LendenClub loan products (Personal, Business, Education loans)
- Eligibility criteria and documentation requirements
- Interest rate calculations and EMI computations
- Loan comparison and recommendations
- P2P lending concepts and benefits

Guidelines:
1. Always provide accurate, up-to-date information about LendenClub's loan products
2. Use the available tools to check eligibility, calculate EMIs, and compare products
3. Be empathetic and understanding of users' financial needs
4. Explain complex financial terms in simple language
5. Always mention that final loan approval depends on detailed verification
6. Encourage users to apply if they seem eligible
7. Be transparent about fees, charges, and terms

Available tools:
- check_loan_eligibility: Check if user is eligible for a specific loan type
- calculate_emi: Calculate EMI for given loan amount, rate, and tenure
- compare_loan_products: Compare different loan products
- search_lending_faqs: Search for answers in LendenClub's FAQ database
- get_product_details: Get detailed information about specific loan products

Remember to use tools when users ask specific questions that require calculations or eligibility checks."""

        super().__init__(
            name="Loan Inquiry Agent",
            description="Specialized agent for LendenClub loan inquiries, eligibility checks, and product information",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence
        )
    
    def _register_tools(self):
        """Register loan-specific tools with the PydanticAI agent"""
        
        @self.agent.tool
        def check_loan_eligibility(ctx, input_data: EligibilityCheckInput) -> Dict[str, Any]:
            """Check loan eligibility based on user profile"""
            try:
                result = check_basic_eligibility(
                    loan_type=input_data.loan_type,
                    age=input_data.age,
                    income=input_data.monthly_income,
                    credit_score=input_data.credit_score
                )
                
                if result["eligible"]:
                    # Add estimated interest rate
                    estimated_rate = get_estimated_rate(
                        input_data.loan_type,
                        input_data.credit_score,
                        input_data.monthly_income * 12  # Annual income
                    )
                    result["estimated_interest_rate"] = f"{estimated_rate:.2f}%"
                
                return result
            except Exception as e:
                logger.error(f"Error checking eligibility: {e}")
                return {"eligible": False, "reason": "Error processing eligibility check"}
        
        @self.agent.tool
        def calculate_emi(ctx, input_data: EMICalculationInput) -> Dict[str, Any]:
            """Calculate EMI for given loan parameters"""
            try:
                return calculate_emi(
                    principal=input_data.loan_amount,
                    rate=input_data.interest_rate,
                    tenure_months=input_data.tenure_months
                )
            except Exception as e:
                logger.error(f"Error calculating EMI: {e}")
                return {"error": "Unable to calculate EMI"}
        
        @self.agent.tool
        def compare_loan_products(ctx, input_data: ProductComparisonInput) -> Dict[str, Any]:
            """Compare different loan products"""
            try:
                comparison = {}
                for loan_type in input_data.loan_types:
                    product_info = get_loan_product_info(loan_type)
                    if product_info:
                        comparison[loan_type] = {
                            "name": product_info["name"],
                            "amount_range": f"₹{product_info['min_amount']:,} - ₹{product_info['max_amount']:,}",
                            "interest_rate": product_info["interest_rate_range"],
                            "max_tenure": f"{max(product_info['tenure_months'])} months",
                            "processing_fee": product_info["processing_fee"],
                            "key_eligibility": {
                                "min_age": product_info["eligibility"].get("min_age"),
                                "min_income": product_info["eligibility"].get("min_income"),
                                "min_credit_score": product_info["eligibility"].get("min_credit_score")
                            }
                        }
                
                return {"comparison": comparison, "products_compared": len(comparison)}
            except Exception as e:
                logger.error(f"Error comparing products: {e}")
                return {"error": "Unable to compare products"}
        
        @self.agent.tool
        def search_lending_faqs(ctx, query: str) -> List[Dict[str, str]]:
            """Search LendenClub FAQs for relevant information"""
            try:
                return search_faqs(query)
            except Exception as e:
                logger.error(f"Error searching FAQs: {e}")
                return []
        
        @self.agent.tool
        def get_product_details(ctx, loan_type: str) -> Dict[str, Any]:
            """Get detailed information about a specific loan product"""
            try:
                return get_loan_product_info(loan_type)
            except Exception as e:
                logger.error(f"Error getting product details: {e}")
                return {}
    
    def get_agent_context(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build context specific to loan inquiries"""
        context = {
            "agent_type": "loan_inquiry",
            "available_products": list(LOAN_PRODUCTS.keys()),
            "query_type": self._classify_query(query)
        }
        
        # Add user profile if available
        if user_context:
            context["user_profile"] = user_context
        
        # Add relevant product info based on query
        detected_products = self._detect_loan_products(query)
        if detected_products:
            context["relevant_products"] = {
                product: get_loan_product_info(product) 
                for product in detected_products
            }
        
        return context
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of loan inquiry"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["eligible", "eligibility", "qualify"]):
            return "eligibility_check"
        elif any(word in query_lower for word in ["emi", "monthly", "payment", "calculate"]):
            return "emi_calculation"
        elif any(word in query_lower for word in ["compare", "difference", "vs", "versus"]):
            return "product_comparison"
        elif any(word in query_lower for word in ["rate", "interest", "apr"]):
            return "interest_inquiry"
        elif any(word in query_lower for word in ["documents", "papers", "requirements"]):
            return "documentation_inquiry"
        elif any(word in query_lower for word in ["apply", "application", "process"]):
            return "application_process"
        else:
            return "general_inquiry"
    
    def _detect_loan_products(self, query: str) -> List[str]:
        """Detect which loan products are mentioned in the query"""
        query_lower = query.lower()
        detected = []
        
        product_keywords = {
            "personal_loan": ["personal", "personal loan"],
            "business_loan": ["business", "business loan", "commercial", "enterprise"],
            "education_loan": ["education", "student", "study", "education loan"]
        }
        
        for product, keywords in product_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append(product)
        
        return detected 