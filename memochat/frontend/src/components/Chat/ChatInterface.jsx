import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import { Send, Mic, Square, Settings as SettingsIcon, Moon, Brain } from 'lucide-react';
import MessageBubble from './MessageBubble';
import { chatService, memoryService } from '../../services/api';
import { systemEvents } from '../../services/eventBus';
import SettingsModal from '../Settings/SettingsModal';
import MemoryPanel from '../Memory/MemoryPanel';

const ChatInterface = () => {
    const [systemStatus, setSystemStatus] = useState('');
    const [statusLog, setStatusLog] = useState([]); // { time, level, message }
    const [isLogExpanded, setIsLogExpanded] = useState(false);
    const [processStartTime, setProcessStartTime] = useState(null);
    const [elapsedTime, setElapsedTime] = useState(0);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isMemoryOpen, setIsMemoryOpen] = useState(false);
    const [systemRole, setSystemRole] = useState('AI Assistant');
    const [currentModel, setCurrentModel] = useState(() => localStorage.getItem('memochat_model') || 'deepseek-r1:8b');
    const [streamingMemory, setStreamingMemory] = useState('');
    const [isMemoryStreaming, setIsMemoryStreaming] = useState(false);
    const [backendStatus, setBackendStatus] = useState('offline'); // offline, connecting, online

    // Neural Parameters
    const [temperature, setTemperature] = useState(() => Number(localStorage.getItem('memochat_temperature')) || 0.7);
    const [stmSize, setStmSize] = useState(() => Number(localStorage.getItem('memochat_stm_size')) || 10);
    const [summaryThreshold, setSummaryThreshold] = useState(() => Number(localStorage.getItem('memochat_summary_threshold')) || 5);

    const statusDescriptions = {
        'Neural Processing': 'Thinking through the response using the local language model core.',
        'Syncing Files': 'Aligning internal states with manual edits in your text files.',
        'Summarizing Chat': 'Distilling the essence of recent messages into factual nodes.',
        'Checking Truth': 'Auditing new information against the existing Knowledge Base.',
        'Conflict Audit': 'Identifying contradictions and preparing clarification queries.',
        'Merging Memory': 'Merging verified facts into the permanent long-term index.',
        'Consolidating': 'Merging verified facts into the permanent long-term index.',
        'Finalizing': 'Persisting changes to disk and refreshing the memory layers.'
    };

    const messagesEndRef = useRef(null);

    useEffect(() => {
        localStorage.setItem('memochat_model', currentModel);
        localStorage.setItem('memochat_temperature', temperature);
        localStorage.setItem('memochat_stm_size', stmSize);
        localStorage.setItem('memochat_summary_threshold', summaryThreshold);
    }, [currentModel, temperature, stmSize, summaryThreshold]);

    useEffect(() => {
        let timer;
        if (isProcessing && processStartTime) {
            timer = setInterval(() => {
                setElapsedTime(((Date.now() - processStartTime) / 1000).toFixed(1));
            }, 100);
        } else {
            setElapsedTime(0);
        }
        return () => clearInterval(timer);
    }, [isProcessing, processStartTime]);

    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

    // FULL RELOAD FROM BACKEND/FILES
    const loadState = async () => {
        try {
            const [historyData, memoryData] = await Promise.all([
                chatService.getHistory().catch(e => ({ history: [] })),
                memoryService.getMemory().catch(e => ({ short_term: [], system_role: 'AI Assistant' }))
            ]);

            if (historyData && Array.isArray(historyData.history)) {
                const formatted = [];
                historyData.history.forEach(m => {
                    if (m && m.input) {
                        formatted.push({
                            role: 'user',
                            content: m.input,
                            timestamp: (m.timestamp || 0) * 1000
                        });
                        formatted.push({
                            role: 'assistant',
                            content: m.output || '',
                            model: m.model || 'Logic Core',
                            timestamp: (m.timestamp || 0) * 1000
                        });
                    }
                });
                setMessages(formatted);
            } else {
                setMessages([]);
            }

            if (memoryData && memoryData.system_role) {
                setSystemRole(memoryData.system_role);
            }
        } catch (error) {
            console.error("Critical Load Error:", error);
            setMessages([]); // Fallback to empty to avoid crash
        }
    };

    useEffect(() => {
        // Event Bus Listener for Low-Level Logs
        const handleLog = (data) => addSystemLog(data.message, data.level);
        systemEvents.on('log', handleLog);

        let isFirstLoad = true;
        const checkConnection = async () => {
            try {
                await memoryService.checkHealth();
                setBackendStatus('online');
                if (isFirstLoad) {
                    loadState();
                    isFirstLoad = false;
                }
            } catch (e) {
                setBackendStatus('offline');
            }
        };

        checkConnection();
        const interval = setInterval(checkConnection, 3000);
        return () => {
            clearInterval(interval);
            systemEvents.off('log', handleLog);
        };
    }, []);

    useEffect(() => { scrollToBottom(); }, [messages]);

    const transitionStatus = async (name, delay = 0) => {
        const now = Date.now();
        setSystemStatus(name);
        if (delay > 0) await new Promise(r => setTimeout(r, delay));
        return Date.now() - now;
    };

    const addSystemLog = (message, level = 'INFO') => {
        const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setStatusLog(prev => [{ time, level, message }, ...prev].slice(0, 50));
    };

    const handleSend = async () => {
        if (!input.trim()) return;
        const userMsg = { role: 'user', content: input, timestamp: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        setIsProcessing(true);
        setProcessStartTime(Date.now());
        addSystemLog(`User query received: "${userMsg.content.slice(0, 20)}..."`, 'INPUT');
        setStreamingMemory('');
        setIsMemoryStreaming(false);

        const stepStart = Date.now();
        setSystemStatus('Neural Processing');
        addSystemLog(`Engagement: ${currentModel} logic core...`, 'CORE');

        const params = { temperature, stmSize, summaryThreshold };

        try {
            const response = await chatService.sendMessage(userMsg.content, currentModel, null, params);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let assistantMessage = {
                role: 'assistant',
                content: '',
                model: currentModel,
                timestamp: Date.now()
            };
            setMessages(prev => [...prev, assistantMessage]);

            let fullContent = '';
            let isRoutingToMemory = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });

                if (chunk.includes('__MEMORY_CHUNK__')) {
                    isRoutingToMemory = true;
                    setIsMemoryStreaming(true);
                    setIsMemoryOpen(true);
                    setSystemStatus('Consolidating');

                    const parts = chunk.split('__MEMORY_CHUNK__');
                    if (parts[0]) fullContent += parts[0];
                    for (let i = 1; i < parts.length; i++) {
                        setStreamingMemory(prev => prev + parts[i]);
                    }
                } else if (chunk.includes('__METADATA__')) {
                    const parts = chunk.split('__METADATA__');
                    if (parts[0]) {
                        if (isRoutingToMemory) setStreamingMemory(prev => prev + parts[0]);
                        else fullContent += parts[0];
                    }

                    try {
                        const meta = JSON.parse(parts[1]);
                        if (meta.consolidated) {
                            addSystemLog('Auto-consolidation complete: Knowledge persisted.', 'SUCCESS');
                            setMessages(prev => [...prev, {
                                role: 'system',
                                content: '✨ Auto-consolidation triggered: Previous messages committed to long-term memory.',
                                timestamp: Date.now()
                            }]);
                        }
                        loadState();
                    } catch (e) { addSystemLog(`Metadata link failed: ${e.message}`, 'ERROR'); }
                    isRoutingToMemory = false;
                } else {
                    if (isRoutingToMemory) {
                        setStreamingMemory(prev => prev + chunk);
                    } else {
                        fullContent += chunk;
                    }
                }

                // Update the last message (the assistant one) in real-time
                setMessages(prev => {
                    const updated = [...prev];
                    if (updated.length > 0) {
                        updated[updated.length - 1] = { ...assistantMessage, content: fullContent };
                    }
                    return updated;
                });
            }

            addSystemLog(`Response stream finalized in ${((Date.now() - stepStart) / 1000).toFixed(2)}s.`, 'READY');

        } catch (error) {
            console.error("Chat error:", error);
            setSystemStatus('Error');
            setMessages(prev => [...prev, { role: 'system', content: `Error: ${error.message}` }]);
        } finally {
            setIsProcessing(false);
            setSystemStatus('');
            setTimeout(() => {
                setIsMemoryStreaming(false);
                setStreamingMemory('');
            }, 3000);
        }
    };

    const handleSleep = async () => {
        setIsProcessing(true);
        setProcessStartTime(Date.now());
        addSystemLog('Initiating systemic Deep Sleep distillation...', 'SYSTEM');
        setStreamingMemory('');
        setIsMemoryStreaming(true);
        setIsMemoryOpen(true);

        let stepStart = Date.now();
        try {
            await transitionStatus('Syncing Files', 600);
            addSystemLog('Syncing operational states with physical drive.', 'SYNC');

            stepStart = Date.now();
            await transitionStatus('Summarizing Chat', 800);
            addSystemLog('Distilling chat fragments into conceptual nodes.', 'SUMM');

            stepStart = Date.now();
            setSystemStatus('Checking Truth');
            addSystemLog('Auditing new information against current truth base.', 'AUDIT');

            const params = { temperature, stmSize, summaryThreshold };
            const response = await chatService.sleep(currentModel, params);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let isRoutingToMemory = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });

                if (chunk.includes('__MEMORY_CHUNK__')) {
                    isRoutingToMemory = true;
                    const parts = chunk.split('__MEMORY_CHUNK__');
                    for (let i = 1; i < parts.length; i++) {
                        setStreamingMemory(prev => prev + parts[i]);
                    }
                    setSystemStatus('Consolidating');
                } else if (chunk.includes('__METADATA__')) {
                    const parts = chunk.split('__METADATA__');
                    if (isRoutingToMemory && parts[0]) setStreamingMemory(prev => prev + parts[0]);
                    isRoutingToMemory = false;
                } else if (isRoutingToMemory) {
                    setStreamingMemory(prev => prev + chunk);
                }
            }

            addSystemLog('Deep distillation complete.', 'SUCCESS');

            stepStart = Date.now();
            await transitionStatus('Finalizing', 800);
            addSystemLog('Memory layers refreshed. Ready for next cycle.', 'READY');

            await loadState();

            setMessages(prev => [
                ...prev,
                {
                    role: 'system',
                    content: '😴 Conversation consolidated into Long-Term Memory. Truth base finalized.',
                    timestamp: Date.now()
                }
            ]);

        } catch (error) {
            console.error("Sleep error:", error);
            setSystemStatus('Error');
        } finally {
            setIsProcessing(false);
            setSystemStatus('');
            setTimeout(() => {
                setIsMemoryStreaming(false);
                setStreamingMemory('');
            }, 3000);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-screen w-full text-slate-100 overflow-hidden bg-[#0a0a0c]">
            {/* Header */}
            <header className="glass flex flex-col px-6 py-4 shadow-xl border-b border-white/10 z-50">
                <div className="flex items-center justify-between">
                    <div className="flex-1 flex flex-col items-start gap-0.5">
                        <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent tracking-tight">
                                MemoChat
                            </h1>
                            <span className="glass px-2 py-0.5 rounded-lg text-[9px] uppercase font-bold text-slate-500 border border-white/5 tracking-widest">
                                {currentModel}
                            </span>
                        </div>
                        <div className="text-[10px] font-medium text-purple-400/70 flex items-center gap-1 overflow-hidden max-w-[40vw]">
                            <span className="text-slate-600 uppercase text-[8px] tracking-tighter font-black">Core Persona:</span>
                            <span className="truncate italic">"{systemRole}"</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {isProcessing && (
                            <div className="flex items-center gap-3 bg-blue-500/5 px-3 py-1.5 rounded-xl border border-blue-500/10">
                                <div className="flex flex-col items-end">
                                    <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest animate-pulse">{systemStatus}</span>
                                    <span className="text-[8px] text-slate-500 tabular-nums font-mono">T-PLUS: {elapsedTime}s</span>
                                </div>
                                <div className="w-[1px] h-6 bg-white/5"></div>
                                <div className="hidden lg:block max-w-[400px]">
                                    <p className="text-[9px] text-slate-400 italic leading-tight">
                                        {statusDescriptions[systemStatus] || 'Initializing sequence...'}
                                    </p>
                                </div>
                            </div>
                        )}
                        {!isProcessing && (
                            <span className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.3em] mr-1 opacity-40">
                                System: Ready
                            </span>
                        )}
                        <div className="flex items-center gap-1.5 border-l border-white/5 pl-3">
                            <button onClick={() => setIsMemoryOpen(!isMemoryOpen)} className={`glass-hover p-2.5 rounded-xl transition-all ${isMemoryOpen ? 'text-purple-400 bg-purple-500/20 border border-purple-500/30' : 'text-slate-400'}`}>
                                <Brain size={18} />
                            </button>
                            <button onClick={handleSleep} disabled={isProcessing} title="Consolidate & Clear" className={`glass-hover p-2.5 rounded-xl transition-all ${isProcessing ? 'text-indigo-400/50 cursor-not-allowed' : 'text-indigo-400 hover:text-indigo-300'}`}>
                                <Moon size={18} />
                            </button>
                            <button onClick={() => setIsSettingsOpen(true)} className="glass-hover p-2.5 rounded-xl text-slate-400 hover:text-white transition-all">
                                <SettingsIcon size={18} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* System Log Monitor */}
                <div className="mt-4 pt-4 border-t border-white/5 relative group">
                    <button
                        onClick={() => setIsLogExpanded(!isLogExpanded)}
                        className="absolute right-0 top-3 glass-hover p-1 rounded-md text-slate-600 hover:text-blue-400 transition-all z-10"
                        title={isLogExpanded ? "Collapse Logs" : "Expand Logs"}
                    >
                        {isLogExpanded ? <span className="text-[10px]">▲</span> : <span className="text-[10px]">▼</span>}
                    </button>

                    <div className={clsx(
                        "font-mono text-[9px] overflow-y-auto scrollbar-hidden transition-all duration-300 ease-in-out px-1",
                        isLogExpanded ? "h-[54px]" : "h-[18px]"
                    )}>
                        {statusLog.length === 0 ? (
                            <div className="text-slate-700 flex items-center gap-2 italic">
                                <span>[{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}]</span>
                                <span className="font-bold opacity-50 uppercase tracking-widest text-[8px]">Bootstrap</span>
                                <span className="opacity-40">System ready. Waiting for user engagement...</span>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-1">
                                {statusLog.map((log, i) => (
                                    <div key={i} className={clsx(
                                        "flex items-baseline gap-3 animate-fade-in group/item",
                                        i === 0 ? "opacity-100" : "opacity-40 hover:opacity-100 transition-opacity"
                                    )}>
                                        <span className="text-slate-600 shrink-0 select-none">[{log.time}]</span>
                                        <span className={clsx(
                                            "font-black uppercase tracking-widest text-[8px] min-w-[45px] select-none",
                                            log.level === 'ERROR' ? 'text-red-500' :
                                                log.level === 'SUCCESS' ? 'text-green-500' :
                                                    log.level === 'CORE' ? 'text-purple-500' :
                                                        'text-blue-500'
                                        )}>
                                            {log.level}
                                        </span>
                                        <span className="text-slate-400 truncate group-hover/item:whitespace-normal group-hover/item:overflow-visible transition-all">
                                            {log.message}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <main className="flex-1 flex flex-row overflow-hidden relative">
                {/* Chat Section */}
                <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-transparent to-black/20">
                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-custom">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400 animate-fade-in opacity-40">
                                <div className="text-6xl mb-4">💬</div>
                                <p className="text-lg font-medium italic">Empty space...</p>
                            </div>
                        )}
                        {Array.isArray(messages) && messages.map((msg, idx) => {
                            if (!msg) return null;
                            return (
                                <MessageBubble
                                    key={idx}
                                    role={msg.role}
                                    content={msg.content}
                                    timestamp={msg.timestamp}
                                    model={msg.model}
                                />
                            );
                        })}
                        {isProcessing && (
                            <div className="flex w-full mt-2 space-x-3 animate-fade-in">
                                <div className="glass p-4 rounded-2xl rounded-bl-none">
                                    <div className="flex gap-1">
                                        <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-1.5 h-1.5 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-6 pt-2">
                        <div className="glass flex items-end gap-3 p-3 rounded-2xl shadow-2xl focus-within:ring-2 focus-within:ring-blue-500/50 transition-all border border-white/5">
                            <button onClick={() => setIsRecording(!isRecording)} className={`p-2.5 rounded-xl transition-all ${isRecording ? 'bg-red-500/20 text-red-400' : 'glass-hover text-slate-400'}`}>
                                {isRecording ? <Square size={20} /> : <Mic size={20} />}
                            </button>
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyPress}
                                placeholder={`Talk to your AI...`}
                                className="flex-1 bg-transparent border-none focus:ring-0 resize-none max-h-32 text-slate-100 placeholder-slate-500 outline-none text-sm leading-relaxed"
                                rows={1}
                                style={{ minHeight: '44px' }}
                            />
                            <button onClick={handleSend} disabled={!input.trim() || isProcessing} className="p-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 rounded-xl text-white transition-all shadow-lg">
                                <Send size={20} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Sidebar Memory Panel */}
                <MemoryPanel
                    isOpen={isMemoryOpen}
                    onClose={() => setIsMemoryOpen(false)}
                    streamingMemory={streamingMemory}
                    isMemoryStreaming={isMemoryStreaming}
                />
            </main>

            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                currentModel={currentModel}
                onModelChange={setCurrentModel}
                temperature={temperature}
                setTemperature={setTemperature}
                stmSize={stmSize}
                setStmSize={setStmSize}
                summaryThreshold={summaryThreshold}
                setSummaryThreshold={setSummaryThreshold}
            />

            {/* Service Status Overlay */}
            {backendStatus === 'offline' && (
                <div className="absolute inset-0 z-[100] glass backdrop-blur-xl flex items-center justify-center p-8 bg-black/40">
                    <div className="max-w-md w-full text-center space-y-8 animate-fade-in">
                        <div className="relative">
                            <div className="w-24 h-24 bg-gradient-to-tr from-blue-500/20 to-purple-500/20 rounded-full flex items-center justify-center mx-auto border border-white/5 shadow-2xl">
                                <Brain size={48} className="text-blue-400 animate-pulse" />
                            </div>
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 border-2 border-dashed border-blue-500/20 rounded-full animate-spin-slow"></div>
                        </div>

                        <div className="space-y-3">
                            <h2 className="text-2xl font-black bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent uppercase tracking-wider">
                                Synchronizing Core
                            </h2>
                            <p className="text-slate-500 text-sm font-medium leading-relaxed italic">
                                Initializing neural pathways and verifying local truth base...
                            </p>
                        </div>

                        <div className="flex flex-col gap-2 items-center">
                            <div className="flex gap-1.5">
                                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '200ms' }}></div>
                                <div className="w-1.5 h-1.5 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '400ms' }}></div>
                            </div>
                            <span className="text-[10px] text-slate-600 font-bold uppercase tracking-widest">Awaiting Backend Link</span>
                        </div>

                        <div className="pt-4 border-t border-white/5">
                            <p className="text-[9px] text-slate-700 font-black uppercase tracking-tighter">
                                Target: http://127.0.0.1:8000/health
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChatInterface;
