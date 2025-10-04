#!/usr/bin/env python3
"""
Simple validation script to check if the basic components are working.
This replaces the MCP validation for the PoC.
"""
import requests
import time
import sys

def check_service_health(url, service_name, timeout=30):
    """Check if a service is responding to health checks"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} is healthy")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    
    print(f"❌ {service_name} health check failed after {timeout}s")
    return False

def main():
    """Main validation function"""
    print("🔍 FreshPoC Wave 1 Validation")
    print("=" * 40)
    
    # List of services to check
    services = [
        ("http://localhost:8011", "Ingestion Service"),
        ("http://localhost:8012", "Miner Service"),
        ("http://localhost:8013", "Analyzer Service"),
        ("http://localhost:8014", "Writer Service"),
        ("http://localhost:8015", "Query API Service"),
        ("http://localhost:8016", "Reporting Service"),
    ]
    
    all_healthy = True
    
    for url, name in services:
        if not check_service_health(url, name):
            all_healthy = False
    
    # Check if reports directory exists and has content
    import os
    if os.path.exists("reports/latest.md"):
        print("✅ Reports directory exists and contains latest.md")
    else:
        print("⚠️  Reports directory or latest.md not found")
    
    print("=" * 40)
    if all_healthy:
        print("🎉 All services are healthy! PoC validation passed.")
        return 0
    else:
        print("❌ Some services failed validation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
