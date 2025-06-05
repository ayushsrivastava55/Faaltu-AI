"""
LendenClub Lending Knowledge Base
================================

Contains all LendenClub-specific loan products, policies, eligibility criteria,
interest rates, and other lending information for AI agents.
"""

from typing import Dict, Any, List
import json

# LendenClub Loan Products
LOAN_PRODUCTS = {
    "personal_loan": {
        "name": "Personal Loan",
        "description": "Unsecured personal loans for various needs like medical expenses, travel, education, etc.",
        "min_amount": 25000,
        "max_amount": 1000000,
        "interest_rate_range": "10.99% - 24.99% p.a.",
        "tenure_months": [6, 12, 18, 24, 36, 48, 60],
        "processing_fee": "Up to 3% of loan amount",
        "eligibility": {
            "min_age": 21,
            "max_age": 60,
            "min_income": 25000,
            "employment_type": ["salaried", "self_employed"],
            "min_credit_score": 650,
            "work_experience": "Minimum 2 years"
        },
        "documents_required": [
            "PAN Card", "Aadhaar Card", "Salary Slips (last 3 months)",
            "Bank Statements (last 6 months)", "Employment Certificate"
        ]
    },
    "business_loan": {
        "name": "Business Loan", 
        "description": "Loans for business expansion, working capital, equipment purchase, etc.",
        "min_amount": 100000,
        "max_amount": 5000000,
        "interest_rate_range": "12.99% - 28.99% p.a.",
        "tenure_months": [12, 24, 36, 48, 60, 84],
        "processing_fee": "Up to 2.5% of loan amount",
        "eligibility": {
            "min_age": 23,
            "max_age": 65,
            "business_vintage": "Minimum 2 years",
            "annual_turnover": 1000000,
            "min_credit_score": 700,
            "business_type": ["proprietorship", "partnership", "private_limited", "llp"]
        },
        "documents_required": [
            "PAN Card", "Aadhaar Card", "Business Registration Certificate",
            "ITR (last 2 years)", "Bank Statements (last 12 months)", 
            "GST Registration", "Financial Statements"
        ]
    },
    "education_loan": {
        "name": "Education Loan",
        "description": "Loans for higher education in India and abroad",
        "min_amount": 50000,
        "max_amount": 2000000,
        "interest_rate_range": "8.99% - 16.99% p.a.",
        "tenure_months": [60, 84, 120, 180, 240],
        "processing_fee": "Up to 1% of loan amount",
        "eligibility": {
            "min_age": 18,
            "max_age": 35,
            "academic_score": "Minimum 60% in previous qualification",
            "co_applicant_required": True,
            "co_applicant_income": 300000
        },
        "documents_required": [
            "PAN Card", "Aadhaar Card", "Academic Transcripts",
            "Admission Letter", "Fee Structure", "Co-applicant Income Proof",
            "Bank Statements", "Passport (for abroad studies)"
        ]
    }
}

# Interest Rate Calculator Data
INTEREST_CALCULATIONS = {
    "base_rates": {
        "personal_loan": 12.99,
        "business_loan": 15.99,
        "education_loan": 10.99
    },
    "risk_adjustments": {
        "credit_score": {
            800: -2.0,  # Excellent credit gets 2% discount
            750: -1.0,  # Good credit gets 1% discount
            700: 0.0,   # Fair credit gets base rate
            650: 2.0,   # Poor credit gets 2% markup
            600: 4.0    # Very poor credit gets 4% markup
        },
        "income_level": {
            "high": -0.5,     # Income > 10L gets discount
            "medium": 0.0,    # Income 5-10L gets base rate
            "low": 1.0        # Income < 5L gets markup
        }
    }
}

# Common FAQs
LENDING_FAQS = {
    "What is LendenClub?": "LendenClub is India's largest peer-to-peer lending platform that connects borrowers with lenders, offering personal loans, business loans, and education loans at competitive interest rates.",
    
    "How does P2P lending work?": "In peer-to-peer lending, LendenClub acts as an intermediary platform where individual lenders can lend money directly to borrowers. This eliminates traditional banks and often results in better rates for both parties.",
    
    "What are the eligibility criteria for personal loans?": "For personal loans, you must be 21-60 years old, have a minimum monthly income of ₹25,000, credit score of 650+, and at least 2 years of work experience.",
    
    "How is my interest rate determined?": "Your interest rate is based on multiple factors including your credit score, income level, employment stability, loan amount, and tenure. Better credit profiles get lower rates.",
    
    "What documents do I need for a loan?": "Common documents include PAN card, Aadhaar card, salary slips, bank statements, and employment certificate. Specific requirements vary by loan type.",
    
    "How long does loan processing take?": "Personal loans can be processed within 24-48 hours of document submission. Business loans may take 3-7 days depending on complexity.",
    
    "Can I prepay my loan?": "Yes, you can prepay your loan anytime after 6 EMIs. Prepayment charges may apply as per the loan agreement.",
    
    "What is the maximum loan amount?": "Personal loans up to ₹10 lakhs, business loans up to ₹50 lakhs, and education loans up to ₹20 lakhs are available.",
    
    "Do you charge processing fees?": "Yes, processing fees vary by loan type - up to 3% for personal loans, 2.5% for business loans, and 1% for education loans.",
    
    "How do I check my loan eligibility?": "You can check eligibility by providing basic details like income, employment type, and credit score. Our system will instantly show your eligible loan amount and rate."
}

# Compliance and Regulatory Info
COMPLIANCE_INFO = {
    "rbi_guidelines": "LendenClub operates under RBI guidelines for peer-to-peer lending platforms and is registered as an NBFC-P2P.",
    "data_security": "All customer data is encrypted and stored securely. We follow industry best practices for data protection.",
    "grievance_redressal": "Any complaints can be raised through our customer support or grievance redressal mechanism as per RBI guidelines.",
    "fair_practices": "We follow fair lending practices and transparent pricing. All charges are disclosed upfront.",
    "credit_bureau_reporting": "Loan performance is reported to credit bureaus which can impact your credit score positively or negatively."
}

def get_loan_product_info(product_type: str) -> Dict[str, Any]:
    """Get detailed information about a specific loan product"""
    return LOAN_PRODUCTS.get(product_type, {})

def calculate_emi(principal: float, rate: float, tenure_months: int) -> Dict[str, float]:
    """Calculate EMI using standard formula"""
    monthly_rate = rate / (12 * 100)
    emi = (principal * monthly_rate * (1 + monthly_rate) ** tenure_months) / \
          ((1 + monthly_rate) ** tenure_months - 1)
    
    total_amount = emi * tenure_months
    total_interest = total_amount - principal
    
    return {
        "emi": round(emi, 2),
        "total_amount": round(total_amount, 2),
        "total_interest": round(total_interest, 2),
        "principal": principal,
        "rate": rate,
        "tenure_months": tenure_months
    }

def check_basic_eligibility(loan_type: str, age: int, income: int, credit_score: int) -> Dict[str, Any]:
    """Check basic eligibility for a loan type"""
    if loan_type not in LOAN_PRODUCTS:
        return {"eligible": False, "reason": "Invalid loan type"}
    
    product = LOAN_PRODUCTS[loan_type]
    eligibility = product["eligibility"]
    
    # Check age
    if age < eligibility["min_age"] or age > eligibility["max_age"]:
        return {
            "eligible": False, 
            "reason": f"Age should be between {eligibility['min_age']} and {eligibility['max_age']} years"
        }
    
    # Check income (for personal and education loans)
    if "min_income" in eligibility and income < eligibility["min_income"]:
        return {
            "eligible": False,
            "reason": f"Minimum monthly income should be ₹{eligibility['min_income']:,}"
        }
    
    # Check credit score
    if "min_credit_score" in eligibility and credit_score < eligibility["min_credit_score"]:
        return {
            "eligible": False,
            "reason": f"Minimum credit score should be {eligibility['min_credit_score']}"
        }
    
    # Calculate eligible amount range
    min_amount = product["min_amount"]
    max_amount = product["max_amount"]
    
    # Adjust max amount based on income (rough calculation)
    if "min_income" in eligibility:
        income_based_max = income * 40  # ~40x monthly income as max loan amount
        max_amount = min(max_amount, income_based_max)
    
    return {
        "eligible": True,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "estimated_rate_range": product["interest_rate_range"],
        "tenure_options": product["tenure_months"]
    }

def get_estimated_rate(loan_type: str, credit_score: int, income: int) -> float:
    """Get estimated interest rate based on profile"""
    if loan_type not in INTEREST_CALCULATIONS["base_rates"]:
        return 18.0  # Default rate
    
    base_rate = INTEREST_CALCULATIONS["base_rates"][loan_type]
    
    # Credit score adjustment
    credit_adjustment = 0.0
    for score_threshold in sorted(INTEREST_CALCULATIONS["risk_adjustments"]["credit_score"].keys(), reverse=True):
        if credit_score >= score_threshold:
            credit_adjustment = INTEREST_CALCULATIONS["risk_adjustments"]["credit_score"][score_threshold]
            break
    
    # Income level adjustment
    income_adjustment = 0.0
    if income >= 1000000:  # 10L+
        income_adjustment = INTEREST_CALCULATIONS["risk_adjustments"]["income_level"]["high"]
    elif income >= 500000:  # 5-10L
        income_adjustment = INTEREST_CALCULATIONS["risk_adjustments"]["income_level"]["medium"]
    else:  # <5L
        income_adjustment = INTEREST_CALCULATIONS["risk_adjustments"]["income_level"]["low"]
    
    final_rate = base_rate + credit_adjustment + income_adjustment
    return max(8.0, min(30.0, final_rate))  # Cap between 8% and 30%

def search_faqs(query: str) -> List[Dict[str, str]]:
    """Search FAQs for relevant answers"""
    query_lower = query.lower()
    matching_faqs = []
    
    for question, answer in LENDING_FAQS.items():
        if any(word in question.lower() or word in answer.lower() 
               for word in query_lower.split()):
            matching_faqs.append({
                "question": question,
                "answer": answer,
                "relevance_score": 0.8  # Simple relevance scoring
            })
    
    return sorted(matching_faqs, key=lambda x: x["relevance_score"], reverse=True)[:3] 