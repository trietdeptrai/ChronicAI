#!/usr/bin/env python3
"""
Test the full doctor orchestrator pipeline.
Run: cd api && python test_full_pipeline.py
"""
import asyncio
import logging
import os

# Enable all logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

async def main():
    from app.services.orchestrator import process_doctor_query
    
    print("\n" + "="*60)
    print("FULL PIPELINE DEBUG TEST")
    print("="*60 + "\n")
    
    query = "Tình trạng của bệnh nhân Trần Thị Bình?"
    print(f"📝 Query: {query}\n")
    
    print("Processing pipeline...\n")
    
    async for update in process_doctor_query(query):
        stage = update.get("stage", "unknown")
        message = update.get("message", "")
        progress = update.get("progress", 0)
        
        print(f"[{progress*100:.0f}%] Stage: {stage}")
        print(f"       Message: {message}")
        
        # Print key data at each stage
        if "translation" in update:
            print(f"       Vi→En Translation: {update['translation']}")
        if "mentioned_patients" in update:
            print(f"       Matched Patients: {update['mentioned_patients']}")
        if "response_en" in update:
            resp_en = update['response_en']
            print(f"       MedGemma Response (En, {len(resp_en)} chars):")
            print(f"       {resp_en[:500]}...")
        if "response" in update:
            resp_vi = update['response']
            print(f"       Final Response (Vi, {len(resp_vi)} chars):")
            print(f"       {resp_vi[:500]}...")
        
        print()
    
    print("="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
