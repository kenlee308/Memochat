import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import { X, Brain, Clock, Database, Hash, History, Archive, ShieldAlert, Tag, Share2, Check, Trash2, Edit2 } from 'lucide-react';
import { memoryService } from '../../services/api';

const MemoryPanel = ({ isOpen, onClose, streamingMemory, isMemoryStreaming }) => {
    const [memoryData, setMemoryData] = useState({ short_term: [], long_term_count: 0 });
    const [longTermMemories, setLongTermMemories] = useState([]);
    const [archivedMemories, setArchivedMemories] = useState([]);
    const [holdingArea, setHoldingArea] = useState([]);
    const [categories, setCategories] = useState({});
    const [relationships, setRelationships] = useState({ nodes: [], edges: [] });
    const [isLoading, setIsLoading] = useState(false);
    const [showLongTerm, setShowLongTerm] = useState(true);
    const [showArchive, setShowArchive] = useState(false);
    const [showHolding, setShowHolding] = useState(false);
    const [showCategories, setShowCategories] = useState(false);
    const [showRelMap, setShowRelMap] = useState(false);
    const [showOldVersion, setShowOldVersion] = useState({});

    const scrollRef = useRef(null);
    useEffect(() => {
        if (isMemoryStreaming && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [streamingMemory, isMemoryStreaming]);

    useEffect(() => {
        let interval;
        if (isOpen) {
            loadMemory(true);
            interval = setInterval(() => loadMemory(false), 5000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [isOpen]);

    const loadMemory = async (showLoading = false) => {
        if (showLoading) setIsLoading(true);
        try {
            const [shortTerm, longTerm, holding, cats, rels] = await Promise.all([
                memoryService.getMemory().catch(e => ({ short_term: [], system_role: 'AI Assistant', stm_max: 10 })),
                memoryService.getLongTermMemory().catch(e => ({ summaries: [], archive: [] })),
                memoryService.getHoldingArea().catch(e => ({ items: [] })),
                memoryService.getCategories().catch(e => ({ categories: {} })),
                memoryService.getRelationships().catch(e => ({ nodes: [], edges: [] }))
            ]);

            if (shortTerm) setMemoryData(shortTerm);
            if (longTerm) {
                setLongTermMemories(longTerm.summaries || []);
                setArchivedMemories(longTerm.archive || []);
            }
            if (holding) setHoldingArea(holding.items || []);
            if (cats) setCategories(cats.categories || {});
            if (rels) setRelationships(rels);
        } catch (error) {
            console.error("Failed to load memory:", error);
        } finally {
            if (showLoading) setIsLoading(false);
        }
    };

    const handleApprove = async (index, action, newContent = null) => {
        try {
            await memoryService.approveHoldingItem(index, action, newContent);
            loadMemory(true);
        } catch (error) {
            console.error("Action failed:", error);
        }
    };

    const handleRestore = async (index) => {
        if (!confirm("Are you sure you want to restore this version? This will replace your current long-term knowledge.")) return;
        try {
            await memoryService.restoreMemory(index);
            loadMemory(true);
        } catch (error) {
            console.error("Restore failed:", error);
            alert("Failed to restore memory.");
        }
    };

    const calculateTokens = (text) => {
        if (!text || typeof text !== 'string') return 0;
        return Math.round(text.trim().split(/\s+/).length * 1.3);
    };

    const stmContent = memoryData.short_term?.map(m => m?.content || '').join(' ') || '';
    const stmTokens = calculateTokens(stmContent);

    const ltmContent = (longTermMemories || []).map(m => m?.content || '').join(' ');
    const ltmTokens = calculateTokens(ltmContent);

    const archiveContent = (archivedMemories || []).map(m => m?.content || '').join(' ');
    const archiveTokens = calculateTokens(archiveContent);

    return (
        <aside
            className={clsx(
                "h-full glass border-l border-white/10 shadow-2xl transition-all duration-500 ease-in-out flex flex-col overflow-hidden shrink-0",
                isOpen ? "w-[26rem] opacity-100" : "w-0 opacity-0 border-none"
            )}
        >
            <div className="flex justify-between items-center p-6 border-b border-white/10 min-w-[26rem]">
                <div className="flex items-center gap-2">
                    <Brain className="text-purple-400" size={20} />
                    <h2 className="text-lg font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Memory Layers</h2>
                    <span className="ml-2 px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[9px] font-mono text-slate-400" title="Total Context Load">
                        {stmTokens + ltmTokens}t load
                    </span>
                </div>
                <button onClick={onClose} className="glass-hover p-2 rounded-xl text-slate-400 hover:text-white transition-all"><X size={20} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6 min-w-[26rem] scrollbar-custom">
                {isLoading ? (
                    <div className="flex items-center justify-center h-32"><div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div></div>
                ) : (
                    <>
                        {/* LAYER 1: STM */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-sm font-semibold text-slate-300"><Clock size={16} className="text-blue-400" /><span>Short-Term (Focus)</span></div>
                            <div className="glass p-3 rounded-xl text-xs space-y-2">
                                <div className="flex justify-between text-slate-400"><span>Messages:</span><span className="text-white">{(memoryData.short_term?.length || 0) / 2}/{memoryData.stm_max}</span></div>
                                <div className="flex justify-between text-slate-400"><span>Consolidation:</span><span className="text-white">{memoryData.turn_count}/{memoryData.summary_threshold} turns</span></div>
                                <div className="flex justify-between text-slate-400 pt-1 border-t border-white/5"><span>Archive Trigger:</span><span className="text-blue-400 font-bold">{memoryData.consolidation_count || 0}/{memoryData.archive_threshold || 5} sleeps</span></div>
                                <div className="text-[10px] text-slate-500 pt-1">~{stmTokens} active tokens</div>
                            </div>
                        </div>

                        {/* LAYER 2: LTM */}
                        <div className="space-y-3">
                            <button onClick={() => setShowLongTerm(!showLongTerm)} className="w-full flex items-center justify-between text-sm font-semibold text-slate-300 glass-hover p-3 rounded-xl transition-all">
                                <div className="flex items-center gap-2"><Database size={16} className="text-purple-400" /><span>Long-Term Knowledge</span></div>
                                {showLongTerm ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                            </button>
                            {showLongTerm && (
                                <div className="space-y-3 animate-fade-in" ref={scrollRef}>
                                    <div className="glass p-3 rounded-xl text-[10px] text-slate-500 flex justify-between"><span>Active Knowledge:</span><span>~{ltmTokens} tokens</span></div>

                                    {isMemoryStreaming && streamingMemory && (
                                        <div className="glass p-4 rounded-xl space-y-3 border-2 border-purple-500/50 bg-purple-500/10 shadow-[0_0_20px_rgba(168,85,247,0.15)] animate-pulse mb-6">
                                            <div className="flex justify-between items-center mb-1">
                                                <div className="text-[10px] text-purple-400 font-black uppercase tracking-widest flex items-center gap-2">
                                                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-ping"></div>
                                                    Live Intelligence Merge
                                                </div>
                                                <div className="text-[9px] text-slate-400 font-mono italic">Writing to Neural Index...</div>
                                            </div>
                                            <div className="text-slate-100 font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-black/80 p-4 rounded-xl border border-purple-500/30 shadow-inner min-h-[100px]">
                                                {streamingMemory}
                                                <span className="inline-block w-2 h-4 bg-purple-500 ml-1 animate-pulse align-middle"></span>
                                            </div>
                                        </div>
                                    )}
                                    {longTermMemories.length > 0 ? (
                                        longTermMemories.map((m, i) => (
                                            <div key={i} className="glass p-4 rounded-xl space-y-3 border border-purple-500/10">
                                                <div className="flex justify-between items-center mb-1">
                                                    <div className="text-[10px] text-purple-400 font-bold uppercase tracking-tight">Current Truth Base</div>
                                                    <div className="text-[9px] text-slate-500 font-mono italic">
                                                        {m.created_at ? new Date(m.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Live'}
                                                    </div>
                                                </div>
                                                <div className="text-slate-200 font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-black/40 p-3 rounded-lg overflow-x-auto border border-white/5">
                                                    {m.content}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center p-8 glass rounded-xl border border-dashed border-white/10">
                                            <p className="text-slate-500 text-xs italic">No long-term knowledge synchronized.</p>
                                            <p className="text-[10px] text-slate-600 mt-1">Try pressing 'Sleep' to consolidate memory.</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* LAYER 3: ARCHIVE */}
                        <div className="space-y-3">
                            <button onClick={() => setShowArchive(!showArchive)} className="w-full flex items-center justify-between text-sm font-semibold text-slate-300 glass-hover p-3 rounded-xl transition-all border border-blue-400/10">
                                <div className="flex items-center gap-2"><Archive size={16} className="text-blue-400" /><span>Deep Archive (Backup)</span></div>
                                {showArchive ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                            </button>
                            {showArchive && (
                                <div className="space-y-3 animate-fade-in">
                                    <div className="glass p-3 rounded-xl flex flex-col gap-2">
                                        <div className="text-[10px] text-slate-500 flex justify-between">
                                            <span>Archival Storage:</span>
                                            <span>{archivedMemories.length}/10 units (~{archiveTokens} tokens)</span>
                                        </div>
                                        <p className="text-[9px] text-slate-600 leading-tight">
                                            "Units" are distilled core snapshots. We keep 10 slots as a revolving history of your AI's evolving identity.
                                        </p>
                                    </div>
                                    <div className="text-[11px] text-slate-500 px-1 italic">Updated every {memoryData.archive_threshold} knowledge updates.</div>
                                    {archivedMemories.map((m, i) => (
                                        <div key={i} className="glass p-4 rounded-xl border border-blue-400/10 group">
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="text-[10px] text-blue-400 font-bold uppercase tracking-widest whitespace-nowrap">
                                                    Snapshot: {m?.created_at ? String(m.created_at).slice(0, 16).replace('T', ' ') : 'Legacy'}
                                                </div>
                                                <button
                                                    onClick={() => handleRestore(m.index)}
                                                    className="opacity-0 group-hover:opacity-100 text-[9px] bg-blue-500/20 text-blue-300 px-2 py-1 rounded hover:bg-blue-500/40 transition-all border border-blue-500/20"
                                                >
                                                    Restore version
                                                </button>
                                            </div>
                                            <div className="text-slate-400 font-mono text-[10px] leading-tight line-clamp-6 hover:line-clamp-none transition-all cursor-pointer bg-black/20 p-2 rounded">
                                                {m.content}
                                            </div>
                                        </div>
                                    ))}
                                    {archivedMemories.length === 0 && <div className="text-center p-6 text-slate-600 text-xs italic">No deep archive snapshots yet.</div>}
                                </div>
                            )}
                        </div>

                        <button onClick={() => loadMemory(true)} className="w-full glass-hover p-3 rounded-xl text-sm font-medium text-slate-300 border border-white/5">Refresh Memory Layers</button>

                        <div className="pt-4 border-t border-white/10 space-y-4">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 mb-2">Relationship Labs (BETA)</h3>

                            {/* NEURAL HOLDING AREA */}
                            <div className="space-y-3">
                                <button onClick={() => setShowHolding(!showHolding)} className={clsx("w-full flex items-center justify-between text-sm font-semibold glass-hover p-3 rounded-xl transition-all border", holdingArea.length > 0 ? "border-amber-400/30 text-amber-300" : "border-white/5 text-slate-400")}>
                                    <div className="flex items-center gap-2">
                                        <ShieldAlert size={16} className={holdingArea.length > 0 ? "text-amber-400" : "text-slate-500"} />
                                        <span>Neural Holding Area</span>
                                        {holdingArea.length > 0 && <span className="ml-2 w-4 h-4 rounded-full bg-amber-500 text-[9px] flex items-center justify-center text-black font-bold animate-pulse">{holdingArea.length}</span>}
                                    </div>
                                    {showHolding ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                                </button>
                                {showHolding && (
                                    <div className="space-y-3 animate-fade-in">
                                        <p className="text-[10px] text-slate-500 px-1 italic">Facts awaiting verification or conflict resolution.</p>
                                        {holdingArea.map((item, i) => (
                                            <div key={i} className="glass p-4 rounded-xl border border-amber-400/20 bg-amber-400/5 space-y-3">
                                                <div className="text-[11px] text-slate-200 font-mono leading-relaxed bg-black/40 p-3 rounded border border-white/5 whitespace-pre-wrap">
                                                    {item.content}
                                                </div>
                                                <div className="flex gap-2">
                                                    <button onClick={() => handleApprove(i, 'approve')} className="flex-1 glass-hover p-2 rounded-lg text-[10px] text-green-400 flex items-center justify-center gap-1 border border-green-500/20"><Check size={12} /> Approve</button>
                                                    <button onClick={() => handleApprove(i, 'reject')} className="flex-1 glass-hover p-2 rounded-lg text-[10px] text-red-400 flex items-center justify-center gap-1 border border-red-500/20"><Trash2 size={12} /> Reject</button>
                                                </div>
                                            </div>
                                        ))}
                                        {holdingArea.length === 0 && <div className="text-center p-4 glass rounded-xl border border-dashed border-white/10 text-slate-600 text-[10px] italic">Holding area clear. AI is confident.</div>}
                                    </div>
                                )}
                            </div>

                            {/* CATEGORY REGISTRY */}
                            <div className="space-y-3">
                                <button onClick={() => setShowCategories(!showCategories)} className="w-full flex items-center justify-between text-sm font-semibold text-slate-300 glass-hover p-3 rounded-xl transition-all border border-green-400/10">
                                    <div className="flex items-center gap-2"><Tag size={16} className="text-green-400" /><span>Category Registry</span></div>
                                    {showCategories ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                                </button>
                                {showCategories && (
                                    <div className="space-y-3 animate-fade-in">
                                        <div className="flex flex-wrap gap-2">
                                            {Object.entries(categories).map(([cat, desc], i) => (
                                                <div key={i} className="glass px-3 py-1.5 rounded-full border border-green-500/10 text-[10px] text-green-300 flex items-center gap-2 group cursor-help" title={desc}>
                                                    <Hash size={10} /> {cat}
                                                </div>
                                            ))}
                                            {Object.keys(categories).length === 0 && <span className="text-slate-600 text-[10px] italic">No custom categories mapped.</span>}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* RELATIONSHIP MAP */}
                            <div className="space-y-3">
                                <button onClick={() => setShowRelMap(!showRelMap)} className="w-full flex items-center justify-between text-sm font-semibold text-slate-300 glass-hover p-3 rounded-xl transition-all border border-blue-400/10">
                                    <div className="flex items-center gap-2"><Share2 size={16} className="text-blue-400" /><span>Neural Connections</span></div>
                                    {showRelMap ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                                </button>
                                {showRelMap && (
                                    <div className="space-y-3 animate-fade-in">
                                        <p className="text-[10px] text-slate-500 px-1 italic">Implicit relationships extracted by the reasoning engine.</p>
                                        <div className="glass p-3 rounded-xl space-y-2">
                                            {relationships.edges.map((edge, i) => (
                                                <div key={i} className="flex items-center gap-2 text-[10px] text-slate-400 border-b border-white/5 pb-2 last:border-0 last:pb-0">
                                                    <span className="text-blue-300">{edge.source}</span>
                                                    <span className="text-[8px] text-slate-600 px-1 bg-white/5 rounded italic">{edge.label}</span>
                                                    <span className="text-blue-300">{edge.target}</span>
                                                </div>
                                            ))}
                                            {relationships.edges.length === 0 && <div className="text-center p-2 text-slate-600 italic text-[10px]">No complex connections mapped yet.</div>}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </aside>
    );
};

export default MemoryPanel;
