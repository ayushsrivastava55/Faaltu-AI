"""
Agent Orchestrator - The Brain of the Agentic System
===================================================

This orchestrator analyzes queries, plans multi-step solutions, and delegates
to specialized agents. It replaces simple knowledge retrieval with intelligent
reasoning and tool usage.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .base import BaseAgent, AgentRequest, AgentResponse
from .loan_advisor import LoanAdvisorAgent
from .document_processor import DocumentProcessorAgent
from .market_researcher import MarketResearcherAgent
from .application_assistant import ApplicationAssistantAgent
from .compliance_checker import ComplianceCheckerAgent
from .knowledge_ingestion import KnowledgeIngestionAgent
from .rl_optimizer import RLOptimizerAgent

logger = logging.getLogger(__name__)


class TaskPlan(BaseModel):
    """Represents a multi-step plan to solve a user query"""
    steps: List[str] = Field(..., description="Ordered list of steps to execute")
    agents_needed: List[str] = Field(..., description="List of agent types needed")
    estimated_complexity: str = Field(..., description="simple, medium, or complex")
    expected_outcome: str = Field(..., description="What we expect to achieve")


class AgentContext(BaseModel):
    """Context that gets passed between agents"""
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)
    current_step: int = Field(default=0)
    total_steps: int = Field(default=1)


class AgentOrchestrator(BaseAgent):
    """
    The main orchestrator that coordinates multiple specialized agents
    to solve complex lending queries through multi-step reasoning.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are the Chief AI Orchestrator for LendenClub's intelligent lending platform.

Your core capabilities:
1. **Analyze complex queries** and break them into actionable steps
2. **Plan multi-step solutions** using available specialized agents
3. **Coordinate agent workflows** to provide comprehensive answers
4. **Adapt plans** based on intermediate results
5. **Synthesize information** from multiple sources
6. **Maintain conversation context** across multiple exchanges

Available Specialized Agents:
- LoanAdvisorAgent: Personalized loan recommendations and comparisons
- DocumentProcessorAgent: Document analysis, verification, and requirements
- MarketResearcherAgent: Real-time market rates and competitor analysis  
- ApplicationAssistantAgent: Step-by-step application guidance
- ComplianceCheckerAgent: Regulatory compliance and risk assessment
- KnowledgeIngestionAgent: Continuous learning from real-world data sources
- RLOptimizerAgent: Reinforcement learning-based optimization

Your Decision-Making Process:
1. **Understand user intent** considering conversation history and context
2. **Analyze query complexity** (simple/medium/complex)
3. **Leverage conversation memory** to provide contextual responses
4. **Create step-by-step execution plan** based on user's journey
5. **Delegate to appropriate specialist agents** with full context
6. **Monitor progress and adapt** as needed
7. **Synthesize results** into comprehensive, personalized responses

Conversation Memory Integration:
- Remember previous interactions and user preferences
- Build on previous conversation topics
- Provide contextual follow-ups and suggestions
- Maintain user financial profile across sessions
- Adapt responses based on user's communication style

Key Principles:
- Always provide actionable, personalized advice
- Consider user's financial profile and goals
- Build on previous conversation context
- Ensure compliance with lending regulations
- Offer multiple options when possible
- Explain reasoning behind recommendations
- Guide users through complex processes step-by-step
- Learn and adapt to user preferences over time

Remember: You're not just retrieving information - you're actively solving problems and guiding users through their lending journey with full awareness of their history and context."""

        super().__init__(
            name="Agent Orchestrator",
            description="Main coordination agent that plans and executes multi-step solutions with conversation memory",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
        
        # Initialize specialized agents with conversation memory
        self.specialist_agents = self._initialize_specialists()
        self.active_contexts: Dict[str, AgentContext] = {}
    
    def _initialize_specialists(self) -> Dict[str, BaseAgent]:
        """Initialize all specialized agents with conversation memory"""
        try:
            return {
                "loan_advisor": LoanAdvisorAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "document_processor": DocumentProcessorAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "market_researcher": MarketResearcherAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "application_assistant": ApplicationAssistantAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "compliance_checker": ComplianceCheckerAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "knowledge_ingestion": KnowledgeIngestionAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                ),
                "rl_optimizer": RLOptimizerAgent(
                    self.openai_client, self.storage_service, self.graph_intelligence, self.conversation_memory
                )
            }
        except Exception as e:
            logger.error(f"Failed to initialize some specialist agents: {e}")
            return {}
    
    def _register_tools(self):
        """Register orchestration tools"""
        
        # Remove keyword matching - let the LLM agent handle analysis and planning
        # Store tool functions as instance methods for the specialist agents
        async def execute_plan_step(step_description: str, agent_type: str, context: AgentContext) -> Dict[str, Any]:
            """Execute a single step of the plan using the appropriate agent"""
            if agent_type not in self.specialist_agents:
                return {"error": f"Agent type {agent_type} not available"}
            
            agent = self.specialist_agents[agent_type]
            
            # Create agent request with context
            request = AgentRequest(
                query=step_description,
                session_id=context.conversation_history[-1].get("session_id") if context.conversation_history else "default",
                user_context=context.user_profile,
                additional_context={
                    "step_context": context.intermediate_results,
                    "conversation_history": context.conversation_history[-3:]  # Last 3 messages for context
                }
            )
            
            try:
                response = await agent.process_query(request)
                return {
                    "success": True,
                    "agent_used": agent_type,
                    "response": response.response,
                    "tools_used": response.tools_used,
                    "confidence": response.confidence,
                    "context_updates": response.context_used
                }
            except Exception as e:
                logger.error(f"Error executing step with {agent_type}: {e}")
                return {"error": str(e), "agent_used": agent_type}
        
        # Store tool functions as instance methods
        self.execute_plan_step = execute_plan_step
    
    def _get_tools_used(self) -> List[str]:
        """Get list of tools used by the orchestrator"""
        return ["query_analysis", "plan_execution", "agent_coordination", "response_synthesis"]
    
    def _generate_follow_up_suggestions(self, query: str, response: str) -> List[str]:
        """Generate intelligent follow-up suggestions based on conversation context"""
        suggestions = []
        
        query_lower = query.lower()
        
        # Context-aware suggestions
        if "loan" in query_lower:
            suggestions.extend([
                "Would you like to compare different loan options?",
                "Do you need help with the application process?",
                "Would you like to see current market rates?"
            ])
        
        if "rate" in query_lower or "interest" in query_lower:
            suggestions.extend([
                "Would you like to see how rates have changed recently?",
                "Should I help you calculate EMI for different amounts?",
                "Do you want to compare rates from different lenders?"
            ])
        
        if "application" in query_lower or "apply" in query_lower:
            suggestions.extend([
                "Would you like a document checklist?",
                "Do you need step-by-step application guidance?",
                "Should I help you prepare your financial documents?"
            ])
        
        # Limit to top 3 suggestions
        return suggestions[:3]

    async def process_query(self, request: AgentRequest) -> AgentResponse:
        """Main orchestration logic using LLM reasoning with conversation memory"""
        start_time = datetime.now()
        session_id = request.session_id or f"session_{int(start_time.timestamp())}"
        
        try:
            # Get conversation context if available
            conversation_context = None
            if self.conversation_memory:
                # Fix: await the async method call
                if hasattr(self.conversation_memory, 'get_conversation_context') and asyncio.iscoroutinefunction(self.conversation_memory.get_conversation_context):
                    conversation_context = await self.conversation_memory.get_conversation_context(session_id)
                else:
                    conversation_context = self.conversation_memory.get_conversation_context(session_id)
            
            # Enhanced user context with conversation memory
            enhanced_user_context = request.user_context.copy()
            if self.conversation_memory:
                # Fix: check if method is async before calling
                if hasattr(self.conversation_memory, 'extract_user_context_from_query'):
                    if asyncio.iscoroutinefunction(self.conversation_memory.extract_user_context_from_query):
                        memory_context = await self.conversation_memory.extract_user_context_from_query(
                            request.query, session_id
                        )
                    else:
                        memory_context = self.conversation_memory.extract_user_context_from_query(
                            request.query, session_id
                        )
                    enhanced_user_context.update(memory_context)
            
            # Build contextual analysis prompt
            context_info = ""
            if conversation_context and conversation_context.conversation_history:
                recent_topics = [turn.user_query for turn in conversation_context.conversation_history[-3:]]
                # Fix: properly truncate each topic string and join
                truncated_topics = [topic[:100] + "..." if len(topic) > 100 else topic for topic in recent_topics]
                context_info = f"\nRecent conversation topics: {', '.join(truncated_topics)}"
                
                if conversation_context.current_topic:
                    context_info += f"\nCurrent conversation topic: {conversation_context.current_topic}"
                
                if conversation_context.user_profile.frequently_asked_topics:
                    context_info += f"\nUser's frequent topics: {', '.join(conversation_context.user_profile.frequently_asked_topics[:3])}"
            
            # Use the LLM agent to analyze the query and create an execution plan
            analysis_prompt = f"""
Analyze this user query with full conversation context: "{request.query}"

User Context: {enhanced_user_context}
{context_info}

Available Specialist Agents:
- loan_advisor: Personalized loan recommendations, calculations, and financial advice
- market_researcher: Real-time market rates, competitor analysis, and trends
- application_assistant: Step-by-step application guidance and process help
- document_processor: Document analysis, verification, and requirements
- compliance_checker: Regulatory compliance and risk assessment
- knowledge_ingestion: Continuous learning from real-world data sources
- rl_optimizer: Reinforcement learning-based optimization

Your task:
1. Understand the user's intent considering conversation history
2. Determine what information/analysis is required
3. Decide which specialist agents should be involved
4. Create a logical sequence of steps that builds on previous context

Respond with a JSON object containing:
{{
    "analysis": "Your understanding of what the user wants, considering context",
    "complexity": "simple/medium/complex",
    "agents_needed": ["list", "of", "agent", "types"],
    "execution_steps": ["step 1 description", "step 2 description"],
    "reasoning": "Why you chose this approach given the conversation context",
    "context_acknowledgment": "How you're building on previous conversation"
}}
"""

            # Get LLM analysis and plan
            analysis_result = await self.agent.run(analysis_prompt, message_history=[])
            
            # Parse the LLM response (should be JSON)
            import json
            try:
                if hasattr(analysis_result, 'data'):
                    plan_data = json.loads(str(analysis_result.data))
                else:
                    plan_data = json.loads(str(analysis_result))
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Failed to parse LLM analysis as JSON: {e}")
                # Fallback to direct LLM response
                return await self._handle_simple_query(request, enhanced_user_context)

            # Execute the plan
            if plan_data.get("complexity") == "simple" and len(plan_data.get("agents_needed", [])) <= 1:
                # Handle simple queries directly or with one agent
                return await self._execute_simple_plan(request, plan_data, enhanced_user_context)
            else:
                # Handle complex multi-agent queries
                return await self._execute_complex_plan(request, plan_data, enhanced_user_context)
                
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            # Fallback to simple response on error
            return AgentResponse(
                query=request.query,
                response=f"I apologize, but I encountered an error processing your request: {str(e)}",
                agent_name=self.name,
                session_id=request.session_id or f"session_{int(start_time.timestamp())}",
                confidence=0.1,
                processing_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                tools_used=[],
                context_used={"error": str(e)},
                follow_up_suggestions=["Please try rephrasing your question", "Contact support if the issue persists"]
            )

    async def _handle_simple_query(self, request: AgentRequest, user_context: Dict[str, Any]) -> AgentResponse:
        """Handle simple queries directly with conversation memory context"""
        start_time = datetime.now()
        
        # Get conversation memory context
        contextual_addition = ""
        if self.conversation_memory:
            # Fix: check if method is async before calling
            if hasattr(self.conversation_memory, 'get_contextual_prompt_addition'):
                if asyncio.iscoroutinefunction(self.conversation_memory.get_contextual_prompt_addition):
                    contextual_addition = await self.conversation_memory.get_contextual_prompt_addition(request.session_id, request.query)
                else:
                    contextual_addition = self.conversation_memory.get_contextual_prompt_addition(request.session_id, request.query)
        
        # Build enhanced prompt with conversation context
        enhanced_prompt = f"""
{contextual_addition}

Current User Query: {request.query}

Please provide a helpful, personalized response that acknowledges any previous conversation context and user information you've learned about them.
"""
        
        # Use orchestrator's own LLM for simple responses with context
        simple_response = await self.agent.run(enhanced_prompt)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AgentResponse(
            query=request.query,
            response=str(simple_response.data) if hasattr(simple_response, 'data') else str(simple_response),
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.7,
            processing_time=processing_time,
            timestamp=datetime.now(),
            tools_used=["direct_llm_response"],
            context_used={"approach": "simple", "agents_consulted": [self.name]},
            follow_up_suggestions=self._generate_follow_up_suggestions(request.query, str(simple_response))
        )

    async def _execute_simple_plan(self, request: AgentRequest, plan_data: Dict[str, Any], user_context: Dict[str, Any]) -> AgentResponse:
        """Execute a simple plan with one or no specialist agents"""
        start_time = datetime.now()
        
        agents_needed = plan_data.get("agents_needed", [])
        
        if not agents_needed:
            return await self._handle_simple_query(request, user_context)
        
        # Use the first (and likely only) agent
        agent_type = agents_needed[0]
        
        if agent_type not in self.specialist_agents:
            return await self._handle_simple_query(request, user_context)
        
        # Delegate to specialist agent
        specialist_request = AgentRequest(
            query=request.query,
            session_id=request.session_id,
            user_context=user_context,
            additional_context=request.additional_context
        )
        
        specialist_response = await self.specialist_agents[agent_type].process_query(specialist_request)
        
        # Update response with orchestration context
        specialist_response.context_used["agents_consulted"] = [agent_type]
        specialist_response.context_used["reasoning_approach"] = plan_data.get("reasoning", "Single agent delegation")
        
        return specialist_response

    async def _execute_complex_plan(self, request: AgentRequest, plan_data: Dict[str, Any], user_context: Dict[str, Any]) -> AgentResponse:
        """Execute a complex multi-step plan"""
        start_time = datetime.now()
        
        steps = plan_data.get("execution_steps", [])
        agents_needed = plan_data.get("agents_needed", [])
        
        step_results = []
        used_agents = []
        all_tools_used = []
        
        # Execute each step
        for i, step in enumerate(steps):
            if i < len(agents_needed):
                agent_type = agents_needed[i]
                if agent_type in self.specialist_agents:
                    
                    # Create context for this step
                    step_context = {
                        "previous_results": step_results,
                        "current_step": i + 1,
                        "total_steps": len(steps),
                        "plan_analysis": plan_data.get("analysis", "")
                    }
                    
                    specialist_request = AgentRequest(
                        query=step,
                        session_id=request.session_id,
                        user_context=user_context,
                        additional_context={"step_context": step_context}
                    )
                    
                    try:
                        response = await self.specialist_agents[agent_type].process_query(specialist_request)
                        step_results.append({
                            "step": step,
                            "agent": agent_type,
                            "response": response.response,
                            "confidence": response.confidence
                        })
                        used_agents.append(agent_type)
                        all_tools_used.extend(response.tools_used)
                    except Exception as e:
                        logger.error(f"Error in step {i+1} with {agent_type}: {e}")
                        step_results.append({
                            "step": step,
                            "agent": agent_type,
                            "response": f"Error processing step: {str(e)}",
                            "confidence": 0.1
                        })
        
        # Synthesize all results
        synthesis = await self._synthesize_results(request.query, step_results, plan_data)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AgentResponse(
            query=request.query,
            response=synthesis["final_response"],
            agent_name=self.name,
            session_id=request.session_id,
            confidence=synthesis["confidence"],
            processing_time=processing_time,
            timestamp=datetime.now(),
            tools_used=list(set(all_tools_used + ["multi_agent_coordination", "response_synthesis"])),
            context_used={
                "agents_consulted": used_agents,
                "reasoning_approach": plan_data.get("reasoning", "Multi-agent coordination"),
                "execution_steps": len(steps),
                "step_results": step_results
            },
            follow_up_suggestions=synthesis.get("follow_ups", self._generate_follow_up_suggestions(request.query, synthesis["final_response"]))
        )

    async def _synthesize_results(self, original_query: str, step_results: List[Dict[str, Any]], plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize results from multiple agents into a coherent response"""
        
        # Prepare synthesis context
        results_summary = "\n".join([
            f"Step {i+1} ({result['agent']}): {result['response'][:300]}..."
            for i, result in enumerate(step_results)
        ])
        
        synthesis_prompt = f"""
Original Query: {original_query}
Plan Analysis: {plan_data.get('analysis', '')}

Results from specialist agents:
{results_summary}

Synthesize these results into a comprehensive, coherent response that:
1. Directly answers the user's original question
2. Integrates insights from all agents
3. Provides actionable recommendations
4. Maintains a conversational tone
5. Builds on any conversation context

Provide a natural, helpful response that flows well and doesn't feel like a concatenation of separate responses.
"""
        
        synthesis_result = await self.agent.run(synthesis_prompt)
        
        # Calculate average confidence
        confidences = [result.get("confidence", 0.5) for result in step_results if "confidence" in result]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7
        
        # Generate follow-up suggestions
        follow_ups = await self._generate_follow_ups(original_query, str(synthesis_result.data))
        
        return {
            "final_response": str(synthesis_result.data) if hasattr(synthesis_result, 'data') else str(synthesis_result),
            "confidence": min(avg_confidence, 0.9),  # Cap at 90%
            "follow_ups": follow_ups
        }

    async def _generate_follow_ups(self, original_query: str, synthesis: str) -> List[str]:
        """Generate contextual follow-up suggestions"""
        
        follow_up_prompt = f"""
Based on this conversation:
User Query: {original_query}
Assistant Response: {synthesis[:500]}...

Generate 3 natural, helpful follow-up questions the user might want to ask next.
Make them specific to the lending context and genuinely useful.
Format as a simple list.
"""
        
        try:
            follow_up_result = await self.agent.run(follow_up_prompt)
            follow_up_text = str(follow_up_result.data) if hasattr(follow_up_result, 'data') else str(follow_up_result)
            
            # Parse the response into a list
            lines = [line.strip() for line in follow_up_text.split('\n') if line.strip()]
            # Remove numbering and bullet points
            suggestions = [line.lstrip('123456789.-• ') for line in lines if line][:3]
            
            return suggestions if suggestions else self._generate_follow_up_suggestions(original_query, synthesis)
            
        except Exception as e:
            logger.warning(f"Failed to generate follow-ups: {e}")
            return self._generate_follow_up_suggestions(original_query, synthesis)

    async def initialize_agents(self):
        """Initialize all specialist agents"""
        try:
            # ... existing agent initialization ...
            
            # Initialize Knowledge Ingestion Agent
            self.knowledge_agent = KnowledgeIngestionAgent(
                openai_client=self.openai_client,
                storage_service=self.storage_service,
                conversation_memory=self.conversation_memory
            )
            
            # Initialize RL Optimizer Agent
            self.rl_optimizer = RLOptimizerAgent(
                openai_client=self.openai_client,
                storage_service=self.storage_service,
                graph_intelligence=self.graph_intelligence,
                conversation_memory=self.conversation_memory
            )
            
            # Define available agents with routing keywords
            self.agents = {
                "loan_specialist": {
                    "agent": self.loan_specialist,
                    "keywords": ["loan", "amount", "eligibility", "income", "credit", "apply", "application", "borrow", "lending", "qualification"],
                    "priority": 1
                },
                "rate_advisor": {
                    "agent": self.rate_advisor,
                    "keywords": ["rate", "interest", "apr", "cost", "fee", "charge", "payment", "emi", "tenure", "calculator"],
                    "priority": 1
                },
                "document_helper": {
                    "agent": self.document_helper,
                    "keywords": ["document", "papers", "verification", "upload", "requirement", "kyc", "proof", "certificate", "statement"],
                    "priority": 2
                },
                "objection_handler": {
                    "agent": self.objection_handler,
                    "keywords": ["concern", "worry", "doubt", "problem", "issue", "risk", "afraid", "unsure", "hesitant", "question about"],
                    "priority": 2
                },
                "general_assistant": {
                    "agent": self.general_assistant,
                    "keywords": ["hello", "hi", "help", "support", "general", "other", "info", "about", "company", "service"],
                    "priority": 3
                },
                "knowledge_ingestion": {
                    "agent": self.knowledge_agent,
                    "keywords": ["learn", "knowledge", "training", "ingest", "document", "study", "analyze", "insight", "gap", "source"],
                    "priority": 4
                },
                "rl_optimizer": {
                    "agent": self.rl_optimizer, 
                    "keywords": ["optimize", "performance", "strategy", "outcome", "track", "analyze", "reward", "conversation", "rl", "reinforcement"],
                    "priority": 4
                }
            }
            
            logger.info(f"Initialized {len(self.agents)} specialist agents including RL Optimizer")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False


def create_orchestrator(openai_client, storage_service, graph_intelligence=None, conversation_memory=None) -> AgentOrchestrator:
    """Factory function to create the orchestrator with all dependencies"""
    return AgentOrchestrator(openai_client, storage_service, graph_intelligence, conversation_memory) 