"""
Realistic Voice AI Assistant - Single Server Production Ready
Everything in one place: voice processing, knowledge base, API, and frontend
"""

import os
import json
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import hmac
import asyncio

# Configure logging first, before any other code that might use it
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Try .env first
    # Also try config.env if it exists
    config_env_path = Path("config.env")
    if config_env_path.exists():
        load_dotenv(config_env_path)
        logger.info("Loaded configuration from config.env")
    # Load Neo4j MCP configuration
    neo4j_config_path = Path("neo4j_mcp_config.env")
    if neo4j_config_path.exists():
        load_dotenv(neo4j_config_path)
        logger.info("Loaded Neo4j MCP configuration from neo4j_mcp_config.env")
except ImportError:
    pass  # python-dotenv not available

from fastapi import FastAPI, HTTPException, status, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

# OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("openai not available, using simple responses")

# Voice processing
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("faster-whisper not available, using mock transcription")

# Neo4j integration
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("neo4j not available, using simple graph storage")

# Agent framework integration
try:
    from agents.orchestrator import create_orchestrator
    from agents.base import AgentRequest, AgentResponse
    from services.conversation_memory import ConversationMemoryService
    # Neo4j MCP conversation memory (optional)
    try:
        from services.neo4j_conversation_memory import Neo4jMCPConversationMemoryService
        NEO4J_MCP_AVAILABLE = True
    except ImportError:
        NEO4J_MCP_AVAILABLE = False
        print("Neo4j MCP conversation memory not available, using file-based storage")
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    print("PydanticAI agents not available, using fallback responses")
    
    # Define fallback classes for type hints when imports fail
    class AgentRequest(BaseModel):
        query: str
        session_id: Optional[str] = None
        
    class AgentResponse(BaseModel):
        query: str
        response: str
        agent_name: str = "Fallback Agent"
        confidence: float = 0.0
        session_id: Optional[str] = None
        processing_time: float = 0.0

# Configuration
class Config:
    PORT = int(os.getenv("PORT", "8080"))
    JWT_SECRET = os.getenv("JWT_SECRET", "realistic-voice-ai-secret-change-in-production")
    DATA_DIR = Path("data")
    FRONTEND_DIR = Path("frontend/build")  # React build directory
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Neo4j configuration (use Neo4j Aura for production)
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Conversation Memory Configuration
    # Re-enable Neo4j MCP now that mcp-neo4j-memory is properly installed
    USE_NEO4J_MCP = os.getenv("USE_NEO4J_MCP", "true").lower() in ("true", "1", "yes")
    # USE_NEO4J_MCP = False  # Force disable for now
    
    # Create data directories
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "knowledge").mkdir(exist_ok=True)
    (DATA_DIR / "users").mkdir(exist_ok=True)
    (DATA_DIR / "sessions").mkdir(exist_ok=True)
    (DATA_DIR / "graph").mkdir(exist_ok=True)

# Data Models
class QueryRequest(BaseModel):
    query: str = Field(..., max_length=500)
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    response: str
    session_id: str
    confidence: float
    processing_time: float
    timestamp: datetime
    relationships: Optional[Dict[str, Any]] = {}
    agents_consulted: Optional[List[str]] = []
    tools_used: Optional[List[str]] = []
    reasoning_approach: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    user_info: Dict[str, Any]
    expires_in: int

# Simple File-Based Storage
class SimpleStorage:
    def __init__(self):
        self.DATA_DIR = Config.DATA_DIR  # Add DATA_DIR attribute for conversation memory
        self.users_file = Config.DATA_DIR / "users" / "users.json"
        self.knowledge_file = Config.DATA_DIR / "knowledge" / "knowledge.json"
        self.sessions_file = Config.DATA_DIR / "sessions" / "sessions.json"
        
        # Initialize files if they don't exist
        self._init_users()
        self._init_knowledge()
        self._init_sessions()
    
    def _init_users(self):
        if not self.users_file.exists():
            users = {
                "demo": {
                    "password_hash": self._hash_password("demo123"),
                    "email": "demo@example.com",
                    "full_name": "Demo User",
                    "created_at": datetime.now().isoformat()
                }
            }
            self._save_json(self.users_file, users)
    
    def _init_knowledge(self):
        if not self.knowledge_file.exists():
            knowledge = {
                "voice ai assistant": "A conversational AI system that processes voice input and provides intelligent responses using speech recognition and natural language processing.",
                "faster whisper": "An optimized implementation of OpenAI's Whisper model for fast and accurate speech recognition.",
                "speech recognition": "Technology that converts spoken language into text, enabling voice-based interactions with computer systems.",
                "natural language processing": "A field of AI that helps computers understand, interpret and generate human language in a valuable way.",
                "fastapi": "A modern, fast web framework for building APIs with Python based on standard Python type hints."
            }
            self._save_json(self.knowledge_file, knowledge)
    
    def _init_sessions(self):
        if not self.sessions_file.exists():
            self._save_json(self.sessions_file, {})
    
    def _load_json(self, file_path: Path) -> Dict:
        try:
            return json.loads(file_path.read_text())
        except:
            return {}
    
    def _save_json(self, file_path: Path, data: Dict):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2, default=str))
    
    def _hash_password(self, password: str) -> str:
        return hmac.new(
            Config.JWT_SECRET.encode(),
            password.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        users = self._load_json(self.users_file)
        user = users.get(username)
        
        if user and hmac.compare_digest(self._hash_password(password), user["password_hash"]):
            return {
                "username": username,
                "email": user["email"],
                "full_name": user["full_name"]
            }
        return None
    
    def create_token(self, user_info: Dict[str, Any]) -> str:
        payload = {
            "user": user_info,
            "exp": time.time() + 86400,  # 24 hours
            "iat": time.time()
        }
        token = hmac.new(
            Config.JWT_SECRET.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Store session
        sessions = self._load_json(self.sessions_file)
        sessions[token] = payload
        self._save_json(self.sessions_file, sessions)
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        sessions = self._load_json(self.sessions_file)
        session = sessions.get(token)
        
        if session and session["exp"] > time.time():
            return session["user"]
        return None
    
    def search_knowledge(self, query: str) -> Dict[str, Any]:
        """Simple fallback knowledge search (replaced by agentic reasoning)"""
        # This is now just a fallback - the main intelligence comes from agents
        return {
            "response": "I'm currently using advanced AI reasoning to help you. If you're seeing this message, please try rephrasing your question or contact support.",
            "confidence": 0.2,
            "source": "fallback_knowledge"
        }

# Graph Intelligence (Neo4j MCP integration)
class GraphIntelligence:
    def __init__(self):
        self.driver = None
        self.graph_file = Config.DATA_DIR / "graph" / "relationships.json"
        
        if NEO4J_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(
                    Config.NEO4J_URI,
                    auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
                )
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                logger.info("Connected to Neo4j successfully")
                self._init_neo4j_data()
            except Exception as e:
                logger.warning(f"Failed to connect to Neo4j: {e}, using simple graph storage")
                self.driver = None
        
        if not self.driver:
            self._init_simple_graph()
    
    def _init_neo4j_data(self):
        """Initialize Neo4j with basic Voice AI Assistant data"""
        with self.driver.session() as session:
            # Create Voice AI Assistant node and relationships
            session.run("""
                MERGE (assistant:Product {name: 'Voice AI Assistant'})
                MERGE (whisper:Technology {name: 'Faster Whisper'})
                MERGE (fastapi:Technology {name: 'FastAPI'})
                MERGE (speech:Feature {name: 'Speech Recognition'})
                MERGE (ai:Feature {name: 'AI Response'})
                
                MERGE (assistant)-[:USES]->(whisper)
                MERGE (assistant)-[:BUILT_WITH]->(fastapi)
                MERGE (assistant)-[:PROVIDES]->(speech)
                MERGE (assistant)-[:PROVIDES]->(ai)
                MERGE (whisper)-[:ENABLES]->(speech)
            """)
    
    def _init_simple_graph(self):
        """Initialize simple JSON-based graph storage"""
        if not self.graph_file.exists():
            graph_data = {
                "nodes": [
                    {"id": "voice_ai_assistant", "type": "Product", "name": "Voice AI Assistant"},
                    {"id": "faster_whisper", "type": "Technology", "name": "Faster Whisper"},
                    {"id": "fastapi", "type": "Technology", "name": "FastAPI"},
                    {"id": "speech_recognition", "type": "Feature", "name": "Speech Recognition"},
                    {"id": "ai_response", "type": "Feature", "name": "AI Response"}
                ],
                "relationships": [
                    {"from": "voice_ai_assistant", "to": "faster_whisper", "type": "USES"},
                    {"from": "voice_ai_assistant", "to": "fastapi", "type": "BUILT_WITH"},
                    {"from": "voice_ai_assistant", "to": "speech_recognition", "type": "PROVIDES"},
                    {"from": "voice_ai_assistant", "to": "ai_response", "type": "PROVIDES"},
                    {"from": "faster_whisper", "to": "speech_recognition", "type": "ENABLES"}
                ]
            }
            self.graph_file.parent.mkdir(parents=True, exist_ok=True)
            self.graph_file.write_text(json.dumps(graph_data, indent=2))
    
    def find_relationships(self, entity: str, depth: int = 1) -> Dict[str, Any]:
        """Find relationships for an entity"""
        if self.driver:
            return self._neo4j_find_relationships(entity, depth)
        else:
            return self._simple_find_relationships(entity, depth)
    
    def _neo4j_find_relationships(self, entity: str, depth: int) -> Dict[str, Any]:
        """Find relationships using Neo4j"""
        with self.driver.session() as session:
            query = """
                MATCH (n)-[r]-(connected)
                WHERE toLower(n.name) CONTAINS toLower($entity)
                RETURN n.name as entity, type(r) as relationship, connected.name as connected_entity
                LIMIT 10
            """
            result = session.run(query, entity=entity)
            
            relationships = []
            for record in result:
                relationships.append({
                    "entity": record["entity"],
                    "relationship": record["relationship"],
                    "connected_entity": record["connected_entity"]
                })
            
            return {
                "source": "neo4j",
                "relationships": relationships,
                "count": len(relationships)
            }
    
    def _simple_find_relationships(self, entity: str, depth: int) -> Dict[str, Any]:
        """Find relationships using simple JSON storage"""
        try:
            graph_data = json.loads(self.graph_file.read_text())
        except:
            return {"source": "simple", "relationships": [], "count": 0}
        
        entity_lower = entity.lower()
        relationships = []
        
        # Find matching nodes
        matching_nodes = [
            node for node in graph_data["nodes"]
            if entity_lower in node["name"].lower()
        ]
        
        # Find relationships for matching nodes
        for node in matching_nodes:
            for rel in graph_data["relationships"]:
                if rel["from"] == node["id"]:
                    # Find target node
                    target_node = next(
                        (n for n in graph_data["nodes"] if n["id"] == rel["to"]), 
                        None
                    )
                    if target_node:
                        relationships.append({
                            "entity": node["name"],
                            "relationship": rel["type"],
                            "connected_entity": target_node["name"]
                        })
        
        return {
            "source": "simple",
            "relationships": relationships,
            "count": len(relationships)
        }
    
    def add_relationship(self, from_entity: str, to_entity: str, relationship_type: str):
        """Add a new relationship"""
        if self.driver:
            self._neo4j_add_relationship(from_entity, to_entity, relationship_type)
        else:
            self._simple_add_relationship(from_entity, to_entity, relationship_type)
    
    def _neo4j_add_relationship(self, from_entity: str, to_entity: str, relationship_type: str):
        """Add relationship to Neo4j"""
        with self.driver.session() as session:
            session.run("""
                MERGE (from:Entity {name: $from_entity})
                MERGE (to:Entity {name: $to_entity})
                MERGE (from)-[r:""" + relationship_type + """]->(to)
            """, from_entity=from_entity, to_entity=to_entity)
    
    def _simple_add_relationship(self, from_entity: str, to_entity: str, relationship_type: str):
        """Add relationship to simple storage"""
        try:
            graph_data = json.loads(self.graph_file.read_text())
        except:
            graph_data = {"nodes": [], "relationships": []}
        
        # Add nodes if they don't exist
        from_id = from_entity.lower().replace(" ", "_")
        to_id = to_entity.lower().replace(" ", "_")
        
        if not any(n["id"] == from_id for n in graph_data["nodes"]):
            graph_data["nodes"].append({
                "id": from_id,
                "type": "Entity",
                "name": from_entity
            })
        
        if not any(n["id"] == to_id for n in graph_data["nodes"]):
            graph_data["nodes"].append({
                "id": to_id,
                "type": "Entity", 
                "name": to_entity
            })
        
        # Add relationship
        graph_data["relationships"].append({
            "from": from_id,
            "to": to_id,
            "type": relationship_type
        })
        
        self.graph_file.write_text(json.dumps(graph_data, indent=2))
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()

# Voice Processing
class VoiceProcessor:
    def __init__(self):
        self.model = None
        if WHISPER_AVAILABLE:
            try:
                self.model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Faster Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                self.model = None
    
    def transcribe(self, audio_file_path: str, language: str = "en") -> Dict[str, Any]:
        start_time = time.time()
        
        if self.model:
            try:
                segments, info = self.model.transcribe(
                    audio_file_path,
                    language=language if language != "auto" else None,
                    beam_size=5
                )
                
                text = " ".join([segment.text for segment in segments])
                
                return {
                    "text": text.strip(),
                    "language": info.language,
                    "confidence": 0.9,
                    "processing_time": time.time() - start_time
                }
            except Exception as e:
                logger.error(f"Transcription error: {e}")
        
        # Fallback for demo
        return {
            "text": "This is a demo transcription since Faster Whisper is not available.",
            "language": language,
            "confidence": 0.5,
            "processing_time": time.time() - start_time
        }

# AI Response Service
class AIResponseService:
    def __init__(self):
        self.client = None
        self.model = Config.OPENAI_MODEL
        
        if OPENAI_AVAILABLE and Config.OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI not available - using fallback responses")
    
    def generate_response(self, query: str, context: str = "", relationships: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        if self.client:
            return self._openai_response(query, context, relationships)
        else:
            return self._fallback_response(query, context)
    
    def _openai_response(self, query: str, context: str, relationships: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        start_time = time.time()
        
        try:
            # Build system prompt with context
            system_prompt = self._build_system_prompt(context, relationships)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            return {
                "response": ai_response,
                "confidence": 0.9,
                "source": "openai",
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._fallback_response(query, context)
    
    def _build_system_prompt(self, context: str, relationships: Dict[str, Any]) -> str:
        """Build system prompt with knowledge base context and relationships"""
        prompt = """You are a helpful Voice AI Assistant with expertise in voice technology, AI, and software development. 

Your knowledge base includes:
- Voice AI systems and speech recognition
- FastAPI web development
- Faster Whisper speech processing
- Neo4j graph databases
- Natural language processing

"""
        
        if context:
            prompt += f"Relevant context from knowledge base:\n{context}\n\n"
        
        if relationships and any(rel.get("relationships") for rel in relationships.values()):
            prompt += "Related concepts from the knowledge graph:\n"
            for entity, rel_data in relationships.items():
                if rel_data.get("relationships"):
                    prompt += f"- {entity} connections: "
                    connections = [r["connected_entity"] for r in rel_data["relationships"][:3]]
                    prompt += ", ".join(connections) + "\n"
            prompt += "\n"
        
        prompt += """Please provide helpful, accurate, and conversational responses. If you don't know something specific, say so rather than making up information. Keep responses concise but informative."""
        
        return prompt
    
    def _fallback_response(self, query: str, context: str) -> Dict[str, Any]:
        """Fallback response when OpenAI is not available"""
        start_time = time.time()
        processing_time = 0.1
        
        if context:
            return {
                "response": f"Based on the available information: {context}",
                "confidence": 0.7,
                "source": "fallback_with_context",
                "processing_time": processing_time
            }
        
        return {
            "response": "I'm a Voice AI Assistant, but I need more context to provide a specific answer. Could you tell me more about what you're looking for?",
            "confidence": 0.3,
            "source": "fallback",
            "processing_time": processing_time
        }

# Agent Management System
class AgentManager:
    """Manager for agentic AI processing with conversation memory"""
    
    def __init__(self, openai_client, storage_service, graph_intelligence):
        self.openai_client = openai_client
        self.storage_service = storage_service
        self.graph_intelligence = graph_intelligence
        
        # Initialize conversation memory service with proper error handling
        logger.info(f"USE_NEO4J_MCP setting: {Config.USE_NEO4J_MCP}")
        
        if Config.USE_NEO4J_MCP:
            logger.info("Attempting to initialize Neo4j MCP conversation memory...")
            try:
                from services.neo4j_conversation_memory import Neo4jMCPConversationMemoryService
                
                # Initialize the service
                temp_memory = Neo4jMCPConversationMemoryService(storage_service.DATA_DIR)
                
                # Test if the MCP agent is properly initialized
                if hasattr(temp_memory, 'agent') and temp_memory.agent is not None:
                    logger.info("Neo4j MCP conversation memory initialized successfully")
                    self.conversation_memory = temp_memory
                else:
                    logger.warning("Neo4j MCP agent not available, falling back to regular conversation memory")
                    from services.conversation_memory import ConversationMemoryService
                    self.conversation_memory = ConversationMemoryService(storage_service.DATA_DIR)
                    
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j MCP conversation memory: {e}")
                logger.info("Falling back to regular conversation memory")
                from services.conversation_memory import ConversationMemoryService
                self.conversation_memory = ConversationMemoryService(storage_service.DATA_DIR)
        else:
            logger.info("Using regular file-based conversation memory")
            from services.conversation_memory import ConversationMemoryService
            self.conversation_memory = ConversationMemoryService(storage_service.DATA_DIR)
        
        # Initialize orchestrator with conversation memory
        if openai_client:
            try:
                from agents.orchestrator import create_orchestrator
                self.orchestrator = create_orchestrator(
                    openai_client=openai_client,
                    storage_service=storage_service,
                    graph_intelligence=graph_intelligence,
                    conversation_memory=self.conversation_memory
                )
                logger.info("Agent orchestrator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize agent orchestrator: {e}")
                self.orchestrator = None
                self.conversation_memory = ConversationMemoryService(storage_service.DATA_DIR)
        else:
            self.orchestrator = None
            self.conversation_memory = ConversationMemoryService(storage_service.DATA_DIR)
    
    async def process_query(self, request: AgentRequest) -> AgentResponse:
        """Process query using agentic orchestrator"""
        if self.orchestrator:
            return await self.orchestrator.process_query(request)
        else:
            # Fallback response
            return AgentResponse(
                query=request.query,
                response="I'm a Voice AI Assistant. I can help you with loan inquiries, but my advanced capabilities are currently unavailable.",
                agent_name="Fallback Agent",
                session_id=request.session_id or f"session_{int(time.time())}",
                confidence=0.3,
                processing_time=0.1,
                timestamp=datetime.now(),
                tools_used=[],
                context_used={},
                follow_up_suggestions=[]
            )
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent capabilities"""
        if self.orchestrator:
            return [
                "orchestrator", 
                "loan_advisor", 
                "market_researcher", 
                "application_assistant", 
                "document_processor", 
                "compliance_checker",
                "knowledge_ingestion",
                "rl_optimizer"
            ]
        return ["fallback"]
    
    async def cleanup_memory(self):
        """Clean up expired conversation contexts"""
        if self.conversation_memory:
            # Handle both async and sync cleanup methods
            if hasattr(self.conversation_memory, 'cleanup_expired_contexts'):
                if asyncio.iscoroutinefunction(self.conversation_memory.cleanup_expired_contexts):
                    await self.conversation_memory.cleanup_expired_contexts()
                else:
                    self.conversation_memory.cleanup_expired_contexts()

# Global instances
storage = SimpleStorage()
voice_processor = VoiceProcessor()
graph_intelligence = GraphIntelligence()
ai_service = AIResponseService()

# Initialize agent manager with OpenAI client
if AGENTS_AVAILABLE and ai_service.client:
    agent_manager = AgentManager(
        openai_client=ai_service.client,
        storage_service=storage,
        graph_intelligence=graph_intelligence
    )
else:
    agent_manager = None

security = HTTPBearer(auto_error=False)

# FastAPI app
app = FastAPI(
    title="Realistic Voice AI Assistant",
    description="Single-server voice AI with speech recognition and knowledge base",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    return storage.verify_token(credentials.credentials)

# API Routes
@app.get("/")
async def root():
    return {
        "service": "Realistic Voice AI Assistant",
        "version": "1.0.0",
        "description": "Single-server voice AI with all functionality integrated",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "login": "/auth/login",
            "query": "/query",
            "voice_query": "/voice-query",
            "transcribe": "/transcribe"
        }
    }

@app.get("/health")
async def health_check():
    # Clean up expired conversation contexts during health check
    if agent_manager:
        await agent_manager.cleanup_memory()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services": {
            "api": "healthy",
            "storage": "healthy",
            "voice_processor": "healthy" if voice_processor.model else "mock",
            "knowledge_base": "healthy",
            "ai_service": "openai" if ai_service.client else "fallback",
            "graph_intelligence": "neo4j" if graph_intelligence.driver else "simple",
            "agents": "available" if agent_manager and agent_manager.orchestrator else "fallback",
            "conversation_memory": "active" if agent_manager and agent_manager.conversation_memory else "disabled"
        },
        "available_agents": agent_manager.get_available_agents() if agent_manager else [],
        "memory_status": {
            "active_contexts": len(agent_manager.conversation_memory.active_contexts) if agent_manager and agent_manager.conversation_memory else 0,
            "context_timeout_hours": 2
        }
    }

@app.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = storage.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = storage.create_token(user)
    return AuthResponse(
        access_token=token,
        user_info=user,
        expires_in=86400
    )

@app.post("/query", response_model=QueryResponse)
async def query_ai(
    request: QueryRequest,
    use_agent: bool = True,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    start_time = time.time()
    # Improved session ID handling - use provided session_id or create a stable fallback
    session_id = request.session_id
    if not session_id:
        # Create a more stable session ID for anonymous users
        user_identifier = current_user.get('username', 'anonymous') if current_user else 'anonymous'
        session_id = f"session_{user_identifier}_{int(start_time // 3600)}"  # Hour-based session for anonymous users
    
    # Try using agent system first (if enabled and available)
    if use_agent and agent_manager and agent_manager.orchestrator:
        try:
            agent_request = AgentRequest(
                query=request.query,
                session_id=session_id,
                user_context=current_user or {},
                voice_input=False
            )
            
            agent_response = await agent_manager.process_query(agent_request)
            
            # Convert agent response to standard QueryResponse format
            return QueryResponse(
                query=agent_response.query,
                response=agent_response.response,
                session_id=agent_response.session_id,
                confidence=agent_response.confidence,
                processing_time=agent_response.processing_time,
                timestamp=agent_response.timestamp,
                relationships=agent_response.context_used.get("relationships", {}),
                agents_consulted=agent_response.context_used.get("agents_consulted", []),
                tools_used=agent_response.tools_used,
                reasoning_approach=agent_response.context_used.get("reasoning_approach")
            )
            
        except Exception as e:
            logger.warning(f"Agent processing failed, falling back to legacy system: {e}")
    
    # Fallback to original system (backward compatibility)
    # Search knowledge base for context
    kb_result = storage.search_knowledge(request.query)
    context = kb_result.get("response", "") if kb_result.get("source") != "fallback" else ""
    
    # Extract entities and find relationships
    entities = _extract_entities(request.query)
    relationships = {}
    
    if entities:
        for entity in entities[:3]:  # Limit to top 3 entities
            entity_relationships = graph_intelligence.find_relationships(entity)
            if entity_relationships.get("relationships"):
                relationships[entity] = entity_relationships
    
    # Generate AI response with context and relationships
    ai_result = ai_service.generate_response(
        query=request.query,
        context=context,
        relationships=relationships
    )
    
    processing_time = time.time() - start_time
    
    return QueryResponse(
        query=request.query,
        response=ai_result["response"],
        session_id=session_id,
        confidence=ai_result["confidence"],
        processing_time=processing_time,
        timestamp=datetime.now(),
        relationships=relationships,
        agents_consulted=[],
        tools_used=[],
        reasoning_approach=None
    )

def _extract_entities(query: str) -> List[str]:
    """Simple entity extraction from query"""
    entities = []
    query_lower = query.lower()
    
    # Common entities to look for
    entity_keywords = {
        "voice ai assistant": ["voice", "assistant", "ai"],
        "faster whisper": ["whisper", "speech", "recognition"],
        "fastapi": ["fastapi", "api", "web"],
        "speech recognition": ["speech", "recognition", "transcribe"],
        "ai response": ["ai", "response", "answer"]
    }
    
    for entity, keywords in entity_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            entities.append(entity)
    
    return entities

@app.post("/voice-query", response_model=QueryResponse)
async def voice_query(
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = None,
    language: str = "en",
    use_agent: bool = True,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.filename.split('.')[-1]}") as temp_file:
        content = await audio_file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Transcribe audio
        transcription = voice_processor.transcribe(temp_file_path, language)
        # Improved session ID handling for voice queries
        if not session_id:
            user_identifier = current_user.get('username', 'anonymous') if current_user else 'anonymous'  
            session_id = f"session_{user_identifier}_{int(time.time() // 3600)}"  # Hour-based session
        
        # Try using agent system first (if enabled and available)
        if use_agent and agent_manager and agent_manager.orchestrator:
            try:
                agent_request = AgentRequest(
                    query=transcription["text"],
                    session_id=session_id,
                    user_context=current_user or {},
                    voice_input=True
                )
                
                agent_response = await agent_manager.process_query(agent_request)
                
                # Convert agent response to standard QueryResponse format
                return QueryResponse(
                    query=agent_response.query,
                    response=agent_response.response,
                    session_id=agent_response.session_id,
                    confidence=min(transcription["confidence"], agent_response.confidence),
                    processing_time=transcription["processing_time"] + agent_response.processing_time,
                    timestamp=agent_response.timestamp,
                    relationships=agent_response.context_used.get("relationships", {}),
                    agents_consulted=agent_response.context_used.get("agents_consulted", []),
                    tools_used=agent_response.tools_used,
                    reasoning_approach=agent_response.context_used.get("reasoning_approach")
                )
                
            except Exception as e:
                logger.warning(f"Agent processing failed for voice query, falling back: {e}")
        
        # Fallback to original system (backward compatibility)
        # Search knowledge base for context
        kb_result = storage.search_knowledge(transcription["text"])
        context = kb_result.get("response", "") if kb_result.get("source") != "fallback" else ""
        
        # Extract entities and find relationships
        entities = _extract_entities(transcription["text"])
        relationships = {}
        
        if entities:
            for entity in entities[:3]:  # Limit to top 3 entities
                entity_relationships = graph_intelligence.find_relationships(entity)
                if entity_relationships.get("relationships"):
                    relationships[entity] = entity_relationships
        
        # Generate AI response with context and relationships
        ai_result = ai_service.generate_response(
            query=transcription["text"],
            context=context,
            relationships=relationships
        )
        
        processing_time = transcription["processing_time"] + ai_result.get("processing_time", 0)
        
        return QueryResponse(
            query=transcription["text"],
            response=ai_result["response"],
            session_id=session_id,
            confidence=min(transcription["confidence"], ai_result["confidence"]),
            processing_time=processing_time,
            timestamp=datetime.now(),
            relationships=relationships,
            agents_consulted=[],
            tools_used=[],
            reasoning_approach=None
        )
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

@app.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language: str = "en"
):
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.filename.split('.')[-1]}") as temp_file:
        content = await audio_file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        transcription = voice_processor.transcribe(temp_file_path, language)
        return transcription
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

# New endpoint for direct relationship queries
@app.get("/relationships/{entity}")
async def get_relationships(entity: str, depth: int = 1):
    """Get relationships for a specific entity"""
    relationships = graph_intelligence.find_relationships(entity, depth)
    return {
        "entity": entity,
        "depth": depth,
        **relationships
    }

@app.post("/relationships")
async def add_relationship(
    from_entity: str,
    to_entity: str, 
    relationship_type: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Add a new relationship (authenticated users only)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to add relationships"
        )
    
    graph_intelligence.add_relationship(from_entity, to_entity, relationship_type)
    return {
        "message": "Relationship added successfully",
        "from_entity": from_entity,
        "to_entity": to_entity,
        "relationship_type": relationship_type
    }

# New Agent-Specific Endpoint
@app.post("/agent/query", response_model=AgentResponse)
async def agent_query(
    request: AgentRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Direct agent query endpoint with full agent response format"""
    if not agent_manager or not agent_manager.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent system not available"
        )
    
    # Add user context from authentication
    if current_user:
        request.user_context.update(current_user)
    
    try:
        return await agent_manager.process_query(request)
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent processing failed"
        )

@app.get("/agents")
async def list_agents():
    """List available AI agents and their capabilities"""
    if agent_manager and agent_manager.orchestrator:
        return {
            "status": "success",
            "agents": {
                "orchestrator": "Main coordination agent with multi-step reasoning",
                "loan_advisor": "Personalized loan recommendations and advice",
                "market_researcher": "Real-time market analysis and competitor insights",
                "application_assistant": "Step-by-step application guidance",
                "document_processor": "Document analysis and verification",
                "compliance_checker": "Regulatory compliance and risk assessment",
                "knowledge_ingestion": "Continuous learning from real-world data sources",
                "rl_optimizer": "Reinforcement learning-based conversation optimization"
            },
            "orchestrator_available": True,
            "memory_service": "active" if agent_manager.conversation_memory else "disabled"
        }
    else:
        return {
            "status": "limited",
            "agents": {
                "fallback": "Basic response generation without advanced capabilities"
            },
            "orchestrator_available": False,
            "memory_service": "disabled"
        }

@app.post("/rl/strategy", response_model=AgentResponse)
async def select_rl_strategy(
    customer_profile: Dict[str, Any],
    session_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Select optimal conversation strategy using RL optimization"""
    if not agent_manager or not agent_manager.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RL optimization service not available"
        )
    
    try:
        # Create request for RL strategy selection
        request = AgentRequest(
            query="select optimal strategy for customer",
            session_id=session_id or f"rl_strategy_{int(time.time())}",
            user_context=customer_profile,
            additional_context={"operation": "strategy_selection"}
        )
        
        # Get RL optimizer agent directly
        rl_agent = agent_manager.orchestrator.specialist_agents.get("rl_optimizer")
        if not rl_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RL optimizer agent not available"
            )
        
        # Process strategy selection
        response = await rl_agent.process_query(request)
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RL strategy selection failed: {str(e)}"
        )

@app.post("/rl/track-outcome")
async def track_conversation_outcome(
    session_id: str,
    outcome_data: Dict[str, Any],
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Track conversation outcome for RL learning"""
    if not agent_manager or not agent_manager.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RL optimization service not available"
        )
    
    try:
        # Create request for outcome tracking
        request = AgentRequest(
            query="track outcome for completed conversation",
            session_id=session_id,
            additional_context=outcome_data
        )
        
        # Get RL optimizer agent directly
        rl_agent = agent_manager.orchestrator.specialist_agents.get("rl_optimizer")
        if not rl_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RL optimizer agent not available"
            )
        
        # Process outcome tracking
        response = await rl_agent.process_query(request)
        
        return {
            "status": "success",
            "message": "Conversation outcome tracked successfully",
            "session_id": session_id,
            "reward_earned": response.context_used.get("reward_earned", 0),
            "learning_impact": "This outcome will improve future strategy selection"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outcome tracking failed: {str(e)}"
        )

@app.get("/rl/performance")
async def get_rl_performance(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get RL performance analysis and learning insights"""
    if not agent_manager or not agent_manager.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RL optimization service not available"
        )
    
    try:
        # Create request for performance analysis
        request = AgentRequest(
            query="analyze performance and show results",
            session_id=f"performance_analysis_{int(time.time())}"
        )
        
        # Get RL optimizer agent directly
        rl_agent = agent_manager.orchestrator.specialist_agents.get("rl_optimizer")
        if not rl_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RL optimizer agent not available"
            )
        
        # Process performance analysis
        response = await rl_agent.process_query(request)
        
        return {
            "status": "success",
            "analysis": response.response,
            "total_conversations": response.context_used.get("total_conversations", 0),
            "conversion_rate": response.context_used.get("conversion_rate", 0),
            "learning_status": "active" if response.context_used.get("total_conversations", 0) > 0 else "building"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance analysis failed: {str(e)}"
        )

@app.post("/rl/start-conversation")
async def start_rl_conversation(
    customer_profile: Dict[str, Any],
    session_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Initialize RL tracking for a new conversation"""
    if not agent_manager or not agent_manager.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RL optimization service not available"
        )
    
    try:
        session_id = session_id or f"rl_conversation_{int(time.time())}"
        
        # Create request for conversation initialization
        request = AgentRequest(
            query="initialize session for new customer conversation",
            session_id=session_id,
            user_context=customer_profile
        )
        
        # Get RL optimizer agent directly
        rl_agent = agent_manager.orchestrator.specialist_agents.get("rl_optimizer")
        if not rl_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RL optimizer agent not available"
            )
        
        # Process conversation initialization
        response = await rl_agent.process_query(request)
        
        return {
            "status": "success",
            "message": "RL conversation tracking initialized",
            "session_id": session_id,
            "recommended_strategy": response.context_used.get("selected_strategy", {}),
            "tracking_active": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RL conversation initialization failed: {str(e)}"
        )

# New endpoints for conversation memory management
@app.get("/memory/insights/{user_id}")
async def get_user_insights(
    user_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get user insights and conversation patterns"""
    if not agent_manager or not agent_manager.conversation_memory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation memory not available"
        )
    
    # Handle both async and sync conversation memory services
    if hasattr(agent_manager.conversation_memory, 'get_user_insights') and \
       hasattr(agent_manager.conversation_memory.get_user_insights, '__call__'):
        # Check if it's an async method
        if asyncio.iscoroutinefunction(agent_manager.conversation_memory.get_user_insights):
            insights = await agent_manager.conversation_memory.get_user_insights(user_id)
        else:
            insights = agent_manager.conversation_memory.get_user_insights(user_id)
    else:
        insights = {}
    
    return {
        "user_id": user_id,
        "insights": insights,
        "timestamp": datetime.now()
    }

@app.get("/memory/context/{session_id}")
async def get_conversation_context(
    session_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get conversation context for a session"""
    if not agent_manager or not agent_manager.conversation_memory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation memory not available"
        )
    
    # Handle both async and sync conversation memory services
    if hasattr(agent_manager.conversation_memory, 'get_conversation_context') and \
       hasattr(agent_manager.conversation_memory.get_conversation_context, '__call__'):
        # Check if it's an async method
        if asyncio.iscoroutinefunction(agent_manager.conversation_memory.get_conversation_context):
            context = await agent_manager.conversation_memory.get_conversation_context(session_id)
        else:
            context = agent_manager.conversation_memory.get_conversation_context(session_id)
    else:
        context = None
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {
        "session_id": session_id,
        "context": {
            "current_topic": context.current_topic,
            "context_summary": context.context_summary,
            "conversation_turns": len(context.conversation_history),
            "last_activity": context.last_activity,
            "user_profile_completeness": agent_manager.conversation_memory._calculate_profile_completeness(context.user_profile)
        },
        "timestamp": datetime.now()
    }

@app.post("/memory/cleanup")
async def cleanup_memory(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Manually trigger memory cleanup"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if not agent_manager or not agent_manager.conversation_memory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation memory not available"
        )
    
    before_count = len(agent_manager.conversation_memory.active_contexts)
    
    # Handle both async and sync cleanup methods
    if hasattr(agent_manager, 'cleanup_memory'):
        if asyncio.iscoroutinefunction(agent_manager.cleanup_memory):
            await agent_manager.cleanup_memory()
        else:
            agent_manager.cleanup_memory()
    
    after_count = len(agent_manager.conversation_memory.active_contexts)
    
    return {
        "message": "Memory cleanup completed",
        "contexts_before": before_count,
        "contexts_after": after_count,
        "contexts_cleaned": before_count - after_count,
        "timestamp": datetime.now()
    }

# Serve React frontend (if available)
if Config.FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=Config.FRONTEND_DIR / "static"), name="static")
    
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = Config.FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(Config.FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=True
    ) 