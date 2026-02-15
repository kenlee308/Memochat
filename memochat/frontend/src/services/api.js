import axios from 'axios';
import { systemEvents } from './eventBus';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Intercept requests to log them
api.interceptors.request.use(request => {
    systemEvents.emit('log', {
        message: `[REQ] ${request.method.toUpperCase()} ${request.url}`,
        level: 'HTTP'
    });
    return request;
});

// Intercept responses to log results
api.interceptors.response.use(
    response => {
        systemEvents.emit('log', {
            message: `[RES] ${response.status} ${response.config.url}`,
            level: 'HTTP'
        });
        return response;
    },
    error => {
        const url = error.config?.url || 'unknown';
        systemEvents.emit('log', {
            message: `[ERR] ${error.message} (${url})`,
            level: 'ERROR'
        });
        return Promise.reject(error);
    }
);

export const chatService = {
    sendMessage: async (message, model, systemInstruction, params = {}) => {
        systemEvents.emit('log', { message: `[REQ] POST /chat`, level: 'HTTP' });
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                model,
                system_instruction: systemInstruction,
                temperature: params.temperature ?? 0.7,
                stm_size: params.stmSize ?? 10,
                summary_threshold: params.summaryThreshold ?? 5
            })
        });
        if (!response.ok) {
            systemEvents.emit('log', { message: `[ERR] ${response.status} /chat`, level: 'ERROR' });
            throw new Error('Network response was not ok');
        }
        systemEvents.emit('log', { message: `[RES] ${response.status} /chat`, level: 'HTTP' });
        return response;
    },
    getHistory: async () => {
        const response = await api.get('/chat/history');
        return response.data;
    },
    sleep: async (model, params = {}) => {
        systemEvents.emit('log', { message: `[REQ] POST /chat/sleep`, level: 'HTTP' });
        const response = await fetch(`${API_BASE_URL}/chat/sleep`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: 'SLEEP_TRIGGER',
                model,
                temperature: params.temperature ?? 0.7,
                stm_size: params.stmSize ?? 10,
                summary_threshold: params.summaryThreshold ?? 5
            })
        });
        if (!response.ok) {
            systemEvents.emit('log', { message: `[ERR] ${response.status} /chat/sleep`, level: 'ERROR' });
            throw new Error('Network response was not ok');
        }
        systemEvents.emit('log', { message: `[RES] ${response.status} /chat/sleep`, level: 'HTTP' });
        return response;
    }
};

export const modelService = {
    listModels: async () => {
        const response = await api.get('/models');
        return response.data;
    },
    pullModel: async (modelName) => {
        const response = await api.post(`/models/pull?model_name=${modelName}`);
        return response.data;
    },
};


export const memoryService = {
    getMemory: async () => {
        const response = await api.get('/memory');
        return response.data;
    },
    getLongTermMemory: async () => {
        const response = await api.get('/memory/long-term');
        return response.data;
    },
    restoreMemory: async (index) => {
        const response = await api.post('/memory/restore', { index });
        return response.data;
    },
    exportMemory: async (format) => {
        const response = await api.get(`/memory/export?format=${format}`);
        return response.data;
    },
    getCategories: async () => {
        const response = await api.get('/memory/categories');
        return response.data;
    },
    getHoldingArea: async () => {
        const response = await api.get('/memory/holding-area');
        return response.data;
    },
    approveHoldingItem: async (index, action, newContent = null) => {
        const response = await api.post('/memory/holding-area/approve', { index, action, new_content: newContent });
        return response.data;
    },
    getRelationships: async () => {
        const response = await api.get('/memory/relationships');
        return response.data;
    },
    checkHealth: async () => {
        const response = await api.get('/health');
        return response.data;
    }
};

export default api;
