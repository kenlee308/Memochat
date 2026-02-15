# 🟢 Version Stable: 3.0.0
**Date**: 2026-01-27
**Status**: Stable / Feature Complete

## Summary
This version marks the completion of the "Hybrid Chunking" milestone. The system now supports incremental, atomic memory updates, significantly reducing CPU/GPU overhead during consolidation cycles.

## Changes
- **Core**: Integrated FAISS for vector-based retrieval of individual memory chunks.
- **API**: Added `get_stats` endpoint to provide granular memory metrics to the frontend.
- **Prompts**: Standardized on v3.0 XML-style operation tags for AI memory management.
- **Stability**: Implemented fail-safes for empty memory states and malformed AI outputs.

## Known Issues
- Large batch deletes (>50 chunks) may cause a slight lag in FAISS re-indexing (planned fix: async indexing).
- Conflict resolution UI requires manual page refresh in some edge cases.

## Future Roadmap (v4.0)
- Temporal weight decay for facts (older facts lose relevance).
- Active questioning: AI proactively asks questions to resolve Holding Area conflicts.
