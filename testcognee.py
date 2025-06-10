#!/usr/bin/env python3
"""
Voice AI Assistant Diagnostic Script
Run this to identify exact issues before applying fixes
"""

import sys
import os
import importlib
import requests
from datetime import datetime

def check_imports():
    """Check if required packages are installed"""
    print("=== CHECKING PYTHON IMPORTS ===")

    required_packages = [
        ("fastapi", "FastAPI web framework"),
        ("openai", "OpenAI API client"),
        ("cognee", "Cognee knowledge graph"),
        ("pydantic_ai", "PydanticAI agent framework"),
        ("neo4j", "Neo4j graph database"),
        ("faster_whisper", "Faster Whisper speech recognition"),
        ("requests", "HTTP requests library"),
        ("beautifulsoup4", "Web scraping library"),
        ("uvicorn", "ASGI server")
    ]

    results = {}
    for package, description in required_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✅ {package}: Available ({description})")
            results[package] = True
        except ImportError:
            print(f"❌ {package}: Missing ({description})")
            results[package] = False

    return results

def check_environment():
    """Check environment variables"""
    print("\n=== CHECKING ENVIRONMENT VARIABLES ===")

    required_vars = [
        ("OPENAI_API_KEY", "OpenAI API access"),
        ("ADMIN_PASSWORD", "Admin authentication"),
        ("NEO4J_URI", "Neo4j database connection"),
        ("LLM_API_KEY", "Cognee LLM access")
    ]

    results = {}
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set ({description})")
            results[var] = True
        else:
            print(f"❌ {var}: Missing ({description})")
            results[var] = False

    return results

def test_server_endpoints():
    """Test server endpoints if running"""
    print("\n=== TESTING SERVER ENDPOINTS ===")

    base_url = "http://localhost:8080"
    endpoints = [
        ("/health", "Basic health check"),
        ("/debug/detailed-health", "Detailed diagnostics"),
        ("/cognee/status", "Cognee system status")
    ]

    results = {}
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: Working ({description})")
                results[endpoint] = {"status": "working", "code": 200}
            else:
                print(f"⚠️  {endpoint}: Status {response.status_code} ({description})")
                results[endpoint] = {"status": "error", "code": response.status_code}
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Server not running ({description})")
            results[endpoint] = {"status": "server_down", "code": None}
        except Exception as e:
            print(f"❌ {endpoint}: Error - {str(e)} ({description})")
            results[endpoint] = {"status": "error", "code": None, "error": str(e)}

    return results

def test_auth_endpoints():
    """Test authentication-required endpoints"""
    print("\n=== TESTING AUTHENTICATION ENDPOINTS ===")

    base_url = "http://localhost:8080"
    auth_endpoints = [
        ("/admin/uploads/status", "Admin upload status"),
        ("/admin/upload/cognee", "File upload to Cognee")
    ]

    results = {}
    for endpoint, description in auth_endpoints:
        try:
            # Test without auth
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 401:
                print(f"✅ {endpoint}: Auth required (as expected) - {description}")
                results[endpoint] = {"status": "auth_required", "code": 401}
            else:
                print(f"⚠️  {endpoint}: Unexpected status {response.status_code} - {description}")
                results[endpoint] = {"status": "unexpected", "code": response.status_code}
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Server not running - {description}")
            results[endpoint] = {"status": "server_down", "code": None}
        except Exception as e:
            print(f"❌ {endpoint}: Error - {str(e)} - {description}")
            results[endpoint] = {"status": "error", "code": None, "error": str(e)}

    return results

def generate_report(import_results, env_results, endpoint_results, auth_results):
    """Generate diagnostic report"""
    print("\n" + "="*50)
    print("DIAGNOSTIC REPORT")
    print("="*50)

    # Count issues
    missing_imports = [pkg for pkg, status in import_results.items() if not status]
    missing_env = [var for var, status in env_results.items() if not status]
    failed_endpoints = [ep for ep, data in endpoint_results.items() if data["status"] != "working"]
    auth_issues = [ep for ep, data in auth_results.items() if data["status"] not in ["auth_required", "server_down"]]

    print(f"Timestamp: {datetime.now()}")
    print(f"Missing Imports: {len(missing_imports)}")
    print(f"Missing Environment Variables: {len(missing_env)}")
    print(f"Failed Endpoints: {len(failed_endpoints)}")
    print(f"Auth Issues: {len(auth_issues)}")

    print("\n=== PRIORITY FIXES ===")

    if missing_imports:
        print("1. INSTALL MISSING PACKAGES:")
        print(f"   pip install {' '.join(missing_imports)}")

    if missing_env:
        print("2. SET ENVIRONMENT VARIABLES:")
        for var in missing_env:
            print(f"   export {var}=your_value_here")

    if any(data["status"] == "server_down" for data in endpoint_results.values()):
        print("3. START THE SERVER:")
        print("   python main.py")

    if failed_endpoints:
        print("4. FIX SERVER ENDPOINTS:")
        for endpoint in failed_endpoints:
            data = endpoint_results[endpoint]
            if data["status"] != "server_down":
                print(f"   {endpoint}: Status {data['code']}")

    if auth_issues:
        print("5. FIX AUTHENTICATION:")
        for endpoint in auth_issues:
            print(f"   {endpoint}: {auth_results[endpoint]['status']}")

    print("\n=== NEXT STEPS ===")
    print("1. Fix issues in priority order above")
    print("2. Apply code fixes from voice-ai-fixes.md")
    print("3. Re-run this diagnostic script to verify fixes")
    print("4. Run your test suite again")

def main():
    """Run full diagnostic"""
    print("Voice AI Assistant Diagnostic Tool")
    print("=" * 50)

    import_results = check_imports()
    env_results = check_environment()
    endpoint_results = test_server_endpoints()
    auth_results = test_auth_endpoints()

    generate_report(import_results, env_results, endpoint_results, auth_results)

if __name__ == "__main__":
    main()
