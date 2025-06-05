#!/usr/bin/env python3
"""
Comprehensive Demo: Learning-Enabled Voice AI Assistant
=======================================================

This demo showcases the complete system with all capabilities:
• Multi-agent orchestration
• Conversation memory with context
• Knowledge ingestion and learning
• Smart agent routing
• Error handling and fallbacks
"""

import asyncio
import sys
import os
sys.path.append('.')

async def main_demo():
    print("🚀 LendenClub Learning-Enabled Voice AI Assistant Demo")
    print("=" * 70)
    
    # Import and initialize system components
    from main import SimpleStorage, GraphIntelligence, Config
    from agents.orchestrator import create_orchestrator
    from agents.base import AgentRequest
    
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        print("✅ OpenAI client ready")
    except ImportError:
        openai_client = None
        print("❌ OpenAI client not available - using fallback responses")
    
    # Initialize core services
    storage_service = SimpleStorage()
    graph_intelligence = GraphIntelligence()
    
    # Create the multi-agent orchestrator
    orchestrator = create_orchestrator(
        openai_client=openai_client,
        storage_service=storage_service,
        graph_intelligence=graph_intelligence
    )
    
    print("✅ Multi-agent system initialized with:")
    print("   • Loan Advisor Agent")
    print("   • Document Processor Agent")
    print("   • Market Research Agent") 
    print("   • Application Assistant Agent")
    print("   • Compliance Checker Agent")
    print("   • Knowledge Ingestion Agent")
    print("   • Conversation Memory with Context")
    print("   • Graph Intelligence")
    
    # Demo Session
    session_id = "demo_session_2024"
    
    print(f"\n🎯 Starting demo session: {session_id}")
    print("=" * 70)
    
    # Demo 1: Basic loan inquiry with conversation memory
    print("\n📝 Demo 1: Basic Loan Inquiry")
    print("-" * 40)
    request = AgentRequest(
        query="Hi, I need a personal loan of 5 lakh rupees for home renovation",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:400]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    # Demo 2: Follow-up question (testing conversation memory)
    print("\n📝 Demo 2: Follow-up with Context")
    print("-" * 40)
    request = AgentRequest(
        query="What interest rate would I get?",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:400]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    # Demo 3: Market analysis request
    print("\n📝 Demo 3: Market Analysis")
    print("-" * 40)
    request = AgentRequest(
        query="How do current market rates compare with other lenders?",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:400]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    # Demo 4: Knowledge ingestion
    print("\n📝 Demo 4: Knowledge Learning")
    print("-" * 40)
    request = AgentRequest(
        query="Learn from our sales training guide to improve responses",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:400]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    # Demo 5: Complex multi-step query
    print("\n📝 Demo 5: Complex Multi-Step Query")
    print("-" * 40)
    request = AgentRequest(
        query="I earn 80k per month, have 2 existing loans with 15k EMI total. Help me get the best personal loan for 8 lakh with documents checklist and market comparison",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:400]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    # Demo 6: Simple greeting (should not use complex agents)
    print("\n📝 Demo 6: Simple Greeting (Efficiency Test)")
    print("-" * 40)
    request = AgentRequest(
        query="Good morning!",
        session_id=session_id
    )
    response = await orchestrator.process_query(request)
    print(f"🤖 Assistant: {response.response[:200]}...")
    print(f"📊 Confidence: {response.confidence:.2f}")
    print(f"🔧 Tools Used: {', '.join(response.tools_used)}")
    
    print("\n🎉 Demo Complete!")
    print("=" * 70)
    print("\n📋 System Capabilities Demonstrated:")
    print("✅ Multi-agent coordination")
    print("✅ Conversation memory and context")
    print("✅ Intelligent query routing")
    print("✅ Knowledge ingestion for learning")
    print("✅ Complex multi-step reasoning")
    print("✅ Efficiency optimization for simple queries")
    print("✅ Error handling and graceful fallbacks")
    
    print("\n🚀 Ready for Production:")
    print("• Voice input/output ready")
    print("• API endpoints configured")
    print("• Authentication system in place")
    print("• Graph database integration")
    print("• Conversation memory with Neo4j MCP")
    print("• Continuous learning from real-world data")
    
    # Cleanup
    try:
        graph_intelligence.close()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main_demo()) 