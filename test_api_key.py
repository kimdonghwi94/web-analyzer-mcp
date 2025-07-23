#!/usr/bin/env python3
"""
Test script to verify API key authentication works correctly
"""
import requests
import json
import os

# Test configuration
BASE_URL = "http://localhost:8002"
TEST_API_KEY = "test-api-key-123"

def test_api_key_auth():
    """Test API key authentication on main API endpoints"""
    
    print("🧪 Testing API key authentication...")
    
    # Test 1: Health check (no auth required)
    print("\n1. Testing health check endpoint (no auth)...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: MCP endpoint without API key (should fail)
    print("\n2. Testing MCP endpoint without API key...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/tools/call",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "test_tool",
                    "arguments": {}
                }
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: MCP endpoint with API key (should work if API key is configured)
    print("\n3. Testing MCP endpoint with API key...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/tools/call",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "test_tool",
                    "arguments": {}
                }
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Bridge status endpoint with API key
    print("\n4. Testing bridge status endpoint with API key...")
    try:
        response = requests.get(
            f"{BASE_URL}/mcp/bridge/status",
            headers={"X-API-Key": TEST_API_KEY}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")

def main():
    print("=" * 60)
    print("API Key Authentication Test")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test API Key: {TEST_API_KEY}")
    print("\nNote: To enable API key authentication, set environment variable:")
    print(f"API_KEYS={TEST_API_KEY}")
    print("=" * 60)
    
    test_api_key_auth()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()