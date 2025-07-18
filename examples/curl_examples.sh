#!/bin/bash

# DIPC API Usage Examples (curl)
# This script demonstrates how to use the DIPC API with curl commands

set -e

# Configuration
API_URL="http://localhost:38100"
SAMPLE_FILE="sample_document.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Helper function to check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install jq for better JSON parsing."
        echo "Install: sudo apt-get install jq (Ubuntu/Debian) or brew install jq (macOS)"
        exit 1
    fi
}

# Helper function to create a sample document
create_sample_document() {
    cat > "$SAMPLE_FILE" << 'EOF'
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
EOF
}

# Example 1: Health Check
example_health_check() {
    print_header "Health Check Example"
    
    echo "Checking API health..."
    
    response=$(curl -s -w "\n%{http_code}" "$API_URL/v1/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "API is healthy"
        echo "Response: $body" | jq '.' 2>/dev/null || echo "Response: $body"
    else
        print_error "API health check failed (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 2: Get Presigned URL
example_get_presigned_url() {
    print_header "Get Presigned URL Example"
    
    file_size=$(wc -c < "$SAMPLE_FILE")
    
    echo "Getting presigned URL for file upload..."
    echo "File: $SAMPLE_FILE"
    echo "Size: $file_size bytes"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"filename\": \"$SAMPLE_FILE\",
            \"file_size\": $file_size,
            \"content_type\": \"text/plain\"
        }" \
        "$API_URL/v1/upload/presigned-url")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Presigned URL obtained"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        
        # Extract values for next steps
        upload_url=$(echo "$body" | jq -r '.upload_url' 2>/dev/null)
        file_url=$(echo "$body" | jq -r '.file_url' 2>/dev/null)
        file_id=$(echo "$body" | jq -r '.file_id' 2>/dev/null)
        
        echo
        echo "Upload URL: $upload_url"
        echo "File URL: $file_url"
        echo "File ID: $file_id"
        
        # Store for other examples
        echo "$upload_url" > .upload_url
        echo "$file_url" > .file_url
        echo "$file_id" > .file_id
    else
        print_error "Failed to get presigned URL (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 3: Upload File
example_upload_file() {
    print_header "File Upload Example"
    
    if [ ! -f .upload_url ]; then
        print_error "No upload URL available. Run presigned URL example first."
        return 1
    fi
    
    upload_url=$(cat .upload_url)
    
    echo "Uploading file to presigned URL..."
    
    response=$(curl -s -w "\n%{http_code}" \
        -X PUT \
        -H "Content-Type: text/plain" \
        --data-binary "@$SAMPLE_FILE" \
        "$upload_url")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "File uploaded successfully"
    else
        print_error "File upload failed (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 4: Create Processing Task
example_create_task() {
    print_header "Create Processing Task Example"
    
    if [ ! -f .file_url ]; then
        print_error "No file URL available. Run file upload example first."
        return 1
    fi
    
    file_url=$(cat .file_url)
    
    echo "Creating processing task..."
    echo "File URL: $file_url"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"file_url\": \"$file_url\",
            \"task_type\": \"document_parsing\",
            \"options\": {
                \"extract_text\": true,
                \"extract_tables\": true,
                \"extract_images\": false,
                \"extract_metadata\": true
            }
        }" \
        "$API_URL/v1/tasks")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        print_success "Task created successfully"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        
        # Extract task ID
        task_id=$(echo "$body" | jq -r '.task_id' 2>/dev/null)
        echo "Task ID: $task_id"
        
        # Store for other examples
        echo "$task_id" > .task_id
    else
        print_error "Failed to create task (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 5: Check Task Status
example_check_status() {
    print_header "Check Task Status Example"
    
    if [ ! -f .task_id ]; then
        print_error "No task ID available. Run create task example first."
        return 1
    fi
    
    task_id=$(cat .task_id)
    
    echo "Checking task status..."
    echo "Task ID: $task_id"
    
    response=$(curl -s -w "\n%{http_code}" \
        "$API_URL/v1/tasks/$task_id/status")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Task status retrieved"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        
        # Extract status
        status=$(echo "$body" | jq -r '.status' 2>/dev/null)
        echo "Current status: $status"
    else
        print_error "Failed to get task status (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 6: Wait for Task Completion
example_wait_for_completion() {
    print_header "Wait for Task Completion Example"
    
    if [ ! -f .task_id ]; then
        print_error "No task ID available. Run create task example first."
        return 1
    fi
    
    task_id=$(cat .task_id)
    max_attempts=30
    attempt=0
    
    echo "Waiting for task completion..."
    echo "Task ID: $task_id"
    
    while [ $attempt -lt $max_attempts ]; do
        response=$(curl -s -w "\n%{http_code}" \
            "$API_URL/v1/tasks/$task_id/status")
        
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n -1)
        
        if [ "$http_code" = "200" ]; then
            status=$(echo "$body" | jq -r '.status' 2>/dev/null)
            echo "Status: $status"
            
            if [ "$status" = "completed" ]; then
                print_success "Task completed successfully"
                break
            elif [ "$status" = "failed" ]; then
                print_error "Task failed"
                echo "$body" | jq '.' 2>/dev/null || echo "$body"
                break
            fi
        else
            print_error "Failed to get task status (HTTP $http_code)"
            break
        fi
        
        attempt=$((attempt + 1))
        echo "Waiting... (attempt $attempt/$max_attempts)"
        sleep 5
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Task did not complete within timeout"
    fi
    
    echo
}

# Example 7: Get Task Result
example_get_result() {
    print_header "Get Task Result Example"
    
    if [ ! -f .task_id ]; then
        print_error "No task ID available. Run create task example first."
        return 1
    fi
    
    task_id=$(cat .task_id)
    
    echo "Getting task result..."
    echo "Task ID: $task_id"
    
    response=$(curl -s -w "\n%{http_code}" \
        "$API_URL/v1/tasks/$task_id/result")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Task result retrieved"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        print_error "Failed to get task result (HTTP $http_code)"
        echo "Response: $body"
    fi
    
    echo
}

# Example 8: Complete Workflow
example_complete_workflow() {
    print_header "Complete Workflow Example"
    
    echo "Running complete document processing workflow..."
    
    # Create sample document
    create_sample_document
    
    # Get presigned URL
    example_get_presigned_url
    
    # Upload file
    example_upload_file
    
    # Create task
    example_create_task
    
    # Wait for completion
    example_wait_for_completion
    
    # Get result
    example_get_result
    
    print_success "Complete workflow finished"
    echo
}

# Example 9: Custom Processing Options
example_custom_options() {
    print_header "Custom Processing Options Example"
    
    # Create invoice sample
    cat > "invoice_sample.txt" << 'EOF'
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
EOF
    
    file_size=$(wc -c < "invoice_sample.txt")
    
    echo "Processing invoice with custom options..."
    
    # Get presigned URL
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"filename\": \"invoice_sample.txt\",
            \"file_size\": $file_size,
            \"content_type\": \"text/plain\"
        }" \
        "$API_URL/v1/upload/presigned-url")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        upload_url=$(echo "$body" | jq -r '.upload_url' 2>/dev/null)
        file_url=$(echo "$body" | jq -r '.file_url' 2>/dev/null)
        
        # Upload file
        curl -s -X PUT \
            -H "Content-Type: text/plain" \
            --data-binary "@invoice_sample.txt" \
            "$upload_url"
        
        # Create task with custom options
        response=$(curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{
                \"file_url\": \"$file_url\",
                \"task_type\": \"document_parsing\",
                \"options\": {
                    \"extract_text\": true,
                    \"extract_tables\": true,
                    \"extract_images\": false,
                    \"extract_metadata\": true,
                    \"custom_instructions\": \"Focus on extracting invoice information including customer details, line items, and totals.\"
                }
            }" \
            "$API_URL/v1/tasks")
        
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n -1)
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
            print_success "Invoice processing task created"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        else
            print_error "Failed to create invoice processing task"
            echo "Response: $body"
        fi
    fi
    
    # Clean up
    rm -f "invoice_sample.txt"
    echo
}

# Cleanup function
cleanup() {
    rm -f "$SAMPLE_FILE" .upload_url .file_url .file_id .task_id
}

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS] [EXAMPLES]"
    echo
    echo "OPTIONS:"
    echo "  --api-url URL    API base URL (default: http://localhost:38100)"
    echo "  --help           Show this help message"
    echo
    echo "EXAMPLES:"
    echo "  health           Health check example"
    echo "  presigned        Get presigned URL example"
    echo "  upload           File upload example"
    echo "  task             Create task example"
    echo "  status           Check task status example"
    echo "  wait             Wait for completion example"
    echo "  result           Get task result example"
    echo "  workflow         Complete workflow example"
    echo "  custom           Custom processing options example"
    echo "  all              Run all examples (default)"
    echo
    echo "EXAMPLES:"
    echo "  $0                           # Run all examples"
    echo "  $0 health                    # Run health check only"
    echo "  $0 workflow                  # Run complete workflow"
    echo "  $0 --api-url http://localhost:8080 workflow"
}

# Main function
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --api-url)
                API_URL="$2"
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                EXAMPLES="$EXAMPLES $1"
                shift
                ;;
        esac
    done
    
    # Default to all examples if none specified
    if [ -z "$EXAMPLES" ]; then
        EXAMPLES="all"
    fi
    
    echo "DIPC API Usage Examples (curl)"
    echo "API URL: $API_URL"
    echo "="
    echo
    
    # Check prerequisites
    check_jq
    
    # Create sample document
    create_sample_document
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run examples
    for example in $EXAMPLES; do
        case $example in
            health)
                example_health_check
                ;;
            presigned)
                example_get_presigned_url
                ;;
            upload)
                example_upload_file
                ;;
            task)
                example_create_task
                ;;
            status)
                example_check_status
                ;;
            wait)
                example_wait_for_completion
                ;;
            result)
                example_get_result
                ;;
            workflow)
                example_complete_workflow
                ;;
            custom)
                example_custom_options
                ;;
            all)
                example_health_check
                example_complete_workflow
                example_custom_options
                ;;
            *)
                print_error "Unknown example: $example"
                usage
                exit 1
                ;;
        esac
    done
    
    print_success "All examples completed!"
}

# Run main function
main "$@"