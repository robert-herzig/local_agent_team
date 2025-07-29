"""
RAG (Retrieval-Augmented Generation) Module

This module provides document processing, vector storage, and hybrid search capabilities
for the AI chat system.

Components:
- DocumentProcessor: Handles file upload, text extraction, and chunking
- VectorStore: Manages embeddings and similarity search using ChromaDB
- HybridSearchEngine: Combines document search with web search
"""

from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .hybrid_search import HybridSearchEngine

__all__ = ['DocumentProcessor', 'VectorStore', 'HybridSearchEngine']

# Version info
__version__ = "1.0.0"
__author__ = "AI Chat Team"
__description__ = "RAG integration for AI chat system"
