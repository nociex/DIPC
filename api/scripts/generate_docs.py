#!/usr/bin/env python3
"""
Script to generate comprehensive API documentation for DIPC.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
from fastapi.openapi.utils import get_openapi
from src.main import app
from src.api.docs import get_openapi_config


def generate_openapi_spec() -> Dict[str, Any]:
    """Generate OpenAPI specification."""
    
    # Get base OpenAPI spec from FastAPI
    openapi_spec = get_openapi(
        title="Document Intelligence & Parsing Center API",
        version="1.3.0",
        description="Comprehensive document processing API using multi-modal LLMs",
        routes=app.routes,
    )
    
    # Merge with custom configuration
    custom_config = get_openapi_config()
    
    # Update with custom metadata
    openapi_spec.update({
        "info": custom_config["info"],
        "tags": custom_config["tags"],
        "servers": custom_config["servers"],
        "components": {
            **openapi_spec.get("components", {}),
            **custom_config["components"]
        }
    })
    
    return openapi_spec


def generate_postman_collection(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Postman collection from OpenAPI spec."""
    
    collection = {
        "info": {
            "name": "DIPC API Collection",
            "description": "Document Intelligence & Parsing Center API endpoints",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:8000",
                "type": "string"
            },
            {
                "key": "userId",
                "value": "test-user",
                "type": "string"
            }
        ],
        "item": []
    }
    
    # Convert OpenAPI paths to Postman requests
    for path, methods in openapi_spec.get("paths", {}).items():
        folder = {
            "name": path.split("/")[2] if len(path.split("/")) > 2 else "Root",
            "item": []
        }
        
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                request = {
                    "name": details.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "url": {
                            "raw": "{{baseUrl}}" + path,
                            "host": ["{{baseUrl}}"],
                            "path": path.strip("/").split("/")
                        }
                    },
                    "response": []
                }
                
                # Add request body for POST/PUT requests
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    if "requestBody" in details:
                        content = details["requestBody"].get("content", {})
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "example" in schema:
                                request["request"]["body"] = {
                                    "mode": "raw",
                                    "raw": json.dumps(schema["example"], indent=2)
                                }
                
                folder["item"].append(request)
        
        if folder["item"]:
            collection["item"].append(folder)
    
    return collection


def generate_curl_examples(openapi_spec: Dict[str, Any]) -> str:
    """Generate curl command examples."""
    
    examples = []
    examples.append("# DIPC API Curl Examples\n")
    
    for path, methods in openapi_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                examples.append(f"## {details.get('summary', f'{method.upper()} {path}')}")
                examples.append(f"# {details.get('description', '')}")
                
                curl_cmd = f"curl -X {method.upper()} \\\n"
                curl_cmd += f"  'http://localhost:8000{path}' \\\n"
                curl_cmd += f"  -H 'Content-Type: application/json'"
                
                # Add request body for POST/PUT
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    if "requestBody" in details:
                        content = details["requestBody"].get("content", {})
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "example" in schema:
                                body = json.dumps(schema["example"], indent=2)
                                curl_cmd += f" \\\n  -d '{body}'"
                
                examples.append(curl_cmd)
                examples.append("")
    
    return "\n".join(examples)


def generate_sdk_examples() -> str:
    """Generate SDK usage examples."""
    
    examples = """# DIPC SDK Examples

## Python SDK

```python
from dipc_client import DIPCClient

# Initialize client
client = DIPCClient(base_url="http://localhost:8000", user_id="your-user-id")

# Upload and process a single document
task = client.create_task(
    file_urls=["https://storage.example.com/document.pdf"],
    options={
        "enable_vectorization": True,
        "storage_policy": "permanent"
    }
)

# Monitor task progress
while task.status in ["pending", "processing"]:
    task = client.get_task_status(task.task_id)
    print(f"Status: {task.status}, Progress: {task.progress}%")
    time.sleep(5)

# Get results
if task.status == "completed":
    results = client.get_task_results(task.task_id)
    print(f"Extracted content: {results.extracted_content}")
```

## JavaScript SDK

```javascript
import { DIPCClient } from 'dipc-js-client';

// Initialize client
const client = new DIPCClient({
  baseUrl: 'http://localhost:8000',
  userId: 'your-user-id'
});

// Upload and process document
const task = await client.createTask({
  fileUrls: ['https://storage.example.com/document.pdf'],
  options: {
    enableVectorization: true,
    storagePolicy: 'permanent'
  }
});

// Monitor progress
const results = await client.waitForCompletion(task.taskId);
console.log('Extracted content:', results.extractedContent);
```

## cURL Examples

### Create Processing Task
```bash
curl -X POST 'http://localhost:8000/v1/tasks' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "file_urls": ["https://storage.example.com/document.pdf"],
    "user_id": "test-user",
    "options": {
      "enable_vectorization": true,
      "storage_policy": "permanent"
    }
  }'
```

### Check Task Status
```bash
curl -X GET 'http://localhost:8000/v1/tasks/{task_id}/status'
```

### Get Task Results
```bash
curl -X GET 'http://localhost:8000/v1/tasks/{task_id}/results'
```

### Get Presigned Upload URL
```bash
curl -X POST 'http://localhost:8000/v1/upload/presigned-url' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "user_id": "test-user"
  }'
```
"""
    
    return examples


def main():
    """Generate all documentation files."""
    
    print("Generating DIPC API documentation...")
    
    # Create output directory
    docs_dir = Path("docs/api")
    docs_dir.mkdir(exist_ok=True)
    
    # Generate OpenAPI specification
    print("Generating OpenAPI specification...")
    openapi_spec = generate_openapi_spec()
    
    # Save OpenAPI spec as JSON
    with open(docs_dir / "openapi.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    # Save OpenAPI spec as YAML
    with open(docs_dir / "openapi.yaml", "w") as f:
        yaml.dump(openapi_spec, f, default_flow_style=False)
    
    # Generate Postman collection
    print("Generating Postman collection...")
    postman_collection = generate_postman_collection(openapi_spec)
    with open(docs_dir / "postman_collection.json", "w") as f:
        json.dump(postman_collection, f, indent=2)
    
    # Generate curl examples
    print("Generating curl examples...")
    curl_examples = generate_curl_examples(openapi_spec)
    with open(docs_dir / "curl_examples.md", "w") as f:
        f.write(curl_examples)
    
    # Generate SDK examples
    print("Generating SDK examples...")
    sdk_examples = generate_sdk_examples()
    with open(docs_dir / "sdk_examples.md", "w") as f:
        f.write(sdk_examples)
    
    # Generate API reference
    print("Generating API reference...")
    api_reference = generate_api_reference(openapi_spec)
    with open(docs_dir / "api_reference.md", "w") as f:
        f.write(api_reference)
    
    print(f"Documentation generated in {docs_dir}")
    print("Files created:")
    for file in docs_dir.glob("*"):
        print(f"  - {file.name}")


def generate_api_reference(openapi_spec: Dict[str, Any]) -> str:
    """Generate comprehensive API reference documentation."""
    
    reference = []
    reference.append("# DIPC API Reference\n")
    reference.append("This document provides detailed information about all DIPC API endpoints.\n")
    
    # Add authentication section
    reference.append("## Authentication\n")
    reference.append("Currently, DIPC uses user-based identification through the `user_id` parameter.")
    reference.append("Future versions will include API key authentication.\n")
    
    # Add base URL section
    reference.append("## Base URL\n")
    reference.append("```")
    reference.append("Production: https://api.dipc.example.com")
    reference.append("Development: http://localhost:8000")
    reference.append("```\n")
    
    # Add endpoints documentation
    reference.append("## Endpoints\n")
    
    for path, methods in openapi_spec.get("paths", {}).items():
        reference.append(f"### {path}\n")
        
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                reference.append(f"#### {method.upper()} {path}")
                reference.append(f"{details.get('description', '')}\n")
                
                # Parameters
                if "parameters" in details:
                    reference.append("**Parameters:**")
                    for param in details["parameters"]:
                        required = " (required)" if param.get("required") else " (optional)"
                        reference.append(f"- `{param['name']}`{required}: {param.get('description', '')}")
                    reference.append("")
                
                # Request body
                if "requestBody" in details:
                    reference.append("**Request Body:**")
                    content = details["requestBody"].get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        if "example" in schema:
                            reference.append("```json")
                            reference.append(json.dumps(schema["example"], indent=2))
                            reference.append("```")
                    reference.append("")
                
                # Responses
                if "responses" in details:
                    reference.append("**Responses:**")
                    for status_code, response in details["responses"].items():
                        reference.append(f"- `{status_code}`: {response.get('description', '')}")
                        
                        content = response.get("content", {})
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "example" in schema:
                                reference.append("  ```json")
                                reference.append("  " + json.dumps(schema["example"], indent=2).replace("\n", "\n  "))
                                reference.append("  ```")
                    reference.append("")
    
    # Add error codes section
    reference.append("## Error Codes\n")
    reference.append("| Code | Description | HTTP Status |")
    reference.append("|------|-------------|-------------|")
    
    error_codes = [
        ("INVALID_REQUEST", "Invalid request parameters", "400"),
        ("FILE_TOO_LARGE", "File exceeds maximum size", "400"),
        ("UNSUPPORTED_FORMAT", "File format not supported", "400"),
        ("COST_LIMIT_EXCEEDED", "Processing cost exceeds limit", "400"),
        ("RATE_LIMITED", "Rate limit exceeded", "429"),
        ("TASK_NOT_FOUND", "Task not found", "404"),
        ("PROCESSING_FAILED", "Task processing failed", "500"),
        ("INTERNAL_ERROR", "Internal server error", "500")
    ]
    
    for code, description, status in error_codes:
        reference.append(f"| {code} | {description} | {status} |")
    
    reference.append("")
    
    # Add rate limiting section
    reference.append("## Rate Limiting\n")
    reference.append("The API implements the following rate limits:")
    reference.append("- Task creation: 100 requests per minute per user")
    reference.append("- Status checks: 1000 requests per minute per user")
    reference.append("- File uploads: 10 concurrent uploads per user")
    reference.append("")
    reference.append("Rate limit headers are included in responses:")
    reference.append("- `X-RateLimit-Limit`: Request limit per window")
    reference.append("- `X-RateLimit-Remaining`: Remaining requests in window")
    reference.append("- `X-RateLimit-Reset`: Time when window resets")
    
    return "\n".join(reference)


if __name__ == "__main__":
    main()