from agents.conversation_memory import ConversationMemoryService
from agents.knowledge_ingestion import KnowledgeIngestionAgent

class AgentOrchestrator:
    def __init__(self, openai_client, storage_service, graph_intelligence=None):
        self.openai_client = openai_client
        self.storage_service = storage_service
        self.graph_intelligence = graph_intelligence
        
        # Initialize conversation memory
        self.conversation_memory = ConversationMemoryService(
            storage_service=storage_service,
            graph_intelligence=graph_intelligence
        )
        
        # Initialize all agents with dependencies
        self.agents = {
            "sales": SalesAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory),
            "calculator": CalculatorAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory),
            "market_analysis": MarketAnalysisAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory),
            "product_expert": ProductExpertAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory),
            "support": SupportAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory),
            "knowledge_ingestion": KnowledgeIngestionAgent(openai_client, storage_service, graph_intelligence, self.conversation_memory)
        }
        
        # Agent routing keywords with learning capabilities
        self.agent_keywords = {
            "sales": ["sell", "convince", "persuade", "close", "deal", "negotiate", "proposal", "pitch", "objection", "follow up"],
            "calculator": ["calculate", "compute", "emi", "interest", "amount", "loan", "rate", "tenure", "payment", "math"],
            "market_analysis": ["market", "trend", "rate", "comparison", "competitor", "analysis", "research", "industry"],
            "product_expert": ["product", "feature", "benefit", "specification", "type", "option", "category", "details"],
            "support": ["help", "issue", "problem", "support", "assistance", "guidance", "how to", "tutorial"],
            "knowledge_ingestion": ["learn", "ingest", "knowledge", "training", "document", "audio", "recording", "analyze gaps", "insights", "knowledge base", "improve"]
        }

    async def route_query(self, user_query: str, session_id: str) -> str:
        """Route user query to appropriate agent with learning integration"""
        start_time = datetime.now()
        
        try:
            # Check for knowledge ingestion requests first
            if any(keyword in user_query.lower() for keyword in self.agent_keywords["knowledge_ingestion"]):
                logger.info(f"Routing to Knowledge Ingestion Agent: {user_query}")
                return await self._handle_agent_query("knowledge_ingestion", user_query, session_id, start_time)
            
            # Continue with existing routing logic
            if self._should_use_mcp_for_query(user_query):
                try:
                    # Enhance query with contextual information using conversation memory
                    enhanced_context = await self.conversation_memory.get_contextual_prompt_addition(
                        user_query, session_id
                    )
                    
                    if enhanced_context and enhanced_context.strip():
                        logger.info("Enhanced query with conversation context")
                        contextual_query = f"{user_query}\n\nContext: {enhanced_context}"
                    else:
                        contextual_query = user_query
                        
                except Exception as e:
                    logger.warning(f"Failed to get contextual enhancement: {e}")
                    contextual_query = user_query
            else:
                contextual_query = user_query
            
            # ... existing routing logic ...
            
        except Exception as e:
            logger.error(f"Error in route_query: {e}")
            return await self._handle_fallback_response(user_query, session_id, str(e))
        
        finally:
            # Store conversation for learning (always, regardless of agent used)
            try:
                if hasattr(self, 'conversation_memory'):
                    await self.conversation_memory.store_conversation(
                        session_id=session_id,
                        user_message=user_query,
                        ai_response="Processing...",  # Will be updated with actual response
                        metadata={"processing_time": (datetime.now() - start_time).total_seconds()}
                    )
            except Exception as e:
                logger.warning(f"Failed to store conversation for learning: {e}") 