import React from 'react';
import { 
  Globe, 
  FileText, 
  Zap, 
  Search,
  Info
} from 'lucide-react';

const SearchModeSelector = ({ searchMode, onSearchModeChange, documentCount = 0 }) => {
  const modes = [
    {
      id: 'auto',
      name: 'Auto',
      icon: Zap,
      description: 'Automatically decide between documents and web search',
      color: 'blue',
      available: true
    },
    {
      id: 'hybrid',
      name: 'Hybrid',
      icon: Search,
      description: 'Search both documents and web, then combine results',
      color: 'purple',
      available: documentCount > 0
    },
    {
      id: 'documents',
      name: 'Documents',
      icon: FileText,
      description: 'Search only in uploaded documents',
      color: 'green',
      available: documentCount > 0
    },
    {
      id: 'web',
      name: 'Web',
      icon: Globe,
      description: 'Search only on the web',
      color: 'orange',
      available: true
    }
  ];

  const getColorClasses = (color, isSelected, isAvailable) => {
    if (!isAvailable) {
      return 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed';
    }
    
    if (isSelected) {
      const selectedColors = {
        blue: 'bg-blue-500 text-white border-blue-500',
        purple: 'bg-purple-500 text-white border-purple-500',
        green: 'bg-green-500 text-white border-green-500',
        orange: 'bg-orange-500 text-white border-orange-500'
      };
      return selectedColors[color];
    }
    
    const hoverColors = {
      blue: 'bg-white hover:bg-blue-50 text-blue-700 border-blue-200 hover:border-blue-300',
      purple: 'bg-white hover:bg-purple-50 text-purple-700 border-purple-200 hover:border-purple-300',
      green: 'bg-white hover:bg-green-50 text-green-700 border-green-200 hover:border-green-300',
      orange: 'bg-white hover:bg-orange-50 text-orange-700 border-orange-200 hover:border-orange-300'
    };
    return hoverColors[color];
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center space-x-2 mb-3">
        <Search className="w-5 h-5 text-gray-600" />
        <h3 className="font-medium text-gray-900">Search Mode</h3>
        {documentCount > 0 && (
          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
            {documentCount} documents
          </span>
        )}
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isSelected = searchMode === mode.id;
          const isAvailable = mode.available;
          
          return (
            <button
              key={mode.id}
              onClick={() => isAvailable && onSearchModeChange(mode.id)}
              disabled={!isAvailable}
              className={`
                relative p-3 rounded-lg border-2 transition-all duration-200 text-left
                ${getColorClasses(mode.color, isSelected, isAvailable)}
              `}
              title={mode.description}
            >
              <div className="flex flex-col items-center space-y-1">
                <Icon className="w-5 h-5" />
                <span className="text-sm font-medium">{mode.name}</span>
              </div>
              
              {!isAvailable && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 rounded-lg">
                  <span className="text-xs text-gray-500">No docs</span>
                </div>
              )}
            </button>
          );
        })}
      </div>
      
      {/* Mode Description */}
      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-start space-x-2">
          <Info className="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-gray-600">
            <p className="font-medium mb-1">
              {modes.find(m => m.id === searchMode)?.name} Mode:
            </p>
            <p>{modes.find(m => m.id === searchMode)?.description}</p>
          </div>
        </div>
      </div>
      
      {/* Document Count Info */}
      {documentCount === 0 && (
        <div className="mt-3 p-3 bg-blue-50 rounded-lg">
          <div className="flex items-start space-x-2">
            <FileText className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">No Documents Uploaded</p>
              <p>Upload documents to enable document and hybrid search modes.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchModeSelector;
