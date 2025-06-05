"""
Compliance Checker Agent - Regulatory Compliance & Risk Assessment
==================================================================

This agent ensures all loan recommendations and processes comply with
RBI guidelines and regulatory requirements.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic_ai import RunContext
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ComplianceCheckerAgent(BaseAgent):
    """Agent that ensures regulatory compliance and risk assessment"""
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are a compliance and regulatory specialist for lending operations.

Your responsibilities include:
- RBI guideline compliance checking
- Risk assessment and mitigation
- Regulatory requirement validation
- Policy adherence monitoring

You ensure all lending activities meet regulatory standards."""

        super().__init__(
            name="Compliance Checker Agent",
            description="Regulatory compliance and risk assessment specialist",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
    
    def _register_tools(self):
        """Register compliance checking tools"""
        
        def check_regulatory_compliance(loan_details: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
            """Check regulatory compliance for loan application"""
            loan_amount = loan_details.get("amount", 0)
            user_income = user_profile.get("income", 0)
            
            compliance_checks = {
                "income_verification": user_income > 0,
                "loan_to_income_ratio": loan_amount <= (user_income * 10) if user_income > 0 else False,
                "kyc_compliance": True,  # Simplified for demo
                "regulatory_limits": loan_amount <= 2000000  # 20L limit for personal loans
            }
            
            all_compliant = all(compliance_checks.values())
            
            return {
                "compliant": all_compliant,
                "checks": compliance_checks,
                "recommendations": [
                    "Ensure income verification is complete",
                    "Maintain loan-to-income ratio within limits",
                    "Complete KYC requirements"
                ] if not all_compliant else ["All compliance checks passed"]
            }
        
        # Store tool function as instance method
        self.check_regulatory_compliance = check_regulatory_compliance 