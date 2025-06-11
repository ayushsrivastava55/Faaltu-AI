"""
Data ingestion module for the Voice-to-Text AI Assistant.
This module handles the ingestion of data from various sources like audio recordings,
FAQs, and web-based knowledge into the Graphiti knowledge graph.
"""

import os
import json
import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Union, Any
import uuid
import re
from urllib.parse import urlparse

# Web scraping imports
import requests
from bs4 import BeautifulSoup

# Audio processing imports
from faster_whisper import WhisperModel

# Graphiti imports
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EntityNode
from graphiti_core.edges import EntityEdge

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

class DataIngestion:
    """Class for handling data ingestion from various sources."""
    
    def __init__(self, graphiti: Graphiti, llm: ChatOpenAI):
        """Initialize with Graphiti client and LLM."""
        self.graphiti = graphiti
        self.llm = llm
    
    async def ingest_audio(self, audio_path: str, source_description: str = "Audio Recording") -> bool:
        """
        Transcribe and ingest audio file content into the knowledge graph.
        
        Args:
            audio_path: Path to the audio file
            source_description: Description of the audio source
            
        Returns:
            bool: True if ingestion was successful, False otherwise
        """
        try:
            # Use faster-whisper to transcribe the audio
            model_size = "small"
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
            # Transcribe the audio file
            segments, info = model.transcribe(audio_path, beam_size=5)
            
            # Combine all segments into a single text
            text = ""
            for segment in segments:
                text += segment.text + " "
            
            # Ingest transcribed text into knowledge graph
            await self.graphiti.add_episode(
                name=f"Audio Transcription {datetime.datetime.now().isoformat()}",
                episode_body=text.strip(),
                source=EpisodeType.text,
                source_description=source_description,
                reference_time=datetime.datetime.now()
            )
            
            logger.info(f"Successfully ingested audio from {audio_path}")
            return True
        except Exception as e:
            logger.error(f"Error ingesting audio: {str(e)}")
            return False
    
    async def ingest_faq(self, faq_path: str, source_description: str = "FAQ Document") -> bool:
        """
        Ingest FAQ document into the knowledge graph.
        
        Args:
            faq_path: Path to the FAQ file (JSON or TXT)
            source_description: Description of the FAQ source
            
        Returns:
            bool: True if ingestion was successful, False otherwise
        """
        try:
            # Read FAQ file
            with open(faq_path, 'r') as file:
                if faq_path.lower().endswith('.json'):
                    # Process JSON FAQ
                    faqs = json.load(file)
                    
                    # Process each FAQ item
                    for i, faq in enumerate(faqs):
                        question = faq.get('question', '')
                        answer = faq.get('answer', '')
                        
                        if question and answer:
                            # Add each FAQ as a separate episode
                            await self.graphiti.add_episode(
                                name=f"FAQ {i+1}: {question[:50]}...",
                                episode_body=json.dumps({
                                    "question": question,
                                    "answer": answer
                                }),
                                source=EpisodeType.json,
                                source_description=source_description,
                                reference_time=datetime.datetime.now()
                            )
                else:
                    # Process text FAQ
                    content = file.read()
                    
                    # Add as a single episode
                    await self.graphiti.add_episode(
                        name=f"FAQ Document: {os.path.basename(faq_path)}",
                        episode_body=content,
                        source=EpisodeType.text,
                        source_description=source_description,
                        reference_time=datetime.datetime.now()
                    )
            
            logger.info(f"Successfully ingested FAQ from {faq_path}")
            return True
        except Exception as e:
            logger.error(f"Error ingesting FAQ: {str(e)}")
            return False
            await graphiti.add_episode_bulk(episodes)
            
            logger.info(f"Successfully ingested FAQ from {faq_path}")
            return True
        except Exception as e:
            logger.error(f"Error ingesting FAQ: {str(e)}")
            return False
    
    async def ingest_web_content(self, url: str, source_description: str = "Web Content") -> bool:
        """
        Scrape and ingest web content into the knowledge graph.
        
        Args:
            url: URL of the web page to scrape
            source_description: Description of the web source
            
        Returns:
            bool: True if ingestion was successful, False otherwise
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.error(f"Invalid URL: {url}")
                return False
            
            # Fetch web content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content (this is a simplified approach)
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean text (remove extra whitespace)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Ingest content into knowledge graph
            await self.graphiti.add_episode(
                name=f"Web Content: {soup.title.string if soup.title else url}",
                episode_body=text,
                source=EpisodeType.text,
                source_description=f"{source_description} - {url}",
                reference_time=datetime.datetime.now()
            )
            
            logger.info(f"Successfully ingested web content from {url}")
            return True
        except Exception as e:
            logger.error(f"Error ingesting web content: {str(e)}")
            return False
    
    @staticmethod
    async def extract_facts_from_content(content: str, context: str = "") -> List[Dict[str, str]]:
        """
        Extract fact triplets from content using LLM.
        
        Args:
            content: Text content to extract facts from
            context: Additional context about the content
            
        Returns:
            List of fact triplets (subject, relationship, object)
        """
        try:
            # Prepare prompt for fact extraction
            prompt = f"""
            Extract key fact triplets from the following content in the format:
            [Subject] [Relationship] [Object]
            
            Content: {content}
            
            Additional Context: {context}
            
            Extract up to 5 most important facts. Each fact should be on a new line.
            Example:
            - Personal loans [HAVE_INTEREST_RATE] 8.5% APR
            - Secured loans [REQUIRE] collateral
            - Credit score [AFFECTS] loan eligibility
            """
            
            # Get response from LLM
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            
            # Parse fact triplets
            facts = []
            for line in response.content.strip().split('\n'):
                line = line.strip()
                if line and '[' in line and ']' in line:
                    # Remove bullet points if present
                    if line.startswith('- '):
                        line = line[2:]
                    
                    # Extract triplet components
                    match = re.match(r'(.*?)\s+\[(.*?)\]\s+(.*)', line)
                    if match:
                        subject = match.group(1).strip()
                        relationship = match.group(2).strip()
                        object_value = match.group(3).strip()
                        
                        facts.append({
                            'subject': subject,
                            'relationship': relationship,
                            'object': object_value
                        })
            
            return facts
        except Exception as e:
            logger.error(f"Error extracting facts: {str(e)}")
            return []
    
    @staticmethod
    async def add_facts_to_knowledge_graph(facts: List[Dict[str, str]]) -> bool:
        """
        Add extracted facts to the knowledge graph.
        
        Args:
            facts: List of fact triplets (subject, relationship, object)
            
        Returns:
            bool: True if addition was successful, False otherwise
        """
        try:
            for fact in facts:
                subject = fact.get('subject')
                relationship = fact.get('relationship')
                object_value = fact.get('object')
                
                if subject and relationship and object_value:
                    # Create UUIDs for the nodes
                    source_uuid = str(uuid.uuid4())
                    target_uuid = str(uuid.uuid4())
                    
                    # Create the source and target nodes
                    source_node = EntityNode(
                        uuid=source_uuid,
                        name=subject,
                        group_id="",
                        summary=f"Financial concept: {subject}"
                    )
                    
                    target_node = EntityNode(
                        uuid=target_uuid,
                        name=object_value,
                        group_id="",
                        summary=f"Financial concept: {object_value}"
                    )
                    
                    # Create the edge with the relationship
                    edge = EntityEdge(
                        group_id="",
                        source_node_uuid=source_uuid,
                        target_node_uuid=target_uuid,
                        created_at=datetime.datetime.now(),
                        name=relationship,
                        fact=f"{subject} {relationship} {object_value}"
                    )
                    
                    # Add the triplet to the graph
                    await graphiti.add_triplet(source_node, edge, target_node)
            
            logger.info(f"Successfully added {len(facts)} facts to the knowledge graph")
            return True
        except Exception as e:
            logger.error(f"Error adding facts to knowledge graph: {str(e)}")
            return False
    
    @staticmethod
    async def process_and_ingest_content(content: str, source: str, source_description: str) -> bool:
        """
        Process and ingest content into the knowledge graph.
        
        Args:
            content: Text content to ingest
            source: Source type (audio, faq, web)
            source_description: Description of the source
            
        Returns:
            bool: True if ingestion was successful, False otherwise
        """
        try:
            # Add content as an episode
            await graphiti.add_episode(
                name=f"{source.capitalize()} Content {datetime.datetime.now().isoformat()}",
                episode_body=content,
                source=EpisodeType.text,
                source_description=source_description,
                reference_time=datetime.datetime.now()
            )
            
            # Extract facts from content
            facts = await DataIngestion.extract_facts_from_content(content, source_description)
            
            # Add facts to knowledge graph
            if facts:
                await DataIngestion.add_facts_to_knowledge_graph(facts)
            
            logger.info(f"Successfully processed and ingested content from {source}")
            return True
        except Exception as e:
            logger.error(f"Error processing and ingesting content: {str(e)}")
            return False


# Example usage
async def main():
    # Initialize Graphiti indices
    await graphiti.build_indices_and_constraints()
    
    # Example: Ingest FAQ
    await DataIngestion.ingest_faq("path/to/faq.json", "Financial Products FAQ")
    
    # Example: Ingest web content
    await DataIngestion.ingest_web_content("https://example.com/financial-terms", "Financial Terms Glossary")
    
    # Example: Process and ingest custom content
    content = """
    A mortgage is a loan used to purchase real estate. The property serves as collateral for the loan.
    Fixed-rate mortgages have the same interest rate for the entire term, typically 15 or 30 years.
    Adjustable-rate mortgages (ARMs) have interest rates that can change periodically based on market conditions.
    """
    await DataIngestion.process_and_ingest_content(content, "manual", "Mortgage Information")


if __name__ == "__main__":
    asyncio.run(main())
