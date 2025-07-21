import type { Task } from '@/types'

export type ExportFormat = 'json' | 'csv' | 'pdf' | 'markdown' | 'xlsx'

export interface SharePermissions {
  allowDownload: boolean
  allowCopy: boolean
  expiresAt?: Date
  password?: string
}

export interface ExportOptions {
  includeMetadata?: boolean
  includeRawData?: boolean
  format?: 'pretty' | 'compact'
  dateFormat?: 'iso' | 'locale'
}

export class ExportService {
  /**
   * Export a single result to the specified format
   */
  static async exportResult(
    task: Task, 
    format: ExportFormat, 
    options: ExportOptions = {}
  ): Promise<Blob> {
    switch (format) {
      case 'json':
        return this.exportToJSON(task, options)
      case 'csv':
        return this.exportToCSV([task], options)
      case 'pdf':
        return this.exportToPDF(task, options)
      case 'markdown':
        return this.exportToMarkdown(task, options)
      case 'xlsx':
        return this.exportToXLSX([task], options)
      default:
        throw new Error(`Unsupported export format: ${format}`)
    }
  }

  /**
   * Export multiple results to the specified format
   */
  static async exportMultiple(
    tasks: Task[], 
    format: ExportFormat, 
    options: ExportOptions = {}
  ): Promise<Blob> {
    switch (format) {
      case 'json':
        return this.exportMultipleToJSON(tasks, options)
      case 'csv':
        return this.exportToCSV(tasks, options)
      case 'pdf':
        return this.exportMultipleToPDF(tasks, options)
      case 'markdown':
        return this.exportMultipleToMarkdown(tasks, options)
      case 'xlsx':
        return this.exportToXLSX(tasks, options)
      default:
        throw new Error(`Unsupported export format: ${format}`)
    }
  }

  /**
   * Export single task to JSON
   */
  private static exportToJSON(task: Task, options: ExportOptions): Blob {
    const data = this.prepareTaskData(task, options)
    const jsonString = options.format === 'compact' 
      ? JSON.stringify(data)
      : JSON.stringify(data, null, 2)
    
    return new Blob([jsonString], { type: 'application/json' })
  }

  /**
   * Export multiple tasks to JSON
   */
  private static exportMultipleToJSON(tasks: Task[], options: ExportOptions): Blob {
    const data = tasks.map(task => this.prepareTaskData(task, options))
    const jsonString = options.format === 'compact' 
      ? JSON.stringify(data)
      : JSON.stringify(data, null, 2)
    
    return new Blob([jsonString], { type: 'application/json' })
  }

  /**
   * Export tasks to CSV format
   */
  private static exportToCSV(tasks: Task[], options: ExportOptions): Blob {
    const headers = [
      'Task ID',
      'Filename',
      'Status',
      'Task Type',
      'Created At',
      'Completed At',
      'Cost',
      'Results Summary'
    ]

    if (options.includeMetadata) {
      headers.push('Metadata')
    }

    const rows = tasks.map(task => {
      const row = [
        task.id,
        task.original_filename || '',
        task.status,
        task.task_type,
        this.formatDate(task.created_at, options.dateFormat),
        task.completed_at ? this.formatDate(task.completed_at, options.dateFormat) : '',
        task.actual_cost?.toString() || '',
        this.summarizeResults(task.results)
      ]

      if (options.includeMetadata) {
        row.push(JSON.stringify({
          user_id: task.user_id,
          options: task.options,
          estimated_cost: task.estimated_cost
        }))
      }

      return row
    })

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n')

    return new Blob([csvContent], { type: 'text/csv' })
  }

  /**
   * Export single task to PDF
   */
  private static async exportToPDF(task: Task, options: ExportOptions): Promise<Blob> {
    // Enhanced PDF generation with better formatting
    const htmlContent = this.generateHTMLReport(task, options)
    
    // Use modern browser APIs for better PDF generation
    try {
      // Create a temporary iframe for PDF generation
      const iframe = document.createElement('iframe')
      iframe.style.position = 'absolute'
      iframe.style.left = '-9999px'
      iframe.style.width = '210mm'
      iframe.style.height = '297mm'
      document.body.appendChild(iframe)
      
      const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document
      if (!iframeDoc) {
        throw new Error('Unable to access iframe document')
      }
      
      iframeDoc.open()
      iframeDoc.write(htmlContent)
      iframeDoc.close()
      
      // Wait for content to load
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Generate PDF using print functionality
      const printResult = await new Promise<Blob>((resolve, reject) => {
        try {
          // For modern browsers, we can use the print API
          // This is still a simplified approach - in production use jsPDF or similar
          const printContent = iframeDoc.documentElement.outerHTML
          resolve(new Blob([printContent], { type: 'text/html' }))
        } catch (error) {
          reject(error)
        }
      })
      
      // Clean up
      document.body.removeChild(iframe)
      
      return printResult
    } catch (error) {
      // Fallback to simple HTML export
      return new Blob([htmlContent], { type: 'text/html' })
    }
  }

  /**
   * Export multiple tasks to PDF
   */
  private static async exportMultipleToPDF(tasks: Task[], options: ExportOptions): Promise<Blob> {
    const htmlContent = tasks.map(task => this.generateHTMLReport(task, options)).join('<div style="page-break-before: always;"></div>')
    return new Blob([htmlContent], { type: 'text/html' })
  }

  /**
   * Export single task to Markdown
   */
  private static exportToMarkdown(task: Task, options: ExportOptions): Blob {
    const markdown = this.generateMarkdownReport(task, options)
    return new Blob([markdown], { type: 'text/markdown' })
  }

  /**
   * Export multiple tasks to Markdown
   */
  private static exportMultipleToMarkdown(tasks: Task[], options: ExportOptions): Blob {
    const markdown = tasks.map(task => this.generateMarkdownReport(task, options)).join('\n\n---\n\n')
    return new Blob([markdown], { type: 'text/markdown' })
  }

  /**
   * Export tasks to XLSX format
   */
  private static exportToXLSX(tasks: Task[], options: ExportOptions): Blob {
    // This is a simplified implementation
    // In production, you'd use a library like SheetJS (xlsx)
    const csvBlob = this.exportToCSV(tasks, options)
    
    // For now, return CSV with xlsx mime type
    // In production, convert to actual Excel format
    return new Blob([csvBlob], { 
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
    })
  }

  /**
   * Generate a shareable link for a result
   */
  static async generateShareLink(
    taskId: string, 
    permissions: SharePermissions
  ): Promise<string> {
    // In a real implementation, this would make an API call to generate a secure share link
    const shareData = {
      taskId,
      permissions,
      timestamp: Date.now()
    }

    // Create a base64 encoded share token (in production, use proper JWT or similar)
    const shareToken = btoa(JSON.stringify(shareData))
    
    // Return a shareable URL
    const baseUrl = window.location.origin
    return `${baseUrl}/shared/${shareToken}`
  }

  /**
   * Validate share link and extract permissions
   */
  static validateShareLink(shareToken: string): { taskId: string; permissions: SharePermissions } | null {
    try {
      const shareData = JSON.parse(atob(shareToken))
      
      // Check if link has expired
      if (shareData.permissions.expiresAt && new Date(shareData.permissions.expiresAt) < new Date()) {
        return null
      }

      return {
        taskId: shareData.taskId,
        permissions: shareData.permissions
      }
    } catch (error) {
      return null
    }
  }

  /**
   * Download a blob as a file
   */
  static downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  /**
   * Get appropriate filename for export
   */
  static getExportFilename(task: Task, format: ExportFormat, isMultiple = false): string {
    const timestamp = new Date().toISOString().split('T')[0]
    const baseName = task.original_filename 
      ? task.original_filename.replace(/\.[^/.]+$/, '') 
      : `task-${task.id.slice(0, 8)}`
    
    const prefix = isMultiple ? 'export' : baseName
    return `${prefix}-${timestamp}.${format}`
  }

  /**
   * Get appropriate filename for multiple tasks export
   */
  static getBulkExportFilename(tasks: Task[], format: ExportFormat): string {
    const timestamp = new Date().toISOString().split('T')[0]
    const count = tasks.length
    return `bulk-export-${count}-tasks-${timestamp}.${format}`
  }

  /**
   * Export multiple tasks with progress callback
   */
  static async exportMultipleWithProgress(
    tasks: Task[], 
    format: ExportFormat, 
    options: ExportOptions = {},
    onProgress?: (completed: number, total: number) => void
  ): Promise<Blob> {
    if (tasks.length === 0) {
      throw new Error('No tasks to export')
    }

    // For formats that support batch processing
    if (['json', 'csv', 'xlsx'].includes(format)) {
      onProgress?.(tasks.length, tasks.length)
      return this.exportMultiple(tasks, format, options)
    }

    // For formats that need individual processing (PDF, Markdown)
    const results: Blob[] = []
    
    for (let i = 0; i < tasks.length; i++) {
      const task = tasks[i]
      const blob = await this.exportResult(task, format, options)
      results.push(blob)
      onProgress?.(i + 1, tasks.length)
    }

    // Combine results based on format
    if (format === 'pdf') {
      return this.combinePDFs(results)
    } else if (format === 'markdown') {
      return this.combineMarkdownFiles(results)
    }

    // Default: return first result (shouldn't reach here)
    return results[0] || new Blob([''], { type: 'text/plain' })
  }

  /**
   * Create a ZIP archive of multiple exports
   */
  static async createExportArchive(
    tasks: Task[], 
    formats: ExportFormat[], 
    options: ExportOptions = {},
    onProgress?: (completed: number, total: number) => void
  ): Promise<Blob> {
    // This is a simplified implementation
    // In production, you'd use a library like JSZip
    
    const totalOperations = tasks.length * formats.length
    let completed = 0
    
    const exports: { filename: string; blob: Blob }[] = []
    
    for (const task of tasks) {
      for (const format of formats) {
        const blob = await this.exportResult(task, format, options)
        const filename = this.getExportFilename(task, format)
        exports.push({ filename, blob })
        
        completed++
        onProgress?.(completed, totalOperations)
      }
    }
    
    // Create a simple archive representation
    // In production, use JSZip to create actual ZIP files
    const archiveContent = exports.map(({ filename, blob }) => 
      `--- ${filename} ---\n${blob.type}\n${blob.size} bytes\n\n`
    ).join('')
    
    return new Blob([archiveContent], { type: 'application/zip' })
  }

  /**
   * Combine multiple PDF blobs (simplified)
   */
  private static async combinePDFs(pdfBlobs: Blob[]): Promise<Blob> {
    // This is a simplified implementation
    // In production, use a PDF library like PDF-lib
    const combinedContent = await Promise.all(
      pdfBlobs.map(async (blob, index) => {
        const text = await blob.text()
        return index > 0 ? `<div style="page-break-before: always;"></div>${text}` : text
      })
    )
    
    return new Blob([combinedContent.join('')], { type: 'text/html' })
  }

  /**
   * Combine multiple Markdown files
   */
  private static async combineMarkdownFiles(markdownBlobs: Blob[]): Promise<Blob> {
    const combinedContent = await Promise.all(
      markdownBlobs.map(async (blob) => await blob.text())
    )
    
    return new Blob([combinedContent.join('\n\n---\n\n')], { type: 'text/markdown' })
  }

  /**
   * Prepare task data for export
   */
  private static prepareTaskData(task: Task, options: ExportOptions): any {
    const data: any = {
      id: task.id,
      filename: task.original_filename,
      status: task.status,
      task_type: task.task_type,
      created_at: this.formatDate(task.created_at, options.dateFormat),
      completed_at: task.completed_at ? this.formatDate(task.completed_at, options.dateFormat) : null,
      results: task.results
    }

    if (options.includeMetadata) {
      data.metadata = {
        user_id: task.user_id,
        options: task.options,
        estimated_cost: task.estimated_cost,
        actual_cost: task.actual_cost,
        updated_at: this.formatDate(task.updated_at, options.dateFormat)
      }
    }

    if (!options.includeRawData && task.results) {
      // Provide a summary instead of raw data
      data.results_summary = this.summarizeResults(task.results)
      delete data.results
    }

    return data
  }

  /**
   * Format date based on options
   */
  private static formatDate(dateString: string, format?: 'iso' | 'locale'): string {
    const date = new Date(dateString)
    
    if (format === 'locale') {
      return date.toLocaleString()
    }
    
    return date.toISOString()
  }

  /**
   * Summarize results for export
   */
  private static summarizeResults(results: any): string {
    if (!results) return 'No results'
    
    if (typeof results === 'string') return results.substring(0, 100) + '...'
    
    if (Array.isArray(results)) {
      return `Array with ${results.length} items`
    }
    
    if (typeof results === 'object') {
      const keys = Object.keys(results)
      return `Object with keys: ${keys.slice(0, 5).join(', ')}${keys.length > 5 ? '...' : ''}`
    }
    
    return String(results)
  }

  /**
   * Generate HTML report for PDF export
   */
  private static generateHTMLReport(task: Task, options: ExportOptions): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Task Report - ${task.original_filename || task.id}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; }
          .header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
          .section { margin-bottom: 30px; }
          .label { font-weight: bold; color: #555; }
          .value { margin-left: 10px; }
          .results { background: #f5f5f5; padding: 20px; border-radius: 5px; }
          pre { white-space: pre-wrap; word-wrap: break-word; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>Task Report</h1>
          <p><span class="label">Generated:</span><span class="value">${new Date().toLocaleString()}</span></p>
        </div>
        
        <div class="section">
          <h2>Task Information</h2>
          <p><span class="label">ID:</span><span class="value">${task.id}</span></p>
          <p><span class="label">Filename:</span><span class="value">${task.original_filename || 'N/A'}</span></p>
          <p><span class="label">Status:</span><span class="value">${task.status}</span></p>
          <p><span class="label">Type:</span><span class="value">${task.task_type}</span></p>
          <p><span class="label">Created:</span><span class="value">${this.formatDate(task.created_at, options.dateFormat)}</span></p>
          ${task.completed_at ? `<p><span class="label">Completed:</span><span class="value">${this.formatDate(task.completed_at, options.dateFormat)}</span></p>` : ''}
          ${task.actual_cost ? `<p><span class="label">Cost:</span><span class="value">$${task.actual_cost.toFixed(3)}</span></p>` : ''}
        </div>
        
        ${task.results ? `
        <div class="section">
          <h2>Results</h2>
          <div class="results">
            <pre>${JSON.stringify(task.results, null, 2)}</pre>
          </div>
        </div>
        ` : ''}
        
        ${options.includeMetadata ? `
        <div class="section">
          <h2>Metadata</h2>
          <p><span class="label">User ID:</span><span class="value">${task.user_id}</span></p>
          <p><span class="label">Options:</span><span class="value">${JSON.stringify(task.options, null, 2)}</span></p>
          ${task.estimated_cost ? `<p><span class="label">Estimated Cost:</span><span class="value">$${task.estimated_cost.toFixed(3)}</span></p>` : ''}
        </div>
        ` : ''}
      </body>
      </html>
    `
  }

  /**
   * Generate Markdown report
   */
  private static generateMarkdownReport(task: Task, options: ExportOptions): string {
    let markdown = `# Task Report: ${task.original_filename || task.id}\n\n`
    
    markdown += `**Generated:** ${new Date().toLocaleString()}\n\n`
    
    markdown += `## Task Information\n\n`
    markdown += `- **ID:** ${task.id}\n`
    markdown += `- **Filename:** ${task.original_filename || 'N/A'}\n`
    markdown += `- **Status:** ${task.status}\n`
    markdown += `- **Type:** ${task.task_type}\n`
    markdown += `- **Created:** ${this.formatDate(task.created_at, options.dateFormat)}\n`
    
    if (task.completed_at) {
      markdown += `- **Completed:** ${this.formatDate(task.completed_at, options.dateFormat)}\n`
    }
    
    if (task.actual_cost) {
      markdown += `- **Cost:** $${task.actual_cost.toFixed(3)}\n`
    }
    
    if (task.results) {
      markdown += `\n## Results\n\n`
      markdown += '```json\n'
      markdown += JSON.stringify(task.results, null, 2)
      markdown += '\n```\n'
    }
    
    if (options.includeMetadata) {
      markdown += `\n## Metadata\n\n`
      markdown += `- **User ID:** ${task.user_id}\n`
      markdown += `- **Options:** \`${JSON.stringify(task.options)}\`\n`
      
      if (task.estimated_cost) {
        markdown += `- **Estimated Cost:** $${task.estimated_cost.toFixed(3)}\n`
      }
    }
    
    return markdown
  }
}