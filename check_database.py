#!/usr/bin/env python3
"""
Quick Neo4j Database Health Check
================================

This script checks your Neo4j database connection and shows basic information
about your conversation memory data.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_neo4j_connection():
    """Check Neo4j database connection and show basic stats"""
    try:
        from neo4j import GraphDatabase
        
        # Get connection details from environment
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        print("🔍 Neo4j Database Health Check")
        print("=" * 40)
        print(f"URI: {uri}")
        print(f"Username: {username}")
        print()
        
        # Test connection
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # Basic connection test
            result = session.run("RETURN 'Connected!' as message")
            message = result.single()["message"]
            print(f"✅ Connection Status: {message}")
            
            # Node counts by type
            print("\n📊 Database Statistics:")
            result = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] as NodeType, count(n) as Count 
                ORDER BY Count DESC
            """)
            
            total_nodes = 0
            for record in result:
                node_type = record["NodeType"] or "Unlabeled"
                count = record["Count"]
                total_nodes += count
                print(f"  {node_type}: {count} nodes")
            
            print(f"  Total Nodes: {total_nodes}")
            
            # Relationship counts
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as RelType, count(r) as Count 
                ORDER BY Count DESC
            """)
            
            relationships = list(result)
            if relationships:
                print("\n🔗 Relationships:")
                total_rels = 0
                for record in relationships:
                    rel_type = record["RelType"]
                    count = record["Count"]
                    total_rels += count
                    print(f"  {rel_type}: {count}")
                print(f"  Total Relationships: {total_rels}")
            else:
                print("\n🔗 No relationships found")
            
            # Recent conversations
            result = session.run("""
                MATCH (s:Session)
                RETURN s.session_id as session_id, s.last_activity as last_activity
                ORDER BY s.last_activity DESC
                LIMIT 5
            """)
            
            sessions = list(result)
            if sessions:
                print("\n💬 Recent Conversation Sessions:")
                for record in sessions:
                    session_id = record["session_id"]
                    last_activity = record["last_activity"]
                    print(f"  {session_id}: {last_activity}")
            else:
                print("\n💬 No conversation sessions found")
            
            # User profiles
            result = session.run("""
                MATCH (p:Person)
                RETURN p.user_id as user_id, p.total_interactions as interactions
                ORDER BY p.total_interactions DESC
                LIMIT 5
            """)
            
            users = list(result)
            if users:
                print("\n👥 User Profiles:")
                for record in users:
                    user_id = record["user_id"]
                    interactions = record["interactions"] or 0
                    print(f"  {user_id}: {interactions} interactions")
            else:
                print("\n👥 No user profiles found")
        
        driver.close()
        
        print("\n" + "=" * 40)
        print("✅ Database check completed successfully!")
        print(f"\n🌐 Access Neo4j Browser at: http://localhost:7474")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        
    except ImportError:
        print("❌ Neo4j driver not installed. Run: pip install neo4j")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check if Neo4j is running")
        print("2. Verify connection details in .env file")
        print("3. Test connection manually at http://localhost:7474")

def show_sample_queries():
    """Show useful Cypher queries for viewing data"""
    print("\n📝 Useful Cypher Queries:")
    print("=" * 40)
    
    queries = [
        ("View all conversation sessions", "MATCH (s:Session) RETURN s LIMIT 10"),
        ("View user profiles", "MATCH (p:Person) RETURN p LIMIT 10"),
        ("View recent conversation turns", "MATCH (e:Event) RETURN e ORDER BY e.timestamp DESC LIMIT 10"),
        ("Count nodes by type", "MATCH (n) RETURN labels(n)[0] as Type, count(n) as Count"),
        ("View conversation flow", "MATCH (s:Session)-[:CONTAINS]->(e:Event) RETURN s.session_id, e.user_query, e.system_response ORDER BY e.timestamp"),
        ("View user financial data", "MATCH (p:Person)-[:HAS_ATTRIBUTE]->(a:Attribute) RETURN p.user_id, a.type, a.value"),
        ("Most discussed topics", "MATCH (e:Event)-[:DISCUSSES]->(c:Concept) RETURN c.value, count(e) as frequency ORDER BY frequency DESC")
    ]
    
    for description, query in queries:
        print(f"\n🔍 {description}:")
        print(f"   {query}")

if __name__ == "__main__":
    check_neo4j_connection()
    show_sample_queries() 