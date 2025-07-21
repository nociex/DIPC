/**
 * Tests for JsonToMarkdownConverter utility
 */

import { JsonToMarkdownConverter } from '../json-to-markdown';

describe('JsonToMarkdownConverter', () => {
  describe('convert', () => {
    beforeEach(() => {
      // Reset any global state if needed
      jest.clearAllMocks();
    });
    it('should convert simple object to markdown', () => {
      const data = { title: 'Test', content: 'Hello world' };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('# 解析结果');
      expect(result.markdown).toContain('Test');
      expect(result.markdown).toContain('Hello world');
      expect(result.isTruncated).toBe(false);
      // Simple objects should be converted to tables
      expect(result.markdown).toContain('| title | content |');
    });
    
    it('should convert array to markdown list', () => {
      const data = ['item1', 'item2', 'item3'];
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('- item1');
      expect(result.markdown).toContain('- item2');
      expect(result.markdown).toContain('- item3');
    });
    
    it('should handle nested objects', () => {
      const data = {
        user: {
          name: 'John',
          age: 30
        },
        settings: {
          theme: 'dark'
        }
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('## user');
      expect(result.markdown).toContain('John');
      expect(result.markdown).toContain('30');
      expect(result.markdown).toContain('## settings');
      expect(result.markdown).toContain('dark');
      // Nested objects with simple values should be converted to tables
      expect(result.markdown).toContain('| name | age |');
    });
    
    it('should create table for simple objects', () => {
      const data = { name: 'John', age: 30, active: true };
      const result = JsonToMarkdownConverter.convert(data, { tableFormat: 'github' });
      
      expect(result.markdown).toContain('| name | age | active |');
      expect(result.markdown).toContain('| --- | --- | --- |');
      expect(result.markdown).toContain('| John | 30 | true |');
    });
    
    it('should handle null and undefined values', () => {
      const data = { value1: null, value2: undefined, value3: 'test' };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('test');
      // Null and undefined values in tables are shown as empty strings
      expect(result.markdown).toContain('| value1 | value2 | value3 |');
    });
    
    it('should truncate large content', () => {
      const largeData = { content: 'x'.repeat(600 * 1024) }; // 600KB
      const result = JsonToMarkdownConverter.convert(largeData, { maxContentSize: 100 * 1024 });
      
      expect(result.isTruncated).toBe(true);
      expect(result.markdown).toContain('内容已被截断');
      expect(result.warnings).toContain('内容较大，已进行截断处理以确保页面性能');
    });
    
    it('should respect max depth', () => {
      const deepData = {
        level1: {
          level2: {
            level3: {
              level4: {
                level5: 'deep content'
              }
            }
          }
        }
      };
      const result = JsonToMarkdownConverter.convert(deepData, { maxDepth: 3 });
      
      expect(result.markdown).toContain('level1');
      expect(result.markdown).toContain('level2');
      expect(result.markdown).toContain('level3');
      expect(result.markdown).toContain('...');
    });
    
    it('should handle empty data', () => {
      const result = JsonToMarkdownConverter.convert({});
      
      expect(result.markdown).toContain('# 解析结果');
      expect(result.markdown).toContain('**数据项数量**: 0');
    });
    
    it('should handle complex arrays', () => {
      const data = [
        { name: 'John', age: 30 },
        { name: 'Jane', age: 25 }
      ];
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('### Item 1');
      expect(result.markdown).toContain('### Item 2');
      expect(result.markdown).toContain('John');
      expect(result.markdown).toContain('Jane');
    });
    
    it('should include metadata when requested', () => {
      const data = { test: 'value' };
      const result = JsonToMarkdownConverter.convert(data, { includeMetadata: true });
      
      expect(result.markdown).toContain('# 解析结果');
      expect(result.markdown).toContain('**生成时间**');
      expect(result.markdown).toContain('**数据项数量**: 1');
    });
    
    it('should exclude metadata when not requested', () => {
      const data = { test: 'value' };
      const result = JsonToMarkdownConverter.convert(data, { includeMetadata: false });
      
      expect(result.markdown).not.toContain('# 解析结果');
      expect(result.markdown).not.toContain('**生成时间**');
    });
    
    it('should handle special characters in strings', () => {
      const data = { 
        markdown: '**bold** _italic_ `code`',
        special: '<script>alert("xss")</script>',
        quotes: 'She said "Hello"'
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('**bold** _italic_ `code`');
      expect(result.markdown).toContain('<script>alert("xss")</script>');
      expect(result.markdown).toContain('She said "Hello"');
    });
    
    it('should handle mixed data types', () => {
      const data = {
        string: 'text value',
        number: 42,
        boolean: true,
        null: null,
        array: [1, 2, 3],
        object: { nested: 'value' }
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('text value');
      expect(result.markdown).toContain('42');
      expect(result.markdown).toContain('true');
      expect(result.markdown).toContain('nested');
    });
    
    it('should handle circular references gracefully', () => {
      const data: any = { name: 'parent' };
      data.circular = data; // Create circular reference
      
      // Should not throw error
      expect(() => {
        JsonToMarkdownConverter.convert(data);
      }).not.toThrow();
    });
    
    it('should format dates properly', () => {
      const now = new Date();
      const data = {
        created: now.toISOString(),
        timestamp: now.getTime()
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain(now.toISOString());
      expect(result.markdown).toContain(now.getTime().toString());
    });
    
    it('should handle very long strings', () => {
      const longString = 'a'.repeat(1000);
      const data = { content: longString };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain(longString);
      expect(result.warnings.length).toBe(0);
    });
    
    it('should create tables for arrays of similar objects', () => {
      const data = [
        { id: 1, name: 'Alice', age: 30 },
        { id: 2, name: 'Bob', age: 25 },
        { id: 3, name: 'Charlie', age: 35 }
      ];
      const result = JsonToMarkdownConverter.convert(data);
      
      // Should create a table-like structure
      expect(result.markdown).toContain('Alice');
      expect(result.markdown).toContain('Bob');
      expect(result.markdown).toContain('Charlie');
      expect(result.markdown).toContain('30');
      expect(result.markdown).toContain('25');
      expect(result.markdown).toContain('35');
    });
    
    it('should handle empty arrays and objects', () => {
      const data = {
        emptyArray: [],
        emptyObject: {},
        nested: {
          alsoEmpty: []
        }
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.isTruncated).toBe(false);
      expect(result.warnings.length).toBe(0);
    });
    
    it('should respect different table formats', () => {
      const data = { col1: 'value1', col2: 'value2' };
      
      const simpleResult = JsonToMarkdownConverter.convert(data, { tableFormat: 'simple' });
      const githubResult = JsonToMarkdownConverter.convert(data, { tableFormat: 'github' });
      
      // Both should contain the data
      expect(simpleResult.markdown).toContain('value1');
      expect(simpleResult.markdown).toContain('value2');
      expect(githubResult.markdown).toContain('value1');
      expect(githubResult.markdown).toContain('value2');
      
      // GitHub format should have separator
      expect(githubResult.markdown).toContain('---');
    });
    
    it('should handle Unicode characters', () => {
      const data = {
        chinese: '你好世界',
        emoji: '🚀 🎉 ✨',
        arabic: 'مرحبا بالعالم',
        special: '©️ ™️ ®️'
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('你好世界');
      expect(result.markdown).toContain('🚀 🎉 ✨');
      expect(result.markdown).toContain('مرحبا بالعالم');
      expect(result.markdown).toContain('©️ ™️ ®️');
    });
    
    it('should calculate sizes correctly', () => {
      const smallData = { small: 'data' };
      const largeData = { large: 'x'.repeat(100 * 1024) }; // 100KB
      
      const smallResult = JsonToMarkdownConverter.convert(smallData);
      const largeResult = JsonToMarkdownConverter.convert(largeData);
      
      expect(smallResult.originalSize).toBeLessThan(1024);
      expect(largeResult.originalSize).toBeGreaterThan(100 * 1024);
    });
    
    it('should handle arrays with different item types', () => {
      const data = [
        'string item',
        123,
        true,
        null,
        { object: 'item' },
        ['nested', 'array']
      ];
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('string item');
      expect(result.markdown).toContain('123');
      expect(result.markdown).toContain('true');
      expect(result.markdown).toContain('object');
      expect(result.markdown).toContain('nested');
      expect(result.markdown).toContain('array');
    });
    
    it('should handle error objects', () => {
      const data = {
        error: {
          message: 'Something went wrong',
          code: 'ERR_001',
          stack: 'Error: Something went wrong\n    at test.js:10:5'
        }
      };
      const result = JsonToMarkdownConverter.convert(data);
      
      expect(result.markdown).toContain('Something went wrong');
      expect(result.markdown).toContain('ERR_001');
      expect(result.markdown).toContain('test.js:10:5');
    });
  });
});