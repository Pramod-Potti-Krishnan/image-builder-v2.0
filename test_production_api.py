"""
Test the production Railway API with new features
"""
import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://web-production-1b5df.up.railway.app/api/v2"

async def test_models_endpoint():
    """Test the models listing endpoint"""
    print("Testing GET /api/v2/models...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/models")
        return response.json()

async def test_single_with_fast_model():
    """Test single image generation with fast model (default)"""
    print("Testing single generation with fast model (default)...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE}/generate",
            json={
                "prompt": "A minimalist icon of a blue rocket ship launching",
                "aspect_ratio": "1:1",
                "archetype": "minimalist_vector_art",
                "options": {"remove_background": True}
            }
        )
        return response.json()

async def test_single_with_standard_model():
    """Test single image generation with standard model"""
    print("Testing single generation with standard quality model...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE}/generate",
            json={
                "prompt": "A serene mountain landscape at sunset with purple sky",
                "aspect_ratio": "16:9",
                "model": "imagen-3.0-generate"
            }
        )
        return response.json()

async def main():
    results = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "models": None,
        "single_fast": None,
        "single_standard": None,
        "errors": []
    }
    
    try:
        # Test models endpoint
        print("\n=== Testing Models Endpoint ===")
        results["models"] = await test_models_endpoint()
        print(f"✅ Found {len(results['models'].get('models', []))} models")
        print(f"   Default: {results['models'].get('default')}")
    except Exception as e:
        results["errors"].append(f"Models endpoint error: {str(e)}")
        print(f"❌ Models endpoint failed: {e}")
    
    try:
        # Test single with fast model
        print("\n=== Testing Fast Model (Default) ===")
        results["single_fast"] = await test_single_with_fast_model()
        if results["single_fast"].get("success"):
            meta = results["single_fast"]["metadata"]
            print(f"✅ Generation successful!")
            print(f"   Model: {meta.get('model')}")
            print(f"   Time: {meta.get('generation_time_ms')}ms")
            print(f"   Cost: $0.02")
            if results["single_fast"].get("urls"):
                print(f"   URL: {results['single_fast']['urls'].get('transparent') or results['single_fast']['urls'].get('original')}")
        else:
            print(f"❌ Failed: {results['single_fast'].get('error')}")
    except Exception as e:
        results["errors"].append(f"Fast model error: {str(e)}")
        print(f"❌ Fast model failed: {e}")
    
    try:
        # Test single with standard model
        print("\n=== Testing Standard Model ===")
        results["single_standard"] = await test_single_with_standard_model()
        if results["single_standard"].get("success"):
            meta = results["single_standard"]["metadata"]
            print(f"✅ Generation successful!")
            print(f"   Model: {meta.get('model')}")
            print(f"   Time: {meta.get('generation_time_ms')}ms")
            print(f"   Cost: $0.04")
            if results["single_standard"].get("urls"):
                print(f"   URL: {results['single_standard']['urls'].get('original')}")
        else:
            print(f"❌ Failed: {results['single_standard'].get('error')}")
    except Exception as e:
        results["errors"].append(f"Standard model error: {str(e)}")
        print(f"❌ Standard model failed: {e}")
    
    # Save results
    with open("production_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Test complete! Results saved to production_test_results.json")
    return results

if __name__ == "__main__":
    asyncio.run(main())
