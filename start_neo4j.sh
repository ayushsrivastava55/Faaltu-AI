#!/bin/bash

# Quick Neo4j Database Setup Script
# ================================

echo "🚀 Starting Neo4j Database with Docker..."
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop existing Neo4j container if running
echo "🔄 Stopping any existing Neo4j containers..."
docker stop realistic-voice-ai-neo4j 2>/dev/null || true
docker rm realistic-voice-ai-neo4j 2>/dev/null || true

# Start new Neo4j container
echo "🎯 Starting Neo4j container..."
docker run -d \
    --name realistic-voice-ai-neo4j \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password123 \
    -e NEO4J_PLUGINS='["apoc"]' \
    -v neo4j_voice_ai_data:/data \
    -v neo4j_voice_ai_logs:/logs \
    neo4j:latest

# Wait a moment for Neo4j to start
echo "⏳ Waiting for Neo4j to start (30 seconds)..."
sleep 30

# Check if Neo4j is running
if docker ps | grep -q realistic-voice-ai-neo4j; then
    echo "✅ Neo4j is running successfully!"
    echo ""
    echo "📊 Database Access Information:"
    echo "================================"
    echo "🌐 Neo4j Browser: http://localhost:7474"
    echo "🔌 Bolt Protocol: bolt://localhost:7687"
    echo "👤 Username: neo4j"
    echo "🔑 Password: password123"
    echo ""
    echo "🧪 Test the connection:"
    echo "python check_database.py"
    echo ""
    echo "📖 View database guide:"
    echo "cat HOW_TO_VIEW_DATABASE.md"
    echo ""
    echo "🛑 To stop Neo4j:"
    echo "docker stop realistic-voice-ai-neo4j"
else
    echo "❌ Failed to start Neo4j. Check Docker logs:"
    echo "docker logs realistic-voice-ai-neo4j"
fi 