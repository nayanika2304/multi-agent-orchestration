#!/usr/bin/env python3
"""
Simple test script for RAG-Report System

Tests basic connectivity to agents once they're running.
Run this after starting all agents manually.
"""

import urllib.request
import urllib.error
import json

def test_agent(url: str, name: str) -> bool:
    """Test if an agent is responding"""
    try:
        with urllib.request.urlopen(f"{url}/agent_card", timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ {name}: {data.get('name', 'Unknown')} - Ready")
                return True
            else:
                print(f"❌ {name}: HTTP {response.status}")
                return False
    except Exception as e:
        print(f"❌ {name}: Connection failed - {e}")
        return False

def main():
    """Main test function"""
    print("🧪 RAG-Report System Test")
    print("=" * 30)
    
    # Test individual agents
    agents = [
        ("http://localhost:8000", "Orchestrator"),
        ("http://localhost:8004", "RAG Agent"),
        ("http://localhost:8003", "Report Agent"),
    ]
    
    print("📡 Testing agent connectivity:")
    results = []
    for url, name in agents:
        result = test_agent(url, name)
        results.append(result)
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} agents responding")
    
    if all(results):
        print("\n🎉 All agents are responding! System connectivity is working.")
        print("\n💡 To test full functionality, use the orchestrator_client:")
        print("  cd orchestrator_client && uv run . --agent http://localhost:8000")
    else:
        print("\n⚠️  Some agents are not responding. Make sure all agents are started:")
        print("  cd orchestrator && uv run -m app")
        print("  cd RAG/ragAgent && uv run -m app") 
        print("  cd RAG/reportAgent && uv run -m app")

if __name__ == "__main__":
    main()
