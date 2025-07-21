#!/bin/bash

# DIPC Quick Deploy Script
# This script automates the deployment of DIPC using pre-built Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo ""
    print_message "$BLUE" "======================================"
    print_message "$BLUE" "   DIPC Quick Deploy Script"
    print_message "$BLUE" "======================================"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker installation
check_docker() {
    print_message "$YELLOW" "Checking Docker installation..."
    
    if ! command_exists docker; then
        print_message "$RED" "Error: Docker is not installed."
        print_message "$YELLOW" "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_message "$RED" "Error: Docker Compose is not installed."
        print_message "$YELLOW" "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_message "$RED" "Error: Docker daemon is not running."
        print_message "$YELLOW" "Please start Docker and try again."
        exit 1
    fi
    
    print_message "$GREEN" "✓ Docker and Docker Compose are installed and running"
}

# Create project directory
create_project_dir() {
    print_message "$YELLOW" "Creating project directory..."
    
    if [ -d "dipc" ]; then
        print_message "$YELLOW" "Directory 'dipc' already exists."
        read -p "Do you want to continue? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_message "$YELLOW" "Deployment cancelled."
            exit 0
        fi
    else
        mkdir -p dipc
    fi
    
    cd dipc
    print_message "$GREEN" "✓ Project directory ready"
}

# Download configuration files
download_configs() {
    print_message "$YELLOW" "Downloading configuration files..."
    
    # Download docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        print_message "$YELLOW" "docker-compose.yml already exists, backing up..."
        mv docker-compose.yml docker-compose.yml.backup
    fi
    
    curl -fsSL https://raw.githubusercontent.com/nociex/DIPC/main/docker-compose.yml -o docker-compose.yml
    
    # Download .env.example
    if [ ! -f ".env" ]; then
        curl -fsSL https://raw.githubusercontent.com/nociex/DIPC/main/.env.example -o .env.example
        cp .env.example .env
    fi
    
    # Create db directory and download init.sql
    mkdir -p db
    curl -fsSL https://raw.githubusercontent.com/nociex/DIPC/main/db/init.sql -o db/init.sql
    
    print_message "$GREEN" "✓ Configuration files downloaded"
}

# Configure API key
configure_api_key() {
    print_message "$YELLOW" "Configuring API key..."
    
    # Check if API key is already configured
    if grep -q "^OPENAI_API_KEY=sk-" .env 2>/dev/null || grep -q "^OPENROUTER_API_KEY=sk-" .env 2>/dev/null; then
        print_message "$GREEN" "✓ API key already configured"
        return
    fi
    
    echo ""
    print_message "$BLUE" "Please choose your LLM provider:"
    echo "1) OpenAI"
    echo "2) OpenRouter"
    echo "3) Custom OpenAI-compatible endpoint"
    echo ""
    
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            read -p "Enter your OpenAI API key: " api_key
            sed -i.bak "s/# OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
            ;;
        2)
            read -p "Enter your OpenRouter API key: " api_key
            sed -i.bak "s/# OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$api_key/" .env
            ;;
        3)
            read -p "Enter your API key: " api_key
            read -p "Enter your API endpoint: " api_endpoint
            sed -i.bak "s/# OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
            echo "OPENAI_API_BASE=$api_endpoint" >> .env
            ;;
        *)
            print_message "$RED" "Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
    
    print_message "$GREEN" "✓ API key configured"
}

# Pull and start services
deploy_services() {
    print_message "$YELLOW" "Pulling Docker images..."
    docker compose pull
    
    print_message "$YELLOW" "Starting services..."
    docker compose up -d
    
    print_message "$GREEN" "✓ Services started"
}

# Check service health
check_services() {
    print_message "$YELLOW" "Checking service health..."
    
    # Wait for services to start
    sleep 10
    
    # Check if all services are running
    if docker compose ps | grep -q "Exit\|Error"; then
        print_message "$RED" "Some services failed to start:"
        docker compose ps
        print_message "$YELLOW" "Check logs with: docker compose logs"
        exit 1
    fi
    
    print_message "$GREEN" "✓ All services are running"
}

# Print success message
print_success() {
    echo ""
    print_message "$GREEN" "======================================"
    print_message "$GREEN" "   Deployment Successful! 🎉"
    print_message "$GREEN" "======================================"
    echo ""
    print_message "$BLUE" "Access your DIPC instance at:"
    print_message "$YELLOW" "  Frontend:  http://localhost:38110"
    print_message "$YELLOW" "  API Docs:  http://localhost:38100/docs"
    echo ""
    print_message "$BLUE" "Useful commands:"
    print_message "$YELLOW" "  View logs:    docker compose logs -f"
    print_message "$YELLOW" "  Stop services: docker compose down"
    print_message "$YELLOW" "  Update:       docker compose pull && docker compose up -d"
    echo ""
}

# Main execution
main() {
    print_header
    check_docker
    create_project_dir
    download_configs
    configure_api_key
    deploy_services
    check_services
    print_success
}

# Run main function
main