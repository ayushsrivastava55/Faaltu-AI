"""
Application Assistant Agent - Step-by-Step Guidance
==================================================

This agent provides step-by-step guidance through loan application workflows,
document preparation, and application tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .base import BaseAgent

logger = logging.getLogger(__name__)


class ApplicationStep(BaseModel):
    """Represents a single step in the application process"""
    step_number: int
    title: str
    description: str
    required_documents: List[str]
    estimated_time: str
    status: str = "pending"  # pending, in_progress, completed


class ApplicationAssistantAgent(BaseAgent):
    """
    Agent that guides users through loan application processes with
    step-by-step instructions and document preparation assistance.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are a loan application specialist who guides users through every step of the loan application process.

Your expertise includes:
- Step-by-step application guidance
- Document preparation assistance
- Application status tracking
- Process optimization recommendations
- Troubleshooting common issues

You provide:
- Clear, actionable instructions
- Document checklists and requirements
- Timeline estimates and expectations
- Progress tracking and updates
- Support for any application challenges

Always ensure users understand each step and feel confident throughout the process."""

        super().__init__(
            name="Application Assistant Agent",
            description="Step-by-step loan application guidance specialist",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
    
    def _register_tools(self):
        """Register application assistance tools"""
        
        def create_application_roadmap(loan_type: str, user_profile: Dict[str, Any]) -> List[ApplicationStep]:
            """Create a personalized application roadmap"""
            steps = [
                ApplicationStep(
                    step_number=1,
                    title="Document Preparation",
                    description="Gather all required documents",
                    required_documents=self._get_required_documents(loan_type),
                    estimated_time="1-2 days"
                ),
                ApplicationStep(
                    step_number=2,
                    title="Online Application",
                    description="Complete the online application form",
                    required_documents=[],
                    estimated_time="30 minutes"
                ),
                ApplicationStep(
                    step_number=3,
                    title="Document Upload",
                    description="Upload all required documents",
                    required_documents=[],
                    estimated_time="15 minutes"
                ),
                ApplicationStep(
                    step_number=4,
                    title="Verification Process",
                    description="Wait for document verification",
                    required_documents=[],
                    estimated_time="1-2 days"
                ),
                ApplicationStep(
                    step_number=5,
                    title="Approval & Disbursal",
                    description="Loan approval and amount disbursal",
                    required_documents=[],
                    estimated_time="1-2 days"
                )
            ]
            return steps
        
        def get_document_checklist(loan_type: str) -> Dict[str, Any]:
            """Get comprehensive document checklist"""
            return {
                "mandatory_documents": self._get_required_documents(loan_type),
                "optional_documents": self._get_optional_documents(loan_type),
                "document_tips": self._get_document_tips(),
                "common_mistakes": self._get_common_mistakes()
            }
        
        # Store tool functions as instance methods
        self.create_application_roadmap = create_application_roadmap
        self.get_document_checklist = get_document_checklist
    
    def _get_required_documents(self, loan_type: str) -> List[str]:
        """Get required documents for loan type"""
        if loan_type == "personal_loan":
            return ["PAN Card", "Aadhaar Card", "Salary Slips", "Bank Statements"]
        elif loan_type == "business_loan":
            return ["PAN Card", "Aadhaar Card", "Business Registration", "ITR", "Bank Statements"]
        else:
            return ["PAN Card", "Aadhaar Card", "Income Proof", "Address Proof"]
    
    def _get_optional_documents(self, loan_type: str) -> List[str]:
        """Get optional documents that can strengthen application"""
        return ["Form 16", "Investment Proofs", "Property Documents"]
    
    def _get_document_tips(self) -> List[str]:
        """Get tips for document preparation"""
        return [
            "Ensure all documents are clear and legible",
            "Keep original documents ready for verification",
            "Update any outdated documents before applying"
        ]
    
    def _get_common_mistakes(self) -> List[str]:
        """Get common application mistakes to avoid"""
        return [
            "Providing outdated bank statements",
            "Mismatched information across documents",
            "Poor quality document scans"
        ] 