#!/bin/bash

# DIPC 快速部署脚本
# 使用预构建的 Docker 镜像快速部署 DIPC

set -e

echo "🚀 DIPC 快速部署脚本"
echo "===================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：未检测到 Docker。请先安装 Docker。"
    echo "   访问 https://docs.docker.com/get-docker/ 获取安装指南"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误：未检测到 Docker Compose。请先安装 Docker Compose。"
    exit 1
fi

# 创建项目目录
echo "📁 创建项目目录..."
mkdir -p dipc && cd dipc

# 下载必要文件
echo "📥 下载配置文件..."
curl -fsSL https://raw.githubusercontent.com/nociex/DIPC/main/docker-compose.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/nociex/DIPC/main/db/init.sql -o init.sql
mkdir -p db && mv init.sql db/

# 检查是否已有 .env 文件
if [ ! -f .env ]; then
    echo ""
    echo "🔑 配置 LLM Provider"
    echo "请选择您的 LLM Provider："
    echo "1) OpenAI"
    echo "2) OpenRouter"
    echo "3) 其他兼容 OpenAI API 的服务"
    read -p "请输入选项 (1-3): " choice

    case $choice in
        1)
            read -p "请输入您的 OpenAI API Key: " api_key
            cat > .env << EOF
# OpenAI Configuration
OPENAI_API_KEY=$api_key
EOF
            ;;
        2)
            read -p "请输入您的 OpenRouter API Key: " api_key
            cat > .env << EOF
# OpenRouter Configuration
OPENROUTER_API_KEY=$api_key
EOF
            ;;
        3)
            read -p "请输入 API Key: " api_key
            read -p "请输入 API 端点 (例如: https://api.example.com/v1): " api_base
            cat > .env << EOF
# Custom OpenAI-compatible API
OPENAI_API_KEY=$api_key
OPENAI_API_BASE=$api_base
EOF
            ;;
        *)
            echo "❌ 无效的选项"
            exit 1
            ;;
    esac
    echo "✅ 配置文件创建成功"
fi

# 拉取镜像
echo ""
echo "🐳 拉取 Docker 镜像（这可能需要几分钟）..."
docker-compose pull

# 启动服务
echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo ""
echo "🔍 检查服务状态..."
docker-compose ps

# 测试 API 健康状态
echo ""
echo "🏥 检查 API 健康状态..."
if curl -f http://localhost:38100/v1/health &> /dev/null; then
    echo "✅ API 服务运行正常"
else
    echo "⚠️  API 服务可能还在启动中，请稍后再试"
fi

# 显示访问信息
echo ""
echo "🎉 部署完成！"
echo "============"
echo ""
echo "📱 前端界面: http://localhost:3000"
echo "🔌 API 接口: http://localhost:38100"
echo "📚 API 文档: http://localhost:38100/docs"
echo ""
echo "💡 提示："
echo "   - 查看日志: docker-compose logs -f"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart"
echo ""
echo "如有问题，请访问: https://github.com/nociex/DIPC/issues"