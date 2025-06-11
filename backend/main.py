import os
import json
import base64
import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

# Speech recognition imports
from faster_whisper import WhisperModel
from tempfile import NamedTemporaryFile
import numpy as np

# Graphiti imports
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EntityNode
from graphiti_core.edges import EntityEdge

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Import application modules
from knowledge_feedback import answer_with_knowledge_feedback, handle_knowledge_gap
from data_ingestion import DataIngestion
from query_handler import QueryHandler
from config import get_settings, Settings
from graphiti_advanced import GraphitiAdvanced, KnowledgeDomain

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_settings().LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Voice-to-Text AI Assistant",
    description="A conversational agent that understands voice input and produces natural language responses with the ability to handle ambiguous and multi-intent queries",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Graphiti client
def get_graphiti(settings: Settings = Depends(get_settings)) -> Graphiti:
    """Get Graphiti client with dependency injection."""
    return Graphiti(
        settings.NEO4J_URI,
        settings.NEO4J_USER,
        settings.NEO4J_PASSWORD
    )

# Initialize LLM
def get_llm(settings: Settings = Depends(get_settings)) -> ChatOpenAI:
    """Get LLM with dependency injection."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE
    )

# Global instances for backward compatibility
graphiti = Graphiti(
    get_settings().NEO4J_URI,
    get_settings().NEO4J_USER,
    get_settings().NEO4J_PASSWORD
)

llm = ChatOpenAI(
    model=get_settings().LLM_MODEL,
    temperature=get_settings().LLM_TEMPERATURE
)

# Initialize data ingestion service
data_ingestion = DataIngestion(graphiti, llm)

# Initialize advanced Graphiti features
graphiti_advanced = GraphitiAdvanced(graphiti)

# Initialize query handler with advanced features
query_handler = QueryHandler(graphiti, graphiti_advanced)

# Define entity types for our domain
class FinancialProduct(BaseModel):
    """A financial product or service"""
    name: str | None = Field(..., description="The name of the financial product")
    category: str | None = Field(..., description="The category of the financial product (e.g., loan, investment)")
    interest_rate: float | None = Field(None, description="The interest rate of the financial product, if applicable")
    term_length: str | None = Field(None, description="The term length of the financial product, if applicable")

class FinancialConcept(BaseModel):
    """A financial concept or term"""
    name: str | None = Field(..., description="The name of the financial concept")
    definition: str | None = Field(..., description="The definition of the financial concept")
    related_to: List[str] | None = Field(None, description="Other financial concepts related to this one")

# Define request and response models
class TranscriptionRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")
    file_format: str = Field("wav", description="Audio file format (default: wav)")

class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text from audio")
    confidence: float = Field(..., description="Confidence score of transcription")

class AssistantRequest(BaseModel):
    query: str = Field(..., description="User query text")
    session_id: str = Field(..., description="Session identifier for conversation tracking")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the query")

class AssistantResponse(BaseModel):
    answer: str = Field(..., description="Assistant's response to the query")
    source: str = Field(..., description="Source of the answer (knowledge graph, llm, etc.)")
    confidence: float = Field(..., description="Confidence score of the answer")
    related_concepts: List[str] = Field(default_factory=list, description="Related concepts to the query")

@app.get("/")
def read_root():
    return {"status": "online", "service": "Voice-to-Text AI Assistant with Complex Query Handling"}

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest):
    """Transcribe audio data to text using faster-whisper."""
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(request.audio_data)
        
        # Create a temporary file to store the audio data
        with NamedTemporaryFile(suffix=f".{request.file_format}") as temp_audio:
            temp_audio.write(audio_data)
            temp_audio.flush()
            
            # Use faster-whisper to transcribe the audio
            # Load the model (use 'tiny', 'base', 'small', 'medium', 'large-v2' based on your needs)
            model_size = "small"
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
            # Transcribe the audio file
            segments, info = model.transcribe(temp_audio.name, beam_size=5)
            
            # Combine all segments into a single text
            text = ""
            for segment in segments:
                text += segment.text + " "
            
            # Get confidence from info
            confidence = info.avg_logprob
            # Normalize confidence to a 0-1 scale (logprob is negative, closer to 0 is better)
            confidence = min(max(1.0 + confidence / 10.0, 0.0), 1.0)
                
            return TranscriptionResponse(text=text.strip(), confidence=confidence)
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/assistant/", response_model=AssistantResponse)
async def process_query(request: AssistantRequest):
    """Process a user query and return an AI assistant response"""
    try:
        # Store the query as an episode in the knowledge graph
        await store_user_query(request.query, request.session_id)
        
        # Process the query using the QueryHandler to handle complex queries
        answer = await QueryHandler.process_query(request.query)
        
        # Get related concepts
        related = await get_related_concepts(request.query)
        
        # Analyze the query to determine complexity
        analysis = await QueryHandler.analyze_query(request.query)
        
        # Determine source and confidence based on analysis
        if analysis.get("is_ambiguous") or analysis.get("is_multi_intent"):
            source = "complex_query_handler"
            confidence = 0.8
        else:
            source = "knowledge_graph" if "added to our knowledge base" not in answer else "llm"
            confidence = 0.9 if source == "knowledge_graph" else 0.7
        
        return AssistantResponse(
            answer=answer,
            source=source,
            confidence=confidence,
            related_concepts=related
        )
    except Exception as e:
        # Fallback to direct LLM if everything else fails
        response = await llm.ainvoke([HumanMessage(content=f"Please answer this question: {request.query}")])
        return AssistantResponse(
            answer=response.content,
            source="llm_fallback",
            confidence=0.5,
            related_concepts=[]
        )

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file for transcription."""
    try:
        # Read the file content
        contents = await file.read()
        
        # Check file size (limit to 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Check file type
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Create a temporary file
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(contents)
            temp_file_path = temp_file.name
        
        try:
            # Use faster-whisper to transcribe the audio
            model_size = "small"
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
            # Transcribe the audio file
            segments, info = model.transcribe(temp_file_path, beam_size=5)
            
            # Combine all segments into a single text
            text = ""
            for segment in segments:
                text += segment.text + " "
            
            # Get confidence from info
            confidence = info.avg_logprob
            # Normalize confidence to a 0-1 scale (logprob is negative, closer to 0 is better)
            confidence = min(max(1.0 + confidence / 10.0, 0.0), 1.0)
                
            return {"text": text.strip(), "confidence": confidence}
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audio upload failed: {str(e)}")

@app.post("/feedback/")
async def provide_feedback(request: Request):
    """Provide feedback on assistant responses to improve the knowledge graph"""
    data = await request.json()
    query = data.get("query")
    response = data.get("response")
    is_helpful = data.get("is_helpful", False)
    feedback = data.get("feedback", "")
    
    # Store feedback in the knowledge graph
    await store_feedback(query, response, is_helpful, feedback)
    
    return {"status": "success", "message": "Feedback recorded"}

async def store_user_query(query: str, session_id: str):
    """Store user query as an episode in the knowledge graph"""
    try:
        await graphiti.add_episode(
            name=f"User Query {datetime.datetime.now().isoformat()}",
            episode_body=query,
            source=EpisodeType.text,
            source_description="User voice query",
            reference_time=datetime.datetime.now(),
            group_id=session_id
        )
        return True
    except Exception as e:
        print(f"Error storing user query: {str(e)}")
        return False

async def store_feedback(query: str, response: str, is_helpful: bool, feedback: str):
    """Store user feedback as an episode in the knowledge graph"""
    try:
        feedback_content = {
            "query": query,
            "response": response,
            "is_helpful": is_helpful,
            "feedback": feedback,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        await graphiti.add_episode(
            name=f"User Feedback {datetime.datetime.now().isoformat()}",
            episode_body=json.dumps(feedback_content),
            source=EpisodeType.json,
            source_description="User feedback on assistant response",
            reference_time=datetime.datetime.now()
        )
        return True
    except Exception as e:
        print(f"Error storing feedback: {str(e)}")
        return False

async def get_related_concepts(query: str, limit: int = 3):
    """Get related concepts to a query from the knowledge graph"""
    try:
        # Search for related nodes
        results = await graphiti.search(query, limit=limit)
        
        # Extract node names
        related_concepts = []
        for result in results:
            if hasattr(result, 'source_node_name') and result.source_node_name:
                related_concepts.append(result.source_node_name)
            if hasattr(result, 'target_node_name') and result.target_node_name:
                related_concepts.append(result.target_node_name)
        
        # Remove duplicates and limit to 3
        return list(set(related_concepts))[:3]
    except Exception as e:
        print(f"Error getting related concepts: {str(e)}")
        return []

# Add new endpoints for data ingestion and complex query handling

@app.post("/ingest/audio/")
async def ingest_audio(file: UploadFile = File(...), source_description: str = "Audio Recording"):
    """Ingest audio file into the knowledge graph"""
    try:
        # Save uploaded file temporarily
        with NamedTemporaryFile(suffix=f".{file.filename.split('.')[-1]}", delete=False) as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        # Ingest audio file
        success = await DataIngestion.ingest_audio(temp_audio_path, source_description)
        
        # Clean up temporary file
        os.unlink(temp_audio_path)
        
        if success:
            return {"status": "success", "message": "Audio ingested successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to ingest audio")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Audio ingestion failed: {str(e)}")

@app.post("/ingest/faq/")
async def ingest_faq(file: UploadFile = File(...), source_description: str = "FAQ Document"):
    """Ingest FAQ document into the knowledge graph"""
    try:
        # Save uploaded file temporarily
        with NamedTemporaryFile(suffix=f".{file.filename.split('.')[-1]}", delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Ingest FAQ file
        success = await DataIngestion.ingest_faq(temp_file_path, source_description)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        if success:
            return {"status": "success", "message": "FAQ ingested successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to ingest FAQ")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"FAQ ingestion failed: {str(e)}")

@app.post("/ingest/web/")
async def ingest_web(url: str = Body(...), source_description: str = Body("Web Content")):
    """Ingest web content into the knowledge graph"""
    try:
        # Ingest web content
        success = await DataIngestion.ingest_web_content(url, source_description)
        
        if success:
            return {"status": "success", "message": "Web content ingested successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to ingest web content")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Web content ingestion failed: {str(e)}")

@app.post("/analyze-query/")
async def analyze_query(query: str = Body(...)):
    """Analyze a query to determine its complexity, ambiguity, and intents"""
    try:
        # Analyze the query
        analysis = await QueryHandler.analyze_query(query)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query analysis failed: {str(e)}")

class QueryRequest(BaseModel):
    query: str

@app.post("/advanced-query/")
async def handle_advanced_query(request: QueryRequest):
    """Handle a query using advanced Graphiti features like namespacing and communities"""
    try:
        # Process the query with advanced features
        result = await query_handler.handle_query_with_advanced_features(request.query)
        return result
    except Exception as e:
        logger.error(f"Error handling advanced query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Advanced query handling failed: {str(e)}")

# Advanced Graphiti feature endpoints

@app.post("/build-communities/")
async def build_communities():
    """Build communities in the knowledge graph to organize related entities"""
    try:
        success = await graphiti_advanced.build_and_maintain_communities()
        if success:
            return {"status": "success", "message": "Communities built successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to build communities")
    except Exception as e:
        logger.error(f"Error building communities: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Community building failed: {str(e)}")

@app.get("/community-summaries/")
async def get_community_summaries(limit: int = 5):
    """Get summaries of the top communities in the knowledge graph"""
    try:
        summaries = await graphiti_advanced.get_community_summaries(limit=limit)
        return {"communities": summaries}
    except Exception as e:
        logger.error(f"Error getting community summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get community summaries: {str(e)}")

@app.post("/advanced-search/")
async def advanced_search(
    query: str = Body(...),
    domain: Optional[str] = Body(None),
    reference_time: Optional[datetime.datetime] = Body(None),
    limit: int = Body(10),
    search_type: str = Body("hybrid")
):
    """Perform advanced search using Graphiti's hybrid search capabilities"""
    try:
        # Convert string domain to enum if provided
        domain_enum = None
        if domain:
            try:
                domain_enum = KnowledgeDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")
        
        results = await graphiti_advanced.advanced_search(
            query=query,
            domain=domain_enum,
            reference_time=reference_time,
            limit=limit,
            search_type=search_type
        )
        
        # Process results for API response
        processed_results = []
        for item in results:
            processed_results.append({
                "id": getattr(item, "uuid", None),
                "name": getattr(item, "name", None),
                "fact": getattr(item, "fact", None),
                "type": type(item).__name__
            })
        
        return {"results": processed_results}
    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")

@app.post("/temporal-query/")
async def temporal_query(
    query: str = Body(...),
    start_time: datetime.datetime = Body(...),
    end_time: datetime.datetime = Body(...),
    domain: Optional[str] = Body(None)
):
    """Query the knowledge graph across a time range to see how facts evolved"""
    try:
        # Convert string domain to enum if provided
        domain_enum = None
        if domain:
            try:
                domain_enum = KnowledgeDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")
        
        results = await graphiti_advanced.temporal_query(
            query=query,
            start_time=start_time,
            end_time=end_time,
            domain=domain_enum
        )
        
        return results
    except Exception as e:
        logger.error(f"Error in temporal query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Temporal query failed: {str(e)}")

@app.post("/add-fact/")
async def add_fact(
    source_name: str = Body(...),
    relation: str = Body(...),
    target_name: str = Body(...),
    fact: str = Body(...),
    domain: str = Body(...),
    reference_time: Optional[datetime.datetime] = Body(None)
):
    """Add a fact triplet with namespace"""
    try:
        # Convert string domain to enum
        try:
            domain_enum = KnowledgeDomain(domain)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")
        
        success = await graphiti_advanced.add_fact_triplet_with_namespace(
            source_name=source_name,
            relation=relation,
            target_name=target_name,
            fact=fact,
            domain=domain_enum,
            reference_time=reference_time
        )
        
        if success:
            return {"status": "success", "message": "Fact added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add fact")
    except Exception as e:
        logger.error(f"Error adding fact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add fact: {str(e)}")

# Custom exception handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    """Custom exception handler to log HTTP exceptions."""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return await http_exception_handler(request, exc)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check Neo4j connection by attempting a simple query
        # This is a safer way to check connection than using ping()
        if hasattr(graphiti, 'driver'):
            # If graphiti has a driver attribute, use it to check connection
            await graphiti.driver.verify_connectivity()
        else:
            # Otherwise try to get communities as a simple test
            await graphiti.get_communities(limit=1)
        
        return {"status": "healthy", "services": {"neo4j": "connected", "app": "running"}}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "services": {"neo4j": "disconnected", "app": "running"}, "error": str(e)}
        )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting Voice-to-Text AI Assistant")
    try:
        # Initialize Graphiti indices
        await graphiti.build_indices_and_constraints()
        logger.info("Graphiti indices initialized")
    except Exception as e:
        logger.error(f"Error initializing Graphiti indices: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down Voice-to-Text AI Assistant")
    try:
        # Close Graphiti connection
        await graphiti.close()
        logger.info("Graphiti connection closed")
    except Exception as e:
        logger.error(f"Error closing Graphiti connection: {str(e)}")

# Mount static files if they exist
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app", 
        host=settings.HOST, 
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
