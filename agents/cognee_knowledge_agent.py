import asyncio
import logging
import os
from typing import Dict, Any, Optional
import json
import re

def configure_litellm_logging():
    """Configure LiteLLM to reduce log spam"""
    import litellm
    
    # Set litellm to non-verbose mode
    litellm.set_verbose = False
    
    # Configure logging levels for LiteLLM components
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("litellm.utils").setLevel(logging.WARNING)
    logging.getLogger("litellm.cost_calculator").setLevel(logging.WARNING)

# Call this function early in your application startup
configure_litellm_logging()

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
# Option 1: If BaseAgent is in a parent directory
# from ..base import BaseAgent
# Option 2: If BaseAgent is in the same directory  
# from .base import BaseAgent
# Option 3: If BaseAgent is in a different module
try:
    from .base import BaseAgent
except ImportError:
    try:
        from base import BaseAgent
    except ImportError:
        # Fallback - create a simple BaseAgent if not found
        class BaseAgent:
            def __init__(self, name, description, system_prompt, openai_client, storage_service):
                self.name = name
                self.description = description
                self.system_prompt = system_prompt
                self.openai_client = openai_client
                self.storage_service = storage_service

logger = logging.getLogger(__name__)

class CogneeKnowledgeIngestionAgent(BaseAgent):
    """
    Specialized agent for handling knowledge ingestion and retrieval using Cognee.
    Transforms documents into semantic knowledge graphs stored in Neo4j.
    """
    
    def __init__(self, system_prompt: str, openai_client, storage_service):
        # Call parent constructor with required arguments
        super().__init__(
            name="Cognee Knowledge Ingestion Agent",
            description="Processes documents into knowledge graphs using Cognee and Neo4j",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service
        )
        
        # Initialize Cognee-specific attributes
        self.initialized = False
        self.error_message = None
        self.neo4j_driver = None
        
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
        
        # Test Neo4j connectivity with improved error handling
        self._test_neo4j_connection()
        
        # Set up Cognee configuration to handle Neo4j compatibility issues
        self._configure_cognee_for_neo4j()
        
        logger.info("Cognee environment setup completed")
    
    def _configure_cognee_for_neo4j(self):
        """Configure Cognee to handle Neo4j version compatibility"""
        try:
            # Set environment variables for Cognee Neo4j configuration
            os.environ['NEO4J_USE_ELEMENT_ID'] = 'true'
            os.environ['NEO4J_CYPHER_USE_ELEMENT_ID'] = 'true'
            os.environ['NEO4J_ELEMENTID_ONLY'] = 'true'
            os.environ['NEO4J_VERSION'] = '5'
     
            # Create a Neo4j driver configuration to handle elementId
            driver_config = {
                'database': 'neo4j',
            }
     
            # Tell Cognee to generate compatible Cypher queries
            if hasattr(cognee, 'config'):
                cognee_config = {
                    'graph_database_provider': 'neo4j',
                    'graph_database_url': os.getenv('GRAPH_DATABASE_URL'),
                    'graph_database_username': os.getenv('GRAPH_DATABASE_USERNAME'),
                    'graph_database_password': os.getenv('GRAPH_DATABASE_PASSWORD'),
                    'use_element_id': True,
                    'cypher_dialect': 'neo4j_5',
                    'suppress_deprecation_warnings': True,
                    'driver_config': driver_config
                }
                
                cognee.config.update(cognee_config)
                
                if hasattr(cognee, 'enable_neo4j_5_compatibility'):
                    cognee.enable_neo4j_5_compatibility()
                    
                self._monkey_patch_cognee_queries()
                    
        except Exception as e:
            logger.warning(f"Could not configure Cognee for Neo4j compatibility: {e}")
            
    def _test_neo4j_connection(self):
        """Test Neo4j database connectivity with improved error handling"""
        try:
            uri = os.getenv('GRAPH_DATABASE_URL')
            username = os.getenv('GRAPH_DATABASE_USERNAME')
            password = os.getenv('GRAPH_DATABASE_PASSWORD')
            
            # Create driver with additional configuration
            self.neo4j_driver = GraphDatabase.driver(
                uri, 
                auth=(username, password),
                # Configure driver to handle newer Neo4j versions
                database="neo4j"  # Explicitly specify database
            )
            
            # Test connection with a simple query that avoids deprecated functions
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record["test"] == 1:
                    logger.info("✅ Neo4j connection test successful")
                else:
                    raise ConnectionError("Neo4j test query failed")
                    
        except Exception as e:
            if self.neo4j_driver:
                self.neo4j_driver.close()
                self.neo4j_driver = None
            raise ConnectionError(f"Neo4j connection failed: {e}")
    
    def _monkey_patch_cognee_queries(self):
        """Apply monkey patches to Cognee query functions if possible"""
        try:
            if hasattr(cognee, 'graph_store') and hasattr(cognee.graph_store, 'execute_query'):
                original_execute = cognee.graph_store.execute_query
                
                def patched_execute(query, *args, **kwargs):
                    patched_query = self._patch_query_for_neo4j_5(query)
                    return original_execute(patched_query, *args, **kwargs)
                
                cognee.graph_store.execute_query = patched_execute
                logger.info("Successfully patched Cognee query execution")
        except Exception as e:
            logger.warning(f"Failed to monkey patch Cognee queries: {e}")

    def _patch_query_for_neo4j_5(self, query_string):
        """Replace deprecated id() function with elementId() in Neo4j Cypher queries"""
        # Pattern to match id() function calls
        id_pattern = r'id\s*\(\s*([a-zA-Z0-9_]+)\s*\)'
        
        # Replace with elementId()
        patched_query = re.sub(id_pattern, r'elementId(\1)', query_string)
        
        # Log the query change if it was modified
        if patched_query != query_string:
            logger.info(f"Patched Neo4j query: {query_string} -> {patched_query}")
        
        return patched_query

    def _apply_neo4j_5_query_patches(self):
        """Apply additional Neo4j 5.x compatibility patches"""
        try:
            # Set additional environment variables for Neo4j 5.x compatibility
            os.environ['NEO4J_FORCE_ELEMENT_ID'] = 'true'
            os.environ['NEO4J_DISABLE_ID_FUNCTION'] = 'true'
            
            # Apply more aggressive monkey patching if available
            if hasattr(cognee, 'query_builder'):
                original_build = cognee.query_builder.build_query
                
                def patched_build(query_parts, *args, **kwargs):
                    query = original_build(query_parts, *args, **kwargs)
                    return self._patch_query_for_neo4j_5(query)
                
                cognee.query_builder.build_query = patched_build
                logger.info("Applied additional Neo4j 5.x query patches")
                
        except Exception as e:
            logger.warning(f"Could not apply additional Neo4j patches: {e}")
        
    async def _cognify_with_retry(self, max_retries: int = 3):
        """Process into knowledge graph with retry mechanism for Neo4j compatibility"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Apply additional patches on retry
                    self._apply_neo4j_5_query_patches()
                    
                    # Apply runtime query patching if needed
                    if hasattr(cognee, '_execute_query'):
                        original_execute = cognee._execute_query
                        
                        def patched_execute(query, *args, **kwargs):
                            patched_query = self._patch_query_for_neo4j_5(query)
                            return original_execute(patched_query, *args, **kwargs)
                        
                        cognee._execute_query = patched_execute
    
                await cognee.cognify()
                return  # Success
                
            except Exception as e:
                error_msg = str(e)
                if ("'id'" in error_msg or "deprecated" in error_msg.lower()) and attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed with Neo4j compatibility issue, retrying...")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise e

    def _register_tools(self):
        """Register tools for the Cognee knowledge ingestion agent"""
        # Define the tools this agent provides
        tools = [
            {
                "name": "ingest_document",
                "description": "Ingest a document into the knowledge graph using Cognee",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Document content to ingest"},
                        "metadata": {"type": "object", "description": "Document metadata"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "query_knowledge",
                "description": "Query the knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Query to search the knowledge graph"}
                    },
                    "required": ["query"]
                }
            }
        ]
        return tools

    # [Rest of the methods remain the same - process_query, _parse_operation, etc.]
    # ... (include all other methods from your original code)



    async def process_query(self, query, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
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
            # Handle AgentRequest object vs string
            if hasattr(query, 'query'):
                # It's an AgentRequest object
                query_text = query.query
                context = getattr(query, 'additional_context', context) or context
                session_id = getattr(query, 'session_id', None)
            else:
                # It's a string
                query_text = query
            
            # Parse the query to determine operation type
            operation = self._parse_operation(query_text, context)
            
            if operation["type"] == "ingest_file":
                return await self._handle_file_ingestion(operation["data"])
            elif operation["type"] == "ingest_source":
                return await self._handle_source_ingestion(operation["data"])
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
    
    def _parse_operation(self, query_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse the query to determine what operation to perform"""
        
        # Check context first for operation hints
        if context:
            if context.get("operation") == "ingest_source":
                return {
                    "type": "ingest_source",
                    "data": {
                        "source_path": context.get("source_path"),
                        "source_type": context.get("source_type", "file"),
                        "dataset_name": context.get("dataset_name", "default"),
                        "url": context.get("url"),
                        "title": context.get("title")
                    }
                }
            elif "file_content" in context:
                return {
                    "type": "ingest_file",
                    "data": {
                        "content": context["file_content"],
                        "filename": context.get("filename", "unknown"),
                        "dataset_name": context.get("dataset_name", "default")
                    }
                }
        
        # Check for specific query patterns
        query_lower = query_text.lower()
        
        if any(keyword in query_lower for keyword in ["search", "find", "query", "tell me about"]):
            return {
                "type": "search",
                "data": {"query": query_text}
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
                "data": {"text": query_text}
            }
    
    async def _handle_file_ingestion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file content ingestion into Cognee with error handling"""
        try:
            content = data["content"]
            filename = data["filename"]
            dataset_name = data["dataset_name"]
            
            # Wrap Cognee operations with error handling for Neo4j compatibility
            try:
                # Add content to Cognee
                await cognee.add(content, dataset_name=dataset_name)
                
                # Process into knowledge graph with retry mechanism
                await self._cognify_with_retry()
                
            except Exception as cognee_error:
                # Handle specific Neo4j compatibility errors
                if "'id'" in str(cognee_error) or "deprecated" in str(cognee_error).lower():
                    logger.warning(f"Neo4j compatibility issue detected: {cognee_error}")
                    return await self._handle_neo4j_compatibility_error(cognee_error, "file_ingestion")
                else:
                    raise cognee_error
            
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
        """Handle text ingestion into Cognee with error handling"""
        try:
            text = data["text"]
            
            # Wrap Cognee operations with error handling
            try:
                # Add text to Cognee
                await cognee.add(text)
                
                # Process into knowledge graph with retry mechanism
                await self._cognify_with_retry()
                
            except Exception as cognee_error:
                # Handle specific Neo4j compatibility errors
                if "'id'" in str(cognee_error) or "deprecated" in str(cognee_error).lower():
                    logger.warning(f"Neo4j compatibility issue detected: {cognee_error}")
                    return await self._handle_neo4j_compatibility_error(cognee_error, "text_ingestion")
                else:
                    raise cognee_error
            
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
    
    async def _handle_source_ingestion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle URL/source ingestion into Cognee knowledge graph with error handling"""
        try:
            source_path = data.get("source_path")
            source_type = data.get("source_type", "file")
            dataset_name = data.get("dataset_name", "default")
            url = data.get("url")
            title = data.get("title", "Unknown")

            logger.info(f"Processing source ingestion: URL={url}, dataset={dataset_name}")

            # Wrap Cognee operations with error handling
            try:
                # Handle URL ingestion
                if url:
                    # Add URL to Cognee for processing
                    await cognee.add(url, dataset_name=dataset_name)
                # Handle file path ingestion
                elif source_path:
                    # Add source path to Cognee
                    await cognee.add(source_path, dataset_name=dataset_name)
                else:
                    return {
                        "success": False,
                        "error": "Missing URL or source path for ingestion",
                        "agent": self.name
                    }

                # Process the content into knowledge graph with retry mechanism
                await self._cognify_with_retry()
                
            except Exception as cognee_error:
                # Handle specific Neo4j compatibility errors
                if "'id'" in str(cognee_error) or "deprecated" in str(cognee_error).lower():
                    logger.warning(f"Neo4j compatibility issue detected: {cognee_error}")
                    return await self._handle_neo4j_compatibility_error(cognee_error, "source_ingestion")
                else:
                    raise cognee_error

            logger.info(f"Successfully processed source into knowledge graph")

            return {
                "success": True,
                "message": f"Source successfully processed into knowledge graph",
                "dataset": dataset_name,
                "url": url,
                "title": title,
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"Source ingestion failed: {e}")
            return {
                "success": False,
                "error": f"Failed to process source: {str(e)}",
                "agent": self.name
            }
    
    async def _handle_neo4j_compatibility_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """Handle Neo4j compatibility errors and provide helpful information"""
        error_msg = str(error)
        
        suggestions = [
            "Update Cognee to the latest version: pip install --upgrade cognee",
            "Check if your Neo4j version is compatible with Cognee",
            "Consider downgrading Neo4j to version 4.x if using 5.x",
            "Set NEO4J_USE_ELEMENT_ID environment variable to 'true'"
        ]
        
        return {
            "success": False,
            "error": f"Neo4j compatibility issue in {operation}: {error_msg}",
            "suggestions": suggestions,
            "agent": self.name,
            "error_type": "neo4j_compatibility"
        }
    
    async def _handle_knowledge_search(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge graph search queries with error handling"""
        try:
            query = data["query"]
            
            # Search the knowledge graph with error handling
            try:
                results = await cognee.search(query)
            except Exception as search_error:
                if "'id'" in str(search_error):
                    logger.warning(f"Search compatibility issue: {search_error}")
                    return await self._handle_neo4j_compatibility_error(search_error, "search")
                else:
                    raise search_error
            
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
        """Check system status and health with improved diagnostics"""
        try:
            status_info = {
                "success": True,
                "status": "healthy",
                "agent": self.name,
                "neo4j": "unknown",
                "cognee": "unknown"
            }
            
            # Test Neo4j connection
            try:
                if self.neo4j_driver:
                    with self.neo4j_driver.session() as session:
                        result = session.run("RETURN 1 as test")
                        if result.single()["test"] == 1:
                            status_info["neo4j"] = "connected"
                else:
                    self._test_neo4j_connection()
                    status_info["neo4j"] = "connected"
            except Exception as neo4j_error:
                status_info["neo4j"] = f"error: {str(neo4j_error)}"
                status_info["success"] = False
            
            # Test Cognee functionality
            try:
                await cognee.add("health_check_test")
                status_info["cognee"] = "functional"
            except Exception as cognee_error:
                status_info["cognee"] = f"error: {str(cognee_error)}"
                if "'id'" in str(cognee_error):
                    status_info["cognee"] += " (Neo4j compatibility issue)"
                status_info["success"] = False
            
            if not status_info["success"]:
                status_info["status"] = "unhealthy"
            
            return status_info
            
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
    

    # LiteLLM logging suppressor
    def configure_litellm_silently():
        
        """Full-stack LiteLLM logging configuration"""
        import logging
        import litellm
        
        # Disable verbose mode at multiple levels
        litellm.set_verbose = False
        litellm.verbose = False
        litellm.logging = False
        
        # Configure root logger first
        logging.getLogger().setLevel(logging.WARNING)
        
        # LiteLLM module-specific configurations
        modules = [
            "litellm", "litellm.llms", "litellm.utils",
            "litellm.cost_calculator", "litellm.proxy"
        ]
        
        for module in modules:
            logger = logging.getLogger(module)
            logger.setLevel(logging.ERROR)
            logger.propagate = False  # Prevent handler duplication
        
        # Disable cost tracking features
        os.environ["LITELLM_DISABLE_COST_CALCULATION"] = "true"
        os.environ["LITELLM_DISABLE_SPEND_LOGS"] = "true"
        os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "false"
     

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
            "Knowledge graph querying",
            "Neo4j compatibility handling"
        ]
    
    def __del__(self):
        """Clean up Neo4j driver connection"""
        if self.neo4j_driver:
            try:
                self.neo4j_driver.close()
            except Exception:
                pass  # Ignore cleanup errors