"""
MemoryManager - Optimized for YAML Configuration and Markdown Persistence.
"""

import os
import json
import time
import logging
import re
from collections import deque
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, user_id: str, config: Dict[str, Any], snapshot_dir: str = "./memory_snapshots"):
        self.user_id = user_id
        self.config = config
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        self.stm_file = os.path.join(snapshot_dir, "short_term_memory.md")
        self.ltm_file = os.path.join(snapshot_dir, "long_term_memory.md")
        self.archive_file = os.path.join(snapshot_dir, "archived_memory.md")
        self.chat_log_file = os.path.join(snapshot_dir, "full_chat_history.md")
        memory_config = config.get("memory", {})
        
        # 1. State Configuration
        self.stm_size = memory_config.get("stm_size", 10)
        self.ltm_max_docs = memory_config.get("ltm_max_docs", 100)
        self.summary_threshold = memory_config.get("summary_threshold", 5)
        self.archive_threshold = memory_config.get("archive_threshold", 5)
        self.clarification_probability = memory_config.get("clarification_probability", 0.5)
        self.memory_db_path = memory_config.get("memory_db_path", "./data/ltm_index")
        
        # 2. State Initialization
        self.stm: deque = deque(maxlen=self.stm_size)
        self.turn_count = 0
        self.consolidation_count = 0 
        self.ltm_metadata: List[Dict] = []
        self.archive_metadata: List[Dict] = []
        
        # 3. Embedding Engine
        embedding_model_name = memory_config.get("embedding_model", 'all-MiniLM-L6-v2')
        logger.info(f"Connecting to embedding model: {embedding_model_name}")
        self.embedder = SentenceTransformer(embedding_model_name)
        # 4. Initialize Core Engine
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        self.ltm_index: Optional[faiss.IndexFlatL2] = None
        
        # 5. Bootstrap State and Prompts
        self.categories: Dict[str, str] = {}
        self.holding_area: List[Dict] = []
        self.graph = nx.DiGraph()
        
        self.load_prompts()
        self._load_ltm() 
        self.load_memory_from_snapshots()

    def load_prompts(self):
        """Load instructions from YAML config."""
        p = self.config.get("prompts", {})
        self.system_role = p.get("system_role", "AI Assistant.")
        self.initial_summarization_prompt = p.get("initial_summarization", "Summarize:\n{stm_content}")
        self.knowledge_consolidation_prompt = p.get("knowledge_consolidation", "Merge:\n{all_existing}\n{new_summary}")
        self.deep_archive_prompt = p.get("deep_archive", "Distill:\n{ltm_content}")
        self.question_generation_prompt = p.get("question_generation", "Q:\n{consolidated}")
        logger.info("Configuration prompts loaded successfully.")

    def sync_all_from_files(self):
        """Public trigger to reload memory layers from snapshots."""
        self.load_memory_from_snapshots()

    def load_memory_from_snapshots(self):
        """Intelligently restores memory from .md or .txt files."""
        snap_dir = "./memory_snapshots"
        if not os.path.exists(snap_dir): return

        # Helper to find file (prefers .md)
        def find_file(name):
            md = os.path.join(snap_dir, f"{name}.md")
            txt = os.path.join(snap_dir, f"{name}.txt")
            return md if os.path.exists(md) else (txt if os.path.exists(txt) else None)

        # 1. LONG-TERM MEMORY
        ltm_path = find_file("long_term_memory")
        if ltm_path:
            try:
                with open(ltm_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract most recent block
                kb_content = ""
                # Handle MD code blocks first
                if "```markdown" in content:
                    kb_content = content.split("```markdown")[-1].split("```")[0].strip()
                elif "CONSOLIDATED KNOWLEDGE BASE:" in content:
                    kb_content = content.split("CONSOLIDATED KNOWLEDGE BASE:")[-1].split("---")[0].strip()
                elif "Content:" in content:
                    kb_content = content.split("Content:")[-1].split("---")[0].strip()

                if kb_content:
                    self._create_new_index()
                    self.ltm_metadata = [{
                        "content": kb_content, 
                        "created_at": datetime.now().isoformat(),
                        "timestamp": time.time()
                    }]
                    self.ltm_index.add(self.embedder.encode([kb_content], convert_to_numpy=True))
                    logger.info(f"LTM RESTORED: {len(kb_content)} chars.")
            except Exception as e: logger.error(f"LTM Restore Fail: {e}")

        # 2. SHORT-TERM MEMORY
        stm_path = find_file("short_term_memory")
        if stm_path:
            try:
                with open(stm_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Simple markdown regex to extract Human/Assistant turns
                turns = []
                # Match "User**: content" or "User: content"
                matches = re.findall(r"\*\*User\*\*:\s*(.*?)\n\n\*\*Assistant\*\*.*?\):\n(.*?)\n\n---", content, re.DOTALL)
                if not matches:
                    # Try legacy .txt format
                    matches = re.findall(r"User:\s*(.*?)\nAI:\s*(.*?)\n\n-", content, re.DOTALL)
                
                for u, ai in matches:
                    turns.append({"input": u.strip(), "output": ai.strip(), "timestamp": time.time()})
                
                self.stm.clear()
                for t in turns: self.stm.append(t)
                self.turn_count = len(turns) % self.summary_threshold
                logger.info(f"STM RESTORED: {len(turns)} turns.")
            except Exception as e: logger.error(f"STM Restore Fail: {e}")

    def _create_new_index(self):
        self.ltm_index = faiss.IndexFlatL2(self.embedding_dim)
        self.ltm_metadata = []

    def _load_ltm(self):
        """Loads the FAISS index from disk if it exists."""
        idx_path = f"{self.memory_db_path}/faiss.index"
        meta_path = f"{self.memory_db_path}/metadata.json"
        if os.path.exists(idx_path) and os.path.exists(meta_path):
            try:
                self.ltm_index = faiss.read_index(idx_path)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.ltm_metadata = json.load(f)
                logger.info("LTM FAISS Index loaded from disk.")
            except Exception as e:
                logger.error(f"LTM Load Error: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _save_ltm(self):
        os.makedirs(self.memory_db_path, exist_ok=True)
        faiss.write_index(self.ltm_index, f"{self.memory_db_path}/faiss.index")
        with open(f"{self.memory_db_path}/metadata.json", 'w', encoding='utf-8') as f:
            json.dump(self.ltm_metadata, f, indent=2)
        self.save_ancillary_data()

    def load_ancillary_data(self):
        """Loads categories, holding area, and relationship graph."""
        try:
            if os.path.exists(self.category_registry_path):
                with open(self.category_registry_path, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
            if os.path.exists(self.holding_area_path):
                with open(self.holding_area_path, 'r', encoding='utf-8') as f:
                    self.holding_area = json.load(f)
            if os.path.exists(self.graph_path):
                self.graph = nx.read_gml(self.graph_path)
            logger.info(f"Ancillary data loaded: {len(self.categories)} categories, {len(self.holding_area)} pending items.")
        except Exception as e:
            logger.error(f"Error loading ancillary data: {e}")

    def save_ancillary_data(self):
        """Saves categories, holding area, and relationship graph."""
        try:
            os.makedirs(os.path.dirname(self.category_registry_path), exist_ok=True)
            with open(self.category_registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=2)
            with open(self.holding_area_path, 'w', encoding='utf-8') as f:
                json.dump(self.holding_area, f, indent=2)
            if self.graph.number_of_nodes() > 0:
                nx.write_gml(self.graph, self.graph_path)
        except Exception as e:
            logger.error(f"Error saving ancillary data: {e}")

    def add_to_stm(self, user_input: str, assistant_output: str, model: str):
        self.stm.append({
            "input": user_input, 
            "output": assistant_output, 
            "model": model,
            "timestamp": time.time()
        })
        self.turn_count += 1
    
    def get_stm_context(self) -> str:
        if not self.stm: return "No recent context."
        return "\n".join([f"User: {m['input']}\nAssistant: {m['output']}" for m in self.stm])
    
    def retrieve_ltm(self, query: str, top_k: int = 2) -> List[str]:
        if not self.ltm_index or self.ltm_index.ntotal == 0: return []
        
        vec = self.embedder.encode([query], convert_to_numpy=True)
        _, indices = self.ltm_index.search(vec, min(top_k, self.ltm_index.ntotal))
        return [self.ltm_metadata[i]['content'] for i in indices[0] if i < len(self.ltm_metadata)]
    
    def should_summarize(self) -> bool:
        return self.turn_count >= self.summary_threshold
    
    def create_summary_prompt(self) -> str:
        return self.initial_summarization_prompt.format(
            stm_content=self.get_stm_context(),
            user_id=self.user_id
        )
    
    def consolidate_knowledge(self, new_summary: str, engine, model: str) -> tuple[str, list[str]]:
        """Simplified consolidation."""
        all_existing = self.ltm_metadata[0]['content'] if self.ltm_metadata else ""
        prompt = self.knowledge_consolidation_prompt.format(
            all_existing=all_existing,
            new_summary=new_summary
        )
        output = engine.generate(model, prompt)
        if "</think>" in output: output = output.split("</think>")[-1].strip()
        return output, []

    def perform_deep_archive(self, engine, model: str):
        if not self.ltm_metadata: return
        ltm_text = self.ltm_metadata[0]['content']
        prompt = self.deep_archive_prompt.format(ltm_content=ltm_text)
        distilled = engine.generate(model, prompt)
        if "</think>" in distilled: distilled = distilled.split("</think>")[-1].strip()
        
        self.archive_metadata.append({"content": distilled, "created_at": datetime.now().isoformat()})
        if len(self.archive_metadata) > 10: self.archive_metadata.pop(0)

    def replace_ltm_with_consolidated(self, kb: str, questions: list[str] = None):
        old = self.ltm_metadata[0].get('content', '') if self.ltm_metadata else ''
        self.ltm_metadata.clear()
        self._create_new_index()
        self.ltm_index.add(self.embedder.encode([kb], convert_to_numpy=True))
        
        self.ltm_metadata.append({
            "content": kb, 
            "old_version": old, 
            "timestamp": time.time(), 
            "created_at": datetime.now().isoformat(), 
            "pending_questions": questions or []
        })
        self._save_ltm()
        self.consolidation_count += 1

    def get_pending_question(self) -> str:
        if self.ltm_metadata and self.ltm_metadata[0].get('pending_questions'):
            import random
            return random.choice(self.ltm_metadata[0]['pending_questions'])
        return None
    
    def remove_pending_question(self, q: str):
        if self.ltm_metadata and q in self.ltm_metadata[0].get('pending_questions', []):
            self.ltm_metadata[0]['pending_questions'].remove(q)
            self._save_ltm()

    def restore_from_archive(self, index: int) -> bool:
        if 0 <= index < len(self.archive_metadata):
            entry = self.archive_metadata[index]
            self.replace_ltm_with_consolidated(entry['content'], [])
            return True
        return False

    def reset_turn_counter(self): self.turn_count = 0
    
    def get_chat_messages(self, user_input: str) -> List[Dict[str, str]]:
        msgs = []
        # Inject dynamic context
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys_content = self.system_role.format(current_time=current_time)
        
        ltm = self.retrieve_ltm(user_input, top_k=1)
        if ltm:
            sys_content += f"\n\nContext from long-term memory: {ltm[0]}"
        
        # Inject Category Info
        if self.categories:
            cat_list = ", ".join(self.categories.keys())
            sys_content += f"\n\nActive Categories in Memory: {cat_list}"

        msgs.append({"role": "system", "content": sys_content})
        for m in self.stm:
            msgs.append({"role": "user", "content": m['input']})
            msgs.append({"role": "assistant", "content": m['output']})
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def get_stats(self) -> Dict:
        return {
            "stm_count": len(self.stm), "stm_max": self.stm_size,
            "ltm_count": len(self.ltm_metadata),
            "long_term_summary": self.ltm_metadata[0]['content'] if self.ltm_metadata else "",
            "archive_count": len(self.archive_metadata), "archive_threshold": self.archive_threshold,
            "turn_count": self.turn_count, "summary_threshold": self.summary_threshold,
            "consolidation_count": self.consolidation_count,
            "system_role": self.system_role
        }

    # --- PERSISTENCE EXPORTERS ---
    def log_exchange(self, user_input: str, ai_output: str, model: str):
        """Append a single exchange to the cumulative Markdown chat log."""
        timestamp = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
        with open(self.chat_log_file, 'a', encoding='utf-8') as f:
            f.write(f"### 💬 Exchange | {timestamp}\n")
            f.write(f"**🤖 Model:** `{model}`\n\n")
            f.write(f"#### 👤 User\n> {user_input}\n\n")
            f.write(f"#### 🤖 Assistant\n{ai_output}\n\n")
            f.write("---\n\n")

    def export_stm(self):
        with open(self.stm_file, 'w', encoding='utf-8') as f:
            f.write("# 🧠 Live Focus (Short-Term Memory)\n")
            f.write(f"> Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            if not self.stm: 
                f.write("_No active context in the current buffer._\n")
            else:
                for i, m in enumerate(self.stm, 1):
                    f.write(f"## [{i}] Message Turn\n")
                    f.write(f"**User**: {m['input']}\n\n")
                    f.write(f"**Assistant** (`{m.get('model', 'unknown')}`):\n{m['output']}\n\n")
                    f.write("---\n")

    def export_ltm(self):
        with open(self.ltm_file, 'w', encoding='utf-8') as f:
            f.write("# 🏛️ Permanent Knowledge Base (Long-Term Truth)\n")
            f.write(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for i, m in enumerate(reversed(self.ltm_metadata), 1):
                f.write(f"## Snapshot version {m.get('created_at', 'v1')}\n")
                f.write(f"```markdown\n{m['content']}\n```\n\n")
                f.write("---\n")

    def export_archive(self):
        with open(self.archive_file, 'w', encoding='utf-8') as f:
            f.write("# 📦 Deep Archival Essence\n")
            f.write(f"> Core identity snapshots distilled over time.\n\n")
            if not self.archive_metadata: 
                f.write("_Deep archive empty. Waiting for consolidation cycles._\n")
            else:
                for i, m in enumerate(reversed(self.archive_metadata), 1):
                    f.write(f"### Archive Node {i} | {m.get('created_at')}\n")
                    f.write(f"> {m['content']}\n\n")

    def export_all(self):
        self.export_stm()
        self.export_ltm()
        self.export_archive()
