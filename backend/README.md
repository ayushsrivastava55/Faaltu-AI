# Voice-to-Text AI Assistant with Graphiti Knowledge Graphs

## Overview

This project implements a voice-to-text AI assistant that leverages Graphiti knowledge graphs for contextual understanding and response generation. The assistant processes voice input, transcribes it to text, queries a knowledge graph, and generates natural language responses.

## Key Features

- **Voice Input Processing**: Transcribes audio input to text using speech recognition
- **Graphiti Knowledge Graph Integration**: Uses Graphiti for contextual understanding and knowledge representation
- **Advanced Knowledge Graph Features**:
  - **Communities**: Organizes related entities into communities for better knowledge synthesis
  - **Namespacing**: Separates knowledge into domains (financial products, customer service, FAQs, etc.)
  - **Hybrid Search**: Combines semantic and keyword search for optimal results
  - **Temporal Querying**: Tracks how facts and relationships change over time
  - **LangGraph Integration**: Enhanced agentic reasoning workflows
- **Natural Language Response Generation**: Generates contextually relevant responses
- **Multi-Intent Query Handling**: Processes ambiguous, vague, or multi-intent queries
- **Learning Capabilities**: Learns from audio recordings, FAQs, and web-based knowledge
- **Production-Ready**: Includes configuration management, logging, health checks, and error handling

## Architecture

The system is built with a modular architecture:

1. **FastAPI Backend**: Handles HTTP requests and orchestrates the processing pipeline
2. **Voice Input Module**: Processes and transcribes audio input
3. **Graphiti Integration**: Connects to and queries the Graphiti knowledge graph
4. **Query Handler**: Processes complex, ambiguous, and multi-intent queries
5. **Advanced Graphiti Features**: Leverages communities, namespacing, and advanced search
6. **Response Generator**: Creates natural language responses
7. **Data Ingestion**: Learns from audio, FAQs, and web content

## Setup and Installation

### Prerequisites

- Python 3.9+
- Neo4j database
- OpenAI API key
- Google Speech Recognition API access

### Environment Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
HOST=0.0.0.0
PORT=8000
DEBUG=True
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.2
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

## API Endpoints

### Core Endpoints

- `POST /transcribe/`: Transcribe audio to text
- `POST /query/`: Process a text query and return a response
- `POST /feedback/`: Submit feedback for a response
- `POST /upload-audio/`: Upload audio for learning
- `POST /ingest-faq/`: Ingest FAQ documents
- `POST /ingest-web/`: Ingest web content

### Advanced Graphiti Endpoints

- `POST /advanced-query/`: Process queries using advanced Graphiti features
- `POST /build-communities/`: Build communities in the knowledge graph
- `GET /community-summaries/`: Get summaries of top communities
- `POST /advanced-search/`: Perform hybrid search across namespaces
- `POST /temporal-query/`: Query knowledge across time ranges
- `POST /add-fact/`: Add fact triplets with namespacing

## Knowledge Graph Integration

The system uses Graphiti as the standard for knowledge graphs, providing:

1. **Episodic Memory**: Stores interactions and learned facts as episodes
2. **Temporal Knowledge**: Tracks how facts change over time
3. **Hybrid Search**: Combines semantic and graph-based search
4. **Communities**: Groups related entities for better knowledge synthesis
5. **Namespacing**: Organizes knowledge into separate domains

## Complex Query Handling

The system handles complex queries through:

1. **Query Analysis**: Determines ambiguity, multiple intents, and relevant domains
2. **Query Decomposition**: Breaks multi-intent queries into sub-queries
3. **Clarification**: Asks for clarification when needed
4. **Domain-Specific Search**: Searches relevant knowledge domains
5. **Community Context**: Uses community summaries for additional context

## Deployment

See the `deployment_guide.md` for detailed deployment instructions, including:

- Direct deployment with Uvicorn
- Deployment with Gunicorn and Uvicorn workers
- Docker deployment
- Kubernetes deployment

## Advanced Graphiti Features

### Communities

Communities group related entities together, providing synthesized information about clusters of knowledge. The system periodically rebuilds communities and updates them when adding new episodes.

```python
# Build communities
POST /build-communities/

# Get community summaries
GET /community-summaries/
```

### Namespacing

The system uses namespacing to organize knowledge into domains:

- FINANCIAL_PRODUCTS
- CUSTOMER_SERVICE
- FAQ
- AUDIO_RECORDINGS
- WEB_CONTENT
- USER_QUERIES
- USER_FEEDBACK

```python
# Add fact with namespace
POST /add-fact/
{
  "source_name": "SuperLight Wool Runners",
  "relation": "is_category_of",
  "target_name": "Sustainable Footwear",
  "fact": "SuperLight Wool Runners is a product in the Sustainable Footwear category",
  "domain": "FINANCIAL_PRODUCTS"
}
```

### Advanced Search

The system supports hybrid search combining semantic and keyword matching:

```python
# Advanced search
POST /advanced-search/
{
  "query": "sustainable investment options",
  "domain": "FINANCIAL_PRODUCTS",
  "search_type": "hybrid"
}
```

### Temporal Querying

Query the knowledge graph across time to see how facts evolve:

```python
# Temporal query
POST /temporal-query/
{
  "query": "interest rates",
  "start_time": "2025-01-01T00:00:00Z",
  "end_time": "2025-06-01T00:00:00Z"
}
```

## LangGraph Integration

The system integrates with LangGraph for enhanced agentic reasoning:

1. **State Management**: Maintains conversation state
2. **Workflow Nodes**: Defines retrieval and response generation nodes
3. **Graph-Based Reasoning**: Creates sophisticated reasoning workflows

## License

[Specify License]

## Contributors

[List Contributors]
