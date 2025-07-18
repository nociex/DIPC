# Document Intelligence & Parsing Center (DIPC)

[![Build Status](https://github.com/your-org/dipc/workflows/CI/badge.svg)](https://github.com/your-org/dipc/actions)
[![Coverage](https://codecov.io/gh/your-org/dipc/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/dipc)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

English | [中文](README.zh.md)

A comprehensive document processing system that leverages multi-modal Large Language Models (LLMs) to extract structured information from various document formats including PDFs, images, and ZIP archives.

## 🚀 Features

- **Multi-format Support**: Process PDFs, images, text files, and ZIP archives
- **Batch Processing**: Handle multiple documents simultaneously through ZIP archives
- **Cost Management**: Built-in cost estimation and limiting capabilities
- **Flexible Storage**: Choose between permanent and temporary storage policies
- **Vectorization**: Optional vector database storage for semantic search
- **Real-time Monitoring**: Track processing status and progress in real-time
- **Web Interface**: User-friendly React-based frontend
- **REST API**: Comprehensive API for programmatic access
- **Scalable Architecture**: Microservices-based design with Docker support

## 🏗️ Architecture

```mermaid
graph TD
    A[Next.js Frontend] --> B[FastAPI Gateway]
    B --> C[Celery Message Queue]
    C --> D[Archive Worker]
    C --> E[Parsing Worker Pool]
    E --> F[LLM Providers]
    E --> G[Vector Database]
    B --> H[PostgreSQL]
    D --> H
    E --> H
    B --> I[Object Storage]
    E --> I
```

## 🛠️ Technology Stack

### Backend
- **API Gateway**: FastAPI with Python 3.11+
- **Message Queue**: Celery with Redis/RabbitMQ
- **Database**: PostgreSQL with SQLAlchemy
- **Storage**: S3-compatible object storage (AWS S3, MinIO)
- **Vector Database**: Qdrant or Milvus (optional)

### Frontend
- **Framework**: Next.js 14 with TypeScript
- **UI Components**: Radix UI with Tailwind CSS
- **State Management**: React Query (TanStack Query)
- **Form Handling**: React Hook Form
- **HTTP Client**: Axios

### Workers
- **Archive Worker**: Processes ZIP files and distributes to parsers
- **Parsing Workers**: Extract information using LLMs
- **LLM Providers**: OpenAI, Anthropic, Google, etc.

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis or RabbitMQ
- S3-compatible storage (AWS S3, MinIO, etc.)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/your-org/dipc.git
cd dipc
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env file with your configurations
```

3. Start the services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Database: localhost:5432
- MinIO Console: http://localhost:9001

### Local Development Setup

#### Backend Setup

1. Create a virtual environment:
```bash
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

5. Start Celery workers in separate terminals:
```bash
# Archive worker
celery -A celery_app worker --loglevel=info -Q archive_queue -n archive_worker

# Parsing worker
celery -A celery_app worker --loglevel=info -Q parsing_queue -n parsing_worker
```

#### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

## 🔧 Configuration

### Environment Variables

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dipc

# Redis/Message Queue
REDIS_URL=redis://localhost:6379/0

# Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=dipc-documents

# LLM Configuration
OPENAI_API_KEY=your-api-key
ANTHROPIC_API_KEY=your-api-key

# Cost Limits
MAX_COST_PER_DOCUMENT=1.0
MAX_COST_PER_BATCH=10.0
```

### Storage Policies

Configure storage policy in `.env`:

- `STORAGE_POLICY=permanent`: Keep all documents permanently
- `STORAGE_POLICY=temporary`: Delete documents after processing

## 📊 API Reference

### Main Endpoints

#### Submit Document
```http
POST /api/submit
Content-Type: multipart/form-data

file: <binary>
parsing_instructions: "Extract all tables and charts"
cost_limit: 5.0
enable_vectorization: true
```

#### Get Processing Status
```http
GET /api/document/{document_id}/status
```

#### Get Parsed Results
```http
GET /api/document/{document_id}/result
```

For complete API documentation, visit: http://localhost:8000/docs

## 🧪 Testing

### Run All Tests
```bash
./run_all_tests.sh
```

### Backend Tests
```bash
cd api
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📈 Monitoring and Logging

- **Logs**: Check the `logs/` directory for application logs
- **Celery Monitoring**: Use Flower for task monitoring
- **Database Monitoring**: Use pgAdmin or your preferred PostgreSQL client

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all LLM providers for their excellent APIs
- Built with modern Python and JavaScript best practices
- Inspired by various open-source document processing projects

## 📞 Support

- Create a [GitHub Issue](https://github.com/your-org/dipc/issues) for bug reports
- Check our [Wiki](https://github.com/your-org/dipc/wiki) for detailed documentation
- Join our [Discussions](https://github.com/your-org/dipc/discussions) for community support