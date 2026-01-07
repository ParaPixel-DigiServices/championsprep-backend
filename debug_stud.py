"""
Enhanced Student Endpoint Debug
Shows exact error messages and response bodies
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_endpoint():
    """Test student endpoint with full error details."""
    
    print("=" * 60)
    print("🔍 DETAILED ENDPOINT TEST")
    print("=" * 60)
    
    # Use your working token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ODljMmYyMi0xY2I1LTRmNDctODJiMi0yMTI5MzBjZWJmOWUiLCJlbWFpbCI6ImFtb2docmFvNjVAZ21haWwuY29tIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzY3NzM5MDc0LCJpYXQiOjE3Njc3MzcyNzQsInR5cGUiOiJhY2Nlc3MifQ.pn33mhetQ_YQ3Z-6pej7wVyWKamOra4sWRzVCCLIEG8"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: /auth/me
        print("\n1️⃣ Testing /auth/me")
        print("-" * 60)
        try:
            response = await client.get(f"{BASE_URL}/auth/me", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        # Test 2: Student materials
        print("\n2️⃣ Testing /student/materials")
        print("-" * 60)
        try:
            response = await client.get(f"{BASE_URL}/student/materials", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Response Body:\n{response.text}")
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    print(f"\nParsed Error:\n{json.dumps(error_data, indent=2)}")
                except:
                    print(f"\nRaw Error Text: {response.text}")
                    
        except Exception as e:
            print(f"Request Error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Try processing endpoint
        print("\n3️⃣ Testing /content/materials/{id}/process")
        print("-" * 60)
        material_id = "edc19b4a-952b-4f64-962c-9479b5a24e6f"
        try:
            response = await client.post(
                f"{BASE_URL}/content/materials/{material_id}/process",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            print(f"Response:\n{response.text}")
        except Exception as e:
            print(f"Error: {str(e)}")
        
        # Test 4: Check what endpoints exist
        print("\n4️⃣ Available Endpoints Check")
        print("-" * 60)
        test_endpoints = [
            "/student/profile",
            "/student/dashboard",
            "/student/chapters",
            "/content/materials",
        ]
        
        for endpoint in test_endpoints:
            try:
                response = await client.get(f"{BASE_URL}{endpoint}", headers=headers)
                status = "✅" if response.status_code < 400 else "❌"
                print(f"{status} {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_endpoint())