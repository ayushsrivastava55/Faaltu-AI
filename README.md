# Voice-to-Text AI Assistant with Graphiti Knowledge Graphs

A scalable voice-to-text AI assistant that uses Graphiti knowledge graphs and an agentic AI approach to process voice input, generate natural language responses, learn from diverse data sources, and handle complex user queries effectively.

## Features

- **Voice Input Processing**: Transcribe spoken language to text using speech recognition technology
- **Knowledge Graph Integration**: Use Graphiti for contextual understanding and knowledge representation
- **Natural Language Response Generation**: Generate human-like responses using LLM technology
- **Learning Capabilities**: Ingest and learn from audio recordings, FAQs, and web-based knowledge
- **Complex Query Handling**: Process ambiguous, vague, or multi-intent queries accurately
- **Agentic AI Approach**: Autonomous reasoning and decision making for complex tasks
- **Scalable Architecture**: Designed for real-world deployment with proper error handling and monitoring

## Project Structure

```
finmate-attempt2/
├── backend/
│   ├── main.py                  # FastAPI application entry point
│   ├── knowledge_feedback.py    # Knowledge feedback loop implementation
│   ├── data_ingestion.py        # Data ingestion from various sources
│   ├── query_handler.py         # Complex query handling
│   ├── config.py                # Configuration management
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Environment variables (not in repo)
│   └── deployment_guide.md      # Deployment instructions
├── graphiti-docs/               # Graphiti documentation
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose configuration
└── README.md                    # This file
```

## Getting Started

### Prerequisites

- Python 3.8+
- Neo4j database (4.4+)
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd finmate-attempt2
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory with the following content:
   ```
   # API Keys
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Neo4j Connection
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   
   # Server Settings
   HOST=0.0.0.0
   PORT=8000
   DEBUG=True
   
   # LLM Settings
   LLM_MODEL=gpt-4o
   LLM_TEMPERATURE=0.2
   ```

### Running the Application

#### Local Development

```bash
cd backend
uvicorn main:app --reload
```

#### Docker Deployment

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key_here

# Start the application with Docker Compose
docker-compose up -d
```

## API Endpoints

### Voice Processing

- `POST /transcribe/`: Transcribe base64-encoded audio to text
- `POST /upload-audio/`: Upload and transcribe audio files

### Assistant Interaction

- `POST /assistant/`: Process user queries and generate responses
- `POST /feedback/`: Submit feedback on assistant responses

### Data Ingestion

- `POST /ingest/audio/`: Ingest audio recordings into the knowledge graph
- `POST /ingest/faq/`: Ingest FAQ documents into the knowledge graph
- `POST /ingest/web/`: Ingest web content into the knowledge graph

### Query Analysis

- `POST /analyze-query/`: Analyze a query for complexity, ambiguity, and intents

### System

- `GET /health`: Check system health
- `GET /`: Root endpoint with service status

## Knowledge Graph Integration

This project uses Graphiti as the standard for knowledge graphs. Graphiti provides:

- Temporal knowledge representation
- Episodic memory
- Hybrid search capabilities
- Scalability for real-world applications

The assistant stores user queries, feedback, and learned information as episodes in the knowledge graph, enabling contextual understanding and continuous learning.

## Complex Query Handling

The assistant can handle:

- **Ambiguous queries**: Queries with multiple possible interpretations
- **Multi-intent queries**: Queries containing multiple distinct questions or requests
- **Vague queries**: Queries lacking specific details
- **Complex queries**: Queries requiring reasoning across multiple knowledge domains

## Deployment

For detailed deployment instructions, see [deployment_guide.md](backend/deployment_guide.md).

## License

[MIT License](LICENSE)

## Acknowledgments

- Graphiti for knowledge graph technology
- OpenAI for language model capabilities
- FastAPI for the web framework
