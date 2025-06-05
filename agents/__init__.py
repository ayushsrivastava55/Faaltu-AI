"""
AI Agents Package
================

This package contains all the specialized AI agents for the LendenClub
voice AI assistant system. Each agent is designed to handle specific
types of queries and use specialized tools.
"""

from .base import BaseAgent, AgentRequest, AgentResponse
from .orchestrator import AgentOrchestrator, create_orchestrator
from .loan_advisor import LoanAdvisorAgent
from .market_researcher import MarketResearcherAgent
from .application_assistant import ApplicationAssistantAgent
from .document_processor import DocumentProcessorAgent
from .compliance_checker import ComplianceCheckerAgent

__all__ = [
    'BaseAgent',
    'AgentRequest', 
    'AgentResponse',
    'AgentOrchestrator',
    'create_orchestrator',
    'LoanAdvisorAgent',
    'MarketResearcherAgent',
    'ApplicationAssistantAgent',
    'DocumentProcessorAgent',
    'ComplianceCheckerAgent'
] 