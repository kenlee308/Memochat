# 🎛️ MemoChat Frontend: Premium Companion UI

This is the React-based interface for MemoChat, built with Vite and TailwindCSS. It provides a glassmorphic design and real-time visualization of the AI's internal memory state.

## 🌟 Key Features

### 1. Unified Log Monitor
Located in the header, this monitor broadcasts all API traffic and background tasks. It's the "Window into the Backend."

### 2. Memory Layers Panel
Click the **Brain** icon to open the advanced memory management sidebar:
- **Short-Term Context**: Real-time view of what the AI is currently "focusing" on.
- **Long-Term Knowledge**: View current factual summaries extracted by the reasoning engine.
- **Neural Holding Area**: Audit and resolve conflicting information before it enters permanent memory.
- **Relationship Map**: View extracted connections between entities (beta).
- **Deep Archive**: Roll back the AI's knowledge to any historical snapshot.

### 3. Settings Dashboard
Configure neural parameters on the fly:
- **Model Selection**: Switch between local Ollama models (default: `deepseek-r1:8b`).
- **Temperature**: Adjust creativity vs. precision.
- **Memory Scaling**: Tune the STM size and summary thresholds for your hardware.

## 🛠️ Tech Stack
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Vanilla CSS + Tailwind-inspired glassmorphism
- **Icons**: Lucide-React
- **API Client**: Axios + EventBus for system-wide logging.

## 🚀 Development
To run the frontend only:
```bash
npm install
npm run dev
```
Note: The frontend depends on the FastAPI backend running on port 8000. Use `start_all.bat` in the root directory for a unified experience.
