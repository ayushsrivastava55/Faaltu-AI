"""
Document Processor Agent - Document Analysis & Verification
===========================================================

This agent analyzes documents, verifies information, and ensures
compliance with lending requirements.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic_ai import RunContext
from .base import BaseAgent

logger = logging.getLogger(__name__)


class DocumentProcessorAgent(BaseAgent):
    """Agent that processes and verifies loan documents"""
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are a document analysis specialist for loan processing.

Your capabilities include:
- Document verification and validation
- Information extraction and analysis
- Compliance checking
- Risk assessment from documents

You ensure all documents meet lending standards and requirements."""

        super().__init__(
            name="Document Processor Agent",
            description="Document analysis and verification specialist",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
    
    def _register_tools(self):
        """Register document processing tools"""
        
        def analyze_document_requirements(loan_type: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze document requirements for specific loan type"""
            base_docs = ["PAN Card", "Aadhaar Card", "Bank Statements"]
            
            if loan_type == "personal_loan":
                required_docs = base_docs + ["Salary Slips", "Form 16"]
            elif loan_type == "business_loan": 
                required_docs = base_docs + ["Business Registration", "ITR", "Financial Statements"]
            else:
                required_docs = base_docs + ["Income Proof", "Address Proof"]
            
            return {
                "required_documents": required_docs,
                "optional_documents": ["Investment Proofs", "Property Documents"],
                "tips": [
                    "Ensure all documents are clear and legible",
                    "Keep originals ready for verification",
                    "Update any outdated documents"
                ]
            }
        
        # Store tool function as instance method
        self.analyze_document_requirements = analyze_document_requirements 