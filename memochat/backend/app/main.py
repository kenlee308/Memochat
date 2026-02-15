import json
import logging
import time
import uvicorn
import yaml
import random

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.memory_manager import MemoryManager
from app.model_engine import ModelEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MemoChat API", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "online", "timestamp": time.time(), "version": "2.5.0"}

# Load configuration
try:
    with open("backend/config.yaml", 'r') as f: config = yaml.safe_load(f)
except FileNotFoundError:
    config = {
        "memory": {"stm_size": 10, "ltm_max_docs": 100, "summary_threshold": 5, "memory_db_path": "./data/ltm_index"},
        "prompts": {"system_role": "AI Assistant."}
    }

mm = MemoryManager(user_id="default", config=config, snapshot_dir="./memory_snapshots")
model_engine = ModelEngine()

class ChatRequest(BaseModel):
    message: str
    model: str
    system_instruction: Optional[str] = None
    temperature: Optional[float] = 0.7
    stm_size: Optional[int] = 10
    summary_threshold: Optional[int] = 5

class ApprovalRequest(BaseModel):
    index: int
    action: str # "approve", "reject", "edit"
    new_content: Optional[str] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        user_input = request.message
        mm.load_prompts()
        
        # 1. Structured Messages for Reasoning Models
        msgs = mm.get_chat_messages(user_input)
        
        # Apply overrides
        mm.stm_size = request.stm_size
        mm.summary_threshold = request.summary_threshold
        
        async def stream_generator():
            full_resp = ""
            # 1. AI Chat Stream
            for chunk in model_engine.chat_stream(request.model, msgs, temperature=request.temperature):
                full_resp += chunk
                yield chunk
            
            # 2. systematic Truth Verification
            final_resp = full_resp
            if random.random() < mm.clarification_probability:
                pq = mm.get_pending_question()
                if pq:
                    clarification = f"\n\n[TRUTH CHECK]: {pq}"
                    final_resp += clarification
                    mm.remove_pending_question(pq)
                    yield clarification

            # 3. Memory & Consolidation
            mm.add_to_stm(user_input, final_resp, request.model)
            mm.log_exchange(user_input, final_resp, request.model)
            mm.export_stm()
            
            consolidated = False
            if mm.should_summarize():
                sp = mm.create_summary_prompt()
                yield f"__MEMORY_CHUNK__"
                
                # Stream the consolidation for live UI update
                sum_text = ""
                for chunk in model_engine.generate_stream(request.model, sp, temperature=request.temperature):
                    sum_text += chunk
                    yield chunk
                
                if "</think>" in sum_text: sum_text = sum_text.split("</think>")[-1].strip()
                
                # Simplified merge logic
                yield f"\n\n[SYSTEM]: Finalizing neural merge..."
                full_kb, _ = mm.consolidate_knowledge(sum_text, model_engine, request.model)
                
                if len(full_kb.strip()) > 10:
                    mm.replace_ltm_with_consolidated(full_kb, [])
                    mm.stm.clear()
                    mm.reset_turn_counter()
                    logger.info(f"Consolidation complete. STM cleared ({len(full_kb)} chars in LTM).")
                else:
                    logger.warning("Consolidation produced suspiciously small output. Aborting clear to prevent data loss.")
                    yield f"\n\n[ERROR]: Brain desync detected. Retrying consolidation next turn."
                
                if mm.consolidation_count >= mm.archive_threshold:
                    mm.perform_deep_archive(model_engine, request.model)
                    mm.consolidation_count = 0 
                    
                mm.export_all()
                consolidated = True

            # 4. Meta Data
            yield f"\n__METADATA__{json.dumps({'memory_stats': mm.get_stats(), 'consolidated': consolidated})}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Chat error: {e}"); raise HTTPException(500, str(e))

@app.post("/chat/sleep")
async def sleep(request: ChatRequest):
    async def sleep_generator():
        try:
            mm.sync_all_from_files()
            if not mm.stm: 
                yield f"__METADATA__{json.dumps({'status': 'nothing_to_consolidate'})}"
                return

            mm.stm_size = request.stm_size
            mm.summary_threshold = request.summary_threshold

            sp = mm.create_summary_prompt()
            yield f"__MEMORY_CHUNK__"
            
            # Stream the sleep distillation for live UI update
            sum_text = ""
            for chunk in model_engine.generate_stream(request.model, sp, temperature=request.temperature):
                sum_text += chunk
                yield chunk
            
            if "</think>" in sum_text: sum_text = sum_text.split("</think>")[-1].strip()
            
            yield f"\n\n[SYSTEM]: Integrating into long-term cores..."
            full_kb, _ = mm.consolidate_knowledge(sum_text, model_engine, request.model)
            
            if len(full_kb.strip()) > 10:
                mm.replace_ltm_with_consolidated(full_kb, [])
                mm.stm.clear()
                mm.reset_turn_counter()
                logger.info(f"Sleep distillation complete. STM cleared ({len(full_kb)} chars).")
            else:
                logger.warning("Sleep distillation produced empty response. STM preserved.")
                yield f"\n\n[ERROR]: Deep sleep failed. Knowledge was not persisted."
            
            if mm.consolidation_count >= mm.archive_threshold:
                mm.perform_deep_archive(model_engine, request.model)
                mm.consolidation_count = 0

            mm.export_all()
            yield f"__METADATA__{json.dumps({'status': 'slept', 'memory_stats': mm.get_stats()})}"
        except Exception as e:
            logger.error(f"Sleep error: {e}")
            yield f"__METADATA__{json.dumps({'error': str(e)})}"

    return StreamingResponse(sleep_generator(), media_type="text/plain")

@app.get("/memory")
async def get_memory():
    stats = mm.get_stats()
    # Filter for UI
    ui_hist = []
    for m in list(mm.stm):
        ui_hist.append({"role": "user", "content": m["input"], "timestamp": m.get("timestamp", 0)*1000})
        ui_hist.append({"role": "assistant", "content": m["output"], "timestamp": m.get("timestamp", 0)*1000})
    stats["short_term"] = ui_hist
    stats["short_term"] = ui_hist
    return stats

@app.get("/memory/categories")
async def get_categories():
    return {"categories": {}}

@app.get("/memory/holding-area")
async def get_holding_area():
    return {"items": []}

@app.post("/memory/holding-area/approve")
async def approve_holding_item(request: ApprovalRequest):
    return {"status": "ok", "items": []}

@app.get("/memory/relationships")
async def get_relationships():
    return {"nodes": [], "edges": []}

@app.get("/memory/long-term")
async def get_long_term():
    l_sum = [{"content": m['content'], "created_at": m.get('created_at'), "type": m.get('type', 'summary')} for m in list(reversed(mm.ltm_metadata))]
    # Include the index so we know which one to restore!
    a_sum = [{"index": i, "content": m['content'], "created_at": m.get('created_at'), "type": "archive"} for i, m in enumerate(list(reversed(mm.archive_metadata)))]
    return {"summaries": l_sum, "archive": a_sum}

@app.post("/memory/restore")
async def restore_memory(request: dict):
    idx = request.get("index")
    if idx is None: raise HTTPException(400, "Missing index")
    
    # Map reversed UI index back to actual list index
    actual_idx = len(mm.archive_metadata) - 1 - idx
    success = mm.restore_from_archive(actual_idx)
    if not success: raise HTTPException(404, "Archive entry not found")
    
    mm.export_ltm() 
    return {"status": "restored", "memory_stats": mm.get_stats()}

@app.get("/memory/export")
async def export_memory(format: str = "txt"):
    try:
        content = ""
        if mm.ltm_metadata:
            content = mm.ltm_metadata[0].get('content', "No knowledge stored.")
        
        if format == "json":
            return {"content": json.dumps(mm.ltm_metadata, indent=2)}
        return {"content": content}
    except Exception as e:
        logger.error(f"Export error: {e}"); raise HTTPException(500, str(e))

@app.get("/chat/history")
async def get_history(): return {"history": list(mm.stm)}

@app.get("/models")
async def list_models(): return {"models": model_engine.list_models()}

if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8000)
