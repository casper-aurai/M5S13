#!/usr/bin/env python3
"""
Test script to verify Dgraph data flow in the FreshPoC stack.
Run this after starting the stack with 'make up'.
"""
import requests
import json
import time

def test_dgraph_flow():
    """Test the complete Dgraph integration flow"""
    print("🧪 Testing Dgraph Integration Flow")
    print("=" * 40)
    
    # Test 1: Check Dgraph health
    print("1. Checking Dgraph health...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Dgraph is healthy")
        else:
            print(f"   ❌ Dgraph health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Dgraph health check error: {e}")
        return False
    
    # Test 2: Set up schema
    print("2. Setting up Dgraph schema...")
    schema_payload = {
        "schema": """
            name: string @index(term) .
            repo: string @index(exact) .
        """
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/alter",
            headers={"Content-Type": "application/json"},
            json=schema_payload,
            timeout=10
        )
        if response.status_code in [200, 201]:
            print("   ✅ Schema setup successful")
        else:
            print(f"   ❌ Schema setup failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Schema setup error: {e}")
        return False
    
    # Test 3: Create test data
    print("3. Creating test nodes...")
    mutation_payload = {
        "set": [
            {"repo": "jaffle-shop-classic"},
            {"name": "demo-user", "repo": "jaffle-shop-classic"}
        ],
        "commitNow": True
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/mutate",
            headers={"Content-Type": "application/json"},
            json=mutation_payload,
            timeout=10
        )
        if response.status_code in [200, 201]:
            mutation_data = response.json()
            uids = mutation_data.get("data", {}).get("uids", {})
            print(f"   ✅ Created nodes with UIDs: {uids}")
        else:
            print(f"   ❌ Mutation failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Mutation error: {e}")
        return False
    
    # Test 4: Query the data
    print("4. Querying Dgraph data...")
    query_payload = {
        "query": "{ all(func: has(repo)) { uid repo name } }"
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/query",
            headers={"Content-Type": "application/json"},
            json=query_payload,
            timeout=10
        )
        if response.status_code == 200:
            query_data = response.json()
            nodes = query_data.get("data", {}).get("all", [])
            print(f"   ✅ Query successful, found {len(nodes)} nodes")
            for node in nodes:
                print(f"      - UID: {node.get('uid')}, Repo: {node.get('repo')}, Name: {node.get('name')}")
        else:
            print(f"   ❌ Query failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Query error: {e}")
        return False
    
    # Test 5: Test writer service
    print("5. Testing writer service...")
    try:
        response = requests.get("http://localhost:8014/apply", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print(f"   ✅ Writer service successful: {data.get('status')}")
            else:
                print(f"   ❌ Writer service failed: {data.get('error')}")
                return False
        else:
            print(f"   ❌ Writer service error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Writer service error: {e}")
        return False
    
    # Test 6: Test query-api service
    print("6. Testing query-api service...")
    try:
        response = requests.get("http://localhost:8015/query", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                results = data.get("results", {})
                nodes = results.get("all", [])
                print(f"   ✅ Query API successful, found {len(nodes)} nodes")
            else:
                print(f"   ❌ Query API failed: {data.get('error')}")
                return False
        else:
            print(f"   ❌ Query API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Query API error: {e}")
        return False
    
    print("=" * 40)
    print("🎉 All Dgraph integration tests passed!")
    return True

if __name__ == "__main__":
    success = test_dgraph_flow()
    exit(0 if success else 1)
