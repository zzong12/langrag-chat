import React from 'react';
import { deleteDocument, reloadDocument } from '../services/api';

const DocumentList = ({ documents, onUpdate }) => {
  const handleDelete = async (documentId) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await deleteDocument(documentId);
        onUpdate();
      } catch (error) {
        alert(`Error deleting document: ${error.message}`);
      }
    }
  };

  const handleReload = async (documentId) => {
    try {
      await reloadDocument(documentId);
      alert('Document reloaded successfully!');
      onUpdate();
    } catch (error) {
      alert(`Error reloading document: ${error.message}`);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-2">
      {documents.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">
          No documents uploaded yet.
        </p>
      ) : (
        documents.map((doc) => (
          <div
            key={doc.id}
            className="bg-white rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-sm text-gray-800 truncate">
                  {doc.filename}
                </h4>
                <div className="mt-1 text-xs text-gray-500 space-y-1">
                  <p>Type: {doc.file_type.toUpperCase()}</p>
                  <p>Size: {formatFileSize(doc.file_size)}</p>
                  <p>Chunks: {doc.chunks_count}</p>
                  <p>Uploaded: {formatDate(doc.upload_date)}</p>
                </div>
              </div>
              <div className="flex space-x-1 ml-2">
                <button
                  onClick={() => handleReload(doc.id)}
                  className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                  title="Reload document"
                >
                  ↻
                </button>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                  title="Delete document"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default DocumentList;

