import asyncio
import os
from neo4j import GraphDatabase
import cognee

async def inspect_cognee_data():
    """Script to inspect uploaded data in Cognee/Neo4j"""
    
    # 1. Check Cognee datasets
    print("=== COGNEE DATASETS ===")
    try:
        # List available datasets (if Cognee supports this)
        datasets = await cognee.get_datasets()  # This might not exist - check Cognee docs
        print(f"Available datasets: {datasets}")
    except Exception as e:
        print(f"Could not list datasets: {e}")
    
    # 2. Search for recent web content
    print("\n=== RECENT WEB CONTENT ===")
    try:
        results = await cognee.search("https://www.lendenclub.com/terms-of-services/")
        print(f"Found {len(results) if results else 0} web-related items:")
        for i, result in enumerate(results[:5] if results else []):
            print(f"{i+1}. {str(result)[:200]}...")
    except Exception as e:
        print(f"Search failed: {e}")
    
    # 3. Direct Neo4j inspection
    print("\n=== NEO4J DATABASE CONTENT ===")
    try:
        uri = os.getenv('GRAPH_DATABASE_URL')
        username = os.getenv('GRAPH_DATABASE_USERNAME') 
        password = os.getenv('GRAPH_DATABASE_PASSWORD')
        
        if all([uri, username, password]):
            driver = GraphDatabase.driver(uri, auth=(username, password))
            
            with driver.session() as session:
                # Count total nodes
                result = session.run("MATCH (n) RETURN count(n) as total_nodes")
                total_nodes = result.single()["total_nodes"]
                print(f"Total nodes in database: {total_nodes}")
                
                # Show node types/labels
                result = session.run("CALL db.labels()")
                labels = [record["label"] for record in result]
                print(f"Node types: {labels}")
                
                # Show recent nodes (if they have timestamps)
                result = session.run("""
                    MATCH (n) 
                    WHERE exists(n.created_at) OR exists(n.timestamp)
                    RETURN n 
                    ORDER BY coalesce(n.created_at, n.timestamp) DESC 
                    LIMIT 10
                """)
                print("\nRecent nodes:")
                for record in result:
                    node = record["n"]
                    print(f"- {dict(node)}")
                
                # Search for URL-related content
                result = session.run("""
                    MATCH (n) 
                    WHERE toString(n) CONTAINS 'http' OR 
                          any(prop in keys(n) WHERE toString(n[prop]) CONTAINS 'http')
                    RETURN n LIMIT 5
                """)
                print("\nURL-related nodes:")
                for record in result:
                    node = record["n"]
                    print(f"- {dict(node)}")
            
            driver.close()
        else:
            print("Neo4j environment variables not set")
            
    except Exception as e:
        print(f"Neo4j inspection failed: {e}")

# Additional utility functions
async def search_by_dataset(dataset_name="web_content"):
    """Search within a specific dataset"""
    try:
        # This depends on how Cognee handles datasets
        results = await cognee.search("", dataset_name=dataset_name)
        return results
    except Exception as e:
        print(f"Dataset search failed: {e}")
        return []

async def get_processing_status():
    """Check if your Cognee agent is working"""
    try:
        # Test basic functionality
        await cognee.add("test content")
        await cognee.cognify()
        results = await cognee.search("test")
        print(f"✅ Cognee is working. Found {len(results) if results else 0} test results")
        return True
    except Exception as e:
        print(f"❌ Cognee status check failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(inspect_cognee_data())