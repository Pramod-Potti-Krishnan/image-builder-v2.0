"""
Test the new multi-model support and batch generation features
"""
import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000/api/v2"

async def test_models_endpoint():
    """Test the models listing endpoint"""
    print("Testing GET /api/v2/models...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/models")
        return response.json()

async def test_single_with_fast_model():
    """Test single image generation with fast model (default)"""
    print("Testing single generation with fast model...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE}/generate",
            json={
                "prompt": "A minimalist icon of a rocket ship in blue and orange",
                "aspect_ratio": "1:1",
                "archetype": "minimalist_vector_art",
                "options": {"remove_background": True}
            }
        )
        return response.json()

async def test_single_with_standard_model():
    """Test single image generation with standard model"""
    print("Testing single generation with standard model...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE}/generate",
            json={
                "prompt": "A beautiful mountain landscape at golden hour",
                "aspect_ratio": "16:9",
                "model": "imagen-3.0-generate",
                "options": {"store_in_cloud": True}
            }
        )
        return response.json()

async def test_batch_generation():
    """Test batch generation with 3 images"""
    print("Testing batch generation (3 images)...")
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{API_BASE}/generate-batch",
            json={
                "requests": [
                    {
                        "prompt": "Abstract geometric pattern in teal and purple",
                        "aspect_ratio": "2:7",
                        "model": "imagen-3.0-fast-generate"
                    },
                    {
                        "prompt": "Modern tech startup logo with gradient",
                        "aspect_ratio": "1:1",
                        "archetype": "minimalist_vector_art",
                        "model": "imagen-3.0-fast-generate"
                    },
                    {
                        "prompt": "Futuristic cityscape at night",
                        "aspect_ratio": "16:9",
                        "model": "imagen-3.0-generate"
                    }
                ],
                "max_concurrent": 3
            }
        )
        return response.json()

async def main():
    results = {
        "timestamp": datetime.now().isoformat(),
        "models": None,
        "single_fast": None,
        "single_standard": None,
        "batch": None,
        "errors": []
    }
    
    try:
        # Test models endpoint
        results["models"] = await test_models_endpoint()
        print(f"✅ Models endpoint: {len(results['models'].get('models', []))} models available")
    except Exception as e:
        results["errors"].append(f"Models endpoint error: {str(e)}")
        print(f"❌ Models endpoint failed: {e}")
    
    try:
        # Test single with fast model
        results["single_fast"] = await test_single_with_fast_model()
        if results["single_fast"].get("success"):
            print(f"✅ Fast model generation: {results['single_fast']['metadata']['generation_time_ms']}ms")
        else:
            print(f"❌ Fast model failed: {results['single_fast'].get('error')}")
    except Exception as e:
        results["errors"].append(f"Fast model error: {str(e)}")
        print(f"❌ Fast model failed: {e}")
    
    try:
        # Test single with standard model
        results["single_standard"] = await test_single_with_standard_model()
        if results["single_standard"].get("success"):
            print(f"✅ Standard model generation: {results['single_standard']['metadata']['generation_time_ms']}ms")
        else:
            print(f"❌ Standard model failed: {results['single_standard'].get('error')}")
    except Exception as e:
        results["errors"].append(f"Standard model error: {str(e)}")
        print(f"❌ Standard model failed: {e}")
    
    try:
        # Test batch generation
        results["batch"] = await test_batch_generation()
        if results["batch"].get("success"):
            print(f"✅ Batch generation: {results['batch']['successful']}/{results['batch']['total_requests']} successful")
        else:
            print(f"⚠️ Batch partial success: {results['batch']['successful']}/{results['batch']['total_requests']}")
    except Exception as e:
        results["errors"].append(f"Batch error: {str(e)}")
        print(f"❌ Batch failed: {e}")
    
    # Save results
    with open("test_results_new_features.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Test complete! Results saved to test_results_new_features.json")
    return results

if __name__ == "__main__":
    asyncio.run(main())
