#!/usr/bin/env python3
"""
DIPC API Usage Examples

This script demonstrates how to use the DIPC API for document processing.
It includes examples for uploading files, creating tasks, and retrieving results.
"""

import requests
import json
import time
import os
from typing import Dict, Any, Optional
from pathlib import Path
import argparse

class DIPCClient:
    """Client for interacting with DIPC API."""
    
    def __init__(self, base_url: str = "http://localhost:38100"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/v1/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def get_presigned_url(self, filename: str, file_size: int, 
                         content_type: str = "application/pdf") -> Dict[str, Any]:
        """Get a presigned URL for file upload."""
        payload = {
            "filename": filename,
            "file_size": file_size,
            "content_type": content_type
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/upload/presigned-url",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """Upload a file to DIPC storage."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        file_size = file_path.stat().st_size
        content_type = self._get_content_type(file_path.suffix)
        
        # Get presigned URL
        presigned_response = self.get_presigned_url(
            file_path.name, file_size, content_type
        )
        
        if "error" in presigned_response:
            return presigned_response
        
        # Upload file using presigned URL
        try:
            with open(file_path, 'rb') as f:
                upload_response = requests.put(
                    presigned_response["upload_url"],
                    data=f,
                    headers={"Content-Type": content_type}
                )
                upload_response.raise_for_status()
            
            return {
                "file_url": presigned_response["file_url"],
                "file_id": presigned_response["file_id"],
                "filename": file_path.name
            }
        except requests.RequestException as e:
            return {"error": f"Upload failed: {str(e)}"}
    
    def create_task(self, file_url: str, task_type: str = "document_parsing", 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a processing task."""
        if options is None:
            options = {
                "extract_text": True,
                "extract_tables": True,
                "extract_images": False,
                "extract_metadata": True
            }
        
        payload = {
            "file_url": file_url,
            "task_type": task_type,
            "options": options
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/tasks",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task."""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/tasks/{task_id}/status"
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get the result of a completed task."""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/tasks/{task_id}/result"
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def wait_for_task(self, task_id: str, max_wait: int = 300, 
                     poll_interval: int = 5) -> Dict[str, Any]:
        """Wait for a task to complete."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = self.get_task_status(task_id)
            
            if "error" in status:
                return status
            
            if status.get("status") in ["completed", "failed"]:
                return status
            
            print(f"Task {task_id} status: {status.get('status', 'unknown')}")
            time.sleep(poll_interval)
        
        return {"error": "Task timeout", "status": "timeout"}
    
    def process_document(self, file_path: str, options: Dict[str, Any] = None,
                        wait: bool = True) -> Dict[str, Any]:
        """Complete document processing workflow."""
        print(f"Processing document: {file_path}")
        
        # Upload file
        print("Uploading file...")
        upload_result = self.upload_file(file_path)
        if "error" in upload_result:
            return upload_result
        
        print(f"File uploaded: {upload_result['file_id']}")
        
        # Create task
        print("Creating processing task...")
        task_result = self.create_task(upload_result["file_url"], options=options)
        if "error" in task_result:
            return task_result
        
        task_id = task_result.get("task_id")
        print(f"Task created: {task_id}")
        
        if not wait:
            return task_result
        
        # Wait for completion
        print("Waiting for task completion...")
        status = self.wait_for_task(task_id)
        if "error" in status:
            return status
        
        if status.get("status") == "completed":
            print("Task completed successfully!")
            return self.get_task_result(task_id)
        else:
            return {"error": "Task failed", "status": status}
    
    def _get_content_type(self, extension: str) -> str:
        """Get content type from file extension."""
        content_types = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".zip": "application/zip"
        }
        return content_types.get(extension.lower(), "application/octet-stream")


def example_health_check():
    """Example: Check API health."""
    print("=== Health Check Example ===")
    
    client = DIPCClient()
    health = client.health_check()
    
    print(f"Health check result: {json.dumps(health, indent=2)}")
    print()


def example_single_document():
    """Example: Process a single document."""
    print("=== Single Document Processing Example ===")
    
    # Create a sample text file
    sample_file = Path("sample_document.txt")
    sample_file.write_text("""
    Sample Document for DIPC Processing
    
    This is a test document that demonstrates DIPC's capabilities.
    
    Key Information:
    - Document Type: Test Document
    - Created: 2024
    - Purpose: API Example
    
    Table Data:
    Name        | Age | City
    John Doe    | 30  | New York
    Jane Smith  | 25  | San Francisco
    Bob Johnson | 35  | Chicago
    
    This document contains both text and structured data that DIPC can extract.
    """)
    
    try:
        client = DIPCClient()
        result = client.process_document(str(sample_file))
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Processing result: {json.dumps(result, indent=2)}")
            
    finally:
        # Clean up
        if sample_file.exists():
            sample_file.unlink()
    
    print()


def example_custom_options():
    """Example: Process document with custom options."""
    print("=== Custom Processing Options Example ===")
    
    # Create a sample document
    sample_file = Path("invoice_sample.txt")
    sample_file.write_text("""
    INVOICE #12345
    Date: 2024-01-15
    
    Bill To:
    John Doe
    123 Main St
    Anytown, ST 12345
    
    Description         | Qty | Unit Price | Total
    Widget A           | 2   | $10.00     | $20.00
    Widget B           | 1   | $15.00     | $15.00
    Service Fee        | 1   | $5.00      | $5.00
    
    Subtotal: $40.00
    Tax: $4.00
    Total: $44.00
    
    Payment Terms: Net 30
    """)
    
    try:
        client = DIPCClient()
        
        # Custom processing options
        options = {
            "extract_text": True,
            "extract_tables": True,
            "extract_images": False,
            "extract_metadata": True,
            "custom_instructions": "Focus on extracting invoice information including customer details, line items, and totals."
        }
        
        result = client.process_document(str(sample_file), options=options)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Processing result: {json.dumps(result, indent=2)}")
            
    finally:
        # Clean up
        if sample_file.exists():
            sample_file.unlink()
    
    print()


def example_async_processing():
    """Example: Asynchronous document processing."""
    print("=== Asynchronous Processing Example ===")
    
    # Create a sample document
    sample_file = Path("async_sample.txt")
    sample_file.write_text("This is a sample document for async processing.")
    
    try:
        client = DIPCClient()
        
        # Start processing without waiting
        result = client.process_document(str(sample_file), wait=False)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        task_id = result.get("task_id")
        print(f"Task started: {task_id}")
        
        # Poll for status
        while True:
            status = client.get_task_status(task_id)
            print(f"Current status: {status.get('status', 'unknown')}")
            
            if status.get("status") in ["completed", "failed"]:
                break
            
            time.sleep(2)
        
        # Get final result
        if status.get("status") == "completed":
            final_result = client.get_task_result(task_id)
            print(f"Final result: {json.dumps(final_result, indent=2)}")
        else:
            print(f"Task failed: {status}")
            
    finally:
        # Clean up
        if sample_file.exists():
            sample_file.unlink()
    
    print()


def example_batch_processing():
    """Example: Process multiple documents."""
    print("=== Batch Processing Example ===")
    
    # Create sample documents
    documents = []
    for i in range(3):
        doc_file = Path(f"batch_doc_{i+1}.txt")
        doc_file.write_text(f"""
        Document {i+1}
        
        This is batch document number {i+1}.
        It contains sample content for testing batch processing.
        
        Data point: {i+1}
        Status: Active
        """)
        documents.append(doc_file)
    
    try:
        client = DIPCClient()
        tasks = []
        
        # Start all tasks
        for doc_file in documents:
            print(f"Starting task for {doc_file.name}")
            result = client.process_document(str(doc_file), wait=False)
            
            if "error" in result:
                print(f"Error starting task for {doc_file.name}: {result['error']}")
                continue
            
            tasks.append({
                "task_id": result.get("task_id"),
                "filename": doc_file.name
            })
        
        # Wait for all tasks to complete
        print(f"Waiting for {len(tasks)} tasks to complete...")
        
        for task in tasks:
            status = client.wait_for_task(task["task_id"])
            print(f"Task {task['task_id']} ({task['filename']}): {status.get('status', 'unknown')}")
            
            if status.get("status") == "completed":
                result = client.get_task_result(task["task_id"])
                print(f"Result preview: {str(result)[:100]}...")
            
    finally:
        # Clean up
        for doc_file in documents:
            if doc_file.exists():
                doc_file.unlink()
    
    print()


def main():
    """Main function to run examples."""
    parser = argparse.ArgumentParser(description="DIPC API Examples")
    parser.add_argument("--api-url", default="http://localhost:38100",
                       help="DIPC API URL")
    parser.add_argument("--example", choices=["health", "single", "custom", "async", "batch", "all"],
                       default="all", help="Which example to run")
    args = parser.parse_args()
    
    print("DIPC API Usage Examples")
    print("=" * 50)
    
    # Update base URL
    global DIPCClient
    original_init = DIPCClient.__init__
    def new_init(self, base_url=args.api_url):
        original_init(self, base_url)
    DIPCClient.__init__ = new_init
    
    # Run examples
    if args.example in ["health", "all"]:
        example_health_check()
    
    if args.example in ["single", "all"]:
        example_single_document()
    
    if args.example in ["custom", "all"]:
        example_custom_options()
    
    if args.example in ["async", "all"]:
        example_async_processing()
    
    if args.example in ["batch", "all"]:
        example_batch_processing()
    
    print("Examples completed!")


if __name__ == "__main__":
    main()