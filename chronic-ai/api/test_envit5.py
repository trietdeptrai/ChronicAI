#!/usr/bin/env python3
"""
Quick test script to debug EnviT5 translation.
Run: cd api && python test_envit5.py
"""
import asyncio
import logging

# Enable all logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    from app.services.transformers_client import transformers_client, strip_markdown, clean_translation_output
    
    print("\n" + "="*60)
    print("EnviT5 TRANSLATION DEBUG TEST")
    print("="*60 + "\n")
    
    # Test 1: Simple Vietnamese to English
    test_vi = "Tình trạng của bệnh nhân Trần Thị Bình?"
    print(f"📝 Test 1: Simple Vi→En")
    print(f"   Input: {test_vi}")
    result_en = await transformers_client.translate_vi_to_en(test_vi)
    print(f"   Output: {result_en}")
    print()
    
    # Test 2: English to Vietnamese
    test_en = "The patient has type 2 diabetes with HbA1c of 8.5%. Blood pressure is well controlled."
    print(f"📝 Test 2: Simple En→Vi")
    print(f"   Input: {test_en}")
    result_vi = await transformers_client.translate_en_to_vi(test_en)
    print(f"   Output: {result_vi}")
    print()
    
    # Test 3: Markdown-heavy text (simulating MedGemma output)
    markdown_text = """## Patient Overview

**Patient Name**: Tran Thi Binh
- Primary Diagnosis: Type 2 Diabetes (E11)
- Last Checkup: 2024-01-15

### Current Status
The patient shows good adherence to medication. HbA1c has improved from 9.2% to 8.1% over 3 months.

### Recommendations
1. Continue current metformin dosage
2. Schedule follow-up in 1 month
3. Monitor blood glucose twice daily
"""
    
    print(f"📝 Test 3: Markdown text (before strip)")
    print(f"   Input length: {len(markdown_text)} chars")
    print(f"   First 100 chars: {markdown_text[:100]}...")
    
    # Test stripping
    stripped = strip_markdown(markdown_text)
    print(f"\n📝 Test 3b: After strip_markdown()")
    print(f"   Output length: {len(stripped)} chars")
    print(f"   Content:\n{stripped}")
    
    # Translate the stripped text
    print(f"\n📝 Test 3c: Translating stripped En→Vi")
    result_vi_md = await transformers_client.translate_en_to_vi(markdown_text)
    print(f"   Output:\n{result_vi_md}")
    print()
    
    # Test 4: Verify clean_translation_output
    weird_outputs = [
        "vi: ?? Some translation here",
        "vi: Đây là kết quả",
        "en: This is a result",
        "Normal output without prefix"
    ]
    print(f"📝 Test 4: clean_translation_output()")
    for weird in weird_outputs:
        cleaned = clean_translation_output(weird)
        print(f"   '{weird[:40]}...' → '{cleaned[:40]}...'")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    # Unload model
    await transformers_client.unload_model()

if __name__ == "__main__":
    asyncio.run(main())
