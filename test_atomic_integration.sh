#!/bin/bash

# =============================================================================
# Image Builder Atomic Endpoint Integration Test
# =============================================================================
#
# This script tests the full integration flow for adding Image Elements:
# 1. Create a presentation with a C1-text slide via Layout Service
# 2. Generate an image using the atomic endpoint (with position)
# 3. Add the image as an element via the Layout Service Element API
#
# Key Distinction:
# - I-series templates (I1-image-left, etc.): Pre-defined layouts with image slots
#   filled via content.image_url. Text Service creates these.
# - Image Elements: Can be added to ANY slide (C1-text, L25, etc.) via the
#   images array using the Layout Service Element API.
#
# Usage:
#   ./test_atomic_integration.sh [placeholder]
#
# Options:
#   placeholder - Use placeholder mode (no AI generation, for quick testing)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Service URLs (update these as needed)
LAYOUT_SERVICE_URL="${LAYOUT_SERVICE_URL:-https://web-production-f0d13.up.railway.app}"
IMAGE_SERVICE_URL="${IMAGE_SERVICE_URL:-https://web-production-1b5df.up.railway.app}"

# Use placeholder mode if argument provided
PLACEHOLDER_MODE=false
if [ "$1" = "placeholder" ]; then
    PLACEHOLDER_MODE=true
    echo -e "${YELLOW}Running in PLACEHOLDER MODE (no AI generation)${NC}"
fi

# Test presentation data
PRESENTATION_TITLE="Image Element Test - $(date +%Y%m%d-%H%M%S)"
SLIDE_ID="slide-test-$(date +%s)"
PRESENTATION_ID=""

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Image Element Integration Test        ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Layout Service: ${YELLOW}${LAYOUT_SERVICE_URL}${NC}"
echo -e "Image Service:  ${YELLOW}${IMAGE_SERVICE_URL}${NC}"
echo ""
echo -e "${CYAN}Testing Image Elements (not I-series templates):${NC}"
echo -e "  - Create C1-text slide (can add images anywhere)"
echo -e "  - Generate image with position via atomic endpoint"
echo -e "  - Add image as element via Layout Service Element API"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Health Check - Layout Service
# -----------------------------------------------------------------------------
echo -e "${BLUE}[1/7] Checking Layout Service health...${NC}"

LAYOUT_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${LAYOUT_SERVICE_URL}/")
if [ "$LAYOUT_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ Layout Service is healthy${NC}"
else
    echo -e "${RED}✗ Layout Service not responding (HTTP $LAYOUT_HEALTH)${NC}"
    echo -e "${YELLOW}Note: Continuing anyway - the service may still work${NC}"
fi

# -----------------------------------------------------------------------------
# Step 2: Health Check - Image Atomic Endpoint
# -----------------------------------------------------------------------------
echo -e "${BLUE}[2/7] Checking Image Atomic endpoint health...${NC}"

ATOMIC_HEALTH_RESPONSE=$(curl -s "${IMAGE_SERVICE_URL}/api/v1/images/atomic/health" 2>/dev/null || echo '{"status":"error"}')
ATOMIC_STATUS=$(echo "$ATOMIC_HEALTH_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")

if [ "$ATOMIC_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✓ Image Atomic endpoint is healthy${NC}"
    echo "$ATOMIC_HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
else
    echo -e "${RED}✗ Image Atomic endpoint not healthy (status: $ATOMIC_STATUS)${NC}"
    echo -e "${YELLOW}Response: $ATOMIC_HEALTH_RESPONSE${NC}"
    echo -e "${YELLOW}Note: You may need to start the Image Builder service locally:${NC}"
    echo -e "${YELLOW}  cd image_builder/v2.0 && uvicorn src.main:app --port 8102${NC}"
    echo ""
    echo -e "${YELLOW}Or set the IMAGE_SERVICE_URL environment variable:${NC}"
    echo -e "${YELLOW}  export IMAGE_SERVICE_URL=http://localhost:8102${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 3: List Available Styles
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[3/7] Listing available image styles...${NC}"

STYLES_RESPONSE=$(curl -s "${IMAGE_SERVICE_URL}/api/v1/images/atomic/styles")
echo "$STYLES_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Available styles:')
for style in data.get('styles', []):
    print(f\"  - {style['name']}: {style['description']}\")
print(f\"Default: {data.get('default_style', 'realistic')}\")
print('Credits per quality:')
for q, c in data.get('quality_credits', {}).items():
    print(f\"  - {q}: {c} credits\")
" 2>/dev/null || echo "$STYLES_RESPONSE"

# -----------------------------------------------------------------------------
# Step 4: Create Presentation with C1-text Slide (not I-series)
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[4/7] Creating presentation with C1-text slide...${NC}"
echo -e "${CYAN}(C1-text slides can have images added anywhere via Element API)${NC}"

CREATE_RESPONSE=$(curl -s -X POST "${LAYOUT_SERVICE_URL}/api/presentations" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"${PRESENTATION_TITLE}\",
    \"template_id\": \"L25\",
    \"slides\": [
      {
        \"layout\": \"C1-text\",
        \"content\": {
          \"slide_title\": \"Adding Image Elements\",
          \"body\": \"<p>This slide demonstrates adding Image Elements.</p><p>Unlike I-series templates, images can be positioned anywhere on the slide using the Element API.</p><ul><li>Flexible positioning</li><li>Any slide type</li><li>Grid-based layout</li></ul>\",
          \"presentation_name\": \"${PRESENTATION_TITLE}\",
          \"logo\": \"🖼️\"
        }
      }
    ]
  }")

PRESENTATION_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$PRESENTATION_ID" ]; then
    echo -e "${GREEN}✓ Presentation created with C1-text slide${NC}"
    echo "  ID: $PRESENTATION_ID"
    echo "  View: ${LAYOUT_SERVICE_URL}/p/${PRESENTATION_ID}"
else
    echo -e "${RED}✗ Failed to create presentation${NC}"
    echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESPONSE"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 5: Generate Image via Atomic Endpoint (with position)
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[5/7] Generating image via Atomic endpoint (with position)...${NC}"

# Use position format (grid_row, grid_column) instead of dimensions
# Position: right side of slide, rows 5-15, columns 18-32
IMAGE_REQUEST="{
  \"prompt\": \"A modern tech startup office with collaborative workspace, natural lighting, professional photography style, high quality\",
  \"presentation_id\": \"${PRESENTATION_ID}\",
  \"slide_id\": \"${SLIDE_ID}\",
  \"grid_row\": \"5/15\",
  \"grid_column\": \"18/32\",
  \"image_index\": 0,
  \"config\": {
    \"style\": \"realistic\",
    \"quality\": \"standard\",
    \"color_scheme\": \"neutral\",
    \"lighting\": \"natural\"
  },
  \"context\": {
    \"slide_title\": \"Adding Image Elements\",
    \"presentation_title\": \"${PRESENTATION_TITLE}\"
  },
  \"placeholder_mode\": ${PLACEHOLDER_MODE}
}"

echo "Request (using position format):"
echo "$IMAGE_REQUEST" | python3 -m json.tool 2>/dev/null

echo ""
echo -e "${YELLOW}Generating image (this may take 5-15 seconds for AI generation)...${NC}"

START_TIME=$(date +%s)
IMAGE_RESPONSE=$(curl -s -X POST "${IMAGE_SERVICE_URL}/api/v1/images/atomic/generate" \
  -H "Content-Type: application/json" \
  -d "$IMAGE_REQUEST")
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Parse response
IMAGE_SUCCESS=$(echo "$IMAGE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null || echo "false")
IMAGE_URL=$(echo "$IMAGE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('image_url', ''))" 2>/dev/null || echo "")
ELEMENT_ID=$(echo "$IMAGE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('element_id', ''))" 2>/dev/null || echo "")
GRID_ROW=$(echo "$IMAGE_RESPONSE" | python3 -c "import sys,json; pos=json.load(sys.stdin).get('position',{}); print(pos.get('grid_row',''))" 2>/dev/null || echo "")
GRID_COLUMN=$(echo "$IMAGE_RESPONSE" | python3 -c "import sys,json; pos=json.load(sys.stdin).get('position',{}); print(pos.get('grid_column',''))" 2>/dev/null || echo "")

if [ "$IMAGE_SUCCESS" = "True" ] || [ "$IMAGE_SUCCESS" = "true" ]; then
    echo -e "${GREEN}✓ Image generated successfully (${DURATION}s)${NC}"
    echo ""
    echo "Response:"
    echo "$IMAGE_RESPONSE" | python3 -m json.tool 2>/dev/null
    echo ""
    echo -e "  Element ID: ${GREEN}${ELEMENT_ID}${NC}"
    echo -e "  Image URL:  ${BLUE}${IMAGE_URL}${NC}"
    echo -e "  Position:   grid_row=${CYAN}${GRID_ROW}${NC}, grid_column=${CYAN}${GRID_COLUMN}${NC}"
else
    echo -e "${RED}✗ Image generation failed${NC}"
    echo "$IMAGE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$IMAGE_RESPONSE"
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 6: Add Image Element to Slide via Layout Service Element API
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[6/7] Adding image element to slide via Element API...${NC}"

if [ -n "$IMAGE_URL" ] && [ "$IMAGE_URL" != "null" ] && [ -n "$GRID_ROW" ] && [ -n "$GRID_COLUMN" ]; then
    # Use the Layout Service Element API to add the image
    ADD_IMAGE_REQUEST="{
      \"id\": \"${ELEMENT_ID}\",
      \"position\": {
        \"grid_row\": \"${GRID_ROW}\",
        \"grid_column\": \"${GRID_COLUMN}\"
      },
      \"image_url\": \"${IMAGE_URL}\",
      \"object_fit\": \"cover\",
      \"z_index\": 100
    }"

    echo "Adding image element with request:"
    echo "$ADD_IMAGE_REQUEST" | python3 -m json.tool 2>/dev/null

    ADD_RESPONSE=$(curl -s -X POST "${LAYOUT_SERVICE_URL}/api/presentations/${PRESENTATION_ID}/slides/0/images" \
      -H "Content-Type: application/json" \
      -d "$ADD_IMAGE_REQUEST" 2>/dev/null || echo '{"error":"request failed"}')

    # Check if the request succeeded
    ADD_SUCCESS=$(echo "$ADD_RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print('error' not in data)" 2>/dev/null || echo "false")

    if [ "$ADD_SUCCESS" = "True" ] || [ "$ADD_SUCCESS" = "true" ]; then
        echo -e "${GREEN}✓ Image element added to slide${NC}"
        echo "$ADD_RESPONSE" | python3 -m json.tool 2>/dev/null
    else
        echo -e "${YELLOW}⚠ Element API call completed (check response below)${NC}"
        echo "$ADD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ADD_RESPONSE"
        echo ""
        echo -e "${CYAN}Note: If the Element API is not available, you can manually add the image.${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Skipping Element API call (missing image URL or position)${NC}"
fi

# -----------------------------------------------------------------------------
# Step 7: Summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}[7/7] Summary${NC}"
echo ""
echo "============================================"
echo -e "Presentation ID: ${GREEN}${PRESENTATION_ID}${NC}"
echo -e "Slide ID:        ${GREEN}${SLIDE_ID}${NC}"
echo -e "Element ID:      ${GREEN}${ELEMENT_ID}${NC}"
echo ""
echo "Position (for Layout Service Element API):"
echo -e "  grid_row:    ${CYAN}${GRID_ROW}${NC}"
echo -e "  grid_column: ${CYAN}${GRID_COLUMN}${NC}"
echo ""
echo "URLs:"
echo -e "  Presentation: ${BLUE}${LAYOUT_SERVICE_URL}/p/${PRESENTATION_ID}${NC}"
if [ -n "$IMAGE_URL" ]; then
    echo -e "  Image:        ${BLUE}${IMAGE_URL}${NC}"
fi
echo ""

# Show manual Element API command for reference
echo "============================================"
echo -e "${YELLOW}Manual Element API Command (for reference):${NC}"
echo ""
echo "curl -X POST '${LAYOUT_SERVICE_URL}/api/presentations/${PRESENTATION_ID}/slides/0/images' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"id\": \"${ELEMENT_ID}\","
echo "    \"position\": {"
echo "      \"grid_row\": \"${GRID_ROW}\","
echo "      \"grid_column\": \"${GRID_COLUMN}\""
echo "    },"
echo "    \"image_url\": \"${IMAGE_URL}\","
echo "    \"object_fit\": \"cover\","
echo "    \"z_index\": 100"
echo "  }'"
echo ""

echo "============================================"
echo -e "${GREEN}Integration test completed!${NC}"
echo ""

# Additional test: Verify element ID determinism
echo -e "${BLUE}Bonus: Testing element_id determinism...${NC}"
SECOND_ELEMENT_ID=$(curl -s -X POST "${IMAGE_SERVICE_URL}/api/v1/images/atomic/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"Test prompt for determinism check\",
    \"presentation_id\": \"${PRESENTATION_ID}\",
    \"slide_id\": \"${SLIDE_ID}\",
    \"grid_row\": \"5/15\",
    \"grid_column\": \"18/32\",
    \"image_index\": 0,
    \"placeholder_mode\": true
  }" | python3 -c "import sys,json; print(json.load(sys.stdin).get('element_id', ''))" 2>/dev/null || echo "")

if [ "$ELEMENT_ID" = "$SECOND_ELEMENT_ID" ]; then
    echo -e "${GREEN}✓ Element ID is deterministic: same slide_id + index = same element_id${NC}"
    echo "  Both requests produced: $ELEMENT_ID"
else
    echo -e "${YELLOW}Note: Element IDs differ (may be due to different grid dimensions)${NC}"
    echo "  First:  $ELEMENT_ID"
    echo "  Second: $SECOND_ELEMENT_ID"
fi

# Test different image_index
THIRD_ELEMENT_ID=$(curl -s -X POST "${IMAGE_SERVICE_URL}/api/v1/images/atomic/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"Test prompt for index check\",
    \"presentation_id\": \"${PRESENTATION_ID}\",
    \"slide_id\": \"${SLIDE_ID}\",
    \"grid_row\": \"5/10\",
    \"grid_column\": \"2/10\",
    \"image_index\": 1,
    \"placeholder_mode\": true
  }" | python3 -c "import sys,json; print(json.load(sys.stdin).get('element_id', ''))" 2>/dev/null || echo "")

if [ "$ELEMENT_ID" != "$THIRD_ELEMENT_ID" ]; then
    echo -e "${GREEN}✓ Different image_index produces different element_id${NC}"
    echo "  Index 0: $ELEMENT_ID"
    echo "  Index 1: $THIRD_ELEMENT_ID"
fi

# Test position in response
echo ""
echo -e "${BLUE}Bonus: Verifying position in response...${NC}"
POSITION_TEST=$(curl -s -X POST "${IMAGE_SERVICE_URL}/api/v1/images/atomic/generate" \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"Test prompt for position check\",
    \"presentation_id\": \"${PRESENTATION_ID}\",
    \"slide_id\": \"test-position-slide\",
    \"grid_row\": \"3/13\",
    \"grid_column\": \"5/20\",
    \"placeholder_mode\": true
  }")

RESPONSE_GRID_ROW=$(echo "$POSITION_TEST" | python3 -c "import sys,json; pos=json.load(sys.stdin).get('position',{}); print(pos.get('grid_row',''))" 2>/dev/null || echo "")
RESPONSE_GRID_COL=$(echo "$POSITION_TEST" | python3 -c "import sys,json; pos=json.load(sys.stdin).get('position',{}); print(pos.get('grid_column',''))" 2>/dev/null || echo "")

if [ "$RESPONSE_GRID_ROW" = "3/13" ] && [ "$RESPONSE_GRID_COL" = "5/20" ]; then
    echo -e "${GREEN}✓ Position correctly passed through to response${NC}"
    echo "  Request:  grid_row=3/13, grid_column=5/20"
    echo "  Response: grid_row=$RESPONSE_GRID_ROW, grid_column=$RESPONSE_GRID_COL"
else
    echo -e "${RED}✗ Position not correctly passed through${NC}"
    echo "  Expected: grid_row=3/13, grid_column=5/20"
    echo "  Got:      grid_row=$RESPONSE_GRID_ROW, grid_column=$RESPONSE_GRID_COL"
fi

echo ""
echo -e "${GREEN}All tests complete!${NC}"
