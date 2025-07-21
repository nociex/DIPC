/**
 * Task Status Checker Utility
 * Validates whether tasks are suitable for markdown editing
 */

import { Task } from '../types';
import { TaskStatusResult } from './markdown-types';

export class TaskStatusChecker {
  /**
   * Check if a task can be edited as markdown
   */
  static canEditAsMarkdown(task: Task): TaskStatusResult {
    if (task.status !== 'completed') {
      return {
        canEdit: false,
        reason: '任务尚未完成',
        suggestion: '请等待任务处理完成后再尝试编辑'
      };
    }
    
    if (!task.results || Object.keys(task.results).length === 0) {
      return {
        canEdit: false,
        reason: '任务没有可用结果',
        suggestion: '该任务没有生成可编辑的内容'
      };
    }
    
    // Check result size
    const resultSize = JSON.stringify(task.results).length;
    if (resultSize > 1024 * 1024) { // 1MB
      return {
        canEdit: true,
        reason: '内容较大，将进行截断处理',
        suggestion: '大型内容将被截断以确保页面响应性能'
      };
    }
    
    return { canEdit: true };
  }
  
  /**
   * Get status message for a task
   */
  static getStatusMessage(task: Task): string {
    switch (task.status) {
      case 'pending':
        return '任务等待处理中...';
      case 'processing':
        return '任务正在处理中...';
      case 'failed':
        return '任务处理失败';
      case 'completed':
        return task.results ? '任务已完成' : '任务已完成但无结果';
      case 'cancelled':
        return '任务已取消';
      default:
        return '未知状态';
    }
  }
  
  /**
   * Determine if markdown button should be shown
   */
  static shouldShowMarkdownButton(task: Task): boolean {
    return task.status === 'completed' && 
           task.results !== null && 
           task.results !== undefined &&
           Object.keys(task.results).length > 0;
  }
  
  /**
   * Get task completion percentage
   */
  static getCompletionPercentage(task: Task): number {
    switch (task.status) {
      case 'pending':
        return 0;
      case 'processing':
        return 50;
      case 'completed':
        return 100;
      case 'failed':
      case 'cancelled':
        return 0;
      default:
        return 0;
    }
  }
  
  /**
   * Check if task has valid results for conversion
   */
  static hasValidResults(task: Task): boolean {
    if (!task.results) return false;
    
    // Check if results is an object with content
    if (typeof task.results === 'object' && task.results !== null) {
      return Object.keys(task.results).length > 0;
    }
    
    // Check if results is a non-empty string
    if (typeof task.results === 'string') {
      return task.results.trim().length > 0;
    }
    
    return false;
  }
  
  /**
   * Estimate content complexity for conversion
   */
  static estimateContentComplexity(task: Task): 'low' | 'medium' | 'high' {
    if (!task.results) return 'low';
    
    const resultString = JSON.stringify(task.results);
    const size = resultString.length;
    
    if (size < 10 * 1024) { // < 10KB
      return 'low';
    } else if (size < 100 * 1024) { // < 100KB
      return 'medium';
    } else {
      return 'high';
    }
  }
}