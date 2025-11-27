import React, { useState, useEffect } from 'react';
import { getDocuments, clearIndex } from '../services/api';
import DocumentList from './DocumentList';
import FileUpload from './FileUpload';

const Sidebar = ({ isOpen, onToggle }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await getDocuments();
      setDocuments(response.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

      const handleUploadSuccess = () => {
        fetchDocuments();
      };

      const handleClearIndex = async () => {
        if (!window.confirm('确定要清空索引库吗？这将删除所有向量数据，但不会删除已上传的文件。此操作不可恢复！')) {
          return;
        }
        
        try {
          setLoading(true);
          const result = await clearIndex();
          alert(`索引库已清空：${result.message}`);
          // Refresh document list
          fetchDocuments();
        } catch (error) {
          alert(`清空索引库失败：${error.message}`);
        } finally {
          setLoading(false);
        }
      };

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed lg:static inset-y-0 left-0 z-50 w-80 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        } flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Documents</h2>
          <button
            onClick={onToggle}
            className="lg:hidden text-gray-500 hover:text-gray-700"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Upload Section */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  Upload Document
                </h3>
                <FileUpload onUploadSuccess={handleUploadSuccess} />
              </div>

              {/* Clear Index Section */}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  Index Management
                </h3>
                <button
                  onClick={handleClearIndex}
                  disabled={loading}
                  className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {loading ? '处理中...' : '清空索引库'}
                </button>
                <p className="text-xs text-gray-500 mt-2">
                  清空所有向量数据，但保留已上传的文件
                </p>
              </div>

              {/* Documents List */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  Loaded Documents ({documents.length})
                </h3>
                {loading ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                  </div>
                ) : (
                  <DocumentList documents={documents} onUpdate={fetchDocuments} />
                )}
              </div>
            </div>
      </div>
    </>
  );
};

export default Sidebar;

