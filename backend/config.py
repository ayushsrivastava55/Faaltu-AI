"""
Configuration module for the Voice-to-Text AI Assistant.
This module handles loading environment variables and configuration settings.
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for LLM and embedding")
    
    # Neo4j Connection
    NEO4J_URI: str = Field("bolt://localhost:7687", description="Neo4j database URI")
    NEO4J_USER: str = Field("neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")
    
    # Server Settings
    HOST: str = Field("0.0.0.0", description="Host to bind the server to")
    PORT: int = Field(8000, description="Port to bind the server to")
    DEBUG: bool = Field(False, description="Enable debug mode")
    
    # LLM Settings
    LLM_MODEL: str = Field("gpt-4o", description="LLM model to use")
    LLM_TEMPERATURE: float = Field(0.2, description="Temperature for LLM generation")
    
    # Speech Recognition Settings
    SPEECH_RECOGNITION_SERVICE: str = Field("google", description="Speech recognition service to use (google, azure, etc.)")
    AZURE_SPEECH_KEY: Optional[str] = Field(None, description="Azure Speech API key (if using Azure)")
    AZURE_SPEECH_REGION: Optional[str] = Field(None, description="Azure Speech API region (if using Azure)")
    
    # CORS Settings
    CORS_ORIGINS: list = Field(["*"], description="CORS allowed origins")
    
    # Logging Settings
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    
    # Cache Settings
    ENABLE_CACHE: bool = Field(True, description="Enable response caching")
    CACHE_TTL: int = Field(3600, description="Cache TTL in seconds")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

def get_settings():
    """Get application settings."""
    return settings
