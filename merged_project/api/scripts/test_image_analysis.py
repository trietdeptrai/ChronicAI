#!/usr/bin/env python3
"""
Test Script for Image Analysis Functionality in ChronicAI.

This script tests:
1. Image upload via /upload/document (OCR extraction)
2. Image analysis via /chat/ with MedGemma (multimodal)

Usage:
    cd api
    uv run python scripts/test_image_analysis.py

Requirements:
    - API server running at http://localhost:8000
    - Ollama running with MedGemma model
    - A test image (will create a sample if not provided)
"""
import asyncio
import base64
import httpx
import os
import sys
from pathlib import Path
from uuid import uuid4

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PATIENT_ID = str(uuid4())  # Generate a test patient ID


def create_sample_medical_text_image():
    """Create a simple test image with medical text using PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a white image with medical-like text
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add sample medical text
        medical_text = """
        Patient Medical Report
        ----------------------
        Name: Test Patient
        Date: 2024-01-15
        
        Chief Complaint: Chest pain
        
        Blood Pressure: 120/80 mmHg
        Heart Rate: 72 bpm
        Temperature: 36.5°C
        
        Diagnosis: Mild hypertension
        
        Prescription:
        - Amlodipine 5mg daily
        - Low sodium diet
        - Exercise 30 min/day
        """
        
        try:
            # Try to use a better font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((50, 50), medical_text, fill='black', font=font)
        
        # Save the image
        test_dir = Path(__file__).parent / "test_assets"
        test_dir.mkdir(exist_ok=True)
        image_path = test_dir / "sample_medical_report.png"
        img.save(image_path)
        
        print(f"✅ Created sample medical image at: {image_path}")
        return str(image_path)
        
    except ImportError:
        print("⚠️  PIL not installed. Using alternative test method.")
        return None


async def test_health_check():
    """Test if the API is running."""
    print("\n" + "="*60)
    print("🔍 Testing API Health...")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print(f"✅ API is running: {response.json()}")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except httpx.ConnectError:
            print("❌ Cannot connect to API. Make sure the server is running:")
            print("   cd api && uv run uvicorn app.main:app --reload")
            return False


async def test_upload_document(image_path: str):
    """Test document upload with OCR extraction."""
    print("\n" + "="*60)
    print("📄 Testing Document Upload (OCR)...")
    print("="*60)
    
    if not image_path or not os.path.exists(image_path):
        print("⚠️  No image available for upload test")
        return None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(image_path, "rb") as f:
            files = {"file": ("test_document.png", f, "image/png")}
            data = {
                "patient_id": TEST_PATIENT_ID,
                "record_type": "notes",
                "title": "Test Medical Report"
            }
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/upload/document",
                    files=files,
                    data=data
                )
                
                if response.status_code == 201:
                    result = response.json()
                    print(f"✅ Document uploaded successfully!")
                    print(f"   Record ID: {result.get('record_id')}")
                    print(f"   Chunks created: {result.get('chunks_created')}")
                    print(f"   Text preview: {result.get('extracted_text_preview', '')[:200]}...")
                    return result
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ Upload error: {e}")
                return None


async def test_chat_with_image(image_path: str):
    """Test chat endpoint with image analysis."""
    print("\n" + "="*60)
    print("🖼️  Testing Chat with Image Analysis (MedGemma)...")
    print("="*60)
    
    if not image_path or not os.path.exists(image_path):
        print("⚠️  No image available for chat test")
        return None
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "patient_id": TEST_PATIENT_ID,
            "message": "Xin hãy phân tích hình ảnh y tế này và cho tôi biết những thông tin quan trọng.",
            "image_path": image_path
        }
        
        print(f"📤 Sending request with image: {image_path}")
        print(f"   Message: {payload['message']}")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/chat/",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Chat with image successful!")
                print(f"\n📝 Response (Vietnamese):")
                print("-" * 40)
                print(result.get('response', 'No response'))
                print("-" * 40)
                print(f"\n📝 Response (English):")
                print("-" * 40)
                print(result.get('response_en', 'No English response'))
                return result
            else:
                print(f"❌ Chat failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return None


async def test_chat_stream_with_image(image_path: str):
    """Test streaming chat endpoint with image analysis."""
    print("\n" + "="*60)
    print("🌊 Testing Streaming Chat with Image...")
    print("="*60)
    
    if not image_path or not os.path.exists(image_path):
        print("⚠️  No image available for streaming test")
        return None
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "patient_id": TEST_PATIENT_ID,
            "message": "Hãy cho tôi biết nội dung của hình ảnh y tế này.",
            "image_path": image_path
        }
        
        print(f"📤 Sending streaming request...")
        
        try:
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/chat/stream",
                json=payload
            ) as response:
                if response.status_code == 200:
                    print("\n📡 Receiving SSE events:")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            import json
                            data = json.loads(line[6:])
                            stage = data.get('stage', 'unknown')
                            message = data.get('message', '')
                            progress = data.get('progress', 0)
                            
                            print(f"   [{stage}] {progress*100:.0f}% - {message}")
                            
                            if stage == 'complete':
                                print(f"\n✅ Streaming complete!")
                                return data
                else:
                    print(f"❌ Stream failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Stream error: {e}")
            return None


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🚀 ChronicAI Image Analysis Test Suite")
    print("="*60)
    print(f"API URL: {API_BASE_URL}")
    print(f"Test Patient ID: {TEST_PATIENT_ID}")
    
    # Check if API is running
    if not await test_health_check():
        sys.exit(1)
    
    # Create or find test image
    image_path = create_sample_medical_text_image()
    
    if image_path:
        # Run tests
        await test_upload_document(image_path)
        await test_chat_with_image(image_path)
        # Uncomment to test streaming:
        # await test_chat_stream_with_image(image_path)
    else:
        print("\n⚠️  Could not create test image. Please provide an image manually:")
        print("   python scripts/test_image_analysis.py /path/to/your/image.jpg")
    
    print("\n" + "="*60)
    print("✨ Test suite complete!")
    print("="*60)
    print("\n💡 Tips:")
    print("   - Visit http://localhost:8000/docs for Swagger UI")
    print("   - Use real medical images for better testing")
    print("   - Check Ollama logs if MedGemma isn't responding")


if __name__ == "__main__":
    # Allow passing image path as argument
    if len(sys.argv) > 1:
        custom_image_path = sys.argv[1]
        if os.path.exists(custom_image_path):
            print(f"Using custom image: {custom_image_path}")
            # Override the create function to return the custom path
            create_sample_medical_text_image = lambda: custom_image_path
    
    asyncio.run(main())
