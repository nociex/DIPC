# DIPC API Examples

This directory contains comprehensive examples demonstrating how to use the DIPC API in different programming languages and tools.

## 📁 Files Overview

| File | Description | Language/Tool |
|------|-------------|---------------|
| `api_examples.py` | Complete Python client with examples | Python |
| `api_examples.js` | Node.js client with examples | JavaScript |
| `curl_examples.sh` | Shell script with curl examples | Bash/curl |
| `README.md` | This documentation file | Markdown |

## 🚀 Quick Start

### Prerequisites

- DIPC running (see [QUICK_START.md](../QUICK_START.md))
- Programming language runtime (Python 3.7+, Node.js 14+, or curl)
- API access (localhost:38100 by default)

### Python Examples

```bash
# Install dependencies
pip install requests

# Run all examples
python api_examples.py

# Run specific example
python api_examples.py --example single

# Use custom API URL
python api_examples.py --api-url http://your-api-server:38100
```

### JavaScript Examples

```bash
# Install dependencies
npm install axios form-data

# Run all examples
node api_examples.js

# Run specific example
node api_examples.js --example=single

# Use custom API URL
node api_examples.js --api-url=http://your-api-server:38100
```

### cURL Examples

```bash
# Make executable
chmod +x curl_examples.sh

# Run all examples
./curl_examples.sh

# Run specific example
./curl_examples.sh workflow

# Use custom API URL
./curl_examples.sh --api-url http://your-api-server:38100 workflow
```

## 📚 Available Examples

### 1. Health Check
Tests if the API is running and responsive.

**Python:**
```python
client = DIPCClient()
health = client.health_check()
print(health)
```

**JavaScript:**
```javascript
const client = new DIPCClient();
const health = await client.healthCheck();
console.log(health);
```

**cURL:**
```bash
curl http://localhost:38100/v1/health
```

### 2. Single Document Processing
Upload and process a single document.

**Key Steps:**
1. Create a sample document
2. Upload to DIPC storage
3. Create processing task
4. Wait for completion
5. Retrieve results

### 3. Custom Processing Options
Process documents with specific extraction options.

**Example Options:**
```json
{
  "extract_text": true,
  "extract_tables": true,
  "extract_images": false,
  "extract_metadata": true,
  "custom_instructions": "Focus on extracting invoice information"
}
```

### 4. Asynchronous Processing
Start processing and poll for completion separately.

**Benefits:**
- Non-blocking processing
- Better for long-running tasks
- Allows monitoring progress

### 5. Batch Processing
Process multiple documents simultaneously.

**Features:**
- Parallel task creation
- Progress monitoring
- Bulk result retrieval

## 🔧 API Client Classes

### Python Client (`DIPCClient`)

```python
class DIPCClient:
    def __init__(self, base_url="http://localhost:38100"):
        # Initialize client
    
    def health_check(self) -> Dict[str, Any]:
        # Check API health
    
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        # Upload file to storage
    
    def create_task(self, file_url: str, options: Dict = None) -> Dict[str, Any]:
        # Create processing task
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        # Get task status
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        # Get task result
    
    def process_document(self, file_path: str, options: Dict = None, wait: bool = True) -> Dict[str, Any]:
        # Complete workflow
```

### JavaScript Client (`DIPCClient`)

```javascript
class DIPCClient {
    constructor(baseUrl = 'http://localhost:38100') {
        // Initialize client
    }
    
    async healthCheck() {
        // Check API health
    }
    
    async uploadFile(filePath) {
        // Upload file to storage
    }
    
    async createTask(fileUrl, options = null) {
        // Create processing task
    }
    
    async getTaskStatus(taskId) {
        // Get task status
    }
    
    async getTaskResult(taskId) {
        // Get task result
    }
    
    async processDocument(filePath, options = null, wait = true) {
        // Complete workflow
    }
}
```

## 🛠️ Usage Patterns

### Basic Document Processing

```python
# Python
client = DIPCClient()
result = client.process_document("document.pdf")
print(result)
```

```javascript
// JavaScript
const client = new DIPCClient();
const result = await client.processDocument('document.pdf');
console.log(result);
```

```bash
# cURL
./curl_examples.sh workflow
```

### Custom Processing

```python
# Python
options = {
    "extract_text": True,
    "extract_tables": True,
    "custom_instructions": "Focus on financial data"
}
result = client.process_document("invoice.pdf", options)
```

```javascript
// JavaScript
const options = {
    extract_text: true,
    extract_tables: true,
    custom_instructions: "Focus on financial data"
};
const result = await client.processDocument('invoice.pdf', options);
```

### Async Processing

```python
# Python
# Start processing
task_result = client.process_document("document.pdf", wait=False)
task_id = task_result['task_id']

# Check status later
status = client.get_task_status(task_id)
if status['status'] == 'completed':
    result = client.get_task_result(task_id)
```

```javascript
// JavaScript
// Start processing
const taskResult = await client.processDocument('document.pdf', null, false);
const taskId = taskResult.task_id;

// Check status later
const status = await client.getTaskStatus(taskId);
if (status.status === 'completed') {
    const result = await client.getTaskResult(taskId);
}
```

## 📊 Response Formats

### Task Creation Response
```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "pending",
  "file_url": "https://storage/file.pdf",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Task Status Response
```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "completed",
  "progress": 100,
  "estimated_cost": 0.05,
  "actual_cost": 0.03,
  "processing_time": 45.2,
  "updated_at": "2024-01-01T00:01:00Z"
}
```

### Task Result Response
```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "result": {
    "text": "Extracted text content...",
    "tables": [
      {
        "page": 1,
        "data": [["Header1", "Header2"], ["Data1", "Data2"]]
      }
    ],
    "metadata": {
      "pages": 1,
      "language": "en",
      "document_type": "invoice"
    }
  },
  "metrics": {
    "processing_time": 45.2,
    "tokens_used": 1500,
    "cost": 0.03
  }
}
```

## 🔍 Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Connection refused | API not running | Start DIPC services |
| 401 Unauthorized | Invalid API key | Check API key configuration |
| 413 Payload too large | File too big | Reduce file size |
| 429 Too many requests | Rate limit exceeded | Slow down requests |
| 500 Internal server error | Server issue | Check logs |

### Error Response Format
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional information"
  }
}
```

### Python Error Handling
```python
try:
    result = client.process_document("document.pdf")
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Success!")
except Exception as e:
    print(f"Exception: {str(e)}")
```

### JavaScript Error Handling
```javascript
try {
    const result = await client.processDocument('document.pdf');
    if (result.error) {
        console.error(`Error: ${result.error}`);
    } else {
        console.log('Success!');
    }
} catch (error) {
    console.error(`Exception: ${error.message}`);
}
```

## 🧪 Testing

### Unit Tests
```python
# Python
import unittest
from api_examples import DIPCClient

class TestDIPCClient(unittest.TestCase):
    def setUp(self):
        self.client = DIPCClient()
    
    def test_health_check(self):
        result = self.client.health_check()
        self.assertIn('status', result)
```

### Integration Tests
```python
# Python
def test_complete_workflow():
    client = DIPCClient()
    
    # Create test document
    with open('test.txt', 'w') as f:
        f.write('Test content')
    
    # Process document
    result = client.process_document('test.txt')
    
    # Verify result
    assert 'result' in result
    assert result['result']['text'] == 'Test content'
```

## 📈 Performance Tips

### 1. Batch Processing
Process multiple documents in parallel:

```python
# Python
import concurrent.futures

def process_doc(file_path):
    return client.process_document(file_path, wait=False)

# Process multiple files
files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(process_doc, file) for file in files]
    results = [future.result() for future in concurrent.futures.as_completed(futures)]
```

### 2. Connection Pooling
Reuse connections:

```python
# Python
import requests
from requests.adapters import HTTPAdapter

session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

### 3. Async/Await Pattern
For long-running tasks:

```python
# Python
async def process_large_document(file_path):
    # Start processing
    task_result = client.process_document(file_path, wait=False)
    task_id = task_result['task_id']
    
    # Poll for completion
    while True:
        status = client.get_task_status(task_id)
        if status['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(5)  # Wait 5 seconds
    
    return client.get_task_result(task_id)
```

## 🔧 Customization

### Custom Client Configuration

```python
# Python
class CustomDIPCClient(DIPCClient):
    def __init__(self, base_url, api_key=None):
        super().__init__(base_url)
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def custom_processing(self, file_path, template='invoice'):
        options = {
            'template': template,
            'extract_text': True,
            'extract_tables': True
        }
        return self.process_document(file_path, options)
```

### Custom Processing Options

```python
# Python
invoice_options = {
    'extract_text': True,
    'extract_tables': True,
    'extract_images': False,
    'custom_instructions': 'Extract invoice number, date, total amount, and line items',
    'output_format': 'structured',
    'language': 'en'
}

contract_options = {
    'extract_text': True,
    'extract_tables': False,
    'extract_images': True,
    'custom_instructions': 'Extract parties, dates, terms, and conditions',
    'output_format': 'markdown',
    'language': 'en'
}
```

## 📝 Contributing

To add new examples:

1. Follow the existing code style
2. Include error handling
3. Add documentation
4. Test with different file types
5. Update this README

## 📧 Support

If you encounter issues with the examples:

1. Check the [troubleshooting guide](../docs/troubleshooting.md)
2. Run the health check: `python ../dipc-health-check.py`
3. Check the logs: `docker-compose logs`
4. Open an issue on GitHub

## 📄 License

These examples are provided under the same license as the main DIPC project (MIT License).