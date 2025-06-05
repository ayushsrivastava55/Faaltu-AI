# LendenClub Voice AI Assistant

A sophisticated conversational agent system that leverages voice input, natural language processing, and reinforcement learning to provide an intelligent, adaptive financial services assistant for LendenClub's lending platform.

## 🚀 Features

- **Voice & Text Processing**: Real-time speech recognition using Faster Whisper
- **Intelligent Specialist Agents**: Domain-specific experts working together to solve complex queries
- **Reinforcement Learning**: Self-optimizing conversation strategies that improve over time
- **Knowledge Integration**: Continuous learning from FAQs, documentation, and real-world conversations
- **Multi-turn Memory**: Long and short-term conversation memory with Neo4j graph storage
- **API-first Design**: Complete RESTful API for seamless integration
- **Production Ready**: Docker containerization, efficient resource usage, and scalable architecture

## 🧠 Agent Architecture

The system uses a modular, multi-agent architecture including:

- **Orchestrator**: Coordinates all specialist agents and determines the optimal workflow
- **Loan Advisor**: Provides personalized loan recommendations and financial advice
- **Market Researcher**: Delivers real-time market analysis and competitor insights
- **Application Assistant**: Offers step-by-step guidance through the loan application process
- **Document Processor**: Analyzes and validates documentation requirements
- **Compliance Checker**: Ensures regulatory compliance and risk assessment
- **Knowledge Ingestion**: Continuously learns from new data sources
- **RL Optimizer**: Uses reinforcement learning to optimize conversation strategies

## 🔄 Reinforcement Learning System

The RL system transforms the assistant from a knowledge-based AI into an outcome-optimized system that:

- Uses a multi-armed bandit algorithm to select optimal conversation strategies
- Tracks real-world outcomes and rewards (conversions, customer satisfaction, etc.)
- Automatically optimizes for different customer profiles
- Continuously improves with every conversation

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI
- **Voice Processing**: Faster Whisper
- **AI/ML**: OpenAI API, Custom Reinforcement Learning
- **Knowledge Storage**: Neo4j Graph Database
- **Frontend**: React with modern UI components
- **Deployment**: Docker, docker-compose

## 🏃‍♀️ Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- Docker and docker-compose (recommended for easy setup)

### Installation

#### Using Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/username/realistic-voice-ai.git
cd realistic-voice-ai

# Create config file from example
cp env_example.txt .env

# Edit configuration
nano .env  # Add your OpenAI API key and other settings

# Start the application
docker-compose up -d
```

#### Manual Setup

```bash
# Clone repository
git clone https://github.com/username/realistic-voice-ai.git
cd realistic-voice-ai

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: For Neo4j MCP memory
pip install -r requirements-neo4j-mcp.txt

# Create config file from example
cp env_example.txt .env

# Edit configuration
nano .env  # Add your OpenAI API key and other settings

# Start the application
python main.py
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 📡 API Endpoints

- **GET /health**: System health check
- **POST /query**: Text-based queries
- **POST /voice-query**: Voice input processing
- **POST /transcribe**: Audio transcription
- **GET /agents**: List available AI agents
- **POST /rl/strategy**: Get optimal conversation strategy
- **POST /rl/track-outcome**: Track conversation outcomes
- **GET /rl/performance**: View learning analytics

## 🧪 Testing

```bash
# Test RL system
python test_rl_system.py

# Test basic API functionality
curl http://localhost:8080/health
```

## 🔐 Security

- Environment variables for sensitive configuration
- Authentication with JWT tokens
- Rate limiting on API endpoints
- Secure handling of customer data

## 📈 Business Impact

The Voice AI Assistant is expected to deliver:

- 20-35% increase in conversion rates
- 40-50% improvement in customer satisfaction
- 25-30% gain in operational efficiency
- Enhanced data collection for business intelligence

## 📜 License

[MIT License](LICENSE)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🙏 Acknowledgements

- [OpenAI](https://openai.com/) for advanced language models
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for efficient speech recognition
- [Neo4j](https://neo4j.com/) for graph database capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the high-performance web framework
