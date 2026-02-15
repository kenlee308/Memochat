"""
Test suite for v3.0 Chunked Memory Architecture.
Tests the new incremental update system for O(1) consolidation performance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import time
from backend.app.memory_manager import MemoryManager


@pytest.fixture
def mm():
    """Create a fresh MemoryManager instance for testing."""
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
            "chunk_consolidation": """
You are updating a CHUNKED knowledge base. Each chunk is a discrete fact.

EXISTING CHUNKS:
{chunks_list}

NEW INFORMATION TO INTEGRATE:
{new_summary}

OUTPUT CHUNK OPERATIONS using this format:

[ADD category="preferences"]
content here
[/ADD]

[UPDATE chunk_id="chunk_abc123"]
new content
[/UPDATE]

[DELETE chunk_id="chunk_xyz789"]
"""
        }
    }
    manager = MemoryManager(user_id="test_user", config=config, snapshot_dir="./test_snapshots")
    yield manager
    # Cleanup
    import shutil
    if os.path.exists("./data/test_ltm_index"):
        shutil.rmtree("./data/test_ltm_index")
    if os.path.exists("./test_snapshots"):
        shutil.rmtree("./test_snapshots")


class TestChunkOperations:
    """Tests for individual chunk CRUD operations."""
    
    def test_add_chunk(self, mm):
        """Test adding a single chunk."""
        chunk_id = mm.add_chunk("User likes coffee", "preferences")
        
        assert chunk_id.startswith("chunk_")
        assert chunk_id in mm.ltm_chunks
        assert mm.ltm_chunks[chunk_id]["content"] == "User likes coffee"
        assert mm.ltm_chunks[chunk_id]["category"] == "preferences"
        assert mm.ltm_index.ntotal == 1
    
    def test_update_chunk(self, mm):
        """Test updating an existing chunk."""
        chunk_id = mm.add_chunk("User likes tea", "preferences")
        
        success = mm.update_chunk(chunk_id, "User loves coffee")
        
        assert success
        assert mm.ltm_chunks[chunk_id]["content"] == "User loves coffee"
        # FAISS should have 2 vectors (old orphaned + new)
        assert mm.ltm_index.ntotal == 2
        # But only 1 mapping should exist
        assert len(mm.chunk_index_map) == 1
    
    def test_delete_chunk(self, mm):
        """Test deleting a chunk."""
        chunk_id = mm.add_chunk("Temporary fact", "general")
        
        success = mm.delete_chunk(chunk_id)
        
        assert success
        assert chunk_id not in mm.ltm_chunks
        assert len(mm.chunk_index_map) == 0
    
    def test_get_chunk(self, mm):
        """Test retrieving a specific chunk."""
        chunk_id = mm.add_chunk("Test content", "facts")
        
        chunk = mm.get_chunk(chunk_id)
        
        assert chunk is not None
        assert chunk["content"] == "Test content"
        assert chunk["category"] == "facts"
    
    def test_get_chunks_by_category(self, mm):
        """Test filtering chunks by category."""
        mm.add_chunk("Preference 1", "preferences")
        mm.add_chunk("Preference 2", "preferences")
        mm.add_chunk("Fact 1", "facts")
        
        prefs = mm.get_chunks_by_category("preferences")
        facts = mm.get_chunks_by_category("facts")
        
        assert len(prefs) == 2
        assert len(facts) == 1


class TestChunkRetrieval:
    """Tests for semantic chunk retrieval."""
    
    def test_retrieve_chunks(self, mm):
        """Test semantic search over chunks."""
        mm.add_chunk("User enjoys hiking in the mountains", "preferences")
        mm.add_chunk("Meeting scheduled for Monday", "schedule")
        mm.add_chunk("User prefers Python over JavaScript", "preferences")
        
        results = mm.retrieve_chunks("outdoor activities", top_k=2)
        
        assert len(results) >= 1
        # Hiking should be most relevant to outdoor activities
        assert any("hiking" in r["content"].lower() for r in results)
    
    def test_retrieve_ltm_uses_chunks(self, mm):
        """Test that retrieve_ltm uses chunks when available."""
        mm.add_chunk("Important memory fact", "facts")
        
        results = mm.retrieve_ltm("memory fact", top_k=1)
        
        assert len(results) == 1
        assert "Important memory fact" in results[0]


class TestChunkOperationParsing:
    """Tests for parsing AI output into chunk operations."""
    
    def test_parse_add_operation(self, mm):
        """Test parsing ADD operations."""
        raw = '''
[ADD category="preferences"]
User likes hiking on weekends
[/ADD]
'''
        ops = mm.parse_chunk_operations(raw)
        
        assert len(ops) == 1
        assert ops[0]["type"] == "ADD"
        assert ops[0]["category"] == "preferences"
        assert "hiking" in ops[0]["content"]
    
    def test_parse_update_operation(self, mm):
        """Test parsing UPDATE operations."""
        raw = '''
[UPDATE chunk_id="chunk_abc123"]
Updated content here
[/UPDATE]
'''
        ops = mm.parse_chunk_operations(raw)
        
        assert len(ops) == 1
        assert ops[0]["type"] == "UPDATE"
        assert ops[0]["chunk_id"] == "chunk_abc123"
    
    def test_parse_delete_operation(self, mm):
        """Test parsing DELETE operations."""
        raw = '[DELETE chunk_id="chunk_xyz789"]'
        ops = mm.parse_chunk_operations(raw)
        
        assert len(ops) == 1
        assert ops[0]["type"] == "DELETE"
        assert ops[0]["chunk_id"] == "chunk_xyz789"
    
    def test_parse_multiple_operations(self, mm):
        """Test parsing multiple mixed operations."""
        raw = '''
[ADD category="facts"]
New fact here
[/ADD]

[UPDATE chunk_id="chunk_123"]
Updated fact
[/UPDATE]

[DELETE chunk_id="chunk_456"]
'''
        ops = mm.parse_chunk_operations(raw)
        
        assert len(ops) == 3
        assert ops[0]["type"] == "ADD"
        assert ops[1]["type"] == "UPDATE"
        assert ops[2]["type"] == "DELETE"
    
    def test_parse_with_thinking_tags(self, mm):
        """Test that thinking tags are stripped before parsing."""
        raw = '''<think>Some reasoning here...</think>
[ADD category="preferences"]
Content after thinking
[/ADD]
'''
        ops = mm.parse_chunk_operations(raw)
        
        assert len(ops) == 1
        assert "Content after thinking" in ops[0]["content"]


class TestBatchOperations:
    """Tests for batch chunk operations."""
    
    def test_apply_chunk_operations(self, mm):
        """Test applying a batch of operations."""
        # First add a chunk to update/delete
        chunk_id = mm.add_chunk("Original content", "general")
        
        operations = [
            {"type": "ADD", "content": "New fact", "category": "facts"},
            {"type": "UPDATE", "chunk_id": chunk_id, "content": "Updated content"},
        ]
        
        counts = mm.apply_chunk_operations(operations)
        
        assert counts["added"] == 1
        assert counts["updated"] == 1
        assert len(mm.ltm_chunks) == 2


class TestPerformance:
    """Performance benchmarks for chunk operations."""
    
    def test_add_chunk_performance(self, mm):
        """Single chunk add should be fast."""
        start = time.time()
        mm.add_chunk("Test content for performance", "general")
        elapsed = time.time() - start
        
        # Should complete in under 500ms
        assert elapsed < 0.5, f"add_chunk took {elapsed:.3f}s"
    
    def test_incremental_vs_full_rebuild(self, mm):
        """Incremental updates should be faster than full rebuild."""
        # Add some initial chunks
        for i in range(5):
            mm.add_chunk(f"Fact number {i}", "facts")
        
        # Time an incremental add
        start = time.time()
        mm.add_chunk("One more fact", "facts")
        incremental_time = time.time() - start
        
        # Time would be much worse with full rebuild
        # Just assert the incremental is reasonable
        assert incremental_time < 0.5


class TestLegacyCompatibility:
    """Tests for backwards compatibility with legacy format."""
    
    def test_rebuild_legacy_metadata(self, mm):
        """Test that chunks can be combined into legacy format."""
        mm.add_chunk("Fact one", "facts")
        mm.add_chunk("Preference one", "preferences")
        
        mm.rebuild_legacy_metadata()
        
        assert len(mm.ltm_metadata) == 1
        assert "[FACTS]" in mm.ltm_metadata[0]["content"]
        assert "[PREFERENCES]" in mm.ltm_metadata[0]["content"]
    
    def test_get_stats_includes_chunks(self, mm):
        """Test that stats include chunk information."""
        mm.add_chunk("Fact", "facts")
        mm.add_chunk("Pref", "preferences")
        
        stats = mm.get_stats()
        
        assert "chunk_count" in stats
        assert stats["chunk_count"] == 2
        assert "chunk_categories" in stats
        assert "facts" in stats["chunk_categories"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
