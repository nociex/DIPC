#!/usr/bin/env python3
"""
DIPC Interactive Setup Wizard
This script provides a guided setup experience for the Document Intelligence & Parsing Center.
"""

import os
import sys
import subprocess
import json
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

try:
    import requests
except ImportError:
    requests = None

def print_banner():
    """Print the DIPC banner."""
    banner = """
╔════════════════════════════════════════════════════════════════╗
║              Document Intelligence & Parsing Center           ║
║                        Setup Wizard                           ║
║                                                                ║
║  This wizard will guide you through the setup process         ║
║  and create a customized configuration for your needs.        ║
╚════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def colored_print(text: str, color: str = "white") -> None:
    """Print colored text."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    
    if color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)

def get_user_input(prompt: str, default: str = "", required: bool = True, 
                   input_type: str = "string", choices: List[str] = None) -> str:
    """Get user input with validation."""
    while True:
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "
        
        if choices:
            display_prompt = f"{prompt} {choices}: "
        
        try:
            user_input = input(display_prompt).strip()
            
            if not user_input and default:
                user_input = default
            
            if required and not user_input:
                colored_print("This field is required. Please enter a value.", "red")
                continue
            
            if choices and user_input not in choices:
                colored_print(f"Please choose from: {', '.join(choices)}", "red")
                continue
            
            if input_type == "int":
                try:
                    return str(int(user_input))
                except ValueError:
                    colored_print("Please enter a valid number.", "red")
                    continue
            
            if input_type == "bool":
                if user_input.lower() in ["y", "yes", "true", "1"]:
                    return "true"
                elif user_input.lower() in ["n", "no", "false", "0"]:
                    return "false"
                else:
                    colored_print("Please enter y/n, yes/no, true/false, or 1/0.", "red")
                    continue
            
            return user_input
            
        except KeyboardInterrupt:
            colored_print("\nSetup cancelled by user.", "yellow")
            sys.exit(0)
        except EOFError:
            colored_print("\nSetup cancelled.", "yellow")
            sys.exit(0)

def generate_secure_password(length: int = 32) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system."""
    try:
        subprocess.run([command, "--version"], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_prerequisites() -> Tuple[bool, List[str]]:
    """Check if all prerequisites are installed."""
    colored_print("Checking prerequisites...", "blue")
    
    required_commands = ["docker", "docker-compose"]
    missing_commands = []
    
    for cmd in required_commands:
        if not check_command_exists(cmd):
            missing_commands.append(cmd)
    
    # Check if Docker is running
    if "docker" not in missing_commands:
        try:
            subprocess.run(["docker", "info"], 
                          capture_output=True, check=True)
        except subprocess.CalledProcessError:
            missing_commands.append("docker (not running)")
    
    if missing_commands:
        colored_print("Missing prerequisites:", "red")
        for cmd in missing_commands:
            colored_print(f"  - {cmd}", "red")
        return False, missing_commands
    else:
        colored_print("All prerequisites are met ✓", "green")
        return True, []

def validate_api_key(api_key: str, provider: str) -> bool:
    """Validate API key by making a test request."""
    if not requests:
        colored_print("Skipping API key validation (requests module not available)", "yellow")
        return True
    
    if not api_key:
        return False
    
    try:
        if provider == "openai":
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", 
                                   headers=headers, timeout=10)
            return response.status_code == 200
        elif provider == "openrouter":
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://openrouter.ai/api/v1/models", 
                                   headers=headers, timeout=10)
            return response.status_code == 200
    except Exception:
        return False
    
    return True

def setup_llm_providers() -> Dict[str, str]:
    """Setup LLM provider configuration."""
    colored_print("\n=== LLM Provider Configuration ===", "cyan")
    print("DIPC requires an LLM provider for document processing.")
    print("OpenAI is recommended for best results. You can add other providers later.")
    print()
    
    providers = {}
    
    # OpenAI (required)
    while True:
        openai_key = get_user_input("Enter your OpenAI API key (sk-...)", 
                                   required=True)
        print("Validating OpenAI API key...")
        if validate_api_key(openai_key, "openai"):
            colored_print("OpenAI API key is valid ✓", "green")
            providers["OPENAI_API_KEY"] = openai_key
            providers["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
            providers["OPENAI_MODEL"] = "gpt-4o-mini"
            break
        else:
            colored_print("OpenAI API key validation failed", "yellow")
            use_anyway = get_user_input("Use this key anyway? (y/n)", 
                                      default="n", input_type="bool")
            if use_anyway == "true":
                providers["OPENAI_API_KEY"] = openai_key
                providers["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
                providers["OPENAI_MODEL"] = "gpt-4o-mini"
                break
            else:
                print("Please get an API key from https://platform.openai.com/api-keys")
    
    # Optional: Add other providers
    add_more = get_user_input("Add alternative LLM providers? (y/n)", 
                             default="n", input_type="bool")
    
    if add_more == "true":
        # OpenRouter (optional)
        openrouter_key = get_user_input("Enter your OpenRouter API key (optional, press Enter to skip)", 
                                       required=False)
        if openrouter_key:
            providers["OPENROUTER_API_KEY"] = openrouter_key
            providers["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"
            providers["OPENROUTER_MODEL"] = "openai/gpt-4o-mini"
    
    return providers

def setup_database() -> Dict[str, str]:
    """Setup database configuration."""
    colored_print("\n=== Database Configuration ===", "cyan")
    print("DIPC uses PostgreSQL for data storage.")
    print()
    
    db_config = {}
    
    # Database name
    db_name = get_user_input("Database name", default="dipc")
    db_config["POSTGRES_DB"] = db_name
    
    # Database user
    db_user = get_user_input("Database user", default="dipc_user")
    db_config["POSTGRES_USER"] = db_user
    
    # Database password
    generate_pwd = get_user_input("Generate secure password automatically? (y/n)", 
                                 default="y", input_type="bool")
    if generate_pwd == "true":
        db_password = generate_secure_password(16)
        colored_print(f"Generated password: {db_password}", "green")
    else:
        db_password = get_user_input("Database password", required=True)
    
    db_config["POSTGRES_PASSWORD"] = db_password
    db_config["DATABASE_URL"] = f"postgresql://{db_user}:{db_password}@localhost:5432/{db_name}"
    
    return db_config

def setup_storage() -> Dict[str, str]:
    """Setup storage configuration."""
    colored_print("\n=== Storage Configuration ===", "cyan")
    print("DIPC supports local storage (recommended) or S3-compatible storage.")
    print()
    
    storage_config = {}
    
    storage_type = get_user_input("Storage type", 
                                 choices=["local", "s3"], 
                                 default="local")
    
    if storage_type == "local":
        storage_config["STORAGE_TYPE"] = "local"
        storage_config["LOCAL_STORAGE_PATH"] = "/app/storage"
        storage_config["STORAGE_BASE_URL"] = "http://localhost:38100/storage"
        colored_print("Local storage configured (recommended for beginners)", "green")
        
    else:  # s3
        storage_config["STORAGE_TYPE"] = "s3"
        storage_config["S3_ENDPOINT_URL"] = get_user_input("S3 Endpoint URL", 
                                                         default="https://s3.amazonaws.com")
        storage_config["S3_ACCESS_KEY_ID"] = get_user_input("AWS Access Key ID", required=True)
        storage_config["S3_SECRET_ACCESS_KEY"] = get_user_input("AWS Secret Access Key", required=True)
        region = get_user_input("AWS Region", default="us-east-1")
        storage_config["S3_REGION"] = region
        
        # Bucket name
        bucket_name = get_user_input("Bucket name", default="dipc-storage")
        storage_config["S3_BUCKET_NAME"] = bucket_name
    
    return storage_config

def setup_advanced_features() -> Dict[str, str]:
    """Setup advanced features."""
    colored_print("\n=== Advanced Features ===", "cyan")
    print("Configure optional advanced features.")
    print()
    
    features = {}
    
    # Vector database
    enable_vector = get_user_input("Enable vector database for semantic search? (y/n)", 
                                  default="y", input_type="bool")
    features["ENABLE_VECTORIZATION"] = enable_vector
    
    if enable_vector == "true":
        features["QDRANT_URL"] = "http://dipc-qdrant:6333"
        features["QDRANT_API_KEY"] = ""
    
    # Performance settings
    max_workers = get_user_input("Number of worker processes", 
                               default="2", input_type="int")
    features["CELERY_WORKER_CONCURRENCY"] = max_workers
    
    # Cost limits
    max_cost = get_user_input("Maximum cost per task (USD)", 
                            default="1.00")
    features["MAX_COST_PER_TASK"] = max_cost
    
    daily_limit = get_user_input("Daily cost limit (USD)", 
                               default="10.00")
    features["DAILY_COST_LIMIT"] = daily_limit
    
    return features

def setup_deployment() -> Dict[str, str]:
    """Setup deployment configuration."""
    colored_print("\n=== Deployment Configuration ===", "cyan")
    print("Configure deployment settings.")
    print()
    
    deployment = {}
    
    # Environment
    env_type = get_user_input("Environment type", 
                             choices=["development", "production"], 
                             default="development")
    deployment["ENVIRONMENT"] = env_type
    
    # Security
    deployment["SECRET_KEY"] = generate_secure_password(32)
    deployment["JWT_SECRET_KEY"] = generate_secure_password(32)
    
    # API URL
    if env_type == "production":
        api_url = get_user_input("Public API URL", 
                               default="https://your-domain.com")
    else:
        api_url = "http://localhost:38100"
    
    deployment["NEXT_PUBLIC_API_URL"] = api_url
    
    return deployment

def create_env_file(config: Dict[str, str]) -> None:
    """Create the .env file with the configuration."""
    colored_print("\n=== Creating Configuration File ===", "cyan")
    
    env_file = Path(".env")
    if env_file.exists():
        backup_file = Path(".env.backup")
        colored_print(f"Backing up existing .env to {backup_file}", "yellow")
        env_file.rename(backup_file)
    
    with open(env_file, "w") as f:
        f.write("# DIPC Configuration\n")
        f.write(f"# Generated by dipc-setup.py\n")
        f.write(f"# Generated on {subprocess.check_output(['date']).decode().strip()}\n\n")
        
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    colored_print(f"Configuration saved to {env_file}", "green")

def show_next_steps(config: Dict[str, str]) -> None:
    """Show next steps to the user."""
    colored_print("\n=== Next Steps ===", "cyan")
    print()
    
    print("1. Start the services:")
    print("   docker-compose -f docker-compose.simple.yml up -d")
    print()
    
    print("2. Wait for services to be ready (may take a few minutes)")
    print()
    
    print("3. Access the application:")
    print("   - Frontend: http://localhost:38110")
    print("   - API: http://localhost:38100")
    print("   - API Docs: http://localhost:38100/docs")
    print()
    
    if config.get("S3_ENDPOINT_URL", "").startswith("http://localhost"):
        print("4. Access MinIO console: http://localhost:9001")
        print(f"   Username: {config.get('S3_ACCESS_KEY_ID', 'minioadmin')}")
        print(f"   Password: {config.get('S3_SECRET_ACCESS_KEY', 'minioadmin')}")
        print()
    
    print("5. Check service health:")
    print("   curl http://localhost:38100/v1/health")
    print()
    
    print("6. View logs if needed:")
    print("   docker-compose logs -f")
    print()
    
    if not config.get("OPENAI_API_KEY"):
        colored_print("⚠️  Remember to add your OpenAI API key to the .env file!", "yellow")
        print()

def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="DIPC Interactive Setup Wizard")
    parser.add_argument("--skip-validation", action="store_true",
                       help="Skip API key validation")
    parser.add_argument("--minimal", action="store_true",
                       help="Minimal setup with default values")
    args = parser.parse_args()
    
    print_banner()
    
    # Check prerequisites
    prereq_ok, missing = check_prerequisites()
    if not prereq_ok:
        colored_print("Please install missing prerequisites and try again.", "red")
        sys.exit(1)
    
    config = {}
    
    if args.minimal:
        colored_print("Running minimal setup with default values...", "blue")
        config.update({
            "POSTGRES_DB": "dipc",
            "POSTGRES_USER": "dipc_user",
            "POSTGRES_PASSWORD": generate_secure_password(16),
            "STORAGE_TYPE": "local",
            "LOCAL_STORAGE_PATH": "/app/storage",
            "STORAGE_BASE_URL": "http://localhost:38100/storage",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "gpt-4o-mini",
            "OPENROUTER_API_KEY": "",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_MODEL": "openai/gpt-4o-mini",
            "ENVIRONMENT": "development",
            "SECRET_KEY": generate_secure_password(32),
            "JWT_SECRET_KEY": generate_secure_password(32),
            "NEXT_PUBLIC_API_URL": "http://localhost:38100",
            "ENABLE_VECTORIZATION": "true",
            "QDRANT_URL": "http://dipc-qdrant:6333",
            "QDRANT_API_KEY": "",
            "CELERY_WORKER_CONCURRENCY": "2",
            "MAX_COST_PER_TASK": "1.00",
            "DAILY_COST_LIMIT": "10.00"
        })
        config["DATABASE_URL"] = f"postgresql://{config['POSTGRES_USER']}:{config['POSTGRES_PASSWORD']}@localhost:5432/{config['POSTGRES_DB']}"
    else:
        # Interactive setup
        config.update(setup_llm_providers())
        config.update(setup_database())
        config.update(setup_storage())
        config.update(setup_advanced_features())
        config.update(setup_deployment())
    
    # Add Redis configuration
    config.update({
        "REDIS_URL": "redis://localhost:6379/0",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0"
    })
    
    create_env_file(config)
    show_next_steps(config)
    
    colored_print("Setup complete! 🎉", "green")

if __name__ == "__main__":
    main()