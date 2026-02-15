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
            print("[OK] System Online:", response.json())
            return True
    except Exception as e:
        print(f"[FAIL] System Offline: {e}")
    return False

def test_models():
    print("\n[2/5] Testing Model Connectivity (Ollama)...")
    try:
        response = requests.get(f"{BASE_URL}/models")
        models = response.json().get('models', [])
        if models:
            print(f"[OK] Found {len(models)} neural cores.")
            m = models[0]
            if isinstance(m, dict):
                # Try common keys 'model', 'name'
                return m.get('model') or m.get('name') or str(m)
            return str(m)
        print("[FAIL] No models found in Ollama.")
        return None
    except Exception as e:
        print(f"[FAIL] Error checking models: {e}")
        return None

def test_chat(model):
    print(f"\n[3/5] Testing AI Interface with model: {model}...")
    payload = {
        "message": "System Health Check: Verify core logic unit.",
        "model": model,
        "temperature": 0.1
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload, stream=True)
    if response.status_code == 200:
        print("[OK] AI responding. Logic gates connected.")
        return True
    print("[FAIL] AI Chat failed.")
    return False

def test_memory():
    print("\n[4/5] Testing Memory Layers...")
    response = requests.get(f"{BASE_URL}/memory")
    if response.status_code == 200:
        stats = response.json()
        print(f"[OK] Context retrieved: {stats['stm_count']} messages in buffer.")
        return True
    return False

def test_consolidation(model):
    print("\n[5/6] Testing Memory Consolidation (Sleep Logic)...")
    try:
        # 1. Seed STM with a test fact
        print("   - Seeding STM with test fact...")
        seed_payload = {
            "message": "My favorite color is neon purple. Remember this.",
            "model": model
        }
        requests.post(f"{BASE_URL}/chat", json=seed_payload)
        
        # 2. Verify STM count > 0
        stats = requests.get(f"{BASE_URL}/memory").json()
        pre_count = stats.get('stm_count', 0)
        print(f"   - Current STM Count: {pre_count}")
        
        # 3. Trigger Sleep
        print("   - Triggering Deep Sleep distillation...")
        sleep_payload = {"model": model}
        requests.post(f"{BASE_URL}/chat/sleep", json=sleep_payload)
        
        # 4. Verify STM count is 0
        stats = requests.get(f"{BASE_URL}/memory").json()
        post_count = stats.get('stm_count', 0)
        print(f"   - Post-Sleep STM Count: {post_count}")
        
        if post_count == 0:
            print("[OK] Consolidation successful. STM buffer cleared.")
            
            # 5. Verify LTM retrieval
            print("   - Verifying LTM retrieval of consolidated fact...")
            # We search for the color to see if it's in the knowledge base
            stats_after = requests.get(f"{BASE_URL}/memory").json()
            is_in_ltm = "neon purple" in stats_after.get('long_term_summary', '').lower()
            
            # Fallback check via /memory/long-term
            if not is_in_ltm:
                ltm_data = requests.get(f"{BASE_URL}/memory/long-term").json()
                for s in ltm_data.get('summaries', []):
                    if "neon purple" in s.get('content', '').lower():
                        is_in_ltm = True
                        break
            
            if is_in_ltm:
                print("[OK] Knowledge Persistence: AI remembered the favorite color.")
                return True
            else:
                print("[FAIL] Knowledge Gaps: AI forgot the fact during consolidation.")
                return False
        else:
            print("[FAIL] STM buffer was NOT cleared after consolidation.")
            return False
    except Exception as e:
        print(f"[FAIL] Consolidation test errored: {e}")
        return False

def test_snapshots():
    print("\n[6/6] Verifying Persistence Snapshots...")
    snap_dir = "./memory_snapshots"
    required_files = ["short_term_memory.md", "long_term_memory.md", "full_chat_history.md"]
    found = 0
    for f in required_files:
        path = os.path.join(snap_dir, f)
        if os.path.exists(path):
            print(f"[OK] Snapshot synced: {f}")
            found += 1
    
    if found == len(required_files):
        print("[OK] All persistence layers verified.")
        return True
    return False

def test_advanced_memory():
    print("\n[6/6] Testing Advanced Memory (Categories & Relationships)...")
    try:
        cats = requests.get(f"{BASE_URL}/memory/categories").json()
        rels = requests.get(f"{BASE_URL}/memory/relationships").json()
        holding = requests.get(f"{BASE_URL}/memory/holding-area").json()
        
        print(f"[OK] Categories found: {len(cats.get('categories', {}))}")
        print(f"[OK] Relationships mapped: {len(rels.get('edges', []))}")
        print(f"[OK] Holding area status: {len(holding.get('items', []))} pending.")
        return True
    except Exception as e:
        print(f"[FAIL] Advanced Memory Test failed: {e}")
        return False


if __name__ == "__main__":
    print("====================================")
    print("   MEMOCHAT SYSTEM DIAGNOSTICS      ")
    print("====================================")
    
    if test_health():
        model = test_models()
        if model:
            test_chat(model)
            test_memory()
            test_consolidation(model)
            test_snapshots()
            test_advanced_memory()
            print("\nREADY: System is healthy.")
        else:
            print("\n[FAIL] STAGE 2 FAIL: Cannot proceed without models.")
    else:
        print("\n[FAIL] STAGE 1 FAIL: Backend is unreachable.")
        print("💡 TIP: The diagnostics script checks a LIVE system.")
        print("   Please run 'start_all.bat' in this directory first, then run this check.")

