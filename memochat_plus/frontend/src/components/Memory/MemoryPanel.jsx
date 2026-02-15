import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import { X, Brain, Clock, Database, Hash, History, Archive, Tag, ShieldAlert } from 'lucide-react';
import { memoryService } from '../../services/api';

const MemoryPanel = ({
    isOpen, onClose, streamingMemory, isMemoryStreaming, lastUpdate, currentModel,
    resolutionResult, setResolutionResult, showResolution, setShowResolution
}) => {
    const [memoryData, setMemoryData] = useState({ short_term: [], long_term_count: 0 });
    const [longTermMemories, setLongTermMemories] = useState([]);
    const [archivedMemories, setArchivedMemories] = useState([]);
    const [categorizedChunks, setCategorizedChunks] = useState({});
    const [isLoading, setIsLoading] = useState(false);
    const [showLongTerm, setShowLongTerm] = useState(true);
    const [showArchive, setShowArchive] = useState(false);
    const [conflicts, setConflicts] = useState([]);
    const [isScanning, setIsScanning] = useState(false);
    const [isResolving, setIsResolving] = useState(false);
    const [showConflicts, setShowConflicts] = useState(false);
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [expandedCategories, setExpandedCategories] = useState({});

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
    }, [isOpen, lastUpdate]);

    const loadMemory = async (showLoadingIndicator = false) => {
        if (showLoadingIndicator) setIsLoading(true);
        try {
            const [shortTerm, longTerm, chunkData] = await Promise.all([
                memoryService.getMemory().catch(e => ({ short_term: [], stm_max: 10, turn_count: 0 })),
                memoryService.getLongTermMemory().catch(e => ({ summaries: [], archive: [] })),
                memoryService.getChunks().catch(e => ({ by_category: {}, total_count: 0 }))
            ]);

            if (shortTerm) setMemoryData(shortTerm);
            if (longTerm) {
                setLongTermMemories(longTerm.summaries || []);
                setArchivedMemories(longTerm.archive || []);
            }
            if (chunkData && chunkData.by_category) {
                setCategorizedChunks(chunkData.by_category);
            }
        } catch (error) {
            console.error("Failed to load memory layers:", error);
        } finally {
            if (showLoadingIndicator) setIsLoading(false);
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

    const handleScanConflicts = async () => {
        setIsScanning(true);
        try {
            const data = await memoryService.scanConflicts();
            setConflicts(data.conflicts || []);
            setShowConflicts(true);
        } catch (error) {
            console.error("Scan failed:", error);
            alert("Failed to scan for conflicts.");
        } finally {
            setIsScanning(false);
        }
    };

    const handleResolveConflicts = async () => {
        setIsResolving(true);
        try {
            const result = await memoryService.resolveConflicts(currentModel);
            // Store result for display
            setResolutionResult(result);
            setShowResolution(true);

            // Refresh data
            setConflicts([]);
            setShowConflicts(false);
            loadMemory(true);
        } catch (error) {
            console.error("Resolution failed:", error);
            alert("Failed to resolve conflicts.");
        } finally {
            setIsResolving(false);
        }
    };

    const handleClearResolution = () => {
        setResolutionResult(null);
        setShowResolution(false);
    };

    const toggleCategory = (category) => {
        setExpandedCategories(prev => ({
            ...prev,
            [category]: !prev[category]
        }));
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
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleScanConflicts}
                        disabled={isScanning || isResolving}
                        className="glass-hover p-2 rounded-xl text-orange-400 hover:text-orange-300 transition-all disabled:opacity-50"
                        title="Manual Consistency Audit"
                    >
                        {isScanning ? (
                            <div className="w-4 h-4 border-2 border-orange-400 border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                            <ShieldAlert size={18} />
                        )}
                    </button>
                    <button onClick={onClose} className="glass-hover p-2 rounded-xl text-slate-400 hover:text-white transition-all"><X size={20} /></button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6 min-w-[26rem] scrollbar-custom">
                {isLoading ? (
                    <div className="flex items-center justify-center h-32"><div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div></div>
                ) : (
                    <>
                        {/* CONFLICT DETECTION PANEL */}
                        {showConflicts && (
                            <div className="space-y-3 animate-fade-in border-b border-white/10 pb-6 mb-6">
                                <div className="flex items-center justify-between p-3 glass rounded-xl border-2 border-orange-500/30 bg-orange-500/10">
                                    <div className="flex items-center gap-2">
                                        <ShieldAlert size={16} className="text-orange-400" />
                                        <span className="text-sm font-bold text-orange-300">
                                            Consistency Check
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => setShowConflicts(false)}
                                        className="text-slate-500 hover:text-slate-300 transition-all"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>

                                {conflicts.length === 0 ? (
                                    <div className="glass p-4 rounded-xl text-center">
                                        <p className="text-green-400 text-sm font-bold">✓ No Conflicts Detected</p>
                                        <p className="text-slate-500 text-[10px] mt-1">Your knowledge base is clean!</p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="glass p-3 rounded-xl text-xs">
                                            <div className="flex justify-between text-slate-400">
                                                <span>Potential Duplicates:</span>
                                                <span className="text-orange-400 font-bold">{conflicts.length} pairs</span>
                                            </div>
                                        </div>

                                        <div className="max-h-[300px] overflow-y-auto scrollbar-custom space-y-2">
                                            {conflicts.map((conflict, idx) => (
                                                <div key={idx} className="glass p-3 rounded-xl border border-orange-500/20 space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-[9px] text-orange-400 font-bold uppercase">
                                                            {Math.round(conflict.similarity * 100)}% Similar
                                                        </span>
                                                    </div>

                                                    <div className="space-y-2">
                                                        <div className="bg-black/40 p-2 rounded border border-white/5">
                                                            <div className="text-[8px] text-slate-600 mb-1">{conflict.chunk1.chunk_id}</div>
                                                            <div className="text-[10px] text-slate-200 leading-tight">{conflict.chunk1.content}</div>
                                                        </div>

                                                        <div className="bg-black/40 p-2 rounded border border-white/5">
                                                            <div className="text-[8px] text-slate-600 mb-1">{conflict.chunk2.chunk_id}</div>
                                                            <div className="text-[10px] text-slate-200 leading-tight">{conflict.chunk2.content}</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        <button
                                            onClick={handleResolveConflicts}
                                            disabled={isResolving}
                                            className="w-full glass-hover p-3 rounded-xl text-[11px] font-bold text-orange-300 border border-orange-500/30 hover:bg-orange-500/10 transition-all disabled:opacity-50"
                                        >
                                            {isResolving ? (
                                                <span className="flex items-center justify-center gap-2">
                                                    <div className="w-4 h-4 border-2 border-orange-400 border-t-transparent rounded-full animate-spin"></div>
                                                    Resolving Conflicts...
                                                </span>
                                            ) : (
                                                `Resolve All ${conflicts.length} Conflicts with AI`
                                            )}
                                        </button>
                                    </>
                                )}
                            </div>
                        )}
                        {/* AI RESOLUTION RESULT PANEL */}
                        {showResolution && resolutionResult && (
                            <div className="space-y-3 animate-fade-in border-b border-white/10 pb-6 mb-6">
                                <div className="flex items-center justify-between p-3 glass rounded-xl border-2 border-green-500/30 bg-green-500/10">
                                    <div className="flex items-center gap-2">
                                        <Brain size={16} className="text-green-400" />
                                        <span className="text-sm font-bold text-green-300">
                                            Neural Core Resolution
                                        </span>
                                    </div>
                                    <button
                                        onClick={handleClearResolution}
                                        className="text-slate-500 hover:text-slate-300 transition-all text-[10px] font-bold uppercase tracking-widest bg-white/5 px-2 py-1 rounded-md"
                                    >
                                        Clear Window
                                    </button>
                                </div>

                                <div className="glass p-4 rounded-xl space-y-4">
                                    <div className="grid grid-cols-4 gap-2">
                                        <div className="flex flex-col items-center p-2 bg-black/40 rounded-lg border border-white/5">
                                            <span className="text-[10px] text-slate-500">Conflicts</span>
                                            <span className="text-sm font-bold text-white">{resolutionResult.conflicts_resolved}</span>
                                        </div>
                                        <div className="flex flex-col items-center p-2 bg-black/40 rounded-lg border border-white/5">
                                            <span className="text-[10px] text-green-500">Added</span>
                                            <span className="text-sm font-bold text-green-400">{resolutionResult.operations_applied.added}</span>
                                        </div>
                                        <div className="flex flex-col items-center p-2 bg-black/40 rounded-lg border border-white/5">
                                            <span className="text-[10px] text-blue-500">Updated</span>
                                            <span className="text-sm font-bold text-blue-400">{resolutionResult.operations_applied.updated}</span>
                                        </div>
                                        <div className="flex flex-col items-center p-2 bg-black/40 rounded-lg border border-white/5">
                                            <span className="text-[10px] text-red-500">Deleted</span>
                                            <span className="text-sm font-bold text-red-400">{resolutionResult.operations_applied.deleted}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="text-[9px] text-slate-500 uppercase tracking-widest px-1">AI Reasoning Engine Output</div>
                                        <div className="text-[10px] font-mono text-slate-300 bg-black/80 p-3 rounded-xl border border-white/10 max-h-[200px] overflow-y-auto scrollbar-custom whitespace-pre-wrap leading-relaxed">
                                            {resolutionResult.raw_output}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

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

                        {/* LAYER 2: LTM (Atomic Chunks) */}
                        <div className="space-y-3">
                            <button onClick={() => setShowLongTerm(!showLongTerm)} className="w-full flex items-center justify-between text-sm font-semibold text-slate-300 glass-hover p-3 rounded-xl transition-all">
                                <div className="flex items-center gap-2"><Database size={16} className="text-purple-400" /><span>Long-Term Knowledge</span></div>
                                {showLongTerm ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                            </button>
                            {showLongTerm && (
                                <div className="space-y-4 animate-fade-in" ref={scrollRef}>
                                    <div className="flex flex-col gap-3">
                                        <div className="glass p-3 rounded-xl text-[10px] text-slate-500 flex justify-between items-center">
                                            <span>Unified Knowledge Index:</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-slate-400">{Object.values(categorizedChunks).flat().length} atomic facts</span>
                                                <div className="w-[1px] h-3 bg-white/10"></div>
                                                <select
                                                    value={selectedCategory}
                                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                                    className="bg-purple-500/10 text-purple-300 border border-purple-500/20 rounded px-1 py-0.5 outline-none text-[9px] font-bold cursor-pointer hover:bg-purple-500/20 transition-all uppercase tracking-tighter"
                                                >
                                                    <option value="all" className="bg-[#0f172a]">All Categories</option>
                                                    {Object.keys(categorizedChunks).sort().map(cat => (
                                                        <option key={cat} value={cat} className="bg-[#0f172a]">{cat.toUpperCase()}</option>
                                                    ))}
                                                </select>
                                            </div>
                                        </div>
                                    </div>

                                    {isMemoryStreaming && streamingMemory && (
                                        <div className="glass p-4 rounded-xl space-y-3 border-2 border-purple-500/50 bg-purple-500/10 shadow-[0_0_20px_rgba(168,85,247,0.15)] animate-pulse mb-6">
                                            <div className="flex justify-between items-center mb-1">
                                                <div className="text-[10px] text-purple-400 font-black uppercase tracking-widest flex items-center gap-2">
                                                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-ping"></div>
                                                    Live Intelligence Merge
                                                </div>
                                            </div>
                                            <div className="text-slate-100 font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-black/80 p-4 rounded-xl border border-purple-500/30 min-h-[100px]">
                                                {streamingMemory}
                                                <span className="inline-block w-2 h-4 bg-purple-500 ml-1 animate-pulse align-middle"></span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Categorized Chunks View */}
                                    {Object.entries(categorizedChunks)
                                        .filter(([category]) => selectedCategory === 'all' || selectedCategory === category)
                                        .map(([category, chunks]) => {
                                            const isExpanded = !!expandedCategories[category];
                                            return (
                                                <div key={category} className="space-y-2">
                                                    <button
                                                        onClick={() => toggleCategory(category)}
                                                        className="w-full flex items-center justify-between px-1 hover:bg-white/5 py-1 rounded transition-all group"
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <Tag size={12} className={clsx("transition-colors", isExpanded ? "text-purple-500" : "text-slate-600")} />
                                                            <span className={clsx("text-[10px] uppercase font-black tracking-widest transition-colors", isExpanded ? "text-slate-200" : "text-slate-600")}>
                                                                {category} ({chunks.length})
                                                            </span>
                                                        </div>
                                                        <span className="text-[8px] text-slate-600 group-hover:text-slate-400 transition-colors">
                                                            {isExpanded ? '▼ HIDE' : '▲ SHOW'}
                                                        </span>
                                                    </button>

                                                    {isExpanded && (
                                                        <div className="space-y-2 animate-fade-in pl-1">
                                                            {chunks.map((chunk, i) => (
                                                                <div key={chunk.chunk_id || i} className="group relative glass p-3 rounded-xl border border-white/5 hover:border-purple-500/20 transition-all">
                                                                    <div className="text-slate-200 font-medium text-[11px] leading-relaxed">
                                                                        {chunk.content}
                                                                    </div>
                                                                    <div className="absolute right-2 bottom-1 opacity-0 group-hover:opacity-100 transition-opacity text-[8px] text-slate-600 font-mono">
                                                                        {chunk.chunk_id}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}

                                    {/* Legacy/Full Summary Fallback */}
                                    {longTermMemories.length > 0 && Object.keys(categorizedChunks).length === 0 && (
                                        <div className="space-y-3">
                                            <div className="text-[9px] text-slate-600 uppercase tracking-widest px-1">Legacy Truth Base</div>
                                            {longTermMemories.map((m, i) => (
                                                <div key={i} className="glass p-4 rounded-xl space-y-3 border border-purple-500/10">
                                                    <div className="text-slate-200 font-mono text-[11px] leading-relaxed whitespace-pre-wrap bg-black/40 p-3 rounded-lg border border-white/5">
                                                        {m.content}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {Object.keys(categorizedChunks).length === 0 && longTermMemories.length === 0 && (
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
                                            <span>{archivedMemories.length}/10 units</span>
                                        </div>
                                        <p className="text-[9px] text-slate-600 leading-tight">
                                            "Units" are distilled core snapshots of your AI's evolving identity.
                                        </p>
                                    </div>
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
                                                    Restore
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
                    </>
                )}
            </div>
        </aside>
    );
};

export default MemoryPanel;
