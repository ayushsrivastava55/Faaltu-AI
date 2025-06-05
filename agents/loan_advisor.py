"""
Loan Advisor Agent - Personalized Financial Intelligence
=======================================================

This agent provides intelligent loan recommendations based on comprehensive
financial analysis, market research, and personalized user profiling.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .base import BaseAgent
from data.lending_knowledge import calculate_emi, get_loan_product_info, LOAN_PRODUCTS

logger = logging.getLogger(__name__)


class UserFinancialProfile(BaseModel):
    """Comprehensive user financial profile for personalized recommendations"""
    monthly_income: Optional[int] = None
    age: Optional[int] = None
    employment_type: Optional[str] = None  # salaried, self_employed, business
    credit_score: Optional[int] = None
    existing_loans: List[Dict[str, Any]] = Field(default_factory=list)
    monthly_expenses: Optional[int] = None
    savings_amount: Optional[int] = None
    loan_purpose: Optional[str] = None
    preferred_tenure: Optional[int] = None
    max_emi_capacity: Optional[int] = None


class LoanRecommendation(BaseModel):
    """Structured loan recommendation with detailed analysis"""
    loan_type: str
    recommended_amount: float
    interest_rate: float
    tenure_months: int
    monthly_emi: float
    total_cost: float
    pros: List[str]
    cons: List[str]
    confidence_score: float
    personalization_factors: List[str]


class LoanAdvisorAgent(BaseAgent):
    """
    Advanced loan advisor that analyzes user profiles, performs financial modeling,
    and provides personalized loan recommendations with detailed reasoning.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are an expert loan advisor and financial analyst for LendenClub.

Your expertise includes:
- **Financial profiling** and risk assessment
- **Loan product optimization** for individual needs
- **Comparative analysis** across multiple loan options
- **Affordability modeling** and EMI planning
- **Market rate analysis** and timing recommendations
- **Credit improvement** strategies and guidance

Your analytical capabilities:
1. Build comprehensive financial profiles from user data
2. Calculate optimal loan amounts and tenures
3. Perform scenario analysis for different loan options
4. Assess affordability and debt-to-income ratios
5. Identify the best loan products for specific situations
6. Provide strategic financial advice

Tools available:
- Financial profile builder and analyzer
- Advanced EMI calculator with scenarios
- Loan product comparison engine
- Affordability assessment tools
- Credit score impact analyzer
- Market trend integration

Always provide:
- Personalized recommendations based on user's specific situation
- Clear reasoning behind each recommendation
- Multiple options when possible
- Risk assessment and mitigation strategies
- Actionable next steps

Remember: You're not just calculating numbers - you're providing strategic financial guidance that can significantly impact someone's financial future."""

        super().__init__(
            name="Loan Advisor Agent",
            description="Advanced financial advisor specializing in personalized loan recommendations",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
    
    def _register_tools(self):
        """Register loan advisory tools"""
        
        def analyze_user_profile(user_context: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze user profile for loan recommendations"""
            # Extract key financial indicators
            income = user_context.get("income", 0)
            credit_score = user_context.get("credit_score", 650)
            employment_type = user_context.get("employment_type", "salaried")
            
            # Calculate basic financial health score
            health_score = min(100, (income / 100000) * 40 + (credit_score / 850) * 60)
            
            return {
                "financial_health_score": health_score,
                "risk_category": "low" if health_score > 75 else "medium" if health_score > 50 else "high",
                "recommended_loan_amount": income * 8 if employment_type == "salaried" else income * 6,
                "profile_strengths": self._identify_strengths(user_context),
                "improvement_areas": self._identify_improvements(user_context)
            }
        
        def calculate_loan_eligibility(income: float, expenses: float, credit_score: int, loan_type: str) -> Dict[str, Any]:
            """Calculate loan eligibility and terms"""
            # Basic eligibility calculation
            disposable_income = income - expenses
            dti_ratio = expenses / income if income > 0 else 1
            
            # Eligibility rules
            eligible = (
                income >= 25000 and  # Minimum income
                credit_score >= 600 and  # Minimum credit score
                dti_ratio <= 0.6  # Maximum debt-to-income ratio
            )
            
            if eligible:
                # Calculate loan amount based on type and profile
                if loan_type == "personal_loan":
                    max_amount = min(income * 10, 2000000)  # 10x income or 20L max
                    interest_rate = self._calculate_interest_rate(credit_score, "personal")
                elif loan_type == "business_loan":
                    max_amount = min(income * 15, 5000000)  # 15x income or 50L max
                    interest_rate = self._calculate_interest_rate(credit_score, "business")
                else:
                    max_amount = income * 8
                    interest_rate = self._calculate_interest_rate(credit_score, "general")
                
                return {
                    "eligible": True,
                    "max_loan_amount": max_amount,
                    "recommended_amount": max_amount * 0.8,  # Conservative recommendation
                    "interest_rate": interest_rate,
                    "max_tenure": 60,  # months
                    "dti_ratio": dti_ratio
                }
            else:
                return {
                    "eligible": False,
                    "reasons": self._get_ineligibility_reasons(income, credit_score, dti_ratio),
                    "suggestions": self._get_improvement_suggestions(income, credit_score, dti_ratio)
                }
        
        def calculate_emi_scenarios(principal: float, interest_rate: float, tenures: List[int]) -> Dict[str, Any]:
            """Calculate EMI for different tenure scenarios"""
            scenarios = {}
            
            for tenure_months in tenures:
                monthly_rate = interest_rate / (12 * 100)
                
                if monthly_rate > 0:
                    emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
                else:
                    emi = principal / tenure_months
                
                total_payment = emi * tenure_months
                total_interest = total_payment - principal
                
                scenarios[f"{tenure_months}_months"] = {
                    "tenure_months": tenure_months,
                    "tenure_years": tenure_months / 12,
                    "emi": round(emi, 2),
                    "total_payment": round(total_payment, 2),
                    "total_interest": round(total_interest, 2),
                    "interest_percentage": round((total_interest / principal) * 100, 2)
                }
            
            return {
                "scenarios": scenarios,
                "recommended_tenure": self._recommend_optimal_tenure(scenarios),
                "comparison_summary": self._create_tenure_comparison(scenarios)
            }
        
        def compare_loan_options(loan_requirements: Dict[str, Any]) -> Dict[str, Any]:
            """Compare different loan options based on requirements"""
            options = [
                {
                    "name": "Personal Loan - Premium",
                    "type": "personal_loan",
                    "interest_rate": 10.5,
                    "max_amount": 2000000,
                    "tenure_range": "12-60 months",
                    "processing_fee": "2% + GST",
                    "features": ["Quick approval", "Minimal documentation", "Flexible tenure"]
                },
                {
                    "name": "Personal Loan - Standard",
                    "type": "personal_loan", 
                    "interest_rate": 12.5,
                    "max_amount": 1500000,
                    "tenure_range": "12-48 months",
                    "processing_fee": "1.5% + GST",
                    "features": ["Good rates", "Standard process", "Regular tenure"]
                },
                {
                    "name": "Business Loan",
                    "type": "business_loan",
                    "interest_rate": 11.5,
                    "max_amount": 5000000,
                    "tenure_range": "12-84 months",
                    "processing_fee": "1% + GST",
                    "features": ["Higher amount", "Business benefits", "Longer tenure"]
                }
            ]
            
            # Score and rank options based on requirements
            scored_options = []
            for option in options:
                score = self._score_loan_option(option, loan_requirements)
                scored_options.append({**option, "suitability_score": score})
            
            # Sort by score
            scored_options.sort(key=lambda x: x["suitability_score"], reverse=True)
            
            return {
                "recommended_options": scored_options,
                "comparison_matrix": self._create_comparison_matrix(scored_options),
                "selection_guide": self._create_selection_guide(loan_requirements)
            }
        
        def generate_personalized_advice(user_profile: Dict[str, Any], loan_requirements: Dict[str, Any]) -> Dict[str, Any]:
            """Generate personalized loan advice"""
            advice = {
                "strategy": self._determine_loan_strategy(user_profile, loan_requirements),
                "optimization_tips": self._get_optimization_tips(user_profile),
                "risk_mitigation": self._get_risk_mitigation_advice(user_profile),
                "timeline_suggestions": self._suggest_application_timeline(user_profile, loan_requirements),
                "preparation_checklist": self._create_preparation_checklist(user_profile, loan_requirements)
            }
            
            return advice
        
        # Store tool functions as instance methods
        self.analyze_user_profile = analyze_user_profile
        self.calculate_loan_eligibility = calculate_loan_eligibility
        self.calculate_emi_scenarios = calculate_emi_scenarios
        self.compare_loan_options = compare_loan_options
        self.generate_personalized_advice = generate_personalized_advice
    
    def _estimate_interest_rate(self, loan_type: str, profile: UserFinancialProfile) -> float:
        """Estimate interest rate based on user profile"""
        base_rates = {
            "personal_loan": 16.99,
            "business_loan": 18.99,
            "education_loan": 12.99
        }
        
        base_rate = base_rates.get(loan_type, 18.99)
        
        # Adjust based on credit score
        if profile.credit_score:
            if profile.credit_score >= 800:
                base_rate -= 3.0
            elif profile.credit_score >= 750:
                base_rate -= 2.0
            elif profile.credit_score >= 700:
                base_rate -= 1.0
            elif profile.credit_score < 650:
                base_rate += 2.0
        
        # Adjust based on income level
        if profile.monthly_income:
            if profile.monthly_income >= 100000:
                base_rate -= 1.0
            elif profile.monthly_income >= 50000:
                base_rate -= 0.5
            elif profile.monthly_income < 25000:
                base_rate += 1.0
        
        return max(8.99, min(base_rate, 28.99))  # Keep within reasonable bounds
    
    def _find_optimal_tenure(self, amount: float, rate: float, profile: UserFinancialProfile) -> int:
        """Find optimal tenure balancing EMI affordability and total cost"""
        tenures = [12, 24, 36, 48, 60, 72, 84]
        
        if not profile.max_emi_capacity:
            return 36  # Default to 3 years
        
        for tenure in tenures:
            emi_calc = calculate_emi(amount, rate, tenure)
            if emi_calc["emi"] <= profile.max_emi_capacity:
                return tenure
        
        return tenures[-1]  # Return longest tenure if none fit
    
    def _analyze_loan_pros_cons(self, loan_type: str, profile: UserFinancialProfile, amount: float, rate: float) -> tuple:
        """Analyze pros and cons for a specific loan recommendation"""
        pros = []
        cons = []
        
        if loan_type == "personal_loan":
            pros = [
                "No collateral required",
                "Quick approval and disbursal",
                "Flexible usage for any purpose"
            ]
            cons = [
                "Higher interest rates",
                "Shorter repayment tenure options"
            ]
        elif loan_type == "business_loan":
            pros = [
                "Tax benefits on interest payments",
                "Higher loan amounts available",
                "Longer repayment tenures"
            ]
            cons = [
                "Requires business documentation",
                "Longer processing time"
            ]
        elif loan_type == "education_loan":
            pros = [
                "Lowest interest rates",
                "Tax benefits under Section 80E",
                "Moratorium period available"
            ]
            cons = [
                "Requires admission confirmation",
                "Limited to education expenses only"
            ]
        
        # Add personalized pros/cons based on profile
        if profile.credit_score and profile.credit_score >= 750:
            pros.append(f"Excellent credit score ({profile.credit_score}) qualifies for best rates")
        
        if profile.monthly_income and profile.monthly_income >= 75000:
            pros.append("High income provides negotiation leverage")
        
        return pros, cons
    
    def _calculate_recommendation_confidence(self, loan_type: str, profile: UserFinancialProfile, amount: float) -> float:
        """Calculate confidence score for recommendation"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on profile completeness
        if profile.monthly_income:
            confidence += 0.1
        if profile.credit_score:
            confidence += 0.1
        if profile.employment_type:
            confidence += 0.05
        if profile.max_emi_capacity:
            confidence += 0.1
        
        # Adjust based on profile suitability
        if loan_type == "personal_loan" and profile.monthly_income and profile.monthly_income >= 25000:
            confidence += 0.1
        
        if loan_type == "business_loan" and profile.employment_type == "self_employed":
            confidence += 0.15
        
        return min(confidence, 0.95)
    
    def _get_personalization_factors(self, loan_type: str, profile: UserFinancialProfile) -> List[str]:
        """Get factors that influenced personalization"""
        factors = []
        
        if profile.monthly_income:
            factors.append(f"Monthly income: ₹{profile.monthly_income:,}")
        if profile.credit_score:
            factors.append(f"Credit score: {profile.credit_score}")
        if profile.employment_type:
            factors.append(f"Employment: {profile.employment_type}")
        if profile.loan_purpose:
            factors.append(f"Purpose: {profile.loan_purpose}")
        
        return factors
    
    def _get_affordability_recommendations(self, dti_ratio: float, disposable_income: float) -> List[str]:
        """Get affordability-based recommendations"""
        recommendations = []
        
        if dti_ratio > 50:
            recommendations.extend([
                "Consider reducing loan amount or extending tenure",
                "Focus on debt consolidation to reduce overall EMI burden",
                "Improve credit score to get better interest rates"
            ])
        elif dti_ratio > 35:
            recommendations.extend([
                "Current EMI burden is manageable but monitor carefully",
                "Maintain emergency fund of 6 months expenses",
                "Consider prepayment options to reduce interest burden"
            ])
        else:
            recommendations.extend([
                "Excellent affordability profile",
                "Consider investing surplus in SIPs or other investments",
                "You have room for additional financial goals"
            ])
        
        return recommendations
    
    def _debt_consolidation_strategy(self, profile: UserFinancialProfile) -> List[str]:
        """Strategy for debt consolidation"""
        return [
            "Consolidate all high-interest debts into a single personal loan",
            "Target loans with interest rates above 18% first",
            "Negotiate with current lenders for better rates before consolidating",
            "Set up automatic payments to avoid missed EMIs"
        ]
    
    def _home_improvement_strategy(self, profile: UserFinancialProfile) -> List[str]:
        """Strategy for home improvement loans"""
        return [
            "Consider home improvement loan for lower interest rates",
            "Get multiple quotations for renovation work",
            "Phase improvements to spread cost over time",
            "Look for tax benefits on home loan interest"
        ]
    
    def _business_loan_strategy(self, profile: UserFinancialProfile) -> List[str]:
        """Strategy for business loans"""
        return [
            "Prepare detailed business plan and financial projections",
            "Maintain separate business and personal finances",
            "Consider MUDRA loan for small business requirements",
            "Explore government schemes for business loans"
        ]
    
    def _education_loan_strategy(self, profile: UserFinancialProfile) -> List[str]:
        """Strategy for education loans"""
        return [
            "Apply for education loan early in admission process",
            "Compare interest rates across multiple banks",
            "Understand moratorium period benefits",
            "Keep all academic and admission documents ready"
        ]
    
    def _general_loan_strategy(self, profile: UserFinancialProfile) -> List[str]:
        """General loan strategy"""
        return [
            "Compare offers from multiple lenders",
            "Improve credit score before applying for better rates",
            "Consider co-applicant to increase eligibility",
            "Read all terms and conditions carefully"
        ]
    
    def _estimate_timeline(self, goal: str, profile: UserFinancialProfile) -> str:
        """Estimate timeline for loan goal"""
        timelines = {
            "debt consolidation": "1-2 weeks",
            "home improvement": "2-4 weeks",
            "business": "3-6 weeks",
            "education": "2-3 weeks",
            "default": "1-3 weeks"
        }
        return timelines.get(goal.lower(), timelines["default"])
    
    def _get_preparation_steps(self, goal: str, profile: UserFinancialProfile) -> List[str]:
        """Get preparation steps for loan application"""
        common_steps = [
            "Gather all required documents",
            "Check and improve credit score if needed",
            "Compare offers from multiple lenders",
            "Calculate exact loan requirement"
        ]
        
        if goal.lower() == "business":
            common_steps.extend([
                "Prepare business plan and projections",
                "Organize business registration documents",
                "Get GST registration if applicable"
            ])
        
        return common_steps 