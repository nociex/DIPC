# 🚀 DIPC Quick Start Guide

This guide will help you get DIPC (Document Intelligence & Parsing Center) up and running in minutes.

## 📋 Prerequisites

Before starting, make sure you have:

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- **Git** for cloning the repository
- **LLM API Key** (OpenAI, OpenRouter, or other supported providers)

## 🎯 Choose Your Installation Method

### Option 1: One-Click Setup (Recommended for Beginners)

The easiest way to get started:

#### For Linux/macOS:
```bash
git clone https://github.com/your-org/dipc.git
cd dipc
./quickstart.sh
```

#### For Windows:
```batch
git clone https://github.com/your-org/dipc.git
cd dipc
quickstart.bat
```

**What it does:**
- ✅ Checks all prerequisites
- ✅ Creates configuration file
- ✅ Asks for your API keys
- ✅ Starts all services
- ✅ Sets up storage and database
- ✅ Shows you access URLs

### Option 2: Interactive Setup Wizard

For more control over the configuration:

```bash
git clone https://github.com/your-org/dipc.git
cd dipc
python dipc-setup.py
```

**Features:**
- 🎛️ Interactive configuration
- 🔍 API key validation
- ⚙️ Advanced settings
- 📊 Performance tuning

### Option 3: Manual Setup

For advanced users who want full control:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/dipc.git
   cd dipc
   ```

2. **Create configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

## 🔧 Configuration

### Required Settings

The minimum configuration you need:

```env
# LLM Provider (choose one)
OPENAI_API_KEY=sk-your-openai-key
# OR
OPENROUTER_API_KEY=sk-or-your-openrouter-key

# Database
POSTGRES_PASSWORD=your-secure-password

# Storage
S3_SECRET_ACCESS_KEY=your-secure-minio-password
```

### Getting API Keys

#### OpenAI (Recommended)
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new key
5. Copy the key (starts with `sk-`)

#### OpenRouter (Alternative)
1. Go to [OpenRouter](https://openrouter.ai/)
2. Create an account
3. Go to Keys section
4. Create a new key
5. Copy the key (starts with `sk-or-`)

## 🏃‍♂️ Running DIPC

### Starting the System

```bash
# Start all services
docker-compose up -d

# Or using the simple configuration
docker-compose -f docker-compose.simple.yml up -d
```

### Checking Status

```bash
# Check if all services are running
docker-compose ps

# Check API health
curl http://localhost:38100/v1/health

# View logs
docker-compose logs -f
```

### Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## 🌐 Accessing DIPC

Once running, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:38110](http://localhost:38110) | Main web interface |
| **API** | [http://localhost:38100](http://localhost:38100) | REST API endpoint |
| **API Docs** | [http://localhost:38100/docs](http://localhost:38100/docs) | Interactive API documentation |
| **Qdrant** | [http://localhost:6333](http://localhost:6333) | Vector database interface |

### Default Services

- **Vector Database**: Qdrant (enabled by default for semantic search)
- **File Storage**: Local storage (./storage directory)

## 📄 Using DIPC

### Web Interface

1. Open [http://localhost:38110](http://localhost:38110)
2. Upload a document (PDF, image, text, or ZIP)
3. Configure parsing options
4. Wait for processing
5. View and export results

### API Usage

#### Upload a Document

```bash
curl -X POST "http://localhost:38100/v1/upload/presigned-url" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "document.pdf",
    "file_size": 1024000,
    "content_type": "application/pdf"
  }'
```

#### Start Processing

```bash
curl -X POST "http://localhost:38100/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "your-uploaded-file-url",
    "task_type": "document_parsing",
    "options": {
      "extract_text": true,
      "extract_tables": true,
      "extract_images": false
    }
  }'
```

#### Check Task Status

```bash
curl "http://localhost:38100/v1/tasks/{task_id}/status"
```

## 🧪 Testing the Installation

### Quick Test

```bash
# Test API health
curl http://localhost:38100/v1/health

# Test worker health
curl http://localhost:8001/health
```

### Upload Test File

```bash
# Create a test document
echo "This is a test document for DIPC." > test.txt

# Upload via web interface at http://localhost:38110
# Or use the API examples above
```

## 🛠️ Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check Docker is running
docker info

# Check ports aren't in use
netstat -tuln | grep -E ":(38110|38100|5432|6379|6333)"

# Check logs
docker-compose logs
```

#### Database Connection Issues

```bash
# Check database status
docker-compose exec db pg_isready -U dipc_user

# Reset database
docker-compose down -v
docker-compose up -d
```

#### API Key Issues

```bash
# Test OpenAI key
curl -H "Authorization: Bearer your-api-key" \
  https://api.openai.com/v1/models

# Check logs for authentication errors
docker-compose logs api worker
```

#### Storage Issues

```bash
# Check local storage directory
ls -la ./storage

# Check storage permissions
ls -la ./storage
chmod 755 ./storage
```

### Performance Issues

#### Low Memory

```bash
# Reduce worker concurrency
echo "CELERY_WORKER_CONCURRENCY=1" >> .env
docker-compose restart worker
```

#### Slow Processing

```bash
# Check system resources
docker stats

# Increase processing timeout
echo "PROCESSING_TIMEOUT=600" >> .env
docker-compose restart
```

### Getting Help

#### Check System Status

```bash
# Run the diagnostic script
python dipc-health-check.py

# Or manually check each service
curl http://localhost:38100/v1/health
curl http://localhost:8001/health
```

#### Log Analysis

```bash
# View recent logs
docker-compose logs --tail=100

# Follow logs in real-time
docker-compose logs -f

# Service-specific logs
docker-compose logs api
docker-compose logs worker
docker-compose logs db
```

## 🔧 Advanced Configuration

### Environment Variables

Key configuration options:

```env
# Performance
CELERY_WORKER_CONCURRENCY=2
MAX_CONCURRENT_TASKS=5
PROCESSING_TIMEOUT=300

# Cost Control
MAX_COST_PER_TASK=1.00
DAILY_COST_LIMIT=10.00

# Security
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=100

# Features
ENABLE_VECTORIZATION=false
ENABLE_BATCH_PROCESSING=true
```

### Scaling

#### Add More Workers

```bash
# Scale worker service
docker-compose up -d --scale worker=3
```

#### Production Deployment

```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Custom Models

```env
# Custom model configurations
CUSTOM_MODEL_CONFIGS='{"gpt-4": {"max_tokens": 4000, "temperature": 0.1}}'
```

## 📚 Next Steps

### Learn More

- [User Guide](docs/user-guide.md) - Complete user documentation
- [API Reference](docs/api/api_reference.md) - Detailed API documentation
- [Deployment Guide](docs/deployment/README.md) - Production deployment
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

### Customize

- Modify parsing templates
- Add custom document types
- Integrate with your applications
- Set up monitoring and alerts

### Contribute

- [Contributing Guide](CONTRIBUTING.md) - How to contribute
- [GitHub Issues](https://github.com/your-org/dipc/issues) - Report bugs
- [GitHub Discussions](https://github.com/your-org/dipc/discussions) - Community support

## 🎉 You're Ready!

Your DIPC installation is now complete and ready to process documents. Upload your first document and start extracting structured information with the power of AI!

---

**Need help?** Check our [troubleshooting guide](docs/troubleshooting.md) or [open an issue](https://github.com/your-org/dipc/issues).