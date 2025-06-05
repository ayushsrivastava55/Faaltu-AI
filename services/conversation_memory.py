"""
Conversation Memory Service - Persistent Context & User Memory
=============================================================

This service manages conversation history, user profiles, and context 
across multiple exchanges, enabling the agentic system to maintain
state and provide personalized, contextually-aware interactions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class ConversationTurn(BaseModel):
    """Represents a single turn in a conversation"""
    timestamp: datetime
    user_query: str
    system_response: str
    agents_consulted: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    reasoning_approach: Optional[str] = None
    user_context: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    processing_time: float = 0.0


class UserProfile(BaseModel):
    """Comprehensive user profile with learned preferences"""
    user_id: str
    session_id: str
    
    # Financial Profile
    monthly_income: Optional[int] = None
    age: Optional[int] = None
    employment_type: Optional[str] = None  # salaried, self_employed, business
    credit_score: Optional[int] = None
    existing_loans: List[Dict[str, Any]] = Field(default_factory=list)
    monthly_expenses: Optional[int] = None
    savings_amount: Optional[int] = None
    
    # Preferences & Goals
    loan_purposes: List[str] = Field(default_factory=list)
    preferred_tenure: Optional[int] = None
    max_emi_capacity: Optional[int] = None
    risk_tolerance: Optional[str] = None  # conservative, moderate, aggressive
    communication_style: Optional[str] = None  # detailed, concise, technical
    
    # Learning Data
    frequently_asked_topics: List[str] = Field(default_factory=list)
    preferred_agents: List[str] = Field(default_factory=list)
    interaction_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    total_interactions: int = 0


class ConversationContext(BaseModel):
    """Active conversation context with memory"""
    session_id: str
    user_profile: UserProfile
    conversation_history: List[ConversationTurn] = Field(default_factory=list)
    current_topic: Optional[str] = None
    active_goals: List[str] = Field(default_factory=list)
    context_summary: Optional[str] = None
    last_agent_used: Optional[str] = None
    pending_actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Session metadata
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_voice_session: bool = False


class ConversationMemoryService:
    """
    Service that manages conversation memory, user profiles, and context
    across multiple interactions to enable truly conversational AI.
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.memory_dir = storage_dir / "conversation_memory"
        self.profiles_dir = self.memory_dir / "profiles"
        self.sessions_dir = self.memory_dir / "sessions"
        self.contexts_dir = self.memory_dir / "contexts"
        
        # Create directories
        for directory in [self.memory_dir, self.profiles_dir, self.sessions_dir, self.contexts_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Active contexts cache (in-memory for performance)
        self.active_contexts: Dict[str, ConversationContext] = {}
        
        # Configuration
        self.max_history_length = 20  # Keep last 20 turns
        self.context_timeout = timedelta(hours=2)  # Context expires after 2 hours
        self.profile_update_threshold = 3  # Update profile every 3 interactions
        
        logger.info("Conversation Memory Service initialized")
    
    def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """Get existing conversation context or create a new one"""
        
        # Check active contexts first (in-memory cache)
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            # Check if context is still valid
            if datetime.now() - context.last_activity < self.context_timeout:
                return context
            else:
                # Context expired, remove from active cache
                del self.active_contexts[session_id]
        
        # Try to load from disk
        context_file = self.contexts_dir / f"{session_id}.json"
        if context_file.exists():
            try:
                data = json.loads(context_file.read_text())
                context = ConversationContext(**data)
                
                # Check if still valid
                if datetime.now() - context.last_activity < self.context_timeout:
                    self.active_contexts[session_id] = context
                    return context
            except Exception as e:
                logger.warning(f"Failed to load context for session {session_id}: {e}")
        
        # Create new context
        user_profile = self.get_or_create_user_profile(user_id or session_id, session_id)
        context = ConversationContext(
            session_id=session_id,
            user_profile=user_profile
        )
        
        self.active_contexts[session_id] = context
        self._save_context(context)
        
        return context
    
    def get_or_create_user_profile(self, user_id: str, session_id: str) -> UserProfile:
        """Get existing user profile or create a new one"""
        profile_file = self.profiles_dir / f"{user_id}.json"
        
        if profile_file.exists():
            try:
                data = json.loads(profile_file.read_text())
                profile = UserProfile(**data)
                profile.last_updated = datetime.now()
                return profile
            except Exception as e:
                logger.warning(f"Failed to load profile for user {user_id}: {e}")
        
        # Create new profile
        profile = UserProfile(
            user_id=user_id,
            session_id=session_id
        )
        
        self._save_user_profile(profile)
        return profile
    
    def add_conversation_turn(
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
        """Add a new conversation turn and update context"""
        
        context = self.get_or_create_context(session_id)
        
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
        
        # Maintain history length limit
        if len(context.conversation_history) > self.max_history_length:
            context.conversation_history = context.conversation_history[-self.max_history_length:]
        
        # Update context metadata
        context.last_activity = datetime.now()
        context.last_agent_used = agents_consulted[0] if agents_consulted else None
        
        # Update user profile with new information
        self._update_user_profile_from_turn(context.user_profile, turn, user_context or {})
        
        # Analyze and update current topic
        context.current_topic = self._extract_current_topic(turn, context.conversation_history[-3:])
        
        # Update context summary
        context.context_summary = self._generate_context_summary(context.conversation_history[-5:])
        
        # Save updates
        self._save_context(context)
        self._save_user_profile(context.user_profile)
        
        return context
    
    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for analysis by agents"""
        return self.active_contexts.get(session_id) or self.get_or_create_context(session_id)
    
    def get_contextual_prompt_addition(self, session_id: str, current_query: str = "") -> str:
        """Generate contextual prompt addition for agents based on conversation history"""
        context = self.get_conversation_context(session_id)
        if not context or not context.conversation_history:
            return ""
        
        prompt_parts = []
        
        # Add user profile context
        profile = context.user_profile
        if any([profile.monthly_income, profile.employment_type, profile.credit_score]):
            profile_info = []
            if profile.monthly_income:
                profile_info.append(f"monthly income: ₹{profile.monthly_income:,}")
            if profile.employment_type:
                profile_info.append(f"employment: {profile.employment_type}")
            if profile.credit_score:
                profile_info.append(f"credit score: {profile.credit_score}")
            
            prompt_parts.append(f"User Profile: {', '.join(profile_info)}")
        
        # Add recent conversation context
        if len(context.conversation_history) > 1:
            recent_context = []
            for turn in context.conversation_history[-3:]:  # Last 3 turns
                recent_context.append(f"User: {turn.user_query}")
                recent_context.append(f"Assistant: {turn.system_response[:200]}...")
            
            prompt_parts.append(f"Recent Conversation:\n{chr(10).join(recent_context)}")
        
        # Add current topic and goals
        if context.current_topic:
            prompt_parts.append(f"Current Topic: {context.current_topic}")
        
        if context.active_goals:
            prompt_parts.append(f"Active Goals: {', '.join(context.active_goals)}")
        
        # Add pending actions
        if context.pending_actions:
            actions = [action.get("description", str(action)) for action in context.pending_actions]
            prompt_parts.append(f"Pending Actions: {', '.join(actions)}")
        
        if prompt_parts:
            return f"""
Previous Context:
{chr(10).join(prompt_parts)}

Based on this context, provide a personalized response that acknowledges previous conversation and user profile."""
        
        return ""
    
    def extract_user_context_from_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """Extract user context information from query and conversation history"""
        context = self.get_conversation_context(session_id)
        if not context:
            return {}
        
        user_context = {
            "session_id": session_id,
            "conversation_turns": len(context.conversation_history),
            "current_topic": context.current_topic,
            "last_agent_used": context.last_agent_used
        }
        
        # Add user profile information
        profile = context.user_profile
        if profile.monthly_income:
            user_context["income"] = profile.monthly_income
        if profile.employment_type:
            user_context["employment_type"] = profile.employment_type
        if profile.credit_score:
            user_context["credit_score"] = profile.credit_score
        if profile.max_emi_capacity:
            user_context["max_emi_capacity"] = profile.max_emi_capacity
        
        # Extract new information from current query
        query_lower = query.lower()
        
        # Income extraction
        income_keywords = ["salary", "earn", "income", "per month", "monthly"]
        if any(keyword in query_lower for keyword in income_keywords):
            # Try to extract numbers (simplified extraction)
            import re
            numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d{2})?', query)
            if numbers:
                # Take the largest number as likely income
                amount = max([float(n.replace(',', '')) for n in numbers])
                if 10000 <= amount <= 10000000:  # Reasonable income range
                    user_context["income"] = int(amount)
        
        # Employment type extraction
        if any(word in query_lower for word in ["self employed", "business", "entrepreneur"]):
            user_context["employment_type"] = "self_employed"
        elif any(word in query_lower for word in ["salaried", "employee", "job", "company"]):
            user_context["employment_type"] = "salaried"
        
        # Loan purpose extraction
        purposes = {
            "personal": ["personal", "emergency", "medical", "travel", "wedding"],
            "business": ["business", "shop", "startup", "equipment", "inventory"],
            "education": ["education", "study", "course", "fees", "college"],
            "home": ["home", "house", "renovation", "improvement"],
            "debt": ["debt", "consolidation", "EMI", "existing loan"]
        }
        
        for purpose, keywords in purposes.items():
            if any(keyword in query_lower for keyword in keywords):
                user_context["loan_purpose"] = purpose
                break
        
        return user_context
    
    def _update_user_profile_from_turn(
        self, 
        profile: UserProfile, 
        turn: ConversationTurn, 
        user_context: Dict[str, Any]
    ):
        """Update user profile based on conversation turn and extracted context"""
        
        # Update interaction count
        profile.total_interactions += 1
        profile.last_updated = datetime.now()
        
        # Update financial information if provided
        if "income" in user_context:
            profile.monthly_income = user_context["income"]
        if "employment_type" in user_context:
            profile.employment_type = user_context["employment_type"]
        if "credit_score" in user_context:
            profile.credit_score = user_context["credit_score"]
        if "max_emi_capacity" in user_context:
            profile.max_emi_capacity = user_context["max_emi_capacity"]
        
        # Track loan purposes
        if "loan_purpose" in user_context:
            purpose = user_context["loan_purpose"]
            if purpose not in profile.loan_purposes:
                profile.loan_purposes.append(purpose)
        
        # Track frequently asked topics
        topic = self._extract_topic_from_query(turn.user_query)
        if topic:
            if topic in profile.frequently_asked_topics:
                # Move to front (most recent)
                profile.frequently_asked_topics.remove(topic)
            profile.frequently_asked_topics.insert(0, topic)
            # Keep only top 10 topics
            profile.frequently_asked_topics = profile.frequently_asked_topics[:10]
        
        # Track preferred agents
        for agent in turn.agents_consulted:
            if agent not in profile.preferred_agents:
                profile.preferred_agents.append(agent)
        
        # Update interaction patterns
        hour = turn.timestamp.hour
        day_of_week = turn.timestamp.strftime("%A")
        
        patterns = profile.interaction_patterns
        patterns["total_interactions"] = patterns.get("total_interactions", 0) + 1
        patterns["hours"] = patterns.get("hours", {})
        patterns["hours"][str(hour)] = patterns["hours"].get(str(hour), 0) + 1
        patterns["days"] = patterns.get("days", {})
        patterns["days"][day_of_week] = patterns["days"].get(day_of_week, 0) + 1
        
        # Communication style detection
        if turn.confidence > 0.8 and turn.processing_time < 2.0:
            if len(turn.user_query.split()) < 10:
                profile.communication_style = "concise"
            elif any(word in turn.user_query.lower() for word in ["technical", "algorithm", "analysis", "details"]):
                profile.communication_style = "technical"
            else:
                profile.communication_style = "detailed"
    
    def _extract_current_topic(self, current_turn: ConversationTurn, recent_turns: List[ConversationTurn]) -> str:
        """Extract the current topic from conversation"""
        # Simple topic extraction (can be enhanced with NLP)
        query = current_turn.user_query.lower()
        
        topics = {
            "loan_application": ["apply", "application", "process", "documents"],
            "loan_rates": ["rate", "interest", "APR", "percentage"],
            "loan_eligibility": ["eligible", "qualify", "requirements", "criteria"],
            "loan_comparison": ["compare", "best", "options", "which loan"],
            "emi_calculation": ["EMI", "monthly payment", "calculate", "amount"],
            "market_research": ["market", "trends", "competitors", "research"],
            "documentation": ["documents", "papers", "verification", "upload"]
        }
        
        for topic, keywords in topics.items():
            if any(keyword in query for keyword in keywords):
                return topic
        
        return "general_inquiry"
    
    def _extract_topic_from_query(self, query: str) -> Optional[str]:
        """Extract topic from a single query"""
        return self._extract_current_topic(
            ConversationTurn(
                timestamp=datetime.now(),
                user_query=query,
                system_response=""
            ), 
            []
        )
    
    def _generate_context_summary(self, recent_turns: List[ConversationTurn]) -> str:
        """Generate a summary of recent conversation context"""
        if not recent_turns:
            return "New conversation"
        
        if len(recent_turns) == 1:
            return f"User asked about: {recent_turns[0].user_query[:100]}..."
        
        topics = [self._extract_topic_from_query(turn.user_query) for turn in recent_turns]
        unique_topics = list(set([t for t in topics if t and t != "general_inquiry"]))
        
        if unique_topics:
            return f"Discussion topics: {', '.join(unique_topics)}"
        else:
            return f"General conversation with {len(recent_turns)} exchanges"
    
    def _save_context(self, context: ConversationContext):
        """Save conversation context to disk"""
        try:
            context_file = self.contexts_dir / f"{context.session_id}.json"
            # Convert to dict for JSON serialization
            context_dict = context.model_dump()
            context_file.write_text(json.dumps(context_dict, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save context for session {context.session_id}: {e}")
    
    def _save_user_profile(self, profile: UserProfile):
        """Save user profile to disk"""
        try:
            profile_file = self.profiles_dir / f"{profile.user_id}.json"
            # Convert to dict for JSON serialization
            profile_dict = profile.model_dump()
            profile_file.write_text(json.dumps(profile_dict, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save profile for user {profile.user_id}: {e}")
    
    def cleanup_expired_contexts(self):
        """Clean up expired contexts to free memory"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            if current_time - context.last_activity > self.context_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_contexts[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired conversation contexts")
    
    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about a user for personalization"""
        profile_file = self.profiles_dir / f"{user_id}.json"
        if not profile_file.exists():
            return {}
        
        try:
            data = json.loads(profile_file.read_text())
            profile = UserProfile(**data)
            
            return {
                "total_interactions": profile.total_interactions,
                "frequently_asked_topics": profile.frequently_asked_topics[:5],
                "preferred_agents": profile.preferred_agents,
                "communication_style": profile.communication_style,
                "financial_profile_completeness": self._calculate_profile_completeness(profile),
                "interaction_patterns": profile.interaction_patterns
            }
        except Exception as e:
            logger.error(f"Failed to get insights for user {user_id}: {e}")
            return {}
    
    def _calculate_profile_completeness(self, profile: UserProfile) -> float:
        """Calculate how complete the user's financial profile is"""
        fields = [
            profile.monthly_income,
            profile.employment_type,
            profile.credit_score,
            profile.max_emi_capacity,
            profile.age
        ]
        
        completed = sum(1 for field in fields if field is not None)
        return (completed / len(fields)) * 100 