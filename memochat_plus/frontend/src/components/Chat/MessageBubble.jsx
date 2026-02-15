import React, { useState } from 'react';
import clsx from 'clsx';
import { Brain } from 'lucide-react';

const MessageBubble = ({ role, content, timestamp, model }) => {
    const isUser = role === 'user';
    const isSystem = role === 'system';
    const [isThoughtOpen, setIsThoughtOpen] = useState(false);
    const [hasAutoOpened, setHasAutoOpened] = useState(false);

    const parseThinking = (text) => {
        if (typeof text !== 'string') return { thinking: null, message: '', isFinished: true };

        let isFinished = true;
        // Define common reasoning tag pairs
        const tagPairs = [
            { open: /<think>/i, close: /<\/think>/i, regex: /<think>([\s\S]*?)<\/think>/i },
            { open: /<thought>/i, close: /<\/thought>/i, regex: /<thought>([\s\S]*?)<\/thought>/i },
            { open: /<\|thought\|>/i, close: /<\|end_thought\|>/i, regex: /<\|thought\|>([\s\S]*?)<\|end_thought\|>/i }
        ];

        for (const pair of tagPairs) {
            const match = text.match(pair.regex);
            if (match) {
                return {
                    thinking: match[1].trim(),
                    message: text.replace(match[0], '').trim(),
                    isFinished: true
                };
            }

            // Fallback: Open tag exists but no closing tag
            if (pair.open.test(text)) {
                const parts = text.split(pair.open);
                return {
                    thinking: parts[1].trim(),
                    message: parts[0].trim() || 'Neural Processing active...',
                    isFinished: false
                };
            }
        }

        return { thinking: null, message: text, isFinished: true };
    };

    const { thinking, message, isFinished } = parseThinking(content || '');

    // Auto-open effect
    React.useEffect(() => {
        if (thinking && !isFinished && !hasAutoOpened) {
            setIsThoughtOpen(true);
            setHasAutoOpened(true);
        }
    }, [thinking, isFinished, hasAutoOpened]);

    // Handle system message early return AFTER hooks
    if (isSystem) {
        return (
            <div className="flex justify-center my-4 animate-fade-in px-4">
                <div className="glass px-6 py-2.5 rounded-full text-[10px] text-slate-500 max-w-lg text-center font-bold tracking-[0.1em] uppercase border border-white/5 shadow-inner">
                    ✨ {content}
                </div>
            </div>
        );
    }

    let formattedTime = '';
    try {
        if (timestamp) {
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                formattedTime = date.toLocaleString([], {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
        }
    } catch (e) {
        console.warn("Timestamp format error", e);
    }

    return (
        <div className={clsx("flex flex-col w-full mt-4 animate-fade-in", isUser ? "items-end" : "items-start")}>
            {/* Meta Header */}
            <div className={clsx("flex items-center gap-2 mb-1.5 px-2 text-[8px] font-black uppercase tracking-widest text-slate-500", isUser && "flex-row-reverse")}>
                <span>{isUser ? 'Human Subject' : `Core Entity (${model || 'Logic'})`}</span>
                <span className="w-1 h-1 bg-slate-700 rounded-full"></span>
                <span className="font-mono">{formattedTime}</span>
            </div>

            <div className={clsx(
                "flex flex-col p-4 rounded-2xl shadow-xl max-w-[90%] lg:max-w-[70%]",
                isUser
                    ? "bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-tr-none border border-white/10"
                    : "glass text-slate-100 rounded-tl-none border border-white/5"
            )}>
                {!isUser && thinking && (
                    <div className="mb-4 border-b border-white/5 pb-3">
                        <button
                            onClick={() => setIsThoughtOpen(!isThoughtOpen)}
                            className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-purple-400 hover:text-purple-300 transition-colors bg-purple-500/10 px-3 py-1.5 rounded-lg border border-purple-500/20 shadow-sm"
                        >
                            <Brain size={12} className="animate-pulse" />
                            <span>Neural Core Analysis</span>
                            {isThoughtOpen ? '▲' : '▼'}
                        </button>
                        {isThoughtOpen && (
                            <div className="text-[11px] text-slate-400 font-mono italic leading-relaxed bg-black/40 p-4 rounded-xl border border-purple-500/10 animate-slide-down max-h-80 overflow-y-auto scrollbar-custom shadow-inner">
                                {thinking}
                            </div>
                        )}
                    </div>
                )}

                <span className="text-[13px] leading-relaxed whitespace-pre-wrap font-medium">{message}</span>
            </div>
        </div>
    );
};

export default MessageBubble;
