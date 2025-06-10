"""
Cognee Integration Testing Script
================================

This script helps you test the Cognee integration with your agent system.
Run this after completing the integration to verify everything works correctly.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
import requests
import tempfile

# Test configuration
API_BASE_URL = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"  # Change this to match your configuration


class CogneeIntegrationTester:
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_health_check(self):
        """Test if the service is running and Cognee is available"""
        print("🔍 Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            health_data = response.json()
            
            print(f"✅ Service Status: {health_data.get('status', 'unknown')}")
            
            services = health_data.get('services', {})
            cognee_status = services.get('cognee', 'not_found')
            neo4j_status = services.get('neo4j_integration', 'not_found')
            
            print(f"🔹 Cognee Status: {cognee_status}")
            print(f"🔹 Neo4j Integration: {neo4j_status}")
            
            if cognee_status == 'connected':
                print("✅ Cognee is properly connected!")
                return True
            else:
                print("❌ Cognee connection issue detected")
                return False
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def test_cognee_status(self):
        """Test Cognee-specific status endpoint"""
        print("\n🔍 Testing Cognee status endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/cognee/status")
            response.raise_for_status()
            
            status_data = response.json()
            print(f"✅ Cognee Status Response: {json.dumps(status_data, indent=2)}")
            
            if status_data.get('status') == 'healthy':
                print("✅ Cognee is healthy!")
                return True
            else:
                print(f"❌ Cognee status issue: {status_data.get('status')}")
                return False
                
        except Exception as e:
            print(f"❌ Cognee status check failed: {e}")
            return False
    
    def create_test_document(self):
        """Create a test document for upload"""
        test_content = """
# Test Document for Cognee Integration

This is a test document to verify that Cognee can properly ingest and process content.

## Key Information

- **Company**: TechCorp Solutions
- **Industry**: Financial Technology
- **Founded**: 2020
- **CEO**: John Smith
- **Employees**: 150
- **Location**: San Francisco, CA

## Products

1. **LoanBot AI**: Automated loan processing system
2. **CreditScore Plus**: Enhanced credit scoring algorithm
3. **RiskAssess Pro**: Real-time risk assessment platform

## Relationships

- TechCorp Solutions partners with major banks
- John Smith has 15 years of fintech experience
- LoanBot AI processes over 10,000 applications monthly
- The company raised $50M in Series B funding in 2023

## Technologies Used

- Machine Learning for credit scoring
- Natural Language Processing for document analysis
- Neo4j for relationship mapping
- Python and FastAPI for backend services

This document contains various entities and relationships that Cognee should be able to extract and map into a knowledge graph.
        """
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(test_content)
        temp_file.close()
        
        return temp_file.name
    
    def test_file_upload(self):
        """Test file upload to Cognee"""
        print("\n🔍 Testing file upload to Cognee...")
        
        # Create test document
        test_file_path = self.create_test_document()
        
        try:
            # Upload file
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_document.txt', f, 'text/plain')}
                data = {'dataset_name': 'test_integration'}
                
                response = self.session.post(
                    f"{self.base_url}/admin/upload/cognee",
                    files=files,
                    data=data,
                    auth=(ADMIN_USER, ADMIN_PASSWORD)
                )
                
                response.raise_for_status()
                upload_result = response.json()
                
                print(f"✅ Upload Response: {json.dumps(upload_result, indent=2)}")
                
                if upload_result.get('success'):
                    print("✅ File uploaded and processed successfully!")
                    return True
                else:
                    print(f"❌ Upload failed: {upload_result.get('message')}")
                    return False
                    
        except Exception as e:
            print(f"❌ File upload failed: {e}")
            return False
        finally:
            # Clean up temporary file
            try:
                os.unlink(test_file_path)
            except:
                pass
    
    def test_knowledge_search(self):
        """Test knowledge graph search"""
        print("\n🔍 Testing knowledge graph search...")
        
        test_queries = [
            "What companies are mentioned in the documents?",
            "Tell me about TechCorp Solutions",
            "Who is the CEO of TechCorp?",
            "What products does TechCorp offer?",
            "How many employees does TechCorp have?"
        ]
        
        for query in test_queries:
            try:
                print(f"\n🔹 Testing query: '{query}'")
                
                response = self.session.post(
                    f"{self.base_url}/cognee/search",
                    params={'query': query, 'search_type': 'GRAPH_COMPLETION'}
                )
                
                response.raise_for_status()
                search_result = response.json()
                
                print(f"✅ Search successful!")
                print(f"   Response: {search_result.get('response', 'No response')[:200]}...")
                print(f"   Confidence: {search_result.get('confidence', 0)}")
                
            except Exception as e:
                print(f"❌ Search failed for query '{query}': {e}")
                return False
        
        print("✅ All search queries completed!")
        return True
    
    def test_agent_routing(self):
        """Test that queries are properly routed to Cognee agent"""
        print("\n🔍 Testing agent routing for knowledge queries...")
        
        knowledge_queries = [
            "Search the knowledge base for information about companies",
            "What documents have been uploaded?",
            "Tell me what you learned from the uploaded data",
            "Find information about financial technology companies"
        ]
        
        for query in knowledge_queries:
            try:
                print(f"\n🔹 Testing routing for: '{query}'")
                
                response = self.session.post(
                    f"{self.base_url}/query",
                    json={'query': query}
                )
                
                response.raise_for_status()
                query_result = response.json()
                
                agents_consulted = query_result.get('agents_consulted', [])
                reasoning_approach = query_result.get('reasoning_approach', '')
                
                print(f"✅ Query routed successfully!")
                print(f"   Agents consulted: {agents_consulted}")
                print(f"   Reasoning approach: {reasoning_approach}")
                print(f"   Response: {query_result.get('response', 'No response')[:150]}...")
                
                # Check if Cognee agent was used
                if 'cognee_knowledge' in agents_consulted or 'cognee' in reasoning_approach.lower():
                    print("✅ Query properly routed to Cognee agent!")
                else:
                    print("⚠️  Query may not have been routed to Cognee agent")
                
            except Exception as e:
                print(f"❌ Agent routing test failed for query '{query}': {e}")
                return False
        
        print("✅ Agent routing tests completed!")
        return True
    
    def test_url_ingestion(self):
        """Test URL content ingestion"""
        print("\n🔍 Testing URL content ingestion...")
        
        try:
            # Test with a simple, reliable URL (you can change this)
            test_url = "https://httpbin.org/json"  # Simple JSON endpoint for testing
            
            response = self.session.post(
                f"{self.base_url}/admin/upload/url/cognee",
                json={'url': test_url, 'category': 'test'},
                params={'dataset_name': 'test_web_content'},
                auth=(ADMIN_USER, ADMIN_PASSWORD)
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ URL ingestion successful: {result.get('message', 'Success')}")
                return True
            else:
                print(f"❌ URL ingestion failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ URL ingestion test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Cognee Integration Tests\n")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Cognee Status", self.test_cognee_status),
            ("File Upload", self.test_file_upload),
            ("Knowledge Search", self.test_knowledge_search),
            ("Agent Routing", self.test_agent_routing),
            ("URL Ingestion", self.test_url_ingestion),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'=' * 50}")
            print(f"Running Test: {test_name}")
            print('=' * 50)
            
            try:
                result = test_func()
                results[test_name] = result
                
                if result:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
                    
            except Exception as e:
                print(f"💥 {test_name} CRASHED: {e}")
                results[test_name] = False
            
            time.sleep(2)  # Brief pause between tests
        
        # Print summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<20} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Your Cognee integration is working correctly!")
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed. Please check the logs and your configuration.")
            return False


def main():
    """Main function to run the tests"""
    print("Cognee Integration Test Suite")
    print("============================")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding properly at {API_BASE_URL}")
            print("Please make sure your application is running before running tests.")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to server at {API_BASE_URL}")
        print("Please make sure your application is running before running tests.")
        sys.exit(1)
    
    # Run tests
    tester = CogneeIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎊 Congratulations! Your Cognee integration is fully functional!")
        print("\nNext steps:")
        print("1. Upload your own documents through the admin interface")
        print("2. Test with your specific use cases")
        print("3. Monitor the Neo4j browser to see your knowledge graph grow")
        print("4. Explore advanced Cognee features like custom ontologies")
    else:
        print("\n🔧 Some tests failed. Please:")
        print("1. Check your .env configuration")
        print("2. Verify Neo4j is running")
        print("3. Check the application logs")
        print("4. Review the implementation steps")
    
    return success


if __name__ == "__main__":
    main()