import os
import uuid
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib
import mimetypes

# PDF processing
import PyPDF2
import pdfplumber
from io import BytesIO

# Text processing
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter

# FastAPI
from fastapi import UploadFile, HTTPException

# Embeddings
from sentence_transformers import SentenceTransformer

# Database
import sqlite3
import json

class DocumentProcessor:
    """Handles document upload, processing, and text extraction."""
    
    def __init__(self, upload_dir: str = "uploads", chunk_size: int = 1000, chunk_overlap: int = 200):
        self.upload_dir = upload_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Supported file types
        self.supported_types = {
            'application/pdf': 'pdf',
            'text/plain': 'txt',
            'text/markdown': 'md',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
        }
    
    async def process_file(self, file: UploadFile) -> Dict:
        """Main entry point for file processing."""
        try:
            # Validate file
            await self._validate_file(file)
            
            # Save file
            file_info = await self._save_file(file)
            
            # Extract text
            text_content = await self._extract_text(file_info)
            
            # Split into chunks
            chunks = await self._split_text(text_content)
            
            # Generate metadata
            metadata = await self._generate_metadata(file_info, text_content, chunks)
            
            return {
                'file_info': file_info,
                'chunks': chunks,
                'metadata': metadata,
                'status': 'completed'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    async def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = 0
        
        # Read file to check size
        content = await file.read()
        file_size = len(content)
        
        # Reset file pointer
        await file.seek(0)
        
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
        
        # Check file type
        content_type = file.content_type
        if content_type not in self.supported_types:
            raise HTTPException(
                status_code=415, 
                detail=f"Unsupported file type. Supported types: {list(self.supported_types.values())}"
            )
    
    async def _save_file(self, file: UploadFile) -> Dict:
        """Save uploaded file and return file info."""
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = self.supported_types.get(file.content_type, 'txt')
        filename = f"{file_id}.{file_extension}"
        filepath = os.path.join(self.upload_dir, filename)
        
        # Save file
        content = await file.read()
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Generate file hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()
        
        return {
            'id': file_id,
            'original_name': file.filename,
            'filename': filename,
            'filepath': filepath,
            'file_type': file_extension,
            'content_type': file.content_type,
            'file_size': len(content),
            'file_hash': file_hash,
            'upload_date': datetime.now().isoformat()
        }
    
    async def _extract_text(self, file_info: Dict) -> str:
        """Extract text content from file based on type."""
        filepath = file_info['filepath']
        file_type = file_info['file_type']
        
        if file_type == 'pdf':
            return await self._extract_pdf_text(filepath)
        elif file_type in ['txt', 'md']:
            return await self._extract_text_file(filepath)
        elif file_type == 'docx':
            return await self._extract_docx_text(filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def _extract_pdf_text(self, filepath: str) -> str:
        """Extract text from PDF using multiple methods for reliability."""
        text_content = ""
        
        # Method 1: Try pdfplumber (better for complex layouts)
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
            
            if text_content.strip():
                return text_content.strip()
        except Exception as e:
            print(f"pdfplumber failed: {e}")
        
        # Method 2: Fallback to PyPDF2
        try:
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
            
            return text_content.strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}")
    
    async def _extract_text_file(self, filepath: str) -> str:
        """Extract text from plain text or markdown files."""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(filepath, 'r', encoding='latin-1') as file:
                return file.read()
    
    async def _extract_docx_text(self, filepath: str) -> str:
        """Extract text from DOCX files."""
        try:
            from docx import Document
            doc = Document(filepath)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            return '\n\n'.join(text_content)
        except ImportError:
            raise ValueError("python-docx not installed. Cannot process DOCX files.")
        except Exception as e:
            raise ValueError(f"Failed to extract text from DOCX: {e}")
    
    async def _split_text(self, text: str) -> List[Dict]:
        """Split text into chunks with metadata."""
        if not text.strip():
            return []
        
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Create chunk objects with metadata
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk_objects.append({
                'chunk_index': i,
                'content': chunk_text,
                'char_count': len(chunk_text),
                'word_count': len(chunk_text.split()),
                'token_count': self._estimate_tokens(chunk_text)
            })
        
        return chunk_objects
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        try:
            # Use tiktoken for accurate token counting
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            # Fallback: rough estimation
            return len(text) // 4
    
    async def _generate_metadata(self, file_info: Dict, text_content: str, chunks: List[Dict]) -> Dict:
        """Generate comprehensive metadata for the document."""
        return {
            'title': self._extract_title(file_info['original_name'], text_content),
            'author': self._extract_author(text_content),
            'language': self._detect_language(text_content),
            'total_chars': len(text_content),
            'total_words': len(text_content.split()),
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk['char_count'] for chunk in chunks) / len(chunks) if chunks else 0,
            'keywords': self._extract_keywords(text_content),
            'summary': self._generate_summary(text_content)
        }
    
    def _extract_title(self, filename: str, text: str) -> str:
        """Extract or generate document title."""
        # Remove file extension
        title = os.path.splitext(filename)[0]
        
        # Try to find a better title in the first few lines
        lines = text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if line and len(line) < 100 and not line.startswith(('http', 'www')):
                # Look for title-like patterns
                if any(char in line for char in [':', '-', '|']) or line.isupper():
                    title = line
                    break
        
        return title
    
    def _extract_author(self, text: str) -> Optional[str]:
        """Try to extract author information."""
        # Look for common author patterns in first 1000 characters
        search_text = text[:1000].lower()
        
        patterns = [
            'author:', 'by ', 'written by', 'created by', 'authored by'
        ]
        
        for pattern in patterns:
            if pattern in search_text:
                # Extract text after pattern
                start = search_text.find(pattern) + len(pattern)
                end = search_text.find('\n', start)
                if end == -1:
                    end = start + 100
                
                author = text[start:end].strip()
                if author and len(author) < 50:
                    return author
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        # Very basic detection - in production, use a proper language detection library
        sample = text[:1000].lower()
        
        english_indicators = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that']
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'in', 'zu', 'von']
        
        english_score = sum(1 for word in english_indicators if word in sample)
        german_score = sum(1 for word in german_indicators if word in sample)
        
        if german_score > english_score:
            return 'de'
        return 'en'
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - in production, use TF-IDF or similar
        import re
        from collections import Counter
        
        # Clean text and extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with', 'for', 'as', 'was', 'on', 'are', 'you'
        }
        
        words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count and return most common
        word_counts = Counter(words)
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a simple summary of the text."""
        # Simple extractive summary - first paragraph or first N characters
        paragraphs = text.split('\n\n')
        
        # Try to find a good first paragraph
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) > 50 and len(paragraph) < 500:
                return paragraph[:max_length] + "..." if len(paragraph) > max_length else paragraph
        
        # Fallback to first N characters
        summary = text[:max_length].strip()
        return summary + "..." if len(text) > max_length else summary
    
    async def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file information by ID."""
        # This would typically query a database
        filepath = os.path.join(self.upload_dir, f"{file_id}.pdf")  # Simplified
        if os.path.exists(filepath):
            stat = os.stat(filepath)
            return {
                'id': file_id,
                'filepath': filepath,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file and its associated data."""
        try:
            # Find and delete file
            for ext in ['pdf', 'txt', 'md', 'docx']:
                filepath = os.path.join(self.upload_dir, f"{file_id}.{ext}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                    return True
            return False
        except Exception:
            return False
