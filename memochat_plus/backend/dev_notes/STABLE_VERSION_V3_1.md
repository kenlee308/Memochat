# 🟢 Version Stable: 3.1.0
**Date**: 2026-01-27
**Status**: Stable / Feature Complete

## Summary
Version 3.1.0 introduces the **Consistency Audit Engine**, a critical layer on top of the Hybrid Chunking system. This update focuses on proactive memory maintenance, ensuring that the "Truth Base" remains logical, deduplicated, and consistent through AI-powered neural resolution.

## Major Updates (v3.1)
- **Neural Core Resolution**: Added automated and manual AI conflict resolution cycles.
- **Enhanced Memory Panel**: Implemented category filtering, collapsible lists, and dedicated resolution reporting.
- **Smart Categorization**: Knowledge chunks are now automatically partitioned into `Preferences`, `Facts`, and `General` domains.
- **Auto-Resolve Toggle**: Integrated a background consistency auditor that runs post-consolidation.
- **UI Persistence**: Advanced neural parameters and audit settings are now persisted across sessions.

## Fixed in this Release
- **Model Synchronization**: Conflict resolution now uses the user's selected computation core instead of a hardcoded default.
- **UI Responsiveness**: Categories are now hidden by default for cleaner navigation, with independent expand/collapse states.
- **Resolution Transparency**: Added a "Neural Reasoning Output" log to the UI to expose the AI's logic during auditing.

## Known Issues
- Very high resolution counts (>100 conflicts) may exceed context window limits for reasoning models (mitigation: tiered resolution planned for v3.2).

## Future Roadmap (v3.2)
- Recursive conflict resolution (auto-scanning until zero conflicts remain).
- Visual relationship graphs between atomic chunks.
