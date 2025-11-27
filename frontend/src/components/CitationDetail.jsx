import React from 'react';

const CitationDetail = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-800">引用详情</h3>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded hover:bg-gray-100"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {/* File Info */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-1 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              来源文件
            </h4>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 shadow-sm">
              <p className="text-sm font-medium text-blue-900 break-words">{citation.filename}</p>
            </div>
          </div>

          {/* Original Text */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
              <svg className="w-4 h-4 mr-1 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              原文内容
            </h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 shadow-sm">
              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                {citation.content || citation.preview || '暂无内容'}
              </p>
            </div>
          </div>

          {/* Document ID */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">文档ID</h4>
            <p className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded break-all">{citation.document_id}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CitationDetail;

