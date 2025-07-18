#!/usr/bin/env node
/**
 * DIPC API Usage Examples (JavaScript/Node.js)
 * 
 * This script demonstrates how to use the DIPC API for document processing.
 * It includes examples for uploading files, creating tasks, and retrieving results.
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

class DIPCClient {
    constructor(baseUrl = 'http://localhost:38100') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    async healthCheck() {
        try {
            const response = await this.client.get('/v1/health');
            return response.data;
        } catch (error) {
            return { error: error.message, status: 'unhealthy' };
        }
    }

    async getPresignedUrl(filename, fileSize, contentType = 'application/pdf') {
        try {
            const response = await this.client.post('/v1/upload/presigned-url', {
                filename,
                file_size: fileSize,
                content_type: contentType
            });
            return response.data;
        } catch (error) {
            return { error: error.message };
        }
    }

    async uploadFile(filePath) {
        try {
            const stats = fs.statSync(filePath);
            const filename = path.basename(filePath);
            const contentType = this.getContentType(path.extname(filePath));

            // Get presigned URL
            const presignedResponse = await this.getPresignedUrl(filename, stats.size, contentType);
            
            if (presignedResponse.error) {
                return presignedResponse;
            }

            // Upload file using presigned URL
            const fileBuffer = fs.readFileSync(filePath);
            
            await axios.put(presignedResponse.upload_url, fileBuffer, {
                headers: {
                    'Content-Type': contentType,
                    'Content-Length': stats.size
                }
            });

            return {
                file_url: presignedResponse.file_url,
                file_id: presignedResponse.file_id,
                filename: filename
            };
        } catch (error) {
            return { error: `Upload failed: ${error.message}` };
        }
    }

    async createTask(fileUrl, taskType = 'document_parsing', options = null) {
        if (!options) {
            options = {
                extract_text: true,
                extract_tables: true,
                extract_images: false,
                extract_metadata: true
            };
        }

        try {
            const response = await this.client.post('/v1/tasks', {
                file_url: fileUrl,
                task_type: taskType,
                options: options
            });
            return response.data;
        } catch (error) {
            return { error: error.message };
        }
    }

    async getTaskStatus(taskId) {
        try {
            const response = await this.client.get(`/v1/tasks/${taskId}/status`);
            return response.data;
        } catch (error) {
            return { error: error.message };
        }
    }

    async getTaskResult(taskId) {
        try {
            const response = await this.client.get(`/v1/tasks/${taskId}/result`);
            return response.data;
        } catch (error) {
            return { error: error.message };
        }
    }

    async waitForTask(taskId, maxWait = 300, pollInterval = 5) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWait * 1000) {
            const status = await this.getTaskStatus(taskId);
            
            if (status.error) {
                return status;
            }
            
            if (['completed', 'failed'].includes(status.status)) {
                return status;
            }
            
            console.log(`Task ${taskId} status: ${status.status || 'unknown'}`);
            await this.sleep(pollInterval * 1000);
        }
        
        return { error: 'Task timeout', status: 'timeout' };
    }

    async processDocument(filePath, options = null, wait = true) {
        console.log(`Processing document: ${filePath}`);
        
        // Upload file
        console.log('Uploading file...');
        const uploadResult = await this.uploadFile(filePath);
        if (uploadResult.error) {
            return uploadResult;
        }
        
        console.log(`File uploaded: ${uploadResult.file_id}`);
        
        // Create task
        console.log('Creating processing task...');
        const taskResult = await this.createTask(uploadResult.file_url, 'document_parsing', options);
        if (taskResult.error) {
            return taskResult;
        }
        
        const taskId = taskResult.task_id;
        console.log(`Task created: ${taskId}`);
        
        if (!wait) {
            return taskResult;
        }
        
        // Wait for completion
        console.log('Waiting for task completion...');
        const status = await this.waitForTask(taskId);
        if (status.error) {
            return status;
        }
        
        if (status.status === 'completed') {
            console.log('Task completed successfully!');
            return await this.getTaskResult(taskId);
        } else {
            return { error: 'Task failed', status: status };
        }
    }

    getContentType(extension) {
        const contentTypes = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.zip': 'application/zip'
        };
        return contentTypes[extension.toLowerCase()] || 'application/octet-stream';
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

async function exampleHealthCheck() {
    console.log('=== Health Check Example ===');
    
    const client = new DIPCClient();
    const health = await client.healthCheck();
    
    console.log(`Health check result: ${JSON.stringify(health, null, 2)}`);
    console.log();
}

async function exampleSingleDocument() {
    console.log('=== Single Document Processing Example ===');
    
    // Create a sample text file
    const sampleFile = 'sample_document.txt';
    const sampleContent = `
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
    `;
    
    fs.writeFileSync(sampleFile, sampleContent);
    
    try {
        const client = new DIPCClient();
        const result = await client.processDocument(sampleFile);
        
        if (result.error) {
            console.log(`Error: ${result.error}`);
        } else {
            console.log(`Processing result: ${JSON.stringify(result, null, 2)}`);
        }
    } finally {
        // Clean up
        if (fs.existsSync(sampleFile)) {
            fs.unlinkSync(sampleFile);
        }
    }
    
    console.log();
}

async function exampleCustomOptions() {
    console.log('=== Custom Processing Options Example ===');
    
    // Create a sample document
    const sampleFile = 'invoice_sample.txt';
    const sampleContent = `
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
    `;
    
    fs.writeFileSync(sampleFile, sampleContent);
    
    try {
        const client = new DIPCClient();
        
        // Custom processing options
        const options = {
            extract_text: true,
            extract_tables: true,
            extract_images: false,
            extract_metadata: true,
            custom_instructions: 'Focus on extracting invoice information including customer details, line items, and totals.'
        };
        
        const result = await client.processDocument(sampleFile, options);
        
        if (result.error) {
            console.log(`Error: ${result.error}`);
        } else {
            console.log(`Processing result: ${JSON.stringify(result, null, 2)}`);
        }
    } finally {
        // Clean up
        if (fs.existsSync(sampleFile)) {
            fs.unlinkSync(sampleFile);
        }
    }
    
    console.log();
}

async function exampleAsyncProcessing() {
    console.log('=== Asynchronous Processing Example ===');
    
    // Create a sample document
    const sampleFile = 'async_sample.txt';
    const sampleContent = 'This is a sample document for async processing.';
    
    fs.writeFileSync(sampleFile, sampleContent);
    
    try {
        const client = new DIPCClient();
        
        // Start processing without waiting
        const result = await client.processDocument(sampleFile, null, false);
        
        if (result.error) {
            console.log(`Error: ${result.error}`);
            return;
        }
        
        const taskId = result.task_id;
        console.log(`Task started: ${taskId}`);
        
        // Poll for status
        while (true) {
            const status = await client.getTaskStatus(taskId);
            console.log(`Current status: ${status.status || 'unknown'}`);
            
            if (['completed', 'failed'].includes(status.status)) {
                break;
            }
            
            await client.sleep(2000);
        }
        
        // Get final result
        const finalStatus = await client.getTaskStatus(taskId);
        if (finalStatus.status === 'completed') {
            const finalResult = await client.getTaskResult(taskId);
            console.log(`Final result: ${JSON.stringify(finalResult, null, 2)}`);
        } else {
            console.log(`Task failed: ${JSON.stringify(finalStatus)}`);
        }
    } finally {
        // Clean up
        if (fs.existsSync(sampleFile)) {
            fs.unlinkSync(sampleFile);
        }
    }
    
    console.log();
}

async function exampleBatchProcessing() {
    console.log('=== Batch Processing Example ===');
    
    // Create sample documents
    const documents = [];
    for (let i = 0; i < 3; i++) {
        const docFile = `batch_doc_${i + 1}.txt`;
        const docContent = `
        Document ${i + 1}
        
        This is batch document number ${i + 1}.
        It contains sample content for testing batch processing.
        
        Data point: ${i + 1}
        Status: Active
        `;
        
        fs.writeFileSync(docFile, docContent);
        documents.push(docFile);
    }
    
    try {
        const client = new DIPCClient();
        const tasks = [];
        
        // Start all tasks
        for (const docFile of documents) {
            console.log(`Starting task for ${docFile}`);
            const result = await client.processDocument(docFile, null, false);
            
            if (result.error) {
                console.log(`Error starting task for ${docFile}: ${result.error}`);
                continue;
            }
            
            tasks.push({
                task_id: result.task_id,
                filename: docFile
            });
        }
        
        // Wait for all tasks to complete
        console.log(`Waiting for ${tasks.length} tasks to complete...`);
        
        for (const task of tasks) {
            const status = await client.waitForTask(task.task_id);
            console.log(`Task ${task.task_id} (${task.filename}): ${status.status || 'unknown'}`);
            
            if (status.status === 'completed') {
                const result = await client.getTaskResult(task.task_id);
                console.log(`Result preview: ${JSON.stringify(result).substring(0, 100)}...`);
            }
        }
    } finally {
        // Clean up
        for (const docFile of documents) {
            if (fs.existsSync(docFile)) {
                fs.unlinkSync(docFile);
            }
        }
    }
    
    console.log();
}

async function main() {
    const args = process.argv.slice(2);
    const apiUrl = args.find(arg => arg.startsWith('--api-url='))?.split('=')[1] || 'http://localhost:38100';
    const example = args.find(arg => arg.startsWith('--example='))?.split('=')[1] || 'all';
    
    console.log('DIPC API Usage Examples (JavaScript)');
    console.log('='.repeat(50));
    
    // Update base URL for all examples
    const originalConstructor = DIPCClient;
    global.DIPCClient = class extends originalConstructor {
        constructor(baseUrl = apiUrl) {
            super(baseUrl);
        }
    };
    
    try {
        // Run examples
        if (['health', 'all'].includes(example)) {
            await exampleHealthCheck();
        }
        
        if (['single', 'all'].includes(example)) {
            await exampleSingleDocument();
        }
        
        if (['custom', 'all'].includes(example)) {
            await exampleCustomOptions();
        }
        
        if (['async', 'all'].includes(example)) {
            await exampleAsyncProcessing();
        }
        
        if (['batch', 'all'].includes(example)) {
            await exampleBatchProcessing();
        }
        
        console.log('Examples completed!');
    } catch (error) {
        console.error('Error running examples:', error.message);
        process.exit(1);
    }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (error) => {
    console.error('Unhandled promise rejection:', error);
    process.exit(1);
});

if (require.main === module) {
    main();
}

module.exports = { DIPCClient };