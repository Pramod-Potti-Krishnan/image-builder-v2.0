#!/usr/bin/env python3
"""
Gemini 2.5 Flash Image - Vertex AI Test Script
===============================================

Tests image generation with gemini-2.5-flash-image via Vertex AI.
Generates 7 test images with different aspect ratios and prompts.

Requirements:
    pip install google-genai>=1.56.0 Pillow

Usage:
    python tests/test_gemini_image.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check and install/upgrade google-genai if needed
try:
    from google import genai
    from google.genai import types
    # Check if ImageConfig exists (requires >= 1.56.0)
    if not hasattr(types, 'ImageConfig'):
        raise ImportError("Need newer version")
except ImportError:
    print("Installing/upgrading google-genai...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-genai", "-q"])
    from google import genai
    from google.genai import types

from PIL import Image
from io import BytesIO
import time


# =============================================================================
# CONFIGURATION
# =============================================================================

# Delay between API calls to avoid rate limiting (seconds)
API_DELAY = 5

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "deckster-xyz")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = "gemini-2.5-flash-image"

OUTPUT_DIR = Path(__file__).parent / "gemini_test_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# =============================================================================
# TEST CASES
# =============================================================================

TEST_CASES = [
    {
        "id": "01",
        "name": "16x9_hero",
        "prompt": "Professional hero slide image: modern tech office with natural lighting, glass walls, collaborative workspace, clean and minimal design, corporate photography style",
        "aspect_ratio": "16:9",
        "description": "Standard presentation format"
    },
    {
        "id": "02",
        "name": "1x1_abstract",
        "prompt": "Abstract gradient background, smooth transition from deep blue to purple, soft ethereal glow, modern minimalist design, suitable for presentation background",
        "aspect_ratio": "1:1",
        "description": "Square format"
    },
    {
        "id": "03",
        "name": "9x16_portrait",
        "prompt": "Professional business person in modern office setting, confident pose, natural lighting, corporate headshot style, clean background",
        "aspect_ratio": "9:16",
        "description": "Portrait/mobile format"
    },
    {
        "id": "04",
        "name": "21x9_panorama",
        "prompt": "Panoramic city skyline at sunset, modern architecture, golden hour lighting, cinematic wide shot, urban landscape photography",
        "aspect_ratio": "21:9",
        "description": "Ultrawide (Gemini-only ratio)"
    },
    {
        "id": "05",
        "name": "2x3_icon",
        "prompt": "Minimalist icon illustration: glowing lightbulb representing innovation and ideas, flat design style, clean lines, simple color palette, centered composition",
        "aspect_ratio": "2:3",
        "description": "Portrait (Gemini-only ratio)"
    },
    {
        "id": "06",
        "name": "16x9_watercolor",
        "prompt": "Beautiful mountain landscape in watercolor painting style, soft pastel colors, artistic brushstrokes, peaceful serene atmosphere, nature art",
        "aspect_ratio": "16:9",
        "description": "Style prompting test"
    },
    {
        "id": "07",
        "name": "16x9_section",
        "prompt": "Abstract presentation section divider: Innovation theme, geometric tech elements, flowing digital lines, modern corporate design, blue and white color scheme, space for text overlay",
        "aspect_ratio": "16:9",
        "description": "Deckster use case"
    },
]


# =============================================================================
# MAIN TEST FUNCTION
# =============================================================================

def run_tests():
    """Run all test cases and save generated images."""

    print("=" * 60)
    print("GEMINI 2.5 FLASH IMAGE - VERTEX AI TEST")
    print("=" * 60)
    print(f"Project:  {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Model:    {MODEL}")
    print(f"Output:   {OUTPUT_DIR}")
    print("=" * 60)
    print()

    # Initialize client for Vertex AI
    print("Initializing Vertex AI client...")
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION
        )
        print("Client initialized successfully!")
    except Exception as e:
        print(f"ERROR: Failed to initialize client: {e}")
        return

    print()

    # Track results
    results = []
    generated_files = []

    # Run each test case
    for i, test in enumerate(TEST_CASES, 1):
        print(f"[{i}/7] Test: {test['name']} ({test['aspect_ratio']})")
        print(f"       {test['description']}")
        print(f"       Prompt: {test['prompt'][:60]}...")

        try:
            # Configure image generation with aspect ratio
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=test["aspect_ratio"]
                )
            )

            # Generate image
            response = client.models.generate_content(
                model=MODEL,
                contents=test["prompt"],
                config=config
            )

            # Extract image from response
            image_data = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_data = part.inline_data.data
                        break

            if image_data:
                # Save image
                filename = f"{test['id']}_{test['name']}.png"
                filepath = OUTPUT_DIR / filename

                # Use PIL to verify and save
                img = Image.open(BytesIO(image_data))
                img.save(filepath, "PNG")

                file_size = len(image_data) / 1024  # KB

                print(f"       SUCCESS - Saved: {filename} ({file_size:.1f} KB)")
                print(f"       Dimensions: {img.size[0]}x{img.size[1]}")

                results.append({
                    "test": test["name"],
                    "status": "SUCCESS",
                    "file": filename,
                    "size_kb": file_size,
                    "dimensions": f"{img.size[0]}x{img.size[1]}"
                })
                generated_files.append(str(filepath))
            else:
                print(f"       FAILED - No image in response")
                results.append({
                    "test": test["name"],
                    "status": "FAILED",
                    "error": "No image in response"
                })

        except Exception as e:
            error_msg = str(e)
            print(f"       FAILED - Error: {error_msg[:100]}")
            results.append({
                "test": test["name"],
                "status": "FAILED",
                "error": error_msg
            })

        # Delay between requests to avoid rate limiting
        if i < len(TEST_CASES):
            print(f"       Waiting {API_DELAY}s before next request...")
            time.sleep(API_DELAY)

        print()

    # Print summary
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"Passed: {success_count}/7")
    print()

    for r in results:
        status_icon = "OK" if r["status"] == "SUCCESS" else "XX"
        if r["status"] == "SUCCESS":
            print(f"  [{status_icon}] {r['test']}: {r['file']} ({r['size_kb']:.1f} KB, {r['dimensions']})")
        else:
            print(f"  [{status_icon}] {r['test']}: {r.get('error', 'Unknown error')[:50]}")

    print()
    print("=" * 60)

    # Open images for validation
    if generated_files:
        print(f"\nOpening {len(generated_files)} images for validation...")
        for filepath in generated_files:
            os.system(f'open "{filepath}"')
        print("Images opened in default viewer.")

    print("\nDone!")
    return results


if __name__ == "__main__":
    run_tests()
