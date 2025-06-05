"""
Reinforcement Learning Optimizer - Outcome-Based Learning Agent
==============================================================

This agent transforms our knowledge-based system into an outcome-optimized
learning system that continuously improves conversion rates through
reinforcement learning from real conversation outcomes.
"""

import json
import logging
import asyncio
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import hashlib

import numpy as np
from pydantic import BaseModel, Field

from .base import BaseAgent, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class ConversationOutcome(BaseModel):
    """Represents the outcome of a conversation for RL learning"""
    session_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Reward signals
    conversion: bool = False  # Did customer apply for loan?
    qualification: bool = False  # Did customer provide complete info?
    satisfaction_score: float = 0.0  # 1-5 rating if available
    engagement_score: float = 0.0  # Calculated from interaction patterns
    
    # Conversation metrics
    total_messages: int = 0
    customer_messages: int = 0
    ai_messages: int = 0
    objections_raised: int = 0
    objections_resolved: int = 0
    information_requests: int = 0
    clarifications_needed: int = 0
    
    # Strategy used
    agents_used: List[str] = Field(default_factory=list)
    primary_strategy: str = "default"
    response_tone: str = "professional"
    conversation_flow: str = "linear"
    
    # Context
    customer_profile: Dict[str, Any] = Field(default_factory=dict)
    query_type: str = "general"
    complexity_level: str = "simple"  # simple, medium, complex
    
    # Calculated reward
    total_reward: float = 0.0


class StrategyPerformance(BaseModel):
    """Tracks performance of different conversation strategies"""
    strategy_name: str
    total_uses: int = 0
    total_reward: float = 0.0
    average_reward: float = 0.0
    conversion_rate: float = 0.0
    success_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Context-specific performance
    performance_by_context: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class ConversationState(BaseModel):
    """Represents the current state of a conversation for RL decision making"""
    session_id: str
    message_count: int = 0
    customer_profile: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_intent: str = "unknown"
    detected_objections: List[str] = Field(default_factory=list)
    information_gathered: Dict[str, Any] = Field(default_factory=dict)
    sentiment_trend: List[float] = Field(default_factory=list)  # Last 5 message sentiments
    engagement_level: float = 0.5  # 0-1 scale


class RLOptimizerAgent(BaseAgent):
    """
    Reinforcement Learning Optimizer that learns optimal conversation strategies
    from real outcomes and continuously improves the AI's sales effectiveness.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are the Reinforcement Learning Optimizer for LendenClub's AI sales assistant.

Your mission is to continuously optimize conversation strategies based on real outcomes to maximize:
1. Conversion rates (loan applications)
2. Customer satisfaction scores
3. Engagement and qualification rates
4. Overall business outcomes

Core Capabilities:
1. **Outcome Tracking**: Monitor conversation results and calculate reward signals
2. **Strategy Testing**: A/B test different conversation approaches
3. **Performance Analysis**: Identify what works for different customer types
4. **Real-time Optimization**: Adapt strategies based on ongoing results
5. **Pattern Recognition**: Discover successful conversation patterns

Learning Signals:
- Conversion success (+100 points)
- Customer qualification (+50 points)
- High satisfaction (+30 points)
- Objection resolution (+40 points)
- Engagement improvement (+20 points)
- Dropout prevention (+25 points)

Strategy Dimensions:
- Agent selection and routing
- Response tone and style
- Information sequencing
- Conversation flow control
- Objection handling approach

Your goal is to transform the AI from a knowledge-retrieval system into a sales-optimized conversation engine that learns and improves from every interaction."""

        super().__init__(
            name="RL Optimizer Agent",
            description="Optimizes conversation strategies through reinforcement learning from real outcomes",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
        
        # Initialize RL infrastructure
        self.rl_dir = Path(storage_service.DATA_DIR) / "reinforcement_learning"
        self.outcomes_dir = self.rl_dir / "outcomes"
        self.strategies_dir = self.rl_dir / "strategies"
        self.experiments_dir = self.rl_dir / "experiments"
        
        # Create directories
        for directory in [self.rl_dir, self.outcomes_dir, self.strategies_dir, self.experiments_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # RL State
        self.conversation_outcomes: Dict[str, ConversationOutcome] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self.active_conversations: Dict[str, ConversationState] = {}
        
        # Strategy configuration
        self.available_strategies = [
            "consultative_approach",
            "direct_sales",
            "educational_first", 
            "benefit_focused",
            "problem_solving",
            "trust_building",
            "urgency_creating"
        ]
        
        self.response_tones = [
            "professional",
            "friendly", 
            "consultative",
            "authoritative",
            "empathetic"
        ]
        
        self.conversation_flows = [
            "linear",
            "adaptive",
            "discovery_first",
            "solution_focused"
        ]
        
        # Multi-armed bandit parameters
        self.epsilon = 0.15  # Exploration rate
        self.min_data_points = 10  # Minimum data before exploitation
        
        # Load existing data
        self._load_rl_data()
        
        logger.info("RL Optimizer Agent initialized")
    
    def _register_tools(self):
        """Register RL optimization tools"""
        self.tools = [
            "outcome_tracking",
            "strategy_selection",
            "performance_analysis",
            "reward_calculation",
            "pattern_recognition",
            "experiment_management"
        ]
    
    def _get_tools_used(self) -> List[str]:
        """Get list of tools used by this agent"""
        return getattr(self, 'tools', [])
    
    def _load_rl_data(self):
        """Load existing RL data from storage"""
        try:
            # Load conversation outcomes
            outcomes_file = self.outcomes_dir / "outcomes.json"
            if outcomes_file.exists():
                data = json.loads(outcomes_file.read_text())
                for outcome_data in data.get("outcomes", []):
                    outcome = ConversationOutcome(**outcome_data)
                    self.conversation_outcomes[outcome.session_id] = outcome
            
            # Load strategy performance
            strategies_file = self.strategies_dir / "performance.json"
            if strategies_file.exists():
                data = json.loads(strategies_file.read_text())
                for strategy_data in data.get("strategies", []):
                    strategy = StrategyPerformance(**strategy_data)
                    self.strategy_performance[strategy.strategy_name] = strategy
            
            # Initialize missing strategies
            for strategy in self.available_strategies:
                if strategy not in self.strategy_performance:
                    self.strategy_performance[strategy] = StrategyPerformance(strategy_name=strategy)
            
            logger.info(f"Loaded {len(self.conversation_outcomes)} outcomes and {len(self.strategy_performance)} strategies")
            
        except Exception as e:
            logger.error(f"Failed to load RL data: {e}")
    
    async def process_query(self, request: AgentRequest) -> AgentResponse:
        """Process RL optimization requests"""
        start_time = datetime.now()
        
        try:
            # Determine operation type
            query = request.query.lower()
            
            if "track outcome" in query or "conversation ended" in query:
                return await self._handle_outcome_tracking(request, start_time)
            elif "select strategy" in query or "optimize conversation" in query:
                return await self._handle_strategy_selection(request, start_time)
            elif "analyze performance" in query or "show results" in query:
                return await self._handle_performance_analysis(request, start_time)
            elif "start conversation" in query or "initialize session" in query:
                return await self._handle_conversation_start(request, start_time)
            elif "update state" in query or "conversation update" in query:
                return await self._handle_state_update(request, start_time)
            else:
                return await self._handle_general_rl_query(request, start_time)
                
        except Exception as e:
            logger.error(f"Error in RL optimizer: {e}")
            return await self._create_error_response(request, str(e), start_time)
    
    async def _handle_conversation_start(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Initialize a new conversation for RL tracking"""
        session_id = request.session_id or f"rl_session_{int(start_time.timestamp())}"
        
        # Extract customer context from request
        customer_profile = request.user_context or {}
        
        # Create conversation state
        conversation_state = ConversationState(
            session_id=session_id,
            customer_profile=customer_profile,
            current_intent=self._detect_intent(request.query),
        )
        
        self.active_conversations[session_id] = conversation_state
        
        # Select optimal strategy for this customer context
        selected_strategy = self._select_strategy(conversation_state)
        
        response_text = f"""Conversation tracking initialized for session: {session_id}

**Recommended Strategy**: {selected_strategy['primary_strategy']}
**Response Tone**: {selected_strategy['response_tone']}
**Conversation Flow**: {selected_strategy['conversation_flow']}

**Customer Context Analysis**:
- Intent: {conversation_state.current_intent}
- Profile completeness: {len(customer_profile)} fields
- Recommended approach: {selected_strategy['reasoning']}

This conversation will be tracked for outcome-based learning to improve future interactions."""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=session_id,
            confidence=0.9,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["conversation_initialization", "strategy_selection"],
            context_used={
                "operation": "conversation_start",
                "selected_strategy": selected_strategy,
                "customer_context": customer_profile
            },
            follow_up_suggestions=[
                "How should I optimize the conversation flow?",
                "What strategy works best for this customer type?",
                "Track this conversation outcome when complete"
            ]
        )
    
    def _select_strategy(self, conversation_state: ConversationState) -> Dict[str, str]:
        """Select optimal strategy using multi-armed bandit approach"""
        
        # Extract context features for strategy selection
        context_key = self._get_context_key(conversation_state)
        
        # Multi-armed bandit strategy selection
        if random.random() < self.epsilon or self._need_exploration(context_key):
            # Exploration: randomly select strategy
            selected_strategy = random.choice(self.available_strategies)
            reasoning = "Exploring new strategy to gather data"
        else:
            # Exploitation: select best performing strategy for this context
            selected_strategy = self._get_best_strategy_for_context(context_key)
            reasoning = f"Selected based on {selected_strategy} showing best results for similar customers"
        
        # Select complementary elements
        response_tone = self._select_tone_for_strategy(selected_strategy, conversation_state)
        conversation_flow = self._select_flow_for_strategy(selected_strategy, conversation_state)
        
        return {
            "primary_strategy": selected_strategy,
            "response_tone": response_tone,
            "conversation_flow": conversation_flow,
            "reasoning": reasoning,
            "context_key": context_key
        }
    
    def _get_context_key(self, conversation_state: ConversationState) -> str:
        """Generate context key for strategy selection"""
        profile = conversation_state.customer_profile
        
        # Create context signature
        context_elements = [
            profile.get("income_level", "unknown"),
            profile.get("loan_purpose", "unknown"),
            profile.get("urgency", "unknown"),
            conversation_state.current_intent,
            "experienced" if profile.get("previous_loans", 0) > 0 else "first_time"
        ]
        
        return "_".join(context_elements)
    
    def _need_exploration(self, context_key: str) -> bool:
        """Determine if we need to explore for this context"""
        # Check if we have enough data for this context
        context_data_count = sum(
            1 for outcome in self.conversation_outcomes.values()
            if self._get_context_key_from_outcome(outcome) == context_key
        )
        
        return context_data_count < self.min_data_points
    
    def _get_best_strategy_for_context(self, context_key: str) -> str:
        """Get the best performing strategy for a specific context"""
        strategy_rewards = defaultdict(list)
        
        # Analyze outcomes for this context
        for outcome in self.conversation_outcomes.values():
            if self._get_context_key_from_outcome(outcome) == context_key:
                strategy_rewards[outcome.primary_strategy].append(outcome.total_reward)
        
        # Calculate average rewards
        best_strategy = "consultative_approach"  # Default
        best_avg_reward = -1
        
        for strategy, rewards in strategy_rewards.items():
            if rewards:
                avg_reward = np.mean(rewards)
                if avg_reward > best_avg_reward:
                    best_avg_reward = avg_reward
                    best_strategy = strategy
        
        return best_strategy
    
    def _get_context_key_from_outcome(self, outcome: ConversationOutcome) -> str:
        """Extract context key from conversation outcome"""
        profile = outcome.customer_profile
        
        context_elements = [
            profile.get("income_level", "unknown"),
            profile.get("loan_purpose", "unknown"), 
            profile.get("urgency", "unknown"),
            outcome.query_type,
            "experienced" if profile.get("previous_loans", 0) > 0 else "first_time"
        ]
        
        return "_".join(context_elements)
    
    def _select_tone_for_strategy(self, strategy: str, conversation_state: ConversationState) -> str:
        """Select appropriate tone for the chosen strategy"""
        tone_mapping = {
            "consultative_approach": "consultative",
            "direct_sales": "authoritative", 
            "educational_first": "professional",
            "benefit_focused": "friendly",
            "problem_solving": "empathetic",
            "trust_building": "professional",
            "urgency_creating": "authoritative"
        }
        
        return tone_mapping.get(strategy, "professional")
    
    def _select_flow_for_strategy(self, strategy: str, conversation_state: ConversationState) -> str:
        """Select appropriate conversation flow for the chosen strategy"""
        flow_mapping = {
            "consultative_approach": "discovery_first",
            "direct_sales": "solution_focused",
            "educational_first": "linear", 
            "benefit_focused": "adaptive",
            "problem_solving": "discovery_first",
            "trust_building": "linear",
            "urgency_creating": "solution_focused"
        }
        
        return flow_mapping.get(strategy, "adaptive")
    
    def _detect_intent(self, query: str) -> str:
        """Detect customer intent from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["loan", "borrow", "money", "amount"]):
            return "loan_inquiry"
        elif any(word in query_lower for word in ["rate", "interest", "cost", "fee"]):
            return "rate_inquiry"
        elif any(word in query_lower for word in ["apply", "application", "process"]):
            return "application_intent"
        elif any(word in query_lower for word in ["document", "papers", "requirement"]):
            return "documentation_query"
        elif any(word in query_lower for word in ["hello", "hi", "good morning", "help"]):
            return "greeting"
        else:
            return "general_inquiry"
    
    async def _handle_outcome_tracking(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Track conversation outcome for RL learning"""
        
        # Parse outcome data from request
        session_id = request.session_id or "unknown_session"
        outcome_data = request.additional_context or {}
        
        # Calculate reward signals
        reward = self._calculate_reward(outcome_data)
        
        # Create conversation outcome
        conversation_outcome = ConversationOutcome(
            session_id=session_id,
            start_time=outcome_data.get("start_time", start_time),
            end_time=start_time,
            duration_seconds=outcome_data.get("duration", 0),
            conversion=outcome_data.get("conversion", False),
            qualification=outcome_data.get("qualification", False),
            satisfaction_score=outcome_data.get("satisfaction_score", 0.0),
            engagement_score=outcome_data.get("engagement_score", 0.0),
            total_messages=outcome_data.get("total_messages", 0),
            customer_messages=outcome_data.get("customer_messages", 0),
            ai_messages=outcome_data.get("ai_messages", 0),
            objections_raised=outcome_data.get("objections_raised", 0),
            objections_resolved=outcome_data.get("objections_resolved", 0),
            agents_used=outcome_data.get("agents_used", []),
            primary_strategy=outcome_data.get("primary_strategy", "default"),
            response_tone=outcome_data.get("response_tone", "professional"),
            conversation_flow=outcome_data.get("conversation_flow", "linear"),
            customer_profile=outcome_data.get("customer_profile", {}),
            query_type=outcome_data.get("query_type", "general"),
            complexity_level=outcome_data.get("complexity_level", "simple"),
            total_reward=reward
        )
        
        # Store outcome
        self.conversation_outcomes[session_id] = conversation_outcome
        
        # Update strategy performance
        self._update_strategy_performance(conversation_outcome)
        
        # Save to disk
        await self._save_rl_data()
        
        # Clean up active conversation
        if session_id in self.active_conversations:
            del self.active_conversations[session_id]
        
        response_text = f"""Conversation outcome tracked successfully!

**Session**: {session_id}
**Total Reward**: {reward:.2f} points
**Conversion**: {"✅ Yes" if conversation_outcome.conversion else "❌ No"}
**Qualification**: {"✅ Complete" if conversation_outcome.qualification else "📝 Partial"}
**Satisfaction**: {conversation_outcome.satisfaction_score:.1f}/5.0
**Engagement**: {conversation_outcome.engagement_score:.1f}/1.0

**Strategy Performance**:
- Primary Strategy: {conversation_outcome.primary_strategy}
- Response Tone: {conversation_outcome.response_tone}
- Conversation Flow: {conversation_outcome.conversation_flow}

**Learning Impact**:
This outcome will improve future strategy selection for similar customer profiles and conversation contexts."""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=session_id,
            confidence=1.0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["outcome_tracking", "reward_calculation", "strategy_update"],
            context_used={
                "operation": "outcome_tracking",
                "reward_earned": reward,
                "strategy_used": conversation_outcome.primary_strategy
            }
        )
    
    def _calculate_reward(self, outcome_data: Dict[str, Any]) -> float:
        """Calculate reward signal from conversation outcome"""
        reward = 0.0
        
        # Primary outcomes
        if outcome_data.get("conversion", False):
            reward += 100  # Successful loan application
        
        if outcome_data.get("qualification", False):
            reward += 50  # Customer provided complete information
        
        # Satisfaction and engagement
        satisfaction = outcome_data.get("satisfaction_score", 0.0)
        reward += satisfaction * 6  # 0-30 points based on satisfaction
        
        engagement = outcome_data.get("engagement_score", 0.0)
        reward += engagement * 20  # 0-20 points based on engagement
        
        # Objection handling
        objections_raised = outcome_data.get("objections_raised", 0)
        objections_resolved = outcome_data.get("objections_resolved", 0)
        if objections_raised > 0:
            resolution_rate = objections_resolved / objections_raised
            reward += resolution_rate * 40  # Up to 40 points for objection handling
        
        # Efficiency bonus
        duration = outcome_data.get("duration", 0)
        if duration > 0 and duration < 900:  # Under 15 minutes
            reward += 10  # Efficiency bonus
        
        # Penalties
        if outcome_data.get("dropout", False):
            reward -= 50  # Customer left conversation
        
        confusion_count = outcome_data.get("clarifications_needed", 0)
        reward -= confusion_count * 5  # Penalty for confusion
        
        return max(0, reward)  # Non-negative rewards
    
    def _update_strategy_performance(self, outcome: ConversationOutcome):
        """Update performance metrics for the strategy used"""
        strategy_name = outcome.primary_strategy
        
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = StrategyPerformance(strategy_name=strategy_name)
        
        strategy = self.strategy_performance[strategy_name]
        
        # Update overall performance
        strategy.total_uses += 1
        strategy.total_reward += outcome.total_reward
        strategy.average_reward = strategy.total_reward / strategy.total_uses
        
        if outcome.conversion:
            strategy.success_count += 1
        
        strategy.conversion_rate = strategy.success_count / strategy.total_uses
        strategy.last_updated = datetime.now()
        
        # Update context-specific performance
        context_key = self._get_context_key_from_outcome(outcome)
        
        if context_key not in strategy.performance_by_context:
            strategy.performance_by_context[context_key] = {
                "uses": 0,
                "total_reward": 0.0,
                "average_reward": 0.0,
                "conversions": 0,
                "conversion_rate": 0.0
            }
        
        context_perf = strategy.performance_by_context[context_key]
        context_perf["uses"] += 1
        context_perf["total_reward"] += outcome.total_reward
        context_perf["average_reward"] = context_perf["total_reward"] / context_perf["uses"]
        
        if outcome.conversion:
            context_perf["conversions"] += 1
        
        context_perf["conversion_rate"] = context_perf["conversions"] / context_perf["uses"]
    
    async def _save_rl_data(self):
        """Save RL data to disk"""
        try:
            # Save outcomes
            outcomes_data = {
                "outcomes": [outcome.model_dump() for outcome in self.conversation_outcomes.values()],
                "last_updated": datetime.now().isoformat()
            }
            (self.outcomes_dir / "outcomes.json").write_text(json.dumps(outcomes_data, indent=2, default=str))
            
            # Save strategy performance
            strategies_data = {
                "strategies": [strategy.model_dump() for strategy in self.strategy_performance.values()],
                "last_updated": datetime.now().isoformat()
            }
            (self.strategies_dir / "performance.json").write_text(json.dumps(strategies_data, indent=2, default=str))
            
        except Exception as e:
            logger.error(f"Failed to save RL data: {e}")
    
    async def _handle_performance_analysis(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Analyze and report strategy performance"""
        
        total_conversations = len(self.conversation_outcomes)
        total_conversions = sum(1 for outcome in self.conversation_outcomes.values() if outcome.conversion)
        overall_conversion_rate = (total_conversions / total_conversations * 100) if total_conversations > 0 else 0
        
        # Get best performing strategies
        strategy_rankings = sorted(
            self.strategy_performance.values(),
            key=lambda s: s.average_reward,
            reverse=True
        )[:3]
        
        response_text = f"""RL Performance Analysis Report

**Overall Metrics**:
- Total Conversations Analyzed: {total_conversations}
- Overall Conversion Rate: {overall_conversion_rate:.1f}%
- Total Conversions: {total_conversions}

**Top Performing Strategies**:
"""
        
        for i, strategy in enumerate(strategy_rankings, 1):
            response_text += f"""
{i}. **{strategy.strategy_name.replace('_', ' ').title()}**
   - Average Reward: {strategy.average_reward:.1f} points
   - Conversion Rate: {strategy.conversion_rate*100:.1f}%
   - Total Uses: {strategy.total_uses}
   - Success Count: {strategy.success_count}
"""
        
        response_text += f"""
**Learning Insights**:
- System has processed {total_conversations} conversations for learning
- Reward signals are continuously improving strategy selection
- {"Exploration phase: Gathering data on different strategies" if total_conversations < 50 else "Exploitation phase: Using proven strategies"}

The RL system is {"actively learning" if total_conversations < 100 else "optimizing performance"} and will continue to improve with more data."""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=1.0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["performance_analysis", "strategy_ranking"],
            context_used={
                "operation": "performance_analysis",
                "total_conversations": total_conversations,
                "conversion_rate": overall_conversion_rate
            }
        )
    
    async def _handle_general_rl_query(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Handle general RL-related queries"""
        
        response_text = f"""RL Optimizer Status:

**Current Learning State**:
- Active Conversations: {len(self.active_conversations)}
- Completed Outcomes: {len(self.conversation_outcomes)}
- Strategy Performance Data: {len(self.strategy_performance)} strategies tracked

**Available Operations**:
1. **Start Conversation**: Initialize RL tracking for a new conversation
2. **Track Outcome**: Record conversation results for learning
3. **Analyze Performance**: View strategy effectiveness metrics
4. **Select Strategy**: Get optimal strategy recommendation

**Learning Progress**:
- Exploration Rate: {self.epsilon*100:.1f}% (testing new strategies)
- Exploitation Rate: {(1-self.epsilon)*100:.1f}% (using proven strategies)
- Data Quality: {"Good" if len(self.conversation_outcomes) > 20 else "Building"}

The system is continuously learning from conversation outcomes to optimize sales effectiveness."""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.9,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["status_reporting"],
            context_used={"operation": "general_query"}
        )
    
    async def _handle_state_update(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Handle conversation state updates during ongoing conversations"""
        session_id = request.session_id or "unknown_session"
        
        if session_id not in self.active_conversations:
            return await self._create_error_response(
                request, 
                f"No active conversation found for session {session_id}. Initialize conversation first.",
                start_time
            )
        
        conversation_state = self.active_conversations[session_id]
        update_data = request.additional_context or {}
        
        # Update conversation state
        if "message_count" in update_data:
            conversation_state.message_count = update_data["message_count"]
        
        if "current_intent" in update_data:
            conversation_state.current_intent = update_data["current_intent"]
        
        if "detected_objections" in update_data:
            conversation_state.detected_objections.extend(update_data["detected_objections"])
        
        if "information_gathered" in update_data:
            conversation_state.information_gathered.update(update_data["information_gathered"])
        
        if "sentiment" in update_data:
            conversation_state.sentiment_trend.append(update_data["sentiment"])
            # Keep only last 5 sentiment scores
            if len(conversation_state.sentiment_trend) > 5:
                conversation_state.sentiment_trend = conversation_state.sentiment_trend[-5:]
        
        if "engagement_level" in update_data:
            conversation_state.engagement_level = update_data["engagement_level"]
        
        if "conversation_history" in update_data:
            conversation_state.conversation_history.extend(update_data["conversation_history"])
        
        # Calculate adaptive recommendations based on current state
        recommendations = self._generate_adaptive_recommendations(conversation_state)
        
        response_text = f"""Conversation state updated for session: {session_id}

**Current State**:
- Message Count: {conversation_state.message_count}
- Current Intent: {conversation_state.current_intent}
- Detected Objections: {len(conversation_state.detected_objections)}
- Information Completeness: {len(conversation_state.information_gathered)} fields
- Engagement Level: {conversation_state.engagement_level:.2f}
- Sentiment Trend: {conversation_state.sentiment_trend[-3:] if conversation_state.sentiment_trend else 'No data'}

**Adaptive Recommendations**:
{recommendations}

State tracking will improve outcome prediction and strategy optimization."""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=session_id,
            confidence=0.85,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["state_tracking", "adaptive_recommendations"],
            context_used={
                "operation": "state_update",
                "conversation_state": conversation_state.model_dump(),
                "recommendations": recommendations
            }
        )
    
    def _generate_adaptive_recommendations(self, conversation_state: ConversationState) -> str:
        """Generate real-time recommendations based on conversation state"""
        recommendations = []
        
        # Engagement level recommendations
        if conversation_state.engagement_level < 0.4:
            recommendations.append("🔄 Consider switching to more engaging conversation style")
            recommendations.append("🎯 Focus on customer's primary pain points")
        
        # Objection handling recommendations
        if len(conversation_state.detected_objections) > 2:
            recommendations.append("⚠️ Multiple objections detected - prioritize trust-building")
            recommendations.append("🤝 Use testimonials or case studies to address concerns")
        
        # Information gathering recommendations
        if len(conversation_state.information_gathered) < 3:
            recommendations.append("📋 Gather more customer context for personalization")
            recommendations.append("❓ Ask targeted questions about loan requirements")
        
        # Sentiment trend recommendations
        if conversation_state.sentiment_trend:
            avg_sentiment = sum(conversation_state.sentiment_trend) / len(conversation_state.sentiment_trend)
            if avg_sentiment < 0.3:
                recommendations.append("😟 Negative sentiment trend - consider empathetic approach")
                recommendations.append("💬 Address customer concerns more directly")
        
        # Message count recommendations
        if conversation_state.message_count > 20:
            recommendations.append("⏱️ Long conversation - consider moving to application stage")
            recommendations.append("🎯 Focus on conversion or qualification")
        
        # Intent-based recommendations
        if conversation_state.current_intent == "rate_inquiry":
            recommendations.append("💰 Customer focused on rates - emphasize competitive advantages")
        elif conversation_state.current_intent == "application_intent":
            recommendations.append("📝 Customer ready to apply - guide through application process")
        
        return "\n".join(f"• {rec}" for rec in recommendations) if recommendations else "• Continue current approach - conversation progressing well"
    
    async def _handle_strategy_selection(self, request: AgentRequest, start_time: datetime) -> AgentResponse:
        """Handle explicit strategy selection requests"""
        
        # Create temporary conversation state from request
        customer_profile = request.user_context or {}
        conversation_state = ConversationState(
            session_id=request.session_id or "strategy_selection",
            customer_profile=customer_profile,
            current_intent=self._detect_intent(request.query)
        )
        
        # Select optimal strategy
        selected_strategy = self._select_strategy(conversation_state)
        
        response_text = f"""Strategy optimization complete!

**Customer Analysis**:
- Profile: {conversation_state.customer_profile}
- Intent: {conversation_state.current_intent}
- Context Key: {selected_strategy['context_key']}

**Recommended Strategy**:
- Primary Strategy: {selected_strategy['primary_strategy']}
- Response Tone: {selected_strategy['response_tone']}
- Conversation Flow: {selected_strategy['conversation_flow']}

**Selection Reasoning**:
{selected_strategy['reasoning']}

**Expected Outcomes**:
- This strategy combination has shown optimal results for similar customer profiles
- Continuous learning will improve strategy selection over time
- Outcome tracking will validate strategy effectiveness"""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.9,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["strategy_selection", "customer_analysis"],
            context_used={
                "operation": "strategy_selection",
                "selected_strategy": selected_strategy,
                "customer_analysis": conversation_state.model_dump()
            },
            follow_up_suggestions=[
                "Start conversation tracking with this strategy",
                "What are the expected outcomes for this approach?",
                "How will this strategy be evaluated?"
            ]
        )
    
    async def _create_error_response(self, request: AgentRequest, error_message: str, start_time: datetime) -> AgentResponse:
        """Create standardized error response"""
        return AgentResponse(
            query=request.query,
            response=f"❌ RL Optimizer Error: {error_message}",
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["error_handling"],
            context_used={"operation": "error", "error": error_message}
        ) 