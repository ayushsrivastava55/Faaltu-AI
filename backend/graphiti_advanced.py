"""
Advanced Graphiti integration module for the Voice-to-Text AI Assistant.
This module implements advanced Graphiti features:
- Communities for organizing related entities
- Namespacing for knowledge domain separation
- Advanced hybrid search capabilities
- Temporal querying
- LangGraph integration
"""

import os
import asyncio
import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel

# Graphiti imports
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EntityNode, CommunityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF,
    COMMUNITY_HYBRID_SEARCH_RRF
)

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# Local imports
from config import get_settings

# Define knowledge domains for namespacing
class KnowledgeDomain(str, Enum):
    FINANCIAL_PRODUCTS = "financial_products"
    CUSTOMER_SERVICE = "customer_service"
    FAQ = "faq"
    AUDIO_RECORDINGS = "audio_recordings"
    WEB_CONTENT = "web_content"
    USER_QUERIES = "user_queries"
    USER_FEEDBACK = "user_feedback"

class GraphitiAdvanced:
    """Advanced Graphiti integration for the Voice-to-Text AI Assistant."""
    
    def __init__(self, graphiti: Graphiti):
        """Initialize with an existing Graphiti instance."""
        self.graphiti = graphiti
        
    async def build_and_maintain_communities(self):
        """Build communities and schedule periodic maintenance."""
        try:
            # Build initial communities
            await self.graphiti.build_communities()
            print("Communities built successfully")
            return True
        except Exception as e:
            print(f"Error building communities: {str(e)}")
            return False
    
    async def add_episode_with_namespace(
        self, 
        name: str,
        episode_body: Union[str, Dict],
        source: EpisodeType,
        source_description: str,
        domain: KnowledgeDomain,
        reference_time: Optional[datetime.datetime] = None,
        update_communities: bool = True
    ):
        """Add an episode with appropriate namespace and community updating."""
        try:
            if reference_time is None:
                reference_time = datetime.datetime.now()
                
            # Add the episode with namespace and community updating
            episode_uuid = await self.graphiti.add_episode(
                name=name,
                episode_body=episode_body,
                source=source,
                source_description=source_description,
                reference_time=reference_time,
                group_id=domain.value,  # Use domain as namespace
                update_communities=update_communities  # Update communities with new entities
            )
            
            return episode_uuid
        except Exception as e:
            print(f"Error adding episode with namespace: {str(e)}")
            return None
    
    async def advanced_search(
        self,
        query: str,
        domain: Optional[KnowledgeDomain] = None,
        reference_time: Optional[datetime.datetime] = None,
        limit: int = 10,
        search_type: str = "hybrid"  # "hybrid", "semantic", "keyword"
    ):
        """Perform advanced search using Graphiti's capabilities."""
        try:
            # Create a copy of the hybrid search recipe
            search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
            search_config.limit = limit
            
            # Configure search type
            if search_type == "semantic":
                search_config.semantic_weight = 1.0
                search_config.keyword_weight = 0.0
            elif search_type == "keyword":
                search_config.semantic_weight = 0.0
                search_config.keyword_weight = 1.0
            # else hybrid (default) uses both
            
            # Execute the search with optional namespace and time constraints
            kwargs = {"query": query, "config": search_config}
            
            # Note: group_id is not supported in the current Graphiti version
            # Instead, we'll filter results after search if domain is specified
            
            if reference_time:
                kwargs["reference_time"] = reference_time
                
            results = await self.graphiti._search(**kwargs)
            
            # If domain is specified, filter results by group_id after search
            if domain and results:
                filtered_results = []
                for result in results:
                    # Check if the result has a group_id attribute that matches the domain
                    if hasattr(result, 'group_id') and result.group_id == domain.value:
                        filtered_results.append(result)
                    # Some results might be in a different format, handle accordingly
                    elif isinstance(result, dict) and result.get('group_id') == domain.value:
                        filtered_results.append(result)
                return filtered_results
            
            return results
        except Exception as e:
            print(f"Error performing advanced search: {str(e)}")
            return []
    
    async def get_community_summaries(self, limit: int = 5):
        """Get summaries of the top communities in the knowledge graph."""
        try:
            # Create a search config for communities
            search_config = COMMUNITY_HYBRID_SEARCH_RRF.model_copy(deep=True)
            search_config.limit = limit
            
            # Get all communities (no specific query)
            communities = await self.graphiti._search(
                query="",
                config=search_config
            )
            
            # Extract summaries
            summaries = []
            for community in communities:
                if isinstance(community, CommunityNode):
                    summaries.append({
                        "id": community.uuid,
                        "summary": community.summary,
                        "size": community.size if hasattr(community, "size") else None
                    })
            
            return summaries
        except Exception as e:
            print(f"Error getting community summaries: {str(e)}")
            return []
    
    async def temporal_query(
        self,
        query: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        domain: Optional[KnowledgeDomain] = None
    ):
        """Query the knowledge graph across a time range to see how facts evolved."""
        try:
            results = []
            
            # Query at start time
            start_results = await self.advanced_search(
                query=query,
                domain=domain,
                reference_time=start_time
            )
            
            # Query at end time
            end_results = await self.advanced_search(
                query=query,
                domain=domain,
                reference_time=end_time
            )
            
            # Analyze changes between the two time points
            start_facts = {self._extract_fact(item) for item in start_results}
            end_facts = {self._extract_fact(item) for item in end_results}
            
            # Find new facts (in end but not in start)
            new_facts = end_facts - start_facts
            
            # Find removed facts (in start but not in end)
            removed_facts = start_facts - end_facts
            
            # Find unchanged facts
            unchanged_facts = start_facts.intersection(end_facts)
            
            return {
                "new_facts": list(new_facts),
                "removed_facts": list(removed_facts),
                "unchanged_facts": list(unchanged_facts),
                "start_time": start_time,
                "end_time": end_time
            }
        except Exception as e:
            print(f"Error performing temporal query: {str(e)}")
            return {"error": str(e)}
    
    def _extract_fact(self, item):
        """Extract a fact string from a search result item."""
        if hasattr(item, "fact"):
            return item.fact
        elif hasattr(item, "name"):
            return item.name
        else:
            return str(item)
    
    async def add_fact_triplet_with_namespace(
        self,
        source_name: str,
        relation: str,
        target_name: str,
        fact: str,
        domain: KnowledgeDomain,
        reference_time: Optional[datetime.datetime] = None
    ):
        """Add a fact triplet with namespace."""
        try:
            if reference_time is None:
                reference_time = datetime.datetime.now()
                
            # Create source and target nodes with namespace
            source_node = EntityNode(
                name=source_name,
                group_id=domain.value
            )
            
            target_node = EntityNode(
                name=target_name,
                group_id=domain.value
            )
            
            # Create edge with namespace
            edge = EntityEdge(
                source_node_uuid=source_node.uuid,
                target_node_uuid=target_node.uuid,
                name=relation,
                fact=fact,
                created_at=reference_time,
                group_id=domain.value
            )
            
            # Add the triplet
            await self.graphiti.add_triplet(source_node, edge, target_node)
            
            return True
        except Exception as e:
            print(f"Error adding fact triplet with namespace: {str(e)}")
            return False

    # LangGraph integration if available
    if LANGGRAPH_AVAILABLE:
        def create_knowledge_agent(self, llm):
            """Create an agent with LangGraph integration."""
            try:
                # Define the agent state
                class AgentState(BaseModel):
                    query: str
                    context: List[str] = []
                    response: Optional[str] = None
                
                # Define the workflow nodes
                def retrieve_context(state):
                    """Retrieve relevant context from Graphiti."""
                    query = state["query"]
                    
                    # Run this synchronously in the workflow
                    loop = asyncio.get_event_loop()
                    search_results = loop.run_until_complete(
                        self.advanced_search(query=query, limit=5)
                    )
                    
                    # Extract facts from search results
                    context = [self._extract_fact(item) for item in search_results]
                    
                    return {"context": context}
                
                def generate_response(state):
                    """Generate a response using the LLM and context."""
                    query = state["query"]
                    context = state["context"]
                    
                    # Format context for the LLM
                    context_str = "\n".join([f"- {fact}" for fact in context])
                    
                    # Generate response with LLM
                    prompt = f"""
                    Based on the following information:
                    {context_str}
                    
                    Please answer the user's question: {query}
                    """
                    
                    response = llm.invoke(prompt)
                    
                    return {"response": response}
                
                # Create the graph
                workflow = StateGraph(AgentState)
                
                # Add nodes
                workflow.add_node("retrieve_context", retrieve_context)
                workflow.add_node("generate_response", generate_response)
                
                # Add edges
                workflow.add_edge("retrieve_context", "generate_response")
                workflow.add_edge("generate_response", END)
                
                # Set the entry point
                workflow.set_entry_point("retrieve_context")
                
                # Compile the graph
                knowledge_agent = workflow.compile()
                
                return knowledge_agent
            except Exception as e:
                print(f"Error creating knowledge agent: {str(e)}")
                return None
    else:
        def create_knowledge_agent(self, llm):
            """Placeholder when LangGraph is not available."""
            print("LangGraph is not available. Install it with: pip install langgraph")
            return None
