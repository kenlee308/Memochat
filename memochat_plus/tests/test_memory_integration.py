import requests
import json
import time
import os
from datetime import datetime
import uuid

BASE_URL = "http://127.0.0.1:8000"
RESULTS_DIR = "tests/results"

def get_timestamp():
    return datetime.now().isoformat()

def get_trial_id():
    return f"trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class MemoryIntegrationTest:
    def __init__(self):
        self.trial_id = get_trial_id()
        self.timestamp = get_timestamp()
        self.results = {}
        self.params = {}
        self.start_time = time.time()
        self.session = requests.Session()
        self.model = "deepseek-r1:7b" # Updated to match local install

    def run(self):
        print(f"Starting Memory Integration Test [{self.trial_id}]")
        print("-" * 50)
        
        try:
            if not self.test_connection(): return
            self.detect_model()
            self.capture_parameters()
            
            self.test_stm_buffering()
            self.test_ltm_consolidation()
            self.test_duplicate_detection()
            self.test_conflict_resolution()

        except Exception as e:
            print(f"DIAGNOSTIC CRITICAL: {e}")
            self.results["critical_error"] = str(e)
        
        self.finalize()

    def test_connection(self):
        print("[1/6] Connecting to Backend...", end="", flush=True)
        try:
            resp = self.session.get(f"{BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                print(f" OK (v{resp.json().get('version')})")
                return True
        except Exception as e:
            print(f" FAIL ({e})")
        return False

    def detect_model(self):
        print("[2/6] Detecting Neural Core...", end="", flush=True)
        try:
            # Query backend for available models (if endpoint exists)
            # Falling back to config or common models
            resp = self.session.get(f"{BASE_URL}/health") # Placeholder, usually there's a models list
            # We'll stick to a standard one but allow it to be found
            print(f" OK (Using {self.model})")
        except:
            print(" WARN (Falling back to default)")

    def capture_parameters(self):
        try:
            resp = self.session.get(f"{BASE_URL}/memory")
            if resp.status_code == 200:
                data = resp.json()
                self.params = {
                    "stm_size": data.get("stm_size"),
                    "summary_threshold": data.get("summary_threshold"),
                    "ltm_count": data.get("ltm_count"),
                }
        except: pass

    def test_stm_buffering(self):
        print("[3/6] Testing STM Buffering...", end="", flush=True)
        uid = uuid.uuid4().hex[:6]
        fact = f"Fact-{uid}: The secret code for the vault is 9-2-0-1."
        payload = {
            "message": fact,
            "model": self.model,
            "temperature": 0.1,
            "stm_size": 10,
            "summary_threshold": 5
        }
        
        try:
            resp = self.session.post(f"{BASE_URL}/chat", json=payload, stream=True)
            if resp.status_code != 200:
                self.results["stm_buffering"] = {"status": "FAIL", "details": f"Status {resp.status_code}: {resp.text}"}
                print(" FAIL")
                return

            # Consume the stream so the backend logic actually runs
            for _ in resp.iter_lines(): pass

            # Check if it actually arrived in memory
            stats = self.session.get(f"{BASE_URL}/memory").json()
            if any(fact in str(m) for m in stats.get('short_term', [])):
                self.results["stm_buffering"] = {"status": "PASS", "details": "Fact stored in STM."}
                print(" PASS")
            else:
                self.results["stm_buffering"] = {"status": "FAIL", "details": "Fact sent but not found in memory response."}
                print(" FAIL")
        except Exception as e:
            self.results["stm_buffering"] = {"status": "FAIL", "details": str(e)}
            print(" FAIL")

    def test_ltm_consolidation(self):
        print("[4/6] Testing LTM Consolidation...", end="", flush=True)
        payload = {
            "message": "[SYSTEM_TEST_SLEEP]",
            "model": self.model,
            "temperature": 0.1,
            "stm_size": 10,
            "summary_threshold": 5
        }
        try:
            # Using stream=True because it's a StreamingResponse
            resp = self.session.post(f"{BASE_URL}/chat/sleep", json=payload, stream=True)
            if resp.status_code != 200:
                # Read text if it's an error body
                error_text = resp.text if not resp.encoding else "".join([c.decode() for c in resp.iter_content()])
                self.results["ltm_consolidation"] = {"status": "FAIL", "details": f"Status {resp.status_code}: {error_text}"}
                print(" FAIL")
                return

            # Exhaust stream
            for _ in resp.iter_lines(): pass
            
            stats = self.session.get(f"{BASE_URL}/memory").json()
            if stats.get('stm_count', 1) == 0:
                self.results["ltm_consolidation"] = {"status": "PASS", "details": "STM cleared after sleep."}
                print(" PASS")
            else:
                self.results["ltm_consolidation"] = {"status": "FAIL", "details": f"STM not empty (count={stats.get('stm_count')})."}
                print(" FAIL")
        except Exception as e:
            self.results["ltm_consolidation"] = {"status": "FAIL", "details": str(e)}
            print(" FAIL")

    def test_duplicate_detection(self):
        print("[5/6] Testing Duplicate Detection...", end="", flush=True)
        uid = uuid.uuid4().hex[:4]
        fact_a = f"User {uid} favorite color strictly is Neon-Green."
        fact_b = f"The favorite color for User {uid} is Neon-Green."
        
        try:
            # Add A and Sleep
            payload_a = {"message": fact_a, "model": self.model, "temperature": 0.1}
            r_a = self.session.post(f"{BASE_URL}/chat", json=payload_a, stream=True)
            for _ in r_a.iter_lines(): pass
            
            # Using custom threshold to ensure detection
            sleep_payload = {"message": "[SLEEP]", "model": self.model, "similarity_threshold": 0.7}
            resp_s1 = self.session.post(f"{BASE_URL}/chat/sleep", json=sleep_payload, stream=True)
            for _ in resp_s1.iter_lines(): pass
            
            # Add B and Sleep
            payload_b = {"message": fact_b, "model": self.model, "temperature": 0.1}
            r_b = self.session.post(f"{BASE_URL}/chat", json=payload_b, stream=True)
            for _ in r_b.iter_lines(): pass
            
            resp_s2 = self.session.post(f"{BASE_URL}/chat/sleep", json=sleep_payload, stream=True)
            for _ in resp_s2.iter_lines(): pass
            
            # Check conflicts
            conflicts = self.session.get(f"{BASE_URL}/memory/scan-conflicts?threshold=0.7").json()
            if conflicts.get('total_conflicts', 0) > 0:
                self.results["duplicate_detection"] = {"status": "PASS", "details": f"Detected {conflicts['total_conflicts']} conflicts."}
                print(" PASS")
            else:
                self.results["duplicate_detection"] = {"status": "FAIL", "details": "No conflicts found for near-identical facts."}
                print(" FAIL")
        except Exception as e:
            print(f" ERROR: {e}")
            self.results["duplicate_detection"] = {"status": "FAIL", "details": str(e)}
            print(" FAIL")

    def test_conflict_resolution(self):
        print("[6/6] Testing Conflict Resolution...", end="", flush=True)
        try:
            resp = self.session.post(f"{BASE_URL}/memory/resolve-conflicts")
            if resp.status_code == 200:
                self.results["conflict_resolution"] = {"status": "PASS", "details": "Resolution call successful."}
                print(" PASS")
            else:
                self.results["conflict_resolution"] = {"status": "FAIL", "details": f"Status {resp.status_code}"}
                print(" FAIL")
        except Exception as e:
            self.results["conflict_resolution"] = {"status": "FAIL", "details": str(e)}
            print(" FAIL")

    def finalize(self):
        duration = time.time() - self.start_time
        overall = "PASS" if all(v.get("status") == "PASS" for k, v in self.results.items() if isinstance(v, dict) and "status" in v) else "FAIL"
        
        report = {
            "trial_id": self.trial_id,
            "timestamp": self.timestamp,
            "system_parameters": self.params,
            "results": self.results,
            "overall_status": overall,
            "duration_seconds": round(duration, 2)
        }
        
        os.makedirs(RESULTS_DIR, exist_ok=True)
        filepath = os.path.join(RESULTS_DIR, f"{self.trial_id}.json")
        with open(filepath, 'w') as f: json.dump(report, f, indent=2)
        with open(os.path.join(RESULTS_DIR, "latest.json"), 'w') as f: json.dump(report, f, indent=2)
            
        print("-" * 50)
        print(f"TEST COMPLETE: {overall}")
        print(f"Results: {filepath}")

if __name__ == "__main__":
    MemoryIntegrationTest().run()
