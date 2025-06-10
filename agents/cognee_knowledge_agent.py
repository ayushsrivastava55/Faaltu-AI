import asyncio
import logging
import os
from typing import Dict, Any, Optional
import json

# Import Cognee and related dependencies
try:
    import cognee
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False
    print("WARNING: Cognee not installed. Install with: pip install cognee")

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("WARNING: Neo4j driver not installed. Install with: pip install neo4j")

# Base agent class - adjust import path to match your project structure
from .base import BaseAgent  # or wherever your BaseAgent is located

logger = logging.getLogger(__name__)

class CogneeKnowledgeIngestionAgent(BaseAgent):
    """
    Specialized agent for handling knowledge ingestion and retrieval using Cognee.
    Transforms documents into semantic knowledge graphs stored in Neo4j.
    """
    
    def __init__(self):
        super().__init__(
            name="Cognee Knowledge Ingestion Agent",
            description="Processes documents into knowledge graphs using Cognee and Neo4j"
        )
        self.initialized = False
        self.error_message = None
        
        # Initialize Cognee if available
        if COGNEE_AVAILABLE and NEO4J_AVAILABLE:
            try:
                self._setup_cognee()
                self.initialized = True
                logger.info("✅ Cognee Knowledge Agent initialized successfully")
            except Exception as e:
                self.error_message = str(e)
                logger.error(f"❌ Failed to initialize Cognee: {e}")
        else:
            self.error_message = "Cognee or Neo4j dependencies not available"
            logger.error(f"❌ {self.error_message}")
    
    def _setup_cognee(self):
        """Initialize Cognee with Neo4j configuration"""
        # Check required environment variables
        required_env_vars = [
            'LLM_API_KEY',
            'GRAPH_DATABASE_URL', 
            'GRAPH_DATABASE_USERNAME',
            'GRAPH_DATABASE_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Test Neo4j connectivity
        self._test_neo4j_connection()
        
        logger.info("Cognee environment setup completed")
    
    def _test_neo4j_connection(self):
        """Test Neo4j database connectivity"""
        try:
            uri = os.getenv('GRAPH_DATABASE_URL')
            username = os.getenv('GRAPH_DATABASE_USERNAME')
            password = os.getenv('GRAPH_DATABASE_PASSWORD')
            
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            logger.info("✅ Neo4j connection test successful")
        except Exception as e:
            raise ConnectionError(f"Neo4j connection failed: {e}")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing queries.
        Handles different types of operations based on the query content.
        """
        
        # Check if agent is properly initialized
        if not self.initialized:
            return {
                "success": False,
                "error": f"Cognee agent not initialized: {self.error_message}",
                "agent": self.name
            }
        
        try:
            # Parse the query to determine operation type
            operation = self._parse_operation(query, context)
            
            if operation["type"] == "ingest_file":
                return await self._handle_file_ingestion(operation["data"])
            elif operation["type"] == "ingest_text":
                return await self._handle_text_ingestion(operation["data"])
            elif operation["type"] == "search":
                return await self._handle_knowledge_search(operation["data"])
            elif operation["type"] == "status":
                return await self._handle_status_check()
            elif operation["type"] == "clear":
                return await self._handle_clear_knowledge()
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation type: {operation['type']}",
                    "agent": self.name
                }
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def _parse_operation(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse the query to determine what operation to perform"""
        
        # If context contains file information, it's a file ingestion
        if context and "file_content" in context:
            return {
                "type": "ingest_file",
                "data": {
                    "content": context["file_content"],
                    "filename": context.get("filename", "unknown"),
                    "dataset_name": context.get("dataset_name", "default")
                }
            }
        
        # Check for specific query patterns
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ["search", "find", "query", "tell me about"]):
            return {
                "type": "search",
                "data": {"query": query}
            }
        elif "status" in query_lower or "health" in query_lower:
            return {
                "type": "status",
                "data": {}
            }
        elif "clear" in query_lower and "knowledge" in query_lower:
            return {
                "type": "clear",
                "data": {}
            }
        else:
            # Default to text ingestion
            return {
                "type": "ingest_text",
                "data": {"text": query}
            }
    
    async def _handle_file_ingestion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file content ingestion into Cognee"""
        try:
            content = data["content"]
            filename = data["filename"]
            dataset_name = data["dataset_name"]
            
            # Add content to Cognee
            await cognee.add(content, dataset_name=dataset_name)
            
            # Process into knowledge graph
            await cognee.cognify()
            
            logger.info(f"Successfully processed file {filename} into knowledge graph")
            
            return {
                "success": True,
                "message": f"File '{filename}' successfully processed into knowledge graph",
                "dataset": dataset_name,
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            return {
                "success": False,
                "error": f"Failed to process file: {str(e)}",
                "agent": self.name
            }
    
    async def _handle_text_ingestion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text ingestion into Cognee"""
        try:
            text = data["text"]
            
            # Add text to Cognee
            await cognee.add(text)
            
            # Process into knowledge graph
            await cognee.cognify()
            
            return {
                "success": True,
                "message": "Text successfully processed into knowledge graph",
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"Text ingestion failed: {e}")
            return {
                "success": False,
                "error": f"Failed to process text: {str(e)}",
                "agent": self.name
            }
    
    async def _handle_knowledge_search(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge graph search queries"""
        try:
            query = data["query"]
            
            # Search the knowledge graph
            results = await cognee.search(query)
            
            # Format results for response
            formatted_results = []
            for result in results[:5]:  # Limit to top 5 results
                formatted_results.append({
                    "content": str(result),
                    "relevance": "high"  # Cognee handles relevance internally
                })
            
            return {
                "success": True,
                "results": formatted_results,
                "query": query,
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "agent": self.name
            }
    
    async def _handle_status_check(self) -> Dict[str, Any]:
        """Check system status and health"""
        try:
            # Test Neo4j connection
            self._test_neo4j_connection()
            
            # Test Cognee functionality
            await cognee.add("health_check_test")
            
            return {
                "success": True,
                "status": "healthy",
                "neo4j": "connected",
                "cognee": "functional",
                "agent": self.name
            }
            
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "agent": self.name
            }
    
    async def _handle_clear_knowledge(self) -> Dict[str, Any]:
        """Clear all knowledge from the system (use with caution)"""
        try:
            # This is a destructive operation - should have confirmation
            # For safety, this is not implemented by default
            return {
                "success": False,
                "error": "Clear operation requires explicit confirmation",
                "agent": self.name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def is_available(self) -> bool:
        """Check if the agent is available for processing"""
        return self.initialized and COGNEE_AVAILABLE and NEO4J_AVAILABLE
    
    def get_capabilities(self) -> list:
        """Return list of agent capabilities"""
        return [
            "Document ingestion into knowledge graphs",
            "Text processing with semantic understanding", 
            "Natural language search across knowledge base",
            "Entity and relationship extraction",
            "Knowledge graph querying"
        ]
