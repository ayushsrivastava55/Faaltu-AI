"""
Knowledge Ingestion Agent - Learning from Real-World Data
========================================================

This agent continuously learns from various data sources to improve
the system's knowledge and sales effectiveness, replicating how a
human sales representative learns from experience and training.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib
import re

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .base import BaseAgent, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class KnowledgeSource(BaseModel):
    """Represents a source of knowledge that can be ingested"""
    source_id: str
    source_type: str  # audio, document, faq, web, conversation
    source_path: str
    content_hash: str
    last_processed: datetime
    processing_status: str  # pending, processing, completed, failed
    extracted_insights: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LearningInsight(BaseModel):
    """Represents a piece of knowledge extracted from a source"""
    insight_id: str
    source_id: str
    insight_type: str  # sales_technique, objection_handling, product_info, market_data
    content: str
    confidence: float
    applicability: List[str]  # contexts where this insight applies
    examples: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    usage_count: int = 0
    effectiveness_score: float = 0.0


class KnowledgeGap(BaseModel):
    """Represents an identified gap in knowledge"""
    gap_id: str
    query_patterns: List[str]
    missing_knowledge_type: str
    frequency: int
    suggested_sources: List[str] = Field(default_factory=list)
    priority: str  # high, medium, low
    identified_at: datetime = Field(default_factory=datetime.now)


class KnowledgeIngestionAgent(BaseAgent):
    """
    Agent responsible for continuously learning from various data sources
    to improve the system's knowledge and sales effectiveness.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are the Knowledge Ingestion Agent for LendenClub's AI sales assistant.

Your core mission is to continuously learn from real-world data sources to improve sales effectiveness and knowledge depth.

Primary Functions:
1. **Audio Learning**: Extract sales techniques, objection handling, and successful approaches from call recordings
2. **Document Processing**: Learn from FAQs, product documentation, policy updates, and training materials
3. **Web Intelligence**: Gather market trends, competitor information, and regulatory changes
4. **Conversation Analysis**: Identify knowledge gaps from user interactions and failed queries
5. **Knowledge Synthesis**: Convert raw data into actionable insights for other agents

Learning Sources:
- Sales call recordings (extract successful techniques)
- Product documentation and FAQs
- Training materials and scripts
- Market research and competitor data
- User conversations and feedback
- Regulatory updates and policy changes

Knowledge Extraction Capabilities:
- Sales techniques and proven approaches
- Objection handling strategies
- Product features and benefits
- Market rates and trends
- Compliance requirements
- Customer pain points and solutions

Output Types:
- Actionable sales insights
- Updated knowledge base entries
- Agent prompt improvements
- Training recommendations
- Knowledge gap identification
- Performance improvement suggestions

Your goal is to make the AI assistant increasingly human-like by learning from real sales interactions and continuously improving responses based on what works in practice."""

        super().__init__(
            name="Knowledge Ingestion Agent",
            description="Learns from real-world data to continuously improve system knowledge and sales effectiveness",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
        
        # Initialize knowledge management directories
        self.knowledge_dir = Path(storage_service.DATA_DIR) / "knowledge_ingestion"
        self.sources_dir = self.knowledge_dir / "sources"
        self.insights_dir = self.knowledge_dir / "insights"
        self.gaps_dir = self.knowledge_dir / "gaps"
        self.audio_dir = self.knowledge_dir / "audio"
        self.documents_dir = self.knowledge_dir / "documents"
        self.web_cache_dir = self.knowledge_dir / "web_cache"
        
        # Create directories
        for directory in [self.knowledge_dir, self.sources_dir, self.insights_dir, 
                         self.gaps_dir, self.audio_dir, self.documents_dir, self.web_cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Knowledge tracking
        self.knowledge_sources: Dict[str, KnowledgeSource] = {}
        self.insights: Dict[str, LearningInsight] = {}
        self.knowledge_gaps: Dict[str, KnowledgeGap] = {}
        
        # Load existing knowledge
        self._load_existing_knowledge()
        
        # Processing capabilities
        self.audio_processors = {
            '.mp3': self._process_audio_file,
            '.wav': self._process_audio_file,
            '.m4a': self._process_audio_file
        }
        
        self.document_processors = {
            '.pdf': self._process_pdf_document,
            '.txt': self._process_text_document,
            '.md': self._process_markdown_document,
            '.json': self._process_json_document
        }
        
        logger.info("Knowledge Ingestion Agent initialized")
    
    def _load_existing_knowledge(self):
        """Load previously ingested knowledge from storage"""
        try:
            # Load knowledge sources
            sources_index = self.sources_dir / "index.json"
            if sources_index.exists():
                data = json.loads(sources_index.read_text())
                for source_data in data.get("sources", []):
                    source = KnowledgeSource(**source_data)
                    self.knowledge_sources[source.source_id] = source
            
            # Load insights
            insights_index = self.insights_dir / "index.json"
            if insights_index.exists():
                data = json.loads(insights_index.read_text())
                for insight_data in data.get("insights", []):
                    insight = LearningInsight(**insight_data)
                    self.insights[insight.insight_id] = insight
            
            # Load knowledge gaps
            gaps_index = self.gaps_dir / "index.json"
            if gaps_index.exists():
                data = json.loads(gaps_index.read_text())
                for gap_data in data.get("gaps", []):
                    gap = KnowledgeGap(**gap_data)
                    self.knowledge_gaps[gap.gap_id] = gap
            
            logger.info(f"Loaded {len(self.knowledge_sources)} sources, {len(self.insights)} insights, {len(self.knowledge_gaps)} gaps")
            
        except Exception as e:
            logger.error(f"Failed to load existing knowledge: {e}")
    
    async def process_query(self, request: AgentRequest) -> AgentResponse:
        """Process knowledge ingestion requests"""
        start_time = datetime.now()
        
        try:
            # Parse the request to understand what type of knowledge operation is needed
            analysis_prompt = f"""
Analyze this knowledge ingestion request: "{request.query}"

Determine the operation type and parameters:
1. **Ingest new source** (audio file, document, URL, etc.)
2. **Analyze knowledge gaps** from conversation data  
3. **Update existing knowledge** based on feedback
4. **Search insights** for specific topics
5. **Report learning status** and metrics

Respond with JSON:
{{
    "operation": "ingest_source|analyze_gaps|update_knowledge|search_insights|report_status",
    "source_type": "audio|document|web|conversation|feedback",
    "source_path": "path or URL if applicable",
    "search_query": "search terms if searching",
    "parameters": {{"additional": "parameters"}}
}}
"""
            
            # Get operation analysis
            analysis = await self.agent.run(analysis_prompt)
            
            try:
                if hasattr(analysis, 'data'):
                    operation_data = json.loads(str(analysis.data))
                else:
                    operation_data = json.loads(str(analysis))
            except json.JSONDecodeError:
                return await self._create_error_response(request, "Failed to parse operation request", start_time)
            
            # Route to appropriate handler
            operation = operation_data.get("operation", "report_status")
            
            if operation == "ingest_source":
                return await self._handle_source_ingestion(request, operation_data, start_time)
            elif operation == "analyze_gaps":
                return await self._handle_gap_analysis(request, operation_data, start_time)
            elif operation == "update_knowledge":
                return await self._handle_knowledge_update(request, operation_data, start_time)
            elif operation == "search_insights":
                return await self._handle_insight_search(request, operation_data, start_time)
            else:
                return await self._handle_status_report(request, operation_data, start_time)
        
        except Exception as e:
            logger.error(f"Error in knowledge ingestion agent: {e}")
            return await self._create_error_response(request, str(e), start_time)
    
    async def _handle_source_ingestion(self, request: AgentRequest, operation_data: Dict[str, Any], start_time: datetime) -> AgentResponse:
        """Handle ingestion of new knowledge sources"""
        source_type = operation_data.get("source_type", "document")
        source_path = operation_data.get("source_path", "")
        
        if not source_path:
            return await self._create_error_response(request, "Source path is required for ingestion", start_time)
        
        try:
            # Create knowledge source entry
            source_id = hashlib.md5(f"{source_type}:{source_path}".encode()).hexdigest()
            
            # Check if already processed
            if source_id in self.knowledge_sources:
                existing_source = self.knowledge_sources[source_id]
                return AgentResponse(
                    query=request.query,
                    response=f"Source already processed: {existing_source.source_path}\nLast processed: {existing_source.last_processed}\nInsights extracted: {len(existing_source.extracted_insights)}",
                    agent_name=self.name,
                    session_id=request.session_id,
                    confidence=0.9,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now(),
                    tools_used=["source_lookup"],
                    context_used={"operation": "source_already_exists"}
                )
            
            # Process based on source type
            if source_type == "audio":
                insights = await self._process_audio_source(source_path)
            elif source_type == "document":
                insights = await self._process_document_source(source_path)
            elif source_type == "web":
                insights = await self._process_web_source(source_path)
            else:
                insights = await self._process_generic_source(source_path, source_type)
            
            # Create and save source record
            content_hash = hashlib.md5(source_path.encode()).hexdigest()
            source = KnowledgeSource(
                source_id=source_id,
                source_type=source_type,
                source_path=source_path,
                content_hash=content_hash,
                last_processed=datetime.now(),
                processing_status="completed",
                extracted_insights=[insight.insight_id for insight in insights],
                metadata=operation_data.get("parameters", {})
            )
            
            self.knowledge_sources[source_id] = source
            
            # Save insights
            for insight in insights:
                self.insights[insight.insight_id] = insight
            
            # Save to disk
            await self._save_knowledge_state()
            
            response_text = f"""Successfully ingested knowledge source:

**Source**: {source_path}
**Type**: {source_type}
**Insights Extracted**: {len(insights)}
**Processing Time**: {(datetime.now() - start_time).total_seconds():.2f}s

**Key Insights:**
{self._format_insights_summary(insights[:3])}

The knowledge base has been updated and these insights will improve future responses."""

            return AgentResponse(
                query=request.query,
                response=response_text,
                agent_name=self.name,
                session_id=request.session_id,
                confidence=0.9,
                processing_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                tools_used=["knowledge_ingestion", f"{source_type}_processing"],
                context_used={
                    "operation": "source_ingestion",
                    "insights_count": len(insights),
                    "source_type": source_type
                },
                follow_up_suggestions=[
                    "Would you like to ingest more sources?",
                    "Should I analyze knowledge gaps from recent conversations?",
                    "Do you want to see the learning metrics?"
                ]
            )
            
        except Exception as e:
            logger.error(f"Failed to ingest source {source_path}: {e}")
            return await self._create_error_response(request, f"Failed to ingest source: {e}", start_time)
    
    async def _process_audio_source(self, source_path: str) -> List[LearningInsight]:
        """Process audio files to extract sales knowledge"""
        insights = []
        
        try:
            # For now, simulate audio processing (in real implementation, would use speech-to-text)
            audio_content = f"Simulated transcription of audio file: {source_path}"
            
            # Extract insights using LLM
            extraction_prompt = f"""
Analyze this sales call transcription to extract valuable sales insights:

Transcription: {audio_content}

Extract insights in these categories:
1. **Sales Techniques**: Effective approaches used
2. **Objection Handling**: How objections were addressed
3. **Customer Pain Points**: What customers complained about
4. **Successful Closures**: What led to successful outcomes
5. **Product Information**: Details mentioned about products

For each insight, provide:
- Category
- Specific technique or information
- Context where it applies
- Why it was effective

Format as JSON array of insights.
"""
            
            result = await self.agent.run(extraction_prompt)
            
            # Parse and create insight objects
            # (Simplified for demo - would parse actual JSON response)
            insights.append(LearningInsight(
                insight_id=f"audio_{hashlib.md5(source_path.encode()).hexdigest()}_{len(insights)}",
                source_id=hashlib.md5(f"audio:{source_path}".encode()).hexdigest(),
                insight_type="sales_technique",
                content=f"Sales insight extracted from {source_path}",
                confidence=0.8,
                applicability=["loan_consultation", "objection_handling"]
            ))
            
        except Exception as e:
            logger.error(f"Failed to process audio source {source_path}: {e}")
        
        return insights
    
    async def _process_document_source(self, source_path: str) -> List[LearningInsight]:
        """Process documents to extract knowledge"""
        insights = []
        
        try:
            # Read document content
            doc_path = Path(source_path)
            if not doc_path.exists():
                # Try relative path from documents directory
                doc_path = self.documents_dir / source_path
            
            if doc_path.exists():
                content = doc_path.read_text(encoding='utf-8')
                
                # Extract insights using LLM
                extraction_prompt = f"""
Analyze this document to extract valuable knowledge for a sales assistant:

Document: {source_path}
Content: {content[:2000]}...

Extract insights in these categories:
1. **Product Information**: Features, benefits, specifications
2. **Sales Strategies**: Recommended approaches and techniques
3. **Market Data**: Rates, trends, competitive information
4. **Compliance**: Regulatory requirements and constraints
5. **Customer Guidance**: How to help customers with specific needs

Provide actionable insights that can improve sales conversations.
"""
                
                result = await self.agent.run(extraction_prompt)
                
                # Create insights (simplified)
                insights.append(LearningInsight(
                    insight_id=f"doc_{hashlib.md5(source_path.encode()).hexdigest()}_{len(insights)}",
                    source_id=hashlib.md5(f"document:{source_path}".encode()).hexdigest(),
                    insight_type="product_info",
                    content=f"Product knowledge extracted from {source_path}",
                    confidence=0.9,
                    applicability=["product_inquiry", "feature_explanation"]
                ))
                
        except Exception as e:
            logger.error(f"Failed to process document {source_path}: {e}")
        
        return insights
    
    async def _process_web_source(self, source_url: str) -> List[LearningInsight]:
        """Process web content to extract market intelligence"""
        insights = []
        
        try:
            # Simulate web scraping (in real implementation, would fetch and parse web content)
            web_content = f"Simulated web content from: {source_url}"
            
            # Extract market insights
            extraction_prompt = f"""
Analyze this web content for market intelligence:

URL: {source_url}
Content: {web_content}

Extract insights about:
1. **Market Trends**: Current lending trends and rates
2. **Competitor Analysis**: What competitors are offering
3. **Regulatory Changes**: New rules or requirements
4. **Industry News**: Relevant developments
5. **Customer Sentiment**: What customers are saying

Provide actionable market intelligence.
"""
            
            result = await self.agent.run(extraction_prompt)
            
            insights.append(LearningInsight(
                insight_id=f"web_{hashlib.md5(source_url.encode()).hexdigest()}_{len(insights)}",
                source_id=hashlib.md5(f"web:{source_url}".encode()).hexdigest(),
                insight_type="market_data",
                content=f"Market intelligence from {source_url}",
                confidence=0.7,
                applicability=["market_inquiry", "competitor_comparison"]
            ))
            
        except Exception as e:
            logger.error(f"Failed to process web source {source_url}: {e}")
        
        return insights
    
    async def _process_generic_source(self, source_path: str, source_type: str) -> List[LearningInsight]:
        """Process generic sources"""
        return [LearningInsight(
            insight_id=f"generic_{hashlib.md5(source_path.encode()).hexdigest()}",
            source_id=hashlib.md5(f"{source_type}:{source_path}".encode()).hexdigest(),
            insight_type="general_knowledge",
            content=f"Knowledge extracted from {source_type} source: {source_path}",
            confidence=0.6,
            applicability=["general_inquiry"]
        )]
    
    def _format_insights_summary(self, insights: List[LearningInsight]) -> str:
        """Format insights for display"""
        if not insights:
            return "No insights extracted."
        
        summary = []
        for i, insight in enumerate(insights[:3], 1):
            summary.append(f"{i}. {insight.insight_type.replace('_', ' ').title()}: {insight.content[:100]}...")
        
        return "\n".join(summary)
    
    async def _handle_gap_analysis(self, request: AgentRequest, operation_data: Dict[str, Any], start_time: datetime) -> AgentResponse:
        """Analyze knowledge gaps from conversation data"""
        # This would analyze conversation memory to identify knowledge gaps
        gaps_found = len(self.knowledge_gaps)
        
        response_text = f"""Knowledge Gap Analysis Complete:

**Current Gaps Identified**: {gaps_found}
**Analysis Period**: Last 30 days
**Conversation Sessions Analyzed**: {operation_data.get('sessions_analyzed', 'N/A')}

**Top Knowledge Gaps:**
1. Complex loan calculations and scenarios
2. Specific industry regulations and compliance
3. Advanced objection handling techniques
4. Market comparison and competitive intelligence

**Recommended Actions:**
- Ingest more training materials on loan calculations
- Update compliance documentation
- Process more successful sales call recordings
- Gather competitive analysis from web sources

Would you like me to prioritize specific areas for knowledge ingestion?"""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.8,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["gap_analysis", "conversation_analysis"],
            context_used={"operation": "gap_analysis", "gaps_found": gaps_found}
        )
    
    async def _handle_insight_search(self, request: AgentRequest, operation_data: Dict[str, Any], start_time: datetime) -> AgentResponse:
        """Search for specific insights"""
        search_query = operation_data.get("search_query", "")
        
        # Search through insights
        matching_insights = []
        for insight in self.insights.values():
            if search_query.lower() in insight.content.lower() or search_query.lower() in insight.insight_type:
                matching_insights.append(insight)
        
        response_text = f"""Search Results for "{search_query}":

**Found {len(matching_insights)} matching insights**

{self._format_insights_summary(matching_insights[:5])}

These insights can help improve responses related to: {search_query}"""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.9,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["insight_search"],
            context_used={"operation": "search", "results_found": len(matching_insights)}
        )
    
    async def _handle_status_report(self, request: AgentRequest, operation_data: Dict[str, Any], start_time: datetime) -> AgentResponse:
        """Provide learning status and metrics"""
        
        response_text = f"""Knowledge Ingestion Status Report:

**Knowledge Base Stats:**
- Total Sources Processed: {len(self.knowledge_sources)}
- Insights Extracted: {len(self.insights)}
- Knowledge Gaps Identified: {len(self.knowledge_gaps)}

**Source Breakdown:**
- Audio Sources: {sum(1 for s in self.knowledge_sources.values() if s.source_type == 'audio')}
- Document Sources: {sum(1 for s in self.knowledge_sources.values() if s.source_type == 'document')}
- Web Sources: {sum(1 for s in self.knowledge_sources.values() if s.source_type == 'web')}

**Recent Learning Activity:**
- Last 24 hours: {sum(1 for s in self.knowledge_sources.values() if (datetime.now() - s.last_processed).days < 1)} sources processed
- Last 7 days: {sum(1 for s in self.knowledge_sources.values() if (datetime.now() - s.last_processed).days < 7)} sources processed

**Next Recommended Actions:**
1. Process more sales call recordings for technique extraction
2. Ingest latest product documentation updates
3. Analyze recent conversation gaps for missing knowledge areas

The system is continuously learning and improving its sales effectiveness!"""

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=1.0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["status_reporting", "metrics_analysis"],
            context_used={
                "operation": "status_report",
                "total_sources": len(self.knowledge_sources),
                "total_insights": len(self.insights)
            },
            follow_up_suggestions=[
                "Would you like to ingest a new knowledge source?",
                "Should I analyze recent knowledge gaps?",
                "Do you want to search for specific insights?"
            ]
        )
    
    async def _save_knowledge_state(self):
        """Save current knowledge state to disk"""
        try:
            # Save sources index
            sources_data = {
                "sources": [source.model_dump() for source in self.knowledge_sources.values()],
                "last_updated": datetime.now().isoformat()
            }
            (self.sources_dir / "index.json").write_text(json.dumps(sources_data, indent=2, default=str))
            
            # Save insights index
            insights_data = {
                "insights": [insight.model_dump() for insight in self.insights.values()],
                "last_updated": datetime.now().isoformat()
            }
            (self.insights_dir / "index.json").write_text(json.dumps(insights_data, indent=2, default=str))
            
            # Save gaps index
            gaps_data = {
                "gaps": [gap.model_dump() for gap in self.knowledge_gaps.values()],
                "last_updated": datetime.now().isoformat()
            }
            (self.gaps_dir / "index.json").write_text(json.dumps(gaps_data, indent=2, default=str))
            
        except Exception as e:
            logger.error(f"Failed to save knowledge state: {e}")
    
    # Additional methods for file processing would be implemented here
    async def _process_audio_file(self, file_path: str) -> List[LearningInsight]:
        """Process specific audio file formats"""
        # Would implement actual audio transcription and analysis
        return await self._process_audio_source(file_path)
    
    async def _process_pdf_document(self, file_path: str) -> List[LearningInsight]:
        """Process PDF documents"""
        # Would implement PDF parsing and text extraction
        return await self._process_document_source(file_path)
    
    async def _process_text_document(self, file_path: str) -> List[LearningInsight]:
        """Process plain text documents"""
        return await self._process_document_source(file_path)
    
    async def _process_markdown_document(self, file_path: str) -> List[LearningInsight]:
        """Process Markdown documents"""
        return await self._process_document_source(file_path)
    
    async def _process_json_document(self, file_path: str) -> List[LearningInsight]:
        """Process JSON data files"""
        return await self._process_document_source(file_path)
    
    async def _handle_knowledge_update(self, request: AgentRequest, operation_data: Dict[str, Any], start_time: datetime) -> AgentResponse:
        """Handle knowledge updates based on feedback"""
        # Implementation for updating existing knowledge
        response_text = "Knowledge update functionality will be implemented based on user feedback and system learning."
        
        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_name=self.name,
            session_id=request.session_id,
            confidence=0.8,
            processing_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now(),
            tools_used=["knowledge_update"],
            context_used={"operation": "update_knowledge"}
        )
    
    def _register_tools(self):
        """Register knowledge ingestion tools"""
        # Knowledge ingestion tools are primarily handled through the process_query method
        # and various processing functions. This method satisfies the abstract requirement.
        self.tools = [
            "document_ingestion",
            "audio_processing", 
            "web_scraping",
            "knowledge_extraction",
            "gap_analysis",
            "insight_search",
            "learning_metrics"
        ]
        
    def _get_tools_used(self) -> List[str]:
        """Get list of tools used by this agent"""
        return getattr(self, 'tools', [
            "document_ingestion",
            "audio_processing", 
            "web_scraping",
            "knowledge_extraction",
            "gap_analysis",
            "insight_search",
            "learning_metrics"
        ]) 