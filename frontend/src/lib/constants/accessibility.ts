/**
 * Accessibility constants for ARIA labels, announcements, and other a11y-related strings
 */

export const ARIA_LABELS = {
  // Navigation
  skipToMain: 'Skip to main content',
  skipToNavigation: 'Skip to navigation',
  skipToUpload: 'Skip to upload section',
  skipToResults: 'Skip to results section',
  mainNavigation: 'Main navigation',
  
  // File Upload
  fileUploadDropZone: 'File upload drop zone. Drag and drop files here or click to browse',
  removeFile: (fileName: string) => `Remove ${fileName} from upload queue`,
  filePreview: (fileName: string) => `Preview of ${fileName}`,
  uploadProgress: (fileName: string, progress: number) => `Upload progress for ${fileName}: ${progress}%`,
  
  // Task Management
  taskStatus: (status: string) => `Task status: ${status}`,
  taskResults: 'Task results viewer',
  viewResults: 'View task results',
  downloadResults: 'Download task results',
  
  // Form Controls
  enableVectorization: 'Enable vectorization for semantic search',
  storagePolicy: 'Select storage policy for processed files',
  costLimit: (amount: number) => `Set maximum cost limit to $${amount}`,
  
  // Interactive Elements
  toggleView: (currentView: string, targetView: string) => `Switch from ${currentView} to ${targetView} view`,
  copyToClipboard: 'Copy results to clipboard',
  closeDialog: 'Close dialog',
  expandCollapse: (isExpanded: boolean) => isExpanded ? 'Collapse' : 'Expand',
  
  // Settings
  accessibilitySettings: 'Accessibility settings',
  languageSelection: 'Select language',
  themeSelection: 'Select theme',
} as const

export const ANNOUNCEMENTS = {
  // File Operations
  fileAdded: (count: number) => `${count} file${count === 1 ? '' : 's'} added to upload queue`,
  fileRemoved: (fileName: string) => `${fileName} removed from upload queue`,
  allFilesCleared: (count: number) => `All ${count} files cleared from upload queue`,
  uploadStarted: (fileName: string) => `Uploading ${fileName}`,
  uploadCompleted: (fileName: string) => `${fileName} uploaded successfully`,
  uploadFailed: (fileName: string) => `Failed to upload ${fileName}`,
  
  // Task Operations
  taskCreated: 'Processing task created',
  taskCompleted: 'Task completed successfully',
  taskFailed: 'Task failed',
  resultsLoaded: 'Results loaded',
  
  // Navigation
  tabChanged: (tabName: string) => `Switched to ${tabName} tab`,
  sectionExpanded: (sectionName: string) => `${sectionName} section expanded`,
  sectionCollapsed: (sectionName: string) => `${sectionName} section collapsed`,
  
  // Form Updates
  settingChanged: (setting: string, value: string) => `${setting} changed to ${value}`,
  limitExceeded: (type: string) => `${type} limit exceeded`,
  
  // Copy Operations
  copiedToClipboard: 'Content copied to clipboard',
  copyFailed: 'Failed to copy to clipboard',
} as const

export const DESCRIPTIONS = {
  // Form Fields
  vectorization: 'Process documents for semantic search and AI-powered queries',
  storagePolicy: 'Choose how long processed files should be stored',
  costLimit: 'Set a spending limit for processing these documents',
  
  // Features
  dragAndDrop: 'Drag files here or click to browse. Supports PDF, images, ZIP archives, and documents',
  batchProcessing: 'Process multiple files simultaneously',
  semanticSearch: 'Search documents using natural language queries',
  
  // Status
  processing: 'Your documents are being processed',
  completed: 'Processing completed successfully',
  failed: 'Processing failed. Please try again',
} as const

export const KEYBOARD_SHORTCUTS = {
  // Navigation
  nextTab: 'Arrow Right',
  previousTab: 'Arrow Left',
  firstTab: 'Home',
  lastTab: 'End',
  
  // Actions
  submit: 'Enter',
  cancel: 'Escape',
  selectAll: 'Ctrl+A / Cmd+A',
  copy: 'Ctrl+C / Cmd+C',
  paste: 'Ctrl+V / Cmd+V',
  
  // Focus Management
  nextElement: 'Tab',
  previousElement: 'Shift+Tab',
  skipToMain: 'Alt+M',
} as const

export const ROLES = {
  // Landmarks
  banner: 'banner',
  navigation: 'navigation',
  main: 'main',
  complementary: 'complementary',
  contentinfo: 'contentinfo',
  
  // Widgets
  button: 'button',
  tab: 'tab',
  tablist: 'tablist',
  tabpanel: 'tabpanel',
  
  // Live Regions
  alert: 'alert',
  status: 'status',
  log: 'log',
  
  // Document Structure
  region: 'region',
  group: 'group',
  list: 'list',
  listitem: 'listitem',
} as const