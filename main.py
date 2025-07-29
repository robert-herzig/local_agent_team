import ollama
import requests
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import json
import re
import os
import time
import random
from colorama import init, Fore, Style
import base64
from datetime import datetime

# Initialize colorama for colored output
init()

class SearchEnhancedChat:
    def __init__(self):
        # Model configuration - using more reliable models to avoid spelling errors
        self.search_query_model = "gemma3"  # Using main model for better accuracy
        self.source_selection_model = "llama3.2:1b"  # Small model for source selection
        self.main_model = "gemma3"  # Main model for final answers
        
        # Alternative models you can try if the default ones are too restrictive:
        # self.search_query_model = "llama3.2:1b"  # Smaller but less accurate
        # self.search_query_model = "llama3.2:3b"
        
        # Conversation memory
        self.conversation_history = []
        self.max_history_length = 10  # Keep last 10 exchanges
        
        # Load prompts from configuration file
        self.prompts = self.load_prompts()
    
    def load_prompts(self):
        """Load prompts from the prompts.json configuration file."""
        try:
            prompts_file = os.path.join(os.path.dirname(__file__), 'prompts.json')
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            print(f"{Fore.GREEN}✓ Loaded prompts from prompts.json{Style.RESET_ALL}")
            return prompts
        except FileNotFoundError:
            print(f"{Fore.RED}Error: prompts.json file not found. Using default prompts.{Style.RESET_ALL}")
            return self.get_default_prompts()
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}Error parsing prompts.json: {e}. Using default prompts.{Style.RESET_ALL}")
            return self.get_default_prompts()
        except Exception as e:
            print(f"{Fore.RED}Error loading prompts: {e}. Using default prompts.{Style.RESET_ALL}")
            return self.get_default_prompts()
    
    def get_default_prompts(self):
        """Fallback default prompts if configuration file is not available."""
        return {
            "search_query_prompt": "Convert this question into search queries. Respond with ONLY the search terms, one per line.\n\nQuestion: {question}\n\nSearch queries:",
            "source_selection_prompt": "Select the 2 most relevant sources from these search results. Respond with JSON format: {{\"selected_sources\": [1, 2]}}\n\nQuestion: {question}\n\nResults:\n{search_results}",
            "main_answer_prompt": "Answer this question based on the provided context.\n\nQuestion: {question}\n\nContext:\n{context}\n\nAnswer:",
            "conversation_answer_prompt": "Answer this question based on our conversation history.\n\nQuestion: {question}\n\nContext:\n{context}\n\nAnswer:",
            "knowledge_assessment_prompt": "Can you answer this question with your built-in knowledge? Respond with YES or NO.\n\nQuestion: {question}\n\nResponse:",
            "knowledge_based_answer_prompt": "Answer this question using your built-in knowledge.\n\nQuestion: {question}\n\nAnswer:"
        }

    def generate_search_queries(self, question):
        """Generate search queries using a small model."""
        try:
            # Include conversation context in query generation
            conversation_context = self.get_conversation_context()
            full_context = f"{conversation_context}Current question: {question}" if conversation_context else question
            
            response = ollama.generate(
                model=self.search_query_model,
                prompt=self.prompts["search_query_prompt"].format(question=full_context)
            )
            
            # Debug: Print the raw response
            print(f"{Fore.MAGENTA}Debug - Raw response: {response['response'][:200]}...{Style.RESET_ALL}")
            
            response_text = response['response'].strip()
            
            # Check for refusal patterns
            refusal_patterns = [
                "i can't", "i cannot", "i'm not able", "i'm unable", 
                "not appropriate", "can't help", "cannot help", 
                "not assist", "cannot assist", "sorry, i can't"
            ]
            
            if any(pattern in response_text.lower() for pattern in refusal_patterns):
                print(f"{Fore.YELLOW}Model refused - using simple keyword extraction{Style.RESET_ALL}")
                # Fallback: extract keywords from the question
                # First clean the question of quotation marks
                clean_question = question.replace('"', '').replace("'", '').replace('`', '')
                words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_question)
                keywords = [word for word in words if word.lower() not in ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'you', 'tell', 'explain', 'about']]
                return [' '.join(keywords[:5])] if keywords else [clean_question]
            
            # Clean up the response - remove unwanted patterns
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
                    
                # Remove numbering (1., 2., etc.)
                line = re.sub(r'^\d+\.\s*', '', line)
                
                # Remove quotation marks and other problematic characters for search
                line = line.replace('"', '').replace("'", '').replace('`', '')
                line = line.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
                
                # Skip lines that contain unwanted patterns
                if any(pattern in line.lower() for pattern in unwanted_patterns):
                    continue
                    
                # Skip very short lines (likely fragments)
                if len(line) < 3:
                    continue
                    
                clean_queries.append(line)
            
            return clean_queries[:3] if clean_queries else [question]  # Limit to 3 queries max
            
        except Exception as e:
            print(f"{Fore.RED}Error generating search queries: {e}{Style.RESET_ALL}")
            return [question]  # Fallback to original question

    def search_web(self, query, num_results=10):
        """Perform web search and return results."""
        try:
            print(f"{Fore.MAGENTA}Debug - Searching for: {query}{Style.RESET_ALL}")
            
            # Add random delay between 1-3 seconds to avoid rate limiting
            delay = random.uniform(1, 3)
            print(f"{Fore.MAGENTA}Debug - Adding {delay:.1f}s delay to avoid bot detection...{Style.RESET_ALL}")
            time.sleep(delay)
            
            # Using DuckDuckGo search (no API key required)
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            
            # Randomize User-Agent to avoid detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
            
            print(f"{Fore.MAGENTA}Debug - Search URL: {search_url}{Style.RESET_ALL}")
            
            response = requests.get(search_url, headers=headers, timeout=15)
            print(f"{Fore.MAGENTA}Debug - Response status: {response.status_code}{Style.RESET_ALL}")
            
            # Handle different response statuses
            if response.status_code == 202:
                print(f"{Fore.YELLOW}DuckDuckGo returned 202 (Accepted) - likely anti-bot protection. Trying alternative search...{Style.RESET_ALL}")
                return self.search_web_alternative(query, num_results)
            elif response.status_code == 429:
                print(f"{Fore.YELLOW}Rate limited by DuckDuckGo. Trying alternative search...{Style.RESET_ALL}")
                return self.search_web_alternative(query, num_results)
            elif response.status_code != 200:
                print(f"{Fore.YELLOW}DuckDuckGo returned status {response.status_code}. Trying alternative search...{Style.RESET_ALL}")
                return self.search_web_alternative(query, num_results)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple selectors for DuckDuckGo results
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
                    print(f"{Fore.MAGENTA}Debug - Found {len(result_elements)} results with selector: {selector}{Style.RESET_ALL}")
                    break
            
            if not result_elements:
                print(f"{Fore.MAGENTA}Debug - No results found with any selector. Trying alternative search...{Style.RESET_ALL}")
                return self.search_web_alternative(query, num_results)
            
            for i, element in enumerate(result_elements, 1):
                title = element.get_text().strip()
                url = element.get('href', '')
                
                # Handle different URL formats
                if url.startswith('/l/?uddg='):
                    # Extract actual URL from DuckDuckGo redirect
                    try:
                        url = requests.utils.unquote(url.split('uddg=')[1])
                    except:
                        continue
                elif url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    continue  # Skip relative URLs
                
                if title and url and url.startswith('http'):
                    results.append({
                        'number': i,
                        'title': title,
                        'url': url
                    })
                    print(f"{Fore.MAGENTA}Debug - Result {i}: {title[:50]}...{Style.RESET_ALL}")
                
            print(f"{Fore.MAGENTA}Debug - Total valid results: {len(results)}{Style.RESET_ALL}")
            return results
            
        except Exception as e:
            print(f"{Fore.RED}Error performing web search: {e}{Style.RESET_ALL}")
            return self.search_web_alternative(query, num_results)
    
    def search_web_alternative(self, query, num_results=10):
        """Alternative search method using a different approach."""
        try:
            print(f"{Fore.YELLOW}Trying alternative search method...{Style.RESET_ALL}")
            
            # Add delay for alternative search too
            delay = random.uniform(2, 4)
            print(f"{Fore.YELLOW}Debug - Adding {delay:.1f}s delay for alternative search...{Style.RESET_ALL}")
            time.sleep(delay)
            
            # Try Google search as fallback
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            # Use different User-Agent for alternative search
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            # Google result selectors
            result_elements = soup.select('h3')[:num_results]
            
            for i, element in enumerate(result_elements, 1):
                parent = element.find_parent('a')
                if parent and parent.get('href'):
                    title = element.get_text().strip()
                    url = parent.get('href')
                    
                    # Clean Google URL
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                        url = requests.utils.unquote(url)
                    
                    if title and url and url.startswith('http'):
                        results.append({
                            'number': i,
                            'title': title,
                            'url': url
                        })
            
            print(f"{Fore.YELLOW}Alternative search found {len(results)} results{Style.RESET_ALL}")
            return results
            
        except Exception as e:
            print(f"{Fore.RED}Alternative search also failed: {e}{Style.RESET_ALL}")
            # Return mock results for testing
            return self.get_mock_results(query)
    
    def get_mock_results(self, query):
        """Generate mock search results for testing when real search fails."""
        print(f"{Fore.YELLOW}Using mock results for testing...{Style.RESET_ALL}")
        
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
    
    def add_to_conversation_history(self, question, answer):
        """Add a question-answer pair to conversation history."""
        self.conversation_history.append({
            'question': question,
            'answer': answer
        })
        
        # Keep only the last N exchanges to prevent context from getting too long
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def get_conversation_context(self):
        """Get formatted conversation history for context."""
        if not self.conversation_history:
            return ""
        
        context = "\n--- Previous Conversation ---\n"
        for i, exchange in enumerate(self.conversation_history[-5:], 1):  # Last 5 exchanges
            context += f"Q{i}: {exchange['question']}\n"
            context += f"A{i}: {exchange['answer'][:200]}{'...' if len(exchange['answer']) > 200 else ''}\n\n"
        
        return context
    
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
                prompt=self.prompts["knowledge_assessment_prompt"].format(question=full_context)
            )
            
            assessment = response['response'].strip().upper()
            print(f"{Fore.MAGENTA}Debug - Knowledge assessment: {assessment}{Style.RESET_ALL}")
            
            return "YES" in assessment
            
        except Exception as e:
            print(f"{Fore.RED}Error in knowledge assessment: {e}{Style.RESET_ALL}")
            return False  # Default to search if assessment fails
    
    def generate_knowledge_based_answer(self, question):
        """Generate an answer using only the model's built-in knowledge and conversation context."""
        try:
            conversation_context = self.get_conversation_context()
            
            response = ollama.generate(
                model=self.main_model,
                prompt=self.prompts["knowledge_based_answer_prompt"].format(
                    question=question,
                    context=conversation_context
                )
            )
            
            return response['response']
            
        except Exception as e:
            return f"Error generating knowledge-based answer: {str(e)}"

    def select_best_sources(self, question, search_results):
        """Use a small model to select the best 2 sources."""
        try:
            # Format search results for the model
            formatted_results = ""
            for result in search_results:
                formatted_results += f"{result['number']}. {result['title']}\n   URL: {result['url']}\n\n"
            
            response = ollama.generate(
                model=self.source_selection_model,
                prompt=self.prompts["source_selection_prompt"].format(
                    question=question,
                    search_results=formatted_results
                )
            )
            
            # Parse JSON response
            response_text = response['response'].strip()
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                selection = json.loads(json_str)
                selected_indices = selection.get('selected_sources', [])
                
                # Return selected sources
                selected_sources = []
                for idx in selected_indices:
                    if 1 <= idx <= len(search_results):
                        selected_sources.append(search_results[idx - 1])
                
                return selected_sources[:2]  # Ensure max 2 sources
            else:
                # Fallback: select first 2 results
                return search_results[:2]
                
        except Exception as e:
            print(f"{Fore.RED}Error selecting sources: {e}{Style.RESET_ALL}")
            return search_results[:2]  # Fallback to first 2 results

    def extract_content(self, url):
        """Extract main content from a URL using trafilatura."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded)
                return content if content else "Content could not be extracted."
            else:
                return "URL could not be accessed."
        except Exception as e:
            return f"Error extracting content: {str(e)}"

    def generate_final_answer(self, question, context="", use_search_context=True):
        """Generate the final answer using the main model with context."""
        try:
            # Include conversation history in the context
            conversation_context = self.get_conversation_context()
            
            if use_search_context and context:
                # Standard mode with web search results
                full_context = f"{conversation_context}\n{context}" if conversation_context else context
                prompt_key = "main_answer_prompt"
            else:
                # Conversation-only mode
                full_context = conversation_context
                prompt_key = "conversation_answer_prompt"
            
            # Use conversation prompt if available, otherwise fall back to main prompt
            if prompt_key == "conversation_answer_prompt" and prompt_key not in self.prompts:
                prompt_key = "main_answer_prompt"
                full_context = f"{conversation_context}\n\nNote: This question may refer to our previous conversation." if conversation_context else "No additional context available."
            
            response = ollama.generate(
                model=self.main_model,
                prompt=self.prompts[prompt_key].format(
                    question=question,
                    context=full_context
                )
            )
            return response['response']
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
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
            print(f"{Fore.RED}Error extracting image prompt: {e}{Style.RESET_ALL}")
            # Fallback: simple keyword extraction
            words = question.split()
            return ' '.join(words[2:]) if len(words) > 2 else "abstract art"
    
    def generate_image_ollama(self, prompt):
        """Generate image using Ollama's vision models (if available)."""
        try:
            print(f"{Fore.CYAN}🎨 Attempting to generate image with Ollama...{Style.RESET_ALL}")
            
            # Try to use a vision model for image generation
            # Note: This requires specific vision models that support image generation
            vision_models = ["llava", "llava:13b", "llava:7b", "bakllava"]
            
            for model in vision_models:
                try:
                    response = ollama.generate(
                        model=model,
                        prompt=f"Generate a detailed description for creating an image of: {prompt}"
                    )
                    print(f"{Fore.YELLOW}📝 Enhanced prompt: {response['response'][:100]}...{Style.RESET_ALL}")
                    return response['response']
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"{Fore.RED}Error with Ollama image generation: {e}{Style.RESET_ALL}")
            return None
    
    def generate_image_stable_diffusion_api(self, prompt):
        """Generate image using Stable Diffusion API (Stability AI or local API)."""
        try:
            print(f"{Fore.CYAN}🎨 Generating image with Stable Diffusion API...{Style.RESET_ALL}")
            
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
            
            print(f"{Fore.CYAN}🔗 Trying local Stable Diffusion WebUI...{Style.RESET_ALL}")
            response = requests.post(local_api_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if 'images' in result and result['images']:
                    image_data = result['images'][0]
                    return self.save_generated_image(image_data, prompt)
                else:
                    print(f"{Fore.RED}No image data in API response{Style.RESET_ALL}")
                    return None
            else:
                print(f"{Fore.YELLOW}Local API not available (status: {response.status_code}){Style.RESET_ALL}")
                return None
                
        except requests.exceptions.ConnectionError:
            print(f"{Fore.YELLOW}Local Stable Diffusion WebUI not running{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Error with Stable Diffusion API: {e}{Style.RESET_ALL}")
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
            
            print(f"{Fore.GREEN}✓ Image saved: {filepath}{Style.RESET_ALL}")
            return filepath
            
        except Exception as e:
            print(f"{Fore.RED}Error saving image: {e}{Style.RESET_ALL}")
            return None
    
    def generate_image_mock(self, prompt):
        """Generate a mock image response for testing when no API is available."""
        print(f"{Fore.YELLOW}📝 Mock image generation for: {prompt}{Style.RESET_ALL}")
        
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
            print(f"{Fore.RED}Error creating mock image: {e}{Style.RESET_ALL}")
            return None
    
    def handle_image_request(self, question):
        """Handle image generation requests."""
        try:
            print(f"{Fore.CYAN}🎨 Processing image generation request...{Style.RESET_ALL}")
            
            # Extract image prompt from question
            image_prompt = self.extract_image_prompt(question)
            print(f"{Fore.CYAN}📝 Image prompt: {image_prompt}{Style.RESET_ALL}")
            
            # Try different image generation methods
            result_path = None
            
            # Method 1: Try Stable Diffusion API
            result_path = self.generate_image_stable_diffusion_api(image_prompt)
            
            # Method 2: If API fails, try Ollama vision models for enhanced description
            if not result_path:
                enhanced_description = self.generate_image_ollama(image_prompt)
                if enhanced_description:
                    print(f"{Fore.YELLOW}🔄 Trying API again with enhanced prompt...{Style.RESET_ALL}")
                    result_path = self.generate_image_stable_diffusion_api(enhanced_description)
            
            # Method 3: Create mock response if all else fails
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

    def chat(self):
        """Main chat loop with search enhancement, conversation memory, and image generation."""
        print(f"{Fore.CYAN}Search-Enhanced Chat System with Conversation Memory & Image Generation{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Models: Query Gen: {self.search_query_model} | Source Selection: {self.source_selection_model} | Main: {self.main_model}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}🎨 Image Generation: Stable Diffusion API supported{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Type 'exit' to quit{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 Try: 'generate an image of a sunset over mountains' or 'create a picture of a cute cat'{Style.RESET_ALL}\n")
        
        while True:
            question = input(f"{Fore.BLUE}You: {Style.RESET_ALL}")
            if question.lower() == "exit":
                break
            
            if not question.strip():
                continue
            
            try:
                # Step -1: Check if this is an image generation request
                if self.is_image_request(question):
                    print(f"{Fore.CYAN}🎨 Image generation request detected!{Style.RESET_ALL}")
                    final_answer = self.handle_image_request(question)
                    print(f"\n{Fore.GREEN}Assistant: {Style.RESET_ALL}{final_answer}\n")
                    self.add_to_conversation_history(question, final_answer)
                    continue
                
                # Step 0: First check if we can answer from conversation context (quick check)
                if not self.needs_search(question) and self.conversation_history:
                    print(f"{Fore.YELLOW}💭 Answering from conversation context...{Style.RESET_ALL}")
                    final_answer = self.generate_final_answer(question, use_search_context=False)
                    print(f"\n{Fore.GREEN}Assistant: {Style.RESET_ALL}{final_answer}\n")
                    self.add_to_conversation_history(question, final_answer)
                    continue
                
                # Step 1: Check if the main model can answer without search
                print(f"{Fore.YELLOW}🧠 Checking if answer is already known...{Style.RESET_ALL}")
                if self.can_answer_without_search(question):
                    print(f"{Fore.YELLOW}✓ Answering with built-in knowledge...{Style.RESET_ALL}")
                    final_answer = self.generate_knowledge_based_answer(question)
                    print(f"\n{Fore.GREEN}Assistant: {Style.RESET_ALL}{final_answer}\n")
                    self.add_to_conversation_history(question, final_answer)
                    continue
                
                print(f"{Fore.YELLOW}🔍 Built-in knowledge insufficient, starting web search...{Style.RESET_ALL}")
                
                # Step 2: Generate search queries (with conversation context)
                print(f"{Fore.YELLOW}🔍 Generating search queries...{Style.RESET_ALL}")
                search_queries = self.generate_search_queries(question)
                print(f"{Fore.CYAN}Search queries: {search_queries}{Style.RESET_ALL}")
                
                # Step 3: Search for each query and collect results
                print(f"{Fore.YELLOW}🌐 Searching web...{Style.RESET_ALL}")
                all_results = []
                for query in search_queries:
                    results = self.search_web(query)
                    all_results.extend(results)
                
                # Remove duplicates and limit to 10
                seen_urls = set()
                unique_results = []
                for result in all_results:
                    if result['url'] not in seen_urls and len(unique_results) < 10:
                        seen_urls.add(result['url'])
                        result['number'] = len(unique_results) + 1
                        unique_results.append(result)
                
                if not unique_results:
                    print(f"{Fore.YELLOW}No search results found. Falling back to built-in knowledge...{Style.RESET_ALL}")
                    final_answer = self.generate_knowledge_based_answer(question)
                    print(f"\n{Fore.GREEN}Assistant: {Style.RESET_ALL}{final_answer}\n")
                    self.add_to_conversation_history(question, final_answer)
                    continue
                
                print(f"{Fore.CYAN}Found {len(unique_results)} search results{Style.RESET_ALL}")
                
                # Step 4: Select best sources
                print(f"{Fore.YELLOW}🎯 Selecting best sources...{Style.RESET_ALL}")
                selected_sources = self.select_best_sources(question, unique_results)
                
                for source in selected_sources:
                    print(f"{Fore.CYAN}Selected: {source['title']}{Style.RESET_ALL}")
                
                # Step 5: Extract content from selected sources
                print(f"{Fore.YELLOW}📖 Extracting content...{Style.RESET_ALL}")
                context = ""
                for i, source in enumerate(selected_sources, 1):
                    print(f"{Fore.CYAN}Extracting from source {i}...{Style.RESET_ALL}")
                    content = self.extract_content(source['url'])
                    context += f"\n--- Source {i}: {source['title']} ---\n{content}\n"
                
                # Step 6: Generate final answer (with conversation context and web sources)
                print(f"{Fore.YELLOW}🤖 Generating answer with web sources...{Style.RESET_ALL}")
                final_answer = self.generate_final_answer(question, context, use_search_context=True)
                
                print(f"\n{Fore.GREEN}Assistant: {Style.RESET_ALL}{final_answer}\n")
                
                # Add to conversation history
                self.add_to_conversation_history(question, final_answer)
                
            except Exception as e:
                print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")

def main():
    chat_system = SearchEnhancedChat()
    chat_system.chat()

if __name__ == "__main__":
    main()