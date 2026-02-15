"""
MemoryManager - Optimized for YAML Configuration and Markdown Persistence.
v3.0 - Chunked Storage Architecture for O(1) incremental updates.
"""

import os
import json
import time
import logging
import re
import uuid
from collections import deque
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

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
        self.summary_threshold = memory_config.get("summary_threshold", 5)
        self.archive_threshold = memory_config.get("archive_threshold", 5)
        self.memory_db_path = memory_config.get("memory_db_path", "./data/ltm_index")
        
        # v3.1: Fact consistency validation settings
        validation_config = memory_config.get("validation", {})
        self.enable_similarity_check = validation_config.get("enable_similarity_check", True)
        self.similarity_threshold = validation_config.get("similarity_threshold", 0.85)
        self.enable_context_aware_consolidation = validation_config.get("enable_context_aware_consolidation", True)
        self.consolidation_context_size = validation_config.get("consolidation_context_size", 10)
        self.validation_log_level = validation_config.get("validation_log_level", "WARNING")
        
        # 2. State Initialization
        self.stm: deque = deque(maxlen=self.stm_size)
        self.turn_count = 0
        self.consolidation_count = 0 
        self.ltm_metadata: List[Dict] = []  # Legacy: single KB blob
        self.archive_metadata: List[Dict] = []
        
        # v3.0 Chunked Storage
        self.ltm_chunks: Dict[str, Dict] = {}  # chunk_id -> {content, category, created_at, updated_at}
        self.chunk_index_map: Dict[int, str] = {}  # FAISS vector index -> chunk_id
        self.next_vector_id: int = 0  # Tracks next FAISS index position
        
        # 3. Embedding Engine
        embedding_model_name = memory_config.get("embedding_model", 'all-MiniLM-L6-v2')
        logger.info(f"Connecting to embedding model: {embedding_model_name}")
        self.embedder = SentenceTransformer(embedding_model_name)
        # 4. Initialize Core Engine
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        self.ltm_index: Optional[faiss.IndexFlatL2] = None
        
        # 5. Bootstrap State and Prompts
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
        # v3.0 Chunk-based consolidation
        self.chunk_consolidation_prompt = p.get("chunk_consolidation", "")
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

        # 1. LONG-TERM MEMORY (Only if empty)
        if self.ltm_index and self.ltm_index.ntotal > 0:
            logger.info("LTM already has state. Skipping snapshot restore.")
            return

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
        """Creates a fresh FAISS index and resets all chunk state."""
        self.ltm_index = faiss.IndexFlatL2(self.embedding_dim)
        self.ltm_metadata = []
        self.ltm_chunks = {}
        self.chunk_index_map = {}
        self.next_vector_id = 0

    def _load_ltm(self):
        """Loads the FAISS index and chunks from disk if they exist."""
        idx_path = f"{self.memory_db_path}/faiss.index"
        meta_path = f"{self.memory_db_path}/metadata.json"
        chunks_path = f"{self.memory_db_path}/chunks.json"
        chunk_map_path = f"{self.memory_db_path}/chunk_map.json"
        
        # 1. Load FAISS Index
        if os.path.exists(idx_path):
            try:
                self.ltm_index = faiss.read_index(idx_path)
                logger.info("FAISS index loaded.")
            except Exception as e:
                logger.error(f"FAISS Load Error: {e}")
                self.ltm_index = faiss.IndexFlatL2(self.embedding_dim)
        else:
            self.ltm_index = faiss.IndexFlatL2(self.embedding_dim)

        # 2. Load Legacy Metadata
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.ltm_metadata = json.load(f)
            except Exception as e:
                logger.error(f"Metadata Load Error: {e}")
                self.ltm_metadata = []
        
        # 3. Load v3.0 Chunks
        if os.path.exists(chunks_path):
            try:
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    self.ltm_chunks = json.load(f)
                logger.info(f"Loaded {len(self.ltm_chunks)} chunks.")
            except Exception as e:
                logger.error(f"Chunks Load Error: {e}")
                self.ltm_chunks = {}

        # 4. Load Chunk Map
        if os.path.exists(chunk_map_path):
            try:
                with open(chunk_map_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.chunk_index_map = {int(k): v for k, v in data.items()}
                    self.next_vector_id = max(self.chunk_index_map.keys(), default=-1) + 1
            except Exception as e:
                logger.error(f"Chunk Map Load Error: {e}")
                self.chunk_index_map = {}
        
        # 5. Sync & Rebuild
        if self.ltm_chunks and not self.ltm_metadata:
            self.rebuild_legacy_metadata()
            logger.info("Rebuilt legacy metadata from chunks.")
        
        logger.info(f"LTM Initialized: {len(self.ltm_chunks)} chunks, {self.ltm_index.ntotal} vectors.")

    def _save_ltm(self):
        """Saves FAISS index and all chunk data to disk."""
        os.makedirs(self.memory_db_path, exist_ok=True)
        faiss.write_index(self.ltm_index, f"{self.memory_db_path}/faiss.index")
        
        with open(f"{self.memory_db_path}/metadata.json", 'w', encoding='utf-8') as f:
            json.dump(self.ltm_metadata, f, indent=2)
            
        with open(f"{self.memory_db_path}/chunks.json", 'w', encoding='utf-8') as f:
            json.dump(self.ltm_chunks, f, indent=2)
        with open(f"{self.memory_db_path}/chunk_map.json", 'w', encoding='utf-8') as f:
            json.dump(self.chunk_index_map, f, indent=2)

    # ========== v3.0 CHUNK MANAGEMENT ==========
    
    def add_chunk(self, content: str, category: str = "general") -> str:
        """Adds a single knowledge chunk to the index. Returns the chunk ID."""
        chunk_id = f"chunk_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        # Store chunk metadata
        self.ltm_chunks[chunk_id] = {
            "content": content,
            "category": category,
            "created_at": now,
            "updated_at": now
        }
        
        # Embed and add to FAISS
        embedding = self.embedder.encode([content], convert_to_numpy=True)
        self.ltm_index.add(embedding)
        
        # Track mapping
        self.chunk_index_map[self.next_vector_id] = chunk_id
        self.next_vector_id += 1
        
        logger.info(f"Added chunk {chunk_id} ({len(content)} chars, category={category})")
        return chunk_id
    
    def update_chunk(self, chunk_id: str, new_content: str, category: str = None) -> bool:
        """Updates an existing chunk. Returns False if chunk not found."""
        if chunk_id not in self.ltm_chunks:
            logger.warning(f"Chunk {chunk_id} not found for update.")
            return False
        
        # Update metadata
        self.ltm_chunks[chunk_id]["content"] = new_content
        self.ltm_chunks[chunk_id]["updated_at"] = datetime.now().isoformat()
        if category:
            self.ltm_chunks[chunk_id]["category"] = category
        
        # Find old vector index and mark for deletion (FAISS doesn't support in-place update)
        # We append a new vector and track the new mapping
        old_vector_ids = [vid for vid, cid in self.chunk_index_map.items() if cid == chunk_id]
        for old_vid in old_vector_ids:
            del self.chunk_index_map[old_vid]  # Orphan the old vector (will be ignored in retrieval)
        
        # Add new embedding
        embedding = self.embedder.encode([new_content], convert_to_numpy=True)
        self.ltm_index.add(embedding)
        self.chunk_index_map[self.next_vector_id] = chunk_id
        self.next_vector_id += 1
        
        logger.info(f"Updated chunk {chunk_id} ({len(new_content)} chars)")
        return True
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Marks a chunk as deleted. Returns False if not found."""
        if chunk_id not in self.ltm_chunks:
            logger.warning(f"Chunk {chunk_id} not found for deletion.")
            return False
        
        # Remove from chunks dict
        del self.ltm_chunks[chunk_id]
        
        # Orphan the vector (remove from mapping, FAISS will ignore it)
        old_vector_ids = [vid for vid, cid in self.chunk_index_map.items() if cid == chunk_id]
        for old_vid in old_vector_ids:
            del self.chunk_index_map[old_vid]
        
        logger.info(f"Deleted chunk {chunk_id}")
        return True
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """Returns chunk data or None if not found."""
        return self.ltm_chunks.get(chunk_id)
    
    def get_all_chunks(self) -> Dict[str, Dict]:
        """Returns all chunks."""
        return self.ltm_chunks
    
    def get_chunks_by_category(self, category: str) -> Dict[str, Dict]:
        """Returns all chunks in a specific category."""
        return {cid: data for cid, data in self.ltm_chunks.items() if data.get("category") == category}
    
    def retrieve_chunks(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieves the most relevant chunks for a query."""
        if not self.ltm_index or self.ltm_index.ntotal == 0:
            return []
        
        vec = self.embedder.encode([query], convert_to_numpy=True)
        distances, indices = self.ltm_index.search(vec, min(top_k * 2, self.ltm_index.ntotal))
        
        results = []
        seen_chunks = set()
        for idx in indices[0]:
            if idx < 0:
                continue
            chunk_id = self.chunk_index_map.get(int(idx))
            if chunk_id and chunk_id not in seen_chunks and chunk_id in self.ltm_chunks:
                seen_chunks.add(chunk_id)
                results.append({
                    "chunk_id": chunk_id,
                    **self.ltm_chunks[chunk_id]
                })
                if len(results) >= top_k:
                    break
        
        return results

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Computes cosine similarity between two texts."""
        emb1 = self.embedder.encode([text1], convert_to_numpy=True)[0]
        emb2 = self.embedder.encode([text2], convert_to_numpy=True)[0]
        
        # Cosine similarity
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0: return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def validate_chunk_consistency(self, chunk_id: str) -> Dict:
        """
        Checks if a chunk is too similar to existing chunks (potential duplicate).
        Returns: {"is_duplicate": bool, "similar_chunks": [...]}
        """
        if not self.enable_similarity_check:
            return {"is_duplicate": False, "similar_chunks": []}
        
        if chunk_id not in self.ltm_chunks:
            return {"is_duplicate": False, "similar_chunks": []}
        
        content = self.ltm_chunks[chunk_id]["content"]
        # Search for similar chunks (top 5)
        similar = self.retrieve_chunks(content, top_k=5)
        
        # Filter out the chunk itself
        similar = [c for c in similar if c["chunk_id"] != chunk_id]
        
        # Check for high similarity
        duplicates = []
        for c in similar:
            similarity = self._compute_similarity(content, c["content"])
            if similarity > self.similarity_threshold:
                duplicates.append({**c, "similarity_score": similarity})
        
        return {
            "is_duplicate": len(duplicates) > 0,
            "similar_chunks": duplicates
        }
    
    def apply_chunk_operations(self, operations: List[Dict]) -> Dict[str, int]:
        """
        Applies a batch of chunk operations.
        Each operation: {"type": "ADD"|"UPDATE"|"DELETE", "content": str, "category": str, "chunk_id": str}
        Returns counts: {"added": N, "updated": N, "deleted": N, "flagged": N}
        """
        counts = {"added": 0, "updated": 0, "deleted": 0, "flagged": 0}
        
        for op in operations:
            op_type = op.get("type", "").upper()
            
            if op_type == "ADD":
                content = op.get("content", "")
                if not content: continue
                chunk_id = self.add_chunk(content, op.get("category", "general"))
                counts["added"] += 1
                
                # Optional consistency check
                if self.enable_similarity_check:
                    validation = self.validate_chunk_consistency(chunk_id)
                    if validation["is_duplicate"]:
                        log_func = getattr(logger, self.validation_log_level.lower(), logger.warning)
                        log_func(f"Potential duplicate detected: {chunk_id}")
                        for sim_chunk in validation["similar_chunks"]:
                            log_func(f"  Similar to {sim_chunk['chunk_id']} (score: {sim_chunk['similarity_score']:.2f})")
                        counts["flagged"] += 1
            elif op_type == "UPDATE":
                if self.update_chunk(op.get("chunk_id"), op.get("content", ""), op.get("category")):
                    counts["updated"] += 1
            elif op_type == "DELETE":
                if self.delete_chunk(op.get("chunk_id")):
                    counts["deleted"] += 1
        
        if counts["added"] + counts["updated"] + counts["deleted"] > 0:
            self._save_ltm()
        
        logger.info(f"Chunk operations complete: {counts}")
        return counts

    def scan_all_chunks_for_conflicts(self) -> List[Dict]:
        """
        Scans all chunks and returns detected conflicts/duplicates.
        Returns: [{"chunk1": {...}, "chunk2": {...}, "similarity": 0.92}, ...]
        """
        if not self.enable_similarity_check:
            logger.warning("Similarity check disabled in config")
            return []
        
        conflicts = []
        processed_pairs = set()
        
        for chunk_id, chunk_data in self.ltm_chunks.items():
            # Find top-6 most similar chunks (one will be self)
            similar_chunks = self.retrieve_chunks(chunk_data["content"], top_k=6)
            
            for sim_chunk in similar_chunks:
                # Skip self-comparison
                if sim_chunk["chunk_id"] == chunk_id:
                    continue
                
                # Avoid duplicate pairs (A,B) and (B,A)
                pair_key = tuple(sorted([chunk_id, sim_chunk["chunk_id"]]))
                if pair_key in processed_pairs:
                    continue
                
                # Compute exact similarity
                similarity = self._compute_similarity(
                    chunk_data["content"], 
                    sim_chunk["content"]
                )
                
                # Flag if above threshold
                if similarity > self.similarity_threshold:
                    conflicts.append({
                        "chunk1": {
                            "chunk_id": chunk_id,
                            "content": chunk_data["content"],
                            "category": chunk_data.get("category", "general")
                        },
                        "chunk2": {
                            "chunk_id": sim_chunk["chunk_id"],
                            "content": sim_chunk["content"],
                            "category": sim_chunk.get("category", "general")
                        },
                        "similarity": round(similarity, 3)
                    })
                    processed_pairs.add(pair_key)
        
        logger.info(f"Found {len(conflicts)} potential conflicts (threshold={self.similarity_threshold})")
        return conflicts

    def generate_conflict_resolution_prompt(self, conflicts: List[Dict]) -> str:
        """Generates a prompt for the AI to resolve detected conflicts."""
        conflict_descriptions = []
        for idx, conflict in enumerate(conflicts, 1):
            conflict_descriptions.append(
                f"CONFLICT {idx} (similarity: {conflict['similarity']:.0%}):\n"
                f"  Chunk A [{conflict['chunk1']['chunk_id']}]: {conflict['chunk1']['content']}\n"
                f"  Chunk B [{conflict['chunk2']['chunk_id']}]: {conflict['chunk2']['content']}\n"
            )
        
        return f"""You are resolving duplicate/conflicting knowledge chunks.

DETECTED CONFLICTS:
{"".join(conflict_descriptions)}

RESOLUTION RULES:
1. If chunks are duplicates with identical meaning -> DELETE one, keep the other
2. If chunks contradict each other -> UPDATE one to the correct version, DELETE the incorrect one
3. If chunks are similar but both add value -> UPDATE to merge them into a single comprehensive chunk

OUTPUT CHUNK OPERATIONS using EXACTLY this format:

[DELETE chunk_id="..."]

[UPDATE chunk_id="..."]
merged/corrected content here
[/UPDATE]

CRITICAL: Only output operations for conflicts listed above. Do not modify unrelated chunks.
"""
    
    def rebuild_legacy_metadata(self):
        """Rebuilds ltm_metadata from chunks for backwards compatibility."""
        if not self.ltm_chunks:
            return
        
        # Combine all chunks into single KB for legacy format
        all_content = "\n\n".join([
            f"[{c['category'].upper()}]\n{c['content']}"
            for c in self.ltm_chunks.values()
        ])
        
        self.ltm_metadata = [{
            "content": all_content,
            "timestamp": time.time(),
            "created_at": datetime.now().isoformat(),
            "chunk_count": len(self.ltm_chunks)
        }]

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
        """Retrieves relevant memory. Uses chunks if available, falls back to legacy."""
        if not self.ltm_index or self.ltm_index.ntotal == 0:
            return []
        
        # v3.0: Use chunk retrieval if chunks exist
        if self.ltm_chunks:
            chunks = self.retrieve_chunks(query, top_k)
            return [c['content'] for c in chunks]
        
        # Legacy fallback
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
    
    # ========== v3.0 CHUNK CONSOLIDATION ==========
    
    def parse_chunk_operations(self, raw_output: str) -> List[Dict]:
        """
        Parses AI output into chunk operations.
        Expected format:
        [ADD category="preferences"]
        content here
        [/ADD]
        
        [UPDATE chunk_id="chunk_abc123"]
        new content
        [/UPDATE]
        
        [DELETE chunk_id="chunk_xyz789"]
        """
        operations = []
        
        # Clean thinking tags
        if "</think>" in raw_output:
            raw_output = raw_output.split("</think>")[-1].strip()
        
        # Parse ADD operations
        add_pattern = r'\[ADD\s+category="([^"]+)"\](.*?)\[/ADD\]'
        for match in re.finditer(add_pattern, raw_output, re.DOTALL | re.IGNORECASE):
            category = match.group(1).strip()
            content = match.group(2).strip()
            if content:
                operations.append({
                    "type": "ADD",
                    "category": category,
                    "content": content
                })
        
        # Parse UPDATE operations
        update_pattern = r'\[UPDATE\s+chunk_id="([^"]+)"\](.*?)\[/UPDATE\]'
        for match in re.finditer(update_pattern, raw_output, re.DOTALL | re.IGNORECASE):
            chunk_id = match.group(1).strip()
            content = match.group(2).strip()
            if content and chunk_id:
                operations.append({
                    "type": "UPDATE",
                    "chunk_id": chunk_id,
                    "content": content
                })
        
        # Parse DELETE operations
        delete_pattern = r'\[DELETE\s+chunk_id="([^"]+)"\]'
        for match in re.finditer(delete_pattern, raw_output, re.IGNORECASE):
            chunk_id = match.group(1).strip()
            if chunk_id:
                operations.append({
                    "type": "DELETE",
                    "chunk_id": chunk_id
                })
        
        logger.info(f"Parsed {len(operations)} chunk operations from AI output")
        return operations
    
    def get_chunks_list_for_prompt(self) -> str:
        """Formats existing chunks for inclusion in prompt."""
        if not self.ltm_chunks:
            return "(No existing chunks)"
        
        lines = []
        for chunk_id, data in self.ltm_chunks.items():
            lines.append(f'[{chunk_id}] ({data["category"]}): {data["content"][:100]}...' 
                        if len(data["content"]) > 100 
                        else f'[{chunk_id}] ({data["category"]}): {data["content"]}')
        return "\n".join(lines)
    
    def get_chunk_consolidation_prompt(self, new_summary: str) -> str:
        """Returns prompt for chunk-based consolidation. Uses context-aware mode if enabled."""
        if self.enable_context_aware_consolidation:
            # Retrieve similar chunks specifically for this summary
            similar = self.retrieve_chunks(new_summary, top_k=self.consolidation_context_size)
            if similar:
                chunks_list = "\n".join([
                    f'[{c["chunk_id"]}] ({c["category"]}): {c["content"]}'
                    for c in similar
                ])
            else:
                chunks_list = "(No existing chunks found)"
        else:
            chunks_list = self.get_chunks_list_for_prompt()
            
        return self.chunk_consolidation_prompt.format(
            chunks_list=chunks_list,
            new_summary=new_summary
        )
    
    def apply_chunk_consolidation(self, raw_output: str, new_summary: str) -> str:
        """
        Applies chunk operations from AI output.
        Returns the combined KB text for display/legacy compatibility.
        """
        operations = self.parse_chunk_operations(raw_output)
        
        # If no valid operations parsed, fall back to adding entire summary as a chunk
        if not operations:
            logger.warning("No chunk operations parsed. Adding summary as single chunk.")
            self.add_chunk(new_summary, "general")
        else:
            self.apply_chunk_operations(operations)
        
        # Rebuild legacy metadata for backwards compatibility
        self.rebuild_legacy_metadata()
        self._save_ltm()
        
        # Return combined text for display
        return self.ltm_metadata[0]['content'] if self.ltm_metadata else new_summary

    def get_consolidation_prompt(self, new_summary: str) -> tuple[str, str]:
        """Returns (prompt, mode) for consolidation. Prefers chunk mode."""
        
        # v3.0: Use chunk consolidation if available
        self.load_prompts()
        if hasattr(self, 'chunk_consolidation_prompt') and self.chunk_consolidation_prompt:
            return self.get_chunk_consolidation_prompt(new_summary), "chunk"
        
        # Legacy fallback: full rewrite (Delta mode removed in v3.0)
        all_existing = self.ltm_metadata[0]['content'] if self.ltm_metadata else ""
        prompt = self.knowledge_consolidation_prompt.format(
            all_existing=all_existing,
            new_summary=new_summary
        )
        return prompt, "rewrite"

    def apply_consolidation_result(self, raw_output: str, mode: str, new_summary: str) -> str:
        """Applies the consolidation result based on mode."""
        if "</think>" in raw_output: raw_output = raw_output.split("</think>")[-1].strip()
        
        # v3.0: Chunk-based consolidation
        if mode == "chunk":
            return self.apply_chunk_consolidation(raw_output, new_summary)
        
        # Fallback to full rewrite
        if mode == "rewrite":
            # For rewrite mode, we also want to transition to chunks if possible
            # but for now we just return the raw output and overwrite legacy state
            logger.info("Performing legacy full rewrite.")
            return raw_output
            
        return self.ltm_metadata[0]['content'] if self.ltm_metadata else ""

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
        
        ltm = self.retrieve_ltm(user_input, top_k=5)
        if ltm:
            sys_content += f"\n\n[RELEVANT LONG-TERM KNOWLEDGE]\n"
            sys_content += "\n".join([f"- {c}" for c in ltm])
            sys_content += f"\n[END KNOWLEDGE]\n"

        msgs.append({"role": "system", "content": sys_content})
        for m in self.stm:
            msgs.append({"role": "user", "content": m['input']})
            msgs.append({"role": "assistant", "content": m['output']})
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def get_stats(self) -> Dict:
        # Collect category counts from chunks
        category_counts = {}
        for chunk in self.ltm_chunks.values():
            cat = chunk.get("category", "general")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "stm_count": len(self.stm), "stm_max": self.stm_size,
            "ltm_count": len(self.ltm_metadata),
            "long_term_summary": self.ltm_metadata[0]['content'] if self.ltm_metadata else "",
            "archive_count": len(self.archive_metadata), "archive_threshold": self.archive_threshold,
            "turn_count": self.turn_count, "summary_threshold": self.summary_threshold,
            "consolidation_count": self.consolidation_count,
            "system_role": self.system_role,
            # v3.0 chunk stats
            "chunk_count": len(self.ltm_chunks),
            "chunk_categories": category_counts,
            "chunks": list(self.ltm_chunks.values())  # Full chunk data for frontend
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
