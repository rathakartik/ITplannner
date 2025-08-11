import requests
import sys
import json
from datetime import datetime

class ITProjectPlannerAPITester:
    def __init__(self, base_url="https://0d8baea8-5b02-4cfd-be37-555809a6cc35.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.conversation_id = None
        self.project_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        if success and response.get("message") == "IT Project Planning Assistant API":
            print("✅ Root endpoint returned correct message")
            return True
        else:
            print("❌ Root endpoint message incorrect")
            return False

    def test_start_conversation(self):
        """Test starting a new conversation"""
        success, response = self.run_test(
            "Start Conversation",
            "POST",
            "chat/start",
            200
        )
        if success and 'id' in response and 'project_id' in response:
            self.conversation_id = response['id']
            self.project_id = response['project_id']
            print(f"✅ Conversation started with ID: {self.conversation_id}")
            print(f"✅ Project ID: {self.project_id}")
            return True
        return False

    def test_chat_flow(self):
        """Test the multi-turn chat conversation"""
        if not self.conversation_id:
            print("❌ No conversation ID available")
            return False

        # Step 1: Initial project details
        success1, response1 = self.run_test(
            "Chat Step 1 - Project Details",
            "POST",
            f"chat/{self.conversation_id}",
            200,
            data={"content": "I want to build a B2B SaaS platform with authentication, dashboard, billing features. Budget 15 lakh, deadline Dec 2025"}
        )

        if not success1:
            return False

        # Step 2: Tech stack details
        success2, response2 = self.run_test(
            "Chat Step 2 - Tech Stack",
            "POST",
            f"chat/{self.conversation_id}",
            200,
            data={"content": "React, Node.js, PostgreSQL, AWS deployment"}
        )

        if not success2:
            return False

        # Step 3: Constraints
        success3, response3 = self.run_test(
            "Chat Step 3 - Constraints",
            "POST",
            f"chat/{self.conversation_id}",
            200,
            data={"content": "Medium complexity, need mobile responsive, team of 4 developers"}
        )

        if success3 and response3.get('step') == 'ready_for_analysis':
            print("✅ Chat flow completed successfully - ready for analysis")
            return True
        else:
            print(f"❌ Chat flow incomplete - current step: {response3.get('step')}")
            return False

    def test_project_analysis(self):
        """Test project analysis with Groq integration"""
        if not self.conversation_id:
            print("❌ No conversation ID available")
            return False

        success, response = self.run_test(
            "Project Analysis",
            "POST",
            f"analyze/{self.conversation_id}",
            200,
            timeout=60  # Longer timeout for LLM processing
        )

        if success and 'tasks' in response and 'total_cost' in response:
            print(f"✅ Analysis completed with {len(response['tasks'])} tasks")
            print(f"✅ Total cost: ₹{response['total_cost']:,.2f}")
            print(f"✅ Duration: {response['total_duration_days']:.1f} days")
            return True
        else:
            print("❌ Analysis failed or incomplete response")
            return False

    def test_get_estimate(self):
        """Test retrieving project estimate"""
        if not self.project_id:
            print("❌ No project ID available")
            return False

        success, response = self.run_test(
            "Get Project Estimate",
            "GET",
            f"estimates/{self.project_id}",
            200
        )

        if success and 'tasks' in response:
            print("✅ Project estimate retrieved successfully")
            return True
        return False

    def test_get_conversation(self):
        """Test retrieving conversation history"""
        if not self.conversation_id:
            print("❌ No conversation ID available")
            return False

        success, response = self.run_test(
            "Get Conversation History",
            "GET",
            f"conversations/{self.conversation_id}",
            200
        )

        if success and 'messages' in response:
            print(f"✅ Conversation retrieved with {len(response['messages'])} messages")
            return True
        return False

def main():
    print("🚀 Starting IT Project Planner API Tests")
    print("=" * 50)
    
    tester = ITProjectPlannerAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Start Conversation", tester.test_start_conversation),
        ("Chat Flow", tester.test_chat_flow),
        ("Project Analysis", tester.test_project_analysis),
        ("Get Estimate", tester.test_get_estimate),
        ("Get Conversation", tester.test_get_conversation),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*50}")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests: {', '.join(failed_tests)}")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())