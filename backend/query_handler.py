"""
Query handler module for the Voice-to-Text AI Assistant.
This module handles complex, ambiguous, and multi-intent queries by breaking them down
and processing them appropriately.
"""

import os
import json
import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from graphiti_core import Graphiti
from graphiti_advanced import GraphitiAdvanced, KnowledgeDomain

# Import knowledge feedback module
from knowledge_feedback import answer_with_knowledge_feedback

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Initialize Graphiti client
graphiti = Graphiti(
    os.environ.get("NEO4J_URI"),
    os.environ.get("NEO4J_USER"),
    os.environ.get("NEO4J_PASSWORD")
)

# Import EpisodeType
from graphiti_core.nodes import EpisodeType

class QueryHandler:
    """Handler for complex, ambiguous, and multi-intent queries using advanced Graphiti features"""
    
    def __init__(self, graphiti: Graphiti, graphiti_advanced: GraphitiAdvanced = None):
        """Initialize with Graphiti instances"""
        self.graphiti = graphiti
        self.graphiti_advanced = graphiti_advanced
        
        # Initialize LLM
        from config import get_settings
        self.llm = ChatOpenAI(
            model=get_settings().LLM_MODEL,
            temperature=0.2  # Lower temperature for more deterministic analysis
        )
    
    @staticmethod
    async def analyze_query(query: str) -> Dict[str, Any]:
        """Analyze a query to determine its complexity, ambiguity, and intents"""
        try:
            # Initialize LLM
            from config import get_settings
            llm = ChatOpenAI(
                model=get_settings().LLM_MODEL,
                temperature=0.2  # Lower temperature for more deterministic analysis
            )
            
            # Prompt for query analysis
            system_prompt = """You are an AI assistant specializing in analyzing user queries.
            Examine the query and provide a structured analysis with the following information:
            1. Is the query ambiguous? (yes/no)
            2. Does the query contain multiple intents? (yes/no)
            3. List all possible interpretations of the query
            4. List all distinct intents contained in the query
            5. Provide clarification questions if needed
            6. Identify the knowledge domain(s) this query relates to from the following options:
               - FINANCIAL_PRODUCTS
               - CUSTOMER_SERVICE
               - FAQ
               - AUDIO_RECORDINGS
               - WEB_CONTENT
               - USER_QUERIES
               - USER_FEEDBACK
            
            Respond in JSON format with the following structure:
            {
                "is_ambiguous": boolean,
                "has_multiple_intents": boolean,
                "interpretations": [list of possible interpretations],
                "intents": [list of distinct intents],
                "clarification_questions": [list of questions to clarify ambiguity],
                "domains": [list of relevant knowledge domains from the options provided]
            }
            """
            
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            
            # Get response
            response = llm.invoke(messages)
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
                return analysis
            except json.JSONDecodeError:
                # Fallback if response is not valid JSON
                return {
                    "is_ambiguous": False,
                    "has_multiple_intents": False,
                    "interpretations": [query],
                    "intents": [query],
                    "clarification_questions": [],
                    "domains": ["USER_QUERIES"]
                }
                
        except Exception as e:
            logging.error(f"Error analyzing query: {str(e)}")
            raise
            
    async def handle_query_with_advanced_features(self, query: str) -> Dict[str, Any]:
        """Handle a query using advanced Graphiti features like namespacing and communities"""
        try:
            # First analyze the query
            analysis = await self.analyze_query(query)
            
            # Determine if we need clarification
            if analysis["is_ambiguous"] or analysis["has_multiple_intents"]:
                return {
                    "requires_clarification": True,
                    "analysis": analysis,
                    "message": "Query requires clarification before proceeding.",
                    "clarification_questions": analysis["clarification_questions"]
                }
            
            # Extract relevant domains
            domains = analysis.get("domains", ["USER_QUERIES"])
            domain_enums = []
            
            # Convert string domains to enums
            for domain in domains:
                try:
                    domain_enum = KnowledgeDomain(domain)
                    domain_enums.append(domain_enum)
                except ValueError:
                    logging.warning(f"Invalid domain: {domain}")
            
            # If no valid domains, use USER_QUERIES as fallback
            if not domain_enums:
                domain_enums = [KnowledgeDomain.USER_QUERIES]
            
            # Perform advanced search in each domain with increased limit for better coverage
            all_results = []
            logging.info(f"Searching Graphiti knowledge graph for query: {query}")
            
            for domain in domain_enums:
                logging.info(f"Searching in domain: {domain.value}")
                try:
                    # Use direct Graphiti search first as per documentation
                    # Note: search() doesn't accept limit parameter according to docs
                    direct_results = await self.graphiti_advanced.graphiti.search(query)
                    if direct_results:
                        logging.info(f"Found {len(direct_results)} results using direct Graphiti search")
                        # Limit results if there are too many
                        if len(direct_results) > 10:
                            direct_results = direct_results[:10]
                            logging.info(f"Limited direct search results to 10 items")
                        all_results.extend(direct_results)
                except Exception as e:
                    logging.warning(f"Direct Graphiti search failed: {str(e)}. Falling back to advanced search.")
                
                # Fallback to advanced search if direct search returned no results
                if not all_results:
                    try:
                        advanced_results = await self.graphiti_advanced.advanced_search(
                            query=query,
                            domain=domain,
                            limit=10,  # Increased from 5 to 10 for better coverage
                            search_type="hybrid"
                        )
                        if advanced_results:
                            logging.info(f"Found {len(advanced_results)} results using advanced search")
                            all_results.extend(advanced_results)
                    except Exception as e:
                        logging.warning(f"Advanced search failed for domain {domain.value}: {str(e)}")
            
            # Get community summaries for additional context
            community_summaries = []
            try:
                community_summaries = await self.graphiti_advanced.get_community_summaries(limit=5)  # Increased from 3 to 5
                logging.info(f"Retrieved {len(community_summaries)} community summaries")
            except Exception as e:
                logging.warning(f"Failed to get community summaries: {str(e)}")
            
            # Format the search results for LLM context
            context = []
            
            # Process search results
            for item in all_results:
                if hasattr(item, "fact") and item.fact:
                    context.append(f"Fact: {item.fact}")
                elif hasattr(item, "name") and item.name:
                    if hasattr(item, "attributes") and item.attributes:
                        attrs = ', '.join([f"{k}: {v}" for k, v in item.attributes.items() if k != 'group_id'])
                        context.append(f"Entity: {item.name} ({attrs})")
                    else:
                        context.append(f"Entity: {item.name}")
            
            # Add community summaries to context
            for community in community_summaries:
                if "summary" in community and community["summary"]:
                    context.append(f"Community knowledge: {community['summary']}")
                    
            # Check if we have any knowledge graph context
            if not context:
                logging.warning("No knowledge graph results found for query")
                context = ["No relevant information found in the knowledge graph."]
            else:
                logging.info(f"Found {len(context)} relevant items in knowledge graph")
            
            # Generate response using LLM with context
            system_prompt = """You are an AI assistant with access to a knowledge graph.
            IMPORTANT: Base your answer PRIMARILY on the knowledge graph information provided below.
            Only fall back to your general knowledge if absolutely necessary.
            
            If the knowledge graph contains relevant information, explicitly mention that your answer 
            is based on the knowledge graph. If you're using general knowledge, clearly indicate this.
            
            Knowledge graph information:
            {context}
            """
            
            # Replace placeholder with actual context
            context_str = "\n".join([f"- {fact}" for fact in context])
            system_prompt = system_prompt.replace("{context}", context_str)
            
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            
            # Get response
            response = self.llm.invoke(messages)
            
            # Record this query in the knowledge graph with appropriate namespace
            try:
                await self.graphiti_advanced.add_episode_with_namespace(
                    name=f"user_query_{datetime.datetime.now().isoformat()}",
                    episode_body=query,
                    source=EpisodeType.text,
                    source_description="User query",
                    domain=KnowledgeDomain.USER_QUERIES,
                    update_communities=True  # Update communities with this new query
                )
                logging.info("Successfully added query to knowledge graph")
            except Exception as e:
                logging.error(f"Failed to add query to knowledge graph: {str(e)}")
            
            return {
                "requires_clarification": False,
                "analysis": analysis,
                "response": response.content,
                "context_used": context,
                "domains_searched": [domain.value for domain in domain_enums],
                "knowledge_graph_used": len(context) > 1  # True if we found actual knowledge graph content
            }
            
        except Exception as e:
            logging.error(f"Error handling query with advanced features: {str(e)}")
            raise
    
    @staticmethod
    async def decompose_multi_intent_query(query: str) -> List[str]:
        """
        Decompose a multi-intent query into individual queries.
        
        Args:
            query: The multi-intent user query
            
        Returns:
            List of individual queries
        """
        try:
            # Prepare prompt for query decomposition
            prompt = f"""
            The following is a multi-intent query that needs to be broken down into separate, individual queries:
            
            Query: "{query}"
            
            Please break this down into individual queries, one per line. Each query should be self-contained and answerable on its own.
            Do not include any explanations or numbering, just the individual queries.
            """
            
            # Get response from LLM
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            
            # Split into individual queries
            individual_queries = [q.strip() for q in response.content.strip().split('\n') if q.strip()]
            
            return individual_queries
        except Exception as e:
            logger.error(f"Error decomposing multi-intent query: {str(e)}")
            return [query]  # Return original query if decomposition fails
    
    @staticmethod
    async def clarify_ambiguous_query(query: str, clarification_question: str) -> str:
        """
        Generate a clarification for an ambiguous query.
        
        Args:
            query: The ambiguous user query
            clarification_question: Question to ask for clarification
            
        Returns:
            Clarification response
        """
        try:
            # For now, we'll just return the clarification question
            # In a real system, this would interact with the user to get clarification
            return f"I need to clarify something about your question. {clarification_question}"
        except Exception as e:
            logger.error(f"Error clarifying ambiguous query: {str(e)}")
            return "I'm not sure I understand your question. Could you please rephrase it?"
    
    @staticmethod
    async def handle_complex_query(query: str, analysis: Dict[str, Any]) -> str:
        """
        Handle a complex query based on its analysis.
        
        Args:
            query: The user query
            analysis: Query analysis results
            
        Returns:
            Response to the query
        """
        try:
            # If clarification is needed, return clarification question
            if analysis.get("clarification_needed", False):
                return await QueryHandler.clarify_ambiguous_query(
                    query, 
                    analysis.get("clarification_question", "Could you please provide more details?")
                )
            
            # If multi-intent, decompose and answer each part
            if analysis.get("is_multi_intent", False):
                individual_queries = await QueryHandler.decompose_multi_intent_query(query)
                
                # Answer each individual query
                responses = []
                for i, individual_query in enumerate(individual_queries):
                    answer = await answer_with_knowledge_feedback(individual_query)
                    responses.append(f"Regarding '{individual_query}':\n{answer}")
                
                # Combine responses
                combined_response = "\n\n".join(responses)
                
                # Store the complex query and response in the knowledge graph
                await graphiti.add_episode(
                    name=f"Complex Query {datetime.datetime.now().isoformat()}",
                    episode_body=json.dumps({
                        "original_query": query,
                        "individual_queries": individual_queries,
                        "responses": responses,
                        "analysis": analysis
                    }),
                    source=EpisodeType.json,
                    source_description="Complex query handling",
                    reference_time=datetime.datetime.now()
                )
                
                return combined_response
            
            # If ambiguous but no clarification needed, use context-aware processing
            if analysis.get("is_ambiguous", False):
                # Prepare a more specific prompt for the LLM
                prompt = f"""
                The following query is ambiguous but I'll try to provide the most helpful response:
                
                Query: "{query}"
                
                Entities mentioned: {", ".join(analysis.get("entities", []))}
                Domain: {analysis.get("domain", "general")}
                
                Please provide a comprehensive answer that addresses the likely intent behind this query.
                """
                
                # Get response from LLM
                response = await llm.ainvoke([HumanMessage(content=prompt)])
                
                # Store the ambiguous query and response in the knowledge graph
                await graphiti.add_episode(
                    name=f"Ambiguous Query {datetime.datetime.now().isoformat()}",
                    episode_body=json.dumps({
                        "query": query,
                        "response": response.content,
                        "analysis": analysis
                    }),
                    source=EpisodeType.json,
                    source_description="Ambiguous query handling",
                    reference_time=datetime.datetime.now()
                )
                
                return response.content
            
            # For other complex queries, use standard knowledge feedback
            return await answer_with_knowledge_feedback(query)
        except Exception as e:
            logger.error(f"Error handling complex query: {str(e)}")
            # Fallback to standard knowledge feedback
            return await answer_with_knowledge_feedback(query)
    
    @staticmethod
    async def process_query(query: str) -> str:
        """
        Process a user query, handling complexity, ambiguity, and multiple intents.
        
        Args:
            query: The user query to process
            
        Returns:
            Response to the query
        """
        try:
            # Analyze the query
            analysis = await QueryHandler.analyze_query(query)
            
            # Log analysis
            logger.info(f"Query analysis: {json.dumps(analysis)}")
            
            # Handle based on complexity
            if analysis.get("complexity") == "simple" and not analysis.get("is_ambiguous") and not analysis.get("is_multi_intent"):
                # Simple query, use standard knowledge feedback
                return await answer_with_knowledge_feedback(query)
            else:
                # Complex query, use specialized handling
                return await QueryHandler.handle_complex_query(query, analysis)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            # Fallback to standard knowledge feedback
            return await answer_with_knowledge_feedback(query)


# Example usage
async def main():
    # Example: Process a simple query
    simple_query = "What is a mortgage?"
    simple_response = await QueryHandler.process_query(simple_query)
    print(f"Simple Query: {simple_query}")
    print(f"Response: {simple_response}\n")
    
    # Example: Process a multi-intent query
    multi_query = "What is the difference between a fixed and variable rate mortgage, and how do I improve my credit score?"
    multi_response = await QueryHandler.process_query(multi_query)
    print(f"Multi-Intent Query: {multi_query}")
    print(f"Response: {multi_response}\n")
    
    # Example: Process an ambiguous query
    ambiguous_query = "Tell me about rates"
    ambiguous_response = await QueryHandler.process_query(ambiguous_query)
    print(f"Ambiguous Query: {ambiguous_query}")
    print(f"Response: {ambiguous_response}")


if __name__ == "__main__":
    asyncio.run(main())
