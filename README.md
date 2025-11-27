# LangRAG Chat

A modern Retrieval-Augmented Generation (RAG) chat application built with FastAPI, LangChain, and Pinecone. This application enables intelligent document-based Q&A through semantic search and AI-powered responses.

## 🌟 Features

- **Document Management**: Upload and manage PDF, DOCX, and TXT documents
- **RAG-Powered Chat**: Ask questions and get answers based on your uploaded documents
- **Streaming Responses**: Real-time streaming chat with typewriter effect
- **Citation Support**: View source documents and citations for each response
- **Vector Search**: Powered by Pinecone with hosted embedding models
- **Modern UI**: Beautiful, responsive React-based frontend
- **Docker Deployment**: Easy deployment with Docker Compose

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   FastAPI    │─────▶│  Pinecone   │
│   (React)   │      │   Backend    │      │  Vector DB  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  LLM Service │
                     │ (OpenAI API) │
                     └──────────────┘
```

- **Frontend**: React-based SPA with streaming chat interface
- **Backend**: FastAPI server with LangChain RAG pipeline
- **Vector Store**: Pinecone for semantic document search
- **LLM**: OpenAI-compatible API (supports various providers)

## 📦 Prerequisites

- Python 3.13+
- Node.js 18+ (for frontend development)
- Docker & Docker Compose (for deployment)
- Pinecone account and API key
- OpenAI-compatible LLM API access

## 🚀 Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/langrag-chat.git
   cd langrag-chat
   ```

2. **Set up Python environment**
   ```bash
   # Using Conda
   conda env create -f environment.yml
   conda activate langrag

   # Or using venv
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Build frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   cp -r frontend/build/* backend/static/
   ```

5. **Run the application**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Access the application at `http://localhost:8000`

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Or deploy to remote server**
   ```bash
   ./deploy.sh
   ```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-3.5-turbo
LLM_API_KEY=your-llm-api-key

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_HOST=https://your-index.svc.pinecone.io
PINECONE_INDEX_NAME=your-index-name
EMBEDDING_MODEL=text-embedding-ada-002

# Application Settings
MAX_FILE_SIZE=104857600  # 100MB
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=4
```

## 💻 Usage

### 1. Upload Documents

- Click the sidebar toggle (hamburger menu on mobile)
- Drag and drop or select a PDF, DOCX, or TXT file
- Wait for processing to complete

### 2. Chat with RAG

- Type your question in the chat input
- The system will retrieve relevant document chunks and generate an answer
- View source documents and citations in the response

### 3. Manage Documents

- View all uploaded documents in the sidebar
- Reload a document to re-process and re-index
- Delete documents to remove them from the vector store
- Clear all index data if needed

## 📚 API Documentation

### Chat Endpoints

- `POST /api/chat` - Send a chat message (non-streaming)
- `POST /api/chat/stream` - Send a chat message (streaming)
- `GET /api/chat/history/{conversation_id}` - Get conversation history

### Document Endpoints

- `GET /api/documents` - List all documents
- `POST /api/documents/upload` - Upload a document
- `DELETE /api/documents/{document_id}` - Delete a document
- `POST /api/documents/{document_id}/reload` - Reload a document
- `POST /api/documents/clear-index` - Clear all index data

### Health

- `GET /api/health` - Health check endpoint

Interactive API documentation is available at `/docs` when the server is running.

## 🐳 Deployment

### Docker Compose

The project includes a `docker-compose.yml` for easy deployment:

```bash
docker-compose up -d
```

### Remote Server Deployment

Use the provided deployment script:

```bash
./deploy.sh
```

This will:
1. Build Docker image for amd64 platform
2. Push to container registry
3. Deploy to remote server
4. Start services with Docker Compose

### Environment Variables

Ensure all required environment variables are set in `.env` file on the deployment server.

## 🔧 Development

### Backend Development

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm start
```

The frontend will run on `http://localhost:3000` with proxy to backend.

### Running Tests

```bash
cd backend
pytest
```

Or use the test script:

```bash
./backend/run_tests.sh
```

## 📁 Project Structure

```
langrag-chat/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Pydantic models
│   │   ├── rag/
│   │   │   ├── chain.py         # RAG chain implementation
│   │   │   ├── embeddings.py    # Embedding setup
│   │   │   ├── vectorstore.py   # Pinecone integration
│   │   │   └── retriever.py    # Custom retriever
│   │   ├── routes/
│   │   │   ├── chat.py          # Chat endpoints
│   │   │   └── documents.py     # Document management endpoints
│   │   └── services/
│   │       ├── document_processor.py  # File processing
│   │       └── document_registry.py   # Document registry
│   ├── static/                  # Frontend build output
│   ├── uploads/                 # Uploaded documents
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── DocumentList.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   └── CitationDetail.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   └── App.jsx
│   └── package.json
├── docker-compose.yml
├── deploy.sh                    # Deployment script
├── test_deployment.sh           # Deployment test script
├── .env.example                 # Environment variables template
└── README.md
```

## 🧪 Testing

The project includes comprehensive tests:

- **API Tests**: Test all API endpoints
- **Vector Store Tests**: Test Pinecone integration
- **RAG Chain Tests**: Test RAG pipeline
- **Document Processor Tests**: Test file processing
- **Full Workflow Tests**: End-to-end integration tests

Run tests with:

```bash
cd backend
pytest
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) - LLM application framework
- [Pinecone](https://www.pinecone.io/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [React](https://react.dev/) - UI library

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: Make sure to keep your `.env` file secure and never commit it to version control.
