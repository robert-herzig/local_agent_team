# 🚀 Quick Start Guide

## Web Interface for Your AI Chat System

You now have a modern web interface for your AI chat system! Here's how to get started:

## 🎯 What You Get

### ✨ Modern Web Interface
- **Real-time chat** with WebSocket communication
- **Beautiful UI** with markdown support and syntax highlighting
- **Image generation** with preview and gallery
- **Source attribution** showing search queries and sources used
- **Conversation memory** with persistent history
- **Mobile-friendly** responsive design

### 🔧 Technical Features
- **FastAPI backend** with async processing
- **React frontend** with modern UI components
- **WebSocket + REST API** for reliable communication
- **Docker support** for easy deployment
- **RAG-ready architecture** for future PDF integration

## 🚀 How to Start

### Option 1: Quick Start (Recommended)
```bash
# 1. Start the backend
cd backend
python main.py

# 2. In a new terminal, start the frontend
cd frontend
npm install
npm start
```

### Option 2: Using Setup Scripts
```bash
# Windows
.\setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### Option 3: Using Docker
```bash
docker-compose up -d
```

## 📱 Access Your Application

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **WebSocket Endpoint**: ws://localhost:8000/ws/{session_id}

## 🎨 Features Walkthrough

### 1. **Chat Interface**
- Type messages just like in your terminal version
- See real-time status updates during processing
- View search queries and sources used for each response

### 2. **Image Generation**
- Ask for images: "generate an image of a sunset over mountains"
- Images are saved and displayed in the chat
- Full gallery view for all generated images

### 3. **Search Enhancement**
- Automatic web search when needed
- Display of search queries used
- Source attribution with clickable links
- Intelligent decision on when to search vs use built-in knowledge

### 4. **Conversation Memory**
- Full conversation history preserved
- Context-aware responses
- Clear chat functionality
- Session management

## 🔧 Configuration

### Backend Configuration
Your existing `prompts.json` file works as-is! The web interface uses the same configuration.

### Frontend Customization
Edit `frontend/src/App.js` to customize:
- UI colors and styling
- Component behavior
- API endpoints

## 🚀 Next Steps: Adding RAG

The architecture is designed for easy RAG integration. See `RAG_INTEGRATION_PLAN.md` for:
- **PDF Upload**: Drag-and-drop document processing
- **Vector Search**: Semantic search through documents
- **Hybrid Intelligence**: Combine web search with document knowledge

### Future RAG Features
- Upload PDFs and text documents
- Search through your document library
- Combine web search with document knowledge
- Document management and organization

## 🛠️ Troubleshooting

### Backend Issues
```bash
# Check if Ollama is running
ollama list

# Verify models are available
ollama pull gemma3
ollama pull llama3.2:1b

# Check Stable Diffusion WebUI (for images)
# Start with: webui.bat --api
```

### Frontend Issues
```bash
# Clear cache and restart
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### WebSocket Connection Issues
- If WebSocket fails, the app automatically falls back to REST API
- Check if port 8000 is available for the backend
- Verify no firewall blocking the connection

## 📊 Performance Tips

### For Better Performance
1. **Use Redis** for session storage (see docker-compose.yml)
2. **Enable caching** for search results
3. **Optimize images** with compression
4. **Use CDN** for static assets in production

### For Development
1. **Hot reload** is enabled for both frontend and backend
2. **Debug mode** shows detailed logs
3. **API docs** available at /docs endpoint

## 🔒 Security Notes

### Development (Current)
- No authentication required
- CORS enabled for localhost
- All endpoints publicly accessible

### Production Recommendations
- Add authentication and authorization
- Implement rate limiting
- Use HTTPS for all communications
- Restrict CORS to specific domains
- Add input validation and sanitization

## 📈 Monitoring

### Available Endpoints
- `GET /health` - Health check
- `GET /sessions/{id}/history` - Get chat history
- `DELETE /sessions/{id}` - Clear session
- `POST /chat` - Send message (REST)
- `WS /ws/{id}` - WebSocket chat

### Logs and Debugging
- Backend logs show detailed processing steps
- Frontend console shows WebSocket events
- API documentation at `/docs` endpoint

## 🎉 You're Ready!

Your AI chat system now has a modern web interface! The architecture supports:
- ✅ **Current features**: Web search, image generation, conversation memory
- 🔄 **Easy upgrades**: RAG integration, authentication, scaling
- 📱 **Modern UX**: Responsive design, real-time updates, rich formatting

Enjoy your new web-based AI assistant! 🤖✨
