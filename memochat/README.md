# 🧠 MemoChat: The Agentic Memory Architecture

MemoChat is a powerful, locally-hosted AI assistant designed with a focus on **long-term identity persistence** and **visual transparency**. Unlike standard chatbots, MemoChat treats its memory as a living, editable knowledge base that you can audit in real-time.

---

## 🚀 Quick Start

### 1. Launch the System
Run the following command to start the system. On the first run, it will automatically trigger the `setup.bat` script to initialize your environment (installing dependencies, etc.).
```batch
start_all.bat
```

> **Manual Setup**: You can also run `setup.bat` independently if you need to re-initialize your dependencies.

### 2. Control & Shutdown
- **Vite Controller**: The launch window acts as your interactive Vite console.
- **Graceful Quit**: Press `q` + `Enter` in the console window to stop the frontend and automatically trigger the background system shutdown.

---

## 🏛️ Architecture: The Advanced Memory Stack

MemoChat uses a sophisticated multi-layered approach to ensure its intelligence remains fast, contextually aware, and relationally deep.

### 1. Live Focus (Short-Term Memory)
- **What it is**: The active conversation context (default: last 10 turns).
- **Efficiency**: Handled as a fast buffer. Cleared during "Sleep" to keep GPU processing speeds high.
- **Auditing**: Viewable in `memory_snapshots/short_term_memory.md`.

### 2. Neural Core (Long-Term Memory + Relationships)
- **What it is**: A vector-indexed (FAISS) "Truth Base" augmented with a **Relationship Graph (NetworkX)**.
- **Processing**: During the **Sleep Cycle**, the AI distills recent chats into factual summaries and maps entity relationships (e.g., "User" specializes in "Python").
- **Relational RAG**: The system retrieves not just facts, but also related context from the graph, providing a "web of knowledge" feel.
- **Auditing**: Viewable in `memory_snapshots/long_term_memory.md`.

### 3. Neural Holding Area (Conflict Resolution)
- **What it is**: A "purgatory" for facts that conflict with existing memory or have low confidence.
- **Workflow**: Conflicting data is marked as `[CONFLICT]` and moved here. Users can resolve these via the **Holding Area UI** in the Memory Panel.
- **Safety**: Prevents the AI from hallucinating or overwriting stable truths with isolated errors.

### 4. Deep Archive
- **What it is**: Distilled snapshots of the AI's identity over time. Every 5 sleep cycles, a deep snapshot is taken.
- **Restoration**: You can "Restore" back to any historical version via the UI to roll back the AI's knowledge base.

---

## ⚙️ Memory Strategies (A/B Testing)

You can swap memory architectures in `backend/config.yaml` to test different retrieval behaviors:

- **Metadata-Heavy**: Precise, tag-based retrieval for high-fidelity fact tracking.
- **Hybrid Graph-Vector (Default)**: Combines vector similarity with relationship depth.
- **Segmented Multi-Index**: Partitions memory into categories (Personal, Technical, etc.) for scalability.

---

## 🛠️ Tech Stack
- **Frontend**: React (Vite, TailwindCSS, Lucide Icons).
- **Backend Core**: Python (FastAPI, Uvicorn, NetworkX).
- **Inference Engine**: Ollama (supports any GGUF models).
- **Vector DB**: FAISS (Facebook AI Similarity Search).
- **Persistence**: Hybrid JSON State + Human-Readable Markdown Snapshots.

---

## 🛡️ Stability & Security
- **Log Monitor**: Real-time broadcast of network requests (`[REQ]`, `[RES]`, `[ERR]`) in the UI header.
- **System Diagnostics**: Run `run_system_check.bat` to verify core, model, and memory integrity.
- **Local-First**: All data, models, and embeddings remain 100% offline on your machine.
