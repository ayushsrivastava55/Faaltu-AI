#!/usr/bin/env python3
"""
Comprehensive Cognee Setup Verification Script

Run this script to diagnose all potential issues with your Cognee integration.
This will help identify exactly what's causing the "503 agent not available" error.

Usage: python verify_cognee_setup.py
"""

import sys
import os
import asyncio
import importlib
import traceback
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def print_check(item, status, details=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {item}")
    if details:
        print(f"   → {details}")

async def main():
    print_header("COGNEE INTEGRATION DIAGNOSTIC REPORT")
    
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    # 1. Check Python Dependencies
    print_header("1. DEPENDENCY CHECK")
    
    dependencies = {
        'cognee': 'Cognee AI memory engine',
        'neo4j': 'Neo4j graph database driver', 
        'fastapi': 'FastAPI web framework',
        'lancedb': 'LanceDB vector database',
        'fastembed': 'FastEmbed embedding library'
    }
    
    missing_deps = []
    for dep, description in dependencies.items():
        try:
            mod = importlib.import_module(dep)
            version = getattr(mod, '__version__', 'unknown')
            print_check(f"{dep} ({description})", True, f"Version: {version}")
        except ImportError:
            print_check(f"{dep} ({description})", False, "NOT INSTALLED")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n⚠️  Install missing dependencies:")
        print(f"   pip install {' '.join(missing_deps)}")
    
    # 2. Check Environment Variables
    print_header("2. ENVIRONMENT VARIABLES")
    
    required_env_vars = {
        'LLM_API_KEY': 'OpenAI/LLM API key',
        'LLM_PROVIDER': 'LLM provider (openai, etc)',
        'GRAPH_DATABASE_URL': 'Neo4j connection URL',
        'GRAPH_DATABASE_USERNAME': 'Neo4j username',
        'GRAPH_DATABASE_PASSWORD': 'Neo4j password'
    }
    
    missing_env_vars = []
    for var, description in required_env_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value[:8] + "..." if len(value) > 8 else value
            if "key" in var.lower() or "password" in var.lower():
                display_value = "*" * len(value)
            print_check(f"{var} ({description})", True, f"Set: {display_value}")
        else:
            print_check(f"{var} ({description})", False, "NOT SET")
            missing_env_vars.append(var)
    
    if missing_env_vars:
        print(f"\n⚠️  Set missing environment variables in .env file:")
        for var in missing_env_vars:
            print(f"   {var}=your_value_here")
    
    # 3. Check File Structure
    print_header("3. FILE STRUCTURE")
    
    required_files = {
        'main.py': 'Main FastAPI application',
        'orchestrator.py': 'Agent orchestrator',
        'agents/cognee_knowledge_agent.py': 'Cognee agent implementation',
        '.env': 'Environment variables file'
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        exists = os.path.exists(file_path)
        print_check(f"{file_path} ({description})", exists)
        if not exists:
            missing_files.append(file_path)
    
    # 4. Test Neo4j Connection
    print_header("4. NEO4J CONNECTIVITY")
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.getenv('GRAPH_DATABASE_URL', 'bolt://localhost:7687')
        username = os.getenv('GRAPH_DATABASE_USERNAME', 'neo4j')
        password = os.getenv('GRAPH_DATABASE_PASSWORD', 'cognee123')
        
        print(f"Testing connection to: {uri}")
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                print_check("Neo4j Connection", True, "Database is accessible")
            else:
                print_check("Neo4j Connection", False, "Unexpected response from database")
        driver.close()
        
    except ImportError:
        print_check("Neo4j Connection", False, "neo4j package not installed")
    except Exception as e:
        print_check("Neo4j Connection", False, f"Connection failed: {str(e)}")
        print("\n💡 To start Neo4j with Docker:")
        print("   docker run --name neo4j-cognee -p 7474:7474 -p 7687:7687 -d")
        print("   --env NEO4J_AUTH=neo4j/cognee123 neo4j:latest")
    
    # 5. Test Cognee Basic Functionality
    print_header("5. COGNEE FUNCTIONALITY")
    
    try:
        import cognee
        print_check("Cognee Import", True)
        
        # Test basic cognee functionality
        try:
            await cognee.add("Test initialization text")
            print_check("Cognee Basic Add", True, "Can add content to Cognee")
        except Exception as e:
            print_check("Cognee Basic Add", False, f"Error: {str(e)}")
            
    except ImportError:
        print_check("Cognee Import", False, "cognee package not installed")
    except Exception as e:
        print_check("Cognee Import", False, f"Import error: {str(e)}")
    
    # 6. Test Agent Import
    print_header("6. AGENT IMPORT TEST")
    
    try:
        # Try to import the Cognee agent
        from FinMate.agents.cognee_knowledge_agent import CogneeKnowledgeIngestionAgent
        print_check("Cognee Agent Import", True)
        
        # Try to initialize the agent
        try:
            agent = CogneeKnowledgeIngestionAgent()
            print_check("Cognee Agent Initialization", True)
            
            # Check if agent is available
            if hasattr(agent, 'is_available'):
                available = agent.is_available()
                error_msg = getattr(agent, 'error_message', None)
                print_check("Cognee Agent Availability", available, 
                          error_msg if error_msg else "Agent ready for use")
            else:
                print_check("Cognee Agent Availability", True, "No availability check method")
                
        except Exception as e:
            print_check("Cognee Agent Initialization", False, f"Error: {str(e)}")
            traceback.print_exc()
            
    except ImportError as e:
        print_check("Cognee Agent Import", False, f"Import error: {str(e)}")
        print("\n💡 Create the agent file using the template provided")
    except Exception as e:
        print_check("Cognee Agent Import", False, f"Unexpected error: {str(e)}")
    
    # 7. Test Orchestrator Integration
    print_header("7. ORCHESTRATOR INTEGRATION")
    
    try:
        # Try to import orchestrator
        if os.path.exists('orchestrator.py'):
            import orchestrator
            print_check("Orchestrator Import", True)
            
            # Check if it has the required structure
            if hasattr(orchestrator, 'AgentOrchestrator'):
                print_check("AgentOrchestrator Class", True)
                
                try:
                    orch = orchestrator.AgentOrchestrator()
                    if hasattr(orch, 'specialist_agents'):
                        agents = list(orch.specialist_agents.keys())
                        print_check("Specialist Agents", True, f"Found: {agents}")
                        
                        # Check if cognee_knowledge agent is registered
                        if 'cognee_knowledge' in agents:
                            print_check("Cognee Agent Registered", True, "Found in specialist_agents")
                        else:
                            print_check("Cognee Agent Registered", False, "Not found in specialist_agents")
                    else:
                        print_check("Specialist Agents", False, "No specialist_agents attribute")
                        
                except Exception as e:
                    print_check("Orchestrator Initialization", False, f"Error: {str(e)}")
            else:
                print_check("AgentOrchestrator Class", False, "Class not found")
        else:
            print_check("Orchestrator File", False, "orchestrator.py not found")
            
    except Exception as e:
        print_check("Orchestrator Integration", False, f"Error: {str(e)}")
    
    # 8. Summary and Recommendations
    print_header("8. SUMMARY AND RECOMMENDATIONS")
    
    if missing_deps:
        print("🔧 INSTALL MISSING DEPENDENCIES:")
        print(f"   pip install {' '.join(missing_deps)}")
        print()
    
    if missing_env_vars:
        print("🔧 SET ENVIRONMENT VARIABLES:")
        print("   Create/update .env file with:")
        for var in missing_env_vars:
            if var == 'LLM_API_KEY':
                print(f"   {var}=your_openai_api_key")
            elif var == 'GRAPH_DATABASE_URL':
                print(f"   {var}=bolt://localhost:7687")
            elif var == 'GRAPH_DATABASE_USERNAME':
                print(f"   {var}=neo4j")
            elif var == 'GRAPH_DATABASE_PASSWORD':
                print(f"   {var}=cognee123")
            else:
                print(f"   {var}=appropriate_value")
        print()
    
    if missing_files:
        print("🔧 CREATE MISSING FILES:")
        for file in missing_files:
            print(f"   {file}")
        print()
    
    print("📋 NEXT STEPS:")
    print("1. Fix any issues identified above")
    print("2. Restart your FastAPI application")
    print("3. Test the /admin/upload/cognee endpoint")
    print("4. Check application logs for any remaining errors")
    
    print_header("DIAGNOSTIC COMPLETE")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
    except Exception as e:
        print(f"\n\nDiagnostic failed with error: {e}")
        traceback.print_exc()
