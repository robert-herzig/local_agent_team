# Future RAG Integration Plan

## 📚 Document Processing Pipeline

### 1. File Upload & Management
```python
# backend/rag/document_processor.py
class DocumentProcessor:
    async def process_pdf(self, file: UploadFile):
        # Extract text using PyPDF2 or pdfplumber
        # Split into chunks (1000 chars with 200 overlap)
        # Generate embeddings using sentence-transformers
        # Store in ChromaDB with metadata
        pass
    
    async def process_text(self, file: UploadFile):
        # Similar processing for .txt, .md files
        pass
```

### 2. Vector Database Integration
```python
# backend/rag/vector_store.py
import chromadb
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.create_collection("documents")
    
    async def add_document(self, chunks: List[str], metadata: dict):
        # Generate embeddings and store
        pass
    
    async def search_similar(self, query: str, top_k: int = 5):
        # Vector similarity search
        pass
```

### 3. Hybrid Search Strategy
```python
# backend/rag/hybrid_search.py
class HybridSearchEngine:
    async def search(self, query: str):
        # 1. Check if document knowledge can answer
        doc_results = await self.vector_search(query)
        
        # 2. If insufficient, supplement with web search
        if self.confidence_score(doc_results) < 0.7:
            web_results = await self.web_search(query)
            return self.combine_results(doc_results, web_results)
        
        return doc_results
```

## 🎯 Frontend RAG Components

### 1. Document Upload Component
```jsx
// frontend/src/components/DocumentUpload.js
const DocumentUpload = () => {
    // Drag-and-drop interface
    // Progress tracking
    // File management (list, delete, organize)
    // PDF preview
};
```

### 2. Knowledge Base Browser
```jsx
// frontend/src/components/KnowledgeBase.js
const KnowledgeBase = () => {
    // List uploaded documents
    // Search within documents
    // View document chunks
    // Manage document collections
};
```

### 3. Enhanced Chat with Document Context
```jsx
// Show which documents were used for answers
// Toggle between web-only, docs-only, or hybrid search
// Document citations in responses
```

## 🔧 Implementation Steps

### Phase 1: Core RAG Infrastructure
1. **Document Processing**
   - PDF text extraction
   - Text chunking strategies
   - Metadata extraction (title, author, date)

2. **Vector Database Setup**
   - ChromaDB integration
   - Embedding model selection
   - Collection management

3. **Basic Document Search**
   - Similarity search implementation
   - Result ranking and filtering

### Phase 2: Hybrid Intelligence
1. **Search Decision Engine**
   - When to use documents vs web
   - Confidence scoring
   - Fallback strategies

2. **Result Fusion**
   - Combine document and web results
   - Deduplication and ranking
   - Source attribution

### Phase 3: Advanced Features
1. **Document Management**
   - Collections and tags
   - Version control
   - Sharing and permissions

2. **Advanced Search**
   - Multi-modal search (text + images)
   - Temporal search (time-based filtering)
   - Cross-document reasoning

## 📊 Database Schema for RAG

### Documents Table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    original_name VARCHAR(255),
    file_type VARCHAR(50),
    file_size BIGINT,
    upload_date TIMESTAMP,
    processed_date TIMESTAMP,
    status VARCHAR(50), -- 'processing', 'completed', 'failed'
    metadata JSONB,
    user_id UUID -- for multi-user support
);
```

### Document Chunks Table
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    chunk_index INTEGER,
    content TEXT,
    chunk_metadata JSONB,
    created_at TIMESTAMP
);
```

## 🚀 Migration Strategy

### 1. Gradual Integration
- Add RAG as optional feature
- Existing web search remains default
- Users can enable document search per session

### 2. Backward Compatibility
- All existing endpoints continue working
- New RAG endpoints are additive
- Configuration remains in prompts.json

### 3. Performance Considerations
- Lazy loading of vector database
- Async document processing
- Caching for frequent searches
- Batch operations for large uploads

## 🎛️ Configuration for RAG

### Environment Variables
```env
# Vector Database
CHROMA_HOST=localhost
CHROMA_PORT=8001
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Document Processing
MAX_FILE_SIZE=50MB
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
SUPPORTED_FORMATS=pdf,txt,md,docx

# Hybrid Search
DOC_SEARCH_THRESHOLD=0.7
MAX_DOC_RESULTS=5
HYBRID_WEIGHT_DOCS=0.6
HYBRID_WEIGHT_WEB=0.4
```

### Enhanced Prompts
```json
{
  "document_search_prompt": "Search the uploaded documents for information about: {query}",
  "hybrid_decision_prompt": "Based on the document search results, should we also search the web? Document confidence: {confidence}",
  "document_synthesis_prompt": "Answer using these document excerpts and web sources: {context}",
  "citation_prompt": "Provide citations for document sources in your answer"
}
```

This RAG integration plan maintains the existing architecture while adding powerful document search capabilities. The modular design allows for gradual implementation and easy maintenance.
