"""
Neo4j MCP Conversation Memory Service
===================================

This service manages conversation history, user profiles, and context 
using Neo4j graph database through MCP (Model Context Protocol) servers.
It provides semantic graph storage for rich conversational AI memory.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
import json

# Import models from original service to maintain compatibility
from .conversation_memory import ConversationTurn, UserProfile, ConversationContext

logger = logging.getLogger(__name__)


class Neo4jMCPConversationMemoryService:
    """
    Conversation memory service using Neo4j graph database through MCP servers.
    
    This service leverages the mcp-neo4j-memory server to store conversation data
    as a knowledge graph, enabling semantic relationships and richer querying.
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.memory_dir = storage_dir / "conversation_memory"
        
        # Create directories for fallback storage
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Active contexts cache (in-memory for performance)
        self.active_contexts: Dict[str, ConversationContext] = {}
        
        # Configuration
        self.max_history_length = 20
        self.context_timeout = timedelta(hours=2)
        self.profile_update_threshold = 3
        
        # MCP error tracking - disable if we encounter syntax errors
        self.mcp_error_count = 0
        self.max_mcp_errors = 3  # Disable MCP after 3 syntax errors
        # Temporarily disable due to mcp-neo4j-memory package syntax error: SET e:$(entity.type)
        self.disable_graph_operations = True  # Will be set to False when package is fixed
        
        # Neo4j connection settings from environment
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_username = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
        self.neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        # Initialize MCP server connection
        self.mcp_server = None
        self.agent = None
        if not self.disable_graph_operations:
            self._initialize_mcp_connection()
        else:
            logger.info("Graph operations disabled due to mcp-neo4j-memory package syntax error")
            logger.info("Conversation memory still working with in-memory storage:")
            logger.info("  ✅ Session management and conversation history")
            logger.info("  ✅ User profile tracking and context")
            logger.info("  ✅ Selective memory for complex vs simple queries")
            logger.info("  ❌ Neo4j graph storage (will be re-enabled when package is fixed)")
        
        logger.info("Neo4j MCP Conversation Memory Service initialized")
    
    def _initialize_mcp_connection(self):
        """Initialize connection to Neo4j MCP memory server"""
        try:
            # Configure the Neo4j Memory MCP server with proper command
            self.mcp_server = MCPServerStdio(
                command="python",
                args=[
                    "-c", 
                    "import mcp_neo4j_memory; mcp_neo4j_memory.main()",
                    "--db-url", self.neo4j_uri,
                    "--username", self.neo4j_username,
                    "--password", self.neo4j_password,
                    "--database", self.neo4j_database
                ],
                env={
                    "NEO4J_URI": self.neo4j_uri,
                    "NEO4J_USERNAME": self.neo4j_username,
                    "NEO4J_PASSWORD": self.neo4j_password,
                    "NEO4J_DATABASE": self.neo4j_database,
                },
                tool_prefix="memory"
            )
            
            # Create PydanticAI agent with MCP server
            self.agent = Agent(
                model='openai:gpt-4o-mini',
                system_prompt="""
                You are a conversation memory assistant. You help manage user conversations,
                profiles, and context using a Neo4j knowledge graph. 
                
                When storing conversation data:
                - Create entities for users, sessions, and conversation topics
                - Create events for conversation turns with temporal information
                - Create relationships between users and their preferences
                - Store user profile data as attributes and propositions
                - Link conversation turns with causal relationships for context flow
                
                Always maintain privacy and only store what's necessary for conversation continuity.
                """,
                mcp_servers=[self.mcp_server]
            )
            
            logger.info("MCP connection to Neo4j memory server initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP connection: {e}")
            logger.warning("Falling back to in-memory storage")
            # Keep the agent as None to signal fallback mode
    
    async def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """Get existing conversation context or create a new one using Neo4j graph storage"""
        
        # Check active contexts first (in-memory cache)
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            # Check if context is still valid
            if datetime.now() - context.last_activity < self.context_timeout:
                return context
            else:
                # Context expired, remove from active cache
                del self.active_contexts[session_id]
        
        # Try to load from Neo4j via MCP
        context = await self._load_context_from_graph(session_id, user_id)
        
        if context is None:
            # Create new context
            user_profile = await self.get_or_create_user_profile(user_id or session_id, session_id)
            context = ConversationContext(
                session_id=session_id,
                user_profile=user_profile
            )
            
            await self._save_context_to_graph(context)
        
        self.active_contexts[session_id] = context
        return context
    
    async def get_or_create_user_profile(self, user_id: str, session_id: str) -> UserProfile:
        """Get existing user profile or create a new one using Neo4j graph storage"""
        
        # Try to load from Neo4j via MCP
        profile = await self._load_user_profile_from_graph(user_id)
        
        if profile is None:
            # Create new profile
            profile = UserProfile(
                user_id=user_id,
                session_id=session_id
            )
            
            await self._save_user_profile_to_graph(profile)
        
        return profile
    
    async def add_conversation_turn(
        self,
        session_id: str,
        user_query: str,
        system_response: str,
        agents_consulted: List[str] = None,
        tools_used: List[str] = None,
        reasoning_approach: str = None,
        user_context: Dict[str, Any] = None,
        confidence: float = 0.0,
        processing_time: float = 0.0
    ) -> ConversationContext:
        """Add a new conversation turn and update context in Neo4j graph"""
        
        context = await self.get_or_create_context(session_id)
        
        # Create conversation turn
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_query=user_query,
            system_response=system_response,
            agents_consulted=agents_consulted or [],
            tools_used=tools_used or [],
            reasoning_approach=reasoning_approach,
            user_context=user_context or {},
            confidence=confidence,
            processing_time=processing_time
        )
        
        # Add to conversation history
        context.conversation_history.append(turn)
        
        # Keep only recent history
        if len(context.conversation_history) > self.max_history_length:
            context.conversation_history = context.conversation_history[-self.max_history_length:]
        
        # Update context metadata
        context.last_activity = datetime.now()
        context.current_topic = self._extract_current_topic(turn, context.conversation_history[-5:])
        
        # Extract and update user context
        extracted_context = self.extract_user_context_from_query(user_query, session_id)
        if extracted_context:
            for key, value in extracted_context.items():
                turn.user_context[key] = value
        
        # Update user profile if needed
        if context.user_profile.total_interactions % self.profile_update_threshold == 0:
            self._update_user_profile_from_turn(context.user_profile, turn, extracted_context)
        
        context.user_profile.total_interactions += 1
        context.user_profile.last_updated = datetime.now()
        
        # Selective MCP storage - only store important conversations in graph
        if self._should_store_in_graph(user_query, system_response):
            logger.info(f"Storing important conversation turn in graph for session {session_id}")
            await self._store_conversation_turn_in_graph(context, turn)
            await self._save_context_to_graph(context)
            await self._save_user_profile_to_graph(context.user_profile)
        else:
            logger.debug(f"Skipping graph storage for simple interaction: {user_query[:20]}...")
        
        # Always update in-memory cache
        self.active_contexts[session_id] = context
        
        return context
    
    async def _load_context_from_graph(self, session_id: str, user_id: Optional[str] = None) -> Optional[ConversationContext]:
        """Load conversation context from Neo4j via MCP"""
        if not self.agent or self.disable_graph_operations:
            return None
        
        try:
            # Add timeout to prevent hanging
            timeout_task = asyncio.wait_for(
                self._try_load_context_from_mcp(session_id),
                timeout=10.0  # 10 second timeout
            )
            return await timeout_task
                
        except asyncio.TimeoutError:
            logger.warning(f"MCP context loading timed out for session {session_id}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load context from graph: {e}")
            return None
    
    async def _try_load_context_from_mcp(self, session_id: str) -> Optional[ConversationContext]:
        """Single attempt to load context from MCP"""
        async with self.agent.run_mcp_servers():
            # Simple query to check if session exists
            result = await self.agent.run(
                f"Check if session '{session_id}' exists in the memory graph. Return 'found' if it exists, 'not found' if it doesn't.",
                max_tokens=50  # Limit response size
            )
            
            # For now, always return None to create new context (avoid complex parsing)
            return None
    
    async def _load_user_profile_from_graph(self, user_id: str) -> Optional[UserProfile]:
        """Load user profile from Neo4j via MCP"""
        if not self.agent or self.disable_graph_operations:
            return None
        
        try:
            # Add timeout to prevent hanging
            timeout_task = asyncio.wait_for(
                self._try_load_profile_from_mcp(user_id),
                timeout=10.0  # 10 second timeout
            )
            return await timeout_task
                
        except asyncio.TimeoutError:
            logger.warning(f"MCP profile loading timed out for user {user_id}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load user profile from graph: {e}")
            return None
    
    async def _try_load_profile_from_mcp(self, user_id: str) -> Optional[UserProfile]:
        """Single attempt to load profile from MCP"""
        async with self.agent.run_mcp_servers():
            # Simple query to check if user exists
            result = await self.agent.run(
                f"Check if user '{user_id}' exists in the memory graph. Return 'found' if they exist, 'not found' if they don't.",
                max_tokens=50  # Limit response size
            )
            
            # For now, always return None to create new profile (avoid complex parsing)
            return None
    
    async def _save_context_to_graph(self, context: ConversationContext):
        """Save conversation context to Neo4j via MCP"""
        if not self.agent or self.disable_graph_operations:
            return
        
        try:
            async with self.agent.run_mcp_servers():
                # Store session entity and context data with simplified approach
                await self.agent.run(
                    f"""Store a conversation session with ID '{context.session_id}':
                    - Session started: {context.started_at}
                    - Last activity: {context.last_activity}
                    - Current topic: {context.current_topic}
                    - Total turns: {len(context.conversation_history)}
                    
                    Create a Session node and store this information as properties."""
                )
                
        except Exception as e:
            if not self._handle_mcp_error(e):
                return  # MCP operations disabled due to errors
            logger.warning(f"Failed to save context to graph (falling back to memory): {e}")
    
    async def _save_user_profile_to_graph(self, profile: UserProfile):
        """Save user profile to Neo4j via MCP"""
        if not self.agent or self.disable_graph_operations:
            return
        
        try:
            async with self.agent.run_mcp_servers():
                # Store user profile with simplified approach
                await self.agent.run(
                    f"""Store a user profile for user '{profile.user_id}':
                    - Monthly income: {profile.monthly_income}
                    - Age: {profile.age}
                    - Employment: {profile.employment_type}
                    - Total interactions: {profile.total_interactions}
                    
                    Create a Person node and store this profile information."""
                )
                
        except Exception as e:
            if not self._handle_mcp_error(e):
                return  # MCP operations disabled due to errors
            logger.warning(f"Failed to save user profile to graph (falling back to memory): {e}")
    
    async def _store_conversation_turn_in_graph(self, context: ConversationContext, turn: ConversationTurn):
        """Store individual conversation turn in Neo4j via MCP"""
        if not self.agent or self.disable_graph_operations:
            return
        
        try:
            async with self.agent.run_mcp_servers():
                # Store conversation turn with simplified approach to avoid syntax errors
                await self.agent.run(
                    f"""Store a conversation turn for session '{context.session_id}':
                    User said: "{turn.user_query}"
                    System replied: "{turn.system_response}"
                    At time: {turn.timestamp}
                    
                    Create a ConversationTurn node and link it to the session."""
                )
                
        except Exception as e:
            if not self._handle_mcp_error(e):
                return  # MCP operations disabled due to errors
            logger.warning(f"Failed to store conversation turn in graph (falling back to memory): {e}")
    
    async def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a session"""
        return await self.get_or_create_context(session_id)
    
    async def get_contextual_prompt_addition(self, session_id: str, current_query: str = "") -> str:
        """Get contextual information to add to prompts"""
        try:
            context = await self.get_conversation_context(session_id)
            if not context:
                return ""
            
            # Only use MCP for complex queries that would benefit from graph context
            if self._should_use_mcp_for_query(current_query, context):
                logger.info(f"Using MCP for contextual enhancement: {current_query[:30]}...")
                if self.agent:
                    try:
                        async with self.agent.run_mcp_servers():
                            result = await self.agent.run(
                                f"""Provide contextual information for session '{session_id}' to enhance AI responses:
                                
                                Current query: "{current_query}"
                                
                                Based on the conversation history and user profile in the graph:
                                1. What does the AI know about this user?
                                2. What are the user's key preferences and goals?
                                3. What topics have been discussed recently?
                                4. What context should inform the next response?
                                
                                Provide a concise contextual summary for the AI assistant.""",
                                max_tokens=200  # Limit response size
                            )
                            
                            return f"Context: {result.output}"
                            
                    except Exception as e:
                        if not self._handle_mcp_error(e):
                            logger.info("MCP operations disabled, using basic context")
                        else:
                            logger.warning(f"Failed to get MCP context: {e}")
            else:
                logger.debug(f"Using basic context for simple query: {current_query[:30]}...")
            
            # Fallback to basic context building
            return self._build_basic_context(context)
            
        except Exception as e:
            logger.error(f"Error getting contextual prompt addition: {e}")
            return ""
    
    def _build_basic_context(self, context: ConversationContext) -> str:
        """Build basic context without MCP (fallback method)"""
        parts = []
        
        profile = context.user_profile
        
        # User profile context
        if profile.monthly_income:
            parts.append(f"User has monthly income of ₹{profile.monthly_income:,}")
        
        if profile.loan_purposes:
            parts.append(f"User is interested in loans for: {', '.join(profile.loan_purposes)}")
        
        if profile.employment_type:
            parts.append(f"Employment type: {profile.employment_type}")
        
        if profile.communication_style:
            parts.append(f"Preferred communication style: {profile.communication_style}")
        
        # Recent conversation context
        if context.current_topic:
            parts.append(f"Current topic: {context.current_topic}")
        
        if context.conversation_history:
            recent_queries = [turn.user_query for turn in context.conversation_history[-3:]]
            parts.append(f"Recent queries: {'; '.join(recent_queries)}")
        
        return " | ".join(parts) if parts else ""
    
    # Implement other methods from original service for compatibility
    def extract_user_context_from_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """Extract user context from query (placeholder implementation)"""
        # This could be enhanced with MCP-based NLP analysis
        context = {}
        
        # Basic keyword extraction for financial terms
        financial_keywords = {
            'income': ['income', 'salary', 'earn', 'monthly income'],
            'loan_amount': ['loan', 'amount', 'borrow', 'need'],
            'employment': ['job', 'work', 'employed', 'business', 'self-employed']
        }
        
        query_lower = query.lower()
        for category, keywords in financial_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    context[f'mentioned_{category}'] = True
                    break
        
        return context
    
    def _extract_current_topic(self, current_turn: ConversationTurn, recent_turns: List[ConversationTurn]) -> str:
        """Extract current conversation topic"""
        # Simple topic extraction based on query content
        query = current_turn.user_query.lower()
        
        if any(word in query for word in ['loan', 'borrow', 'credit', 'emi']):
            return 'loan_inquiry'
        elif any(word in query for word in ['income', 'salary', 'earn']):
            return 'income_discussion'
        elif any(word in query for word in ['investment', 'save', 'savings']):
            return 'investment_planning'
        else:
            return 'general_inquiry'
    
    def _update_user_profile_from_turn(
        self, 
        profile: UserProfile, 
        turn: ConversationTurn, 
        user_context: Dict[str, Any]
    ):
        """Update user profile based on conversation turn"""
        # Update frequently asked topics
        topic = self._extract_current_topic(turn, [])
        if topic not in profile.frequently_asked_topics:
            profile.frequently_asked_topics.append(topic)
        
        # Update preferred agents
        for agent in turn.agents_consulted:
            if agent not in profile.preferred_agents:
                profile.preferred_agents.append(agent)
        
        # Update interaction patterns
        if 'interaction_time' not in profile.interaction_patterns:
            profile.interaction_patterns['interaction_time'] = []
        
        profile.interaction_patterns['interaction_time'].append(
            turn.timestamp.hour
        )
        
        # Keep only recent interaction times (last 10)
        if len(profile.interaction_patterns['interaction_time']) > 10:
            profile.interaction_patterns['interaction_time'] = \
                profile.interaction_patterns['interaction_time'][-10:]
    
    async def cleanup_expired_contexts(self):
        """Clean up expired contexts from memory and storage"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            if current_time - context.last_activity > self.context_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_contexts[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired contexts")
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user insights and analytics"""
        if self.agent:
            try:
                async with self.agent.run_mcp_servers():
                    result = await self.agent.run(
                        f"""Analyze user '{user_id}' data in the graph and provide insights:
                        1. Communication patterns and preferences
                        2. Most frequently discussed topics
                        3. Loan and financial interests
                        4. Interaction behavior and timing
                        5. Profile completeness and data quality
                        
                        Return a comprehensive user analysis."""
                    )
                    
                    return {
                        'analysis': result.output,
                        'generated_at': datetime.now(),
                        'source': 'neo4j_mcp_analysis'
                    }
                    
            except Exception as e:
                logger.error(f"Failed to get MCP insights: {e}")
        
        # Fallback to basic insights
        try:
            profile = await self.get_or_create_user_profile(user_id, user_id)
            return {
                'total_interactions': profile.total_interactions,
                'frequently_asked_topics': profile.frequently_asked_topics,
                'profile_completeness': self._calculate_profile_completeness(profile),
                'last_updated': profile.last_updated,
                'communication_style': profile.communication_style,
                'source': 'basic_profile_analysis'
            }
        except Exception as e:
            logger.error(f"Failed to get user insights: {e}")
            return {}
    
    def _calculate_profile_completeness(self, profile: UserProfile) -> float:
        """Calculate how complete a user profile is"""
        total_fields = 15  # Total number of profile fields
        filled_fields = 0
        
        # Count filled fields
        if profile.monthly_income is not None: filled_fields += 1
        if profile.age is not None: filled_fields += 1
        if profile.employment_type is not None: filled_fields += 1
        if profile.credit_score is not None: filled_fields += 1
        if profile.monthly_expenses is not None: filled_fields += 1
        if profile.savings_amount is not None: filled_fields += 1
        if profile.loan_purposes: filled_fields += 1
        if profile.preferred_tenure is not None: filled_fields += 1
        if profile.max_emi_capacity is not None: filled_fields += 1
        if profile.risk_tolerance is not None: filled_fields += 1
        if profile.communication_style is not None: filled_fields += 1
        if profile.frequently_asked_topics: filled_fields += 1
        if profile.preferred_agents: filled_fields += 1
        if profile.interaction_patterns: filled_fields += 1
        if profile.existing_loans: filled_fields += 1
        
        return filled_fields / total_fields 
    
    def _should_use_mcp_for_query(self, query: str, context: Optional[ConversationContext] = None) -> bool:
        """Determine if MCP should be used based on query complexity and context"""
        if self.disable_graph_operations or not self.agent:
            return False
        
        query_lower = query.lower().strip()
        
        # Don't use MCP for simple greetings and basic responses
        simple_patterns = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'ok', 'okay', 'yes', 'no'
        ]
        
        if any(pattern in query_lower for pattern in simple_patterns) and len(query_lower) < 20:
            return False
        
        # Use MCP for complex queries that would benefit from graph context
        complex_patterns = [
            'remember', 'previous', 'before', 'earlier', 'history', 'last time',
            'profile', 'preference', 'similar', 'related', 'connection', 'relationship',
            'analyze', 'insight', 'pattern', 'recommend', 'suggest based on'
        ]
        
        if any(pattern in query_lower for pattern in complex_patterns):
            return True
        
        # Use MCP if user has significant conversation history (more than 3 interactions)
        if context and len(context.conversation_history) > 3:
            return True
        
        # Use MCP for queries longer than 50 characters (likely complex)
        if len(query) > 50:
            return True
        
        # Default: don't use MCP for simple queries
        return False
    
    def _should_store_in_graph(self, user_query: str, system_response: str) -> bool:
        """Determine if this conversation turn should be stored in the graph"""
        if self.disable_graph_operations or not self.agent:
            return False
        
        # Don't store simple greetings
        simple_query = user_query.lower().strip()
        if any(pattern in simple_query for pattern in ['hi', 'hello', 'hey', 'thanks', 'bye']) and len(simple_query) < 20:
            return False
        
        # Store if the response contains valuable information
        response_lower = system_response.lower()
        valuable_patterns = [
            'loan', 'credit', 'financial', 'income', 'profile', 'eligibility',
            'rate', 'emi', 'tenure', 'amount', 'application', 'document'
        ]
        
        if any(pattern in response_lower for pattern in valuable_patterns):
            return True
        
        # Store if query is substantial (more than 30 characters)
        if len(user_query) > 30:
            return True
        
        return False 

    def _handle_mcp_error(self, error: Exception) -> bool:
        """Handle MCP errors and disable operations if needed. Returns True if operations should continue."""
        error_str = str(error).lower()
        
        # Check for Neo4j syntax errors
        if "syntax error" in error_str or "dynamic" in error_str or "set e:" in error_str:
            self.mcp_error_count += 1
            logger.warning(f"Neo4j syntax error detected in MCP ({self.mcp_error_count}/{self.max_mcp_errors}): {error}")
            
            if self.mcp_error_count >= self.max_mcp_errors:
                self.disable_graph_operations = True
                logger.error(f"Too many MCP syntax errors ({self.mcp_error_count}). Disabling graph operations permanently for this session.")
                logger.info("Conversation memory will continue working with in-memory storage only.")
                return False
        else:
            # For other errors, just log and continue
            logger.warning(f"MCP operation failed: {error}")
        
        return not self.disable_graph_operations 

    def enable_mcp_operations(self):
        """Re-enable MCP operations when the mcp-neo4j-memory package is fixed"""
        logger.info("Re-enabling MCP graph operations...")
        self.disable_graph_operations = False
        self.mcp_error_count = 0
        
        if not self.agent:
            self._initialize_mcp_connection()
        
        if self.agent:
            logger.info("✅ MCP operations re-enabled successfully")
        else:
            logger.warning("❌ Failed to re-enable MCP operations")
            self.disable_graph_operations = True 