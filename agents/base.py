"""
Base Agent Classes and Models
============================

Contains the base classes and data models that all agents inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent
import asyncio

logger = logging.getLogger(__name__)


class AgentRequest(BaseModel):
    """Request model for agent queries"""
    query: str = Field(..., description="The user's query or question")
    session_id: Optional[str] = Field(default=None, description="Session identifier for context")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User profile and context information")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context from previous steps")
    voice_input: bool = Field(default=False, description="Whether the input came from voice")


class AgentResponse(BaseModel):
    """Response model from agent processing"""
    query: str = Field(..., description="The original query")
    response: str = Field(..., description="The agent's response")
    agent_name: str = Field(..., description="Name of the agent that processed the query")
    session_id: str = Field(..., description="Session identifier")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the response")
    processing_time: float = Field(..., description="Time taken to process the query in seconds")
    timestamp: datetime = Field(..., description="When the response was generated")
    tools_used: List[str] = Field(default_factory=list, description="List of tools/functions used")
    context_used: Dict[str, Any] = Field(default_factory=dict, description="Context information used in processing")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the system.
    
    This class provides the common interface and functionality that all
    specialized agents must implement, including conversation memory integration.
    """
    
    def __init__(self, name: str, description: str, system_prompt: str, 
                 openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.openai_client = openai_client
        self.storage_service = storage_service
        self.graph_intelligence = graph_intelligence
        self.conversation_memory = conversation_memory
        
        # Initialize PydanticAI agent
        try:
            self.agent = Agent(
                model='openai:gpt-3.5-turbo',
                system_prompt=system_prompt,
                deps_type=type(None)  # No dependencies for now
            )
            self._register_tools()
            logger.info(f"Initialized {name} successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {name}: {e}")
            self.agent = None
    
    @abstractmethod
    def _register_tools(self):
        """Register tools/functions that this agent can use"""
        pass
    
    def get_agent_context(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context specific to this agent type.
        Can be overridden by subclasses for specialized context building.
        """
        return {
            "agent_name": self.name,
            "agent_type": self.__class__.__name__,
            "query": query,
            "user_context": user_context,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _build_contextual_prompt(self, request: AgentRequest) -> str:
        """Build a contextual prompt including conversation memory"""
        base_prompt = self.system_prompt
        
        # Add conversation memory context if available
        if self.conversation_memory and request.session_id:
            if hasattr(self.conversation_memory, 'get_contextual_prompt_addition'):
                if asyncio.iscoroutinefunction(self.conversation_memory.get_contextual_prompt_addition):
                    contextual_addition = await self.conversation_memory.get_contextual_prompt_addition(request.session_id)
                else:
                    contextual_addition = self.conversation_memory.get_contextual_prompt_addition(request.session_id)
                if contextual_addition:
                    base_prompt += contextual_addition
        
        # Add additional context from request
        if request.additional_context:
            context_parts = []
            if "step_context" in request.additional_context:
                context_parts.append(f"Previous Step Results: {request.additional_context['step_context']}")
            if "conversation_history" in request.additional_context:
                history = request.additional_context["conversation_history"]
                if history:
                    history_text = "\n".join([f"User: {turn.get('user_query', '')}\nAssistant: {turn.get('system_response', '')[:100]}..." for turn in history[-2:]])
                    context_parts.append(f"Recent Exchange:\n{history_text}")
            
            if context_parts:
                base_prompt += f"\n\nAdditional Context:\n{chr(10).join(context_parts)}"
        
        return base_prompt
    
    async def process_query(self, request: AgentRequest) -> AgentResponse:
        """
        Main method to process a query with conversation memory integration.
        This is the standard interface all agents must implement.
        """
        start_time = datetime.now()
        
        if not self.agent:
            return await self._create_error_response(
                request, "Agent not properly initialized", start_time
            )
        
        try:
            # Extract and enhance user context with conversation memory
            enhanced_user_context = request.user_context.copy()
            if self.conversation_memory and request.session_id:
                if hasattr(self.conversation_memory, 'extract_user_context_from_query'):
                    if asyncio.iscoroutinefunction(self.conversation_memory.extract_user_context_from_query):
                        memory_context = await self.conversation_memory.extract_user_context_from_query(
                            request.query, request.session_id
                        )
                    else:
                        memory_context = self.conversation_memory.extract_user_context_from_query(
                            request.query, request.session_id
                        )
                    enhanced_user_context.update(memory_context)
            
            # Build agent-specific context
            agent_context = self.get_agent_context(request.query, enhanced_user_context)
            
            # Build contextual prompt
            contextual_prompt = await self._build_contextual_prompt(request)
            
            # Update the agent's system prompt temporarily for this request
            original_prompt = self.agent.system_prompt
            try:
                # Create a new agent instance with contextual prompt for this request
                contextual_agent = Agent(
                    model='openai:gpt-3.5-turbo',
                    system_prompt=contextual_prompt,
                    deps_type=type(None)
                )
                
                # Process the query using PydanticAI with contextual prompt
                result = await contextual_agent.run(request.query)
                
            finally:
                # Restore original prompt (though we're using a separate agent instance)
                pass
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = AgentResponse(
                query=request.query,
                response=str(result.data) if hasattr(result, 'data') else str(result),
                agent_name=self.name,
                session_id=request.session_id or f"session_{int(start_time.timestamp())}",
                confidence=0.8,  # Default confidence, can be overridden by subclasses
                processing_time=processing_time,
                timestamp=datetime.now(),
                tools_used=self._get_tools_used(),  # Get tools from specific agent implementation
                context_used=agent_context,
                follow_up_suggestions=self._generate_follow_up_suggestions(request.query, str(result.data) if hasattr(result, 'data') else str(result))
            )
            
            # Store conversation in memory if available
            if self.conversation_memory and request.session_id:
                if hasattr(self.conversation_memory, 'add_conversation_turn'):
                    if asyncio.iscoroutinefunction(self.conversation_memory.add_conversation_turn):
                        await self.conversation_memory.add_conversation_turn(
                            session_id=request.session_id,
                            user_query=request.query,
                            system_response=response.response,
                            agents_consulted=[self.name],
                            tools_used=response.tools_used,
                            reasoning_approach=f"{self.name} processing",
                            user_context=enhanced_user_context,
                            confidence=response.confidence,
                            processing_time=response.processing_time
                        )
                    else:
                        self.conversation_memory.add_conversation_turn(
                            session_id=request.session_id,
                            user_query=request.query,
                            system_response=response.response,
                            agents_consulted=[self.name],
                            tools_used=response.tools_used,
                            reasoning_approach=f"{self.name} processing",
                            user_context=enhanced_user_context,
                            confidence=response.confidence,
                            processing_time=response.processing_time
                        )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return await self._create_error_response(request, str(e), start_time)
    
    def _get_tools_used(self) -> List[str]:
        """Get list of tools used by this agent. Override in subclasses."""
        return []
    
    def _generate_follow_up_suggestions(self, query: str, response: str) -> List[str]:
        """Generate follow-up suggestions based on query and response. Override in subclasses."""
        return []
    
    async def _create_error_response(self, request: AgentRequest, error_message: str, 
                             start_time: datetime) -> AgentResponse:
        """Create a standardized error response"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        response = AgentResponse(
            query=request.query,
            response=f"I apologize, but I encountered an error processing your request: {error_message}",
            agent_name=self.name,
            session_id=request.session_id or f"session_{int(start_time.timestamp())}",
            confidence=0.1,
            processing_time=processing_time,
            timestamp=datetime.now(),
            tools_used=[],
            context_used={"error": error_message},
            follow_up_suggestions=["Please try rephrasing your question", "Contact support if the issue persists"]
        )
        
        # Store error in conversation memory if available
        if self.conversation_memory and request.session_id:
            if hasattr(self.conversation_memory, 'add_conversation_turn'):
                if asyncio.iscoroutinefunction(self.conversation_memory.add_conversation_turn):
                    await self.conversation_memory.add_conversation_turn(
                        session_id=request.session_id,
                        user_query=request.query,
                        system_response=response.response,
                        agents_consulted=[self.name],
                        tools_used=[],
                        reasoning_approach=f"{self.name} error handling",
                        user_context=request.user_context,
                        confidence=response.confidence,
                        processing_time=response.processing_time
                    )
                else:
                    self.conversation_memory.add_conversation_turn(
                        session_id=request.session_id,
                        user_query=request.query,
                        system_response=response.response,
                        agents_consulted=[self.name],
                        tools_used=[],
                        reasoning_approach=f"{self.name} error handling",
                        user_context=request.user_context,
                        confidence=response.confidence,
                        processing_time=response.processing_time
                    )
        
        return response
    
    def is_available(self) -> bool:
        """Check if the agent is available and properly initialized"""
        return self.agent is not None
    
    def get_capabilities(self) -> List[str]:
        """Return a list of this agent's capabilities"""
        capabilities = [
            "Natural language processing",
            "Query understanding",
            "Context-aware responses"
        ]
        
        if self.conversation_memory:
            capabilities.extend([
                "Conversation memory",
                "User profile learning",
                "Contextual continuity"
            ])
        
        return capabilities 