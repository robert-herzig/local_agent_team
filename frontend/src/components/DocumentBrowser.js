import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, 
  File, 
  Search, 
  Trash2, 
  Eye, 
  Calendar,
  Download,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const DocumentBrowser = ({ onDocumentSelect, selectedDocumentId }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, [statusFilter]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('limit', '100');
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await axios.get(`${API_BASE_URL}/documents?${params}`);
      setDocuments(response.data);
    } catch (error) {
      if (error.response?.status === 501) {
        toast.error('RAG functionality not available. Please install RAG dependencies.');
      } else {
        toast.error('Failed to load documents');
      }
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (documentId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/documents/${documentId}`);
      toast.success(`Deleted: ${filename}`);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      
      if (selectedDocumentId === documentId && onDocumentSelect) {
        onDocumentSelect(null);
      }
    } catch (error) {
      toast.error('Failed to delete document');
      console.error('Error deleting document:', error);
    }
  };

  const viewDocumentDetails = async (document) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/documents/${document.id}`);
      setSelectedDoc({
        ...document,
        details: response.data
      });
      setShowDetails(true);
    } catch (error) {
      toast.error('Failed to load document details');
      console.error('Error loading document details:', error);
    }
  };

  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'pdf':
        return <File className="w-5 h-5 text-red-500" />;
      case 'docx':
        return <FileText className="w-5 h-5 text-blue-500" />;
      case 'txt':
      case 'md':
        return <FileText className="w-5 h-5 text-green-500" />;
      default:
        return <FileText className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredDocuments = documents.filter(doc =>
    doc.original_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.metadata.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.metadata.keywords?.some(keyword => 
      keyword.toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin mr-2" />
          <span className="text-gray-600">Loading documents...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Document Library</h3>
          <button
            onClick={loadDocuments}
            className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>

        {/* Search and Filter */}
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div className="relative">
            <Filter className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Document List */}
      <div className="max-h-96 overflow-y-auto">
        {filteredDocuments.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {documents.length === 0 ? (
              <div className="space-y-2">
                <FileText className="w-12 h-12 text-gray-300 mx-auto" />
                <p>No documents uploaded yet</p>
                <p className="text-sm">Upload documents to get started with RAG search</p>
              </div>
            ) : (
              <div className="space-y-2">
                <Search className="w-12 h-12 text-gray-300 mx-auto" />
                <p>No documents match your search</p>
                <p className="text-sm">Try adjusting your search terms or filter</p>
              </div>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredDocuments.map((document) => (
              <div
                key={document.id}
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  selectedDocumentId === document.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                }`}
                onClick={() => onDocumentSelect && onDocumentSelect(document.id)}
              >
                <div className="flex items-start space-x-3">
                  {getFileIcon(document.file_type)}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {document.original_name}
                      </p>
                      {getStatusIcon(document.status)}
                    </div>
                    
                    {document.metadata.title && document.metadata.title !== document.original_name && (
                      <p className="text-xs text-gray-600 truncate mt-1">
                        {document.metadata.title}
                      </p>
                    )}
                    
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>{formatFileSize(document.file_size)}</span>
                      <span className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3" />
                        <span>{formatDate(document.upload_date)}</span>
                      </span>
                      {document.metadata.total_chunks && (
                        <span>{document.metadata.total_chunks} chunks</span>
                      )}
                    </div>
                    
                    {document.metadata.keywords && document.metadata.keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {document.metadata.keywords.slice(0, 3).map((keyword, index) => (
                          <span
                            key={index}
                            className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                          >
                            {keyword}
                          </span>
                        ))}
                        {document.metadata.keywords.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{document.metadata.keywords.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        viewDocumentDetails(document);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="View details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteDocument(document.id, document.original_name);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document Details Modal */}
      {showDetails && selectedDoc && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden mx-4">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">
                  {selectedDoc.original_name}
                </h2>
                <button
                  onClick={() => setShowDetails(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Document Info</h3>
                  <dl className="space-y-2 text-sm">
                    <div>
                      <dt className="text-gray-500">File Type:</dt>
                      <dd className="text-gray-900">{selectedDoc.file_type.toUpperCase()}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Size:</dt>
                      <dd className="text-gray-900">{formatFileSize(selectedDoc.file_size)}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Status:</dt>
                      <dd className="text-gray-900 flex items-center space-x-1">
                        {getStatusIcon(selectedDoc.status)}
                        <span className="capitalize">{selectedDoc.status}</span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Uploaded:</dt>
                      <dd className="text-gray-900">{formatDate(selectedDoc.upload_date)}</dd>
                    </div>
                  </dl>
                </div>
                
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Content Analysis</h3>
                  <dl className="space-y-2 text-sm">
                    <div>
                      <dt className="text-gray-500">Title:</dt>
                      <dd className="text-gray-900">{selectedDoc.metadata.title || 'N/A'}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Language:</dt>
                      <dd className="text-gray-900">{selectedDoc.metadata.language || 'Unknown'}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Chunks:</dt>
                      <dd className="text-gray-900">{selectedDoc.details?.chunk_count || 0}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Words:</dt>
                      <dd className="text-gray-900">{selectedDoc.metadata.total_words || 'N/A'}</dd>
                    </div>
                  </dl>
                </div>
              </div>
              
              {selectedDoc.metadata.summary && (
                <div className="mt-6">
                  <h3 className="font-medium text-gray-900 mb-3">Summary</h3>
                  <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
                    {selectedDoc.metadata.summary}
                  </p>
                </div>
              )}
              
              {selectedDoc.metadata.keywords && selectedDoc.metadata.keywords.length > 0 && (
                <div className="mt-6">
                  <h3 className="font-medium text-gray-900 mb-3">Keywords</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedDoc.metadata.keywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="inline-block px-3 py-1 text-sm bg-blue-100 text-blue-800 rounded-full"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentBrowser;
