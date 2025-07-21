/**
 * JSON to Markdown Converter
 * Converts JSON results to markdown format with content truncation and performance optimization
 */

import { ConversionOptions, ConversionResult, ContentProcessingResult } from './markdown-types';

export class JsonToMarkdownConverter {
  private static readonly DEFAULT_MAX_SIZE = 500 * 1024; // 500KB
  private static readonly TRUNCATE_THRESHOLD = 400 * 1024; // 400KB
  private static readonly DEFAULT_MAX_DEPTH = 5;
  private static visitedObjects = new WeakSet<object>();
  
  /**
   * Convert JSON data to markdown format
   */
  static convert(data: any, options: ConversionOptions = {}): ConversionResult {
    const {
      includeMetadata = true,
      maxDepth = this.DEFAULT_MAX_DEPTH,
      maxContentSize = this.DEFAULT_MAX_SIZE,
      truncateThreshold = this.TRUNCATE_THRESHOLD,
      tableFormat = 'github'
    } = options;
    
    // Clear visited objects for new conversion
    this.visitedObjects = new WeakSet<object>();
    
    let markdown = '';
    const warnings: string[] = [];
    
    // Estimate content size - handle circular references
    let estimatedSize = 0;
    try {
      estimatedSize = JSON.stringify(data).length * 1.5; // markdown is usually 50% larger than JSON
    } catch (error) {
      // Handle circular references - estimate size differently
      const seen = new Set();
      const countSize = (obj: any): number => {
        if (!obj || typeof obj !== 'object' || seen.has(obj)) {
          return 50; // Estimate for simple values or circular refs
        }
        seen.add(obj);
        let size = 100; // Base size for object overhead
        for (const key in obj) {
          if (obj.hasOwnProperty(key)) {
            size += key.length + countSize(obj[key]);
          }
        }
        return size;
      };
      estimatedSize = countSize(data) * 1.5;
    }
    
    if (estimatedSize > truncateThreshold) {
      warnings.push('内容较大，已进行截断处理以确保页面性能');
    }
    
    // Add document header
    if (includeMetadata) {
      markdown += this.generateHeader(data);
    }
    
    // Convert main content recursively
    const contentResult = this.convertValue(data, 0, maxDepth, maxContentSize, tableFormat);
    markdown += contentResult.content;
    
    const finalSize = markdown.length;
    const isTruncated = contentResult.isTruncated || finalSize >= maxContentSize;
    
    if (isTruncated) {
      markdown = this.truncateContent(markdown, maxContentSize);
      markdown += '\n\n---\n\n**注意**: 内容已被截断以确保页面性能。[查看完整内容](../)\n';
    }
    
    return {
      markdown: markdown.trim(),
      isTruncated,
      originalSize: Math.round(estimatedSize),
      truncatedSize: finalSize,
      warnings
    };
  }
  
  /**
   * Generate document header with metadata
   */
  private static generateHeader(data: any): string {
    const timestamp = new Date().toLocaleString('zh-CN');
    let header = `# 解析结果\n\n`;
    header += `**生成时间**: ${timestamp}\n\n`;
    
    // Add basic statistics
    if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data);
      header += `**数据项数量**: ${keys.length}\n\n`;
      
      if (keys.length > 0) {
        header += `**主要字段**: ${keys.slice(0, 5).join(', ')}${keys.length > 5 ? '...' : ''}\n\n`;
      }
    }
    
    header += `---\n\n`;
    return header;
  }
  
  /**
   * Convert a value to markdown recursively
   */
  private static convertValue(
    value: any, 
    depth: number, 
    maxDepth: number, 
    remainingSize: number,
    tableFormat: 'simple' | 'github'
  ): ContentProcessingResult {
    if (depth > maxDepth || remainingSize <= 0) {
      return { content: '...', isTruncated: true, processedSize: 3 };
    }
    
    // Check for circular references
    if (typeof value === 'object' && value !== null) {
      if (this.visitedObjects.has(value)) {
        const content = '_[Circular Reference]_\n\n';
        return { content, isTruncated: false, processedSize: content.length };
      }
      this.visitedObjects.add(value);
    }
    
    if (value === null || value === undefined) {
      const content = '_null_\n\n';
      return { content, isTruncated: false, processedSize: content.length };
    }
    
    if (typeof value === 'string') {
      if (value.length > remainingSize) {
        const truncated = value.substring(0, remainingSize - 10) + '...\n\n';
        return { content: truncated, isTruncated: true, processedSize: truncated.length };
      }
      const content = `${value}\n\n`;
      return { content, isTruncated: false, processedSize: content.length };
    }
    
    if (typeof value === 'number' || typeof value === 'boolean') {
      const content = `**${value}**\n\n`;
      return { content, isTruncated: false, processedSize: content.length };
    }
    
    if (Array.isArray(value)) {
      return this.convertArray(value, depth, maxDepth, remainingSize, tableFormat);
    }
    
    if (typeof value === 'object') {
      return this.convertObject(value, depth, maxDepth, remainingSize, tableFormat);
    }
    
    const content = String(value) + '\n\n';
    return { content, isTruncated: false, processedSize: content.length };
  }
  
  /**
   * Convert object to markdown
   */
  private static convertObject(
    obj: any, 
    depth: number, 
    maxDepth: number, 
    remainingSize: number,
    tableFormat: 'simple' | 'github'
  ): ContentProcessingResult {
    const entries = Object.entries(obj);
    let result = '';
    let isTruncated = false;
    let currentSize = remainingSize;
    let totalProcessedSize = 0;
    
    // Check if suitable for table format
    if (this.isTableCandidate(obj)) {
      const tableResult = this.formatAsTable(obj, tableFormat);
      if (tableResult.length <= currentSize) {
        const content = tableResult + '\n\n';
        return { content, isTruncated: false, processedSize: content.length };
      } else {
        const content = '表格内容过大，已省略\n\n';
        return { content, isTruncated: true, processedSize: content.length };
      }
    }
    
    // Standard object format
    for (const [key, value] of entries) {
      if (currentSize <= 0) {
        result += '\n\n_更多内容已省略..._\n\n';
        isTruncated = true;
        totalProcessedSize += 20;
        break;
      }
      
      const heading = '#'.repeat(Math.min(depth + 2, 6));
      const headerContent = `${heading} ${key}\n\n`;
      
      if (headerContent.length > currentSize) {
        isTruncated = true;
        break;
      }
      
      result += headerContent;
      currentSize -= headerContent.length;
      totalProcessedSize += headerContent.length;
      
      const valueResult = this.convertValue(value, depth + 1, maxDepth, currentSize, tableFormat);
      result += valueResult.content;
      currentSize -= valueResult.processedSize;
      totalProcessedSize += valueResult.processedSize;
      
      if (valueResult.isTruncated) {
        isTruncated = true;
        break;
      }
    }
    
    return { content: result, isTruncated, processedSize: totalProcessedSize };
  }
  
  /**
   * Convert array to markdown
   */
  private static convertArray(
    arr: any[], 
    depth: number, 
    maxDepth: number, 
    remainingSize: number,
    tableFormat: 'simple' | 'github'
  ): ContentProcessingResult {
    if (arr.length === 0) {
      const content = '_Empty array_\n\n';
      return { content, isTruncated: false, processedSize: content.length };
    }
    
    let currentSize = remainingSize;
    let isTruncated = false;
    let totalProcessedSize = 0;
    
    // Check if it's a simple list
    if (arr.every(item => typeof item === 'string' || typeof item === 'number')) {
      let result = '';
      for (let i = 0; i < arr.length; i++) {
        const itemContent = `- ${arr[i]}\n`;
        if (itemContent.length > currentSize) {
          result += `\n_还有 ${arr.length - i} 项未显示..._\n`;
          isTruncated = true;
          totalProcessedSize += 30;
          break;
        }
        result += itemContent;
        currentSize -= itemContent.length;
        totalProcessedSize += itemContent.length;
      }
      const finalContent = result + '\n';
      return { content: finalContent, isTruncated, processedSize: totalProcessedSize + 1 };
    }
    
    // Complex array processing
    let result = '';
    for (let i = 0; i < arr.length; i++) {
      if (currentSize <= 0) {
        result += `\n_还有 ${arr.length - i} 项未显示..._\n\n`;
        isTruncated = true;
        totalProcessedSize += 30;
        break;
      }
      
      const headerContent = `### Item ${i + 1}\n\n`;
      if (headerContent.length > currentSize) {
        isTruncated = true;
        break;
      }
      
      result += headerContent;
      currentSize -= headerContent.length;
      totalProcessedSize += headerContent.length;
      
      const itemResult = this.convertValue(arr[i], depth + 1, maxDepth, currentSize, tableFormat);
      result += itemResult.content;
      currentSize -= itemResult.processedSize;
      totalProcessedSize += itemResult.processedSize;
      
      if (itemResult.isTruncated) {
        isTruncated = true;
        break;
      }
    }
    
    return { content: result, isTruncated, processedSize: totalProcessedSize };
  }
  
  /**
   * Check if object is suitable for table format
   */
  private static isTableCandidate(obj: any): boolean {
    const values = Object.values(obj);
    return values.length > 1 && 
           values.length <= 10 && // Don't create huge tables
           values.every(v => 
             typeof v === 'string' || 
             typeof v === 'number' || 
             typeof v === 'boolean' ||
             v === null ||
             v === undefined
           );
  }
  
  /**
   * Format object as table
   */
  private static formatAsTable(obj: any, format: 'simple' | 'github'): string {
    const entries = Object.entries(obj);
    
    if (format === 'github') {
      const headers = entries.map(([key]) => key).join(' | ');
      const separator = entries.map(() => '---').join(' | ');
      const values = entries.map(([, value]) => String(value ?? '')).join(' | ');
      
      return `| ${headers} |\n| ${separator} |\n| ${values} |`;
    } else {
      // Simple format
      return entries.map(([key, value]) => `**${key}**: ${value ?? 'null'}`).join('\n');
    }
  }
  
  /**
   * Truncate content at appropriate position
   */
  private static truncateContent(content: string, maxSize: number): string {
    if (content.length <= maxSize) return content;
    
    // Find appropriate truncation point (avoid cutting in middle of words)
    let truncateIndex = maxSize;
    while (truncateIndex > 0 && content[truncateIndex] !== '\n' && content[truncateIndex] !== ' ') {
      truncateIndex--;
    }
    
    if (truncateIndex === 0) truncateIndex = maxSize;
    
    return content.substring(0, truncateIndex);
  }
  
  /**
   * Escape markdown special characters
   */
  private static escapeMarkdown(text: string): string {
    return text.replace(/([\\`*_{}[\]()#+\-.!])/g, '\\$1');
  }
  
  /**
   * Clean and format text for markdown
   */
  private static cleanText(text: string): string {
    return text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }
}