# test_imports.py
import sys
print("Python path:", sys.path)
print("\n" + "="*70)

try:
    print("1. Testing app import...")
    import app
    print("   ✅ app imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("2. Testing app.api import...")
    import app.api
    print("   ✅ app.api imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("3. Testing app.api.v1 import...")
    import app.api.v1
    print("   ✅ app.api.v1 imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("4. Testing app.api.v1.endpoints import...")
    import app.api.v1.endpoints
    print("   ✅ app.api.v1.endpoints imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("5. Testing app.api.v1.endpoints.auth import...")
    from app.api.v1.endpoints import auth
    print("   ✅ auth module imported successfully")
    print(f"   - Has 'router' attribute: {hasattr(auth, 'router')}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("6. Testing app.api.v1.router import...")
    from app.api.v1 import router
    print("   ✅ router module imported successfully")
    print(f"   - Has 'api_router' attribute: {hasattr(router, 'api_router')}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("="*70)