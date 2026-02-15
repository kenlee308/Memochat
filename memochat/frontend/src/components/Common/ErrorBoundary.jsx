import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-[#0a0a0c] flex items-center justify-center p-6 text-center">
                    <div className="glass p-8 rounded-3xl border border-red-500/20 max-w-md shadow-2xl animate-fade-in">
                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-500/20">
                            <span className="text-3xl">⚠️</span>
                        </div>
                        <h1 className="text-2xl font-bold bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent mb-4">
                            System Instability Detected
                        </h1>
                        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                            MemoChat encountered a processing error. This is likely due to a malformed data packet or a network desync.
                        </p>
                        <button
                            onClick={() => window.location.reload()}
                            className="w-full py-3 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold transition-all shadow-lg active:scale-[0.98]"
                        >
                            Reset Neural Connection
                        </button>
                        <p className="text-[10px] text-slate-600 mt-4 font-mono uppercase tracking-widest"> Error ID: {this.state.error?.message || 'NULL_PTR'} </p>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
