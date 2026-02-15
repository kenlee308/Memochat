import requests
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("\n[1/5] Testing System Health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] System Online: v{data.get('version', 'unknown')}")
            return True
    except Exception as e:
        print(f"[FAIL] System Offline: {e}")
    return False

def test_models():
    print("\n[2/5] Testing Neural Core Connectivity (Ollama)...")
    try:
        response = requests.get(f"{BASE_URL}/models")
        models = response.json().get('models', [])
        if models:
            print(f"[OK] Found {len(models)} neural cores.")
            # Return the first available model name
            m = models[0]
            return m.get('name') if isinstance(m, dict) else str(m)
        print("[FAIL] No models found in Ollama.")
        return None
    except Exception as e:
        print(f"[FAIL] Error checking models: {e}")
        return None

def test_memory_indexing():
    print("\n[3/5] Testing Knowledge Indexing (v3.1 Chunks)...")
    try:
        # Check atomic chunks
        response = requests.get(f"{BASE_URL}/memory/chunks")
        if response.status_code == 200:
            data = response.json()
            count = data.get('total_count', 0)
            cats = data.get('categories', [])
            print(f"[OK] Knowledge Base: {count} atomic facts indexed across {len(cats)} categories.")
            return True
        print("[FAIL] Could not retrieve memory chunks.")
    except Exception as e:
        print(f"[FAIL] Memory check error: {e}")
    return False

def test_persistence_integrity():
    print("\n[4/5] Verifying Physical Persistence (Disk Integrity)...")
    data_dir = "./data/ltm_index"
    snapshot_dir = "./memory_snapshots"
    
    # Check FAISS index
    faiss_path = os.path.join(data_dir, "faiss.index")
    chunks_path = os.path.join(data_dir, "chunks.json")
    
    healthy = True
    if os.path.exists(faiss_path):
        print(f"[OK] Vector Index: faiss.index exists ({os.path.getsize(faiss_path)} bytes)")
    else:
        print("[WARN] Vector Index: faiss.index missing (Empty Knowledge Base?)")
        
    if os.path.exists(chunks_path):
        print(f"[OK] Data Store: chunks.json is persistent.")
    else:
        print("[FAIL] Data Store: chunks.json missing!")
        healthy = False
        
    return healthy

def test_consistency_engine():
    print("\n[5/5] Testing Neural Consistency Engine...")
    try:
        # Test manual conflict scan
        response = requests.get(f"{BASE_URL}/memory/scan-conflicts")
        if response.status_code == 200:
            data = response.json()
            conflicts = data.get('total_conflicts', 0)
            print(f"[OK] Consistency Engine: Active. Currently detecting {conflicts} conflicts.")
            return True
        print("[FAIL] Consistency Engine unreachable.")
    except Exception as e:
        print(f"[FAIL] Consistency check error: {e}")
    return False

if __name__ == "__main__":
    print("==================================================")
    print("   MEMOCHAT + SYSTEM DIAGNOSTICS (v3.1)           ")
    print("==================================================")
    
    overall_health = True
    
    if test_health():
        if not test_models(): overall_health = False
        if not test_memory_indexing(): overall_health = False
        if not test_persistence_integrity(): overall_health = False
        if not test_consistency_engine(): overall_health = False
        
        if overall_health:
            print("\n✅ STATUS: SYSTEM HEALTHY")
            print("   The Hybrid Memory Architecture is operational.")
        else:
            print("\n⚠️ STATUS: SYSTEM DEGRADED")
            print("   Some sub-systems are unresponsive.")
    else:
        print("\n❌ STATUS: SYSTEM OFFLINE")
        print("💡 TIP: Start the system using './start_all.bat' before running diagnostics.")
    
    print("==================================================")
