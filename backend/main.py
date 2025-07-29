from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import json
import asyncio
import os
import uuid
from typing import List, Optional
import ollama
import requests
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import time
import random
from datetime import datetime
import base64

# Import RAG components
RAG_AVAILABLE = False
try:
    from rag import DocumentProcessor, VectorStore, HybridSearchEngine
    RAG_AVAILABLE = True
    print("✓ RAG components imported successfully")
except ImportError as e:
    print(f"RAG components not available: {e}")
    RAG_AVAILABLE = False

# We'll create a web-compatible version of the chat system
class WebSearchEnhancedChat:
    def __init__(self):
        # Model configuration
        self.search_query_model = "gemma3"
        self.source_selection_model = "llama3.2:1b"
        self.main_model = "gemma3"
        
        # Conversation memory
        self.conversation_history = {}  # Store by session_id
        self.max_history_length = 10
        
        # Load prompts from configuration file
        self.prompts = self.load_prompts()
        
        # Initialize RAG if available
        if RAG_AVAILABLE:
            try:
                # self.document_processor = DocumentProcessor()
                # self.vector_store = VectorStore()
                # self.hybrid_search = HybridSearchEngine(self.vector_store)
                print("✓ RAG components initialized successfully")
            except Exception as e:
                print(f"Failed to initialize RAG components: {e}")
                # Note: Can't modify global RAG_AVAILABLE from here
    
    def load_prompts(self):
        """Load prompts from the prompts.json configuration file."""
        try:
            prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts.json')
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            print("✓ Loaded prompts from prompts.json")
            return prompts
        except FileNotFoundError:
            print("Error: prompts.json file not found. Using default prompts.")
            return self.get_default_prompts()
        except json.JSONDecodeError as e:
            print(f"Error parsing prompts.json: {e}. Using default prompts.")
            return self.get_default_prompts()
        except Exception as e:
            print(f"Error loading prompts: {e}. Using default prompts.")
            return self.get_default_prompts()
    
    def get_default_prompts(self):
        """Return default prompts if configuration file is not available."""
        return {
            "search_query_prompt": "Convert this question into search queries. If there is previous conversation context, use it to understand references and create better search terms. Respond with ONLY the search terms, one per line. No explanations, no numbering, no introductory text.\n\nQuestion: {question}\n\nSearch queries:",
            
            "source_selection_prompt": "You are a source evaluator. Your task is to select the 2 most relevant and reliable sources from search results.\n\nUser question: {question}\n\nSearch results:\n{sources}\n\nSelect exactly 2 sources by providing their numbers. Return only the numbers, one per line.",
            
            "knowledge_assessment_prompt": "You are assessing whether you can provide a good answer to this question using only your built-in knowledge and any conversation context provided.\n\nQuestion and context: {question}\n\nCan you provide a comprehensive, accurate answer to this question without needing to search for current information online?\n\nRespond with ONLY:\n- \"YES\" if you can answer well without search\n- \"NO\" if you need to search for information\n\nResponse:",
            
            "knowledge_based_prompt": "You are a knowledgeable assistant answering based on your built-in knowledge and conversation history.\n\n{question}\n\nInstructions:\n- Use your built-in knowledge to provide a comprehensive answer\n- Be accurate and acknowledge if there are aspects you're uncertain about\n\nAnswer:",
            
            "final_answer_prompt": "You are a knowledgeable assistant providing comprehensive answers based on web-sourced information and conversation history.\n\nUser question: {question}\n\nContext from selected sources and previous conversation:\n{context}\n\nInstructions:\n- Use both the web sources and conversation history to provide a complete answer\n- Provide a thorough, accurate answer based on the provided context\n- Be objective and factual\n\nAnswer:",
            
            "conversation_prompt": "You are a knowledgeable assistant continuing a conversation. Answer the question based on our previous conversation history.\n\nUser question: {question}\n\nInstructions:\n- Use the conversation history to understand references and context\n- Provide a clear, helpful answer based on our conversation\n\nAnswer:",
            
            "image_prompt_extraction": "Extract and improve the image description from this user request. Make it a clear, detailed prompt suitable for image generation.\n\nUser request: {question}\n\nImage description:"
        }

app = FastAPI(title="AI Chat Web Interface", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (generated images)
images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_images")
if not os.path.exists(images_dir):
    os.makedirs(images_dir)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

# Models for API requests/responses
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    image_path: Optional[str] = None
    search_queries: Optional[List[str]] = None
    sources: Optional[List[dict]] = None

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

class DocumentInfo(BaseModel):
    id: str
    original_name: str
    file_type: str
    file_size: int
    upload_date: str
    status: str
    metadata: dict

class SearchRequest(BaseModel):
    query: str
    search_mode: str = "hybrid"  # "hybrid", "documents", "web", "auto"
    document_filter: Optional[dict] = None
    session_id: Optional[str] = None

# Session management
chat_sessions = {}

# RAG components (initialized if available)
if RAG_AVAILABLE:
    try:
        print("Initializing RAG components...")
        document_processor = DocumentProcessor()
        print("✓ DocumentProcessor initialized")
        
        vector_store = VectorStore()
        print("✓ VectorStore initialized")
        
        hybrid_search = HybridSearchEngine(vector_store)
        print("✓ HybridSearchEngine initialized")
        
        print("✓ Global RAG components initialized")
    except Exception as e:
        print(f"Failed to initialize RAG components: {e}")
        import traceback
        traceback.print_exc()
        RAG_AVAILABLE = False
        document_processor = None
        vector_store = None
        hybrid_search = None
else:
    document_processor = None
    vector_store = None
    hybrid_search = None

class WebSearchEnhancedChat:
    """Extended version for web interface with async support"""
    
    def __init__(self, session_id: str):
        # Initialize like the original WebSearchEnhancedChat
        self.search_query_model = "gemma3"
        self.source_selection_model = "llama3.2:1b"
        self.main_model = "gemma3"
        self.conversation_history = {}
        self.max_history_length = 10
        self.prompts = self.load_prompts()
        
        # Web interface specific
        self.session_id = session_id
        self.websocket = None
        self.use_rag = RAG_AVAILABLE
        
        # Set up hybrid search if available
        if self.use_rag and hybrid_search:
            hybrid_search.set_web_searcher(self)
    
    def load_prompts(self):
        """Load prompts from the prompts.json configuration file."""
        try:
            prompts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts.json')
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            print("✓ Loaded prompts from prompts.json")
            return prompts
        except FileNotFoundError:
            print("Error: prompts.json file not found. Using default prompts.")
            return self.get_default_prompts()
        except json.JSONDecodeError as e:
            print(f"Error parsing prompts.json: {e}. Using default prompts.")
            return self.get_default_prompts()
        except Exception as e:
            print(f"Error loading prompts: {e}. Using default prompts.")
            return self.get_default_prompts()
    
    def get_default_prompts(self):
        """Return default prompts if configuration file is not available."""
        return {
            "search_query": "Given this user message, generate 2-3 specific search queries that would help answer their question. Return only the search queries, one per line, without numbers or bullets:",
            "source_selection": "Based on these search results, select the most relevant sources that would help answer the user's question. Return only the URLs of the selected sources, one per line:",
            "final_answer": "Based on the provided sources and information, provide a comprehensive answer to the user's question. Include relevant details and cite your sources when possible."
        }
    
    async def send_status_update(self, message: str, status_type: str = "info"):
        """Send status updates via WebSocket"""
        if self.websocket:
            try:
                await self.websocket.send_text(json.dumps({
                    "type": "status",
                    "status_type": status_type,
                    "message": message
                }))
            except:
                pass  # WebSocket might be closed
    
    async def async_generate_search_queries(self, question):
        """Async version of search query generation with status updates"""
        await self.send_status_update("🔍 Generating search queries...", "info")
        
        try:
            conversation_context = self.get_conversation_context()
            full_context = f"{conversation_context}Current question: {question}" if conversation_context else question
            
            response = ollama.generate(
                model=self.search_query_model,
                prompt=self.prompts["search_query_prompt"].format(question=full_context)
            )
            
            response_text = response['response'].strip()
            
            # Process response (same logic as parent class)
            refusal_patterns = [
                "i can't", "i cannot", "i'm not able", "i'm unable", 
                "not appropriate", "can't help", "cannot help", 
                "not assist", "cannot assist", "sorry, i can't"
            ]
            
            if any(pattern in response_text.lower() for pattern in refusal_patterns):
                await self.send_status_update("Using fallback keyword extraction", "warning")
                clean_question = question.replace('"', '').replace("'", '').replace('`', '')
                words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_question)
                keywords = [word for word in words if word.lower() not in ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'you', 'tell', 'explain', 'about']]
                return [' '.join(keywords[:5])] if keywords else [clean_question]
            
            lines = response_text.split('\n')
            clean_queries = []
            
            unwanted_patterns = [
                'here are', 'search queries', 'based on', 'question:', 
                'search terms:', 'queries:', 'search query:', 'terms:'
            ]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                line = re.sub(r'^\d+\.\s*', '', line)
                line = line.replace('"', '').replace("'", '').replace('`', '')
                line = line.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
                
                if any(pattern in line.lower() for pattern in unwanted_patterns):
                    continue
                    
                if len(line) < 3:
                    continue
                    
                clean_queries.append(line)
            
            queries = clean_queries[:3] if clean_queries else [question]
            await self.send_status_update(f"Generated {len(queries)} search queries", "success")
            return queries
            
        except Exception as e:
            await self.send_status_update(f"Error generating queries: {str(e)}", "error")
            return [question]
    
    async def async_search_web(self, query, num_results=10):
        """Async version of web search with status updates"""
        await self.send_status_update(f"🌐 Searching for: {query}", "info")
        
        try:
            delay = random.uniform(1, 3)
            await asyncio.sleep(delay)
            
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 202:
                await self.send_status_update("Trying alternative search method...", "warning")
                return await self.async_search_web_alternative(query, num_results)
            elif response.status_code != 200:
                await self.send_status_update(f"Search returned status {response.status_code}", "warning")
                return await self.async_search_web_alternative(query, num_results)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            result_selectors = [
                'a.result__a',
                '.result__title a',
                '.results_links_deep a',
                '.web-result__title a',
                'h2.result__title a'
            ]
            
            results = []
            result_elements = []
            
            for selector in result_selectors:
                result_elements = soup.select(selector)[:num_results]
                if result_elements:
                    break
            
            if not result_elements:
                return await self.async_search_web_alternative(query, num_results)
            
            for i, element in enumerate(result_elements, 1):
                title = element.get_text().strip()
                url = element.get('href', '')
                
                if url.startswith('/l/?uddg='):
                    try:
                        url = requests.utils.unquote(url.split('uddg=')[1])
                    except:
                        continue
                elif url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    continue
                
                if title and url and url.startswith('http'):
                    results.append({
                        'number': i,
                        'title': title,
                        'url': url
                    })
                
            await self.send_status_update(f"Found {len(results)} search results", "success")
            return results
            
        except Exception as e:
            await self.send_status_update(f"Search error: {str(e)}", "error")
            return await self.async_search_web_alternative(query, num_results)
    
    async def async_search_web_alternative(self, query, num_results=10):
        """Async alternative search method"""
        try:
            await asyncio.sleep(random.uniform(2, 4))
            
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            result_elements = soup.select('h3')[:num_results]
            
            for i, element in enumerate(result_elements, 1):
                parent = element.find_parent('a')
                if parent and parent.get('href'):
                    title = element.get_text().strip()
                    url = parent.get('href')
                    
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                        url = requests.utils.unquote(url)
                    
                    if title and url and url.startswith('http'):
                        results.append({
                            'number': i,
                            'title': title,
                            'url': url
                        })
            
            return results
            
        except Exception as e:
            await self.send_status_update("Using mock results for testing", "warning")
            return self.get_mock_results(query)
    
    async def async_chat_response(self, question: str, search_mode: str = "auto"):
        """Async version of the main chat logic with RAG support"""
        try:
            # Check if this is an image generation request
            if self.is_image_request(question):
                await self.send_status_update("🎨 Processing image generation request...", "info")
                final_answer = self.handle_image_request(question)
                self.add_to_conversation_history(question, final_answer)
                
                # Extract image path if generated
                image_path = None
                if "Saved to:" in final_answer:
                    path_start = final_answer.find("Saved to:") + 10
                    path_end = final_answer.find("\n", path_start)
                    if path_end == -1:
                        path_end = len(final_answer)
                    image_path = final_answer[path_start:path_end].strip()
                
                return {
                    "response": final_answer,
                    "image_path": image_path,
                    "search_queries": None,
                    "sources": None
                }
            
            # Use RAG if available and enabled
            if self.use_rag and hybrid_search and search_mode != "web":
                return await self._async_chat_response_with_rag(question, search_mode)
            else:
                return await self._async_chat_response_original(question)
                
        except Exception as e:
            await self.send_status_update(f"Error: {str(e)}", "error")
            return {
                "response": f"An error occurred: {str(e)}",
                "image_path": None,
                "search_queries": None,
                "sources": None
            }
    
    async def _async_chat_response_with_rag(self, question: str, search_mode: str = "auto"):
        """Chat response using RAG capabilities"""
        try:
            await self.send_status_update("🔍 Searching documents and web...", "info")
            
            # Use hybrid search
            search_results = await hybrid_search.search(
                query=question,
                search_mode=search_mode
            )
            
            # Check if we found useful results
            doc_results = search_results.get('document_results', [])
            web_results = search_results.get('web_results', [])
            
            if not doc_results and not web_results:
                await self.send_status_update("No relevant sources found, using built-in knowledge", "warning")
                final_answer = self.generate_knowledge_based_answer(question)
                self.add_to_conversation_history(question, final_answer)
                return {
                    "response": final_answer,
                    "image_path": None,
                    "search_queries": None,
                    "sources": None
                }
            
            # Generate answer using combined context
            await self.send_status_update("🤖 Generating answer from sources...", "info")
            context = search_results.get('combined_context', '')
            
            # Use enhanced prompt for RAG responses
            conversation_context = self.get_conversation_context()
            rag_prompt = self.prompts.get("document_synthesis_prompt", 
                "Answer this question using the provided document excerpts and web sources:\n\nQuestion: {question}\n\nContext:\n{context}\n\nAnswer:")
            
            full_context = f"{conversation_context}\n{context}" if conversation_context else context
            
            response = ollama.generate(
                model=self.main_model,
                prompt=rag_prompt.format(question=question, context=full_context)
            )
            
            final_answer = response['response']
            self.add_to_conversation_history(question, final_answer)
            
            # Format sources for response
            sources = search_results.get('sources', [])
            formatted_sources = []
            
            for source in sources:
                if source['type'] == 'document':
                    formatted_sources.append({
                        "title": f"{source['title']} ({source['chunk_info']})",
                        "url": f"document://{source['filename']}",
                        "type": "document"
                    })
                else:
                    formatted_sources.append({
                        "title": source['title'],
                        "url": source['url'],
                        "type": "web"
                    })
            
            return {
                "response": final_answer,
                "image_path": None,
                "search_queries": None,  # Could extract from search_results if needed
                "sources": formatted_sources,
                "rag_info": {
                    "search_mode": search_mode,
                    "document_count": len(doc_results),
                    "web_count": len(web_results),
                    "confidence_scores": search_results.get('confidence_scores', {})
                }
            }
            
        except Exception as e:
            await self.send_status_update(f"RAG search failed: {str(e)}", "error")
            # Fallback to original method
            return await self._async_chat_response_original(question)
    
    async def _async_chat_response_original(self, question: str):
        """Original chat response method (existing logic)"""
        try:
            # Check if this is an image generation request
            if self.is_image_request(question):
                await self.send_status_update("🎨 Processing image generation request...", "info")
                final_answer = self.handle_image_request(question)
                self.add_to_conversation_history(question, final_answer)
                
                # Extract image path if generated
                image_path = None
                if "Saved to:" in final_answer:
                    path_start = final_answer.find("Saved to:") + 10
                    path_end = final_answer.find("\n", path_start)
                    if path_end == -1:
                        path_end = len(final_answer)
                    image_path = final_answer[path_start:path_end].strip()
                
                return {
                    "response": final_answer,
                    "image_path": image_path,
                    "search_queries": None,
                    "sources": None
                }
            
            # Check if we can answer from conversation context
            if not self.needs_search(question) and self.conversation_history:
                await self.send_status_update("💭 Answering from conversation context...", "info")
                final_answer = self.generate_final_answer(question, use_search_context=False)
                self.add_to_conversation_history(question, final_answer)
                return {
                    "response": final_answer,
                    "image_path": None,
                    "search_queries": None,
                    "sources": None
                }
            
            # Check if the model can answer without search
            await self.send_status_update("🧠 Checking built-in knowledge...", "info")
            if self.can_answer_without_search(question):
                await self.send_status_update("✓ Answering with built-in knowledge...", "success")
                final_answer = self.generate_knowledge_based_answer(question)
                self.add_to_conversation_history(question, final_answer)
                return {
                    "response": final_answer,
                    "image_path": None,
                    "search_queries": None,
                    "sources": None
                }
            
            await self.send_status_update("🔍 Starting web search...", "info")
            
            # Generate search queries
            search_queries = await self.async_generate_search_queries(question)
            
            # Search for each query
            all_results = []
            for query in search_queries:
                results = await self.async_search_web(query)
                all_results.extend(results)
            
            # Remove duplicates
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result['url'] not in seen_urls and len(unique_results) < 10:
                    seen_urls.add(result['url'])
                    result['number'] = len(unique_results) + 1
                    unique_results.append(result)
            
            if not unique_results:
                await self.send_status_update("No search results found, using built-in knowledge", "warning")
                final_answer = self.generate_knowledge_based_answer(question)
                self.add_to_conversation_history(question, final_answer)
                return {
                    "response": final_answer,
                    "image_path": None,
                    "search_queries": search_queries,
                    "sources": None
                }
            
            # Select best sources
            await self.send_status_update("🎯 Selecting best sources...", "info")
            selected_sources = self.select_best_sources(question, unique_results)
            
            # Extract content
            await self.send_status_update("📖 Extracting content from sources...", "info")
            context = ""
            for i, source in enumerate(selected_sources, 1):
                content = self.extract_content(source['url'])
                context += f"\n--- Source {i}: {source['title']} ---\n{content}\n"
            
            # Generate final answer
            await self.send_status_update("🤖 Generating final answer...", "info")
            final_answer = self.generate_final_answer(question, context, use_search_context=True)
            
            self.add_to_conversation_history(question, final_answer)
            
            return {
                "response": final_answer,
                "image_path": None,
                "search_queries": search_queries,
                "sources": [{"title": s["title"], "url": s["url"]} for s in selected_sources]
            }
            
        except Exception as e:
            await self.send_status_update(f"Error: {str(e)}", "error")
            return {
                "response": f"An error occurred: {str(e)}",
                "image_path": None,
                "search_queries": None,
                "sources": None
            }
    
    def needs_search(self, question):
        """Determine if a question needs web search or can be answered from conversation history."""
        # Keywords that typically indicate need for fresh information
        search_keywords = [
            'latest', 'recent', 'current', 'new', 'update', 'now', 'today', 
            'what is', 'who is', 'when did', 'where is', 'how many', 'statistics',
            'facts about', 'information about', 'tell me about'
        ]
        
        # Keywords that suggest referencing previous conversation
        reference_keywords = [
            'that', 'this', 'it', 'he', 'she', 'they', 'them', 'his', 'her', 'their',
            'mentioned', 'said', 'previous', 'before', 'earlier', 'above', 'also',
            'and', 'furthermore', 'additionally', 'moreover'
        ]
        
        question_lower = question.lower()
        
        # If question has reference keywords and conversation history exists, might not need search
        if any(keyword in question_lower for keyword in reference_keywords) and self.conversation_history:
            # But still search if it also has search keywords
            if any(keyword in question_lower for keyword in search_keywords):
                return True
            # For short questions with references, try to answer from context first
            if len(question.split()) < 8:
                return False
        
        return True
    
    def can_answer_without_search(self, question):
        """Check if the main model can answer the question without web search."""
        try:
            # Include conversation context
            conversation_context = self.get_conversation_context()
            full_context = f"{conversation_context}Current question: {question}" if conversation_context else question
            
            response = ollama.generate(
                model=self.main_model,
                prompt=self.prompts.get("knowledge_assessment_prompt", "Can you answer this question: {question} - Respond with YES or NO").format(question=full_context)
            )
            
            assessment = response['response'].strip().upper()
            
            return "YES" in assessment
            
        except Exception as e:
            print(f"Error in knowledge assessment: {e}")
            return False  # Default to search if assessment fails
    
    def generate_knowledge_based_answer(self, question):
        """Generate an answer using only the model's built-in knowledge and conversation context."""
        try:
            conversation_context = self.get_conversation_context()
            full_context = f"{conversation_context}Current question: {question}" if conversation_context else question
            
            response = ollama.generate(
                model=self.main_model,
                prompt=self.prompts.get("knowledge_based_prompt", "Answer this question using your built-in knowledge: {question}").format(question=full_context)
            )
            
            return response['response'].strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"
    
    def select_best_sources(self, question, search_results):
        """Use a small model to select the best 2 sources."""
        try:
            sources_text = "\n".join([
                f"{i}. {result['title']} - {result['url']}"
                for i, result in enumerate(search_results, 1)
            ])
            
            response = ollama.generate(
                model=self.source_selection_model,
                prompt=self.prompts.get("source_selection_prompt", "Select the best 2 sources from: {search_results}").format(
                    question=question,
                    search_results=sources_text
                )
            )
            
            selected_text = response['response'].strip()
            
            # Extract numbers from response
            numbers = re.findall(r'\b(\d+)\b', selected_text)
            selected_indices = []
            
            for num in numbers:
                try:
                    idx = int(num) - 1
                    if 0 <= idx < len(search_results):
                        selected_indices.append(idx)
                except ValueError:
                    continue
            
            # Return selected sources or first 2 if nothing selected
            if selected_indices:
                return [search_results[i] for i in selected_indices[:2]]
            else:
                return search_results[:2]
                
        except Exception as e:
            print(f"Error selecting sources: {e}")
            return search_results[:2]
    
    def extract_content(self, url):
        """Extract main content from a URL using trafilatura."""
        try:
            response = requests.get(url, timeout=10)
            content = trafilatura.extract(response.content)
            
            if content:
                # Limit content length
                return content[:2000] + "..." if len(content) > 2000 else content
            else:
                return "Could not extract content from this URL."
                
        except Exception as e:
            return f"Error accessing URL: {str(e)}"
    
    def generate_final_answer(self, question, context="", use_search_context=True):
        """Generate the final answer using the main model with context."""
        try:
            conversation_context = self.get_conversation_context()
            
            if use_search_context and context:
                full_context = f"{conversation_context}\n\nWeb Search Results:\n{context}" if conversation_context else f"Web Search Results:\n{context}"
                prompt = self.prompts.get("main_answer_prompt", self.prompts.get("final_answer_prompt", "Answer this question using the provided context: {question}\n\nContext: {context}")).format(
                    question=question,
                    context=full_context
                )
            else:
                full_context = f"{conversation_context}Current question: {question}" if conversation_context else question
                prompt = self.prompts.get("conversation_answer_prompt", self.prompts.get("conversation_prompt", "Answer this question using the conversation history: {question}")).format(question=full_context)
            
            response = ollama.generate(
                model=self.main_model,
                prompt=prompt
            )
            
            return response['response'].strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error while generating the response: {str(e)}"
    
    def get_conversation_context(self):
        """Get recent conversation history as context."""
        if not self.conversation_history.get(self.session_id):
            return ""
        
        history = self.conversation_history[self.session_id]
        if len(history) == 0:
            return ""
        
        # Get last few exchanges for context
        recent_exchanges = history[-3:]  # Last 3 exchanges
        context_parts = []
        
        for exchange in recent_exchanges:
            context_parts.append(f"Human: {exchange['question']}")
            context_parts.append(f"Assistant: {exchange['answer']}")
        
        return "\n".join(context_parts) + "\n\n"
    
    def add_to_conversation_history(self, question, answer):
        """Add exchange to conversation history."""
        if self.session_id not in self.conversation_history:
            self.conversation_history[self.session_id] = []
        
        self.conversation_history[self.session_id].append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only recent history
        if len(self.conversation_history[self.session_id]) > self.max_history_length:
            self.conversation_history[self.session_id] = self.conversation_history[self.session_id][-self.max_history_length:]
    
    def get_mock_results(self, query):
        """Generate mock search results for testing when real search fails."""
        print(f"Using mock results for testing...")
        
        # Generate some realistic mock results based on the query
        mock_results = [
            {
                'number': 1,
                'title': f"{query} - Wikipedia",
                'url': f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
            },
            {
                'number': 2,
                'title': f"About {query} - Encyclopedia Britannica",
                'url': f"https://www.britannica.com/search?query={quote_plus(query)}"
            },
            {
                'number': 3,
                'title': f"{query} Information and Facts",
                'url': f"https://www.biography.com/search/{quote_plus(query)}"
            }
        ]
        
        return mock_results
    
    async def send_status_update(self, message, status_type="info"):
        """Send status update via WebSocket if available."""
        if self.websocket:
            try:
                await self.websocket.send_text(json.dumps({
                    "type": "status",
                    "message": message,
                    "status_type": status_type
                }))
            except Exception:
                pass  # WebSocket might be closed
    
    def is_image_request(self, question):
        """Check if the user is requesting image generation."""
        image_keywords = [
            'generate image', 'create image', 'make image', 'draw', 'picture', 'photo',
            'generate picture', 'create picture', 'make picture', 'show me', 'visualize',
            'image of', 'picture of', 'drawing of', 'illustration of', 'artwork of',
            'generate art', 'create art', 'make art', 'paint', 'sketch', 'render'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in image_keywords)
    
    def extract_image_prompt(self, question):
        """Extract the image description from the user's request."""
        try:
            # Use the main model to extract and improve the image prompt
            prompt_template = self.prompts.get("image_prompt_extraction", 
                f"Extract and improve the image description from this request. Return ONLY the image description, no other text.\n\nUser request: {{question}}\n\nImage description:")
            
            response = ollama.generate(
                model=self.main_model,
                prompt=prompt_template.format(question=question)
            )
            
            description = response['response'].strip()
            
            # Clean up the description
            description = description.replace('"', '').replace("'", '')
            
            # If the description is too short or doesn't make sense, fallback to keyword extraction
            if len(description) < 10:
                # Remove image request keywords and extract the subject
                clean_question = question.lower()
                remove_words = ['generate', 'create', 'make', 'draw', 'show', 'me', 'image', 'picture', 'photo', 'of', 'a', 'an', 'the']
                words = clean_question.split()
                filtered_words = [word for word in words if word not in remove_words]
                description = ' '.join(filtered_words)
            
            return description if description else "abstract art"
            
        except Exception as e:
            print(f"Error extracting image prompt: {e}")
            # Fallback: simple keyword extraction
            words = question.split()
            return ' '.join(words[2:]) if len(words) > 2 else "abstract art"
    
    def generate_image_stable_diffusion_api(self, prompt):
        """Generate image using Stable Diffusion API (Stability AI or local API)."""
        try:
            print(f"🎨 Generating image with Stable Diffusion API...")
            
            # Try local Stable Diffusion WebUI API first (if running on localhost:7860)
            local_api_url = "http://127.0.0.1:7860/sdapi/v1/txt2img"
            
            payload = {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy",
                "steps": 20,
                "width": 512,
                "height": 512,
                "cfg_scale": 7,
                "sampler_name": "DPM++ 2M Karras"
            }
            
            headers = {"Content-Type": "application/json"}
            
            print(f"🔗 Trying local Stable Diffusion WebUI...")
            
            response = requests.post(local_api_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if 'images' in result and result['images']:
                    image_data = result['images'][0]
                    return self.save_generated_image(image_data, prompt)
                else:
                    print(f"No image data in API response")
                    return None
            else:
                print(f"Local API not available (status: {response.status_code})")
                return None
                
        except requests.exceptions.ConnectionError:
            print(f"Local Stable Diffusion WebUI not running")
            return None
        except Exception as e:
            print(f"Error with Stable Diffusion API: {e}")
            return None
    
    def save_generated_image(self, image_data, prompt):
        """Save generated image to file."""
        try:
            # Create images directory if it doesn't exist
            images_dir = os.path.join(os.path.dirname(__file__), 'generated_images')
            os.makedirs(images_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = re.sub(r'[^a-zA-Z0-9_\-]', '_', prompt[:30])
            filename = f"{timestamp}_{safe_prompt}.png"
            filepath = os.path.join(images_dir, filename)
            
            # Decode and save image
            image_bytes = base64.b64decode(image_data)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✓ Image saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    
    def generate_image_mock(self, prompt):
        """Generate a mock image response for testing when no API is available."""
        print(f"📝 Mock image generation for: {prompt}")
        
        # Create a simple text file as a placeholder
        try:
            images_dir = os.path.join(os.path.dirname(__file__), 'generated_images')
            os.makedirs(images_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = re.sub(r'[^a-zA-Z0-9_\-]', '_', prompt[:30])
            filename = f"{timestamp}_{safe_prompt}_MOCK.txt"
            filepath = os.path.join(images_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"Mock image placeholder\n")
                f.write(f"Prompt: {prompt}\n")
                f.write(f"Generated at: {datetime.now()}\n")
                f.write(f"\nTo enable real image generation:\n")
                f.write(f"1. Install Stable Diffusion WebUI (AUTOMATIC1111)\n")
                f.write(f"2. Start it with --api flag\n")
                f.write(f"3. Or add your Stability AI API key\n")
            
            return filepath
            
        except Exception as e:
            print(f"Error creating mock image: {e}")
            return None
    
    def handle_image_request(self, question):
        """Handle image generation requests."""
        try:
            print(f"🎨 Processing image generation request...")
            
            # Extract image prompt from question
            image_prompt = self.extract_image_prompt(question)
            print(f"📝 Image prompt: {image_prompt}")
            
            # Try different image generation methods
            result_path = None
            
            # Method 1: Try Stable Diffusion API
            result_path = self.generate_image_stable_diffusion_api(image_prompt)
            
            # Method 2: Create mock response if all else fails
            if not result_path:
                result_path = self.generate_image_mock(image_prompt)
            
            if result_path:
                response = f"I've generated an image based on your request!\n\n"
                response += f"📝 **Prompt:** {image_prompt}\n"
                response += f"💾 **Saved to:** {result_path}\n\n"
                
                if result_path.endswith('_MOCK.txt'):
                    response += f"⚠️ **Note:** This is a mock response. To generate real images:\n"
                    response += f"1. Install Stable Diffusion WebUI (AUTOMATIC1111)\n"
                    response += f"2. Start it with `--api` flag on localhost:7860\n"
                    response += f"3. Or configure a Stability AI API key\n\n"
                else:
                    response += f"✨ **Real image generated successfully!**\n\n"
                
                response += f"You can view the {'file' if result_path.endswith('.txt') else 'image'} at the saved location."
                
                return response
            else:
                return "Sorry, I wasn't able to generate an image at this time. Please check if Stable Diffusion WebUI is running with the --api flag, or try again later."
                
        except Exception as e:
            return f"Error processing image request: {str(e)}"


@app.get("/")
async def root():
    return {"message": "AI Chat Web Interface API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """REST endpoint for chat (alternative to WebSocket)"""
    session_id = message.session_id or str(uuid.uuid4())
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = WebSearchEnhancedChat(session_id)
    
    chat_system = chat_sessions[session_id]
    result = await chat_system.async_chat_response(message.message)
    
    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        image_path=result["image_path"],
        search_queries=result["search_queries"],
        sources=result["sources"]
    )

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = WebSearchEnhancedChat(session_id)
    
    chat_system = chat_sessions[session_id]
    chat_system.websocket = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                question = message_data.get("message", "")
                
                if question.strip():
                    result = await chat_system.async_chat_response(question)
                    
                    await websocket.send_text(json.dumps({
                        "type": "response",
                        "response": result["response"],
                        "session_id": session_id,
                        "image_path": result["image_path"],
                        "search_queries": result["search_queries"],
                        "sources": result["sources"]
                    }))
                    
    except WebSocketDisconnect:
        if session_id in chat_sessions:
            chat_sessions[session_id].websocket = None

@app.get("/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chat_system = chat_sessions[session_id]
    return {"history": chat_system.conversation_history}

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"message": "Session cleared"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/images/{filename}")
async def get_image(filename: str):
    """Serve generated images"""
    image_path = os.path.join("../generated_images", filename)
    if os.path.exists(image_path):
        return FileResponse(image_path)
    raise HTTPException(status_code=404, detail="Image not found")

# Future RAG endpoints
@app.post("/upload-pdf", response_model=DocumentUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF for RAG processing"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        # Process the document
        result = await document_processor.process_file(file)
        
        if result.get('status') == 'failed':
            raise HTTPException(status_code=400, detail=result.get('error', 'Processing failed'))
        
        # Add to vector store
        document_id = await vector_store.add_document(
            file_info=result['file_info'],
            chunks=result['chunks'],
            metadata=result['metadata']
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=result['file_info']['original_name'],
            status="completed",
            message=f"Successfully processed document with {len(result['chunks'])} chunks"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """List uploaded documents"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        documents = await vector_store.list_documents(limit=limit, offset=offset, status_filter=status)
        
        result = []
        for doc in documents:
            result.append(DocumentInfo(
                id=doc['id'],
                original_name=doc['original_name'],
                file_type=doc['file_type'],
                file_size=doc['file_size'],
                upload_date=doc['upload_date'],
                status=doc['status'],
                metadata=json.loads(doc['metadata']) if isinstance(doc['metadata'], str) else doc['metadata']
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        success = await vector_store.delete_document(document_id)
        
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/documents/{document_id}")
async def get_document_info(document_id: str):
    """Get detailed information about a document"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        doc_metadata = await vector_store.get_document_metadata(document_id)
        if not doc_metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        chunks = await vector_store.get_document_chunks(document_id)
        
        return {
            "document": doc_metadata,
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {str(e)}")

@app.post("/search")
async def hybrid_search_endpoint(request: SearchRequest):
    """Perform hybrid search across documents and web"""
    if not RAG_AVAILABLE:
        # Fallback to web-only search
        session_id = request.session_id or str(uuid.uuid4())
        if session_id not in chat_sessions:
            chat_sessions[session_id] = WebSearchEnhancedChat(session_id)
        
        chat_system = chat_sessions[session_id]
        result = await chat_system._async_chat_response_original(request.query)
        
        return {
            "results": result,
            "search_mode": "web_only",
            "message": "RAG not available, used web search only"
        }
    
    try:
        results = await hybrid_search.search(
            query=request.query,
            search_mode=request.search_mode,
            document_filter=request.document_filter
        )
        
        return {
            "results": results,
            "search_mode": request.search_mode
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/documents/{document_id}/search")
async def search_within_document(document_id: str, query: str, top_k: int = 5):
    """Search within a specific document"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        results = await hybrid_search.search_specific_document(document_id, query, top_k)
        return {"results": results, "document_id": document_id, "query": query}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    if not RAG_AVAILABLE:
        return {"available": False, "message": "RAG functionality not installed"}
    
    try:
        stats = await hybrid_search.get_stats()
        stats["available"] = True
        return stats
        
    except Exception as e:
        return {"available": True, "error": str(e)}

@app.get("/rag/documents", response_model=List[DocumentInfo])
async def get_rag_documents(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """Get all documents for RAG system (alias for /documents)"""
    return await list_documents(limit=limit, offset=offset, status=status)

@app.post("/rag/reset")
async def reset_rag_system():
    """Reset the RAG system (development only)"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=501, detail="RAG functionality not available")
    
    try:
        await vector_store.reset_collection()
        return {"message": "RAG system reset successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@app.post("/chat-rag", response_model=ChatResponse)
async def chat_with_rag(message: ChatMessage, search_mode: str = "auto"):
    """Chat endpoint with RAG support"""
    session_id = message.session_id or str(uuid.uuid4())
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = WebSearchEnhancedChat(session_id)
    
    chat_system = chat_sessions[session_id]
    result = await chat_system.async_chat_response(message.message, search_mode)
    
    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        image_path=result["image_path"],
        search_queries=result["search_queries"],
        sources=result["sources"]
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
