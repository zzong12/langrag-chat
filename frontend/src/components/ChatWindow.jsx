import React, { useState, useRef, useEffect } from 'react';
import { chatStream } from '../services/api';
import CitationDetail from './CitationDetail';

const ChatWindow = ({ conversationId, onConversationChange }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [citations, setCitations] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setSelectedCitation(null);

    // Add user message to UI
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newUserMessage]);

    // Initialize streaming message
    const messageId = Date.now();
    const newStreamingMessage = {
      id: messageId,
      role: 'assistant',
      content: '',
      citations: [],
      timestamp: new Date(),
    };
    setStreamingMessage(newStreamingMessage);
    setCitations({});

    try {
      let currentConversationId = conversationId;
      let fullContent = '';
      const messageCitations = [];

      // Stream response
      for await (const chunk of chatStream(userMessage, conversationId)) {
        if (chunk.type === 'done') {
          // Update conversation ID if new
          if (chunk.conversation_id && chunk.conversation_id !== currentConversationId) {
            currentConversationId = chunk.conversation_id;
            onConversationChange(chunk.conversation_id);
          }
        } else if (chunk.type === 'text') {
          fullContent += chunk.content;
          setStreamingMessage({
            ...newStreamingMessage,
            content: fullContent,
            citations: messageCitations,
          });
        } else if (chunk.type === 'citation') {
          const citationId = `cite-${chunk.index}`;
          const citationData = {
            id: citationId,
            index: chunk.index,
            filename: chunk.filename,
            document_id: chunk.document_id,
            preview: chunk.preview || chunk.content?.substring(0, 200) || '',
            content: chunk.content || chunk.preview || '',
          };
          messageCitations.push(citationData);
          setCitations(prev => ({
            ...prev,
            [citationId]: citationData
          }));
          setStreamingMessage({
            ...newStreamingMessage,
            content: fullContent,
            citations: [...messageCitations],
          });
        } else if (chunk.type === 'error') {
          throw new Error(chunk.content);
        }
      }

      // Add completed message to messages
      setMessages((prev) => [...prev, {
        ...newStreamingMessage,
        content: fullContent,
        citations: messageCitations,
      }]);
      setStreamingMessage(null);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message}`,
        isError: true,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setStreamingMessage(null);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const renderContentWithCitations = (content, citations) => {
    if (!citations || citations.length === 0) {
      return <div className="whitespace-pre-wrap leading-relaxed">{content}</div>;
    }

    // Insert citations at natural break points (sentence endings)
    const parts = [];
    let lastIndex = 0;
    let citationIndex = 0;
    
    // Find sentence boundaries
    const sentencePattern = /([.!?。！？]\s+)/g;
    const sentences = [];
    let match;
    let lastEnd = 0;
    
    while ((match = sentencePattern.exec(content)) !== null) {
      const sentenceEnd = match.index + match[0].length;
      sentences.push({
        text: content.substring(lastEnd, sentenceEnd),
        endPos: sentenceEnd
      });
      lastEnd = sentenceEnd;
    }
    
    // Add remaining text
    if (lastEnd < content.length) {
      sentences.push({
        text: content.substring(lastEnd),
        endPos: content.length
      });
    }

    // Insert citations after every 2-3 sentences, or at the end
    const result = [];
    sentences.forEach((sentence, idx) => {
      result.push(
        <span key={`text-${idx}`}>{sentence.text}</span>
      );
      
      // Insert citation after every 2 sentences, or at the end if we have remaining citations
      const shouldInsert = (idx > 0 && (idx + 1) % 2 === 0 && citationIndex < citations.length) ||
                          (idx === sentences.length - 1 && citationIndex < citations.length);
      
      if (shouldInsert) {
        const citation = citations[citationIndex];
        result.push(
          <CitationMarker
            key={`cite-${citationIndex}`}
            citation={citation}
            onClick={() => {
              const fullCitation = citations[citation.id] || citation;
              setSelectedCitation({
                ...fullCitation,
                index: citation.index,
              });
            }}
          />
        );
        citationIndex++;
      }
    });
    
    // Add any remaining citations at the very end
    citations.slice(citationIndex).forEach((citation, idx) => {
      result.push(
        <CitationMarker
          key={`end-cite-${idx}`}
          citation={citation}
          onClick={() => {
            const fullCitation = citations[citation.id] || citation;
            setSelectedCitation({
              ...fullCitation,
              index: citation.index,
            });
          }}
        />
      );
    });

    return <div className="whitespace-pre-wrap leading-relaxed">{result}</div>;
  };

  const CitationMarker = ({ citation, onClick }) => {
    if (!citation) return null;
    
    return (
      <button
        onClick={onClick}
        className="inline-flex items-center mx-1 px-2 py-0.5 bg-blue-100 hover:bg-blue-200 text-blue-700 text-xs font-semibold rounded-md transition-all cursor-pointer shadow-sm hover:shadow-md"
        title={`点击查看引用详情: ${citation.filename}`}
      >
        <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span className="font-bold">[{citation.index + 1}]</span>
      </button>
    );
  };

  return (
    <div className="flex h-full bg-white">
      {/* Main Chat Area */}
      <div className={`flex-1 flex flex-col ${selectedCitation ? 'mr-96' : ''} transition-all duration-300`}>
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !streamingMessage && (
            <div className="text-center text-gray-500 mt-12">
              <h2 className="text-2xl font-semibold mb-2">Welcome to RAG Chat</h2>
              <p>Start a conversation by typing a message below.</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg px-4 py-3 shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : msg.isError
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-50 text-gray-800 border border-gray-200'
                }`}
              >
                {renderContentWithCitations(msg.content, msg.citations)}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-300">
                    <p className="text-xs font-semibold mb-2 text-gray-600">引用来源:</p>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((citation, cidx) => (
                        <button
                          key={cidx}
                          onClick={() => {
                            const fullCitation = citations[citation.id] || citation;
                            setSelectedCitation({
                              ...fullCitation,
                              index: citation.index,
                            });
                          }}
                          className="text-xs px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded border border-blue-200 transition-colors"
                        >
                          {citation.filename}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {/* Streaming Message */}
          {streamingMessage && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-lg px-4 py-3 bg-gray-50 text-gray-800 border border-gray-200 shadow-sm">
                {renderContentWithCitations(streamingMessage.content, streamingMessage.citations)}
                <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse"></span>
                {streamingMessage.citations && streamingMessage.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-300">
                    <p className="text-xs font-semibold mb-2 text-gray-600">引用来源 ({streamingMessage.citations.length}):</p>
                    <div className="flex flex-wrap gap-2">
                      {streamingMessage.citations.map((citation, cidx) => (
                        <button
                          key={cidx}
                          onClick={() => {
                            const fullCitation = citations[citation.id] || citation;
                            setSelectedCitation({
                              ...fullCitation,
                              index: citation.index,
                            });
                          }}
                          className="text-xs px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded border border-blue-200 transition-colors"
                        >
                          {citation.filename}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {loading && !streamingMessage && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <form onSubmit={handleSend} className="flex space-x-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Citation Detail Sidebar */}
      {selectedCitation && (
        <div className="absolute right-0 top-0 bottom-0 w-96 z-40 shadow-2xl bg-white">
          <CitationDetail
            citation={selectedCitation}
            onClose={() => setSelectedCitation(null)}
          />
        </div>
      )}
    </div>
  );
};

export default ChatWindow;

