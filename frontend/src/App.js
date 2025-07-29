import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  Send, 
  Image, 
  Search, 
  MessageSquare, 
  Loader, 
  ExternalLink,
  Bot,
  User,
  FileText,
  Upload,
  Settings,
  BookOpen,
  Globe
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import DocumentUpload from './components/DocumentUpload';
import DocumentBrowser from './components/DocumentBrowser';
import SearchModeSelector from './components/SearchModeSelector';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [websocket, setWebsocket] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [statusMessage, setStatusMessage] = useState('');
  const [searchMode, setSearchMode] = useState('auto');
  const [showDocuments, setShowDocuments] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [searchStats, setSearchStats] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initialize session and WebSocket
  useEffect(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    
    // Initialize WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/ws/${newSessionId}`);
    
    ws.onopen = () => {
      setConnectionStatus('connected');
      setWebsocket(ws);
      toast.success('Connected to AI Chat');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'response') {
        const newMessage = {
          id: Date.now(),
          type: 'assistant',
          content: data.response,
          imagePath: data.image_path,
          searchQueries: data.search_queries,
          sources: data.sources,
          searchStats: data.search_stats,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, newMessage]);
        setIsLoading(false);
        setStatusMessage('');
        
        if (data.search_stats) {
          setSearchStats(data.search_stats);
        }
      } else if (data.type === 'status') {
        setStatusMessage(data.message);
        
        if (data.status_type === 'error') {
          toast.error(data.message);
        }
      }
    };
    
    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setWebsocket(null);
      toast.error('Disconnected from AI Chat');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      toast.error('Connection error');
    };
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  // Load documents
  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/rag/documents`);
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  // Handle document upload success
  const handleUploadSuccess = () => {
    loadDocuments();
    toast.success('Document uploaded successfully!');
  };

  // Handle document deletion
  const handleDocumentDelete = async (documentId) => {
    try {
      await axios.delete(`${API_BASE_URL}/rag/documents/${documentId}`);
      loadDocuments();
      toast.success('Document deleted successfully!');
    } catch (error) {
      console.error('Error deleting document:', error);
      toast.error('Failed to delete document');
    }
  };

  // Send message via WebSocket
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !websocket) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setStatusMessage('Processing your request...');

    // Send via WebSocket with search mode
    websocket.send(JSON.stringify({
      type: 'chat',
      message: inputMessage,
      search_mode: searchMode
    }));

    setInputMessage('');
  };

  // Fallback to REST API if WebSocket fails
  const sendMessageREST = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: inputMessage,
        session_id: sessionId,
        search_mode: searchMode
      });

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        imagePath: response.data.image_path,
        searchQueries: response.data.search_queries,
        sources: response.data.sources,
        searchStats: response.data.search_stats,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (response.data.search_stats) {
        setSearchStats(response.data.search_stats);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsLoading(false);
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (websocket && connectionStatus === 'connected') {
        sendMessage();
      } else {
        sendMessageREST();
      }
    }
  };

  const clearChat = () => {
    setMessages([]);
    if (sessionId) {
      axios.delete(`${API_BASE_URL}/sessions/${sessionId}`)
        .catch(error => console.error('Error clearing session:', error));
    }
    toast.success('Chat cleared');
  };

  const MessageComponent = ({ message }) => {
    const isUser = message.type === 'user';
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {/* Avatar */}
          <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              isUser ? 'bg-blue-500' : 'bg-gray-600'
            }`}>
              {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
            </div>
          </div>
          
          {/* Message Content */}
          <div className={`rounded-lg px-4 py-2 ${
            isUser 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-900 border border-gray-200'
          }`}>
            {/* Text Content */}
            <div className="prose prose-sm max-w-none">
              {isUser ? (
                <p className="mb-0">{message.content}</p>
              ) : (
                <ReactMarkdown
                  components={{
                    code({node, inline, className, children, ...props}) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>
            
            {/* Generated Image */}
            {message.imagePath && (
              <div className="mt-3">
                <img 
                  src={`${API_BASE_URL}/images/${message.imagePath.split('/').pop()}`}
                  alt="Generated image"
                  className="max-w-full rounded-lg"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              </div>
            )}
            
            {/* Search Queries */}
            {message.searchQueries && message.searchQueries.length > 0 && (
              <div className="mt-3 p-2 bg-blue-50 rounded border-l-4 border-blue-400">
                <div className="flex items-center mb-1">
                  <Search size={14} className="text-blue-600 mr-1" />
                  <span className="text-sm font-medium text-blue-800">Search Queries:</span>
                </div>
                <ul className="text-sm text-blue-700">
                  {message.searchQueries.map((query, index) => (
                    <li key={index} className="list-disc list-inside">{query}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 p-2 bg-green-50 rounded border-l-4 border-green-400">
                <div className="flex items-center mb-1">
                  <ExternalLink size={14} className="text-green-600 mr-1" />
                  <span className="text-sm font-medium text-green-800">Sources:</span>
                </div>
                <ul className="text-sm">
                  {message.sources.map((source, index) => (
                    <li key={index} className="mb-1">
                      {source.type === 'document' ? (
                        <div className="flex items-center text-green-700">
                          <FileText size={12} className="mr-1" />
                          <span className="font-medium">{source.title}</span>
                          {source.page && <span className="text-gray-500 ml-1">(Page {source.page})</span>}
                        </div>
                      ) : (
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-green-700 hover:text-green-900 underline flex items-center"
                        >
                          <Globe size={12} className="mr-1" />
                          {source.title}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Search Stats */}
            {message.searchStats && (
              <div className="mt-3 p-2 bg-purple-50 rounded border-l-4 border-purple-400">
                <div className="flex items-center mb-1">
                  <Search size={14} className="text-purple-600 mr-1" />
                  <span className="text-sm font-medium text-purple-800">Search Information:</span>
                </div>
                <div className="text-sm text-purple-700">
                  <div>Mode: <span className="font-medium">{message.searchStats.search_mode}</span></div>
                  {message.searchStats.document_results > 0 && (
                    <div>Documents found: <span className="font-medium">{message.searchStats.document_results}</span></div>
                  )}
                  {message.searchStats.web_results > 0 && (
                    <div>Web results: <span className="font-medium">{message.searchStats.web_results}</span></div>
                  )}
                </div>
              </div>
            )}
            
            {/* Timestamp */}
            <div className={`text-xs mt-2 ${isUser ? 'text-blue-200' : 'text-gray-500'}`}>
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Toaster position="top-right" />
      
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">AI Search Chat</h1>
              <p className="text-sm text-gray-500">
                Status: 
                <span className={`ml-1 ${connectionStatus === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                  {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
                </span>
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Tab Navigation */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  activeTab === 'chat' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <MessageSquare size={14} className="inline mr-1" />
                Chat
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  activeTab === 'documents' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BookOpen size={14} className="inline mr-1" />
                Documents ({documents.length})
              </button>
              <button
                onClick={() => setActiveTab('upload')}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  activeTab === 'upload' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Upload size={14} className="inline mr-1" />
                Upload
              </button>
            </div>
            
            <button
              onClick={clearChat}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
            >
              Clear Chat
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'chat' && (
          <div className="px-4 py-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-4">
                  <MessageSquare className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-semibold mb-2">Welcome to AI Search Chat</h2>
                <p className="text-center max-w-md mb-6">
                  Ask me anything! I can search the web, search your documents, generate images, and remember our conversation.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl">
                  <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <Search className="w-5 h-5 text-blue-500 mr-2" />
                      <span className="font-medium">Web Search</span>
                    </div>
                    <p className="text-sm text-gray-600">Ask about current events, facts, or any topic that needs web research.</p>
                  </div>
                  <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <BookOpen className="w-5 h-5 text-green-500 mr-2" />
                      <span className="font-medium">Document Search</span>
                    </div>
                    <p className="text-sm text-gray-600">Upload PDFs, Word docs, and more. Ask questions about your documents.</p>
                  </div>
                  <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center mb-2">
                      <Image className="w-5 h-5 text-purple-500 mr-2" />
                      <span className="font-medium">Image Generation</span>
                    </div>
                    <p className="text-sm text-gray-600">Generate images by asking "create an image of..." or "draw a picture of..."</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto">
                {messages.map((message) => (
                  <MessageComponent key={message.id} message={message} />
                ))}
                
                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex justify-start mb-4">
                    <div className="flex max-w-[80%]">
                      <div className="mr-3">
                        <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center">
                          <Bot size={16} className="text-white" />
                        </div>
                      </div>
                      <div className="bg-gray-100 text-gray-900 border border-gray-200 rounded-lg px-4 py-2">
                        <div className="flex items-center space-x-2">
                          <Loader className="w-4 h-4 animate-spin" />
                          <span className="text-sm">{statusMessage || 'Thinking...'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="px-4 py-4">
            <DocumentBrowser 
              documents={documents}
              onDelete={handleDocumentDelete}
              onRefresh={loadDocuments}
            />
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="px-4 py-4">
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        )}
      </div>

      {/* Input Area - Only show in chat mode */}
      {activeTab === 'chat' && (
        <div className="bg-white border-t border-gray-200 px-4 py-4">
          <div className="max-w-4xl mx-auto">
            {/* Search Mode Selector */}
            <div className="mb-3">
              <SearchModeSelector 
                searchMode={searchMode}
                onSearchModeChange={setSearchMode}
                documentsAvailable={documents.length > 0}
              />
            </div>
            
            <div className="flex space-x-3">
              <div className="flex-1">
                <textarea
                  ref={inputRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={`Ask me anything... ${
                    searchMode === 'documents' ? 'I\'ll search your documents' :
                    searchMode === 'web' ? 'I\'ll search the web' :
                    searchMode === 'hybrid' ? 'I\'ll search both documents and web' :
                    'I\'ll choose the best search method'
                  }`}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={1}
                  style={{ minHeight: '52px', maxHeight: '120px' }}
                  disabled={isLoading}
                  onInput={(e) => {
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                  }}
                />
              </div>
              <button
                onClick={websocket && connectionStatus === 'connected' ? sendMessage : sendMessageREST}
                disabled={isLoading || !inputMessage.trim()}
                className="px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-2"
              >
                {isLoading ? (
                  <Loader className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
                <span className="hidden sm:inline">Send</span>
              </button>
            </div>
            
            <div className="mt-2 text-xs text-gray-500 flex items-center space-x-4">
              <span>Press Enter to send, Shift+Enter for new line</span>
              {connectionStatus === 'disconnected' && (
                <span className="text-amber-600">Using fallback mode (no real-time updates)</span>
              )}
              {searchStats && (
                <span className="text-blue-600">
                  Last search: {searchStats.search_mode} mode
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
