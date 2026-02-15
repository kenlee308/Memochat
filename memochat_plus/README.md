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

## 🏛️ Architecture: Hybrid Memory Stack (v3.1)

MemoChat v3.1 introduces a sophisticated three-layer memory system designed for speed, consistency, and depth.

### 1. Live Focus (Short-Term Memory)
- **What it is**: The active conversation window.
- **Auditing**: Viewable in real-time in the Memory Panel. Cleared during "Sleep" to maintain GPU inference speeds.

### 2. Long-Term Knowledge (Atomic Chunks)
- **What it is**: Knowledge stored as discrete, categorized facts (Preferences, Facts, General).
- **Hybrid Search**: Uses FAISS for semantic similarity and category-based indexing for precise retrieval.
- **Efficiency**: Updates are handled via atomic `[ADD]`, `[UPDATE]`, and `[DELETE]` operations.

### 3. Neural Core Resolution (Consistency Audit)
- **What it is**: AI-powered conflict detection and resolution.
- **v3.1 Innovation**: Automated consistency audits can run after every consolidation cycle, ensuring the knowledge base remains logical and non-contradictory.
- **Reporting**: Detailed resolution logs showing exactly what the AI changed and why.

---

## 🚀 Key Features (v3.1)

- **AI Consistency Audit**: Manually trigger or automate "Truth Base" synchronization.
- **Enhanced Memory Panel**: Interactive categories with collapsible lists and filtering.
- **Dynamic Neural Parameters**: Real-time adjustment of model, temperature, and memory thresholds.
- **Neural Resolution Window**: Full visibility into the AI's reasoning during memory cleanup.

---

## ⚙️ Memory Strategies (A/B Testing)

You can swap memory architectures in `backend/config.yaml` to test different retrieval behaviors:

- **Metadata-Heavy**: Precise, tag-based retrieval for high-fidelity fact tracking.
- **Hybrid Graph-Vector (Default)**: Combines vector similarity with relationship depth.
- **Segmented Multi-Index**: Partitions memory into categories (Personal, Technical, etc.) for scalability.

---

## 🛠️ Tech Stack
- **Frontend**: React (Vite, TailwindCSS, Lucide Icons).
- **Backend Core**: Python (FastAPI, Uvicorn, PyYAML).
- **Inference Engine**: Ollama (supports any GGUF models).
- **Vector DB**: FAISS (Facebook AI Similarity Search).
- **Persistence**: Hybrid JSON State + Human-Readable Markdown Snapshots.

---

## 🛡️ Stability & Security
- **Log Monitor**: Real-time broadcast of network requests (`[REQ]`, `[RES]`, `[ERR]`) in the UI header.
- **System Diagnostics**: Run `run_system_check.bat` to verify core, model, and memory integrity.
- **Local-First**: All data, models, and embeddings remain 100% offline on your machine.
