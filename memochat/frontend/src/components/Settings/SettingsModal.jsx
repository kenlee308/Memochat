import React, { useState, useEffect } from 'react';
import { X, Download, HardDrive, Brain, Zap, Target, RefreshCw } from 'lucide-react';
import { modelService, memoryService } from '../../services/api';

const SettingsModal = ({
    isOpen,
    onClose,
    currentModel,
    onModelChange,
    temperature,
    setTemperature,
    stmSize,
    setStmSize,
    summaryThreshold,
    setSummaryThreshold
}) => {
    const [models, setModels] = useState([]);
    const [exportFormat, setExportFormat] = useState('txt');

    useEffect(() => {
        if (isOpen) {
            loadModels();
        }
    }, [isOpen]);

    const loadModels = async () => {
        try {
            const data = await modelService.listModels();
            setModels(data.models || []);
        } catch (error) {
            console.error("Failed to load models", error);
        }
    };

    const formatSize = (bytes) => {
        if (!bytes) return '';
        const gb = bytes / (1024 * 1024 * 1024);
        if (gb >= 1) return `(${gb.toFixed(1)} GB)`;
        const mb = bytes / (1024 * 1024);
        return `(${mb.toFixed(0)} MB)`;
    };

    const handleExport = async () => {
        try {
            const data = await memoryService.exportMemory(exportFormat);
            const blob = new Blob([data.content || data], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `memory_export_${new Date().toISOString().split('T')[0]}.${exportFormat}`;
            a.click();
        } catch (error) {
            console.error("Export failed", error);
            alert("Failed to export memory.");
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fade-in">
            <div className="glass rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border-2 border-white/10 flex flex-col max-h-[90vh]">
                <div className="flex justify-between items-center p-6 border-b border-white/10 shrink-0">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">System Parameters</h2>
                    <button onClick={onClose} className="glass-hover p-2 rounded-xl text-slate-400 hover:text-white transition-all">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 space-y-8 overflow-y-auto scrollbar-custom">
                    {/* 1. Model Selection */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                            <Zap size={14} className="text-yellow-400" /> Computation Core
                        </label>
                        <select
                            value={currentModel}
                            onChange={(e) => onModelChange(e.target.value)}
                            className="w-full p-3 rounded-xl text-white bg-slate-900 border border-white/10 outline-none transition-all cursor-pointer text-sm appearance-none shadow-inner"
                            style={{
                                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='white'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                                backgroundRepeat: 'no-repeat',
                                backgroundPosition: 'right 1rem center',
                                backgroundSize: '1.2em'
                            }}
                        >
                            {models.length === 0 ? (
                                <option style={{ backgroundColor: '#0f172a', color: 'white' }}>Neural cores loading...</option>
                            ) : (
                                models.map((m, idx) => (
                                    <option key={idx} value={m.name || m} style={{ backgroundColor: '#0f172a', color: 'white' }}>
                                        {m.name || m} {formatSize(m.size)}
                                    </option>
                                ))
                            )}
                        </select>
                    </div>

                    {/* 2. Accuracy vs Creativity */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                <Target size={14} className="text-blue-400" /> Neural Accuracy
                            </label>
                            <span className="text-[10px] font-mono text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">{temperature}</span>
                        </div>
                        <input
                            type="range"
                            min="0.1"
                            max="1.5"
                            step="0.1"
                            value={temperature}
                            onChange={(e) => setTemperature(Number(e.target.value))}
                            className="w-full accent-blue-500 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-[8px] font-black uppercase tracking-tighter">
                            <div className="flex flex-col items-start gap-1">
                                <span className="text-blue-400">⊕ Accuracy / Precise</span>
                                <span className="text-slate-500 font-medium lowercase italic">best for logic</span>
                            </div>
                            <div className="flex flex-col items-end gap-1 text-right">
                                <span className="text-purple-400">Creative / Varying ⊖</span>
                                <span className="text-slate-500 font-medium lowercase italic">best for stories</span>
                            </div>
                        </div>
                        <p className="text-[9px] text-slate-500 leading-relaxed italic border-l-2 border-white/5 pl-3">
                            Determines the randomness of token selection. Lowering this ensures the AI adheres strictly to facts and logical constraints in your Truth Base.
                        </p>
                    </div>

                    {/* 3. Neural Frequency */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                <RefreshCw size={14} className="text-pink-400" /> Synapse Window
                            </label>
                            <span className="text-[10px] font-mono text-pink-400 bg-pink-400/10 px-2 py-0.5 rounded">{stmSize} turns</span>
                        </div>
                        <input
                            type="range"
                            min="5"
                            max="30"
                            step="1"
                            value={stmSize}
                            onChange={(e) => setStmSize(Number(e.target.value))}
                            className="w-full accent-pink-500 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-[8px] font-black uppercase tracking-tighter">
                            <div className="flex flex-col items-start gap-1">
                                <span className="text-green-500">⊕ Speed / Minimalist</span>
                                <span className="text-slate-500 font-medium lowercase italic">GPU friendly</span>
                            </div>
                            <div className="flex flex-col items-end gap-1 text-right">
                                <span className="text-red-500">Long Context / Slower ⊖</span>
                                <span className="text-slate-500 font-medium lowercase italic">identity depth</span>
                            </div>
                        </div>
                        <p className="text-[9px] text-slate-500 leading-relaxed italic border-l-2 border-white/5 pl-3">
                            Controls the Short-Term Memory size. Reducing this allows the local GPU to process logic faster by reducing the active token payload.
                        </p>
                    </div>

                    {/* 4. Sleep Efficiency */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                <Brain size={14} className="text-purple-400" /> Distillation Granularity
                            </label>
                            <span className="text-[10px] font-mono text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded">{summaryThreshold} turns</span>
                        </div>
                        <input
                            type="range"
                            min="3"
                            max="15"
                            step="1"
                            value={summaryThreshold}
                            onChange={(e) => setSummaryThreshold(Number(e.target.value))}
                            className="w-full accent-purple-500 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-[8px] font-black uppercase tracking-tighter">
                            <div className="flex flex-col items-start gap-1">
                                <span className="text-orange-400">⊕ Precision Audit</span>
                                <span className="text-slate-500 font-medium lowercase italic">dense facts</span>
                            </div>
                            <div className="flex flex-col items-end gap-1 text-right">
                                <span className="text-indigo-400">Quick Sleep / Coarse ⊖</span>
                                <span className="text-slate-500 font-medium lowercase italic">fast merge</span>
                            </div>
                        </div>
                        <p className="text-[9px] text-slate-500 leading-relaxed italic border-l-2 border-white/5 pl-3">
                            How often the AI audits its internal logic. Lower values create more surgical, accurate memories by analyzing smaller data batches during "Sleep".
                        </p>
                    </div>

                    {/* 5. Memory Management */}
                    <div className="space-y-4 pt-4 border-t border-white/10">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                            <HardDrive size={14} className="text-indigo-400" /> Persistence
                        </h3>

                        <div className="flex gap-2">
                            <select
                                value={exportFormat}
                                onChange={(e) => setExportFormat(e.target.value)}
                                className="p-2.5 rounded-xl text-xs text-white bg-slate-900 border border-white/10 outline-none cursor-pointer appearance-none pr-8"
                                style={{
                                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='white'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                                    backgroundRepeat: 'no-repeat',
                                    backgroundPosition: 'right 0.5rem center',
                                    backgroundSize: '1em'
                                }}
                            >
                                <option value="txt" style={{ backgroundColor: '#0f172a', color: 'white' }}>Text (.txt)</option>
                                <option value="json" style={{ backgroundColor: '#0f172a', color: 'white' }}>JSON (.json)</option>
                            </select>
                            <button
                                onClick={handleExport}
                                className="flex-1 flex items-center justify-center gap-2 glass-hover text-white rounded-xl p-2.5 transition-all text-xs font-bold hover:bg-white/20 border border-white/5"
                            >
                                <Download size={14} /> Export Identity
                            </button>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-black/40 border-t border-white/5 shrink-0">
                    <button
                        onClick={onClose}
                        className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-sm shadow-lg hover:shadow-blue-500/20 transition-all active:scale-[0.98]"
                    >
                        Apply Neural Parameters
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
