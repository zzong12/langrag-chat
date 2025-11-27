import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat API
export const chat = async (message, conversationId = null) => {
  try {
    const response = await api.post('/api/chat', {
      message,
      conversation_id: conversationId,
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to send message');
  }
};

// Streaming chat API
export const chatStream = async function* (message, conversationId = null) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            try {
              const jsonStr = trimmedLine.slice(6).trim();
              if (jsonStr) {
                const data = JSON.parse(jsonStr);
                yield data;
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', trimmedLine, e);
              // Skip invalid JSON but continue processing
            }
          } else if (trimmedLine && !trimmedLine.startsWith(':')) {
            // Handle non-standard SSE format
            try {
              const data = JSON.parse(trimmedLine);
              yield data;
            } catch (e) {
              // Ignore non-JSON lines
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error) {
    console.error('Stream error:', error);
    throw new Error(error.message || 'Failed to stream message');
  }
};

// Documents API
export const getDocuments = async () => {
  try {
    const response = await api.get('/api/documents');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch documents');
  }
};

export const uploadDocument = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to upload document');
  }
};

export const deleteDocument = async (documentId) => {
  try {
    const response = await api.delete(`/api/documents/${documentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to delete document');
  }
};

export const reloadDocument = async (documentId) => {
  try {
    const response = await api.post(`/api/documents/${documentId}/reload`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to reload document');
  }
};

export const clearIndex = async () => {
  try {
    const response = await api.post('/api/documents/clear-index');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to clear index');
  }
};

export default api;

