import asyncio
from typing import List, Dict, Optional, Tuple, Any
import logging
from datetime import datetime

# Local imports
from .vector_store import VectorStore
from .document_processor import DocumentProcessor

# We'll implement web search functionality directly here instead of importing from main

logger = logging.getLogger(__name__)

class HybridSearchEngine:
    """Combines document search with web search for comprehensive results."""
    
    def __init__(self, 
                 vector_store: VectorStore,
                 doc_search_threshold: float = 0.5,  # Lowered from 0.7 for stricter filtering
                 max_doc_results: int = 5,
                 max_web_results: int = 3,
                 hybrid_weight_docs: float = 0.4,    # Reduced document weight
                 hybrid_weight_web: float = 0.6):    # Increased web weight
        
        self.vector_store = vector_store
        self.doc_search_threshold = doc_search_threshold
        self.max_doc_results = max_doc_results
        self.max_web_results = max_web_results
        self.hybrid_weight_docs = hybrid_weight_docs
        self.hybrid_weight_web = hybrid_weight_web
        
        # Initialize web search component (from existing system)
        self.web_searcher = None
        
        logger.info("Initialized HybridSearchEngine")
    
    def set_web_searcher(self, web_searcher: Any):
        """Set the web search component."""
        self.web_searcher = web_searcher
    
    async def search(self, 
                    query: str, 
                    search_mode: str = "hybrid",
                    document_filter: Optional[Dict] = None) -> Dict:
        """
        Main search function that combines document and web search.
        
        search_mode options:
        - "hybrid": Use both document and web search
        - "documents": Use only document search
        - "web": Use only web search
        - "auto": Automatically decide based on document confidence
        """
        
        results = {
            'query': query,
            'search_mode': search_mode,
            'timestamp': datetime.now().isoformat(),
            'document_results': [],
            'web_results': [],
            'combined_context': '',
            'confidence_scores': {},
            'sources': []
        }
        
        try:
            if search_mode in ["hybrid", "documents", "auto"]:
                # Search documents first
                doc_results = await self._search_documents(query, document_filter)
                results['document_results'] = doc_results
                
                # Calculate document confidence
                doc_confidence = self._calculate_document_confidence(doc_results)
                results['confidence_scores']['document_confidence'] = doc_confidence
                
                # Decide if web search is needed
                need_web_search = self._should_search_web(search_mode, doc_confidence, doc_results)
                
            else:
                need_web_search = True
                doc_confidence = 0.0
                results['confidence_scores']['document_confidence'] = 0.0
            
            # Perform web search if needed
            if need_web_search and search_mode != "documents":
                if self.web_searcher:
                    web_results = await self._search_web(query)
                    results['web_results'] = web_results
                    results['confidence_scores']['web_confidence'] = 0.8  # Assume decent web confidence
                else:
                    logger.warning("Web searcher not available")
            
            # Combine and rank results
            combined_context = await self._combine_results(
                results['document_results'], 
                results['web_results']
            )
            results['combined_context'] = combined_context
            
            # Generate source list
            results['sources'] = self._generate_source_list(
                results['document_results'], 
                results['web_results']
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            results['error'] = str(e)
            return results
    
    async def _search_documents(self, query: str, document_filter: Optional[Dict] = None) -> List[Dict]:
        """Search in document vector store."""
        try:
            results = await self.vector_store.search_similar(
                query=query,
                top_k=self.max_doc_results,
                document_filter=document_filter
            )
            
            # Enhance results with document metadata
            enhanced_results = []
            for result in results:
                doc_id = result['metadata'].get('document_id')
                if doc_id:
                    doc_metadata = await self.vector_store.get_document_metadata(doc_id)
                    if doc_metadata:
                        result['document_info'] = {
                            'title': doc_metadata.get('metadata', {}).get('title', 'Unknown'),
                            'filename': doc_metadata.get('original_name', 'Unknown'),
                            'file_type': doc_metadata.get('file_type', 'Unknown'),
                            'upload_date': doc_metadata.get('upload_date', 'Unknown')
                        }
                
                enhanced_results.append(result)
            
            logger.info(f"Found {len(enhanced_results)} document results for query: {query}")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def _search_web(self, query: str) -> List[Dict]:
        """Search the web using existing web search functionality."""
        try:
            if not self.web_searcher:
                return []
            
            # Generate search queries
            search_queries = await self.web_searcher.async_generate_search_queries(query)
            
            # Perform web search
            all_results = []
            for search_query in search_queries[:2]:  # Limit to 2 queries for performance
                results = await self.web_searcher.async_search_web(search_query)
                all_results.extend(results)
            
            # Remove duplicates and limit results
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result['url'] not in seen_urls and len(unique_results) < self.max_web_results:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            
            # Extract content from top results
            enhanced_results = []
            for result in unique_results:
                try:
                    content = self.web_searcher.extract_content(result['url'])
                    enhanced_results.append({
                        'title': result['title'],
                        'url': result['url'],
                        'content': content[:1000] + "..." if len(content) > 1000 else content,
                        'full_content': content,
                        'source_type': 'web'
                    })
                except Exception as e:
                    logger.warning(f"Failed to extract content from {result['url']}: {e}")
            
            logger.info(f"Found {len(enhanced_results)} web results for query: {query}")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return []
    
    def _calculate_document_confidence(self, doc_results: List[Dict]) -> float:
        """Calculate confidence score for document search results."""
        if not doc_results:
            return 0.0
        
        # Base confidence on similarity scores and number of results
        similarity_scores = [result.get('similarity_score', 0) for result in doc_results]
        
        if not similarity_scores:
            return 0.0
        
        # Calculate weighted confidence with stricter thresholds
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        max_similarity = max(similarity_scores)
        
        # Only count high-confidence results (similarity > 0.5)
        high_confidence_count = sum(1 for score in similarity_scores if score > 0.5)
        result_quality_factor = high_confidence_count / len(similarity_scores)
        
        # More stringent confidence calculation
        # Require both good similarity AND multiple relevant results
        base_confidence = avg_similarity * 0.6 + max_similarity * 0.4
        quality_penalty = result_quality_factor
        
        final_confidence = base_confidence * quality_penalty
        
        # Additional penalty for very low similarities
        if max_similarity < 0.3:
            final_confidence *= 0.3
        elif max_similarity < 0.5:
            final_confidence *= 0.6
        
        return min(final_confidence, 1.0)
    
    def _should_search_web(self, search_mode: str, doc_confidence: float, doc_results: List[Dict]) -> bool:
        """Decide whether to perform web search based on document results."""
        if search_mode == "web":
            return True
        elif search_mode == "documents":
            return False
        elif search_mode == "hybrid":
            # In hybrid mode, always search web but filter document results better
            return True
        elif search_mode == "auto":
            # Auto mode: search web if document confidence is low OR results are irrelevant
            has_relevant_docs = any(
                result.get('similarity_score', 0) > 0.5 
                for result in doc_results
            )
            return doc_confidence < self.doc_search_threshold or not has_relevant_docs
        
        return True
    
    async def _combine_results(self, doc_results: List[Dict], web_results: List[Dict]) -> str:
        """Combine document and web results into a unified context, filtering irrelevant docs."""
        context_parts = []
        
        # Filter document results by relevance threshold
        relevant_doc_results = [
            result for result in doc_results 
            if result.get('similarity_score', 0) > 0.4  # Only include docs with >40% similarity
        ]
        
        # Add document results only if they're relevant
        if relevant_doc_results:
            context_parts.append("=== DOCUMENT SOURCES ===")
            for i, result in enumerate(relevant_doc_results, 1):
                doc_info = result.get('document_info', {})
                title = doc_info.get('title', 'Unknown Document')
                
                context_parts.append(f"\n--- Document {i}: {title} ---")
                context_parts.append(f"Content: {result['content']}")
                context_parts.append(f"Relevance Score: {result.get('similarity_score', 0):.3f}")
        
        # Add web results
        if web_results:
            context_parts.append("\n\n=== WEB SOURCES ===")
            for i, result in enumerate(web_results, 1):
                context_parts.append(f"\n--- Web Source {i}: {result['title']} ---")
                context_parts.append(f"URL: {result['url']}")
                context_parts.append(f"Content: {result['content']}")
        
        return "\n".join(context_parts)
    
    def _generate_source_list(self, doc_results: List[Dict], web_results: List[Dict]) -> List[Dict]:
        """Generate a list of sources for citation, filtering irrelevant docs."""
        sources = []
        
        # Filter and add document sources (only relevant ones)
        relevant_doc_results = [
            result for result in doc_results 
            if result.get('similarity_score', 0) > 0.4  # Only include docs with >40% similarity
        ]
        
        for result in relevant_doc_results:
            doc_info = result.get('document_info', {})
            sources.append({
                'type': 'document',
                'title': f"{doc_info.get('title', 'Unknown Document')} (Chunk {result['metadata'].get('chunk_index', 0)})",
                'url': f"document://{doc_info.get('filename', 'Unknown')}",
                'similarity_score': result.get('similarity_score', 0),
                'filename': doc_info.get('filename', 'Unknown'),
                'file_type': doc_info.get('file_type', 'Unknown')
            })
        
        # Add web sources
        for result in web_results:
            sources.append({
                'type': 'web',
                'title': result['title'],
                'url': result['url']
            })
        
        return sources
    
    async def search_specific_document(self, document_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """Search within a specific document."""
        try:
            return await self.vector_store.search_by_document(document_id, query, top_k)
        except Exception as e:
            logger.error(f"Error searching specific document: {e}")
            return []
    
    async def get_document_context(self, document_id: str, max_chunks: int = 10) -> str:
        """Get context from a specific document."""
        try:
            chunks = await self.vector_store.get_document_chunks(document_id)
            
            if not chunks:
                return ""
            
            # Sort by chunk index and take first N chunks
            sorted_chunks = sorted(chunks, key=lambda x: x['chunk_index'])[:max_chunks]
            
            context_parts = []
            for chunk in sorted_chunks:
                context_parts.append(f"Chunk {chunk['chunk_index']}: {chunk['content']}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting document context: {e}")
            return ""
    
    async def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on document content."""
        try:
            # Simple implementation: search for partial query and extract related terms
            results = await self.vector_store.search_similar(partial_query, top_k=3)
            
            suggestions = set()
            for result in results:
                content = result['content'].lower()
                words = content.split()
                
                # Find words near the query terms
                query_words = partial_query.lower().split()
                for query_word in query_words:
                    if query_word in content:
                        word_index = words.index(query_word)
                        # Get surrounding words
                        start = max(0, word_index - 2)
                        end = min(len(words), word_index + 3)
                        nearby_words = words[start:end]
                        
                        # Create suggestions
                        for i in range(len(nearby_words) - 1):
                            suggestion = " ".join(nearby_words[i:i+2])
                            if len(suggestion) > len(partial_query):
                                suggestions.add(suggestion)
            
            return list(suggestions)[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    async def get_stats(self) -> Dict:
        """Get hybrid search engine statistics."""
        try:
            vector_stats = await self.vector_store.get_collection_stats()
            
            return {
                'vector_store_stats': vector_stats,
                'search_config': {
                    'doc_search_threshold': self.doc_search_threshold,
                    'max_doc_results': self.max_doc_results,
                    'max_web_results': self.max_web_results,
                    'hybrid_weight_docs': self.hybrid_weight_docs,
                    'hybrid_weight_web': self.hybrid_weight_web
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
