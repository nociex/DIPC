/**
 * Integration tests for frontend API integration
 * Tests Requirements: 5.1, 5.2, 5.3, 5.5
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient } from '../api';
import { TaskStatus, TaskResponse, CreateTaskRequest } from '../../types';

// Mock server for API integration tests
const server = setupServer(
  rest.post('/v1/tasks', (req, res, ctx) => {
    return res(
      ctx.json({
        task_id: 'test-task-123',
        status: 'pending',
        created_at: new Date().toISOString(),
        estimated_cost: 0.05
      })
    );
  }),
  
  rest.get('/v1/tasks/:taskId/status', (req, res, ctx) => {
    return res(
      ctx.json({
        task_id: req.params.taskId,
        status: 'completed',
        progress: 100,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString()
      })
    );
  }),
  
  rest.get('/v1/tasks/:taskId/results', (req, res, ctx) => {
    return res(
      ctx.json({
        extracted_content: {
          title: 'Test Document',
          content: 'Sample extracted content',
          metadata: { pages: 1 }
        },
        confidence_score: 0.95,
        processing_time: 2.5
      })
    );
  }),
  
  rest.post('/v1/upload/presigned-url', (req, res, ctx) => {
    return res(
      ctx.json({
        upload_url: 'https://storage.example.com/presigned-upload-url',
        file_id: 'file-123',
        expires_at: new Date(Date.now() + 3600000).toISOString()
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('API Integration Tests', () => {
  describe('Task Management Integration', () => {
    it('should create task and track status through completion', async () => {
      // Create task
      const createRequest: CreateTaskRequest = {
        file_urls: ['https://storage.example.com/test.pdf'],
        user_id: 'test-user',
        options: {
          enable_vectorization: true,
          storage_policy: 'permanent'
        }
      };
      
      const createResponse = await apiClient.createTask(createRequest);
      expect(createResponse.task_id).toBe('test-task-123');
      expect(createResponse.status).toBe('pending');
      
      // Check status
      const statusResponse = await apiClient.getTaskStatus('test-task-123');
      expect(statusResponse.status).toBe('completed');
      expect(statusResponse.progress).toBe(100);
      
      // Get results
      const resultsResponse = await apiClient.getTaskResults('test-task-123');
      expect(resultsResponse.extracted_content.title).toBe('Test Document');
      expect(resultsResponse.confidence_score).toBe(0.95);
    });
    
    it('should handle task creation errors gracefully', async () => {
      // Mock error response
      server.use(
        rest.post('/v1/tasks', (req, res, ctx) => {
          return res(
            ctx.status(400),
            ctx.json({
              error_code: 'INVALID_FILE_URL',
              error_message: 'Invalid file URL provided',
              timestamp: new Date().toISOString()
            })
          );
        })
      );
      
      const createRequest: CreateTaskRequest = {
        file_urls: ['invalid-url'],
        user_id: 'test-user',
        options: { enable_vectorization: false }
      };
      
      await expect(apiClient.createTask(createRequest)).rejects.toThrow('Invalid file URL provided');
    });
  });
  
  describe('File Upload Integration', () => {
    it('should get presigned URL for file upload', async () => {
      const response = await apiClient.getPresignedUrl({
        filename: 'test-document.pdf',
        content_type: 'application/pdf',
        user_id: 'test-user'
      });
      
      expect(response.upload_url).toBe('https://storage.example.com/presigned-upload-url');
      expect(response.file_id).toBe('file-123');
      expect(response.expires_at).toBeDefined();
    });
    
    it('should handle upload URL generation errors', async () => {
      server.use(
        rest.post('/v1/upload/presigned-url', (req, res, ctx) => {
          return res(
            ctx.status(400),
            ctx.json({
              error_code: 'FILE_TOO_LARGE',
              error_message: 'File size exceeds maximum limit'
            })
          );
        })
      );
      
      await expect(
        apiClient.getPresignedUrl({
          filename: 'huge-file.pdf',
          content_type: 'application/pdf',
          user_id: 'test-user',
          file_size: 500 * 1024 * 1024 // 500MB
        })
      ).rejects.toThrow('File size exceeds maximum limit');
    });
  });
  
  describe('Error Handling Integration', () => {
    it('should handle network errors gracefully', async () => {
      // Simulate network error
      server.use(
        rest.get('/v1/tasks/:taskId/status', (req, res, ctx) => {
          return res.networkError('Network connection failed');
        })
      );
      
      await expect(apiClient.getTaskStatus('test-task-123')).rejects.toThrow();
    });
    
    it('should handle server errors with proper error messages', async () => {
      server.use(
        rest.get('/v1/tasks/:taskId/results', (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({
              error_code: 'INTERNAL_SERVER_ERROR',
              error_message: 'An unexpected error occurred'
            })
          );
        })
      );
      
      await expect(apiClient.getTaskResults('test-task-123')).rejects.toThrow('An unexpected error occurred');
    });
  });
  
  describe('Concurrent Operations Integration', () => {
    it('should handle multiple concurrent API calls', async () => {
      const taskIds = ['task-1', 'task-2', 'task-3', 'task-4', 'task-5'];
      
      // Make concurrent status requests
      const statusPromises = taskIds.map(taskId => 
        apiClient.getTaskStatus(taskId)
      );
      
      const results = await Promise.all(statusPromises);
      
      expect(results).toHaveLength(5);
      results.forEach((result, index) => {
        expect(result.task_id).toBe(taskIds[index]);
        expect(result.status).toBe('completed');
      });
    });
    
    it('should handle mixed success and failure responses', async () => {
      server.use(
        rest.get('/v1/tasks/task-1/status', (req, res, ctx) => {
          return res(ctx.json({ task_id: 'task-1', status: 'completed' }));
        }),
        rest.get('/v1/tasks/task-2/status', (req, res, ctx) => {
          return res(ctx.status(404), ctx.json({ error_code: 'TASK_NOT_FOUND' }));
        }),
        rest.get('/v1/tasks/task-3/status', (req, res, ctx) => {
          return res(ctx.json({ task_id: 'task-3', status: 'processing' }));
        })
      );
      
      const results = await Promise.allSettled([
        apiClient.getTaskStatus('task-1'),
        apiClient.getTaskStatus('task-2'),
        apiClient.getTaskStatus('task-3')
      ]);
      
      expect(results[0].status).toBe('fulfilled');
      expect(results[1].status).toBe('rejected');
      expect(results[2].status).toBe('fulfilled');
    });
  });
  
  describe('Real-time Updates Integration', () => {
    it('should handle polling for task status updates', async () => {
      let callCount = 0;
      
      server.use(
        rest.get('/v1/tasks/polling-task/status', (req, res, ctx) => {
          callCount++;
          const status = callCount < 3 ? 'processing' : 'completed';
          const progress = callCount < 3 ? callCount * 30 : 100;
          
          return res(
            ctx.json({
              task_id: 'polling-task',
              status,
              progress,
              created_at: new Date().toISOString()
            })
          );
        })
      );
      
      // Simulate polling
      const pollTask = async () => {
        let status = 'processing';
        let attempts = 0;
        const maxAttempts = 5;
        
        while (status === 'processing' && attempts < maxAttempts) {
          const response = await apiClient.getTaskStatus('polling-task');
          status = response.status;
          attempts++;
          
          if (status === 'processing') {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
        
        return status;
      };
      
      const finalStatus = await pollTask();
      expect(finalStatus).toBe('completed');
      expect(callCount).toBe(3);
    });
  });
});

describe('Performance Integration Tests', () => {
  it('should handle rapid successive API calls', async () => {
    const startTime = Date.now();
    const numCalls = 20;
    
    const promises = Array.from({ length: numCalls }, (_, i) =>
      apiClient.getTaskStatus(`rapid-task-${i}`)
    );
    
    const results = await Promise.all(promises);
    const endTime = Date.now();
    const totalTime = endTime - startTime;
    
    expect(results).toHaveLength(numCalls);
    expect(totalTime).toBeLessThan(5000); // Should complete within 5 seconds
    
    // All requests should succeed
    results.forEach(result => {
      expect(result.status).toBeDefined();
    });
  });
  
  it('should handle large response payloads efficiently', async () => {
    // Mock large response
    const largeContent = {
      extracted_content: {
        title: 'Large Document',
        content: 'A'.repeat(100000), // 100KB of content
        metadata: {
          pages: 1000,
          sections: Array.from({ length: 100 }, (_, i) => ({
            title: `Section ${i}`,
            content: 'B'.repeat(1000)
          }))
        }
      },
      confidence_score: 0.95,
      processing_time: 15.2
    };
    
    server.use(
      rest.get('/v1/tasks/large-task/results', (req, res, ctx) => {
        return res(ctx.json(largeContent));
      })
    );
    
    const startTime = Date.now();
    const results = await apiClient.getTaskResults('large-task');
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    expect(results.extracted_content.content).toHaveLength(100000);
    expect(results.extracted_content.metadata.sections).toHaveLength(100);
    expect(responseTime).toBeLessThan(2000); // Should handle large responses quickly
  });
});