"""
OpenAPI documentation configuration for DIPC API.
"""

from typing import Dict, Any

# OpenAPI metadata
OPENAPI_METADATA = {
    "title": "Document Intelligence & Parsing Center API",
    "version": "1.3.0",
    "description": """
# Document Intelligence & Parsing Center API

The Document Intelligence & Parsing Center (DIPC) API provides comprehensive document processing capabilities using multi-modal Large Language Models (LLMs). This API enables developers to extract structured information from various document formats including PDFs, images, and ZIP archives.

## Key Features

- **Multi-format Support**: Process PDFs, images, text files, and ZIP archives
- **Batch Processing**: Handle multiple documents simultaneously through ZIP archives
- **Cost Management**: Built-in cost estimation and limiting capabilities
- **Flexible Storage**: Choose between permanent and temporary storage policies
- **Vectorization**: Optional vector database storage for semantic search
- **Real-time Monitoring**: Track processing status and progress in real-time

## Authentication

Currently, the API uses user-based identification through the `user_id` parameter. Future versions will include API key authentication.

## Rate Limiting

The API implements rate limiting to ensure fair usage:
- 100 requests per minute per user for task creation
- 1000 requests per minute per user for status checks
- 10 concurrent file uploads per user

## Error Handling

All API endpoints return structured error responses with the following format:

```json
{
  "error_code": "ERROR_TYPE",
  "error_message": "Human-readable error description",
  "details": {
    "additional": "context-specific information"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_abc123"
}
```

## Webhooks (Coming Soon)

Future versions will support webhook notifications for task completion and status updates.
    """,
    "contact": {
        "name": "DIPC Support",
        "email": "support@dipc.example.com"
    },
    "license": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
}

# OpenAPI tags for endpoint organization
OPENAPI_TAGS = [
    {
        "name": "Tasks",
        "description": "Document processing task management endpoints"
    },
    {
        "name": "Upload",
        "description": "File upload and storage management endpoints"
    },
    {
        "name": "Health",
        "description": "System health and monitoring endpoints"
    },
    {
        "name": "Admin",
        "description": "Administrative endpoints (future)"
    }
]

# Common response schemas
COMMON_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"},
                        "details": {"type": "object"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "request_id": {"type": "string"}
                    }
                },
                "example": {
                    "error_code": "INVALID_REQUEST",
                    "error_message": "Invalid request parameters",
                    "details": {"field": "file_urls", "issue": "cannot be empty"},
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "req_abc123"
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"}
                    }
                },
                "example": {
                    "error_code": "UNAUTHORIZED",
                    "error_message": "Authentication required"
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"}
                    }
                },
                "example": {
                    "error_code": "TASK_NOT_FOUND",
                    "error_message": "Task with specified ID not found"
                }
            }
        }
    },
    429: {
        "description": "Rate Limited",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"},
                        "retry_after": {"type": "integer"}
                    }
                },
                "example": {
                    "error_code": "RATE_LIMITED",
                    "error_message": "Rate limit exceeded",
                    "retry_after": 60
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"},
                        "request_id": {"type": "string"}
                    }
                },
                "example": {
                    "error_code": "INTERNAL_ERROR",
                    "error_message": "An unexpected error occurred",
                    "request_id": "req_abc123"
                }
            }
        }
    }
}

# Example request/response payloads
EXAMPLE_PAYLOADS = {
    "create_task_request": {
        "file_urls": [
            "https://storage.example.com/document1.pdf",
            "https://storage.example.com/archive.zip"
        ],
        "user_id": "user-123",
        "options": {
            "enable_vectorization": True,
            "storage_policy": "permanent",
            "max_cost_limit": 10.0
        }
    },
    "create_task_response": {
        "task_id": "task-abc123",
        "status": "pending",
        "created_at": "2024-01-15T10:30:00Z",
        "estimated_cost": 2.50,
        "options": {
            "enable_vectorization": True,
            "storage_policy": "permanent"
        }
    },
    "task_status_response": {
        "task_id": "task-abc123",
        "status": "processing",
        "progress": 65,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:32:15Z",
        "estimated_completion": "2024-01-15T10:35:00Z",
        "subtasks": [
            {
                "subtask_id": "subtask-1",
                "status": "completed",
                "file_name": "document1.pdf"
            },
            {
                "subtask_id": "subtask-2", 
                "status": "processing",
                "file_name": "document2.pdf"
            }
        ]
    },
    "task_results_response": {
        "task_id": "task-abc123",
        "status": "completed",
        "results": {
            "extracted_content": {
                "title": "Annual Financial Report 2023",
                "content": "This report summarizes the financial performance...",
                "metadata": {
                    "pages": 45,
                    "language": "en",
                    "document_type": "financial_report"
                },
                "sections": [
                    {
                        "title": "Executive Summary",
                        "content": "Key highlights of the year...",
                        "page_range": [1, 3]
                    }
                ]
            },
            "confidence_score": 0.95,
            "processing_time": 12.5,
            "token_usage": {
                "prompt_tokens": 15000,
                "completion_tokens": 2500,
                "total_tokens": 17500,
                "estimated_cost": 2.45
            }
        },
        "vector_storage": {
            "enabled": True,
            "collection_id": "collection-xyz789",
            "vector_count": 156
        },
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:32:30Z"
    },
    "presigned_url_request": {
        "filename": "financial-report-2023.pdf",
        "content_type": "application/pdf",
        "user_id": "user-123",
        "file_size": 5242880
    },
    "presigned_url_response": {
        "upload_url": "https://storage.example.com/presigned-upload-url?signature=...",
        "file_id": "file-def456",
        "expires_at": "2024-01-15T11:30:00Z",
        "max_file_size": 104857600,
        "allowed_content_types": [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "application/zip",
            "text/plain"
        ]
    }
}

def get_openapi_config() -> Dict[str, Any]:
    """Get complete OpenAPI configuration."""
    return {
        "openapi": "3.0.2",
        "info": OPENAPI_METADATA,
        "tags": OPENAPI_TAGS,
        "servers": [
            {
                "url": "https://api.dipc.example.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.dipc.example.com", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ],
        "components": {
            "responses": COMMON_RESPONSES,
            "examples": EXAMPLE_PAYLOADS
        }
    }