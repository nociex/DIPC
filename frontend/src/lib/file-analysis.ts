/**
 * Smart File Analysis Service
 * Provides intelligent file type detection, processing suggestions,
 * cost estimation, and compatibility warnings
 */

import { TaskOptions, StoragePolicy } from '@/types'

// File analysis result interface
export interface FileAnalysisResult {
  fileType: string
  category: FileCategory
  suggestedConfig: TaskOptions
  estimatedCost: number
  estimatedTime: number // in seconds
  compatibility: CompatibilityLevel
  warnings: string[]
  recommendations: string[]
  processingSteps: ProcessingStep[]
  metadata: FileMetadata
}

// File categories
export type FileCategory = 'document' | 'image' | 'archive' | 'text' | 'unknown'

// Compatibility levels
export type CompatibilityLevel = 'excellent' | 'good' | 'fair' | 'poor'

// Processing steps
export interface ProcessingStep {
  id: string
  name: string
  description: string
  estimatedTime: number
  required: boolean
}

// File metadata
export interface FileMetadata {
  extension: string
  mimeType: string
  sizeCategory: 'small' | 'medium' | 'large' | 'xlarge'
  complexity: 'simple' | 'moderate' | 'complex'
  textDensity?: 'low' | 'medium' | 'high'
  imageCount?: number
  pageCount?: number
}

// File type configurations
const FILE_TYPE_CONFIGS = {
  // PDF Documents
  'application/pdf': {
    category: 'document' as FileCategory,
    compatibility: 'excellent' as CompatibilityLevel,
    baseProcessingTime: 30, // seconds per MB
    costMultiplier: 1.0,
    defaultConfig: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 2.0,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'extract', name: 'Text Extraction', description: 'Extract text from PDF', estimatedTime: 10, required: true },
      { id: 'ocr', name: 'OCR Processing', description: 'Process images and scanned text', estimatedTime: 20, required: false },
      { id: 'structure', name: 'Structure Analysis', description: 'Analyze document structure', estimatedTime: 15, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 25, required: false }
    ]
  },

  // Word Documents
  'application/msword': {
    category: 'document' as FileCategory,
    compatibility: 'good' as CompatibilityLevel,
    baseProcessingTime: 20,
    costMultiplier: 0.8,
    defaultConfig: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 1.5,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'extract', name: 'Content Extraction', description: 'Extract text and formatting', estimatedTime: 8, required: true },
      { id: 'clean', name: 'Text Cleaning', description: 'Clean and normalize text', estimatedTime: 5, required: true },
      { id: 'structure', name: 'Structure Analysis', description: 'Analyze document structure', estimatedTime: 10, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 15, required: false }
    ]
  },

  // DOCX Documents
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    category: 'document' as FileCategory,
    compatibility: 'excellent' as CompatibilityLevel,
    baseProcessingTime: 15,
    costMultiplier: 0.7,
    defaultConfig: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 1.2,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'extract', name: 'Content Extraction', description: 'Extract text and metadata', estimatedTime: 5, required: true },
      { id: 'structure', name: 'Structure Analysis', description: 'Analyze document structure', estimatedTime: 8, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 12, required: false }
    ]
  },

  // Plain Text
  'text/plain': {
    category: 'text' as FileCategory,
    compatibility: 'excellent' as CompatibilityLevel,
    baseProcessingTime: 5,
    costMultiplier: 0.3,
    defaultConfig: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 0.5,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'clean', name: 'Text Cleaning', description: 'Clean and normalize text', estimatedTime: 2, required: true },
      { id: 'analyze', name: 'Content Analysis', description: 'Analyze text content', estimatedTime: 3, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 8, required: false }
    ]
  },

  // Images
  'image/jpeg': {
    category: 'image' as FileCategory,
    compatibility: 'good' as CompatibilityLevel,
    baseProcessingTime: 45,
    costMultiplier: 1.5,
    defaultConfig: {
      enable_vectorization: false,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 3.0,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'ocr', name: 'OCR Processing', description: 'Extract text from image', estimatedTime: 30, required: true },
      { id: 'analyze', name: 'Image Analysis', description: 'Analyze image content', estimatedTime: 15, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 20, required: false }
    ]
  },

  'image/png': {
    category: 'image' as FileCategory,
    compatibility: 'good' as CompatibilityLevel,
    baseProcessingTime: 40,
    costMultiplier: 1.4,
    defaultConfig: {
      enable_vectorization: false,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 2.8,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'ocr', name: 'OCR Processing', description: 'Extract text from image', estimatedTime: 25, required: true },
      { id: 'analyze', name: 'Image Analysis', description: 'Analyze image content', estimatedTime: 15, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 18, required: false }
    ]
  },

  // Archives
  'application/zip': {
    category: 'archive' as FileCategory,
    compatibility: 'fair' as CompatibilityLevel,
    baseProcessingTime: 60,
    costMultiplier: 2.0,
    defaultConfig: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 5.0,
      llm_provider: 'openai'
    },
    processingSteps: [
      { id: 'extract', name: 'Archive Extraction', description: 'Extract files from archive', estimatedTime: 20, required: true },
      { id: 'scan', name: 'Content Scanning', description: 'Scan extracted files', estimatedTime: 15, required: true },
      { id: 'process', name: 'Batch Processing', description: 'Process individual files', estimatedTime: 40, required: true },
      { id: 'vectorize', name: 'Vectorization', description: 'Create vector embeddings', estimatedTime: 30, required: false }
    ]
  }
} as const

// File size categories (in bytes)
const SIZE_CATEGORIES = {
  small: 1024 * 1024, // 1MB
  medium: 10 * 1024 * 1024, // 10MB
  large: 50 * 1024 * 1024, // 50MB
  xlarge: Infinity
}

// Base cost per MB for different operations
const BASE_COSTS = {
  textExtraction: 0.01,
  ocrProcessing: 0.05,
  vectorization: 0.02,
  imageAnalysis: 0.03,
  archiveProcessing: 0.04
}

/**
 * Smart File Analysis Service
 */
export class FileAnalysisService {
  /**
   * Analyze a single file and provide processing recommendations
   */
  static async analyzeFile(file: File): Promise<FileAnalysisResult> {
    const metadata = this.extractMetadata(file)
    const config = FILE_TYPE_CONFIGS[file.type as keyof typeof FILE_TYPE_CONFIGS]
    
    if (!config) {
      return this.createUnknownFileAnalysis(file, metadata)
    }

    const estimatedTime = this.calculateProcessingTime(file, config, metadata)
    const estimatedCost = this.calculateProcessingCost(file, config, metadata)
    const warnings = this.generateWarnings(file, metadata, config)
    const recommendations = this.generateRecommendations(file, metadata, config)

    return {
      fileType: file.type,
      category: config.category,
      suggestedConfig: { ...config.defaultConfig },
      estimatedCost,
      estimatedTime,
      compatibility: config.compatibility,
      warnings,
      recommendations,
      processingSteps: [...config.processingSteps],
      metadata
    }
  }

  /**
   * Analyze multiple files and suggest batch configuration
   */
  static async analyzeBatch(files: File[]): Promise<{
    individualAnalyses: FileAnalysisResult[]
    batchConfig: TaskOptions
    totalEstimatedCost: number
    totalEstimatedTime: number
    batchWarnings: string[]
    batchRecommendations: string[]
  }> {
    const individualAnalyses = await Promise.all(
      files.map(file => this.analyzeFile(file))
    )

    const batchConfig = this.generateBatchConfig(individualAnalyses)
    const totalEstimatedCost = individualAnalyses.reduce((sum, analysis) => sum + analysis.estimatedCost, 0)
    const totalEstimatedTime = Math.max(...individualAnalyses.map(analysis => analysis.estimatedTime))
    const batchWarnings = this.generateBatchWarnings(individualAnalyses)
    const batchRecommendations = this.generateBatchRecommendations(individualAnalyses)

    return {
      individualAnalyses,
      batchConfig,
      totalEstimatedCost,
      totalEstimatedTime,
      batchWarnings,
      batchRecommendations
    }
  }

  /**
   * Extract metadata from file
   */
  private static extractMetadata(file: File): FileMetadata {
    const extension = file.name.split('.').pop()?.toLowerCase() || ''
    const sizeCategory = this.getSizeCategory(file.size)
    const complexity = this.estimateComplexity(file)

    return {
      extension,
      mimeType: file.type,
      sizeCategory,
      complexity
    }
  }

  /**
   * Get file size category
   */
  private static getSizeCategory(size: number): 'small' | 'medium' | 'large' | 'xlarge' {
    if (size <= SIZE_CATEGORIES.small) return 'small'
    if (size <= SIZE_CATEGORIES.medium) return 'medium'
    if (size <= SIZE_CATEGORIES.large) return 'large'
    return 'xlarge'
  }

  /**
   * Estimate file complexity based on size and type
   */
  private static estimateComplexity(file: File): 'simple' | 'moderate' | 'complex' {
    const sizeMB = file.size / (1024 * 1024)
    
    if (file.type.startsWith('text/')) {
      return sizeMB < 1 ? 'simple' : sizeMB < 5 ? 'moderate' : 'complex'
    }
    
    if (file.type.startsWith('image/')) {
      return sizeMB < 2 ? 'simple' : sizeMB < 10 ? 'moderate' : 'complex'
    }
    
    if (file.type === 'application/pdf') {
      return sizeMB < 5 ? 'simple' : sizeMB < 20 ? 'moderate' : 'complex'
    }
    
    if (file.type.includes('zip') || file.type.includes('archive')) {
      return sizeMB < 10 ? 'moderate' : 'complex'
    }
    
    return 'moderate'
  }

  /**
   * Calculate processing time estimate
   */
  private static calculateProcessingTime(
    file: File, 
    config: typeof FILE_TYPE_CONFIGS[keyof typeof FILE_TYPE_CONFIGS],
    metadata: FileMetadata
  ): number {
    const sizeMB = file.size / (1024 * 1024)
    let baseTime = config.baseProcessingTime * sizeMB
    
    // Apply complexity multiplier
    const complexityMultipliers = { simple: 0.8, moderate: 1.0, complex: 1.5 }
    baseTime *= complexityMultipliers[metadata.complexity]
    
    // Apply size category multiplier
    const sizeMultipliers = { small: 0.9, medium: 1.0, large: 1.2, xlarge: 1.5 }
    baseTime *= sizeMultipliers[metadata.sizeCategory]
    
    return Math.max(5, Math.round(baseTime)) // Minimum 5 seconds
  }

  /**
   * Calculate processing cost estimate
   */
  private static calculateProcessingCost(
    file: File,
    config: typeof FILE_TYPE_CONFIGS[keyof typeof FILE_TYPE_CONFIGS],
    metadata: FileMetadata
  ): number {
    const sizeMB = file.size / (1024 * 1024)
    let baseCost = 0
    
    // Calculate cost based on processing steps
    config.processingSteps.forEach(step => {
      switch (step.id) {
        case 'extract':
        case 'clean':
          baseCost += BASE_COSTS.textExtraction * sizeMB
          break
        case 'ocr':
          baseCost += BASE_COSTS.ocrProcessing * sizeMB
          break
        case 'vectorize':
          baseCost += BASE_COSTS.vectorization * sizeMB
          break
        case 'analyze':
          if (config.category === 'image') {
            baseCost += BASE_COSTS.imageAnalysis * sizeMB
          } else {
            baseCost += BASE_COSTS.textExtraction * sizeMB
          }
          break
        case 'process':
          baseCost += BASE_COSTS.archiveProcessing * sizeMB
          break
      }
    })
    
    // Apply cost multiplier
    baseCost *= config.costMultiplier
    
    // Apply complexity multiplier
    const complexityMultipliers = { simple: 0.8, moderate: 1.0, complex: 1.3 }
    baseCost *= complexityMultipliers[metadata.complexity]
    
    return Math.round(baseCost * 100) / 100 // Round to 2 decimal places
  }

  /**
   * Generate warnings for file
   */
  private static generateWarnings(
    file: File,
    metadata: FileMetadata,
    config: typeof FILE_TYPE_CONFIGS[keyof typeof FILE_TYPE_CONFIGS]
  ): string[] {
    const warnings: string[] = []
    
    // Size warnings
    if (metadata.sizeCategory === 'xlarge') {
      warnings.push('Large file size may result in longer processing times and higher costs')
    }
    
    // Compatibility warnings
    if (config.compatibility === 'fair') {
      warnings.push('This file type has limited processing capabilities')
    } else if (config.compatibility === 'poor') {
      warnings.push('This file type may not process correctly')
    }
    
    // Complexity warnings
    if (metadata.complexity === 'complex') {
      warnings.push('Complex file structure may require additional processing time')
    }
    
    // Type-specific warnings
    if (file.type.includes('zip') || file.type.includes('archive')) {
      warnings.push('Archive files will be extracted and processed individually')
    }
    
    if (file.type.startsWith('image/')) {
      warnings.push('Image processing requires OCR which may be less accurate than text extraction')
    }
    
    return warnings
  }

  /**
   * Generate recommendations for file
   */
  private static generateRecommendations(
    file: File,
    metadata: FileMetadata,
    config: typeof FILE_TYPE_CONFIGS[keyof typeof FILE_TYPE_CONFIGS]
  ): string[] {
    const recommendations: string[] = []
    
    // Size recommendations
    if (metadata.sizeCategory === 'xlarge') {
      recommendations.push('Consider splitting large files into smaller chunks for better performance')
    }
    
    // Type-specific recommendations
    if (file.type === 'application/pdf' && metadata.complexity === 'complex') {
      recommendations.push('Enable OCR processing for scanned PDF content')
    }
    
    if (file.type.startsWith('image/')) {
      recommendations.push('Ensure images have good contrast and resolution for better OCR results')
    }
    
    if (file.type.includes('zip')) {
      recommendations.push('Ensure archive contains supported file types for optimal processing')
    }
    
    // Vectorization recommendations
    if (config.defaultConfig.enable_vectorization) {
      recommendations.push('Vectorization is recommended for this file type to enable semantic search')
    }
    
    return recommendations
  }

  /**
   * Create analysis for unknown file types
   */
  private static createUnknownFileAnalysis(file: File, metadata: FileMetadata): FileAnalysisResult {
    return {
      fileType: file.type || 'unknown',
      category: 'unknown',
      suggestedConfig: {
        enable_vectorization: false,
        storage_policy: StoragePolicy.TEMPORARY,
        max_cost_limit: 1.0,
        llm_provider: 'openai'
      },
      estimatedCost: 0,
      estimatedTime: 0,
      compatibility: 'poor',
      warnings: ['Unsupported file type - processing may not be available'],
      recommendations: ['Convert to a supported format (PDF, DOCX, TXT, JPG, PNG, ZIP)'],
      processingSteps: [],
      metadata
    }
  }

  /**
   * Generate batch configuration from individual analyses
   */
  private static generateBatchConfig(analyses: FileAnalysisResult[]): TaskOptions {
    const hasVectorization = analyses.some(a => a.suggestedConfig.enable_vectorization)
    const maxCostLimit = Math.max(...analyses.map(a => a.suggestedConfig.max_cost_limit || 1.0))
    const hasLongTermStorage = analyses.some(a => a.suggestedConfig.storage_policy === StoragePolicy.PERMANENT)
    
    return {
      enable_vectorization: hasVectorization,
      storage_policy: hasLongTermStorage ? StoragePolicy.PERMANENT : StoragePolicy.TEMPORARY,
      max_cost_limit: maxCostLimit * 1.2, // Add 20% buffer for batch processing
      llm_provider: 'openai'
    }
  }

  /**
   * Generate batch warnings
   */
  private static generateBatchWarnings(analyses: FileAnalysisResult[]): string[] {
    const warnings: string[] = []
    
    const hasLargeFiles = analyses.some(a => a.metadata.sizeCategory === 'xlarge')
    const hasComplexFiles = analyses.some(a => a.metadata.complexity === 'complex')
    const hasPoorCompatibility = analyses.some(a => a.compatibility === 'poor')
    const totalCost = analyses.reduce((sum, a) => sum + a.estimatedCost, 0)
    
    if (hasLargeFiles) {
      warnings.push('Batch contains large files that may slow down processing')
    }
    
    if (hasComplexFiles) {
      warnings.push('Some files in the batch are complex and may require additional processing time')
    }
    
    if (hasPoorCompatibility) {
      warnings.push('Some files in the batch may not process correctly due to compatibility issues')
    }
    
    if (totalCost > 10) {
      warnings.push('Batch processing cost is high - consider processing files individually')
    }
    
    return warnings
  }

  /**
   * Generate batch recommendations
   */
  private static generateBatchRecommendations(analyses: FileAnalysisResult[]): string[] {
    const recommendations: string[] = []
    
    const categories = Array.from(new Set(analyses.map(a => a.category)))
    const hasImages = categories.includes('image')
    const hasDocuments = categories.includes('document')
    const hasArchives = categories.includes('archive')
    
    if (categories.length > 2) {
      recommendations.push('Consider grouping similar file types for more efficient batch processing')
    }
    
    if (hasImages && hasDocuments) {
      recommendations.push('Process images and documents separately for optimal results')
    }
    
    if (hasArchives) {
      recommendations.push('Process archive files separately as they may contain multiple file types')
    }
    
    const avgComplexity = analyses.reduce((sum, a) => {
      const complexityScores = { simple: 1, moderate: 2, complex: 3 }
      return sum + complexityScores[a.metadata.complexity]
    }, 0) / analyses.length
    
    if (avgComplexity > 2) {
      recommendations.push('Enable extended processing time for complex files in this batch')
    }
    
    return recommendations
  }
}

/**
 * Utility functions for file analysis
 */
export const FileAnalysisUtils = {
  /**
   * Format file size for display
   */
  formatFileSize: (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },

  /**
   * Format processing time for display
   */
  formatProcessingTime: (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  },

  /**
   * Format cost for display
   */
  formatCost: (cost: number): string => {
    return `$${cost.toFixed(2)}`
  },

  /**
   * Get compatibility color
   */
  getCompatibilityColor: (compatibility: CompatibilityLevel): string => {
    const colors = {
      excellent: 'text-green-600',
      good: 'text-blue-600',
      fair: 'text-yellow-600',
      poor: 'text-red-600'
    }
    return colors[compatibility]
  },

  /**
   * Get category icon
   */
  getCategoryIcon: (category: FileCategory): string => {
    const icons = {
      document: 'FileText',
      image: 'Image',
      archive: 'Archive',
      text: 'FileText',
      unknown: 'File'
    }
    return icons[category]
  }
}