#!/usr/bin/env python3
"""
Context Bridge Test Script

Tests the new orchestrator context bridge functionality that enables
seamless conversation flow between ragAgent and reportAgent.
"""

import asyncio
import httpx
import json
from typing import Dict, Any
import time

class ContextBridgeTester:
    """Test the context bridge functionality"""
    
    def __init__(self, orchestrator_url: str = "http://localhost:8000"):
        self.orchestrator_url = orchestrator_url
        self.session_id = "test-session-123"  # Use consistent session ID
        
    async def send_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Send a query to the orchestrator"""
        if session_id is None:
            session_id = self.session_id
            
        payload = {
            "jsonrpc": "2.0",
            "id": f"test-{int(time.time())}",
            "method": "message/send",
            "params": {
                "id": f"task-{int(time.time())}",
                "message": {
                    "role": "user",
                    "messageId": f"msg-{int(time.time())}",
                    "contextId": session_id,
                    "parts": [{"type": "text", "text": query}]
                },
                "configuration": {"acceptedOutputModes": ["text"]}
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.orchestrator_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {"success": True, "result": result}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_basic_connectivity(self) -> bool:
        """Test basic connectivity to orchestrator"""
        print("🔗 Testing basic connectivity...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.orchestrator_url}/agent_card")
                if response.status_code == 200:
                    print("✅ Orchestrator is responding")
                    return True
                else:
                    print(f"❌ Orchestrator responded with status {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Failed to connect to orchestrator: {e}")
            return False
    
    async def test_context_bridge_scenario(self):
        """Test the main context bridge scenario"""
        print("\n🌉 TESTING CONTEXT BRIDGE SCENARIO")
        print("=" * 60)
        
        # Scenario 1: Ask ragAgent about NYC winter
        print("📍 STEP 1: Query ragAgent about NYC winter")
        print("-" * 40)
        
        winter_query = "How was the winter in New York?"
        print(f"🔍 Query: '{winter_query}'")
        
        result1 = await self.send_query(winter_query)
        if result1["success"]:
            print("✅ Query sent successfully")
            print("📊 Expected: Should route to ragAgent")
            # Note: In real scenario, this would search weather data
            print("📝 Response received (check orchestrator logs for routing)")
        else:
            print(f"❌ Query failed: {result1['error']}")
            return
        
        # Wait a moment for processing
        await asyncio.sleep(2)
        
        # Scenario 2: Ask reportAgent to generate report using "it"
        print(f"\n📍 STEP 2: Query reportAgent with pronoun reference")
        print("-" * 40)
        
        report_query = "Generate a report on it"
        print(f"📊 Query: '{report_query}'")
        print("🔗 Expected: Context bridge should resolve 'it' → 'NYC winter analysis'")
        
        result2 = await self.send_query(report_query)
        if result2["success"]:
            print("✅ Query sent successfully")
            print("📊 Expected: Should route to reportAgent with enriched context")
            print("🎯 Context bridge should have:")
            print("   • Detected pronoun 'it' in query")
            print("   • Enriched query with previous NYC winter context")
            print("   • Routed to reportAgent with full context")
        else:
            print(f"❌ Query failed: {result2['error']}")
            return
        
        print("\n✨ CONTEXT BRIDGE TEST COMPLETED")
        print("Check orchestrator logs for context enrichment messages!")
    
    async def test_multiple_queries(self):
        """Test multiple context-dependent queries"""
        print("\n🔄 TESTING MULTIPLE CONTEXT QUERIES")
        print("=" * 60)
        
        queries = [
            ("What's the weather like in California?", "ragAgent"),
            ("How does that compare to New York?", "ragAgent (with context)"),
            ("Create charts showing the comparison", "reportAgent (with context)"),
            ("Save it as a PDF", "reportAgent (with context)")
        ]
        
        for i, (query, expected_routing) in enumerate(queries, 1):
            print(f"\n📍 Query {i}: '{query}'")
            print(f"🎯 Expected: {expected_routing}")
            
            result = await self.send_query(query)
            if result["success"]:
                print("✅ Query sent successfully")
            else:
                print(f"❌ Query failed: {result['error']}")
            
            await asyncio.sleep(1)  # Brief pause between queries
    
    async def demonstrate_without_context_bridge(self):
        """Demonstrate what would happen without context bridge"""
        print("\n🚫 WITHOUT CONTEXT BRIDGE (Previous Behavior)")
        print("=" * 60)
        
        print("Scenario: User asks ragAgent, then reportAgent")
        print("1. 'How was winter in NYC?' → ragAgent responds")
        print("2. 'Generate report on it' → reportAgent gets confused")
        print()
        print("❌ Problems:")
        print("   • reportAgent doesn't know what 'it' refers to")
        print("   • No cross-agent context sharing")
        print("   • User has to repeat information")
        print("   • Broken conversation flow")
    
    async def demonstrate_with_context_bridge(self):
        """Demonstrate the improved behavior with context bridge"""
        print("\n✅ WITH CONTEXT BRIDGE (New Behavior)")
        print("=" * 60)
        
        print("Scenario: User asks ragAgent, then reportAgent")
        print("1. 'How was winter in NYC?' → ragAgent responds")
        print("2. 'Generate report on it' → Context bridge enriches query")
        print()
        print("🌉 Context Bridge Process:")
        print("   1. Detects pronoun 'it' in query")
        print("   2. Looks up conversation history")
        print("   3. Finds previous NYC winter analysis")
        print("   4. Enriches query: 'Generate report on NYC winter analysis'")
        print("   5. Routes to reportAgent with full context")
        print()
        print("✅ Benefits:")
        print("   • Seamless conversation flow")
        print("   • Intelligent pronoun resolution")
        print("   • Cross-agent context sharing")
        print("   • Natural conversation experience")

async def main():
    """Run the context bridge tests"""
    print("🌉 ORCHESTRATOR CONTEXT BRIDGE TESTER")
    print("=" * 60)
    
    tester = ContextBridgeTester()
    
    # Test basic connectivity
    if not await tester.test_basic_connectivity():
        print("\n❌ Cannot connect to orchestrator. Please ensure:")
        print("   1. Orchestrator is running on localhost:8000")
        print("   2. ragAgent is running on localhost:8004")
        print("   3. reportAgent is running on localhost:8003")
        return
    
    # Demonstrate the difference
    await tester.demonstrate_without_context_bridge()
    await tester.demonstrate_with_context_bridge()
    
    # Run actual tests
    await tester.test_context_bridge_scenario()
    await tester.test_multiple_queries()
    
    print("\n🎉 TESTING COMPLETED!")
    print("📋 Summary:")
    print("   • Context bridge enables cross-agent conversation continuity")
    print("   • Pronoun resolution makes conversations more natural")
    print("   • Session management maintains context across agent switches")
    print("   • Users can have seamless multi-agent conversations")
    
    print("\n💡 Next Steps:")
    print("   • Check orchestrator logs for context enrichment messages")
    print("   • Try the improved conversation flow with real agents")
    print("   • Experiment with complex multi-turn conversations")

if __name__ == "__main__":
    asyncio.run(main())
