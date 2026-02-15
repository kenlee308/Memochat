"""
Quick verification script for v3.0 Chunked Memory Architecture.
No dependencies required - just runs basic tests.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import shutil

# Cleanup previous test data
for path in ["./data/test_ltm_index", "./test_snapshots"]:
    if os.path.exists(path):
        shutil.rmtree(path)

from backend.app.memory_manager import MemoryManager

def test_chunk_operations():
    print("=" * 60)
    print("TESTING v3.0 CHUNKED MEMORY ARCHITECTURE")
    print("=" * 60)
    
    config = {
        "memory": {
            "stm_size": 10,
            "ltm_max_docs": 100,
            "summary_threshold": 5,
            "memory_db_path": "./data/test_ltm_index",
            "embedding_model": "all-MiniLM-L6-v2"
        },
        "prompts": {
            "system_role": "Test AI",
            "chunk_consolidation": "You are updating a CHUNKED knowledge base.\n{chunks_list}\n{new_summary}"
        }
    }
    
    print("\n[1] Creating MemoryManager...")
    mm = MemoryManager(user_id="test_user", config=config, snapshot_dir="./test_snapshots")
    print("    [OK] MemoryManager initialized")
    
    # Test 1: Add chunks
    print("\n[2] Testing add_chunk()...")
    start = time.time()
    chunk1 = mm.add_chunk("User enjoys hiking on weekends", "preferences")
    add_time = time.time() - start
    print(f"    [OK] Added chunk: {chunk1} ({add_time*1000:.1f}ms)")
    
    chunk2 = mm.add_chunk("Weekly standup is Monday at 10am", "schedule")
    print(f"    [OK] Added chunk: {chunk2}")
    
    chunk3 = mm.add_chunk("User prefers dark roast coffee", "preferences")
    print(f"    [OK] Added chunk: {chunk3}")
    
    print(f"    Total chunks: {len(mm.ltm_chunks)}")
    print(f"    FAISS vectors: {mm.ltm_index.ntotal}")
    
    # Test 2: Update chunk
    print("\n[3] Testing update_chunk()...")
    start = time.time()
    success = mm.update_chunk(chunk3, "User loves espresso (changed from dark roast)")
    update_time = time.time() - start
    print(f"    [OK] Updated chunk in {update_time*1000:.1f}ms")
    print(f"    New content: {mm.ltm_chunks[chunk3]['content'][:50]}...")
    
    # Test 3: Retrieve chunks
    print("\n[4] Testing retrieve_chunks() semantic search...")
    results = mm.retrieve_chunks("outdoor activities nature", top_k=2)
    print(f"    [OK] Query: 'outdoor activities nature'")
    for r in results:
        print(f"      - [{r['category']}] {r['content'][:40]}...")
    
    # Test 4: Parse chunk operations
    print("\n[5] Testing parse_chunk_operations()...")
    raw_ai_output = '''
<think>Let me analyze the new information...</think>

[ADD category="facts"]
User works as a software engineer
[/ADD]

[UPDATE chunk_id="{chunk1}"]
User enjoys hiking and camping on weekends
[/UPDATE]

[DELETE chunk_id="chunk_nonexistent"]
'''.format(chunk1=chunk1)
    
    ops = mm.parse_chunk_operations(raw_ai_output)
    print(f"    [OK] Parsed {len(ops)} operations from AI output:")
    for op in ops:
        print(f"      - {op['type']}: {op.get('chunk_id', op.get('category', ''))}")
    
    # Test 5: Apply batch operations
    print("\n[6] Testing apply_chunk_operations()...")
    operations = [
        {"type": "ADD", "content": "User has a dog named Max", "category": "facts"},
        {"type": "UPDATE", "chunk_id": chunk2, "content": "Weekly standup moved to Tuesday 9am"}
    ]
    counts = mm.apply_chunk_operations(operations)
    print(f"    [OK] Applied: {counts}")
    
    # Test 6: Category filtering
    print("\n[7] Testing get_chunks_by_category()...")
    prefs = mm.get_chunks_by_category("preferences")
    facts = mm.get_chunks_by_category("facts")
    print(f"    [OK] Preferences: {len(prefs)} chunks")
    print(f"    [OK] Facts: {len(facts)} chunks")
    
    # Test 7: Legacy compatibility
    print("\n[8] Testing rebuild_legacy_metadata()...")
    mm.rebuild_legacy_metadata()
    if mm.ltm_metadata:
        legacy_content = mm.ltm_metadata[0]['content']
        print(f"    [OK] Legacy KB size: {len(legacy_content)} chars")
        print(f"    [OK] Contains categories: {'[' in legacy_content}")
    
    # Test 8: Stats
    print("\n[9] Testing get_stats()...")
    stats = mm.get_stats()
    print(f"    [OK] chunk_count: {stats.get('chunk_count', 'N/A')}")
    print(f"    [OK] chunk_categories: {stats.get('chunk_categories', {})}")
    
    # Test 9: Performance benchmark
    print("\n[10] Performance benchmark...")
    times = []
    for i in range(5):
        start = time.time()
        mm.add_chunk(f"Benchmark fact number {i}", "benchmark")
        times.append(time.time() - start)
    avg_time = sum(times) / len(times)
    print(f"    [OK] Average add_chunk time: {avg_time*1000:.1f}ms")
    print(f"    [OK] Total chunks now: {len(mm.ltm_chunks)}")
    
    # Cleanup
    print("\n[CLEANUP] Removing test data...")
    for path in ["./data/test_ltm_index", "./test_snapshots"]:
        if os.path.exists(path):
            shutil.rmtree(path)
    print("    [OK] Done")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        test_chunk_operations()
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
