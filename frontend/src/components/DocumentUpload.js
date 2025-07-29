import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { 
  Upload, 
  File, 
  CheckCircle, 
  XCircle, 
  Loader, 
  AlertCircle,
  FileText
} from 'lucide-react';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const DocumentUpload = ({ onUploadSuccess, onUploadError }) => {
  const [uploads, setUploads] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'pdf':
        return <File className="w-6 h-6 text-red-500" />;
      case 'docx':
        return <FileText className="w-6 h-6 text-blue-500" />;
      case 'txt':
      case 'md':
        return <FileText className="w-6 h-6 text-green-500" />;
      default:
        return <File className="w-6 h-6 text-gray-500" />;
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    setIsUploading(true);
    
    for (const file of acceptedFiles) {
      const uploadId = Date.now() + Math.random();
      
      // Add file to uploads list
      setUploads(prev => [...prev, {
        id: uploadId,
        file,
        status: 'uploading',
        progress: 0,
        error: null
      }]);

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_BASE_URL}/upload-pdf`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploads(prev => prev.map(upload => 
              upload.id === uploadId 
                ? { ...upload, progress }
                : upload
            ));
          }
        });

        // Success
        setUploads(prev => prev.map(upload => 
          upload.id === uploadId 
            ? { ...upload, status: 'completed', progress: 100, result: response.data }
            : upload
        ));

        toast.success(`Successfully uploaded: ${file.name}`);
        if (onUploadSuccess) {
          onUploadSuccess(response.data);
        }

      } catch (error) {
        const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';
        
        setUploads(prev => prev.map(upload => 
          upload.id === uploadId 
            ? { ...upload, status: 'error', error: errorMessage }
            : upload
        ));

        toast.error(`Upload failed: ${file.name} - ${errorMessage}`);
        if (onUploadError) {
          onUploadError(error);
        }
      }
    }
    
    setIsUploading(false);
  }, [onUploadSuccess, onUploadError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true
  });

  const clearCompleted = () => {
    setUploads(prev => prev.filter(upload => upload.status !== 'completed'));
  };

  const clearAll = () => {
    setUploads([]);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Documents</h3>
        <p className="text-sm text-gray-600">
          Upload PDF, DOCX, TXT, or Markdown files to add them to your knowledge base.
        </p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
          ${isUploading ? 'pointer-events-none opacity-50' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-3">
          <Upload className={`w-12 h-12 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
          
          {isDragActive ? (
            <p className="text-blue-600 font-medium">Drop files here...</p>
          ) : (
            <>
              <p className="text-gray-600">
                <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
              </p>
              <p className="text-sm text-gray-500">
                PDF, DOCX, TXT, MD files up to 50MB
              </p>
            </>
          )}
        </div>
      </div>

      {/* Upload List */}
      {uploads.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-gray-900">Upload Progress</h4>
            <div className="flex space-x-2">
              <button
                onClick={clearCompleted}
                className="text-sm text-gray-500 hover:text-gray-700"
                disabled={!uploads.some(u => u.status === 'completed')}
              >
                Clear Completed
              </button>
              <button
                onClick={clearAll}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear All
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {uploads.map((upload) => (
              <div key={upload.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                {getFileIcon(upload.file.name.split('.').pop())}
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {upload.file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(upload.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  
                  {upload.status === 'uploading' && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${upload.progress}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{upload.progress}%</p>
                    </div>
                  )}
                  
                  {upload.status === 'error' && (
                    <p className="text-xs text-red-600 mt-1">{upload.error}</p>
                  )}
                  
                  {upload.status === 'completed' && upload.result && (
                    <p className="text-xs text-green-600 mt-1">
                      Processed successfully - {upload.result.message}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0">
                  {upload.status === 'uploading' && (
                    <Loader className="w-5 h-5 text-blue-500 animate-spin" />
                  )}
                  {upload.status === 'completed' && (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}
                  {upload.status === 'error' && (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Guidelines */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <div className="flex items-start space-x-2">
          <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Upload Tips:</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700">
              <li>Documents are automatically processed and indexed for search</li>
              <li>Larger documents are split into chunks for better search results</li>
              <li>Duplicate files (same content) are automatically detected</li>
              <li>Processing may take a few moments for large documents</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentUpload;
