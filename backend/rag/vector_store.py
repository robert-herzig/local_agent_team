import os
import asyncio
import uuid
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import json
from datetime import datetime
import logging

# Vector database
import chromadb
from chromadb.config import Settings

# Embeddings
from sentence_transformers import SentenceTransformer

# Database
import sqlite3
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class VectorStore:
    """Manages document embeddings and vector similarity search."""
    
    def __init__(self, 
                 db_path: str = "vector_db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 collection_name: str = "documents"):
        
        self.db_path = db_path
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # Ensure database directory exists
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Found existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            logger.info(f"Creating new collection: {collection_name}")
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Document chunks for RAG"}
            )
        
        # Initialize metadata database
        self.metadata_db_path = os.path.join(db_path, "metadata.db")
        self._init_metadata_db()
    
    def _init_metadata_db(self):
        """Initialize SQLite database for document metadata."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    original_name TEXT,
                    filename TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    file_hash TEXT,
                    upload_date TEXT,
                    processed_date TEXT,
                    status TEXT,
                    metadata TEXT,
                    UNIQUE(file_hash)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT,
                    chunk_index INTEGER,
                    content TEXT,
                    char_count INTEGER,
                    word_count INTEGER,
                    token_count INTEGER,
                    chunk_metadata TEXT,
                    created_at TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id 
                ON document_chunks(document_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_hash 
                ON documents(file_hash)
            """)
    
    async def add_document(self, 
                          file_info: Dict, 
                          chunks: List[Dict], 
                          metadata: Dict) -> str:
        """Add a document and its chunks to the vector store."""
        try:
            document_id = file_info['id']
            
            # Check for duplicate based on file hash
            existing_doc = await self.get_document_by_hash(file_info['file_hash'])
            if existing_doc:
                logger.info(f"Document with hash {file_info['file_hash']} already exists")
                return existing_doc['id']
            
            # Store document metadata
            await self._store_document_metadata(file_info, metadata)
            
            # Process chunks
            chunk_ids = []
            chunk_contents = []
            chunk_metadatas = []
            
            for chunk in chunks:
                chunk_id = f"{document_id}_chunk_{chunk['chunk_index']}"
                chunk_ids.append(chunk_id)
                chunk_contents.append(chunk['content'])
                
                # Prepare chunk metadata for ChromaDB
                chunk_metadata = {
                    'document_id': document_id,
                    'chunk_index': chunk['chunk_index'],
                    'char_count': chunk['char_count'],
                    'word_count': chunk['word_count'],
                    'token_count': chunk['token_count'],
                    'document_title': metadata.get('title', ''),
                    'document_type': file_info['file_type'],
                    'upload_date': file_info['upload_date']
                }
                chunk_metadatas.append(chunk_metadata)
                
                # Store chunk in metadata database
                await self._store_chunk_metadata(chunk_id, document_id, chunk, chunk_metadata)
            
            # Generate embeddings and add to ChromaDB
            if chunk_contents:
                embeddings = self.embedding_model.encode(chunk_contents)
                
                self.collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings.tolist(),
                    documents=chunk_contents,
                    metadatas=chunk_metadatas
                )
            
            # Update document status
            await self._update_document_status(document_id, 'completed')
            
            logger.info(f"Successfully added document {document_id} with {len(chunks)} chunks")
            return document_id
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            await self._update_document_status(document_id, 'failed')
            raise
    
    async def search_similar(self, 
                           query: str, 
                           top_k: int = 5,
                           document_filter: Optional[Dict] = None) -> List[Dict]:
        """Search for similar document chunks."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Prepare where clause for filtering
            where_clause = {}
            if document_filter:
                where_clause.update(document_filter)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'chunk_id': results['ids'][0][i] if 'ids' in results else None
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    async def search_by_document(self, 
                               document_id: str, 
                               query: str, 
                               top_k: int = 5) -> List[Dict]:
        """Search within a specific document."""
        document_filter = {'document_id': document_id}
        return await self.search_similar(query, top_k, document_filter)
    
    async def get_document_chunks(self, document_id: str) -> List[Dict]:
        """Get all chunks for a specific document."""
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM document_chunks 
                    WHERE document_id = ? 
                    ORDER BY chunk_index
                """, (document_id,))
                
                chunks = []
                for row in cursor.fetchall():
                    chunk = dict(row)
                    chunk['chunk_metadata'] = json.loads(chunk['chunk_metadata']) if chunk['chunk_metadata'] else {}
                    chunks.append(chunk)
                
                return chunks
                
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict]:
        """Get document metadata by ID."""
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM documents WHERE id = ?
                """, (document_id,))
                
                row = cursor.fetchone()
                if row:
                    doc = dict(row)
                    doc['metadata'] = json.loads(doc['metadata']) if doc['metadata'] else {}
                    return doc
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return None
    
    async def get_document_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Get document by file hash to prevent duplicates."""
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM documents WHERE file_hash = ?
                """, (file_hash,))
                
                row = cursor.fetchone()
                if row:
                    doc = dict(row)
                    doc['metadata'] = json.loads(doc['metadata']) if doc['metadata'] else {}
                    return doc
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting document by hash: {e}")
            return None
    
    async def list_documents(self, 
                           limit: int = 100, 
                           offset: int = 0,
                           status_filter: Optional[str] = None) -> List[Dict]:
        """List all documents with pagination."""
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM documents"
                params = []
                
                if status_filter:
                    query += " WHERE status = ?"
                    params.append(status_filter)
                
                query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor = conn.execute(query, params)
                
                documents = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    doc['metadata'] = json.loads(doc['metadata']) if doc['metadata'] else {}
                    documents.append(doc)
                
                return documents
                
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        try:
            # Get chunk IDs for this document
            chunks = await self.get_document_chunks(document_id)
            chunk_ids = [chunk['id'] for chunk in chunks]
            
            # Delete from ChromaDB
            if chunk_ids:
                self.collection.delete(ids=chunk_ids)
            
            # Delete from metadata database
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                conn.commit()
            
            logger.info(f"Successfully deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict:
        """Get statistics about the vector collection."""
        try:
            # Get ChromaDB stats
            collection_count = self.collection.count()
            
            # Get database stats
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) as doc_count FROM documents")
                doc_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) as chunk_count FROM document_chunks")
                chunk_count = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM documents 
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'total_documents': doc_count,
                'total_chunks': chunk_count,
                'vector_count': collection_count,
                'status_breakdown': status_counts,
                'embedding_model': self.embedding_model_name
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    async def _store_document_metadata(self, file_info: Dict, metadata: Dict):
        """Store document metadata in SQLite."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO documents 
                (id, original_name, filename, file_type, file_size, file_hash, 
                 upload_date, processed_date, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_info['id'],
                file_info['original_name'],
                file_info['filename'],
                file_info['file_type'],
                file_info['file_size'],
                file_info['file_hash'],
                file_info['upload_date'],
                datetime.now().isoformat(),
                'processing',
                json.dumps(metadata)
            ))
            conn.commit()
    
    async def _store_chunk_metadata(self, chunk_id: str, document_id: str, chunk: Dict, chunk_metadata: Dict):
        """Store chunk metadata in SQLite."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute("""
                INSERT INTO document_chunks 
                (id, document_id, chunk_index, content, char_count, word_count, 
                 token_count, chunk_metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                document_id,
                chunk['chunk_index'],
                chunk['content'],
                chunk['char_count'],
                chunk['word_count'],
                chunk['token_count'],
                json.dumps(chunk_metadata),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    async def _update_document_status(self, document_id: str, status: str):
        """Update document processing status."""
        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute("""
                UPDATE documents 
                SET status = ?, processed_date = ? 
                WHERE id = ?
            """, (status, datetime.now().isoformat(), document_id))
            conn.commit()
    
    async def reset_collection(self):
        """Reset the entire collection (for development/testing)."""
        try:
            # Delete ChromaDB collection
            self.client.delete_collection(self.collection_name)
            
            # Recreate collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Document chunks for RAG"}
            )
            
            # Clear metadata database
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.execute("DELETE FROM document_chunks")
                conn.execute("DELETE FROM documents")
                conn.commit()
            
            logger.info("Successfully reset vector collection")
            
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise
