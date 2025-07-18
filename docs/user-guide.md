# DIPC User Guide

Welcome to the Document Intelligence & Parsing Center (DIPC) User Guide. This comprehensive guide will help you get the most out of DIPC's document processing capabilities.

## Table of Contents

- [Getting Started](#getting-started)
- [Uploading Documents](#uploading-documents)
- [Processing Options](#processing-options)
- [Monitoring Tasks](#monitoring-tasks)
- [Understanding Results](#understanding-results)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing DIPC

1. Open your web browser and navigate to the DIPC application
2. You'll see the main dashboard with the file upload area
3. No registration is required - simply start uploading documents

### System Overview

DIPC processes documents through several stages:
1. **Upload**: Files are securely uploaded to cloud storage
2. **Queue**: Processing tasks are queued for execution
3. **Processing**: AI models extract structured information
4. **Storage**: Results are stored and optionally vectorized
5. **Retrieval**: Access your processed documents and results

## Uploading Documents

### Supported File Types

DIPC supports the following document formats:

| Format | Extension | Description |
|--------|-----------|-------------|
| PDF | `.pdf` | Portable Document Format files |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif` | Image files with text content |
| Text | `.txt` | Plain text files |
| Archives | `.zip` | ZIP archives containing multiple documents |

### Single Document Upload

1. **Drag and Drop**: Simply drag a file from your computer onto the upload area
2. **Click to Browse**: Click the upload area to open a file browser
3. **File Validation**: The system will validate file type and size
4. **Upload Progress**: Monitor upload progress with the progress bar

![Upload Interface](images/upload-interface.png)

### Batch Upload with ZIP Archives

For processing multiple documents simultaneously:

1. Create a ZIP archive containing your documents
2. Upload the ZIP file using the same upload process
3. DIPC will automatically extract and process each document
4. Monitor progress for the parent task and individual subtasks

**ZIP Archive Guidelines:**
- Maximum archive size: 100MB
- Maximum files per archive: 100
- Nested folders are supported
- Executable files are automatically filtered out

### Upload Limits

- **File Size**: Maximum 50MB per individual file
- **Archive Size**: Maximum 100MB per ZIP archive
- **Concurrent Uploads**: Up to 10 files simultaneously
- **Daily Limit**: 1000 files per user per day

## Processing Options

### Configuration Panel

Before starting processing, configure your options in the task configuration panel:

![Configuration Panel](images/config-panel.png)

### Vectorization

**Enable Vectorization**: Toggle this option to store processed content in a vector database for semantic search capabilities.

- **Enabled**: Content is converted to vector embeddings and stored
- **Disabled**: Only structured text extraction is performed
- **Cost Impact**: Vectorization increases processing cost by ~30%

### Storage Policy

Choose how long your processed files and results are stored:

#### Permanent Storage
- Files and results stored indefinitely
- Suitable for important documents you'll reference frequently
- Higher storage costs

#### Temporary Storage
- Files automatically deleted after 30 days
- Results retained for 90 days
- Cost-effective for one-time processing

### Cost Management

DIPC provides transparent cost estimation:

1. **Pre-processing Estimate**: See estimated costs before starting
2. **Cost Limits**: Set maximum spending limits per task
3. **Real-time Tracking**: Monitor actual costs during processing
4. **Detailed Breakdown**: View token usage and pricing details

![Cost Estimation](images/cost-estimation.png)

## Monitoring Tasks

### Task List View

The task list shows all your processing jobs:

![Task List](images/task-list.png)

### Task Status Indicators

| Status | Description | Actions Available |
|--------|-------------|-------------------|
| 🟡 Pending | Task queued for processing | Cancel |
| 🔵 Processing | Currently being processed | Monitor progress |
| 🟢 Completed | Successfully processed | View results, download |
| 🔴 Failed | Processing failed | View error details, retry |
| ⚫ Cancelled | Task was cancelled | Restart if needed |

### Real-time Updates

Tasks update automatically without page refresh:
- Progress bars show completion percentage
- Status changes are reflected immediately
- Estimated completion times are updated dynamically

### Batch Processing Monitoring

For ZIP archives, you'll see:
- **Parent Task**: Overall archive processing status
- **Subtasks**: Individual document processing status
- **Aggregate Progress**: Combined progress across all documents

## Understanding Results

### Results Viewer

Once processing completes, access your results through the Results Viewer:

![Results Viewer](images/results-viewer.png)

### Structured Data Output

DIPC extracts structured information including:

```json
{
  "extracted_content": {
    "title": "Document Title",
    "content": "Main document content...",
    "metadata": {
      "pages": 10,
      "language": "en",
      "document_type": "report"
    },
    "sections": [
      {
        "title": "Section 1",
        "content": "Section content...",
        "page_range": [1, 3]
      }
    ],
    "entities": [
      {
        "text": "John Doe",
        "type": "PERSON",
        "confidence": 0.95
      }
    ]
  },
  "confidence_score": 0.92,
  "processing_time": 15.3
}
```

### Data Fields Explained

#### Core Content
- **Title**: Extracted document title or filename
- **Content**: Main text content with formatting preserved
- **Metadata**: Document properties (pages, language, type)

#### Sections
- **Title**: Section headings
- **Content**: Section text content
- **Page Range**: Physical page numbers where section appears

#### Entities (when available)
- **Text**: Extracted entity text
- **Type**: Entity category (PERSON, ORG, DATE, etc.)
- **Confidence**: AI confidence score (0-1)

#### Processing Metrics
- **Confidence Score**: Overall extraction quality (0-1)
- **Processing Time**: Time taken in seconds
- **Token Usage**: API tokens consumed
- **Cost**: Actual processing cost

### Downloading Results

Multiple download options are available:

1. **JSON Format**: Complete structured data
2. **CSV Export**: Tabular data for spreadsheet applications
3. **Plain Text**: Extracted text content only
4. **Original File**: Download the original uploaded file

## Best Practices

### Document Preparation

For optimal results:

1. **Image Quality**: Use high-resolution scans (300 DPI minimum)
2. **File Format**: PDF files generally produce better results than images
3. **Text Clarity**: Ensure text is clearly readable
4. **Language**: Specify document language when possible

### Batch Processing Tips

1. **Organize Files**: Use descriptive filenames
2. **Archive Structure**: Organize files in logical folders within ZIP
3. **File Sizes**: Keep individual files under 20MB for faster processing
4. **Mixed Formats**: You can mix different file types in one archive

### Cost Optimization

1. **Disable Vectorization**: Turn off if you don't need semantic search
2. **Use Temporary Storage**: For one-time processing needs
3. **Set Cost Limits**: Prevent unexpected charges
4. **Batch Similar Documents**: Process related documents together

### Performance Tips

1. **Upload During Off-Peak Hours**: Faster processing times
2. **Monitor Queue Length**: Check system load before large batches
3. **Use Appropriate File Sizes**: Balance quality vs. processing time

## Troubleshooting

### Common Upload Issues

#### File Upload Fails
**Symptoms**: Upload progress stops or shows error
**Solutions**:
- Check file size (must be under 50MB)
- Verify file format is supported
- Ensure stable internet connection
- Try uploading one file at a time

#### ZIP Archive Rejected
**Symptoms**: ZIP file upload rejected with error
**Solutions**:
- Check archive size (must be under 100MB)
- Verify no executable files in archive
- Ensure file paths don't contain special characters
- Try creating a new ZIP archive

### Processing Issues

#### Task Stuck in Pending
**Symptoms**: Task remains in pending status for extended time
**Solutions**:
- Check system status page for outages
- Wait for queue to clear during high-load periods
- Contact support if stuck for over 30 minutes

#### Processing Failed
**Symptoms**: Task shows failed status with error message
**Common Causes & Solutions**:

| Error Type | Cause | Solution |
|------------|-------|----------|
| COST_LIMIT_EXCEEDED | Processing cost exceeds limit | Increase cost limit or reduce document size |
| INVALID_FILE_FORMAT | Unsupported file type | Convert to supported format |
| FILE_CORRUPTED | Damaged or corrupted file | Re-upload original file |
| TIMEOUT | Processing took too long | Split large documents into smaller parts |

#### Poor Extraction Quality
**Symptoms**: Low confidence scores or missing content
**Solutions**:
- Use higher quality source documents
- Try different file formats (PDF vs. image)
- Check document language settings
- Ensure text is clearly readable

### Results Issues

#### Missing Results
**Symptoms**: Completed task shows no results
**Solutions**:
- Refresh the page
- Check if results expired (temporary storage)
- Verify task actually completed successfully

#### Download Fails
**Symptoms**: Cannot download results or files
**Solutions**:
- Check internet connection
- Try different download format
- Clear browser cache
- Use different browser

### Getting Help

If you continue experiencing issues:

1. **Check Status Page**: Visit the system status page for known issues
2. **Review Error Messages**: Look for specific error codes and messages
3. **Contact Support**: Email support with:
   - Task ID
   - Error message
   - Steps to reproduce
   - Browser and operating system information

### Support Channels

- **Email**: support@dipc.example.com
- **Documentation**: [docs.dipc.example.com](https://docs.dipc.example.com)
- **Status Page**: [status.dipc.example.com](https://status.dipc.example.com)

## Advanced Features

### API Access

For developers, DIPC provides a REST API:
- **Documentation**: Available at `/docs` endpoint
- **Authentication**: API key required for programmatic access
- **Rate Limits**: Higher limits available for API users

### Webhook Notifications

Configure webhooks to receive notifications when tasks complete:
1. Go to Settings > Webhooks
2. Add your endpoint URL
3. Select events to monitor
4. Test webhook delivery

### Bulk Operations

For processing large document collections:
1. Use the bulk upload interface
2. Configure batch processing options
3. Monitor progress through the bulk operations dashboard
4. Download results in batch format

## Frequently Asked Questions

### General Questions

**Q: Is my data secure?**
A: Yes, all files are encrypted in transit and at rest. Documents are processed in isolated environments and automatically deleted according to your storage policy.

**Q: What languages are supported?**
A: DIPC supports over 50 languages including English, Spanish, French, German, Chinese, Japanese, and more.

**Q: Can I process handwritten documents?**
A: Yes, but results may vary depending on handwriting clarity. Printed text generally produces better results.

### Pricing Questions

**Q: How is pricing calculated?**
A: Pricing is based on document size, processing complexity, and optional features like vectorization. See the pricing page for detailed information.

**Q: Are there any free processing credits?**
A: New users receive 100 free processing credits. Additional credits can be purchased as needed.

### Technical Questions

**Q: What AI models are used?**
A: DIPC uses state-of-the-art multi-modal language models from leading providers, optimized for document understanding tasks.

**Q: Can I integrate DIPC with my application?**
A: Yes, DIPC provides a comprehensive REST API for integration with external applications and workflows.

**Q: Is there a mobile app?**
A: The web interface is mobile-responsive. Native mobile apps are planned for future release.

---

*This user guide is regularly updated. For the latest version, visit [docs.dipc.example.com](https://docs.dipc.example.com)*