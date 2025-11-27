import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { chatStream } from '../services/api';
import CitationDetail from './CitationDetail';

const ChatWindow = ({ conversationId, onConversationChange }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [citations, setCitations] = useState({});
  const [copySuccess, setCopySuccess] = useState(false);
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
    // Markdown renderer components
    const markdownComponents = {
      code({ node, inline, className, children, ...props }) {
        const match = /language-(\w+)/.exec(className || '');
        return !inline && match ? (
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={match[1]}
            PreTag="div"
            customStyle={{ margin: '0.5em 0', borderRadius: '4px' }}
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        ) : (
          <code className={className} style={{ backgroundColor: '#f4f4f4', padding: '0.2em 0.4em', borderRadius: '3px', fontSize: '0.9em' }} {...props}>
            {children}
          </code>
        );
      },
      p: ({ children }) => <p style={{ margin: '0.5em 0' }}>{children}</p>,
      h1: ({ children }) => <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', margin: '0.8em 0 0.4em 0' }}>{children}</h1>,
      h2: ({ children }) => <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', margin: '0.7em 0 0.3em 0' }}>{children}</h2>,
      h3: ({ children }) => <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', margin: '0.6em 0 0.3em 0' }}>{children}</h3>,
      ul: ({ children }) => <ul style={{ margin: '0.5em 0', paddingLeft: '1.5em' }}>{children}</ul>,
      ol: ({ children }) => <ol style={{ margin: '0.5em 0', paddingLeft: '1.5em' }}>{children}</ol>,
      li: ({ children }) => <li style={{ margin: '0.2em 0' }}>{children}</li>,
      blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid #ddd', paddingLeft: '1em', margin: '0.5em 0', color: '#666' }}>{children}</blockquote>,
      a: ({ href, children }) => <a href={href} style={{ color: '#3b82f6', textDecoration: 'underline' }} target="_blank" rel="noopener noreferrer">{children}</a>,
    };

    if (!citations || citations.length === 0) {
      return (
        <div className="markdown-content" style={{ lineHeight: '1.6' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {content}
          </ReactMarkdown>
        </div>
      );
    }

    // Find sentence boundaries and insert citations
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
    
    if (lastEnd < content.length) {
      sentences.push({
        text: content.substring(lastEnd),
        endPos: content.length
      });
    }

    // Build parts array with markdown and citations
    const parts = [];
    let citationIndex = 0;
    
    sentences.forEach((sentence, idx) => {
      parts.push(
        <ReactMarkdown
          key={`text-${idx}`}
          remarkPlugins={[remarkGfm]}
          components={markdownComponents}
        >
          {sentence.text}
        </ReactMarkdown>
      );
      
      // Insert citation after every 2 sentences, or at the end
      const shouldInsert = (idx > 0 && (idx + 1) % 2 === 0 && citationIndex < citations.length) ||
                          (idx === sentences.length - 1 && citationIndex < citations.length);
      
      if (shouldInsert) {
        const citation = citations[citationIndex];
        parts.push(
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
    
    // Add remaining citations at the end
    citations.slice(citationIndex).forEach((citation, idx) => {
      parts.push(
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

    return <div className="markdown-content" style={{ lineHeight: '1.6' }}>{parts}</div>;
  };
  
  const handleCopyMessage = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
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
      {/* Copy success notification */}
      {copySuccess && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center space-x-2 animate-fade-in">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>已复制到剪贴板</span>
        </div>
      )}
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
                className={`max-w-3xl rounded-lg px-4 py-3 shadow-sm relative group ${
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
                {/* Copy button */}
                {msg.role === 'assistant' && !msg.isError && (
                  <button
                    onClick={() => handleCopyMessage(msg.content)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-gray-200 text-gray-600 hover:text-gray-800"
                    title="复制消息内容"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
          
          {/* Streaming Message */}
          {streamingMessage && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-lg px-4 py-3 bg-gray-50 text-gray-800 border border-gray-200 shadow-sm relative group">
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
                {/* Copy button for streaming message */}
                <button
                  onClick={() => handleCopyMessage(streamingMessage.content)}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-gray-200 text-gray-600 hover:text-gray-800"
                  title="复制消息内容"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
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

