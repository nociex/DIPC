# 文档智能解析中心 (DIPC)

[![Build Status](https://github.com/your-org/dipc/workflows/CI/badge.svg)](https://github.com/your-org/dipc/actions)
[![Coverage](https://codecov.io/gh/your-org/dipc/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/dipc)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

[English](README.md) | 中文

一个全面的文档处理系统，利用多模态大型语言模型（LLM）从各种文档格式（包括PDF、图像和ZIP档案）中提取结构化信息。

## 🚀 特性

- **多格式支持**：处理PDF、图像、文本文件和ZIP档案
- **批量处理**：通过ZIP档案同时处理多个文档
- **成本管理**：内置成本估算和限制功能
- **灵活存储**：选择永久或临时存储策略
- **向量化**：可选的向量数据库存储，支持语义搜索
- **实时监控**：实时跟踪处理状态和进度
- **Web界面**：用户友好的基于React的前端
- **REST API**：全面的API支持程序化访问
- **可扩展架构**：基于微服务的设计，支持Docker

## 🏗️ 架构

```mermaid
graph TD
    A[Next.js 前端] --> B[FastAPI 网关]
    B --> C[Celery 消息队列]
    C --> D[归档处理器]
    C --> E[解析处理器池]
    E --> F[LLM 提供商]
    E --> G[向量数据库]
    B --> H[PostgreSQL]
    D --> H
    E --> H
    B --> I[对象存储]
    E --> I
```

## 🛠️ 技术栈

### 后端
- **API网关**：FastAPI with Python 3.11+
- **消息队列**：Celery with Redis/RabbitMQ
- **数据库**：PostgreSQL with SQLAlchemy
- **存储**：S3兼容对象存储（AWS S3、MinIO）
- **向量数据库**：Qdrant 或 Milvus（可选）

### 前端
- **框架**：Next.js 14 with TypeScript
- **UI组件**：Radix UI with Tailwind CSS
- **状态管理**：React Query (TanStack Query)
- **表单处理**：React Hook Form
- **HTTP客户端**：Axios

### 工作流程
- **归档处理器**：处理ZIP文件并分发到解析器
- **解析处理器**：使用LLM提取文档信息
- **LLM提供商**：OpenAI、Anthropic、Google等

## 📋 先决条件

- Docker 和 Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 或 RabbitMQ
- S3兼容存储（AWS S3、MinIO等）

## 🚀 快速开始

### 使用Docker Compose（推荐）

1. 克隆仓库：
```bash
git clone https://github.com/your-org/dipc.git
cd dipc
```

2. 复制并配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，配置你的设置
```

3. 启动服务：
```bash
docker-compose up -d
```

4. 访问应用：
- 前端：http://localhost:3000
- API文档：http://localhost:8000/docs
- 数据库：localhost:5432
- MinIO控制台：http://localhost:9001

### 本地开发设置

#### 后端设置

1. 创建虚拟环境：
```bash
cd api
python -m venv venv
source venv/bin/activate  # Windows使用: venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. 运行数据库迁移：
```bash
alembic upgrade head
```

4. 启动FastAPI服务器：
```bash
uvicorn main:app --reload --port 8000
```

5. 在单独的终端启动Celery工作器：
```bash
# 归档处理器
celery -A celery_app worker --loglevel=info -Q archive_queue -n archive_worker

# 解析处理器
celery -A celery_app worker --loglevel=info -Q parsing_queue -n parsing_worker
```

#### 前端设置

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

## 🔧 配置

### 环境变量

关键环境变量：

```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/dipc

# Redis/消息队列
REDIS_URL=redis://localhost:6379/0

# 存储
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=dipc-documents

# LLM配置
OPENAI_API_KEY=your-api-key
ANTHROPIC_API_KEY=your-api-key

# 成本限制
MAX_COST_PER_DOCUMENT=1.0
MAX_COST_PER_BATCH=10.0
```

### 存储策略

在 `.env` 中配置存储策略：

- `STORAGE_POLICY=permanent`：永久保留所有文档
- `STORAGE_POLICY=temporary`：处理后删除文档

## 📊 API参考

### 主要端点

#### 提交文档
```http
POST /api/submit
Content-Type: multipart/form-data

file: <binary>
parsing_instructions: "提取所有表格和图表"
cost_limit: 5.0
enable_vectorization: true
```

#### 获取处理状态
```http
GET /api/document/{document_id}/status
```

#### 获取解析结果
```http
GET /api/document/{document_id}/result
```

完整的API文档请访问：http://localhost:8000/docs

## 🧪 测试

### 运行所有测试
```bash
./run_all_tests.sh
```

### 后端测试
```bash
cd api
pytest
```

### 前端测试
```bash
cd frontend
npm test
```

## 📈 监控和日志

- **日志**：检查 `logs/` 目录中的应用日志
- **Celery监控**：使用Flower进行任务监控
- **数据库监控**：使用pgAdmin或你喜欢的PostgreSQL客户端

## 🤝 贡献

我们欢迎贡献！请查看我们的[贡献指南](CONTRIBUTING.md)了解详情。

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 🙏 致谢

- 感谢所有LLM提供商的优秀API
- 基于现代Python和JavaScript最佳实践构建
- 受到文档处理领域各种开源项目的启发

## 📞 支持

- 创建[GitHub Issue](https://github.com/your-org/dipc/issues)报告问题
- 查看[Wiki](https://github.com/your-org/dipc/wiki)获取详细文档
- 加入我们的[讨论区](https://github.com/your-org/dipc/discussions)