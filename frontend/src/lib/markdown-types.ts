/**
 * TypeScript interfaces and types for Markdown Result Editor
 */

// Conversion Options Interface
export interface ConversionOptions {
  includeMetadata?: boolean;
  maxDepth?: number;
  tableFormat?: 'simple' | 'github';
  maxContentSize?: number; // Maximum content size in characters
  truncateThreshold?: number; // Truncation threshold
}

// Conversion Result Interface
export interface ConversionResult {
  markdown: string;
  isTruncated: boolean;
  originalSize: number;
  truncatedSize: number;
  warnings: string[];
}

// Task Status Check Result Interface
export interface TaskStatusResult {
  canEdit: boolean;
  reason?: string;
  suggestion?: string;
}

// Edit History Entry Interface
export interface EditHistoryEntry {
  content: string;
  timestamp: Date;
  operationType: 'manual' | 'paste' | 'undo' | 'redo' | 'reset' | 'format' | 'import';
  description?: string;
  contentSize: number;
}

// Markdown Editor State Interface
export interface MarkdownEditorState {
  // Original data
  originalMarkdown: string;
  
  // Edit state
  currentMarkdown: string;
  isEdited: boolean;
  editHistory: EditHistoryEntry[];
  historyIndex: number;
  
  // UI state
  isPreviewMode: boolean;
  isSplitView: boolean;
  
  // Auto-save
  lastSaved: Date | null;
  autoSaveEnabled: boolean;
}

// Local Storage Data Interface
export interface LocalStorageData {
  taskId: string;
  content: string;
  timestamp: number;
  version: string;
}

// Export Options Interface
export interface ExportOptions {
  format: 'markdown' | 'html';
  filename?: string;
  includeMetadata?: boolean;
}

// Export Result Interface
export interface ExportResult {
  content: string;
  filename: string;
  mimeType: string;
}

// Format Types for Toolbar
export type FormatType = 
  | 'bold' 
  | 'italic' 
  | 'heading1' 
  | 'heading2' 
  | 'heading3'
  | 'unordered-list' 
  | 'ordered-list' 
  | 'link' 
  | 'code' 
  | 'quote';

// Content Processing Result Interface
export interface ContentProcessingResult {
  content: string;
  isTruncated: boolean;
  processedSize: number;
}

// Markdown Editor Props Interfaces
export interface MarkdownEditorContainerProps {
  taskId: string;
  onBack: () => void;
}

export interface MarkdownToolbarProps {
  onFormat: (type: FormatType, text?: string) => void;
  disabled?: boolean;
}

export interface MarkdownPreviewProps {
  content: string;
  className?: string;
  onScroll?: (scrollTop: number) => void;
}

// Error Recovery Actions
export const ErrorRecoveryActions = {
  RETRY: 'retry',
  RESET: 'reset',
  GO_BACK: 'go_back'
} as const;

export type ErrorRecoveryAction = typeof ErrorRecoveryActions[keyof typeof ErrorRecoveryActions];