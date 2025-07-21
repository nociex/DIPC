/**
 * Tests for TaskStatusChecker utility
 */

import { TaskStatusChecker } from '../task-status-checker';
import type { Task } from '@/types';

describe('TaskStatusChecker', () => {
  // Mock task factory
  const createMockTask = (overrides: Partial<Task> = {}): Task => ({
    id: 'test-task-123',
    user_id: 'user-123',
    task_type: 'single_file_task',
    status: 'completed',
    file_url: 'https://example.com/file.pdf',
    files: [],
    cost_limit: 1.0,
    cost_incurred: 0.5,
    permanent_storage: false,
    vectorize: false,
    results: { data: 'test' },
    error_message: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides
  });

  describe('canEditAsMarkdown', () => {
    it('should allow editing when task is completed with results', () => {
      const task = createMockTask({
        status: 'completed',
        results: { content: 'markdown content' }
      });
      
      const result = TaskStatusChecker.canEditAsMarkdown(task);
      
      expect(result.canEdit).toBe(true);
      expect(result.reason).toBeUndefined();
      expect(result.suggestion).toBeUndefined();
    });

    it('should not allow editing when task is not completed', () => {
      const statuses: Array<Task['status']> = ['pending', 'processing', 'failed'];
      
      statuses.forEach(status => {
        const task = createMockTask({
          status,
          results: { data: 'test' }
        });
        
        const result = TaskStatusChecker.canEditAsMarkdown(task);
        
        expect(result.canEdit).toBe(false);
        expect(result.reason).toBe('任务尚未完成');
        expect(result.suggestion).toBe('请等待任务处理完成后再尝试编辑');
      });
    });

    it('should not allow editing when task has no results', () => {
      const task = createMockTask({
        status: 'completed',
        results: null
      });
      
      const result = TaskStatusChecker.canEditAsMarkdown(task);
      
      expect(result.canEdit).toBe(false);
      expect(result.reason).toBe('任务没有可用结果');
      expect(result.suggestion).toBe('该任务没有生成可编辑的内容');
    });

    it('should not allow editing when results are empty object', () => {
      const task = createMockTask({
        status: 'completed',
        results: {}
      });
      
      const result = TaskStatusChecker.canEditAsMarkdown(task);
      
      expect(result.canEdit).toBe(false);
      expect(result.reason).toBe('任务没有可用结果');
      expect(result.suggestion).toBe('该任务没有生成可编辑的内容');
    });

    it('should warn about large content but allow editing', () => {
      // Create a large result object (> 1MB)
      const largeContent = 'x'.repeat(1024 * 1024 + 1);
      const task = createMockTask({
        status: 'completed',
        results: { content: largeContent }
      });
      
      const result = TaskStatusChecker.canEditAsMarkdown(task);
      
      expect(result.canEdit).toBe(true);
      expect(result.reason).toBe('内容较大，将进行截断处理');
      expect(result.suggestion).toBe('大型内容将被截断以确保页面响应性能');
    });

    it('should handle array results', () => {
      const task = createMockTask({
        status: 'completed',
        results: ['item1', 'item2', 'item3'] as any
      });
      
      const result = TaskStatusChecker.canEditAsMarkdown(task);
      
      expect(result.canEdit).toBe(true);
    });
  });

  describe('getStatusMessage', () => {
    it('should return correct status messages', () => {
      const testCases = [
        { status: 'pending' as const, expected: '任务等待处理中...' },
        { status: 'processing' as const, expected: '任务正在处理中...' },
        { status: 'failed' as const, expected: '任务处理失败' },
        { status: 'completed' as const, expected: '任务已完成' },
        { status: 'cancelled' as any, expected: '任务已取消' },
        { status: 'unknown' as any, expected: '未知状态' }
      ];

      testCases.forEach(({ status, expected }) => {
        const task = createMockTask({ status, results: { data: 'test' } });
        expect(TaskStatusChecker.getStatusMessage(task)).toBe(expected);
      });
    });

    it('should handle completed task without results', () => {
      const task = createMockTask({
        status: 'completed',
        results: null
      });
      
      expect(TaskStatusChecker.getStatusMessage(task)).toBe('任务已完成但无结果');
    });
  });

  describe('shouldShowMarkdownButton', () => {
    it('should show button for completed tasks with results', () => {
      const task = createMockTask({
        status: 'completed',
        results: { data: 'content' }
      });
      
      expect(TaskStatusChecker.shouldShowMarkdownButton(task)).toBe(true);
    });

    it('should not show button for non-completed tasks', () => {
      const statuses: Array<Task['status']> = ['pending', 'processing', 'failed'];
      
      statuses.forEach(status => {
        const task = createMockTask({
          status,
          results: { data: 'test' }
        });
        
        expect(TaskStatusChecker.shouldShowMarkdownButton(task)).toBe(false);
      });
    });

    it('should not show button when results are null or undefined', () => {
      const task1 = createMockTask({
        status: 'completed',
        results: null
      });
      
      const task2 = createMockTask({
        status: 'completed',
        results: undefined as any
      });
      
      expect(TaskStatusChecker.shouldShowMarkdownButton(task1)).toBe(false);
      expect(TaskStatusChecker.shouldShowMarkdownButton(task2)).toBe(false);
    });

    it('should not show button for empty results', () => {
      const task = createMockTask({
        status: 'completed',
        results: {}
      });
      
      expect(TaskStatusChecker.shouldShowMarkdownButton(task)).toBe(false);
    });
  });

  describe('getCompletionPercentage', () => {
    it('should return correct completion percentages', () => {
      const testCases = [
        { status: 'pending' as const, expected: 0 },
        { status: 'processing' as const, expected: 50 },
        { status: 'completed' as const, expected: 100 },
        { status: 'failed' as const, expected: 0 },
        { status: 'cancelled' as any, expected: 0 },
        { status: 'unknown' as any, expected: 0 }
      ];

      testCases.forEach(({ status, expected }) => {
        const task = createMockTask({ status });
        expect(TaskStatusChecker.getCompletionPercentage(task)).toBe(expected);
      });
    });
  });

  describe('hasValidResults', () => {
    it('should return true for object results with content', () => {
      const task = createMockTask({
        results: { data: 'content', value: 123 }
      });
      
      expect(TaskStatusChecker.hasValidResults(task)).toBe(true);
    });

    it('should return false for empty object results', () => {
      const task = createMockTask({
        results: {}
      });
      
      expect(TaskStatusChecker.hasValidResults(task)).toBe(false);
    });

    it('should return true for non-empty string results', () => {
      const task = createMockTask({
        results: 'string content' as any
      });
      
      expect(TaskStatusChecker.hasValidResults(task)).toBe(true);
    });

    it('should return false for empty string results', () => {
      const task = createMockTask({
        results: '   ' as any
      });
      
      expect(TaskStatusChecker.hasValidResults(task)).toBe(false);
    });

    it('should return false for null or undefined results', () => {
      const task1 = createMockTask({ results: null });
      const task2 = createMockTask({ results: undefined as any });
      
      expect(TaskStatusChecker.hasValidResults(task1)).toBe(false);
      expect(TaskStatusChecker.hasValidResults(task2)).toBe(false);
    });

    it('should handle array results', () => {
      const task = createMockTask({
        results: [1, 2, 3] as any
      });
      
      // Arrays are objects, so they should have keys (indices)
      expect(TaskStatusChecker.hasValidResults(task)).toBe(true);
    });
  });

  describe('estimateContentComplexity', () => {
    it('should return low complexity for small content', () => {
      const task = createMockTask({
        results: { small: 'content' }
      });
      
      expect(TaskStatusChecker.estimateContentComplexity(task)).toBe('low');
    });

    it('should return medium complexity for medium content', () => {
      // Create content between 10KB and 100KB
      const mediumContent = 'x'.repeat(50 * 1024);
      const task = createMockTask({
        results: { content: mediumContent }
      });
      
      expect(TaskStatusChecker.estimateContentComplexity(task)).toBe('medium');
    });

    it('should return high complexity for large content', () => {
      // Create content > 100KB
      const largeContent = 'x'.repeat(150 * 1024);
      const task = createMockTask({
        results: { content: largeContent }
      });
      
      expect(TaskStatusChecker.estimateContentComplexity(task)).toBe('high');
    });

    it('should return low complexity for null results', () => {
      const task = createMockTask({
        results: null
      });
      
      expect(TaskStatusChecker.estimateContentComplexity(task)).toBe('low');
    });

    it('should handle nested objects correctly', () => {
      const task = createMockTask({
        results: {
          level1: {
            level2: {
              level3: {
                data: 'nested content with some length'
              }
            }
          }
        }
      });
      
      const complexity = TaskStatusChecker.estimateContentComplexity(task);
      expect(['low', 'medium', 'high']).toContain(complexity);
    });
  });
});