import type { Task } from '@/types'

export interface ResultSummary {
  overview: string
  keyFindings: string[]
  dataStructure: {
    type: 'object' | 'array' | 'primitive'
    size: number
    depth: number
    complexity: 'low' | 'medium' | 'high'
  }
  insights: {
    type: 'pattern' | 'anomaly' | 'trend' | 'highlight'
    description: string
    confidence: number
    data?: any
  }[]
  recommendations: string[]
  metadata: {
    processingTime: number
    dataQuality: number
    completeness: number
  }
}

export interface KeyInformation {
  path: string
  value: any
  importance: number
  category: 'critical' | 'important' | 'informational'
  description: string
}

export class ResultAnalyzer {
  /**
   * Generate a comprehensive summary of task results
   */
  static generateSummary(task: Task): ResultSummary {
    if (!task.results) {
      return this.getEmptySummary()
    }

    const dataStructure = this.analyzeDataStructure(task.results)
    const keyFindings = this.extractKeyFindings(task.results)
    const insights = this.generateInsights(task.results, task)
    const recommendations = this.generateRecommendations(task.results, task)
    const overview = this.generateOverview(task, dataStructure, keyFindings)
    const metadata = this.analyzeMetadata(task)

    return {
      overview,
      keyFindings,
      dataStructure,
      insights,
      recommendations,
      metadata
    }
  }

  /**
   * Extract and highlight key information from results
   */
  static extractKeyInformation(results: any): KeyInformation[] {
    const keyInfo: KeyInformation[] = []
    
    this.traverseObject(results, (path, value, depth) => {
      const importance = this.calculateImportance(path, value, depth || 0)
      
      if (importance > 0.5) {
        keyInfo.push({
          path,
          value,
          importance,
          category: importance > 0.8 ? 'critical' : importance > 0.6 ? 'important' : 'informational',
          description: this.generateDescription(path, value)
        })
      }
    })

    return keyInfo.sort((a, b) => b.importance - a.importance).slice(0, 20)
  }

  /**
   * Compare multiple results and highlight differences
   */
  static compareResults(tasks: Task[]): {
    commonPatterns: string[]
    uniqueElements: { taskId: string; elements: string[] }[]
    differences: { path: string; values: { [taskId: string]: any } }[]
    similarity: number
  } {
    const tasksWithResults = tasks.filter(task => task.results)
    
    if (tasksWithResults.length < 2) {
      return {
        commonPatterns: [],
        uniqueElements: [],
        differences: [],
        similarity: 0
      }
    }

    const allPaths = new Set<string>()
    const pathValues: { [path: string]: { [taskId: string]: any } } = {}

    // Extract all paths from all tasks
    tasksWithResults.forEach(task => {
      this.traverseObject(task.results, (path, value) => {
        allPaths.add(path)
        if (!pathValues[path]) pathValues[path] = {}
        pathValues[path][task.id] = value
      })
    })

    // Analyze differences
    const differences: { path: string; values: { [taskId: string]: any } }[] = []
    const commonPaths: string[] = []

    Array.from(allPaths).forEach(path => {
      const values = pathValues[path]
      const taskIds = Object.keys(values)
      const uniqueValues = new Set(taskIds.map(id => JSON.stringify(values[id])))

      if (uniqueValues.size > 1) {
        differences.push({ path, values })
      } else if (taskIds.length === tasksWithResults.length) {
        commonPaths.push(path)
      }
    })

    // Calculate similarity
    const totalPaths = allPaths.size
    const similarity = totalPaths > 0 ? commonPaths.length / totalPaths : 0

    // Find unique elements per task
    const uniqueElements = tasksWithResults.map(task => ({
      taskId: task.id,
      elements: Array.from(allPaths).filter(path => 
        pathValues[path][task.id] !== undefined && 
        Object.keys(pathValues[path]).length === 1
      )
    }))

    return {
      commonPatterns: commonPaths.slice(0, 10),
      uniqueElements,
      differences: differences.slice(0, 20),
      similarity
    }
  }

  /**
   * Generate insights about data quality and completeness
   */
  static analyzeDataQuality(results: any): {
    completeness: number
    consistency: number
    accuracy: number
    issues: { type: string; description: string; severity: 'low' | 'medium' | 'high' }[]
  } {
    const issues: { type: string; description: string; severity: 'low' | 'medium' | 'high' }[] = []
    let totalFields = 0
    let completeFields = 0
    let consistentFields = 0

    this.traverseObject(results, (path, value) => {
      totalFields++
      
      // Check completeness
      if (value !== null && value !== undefined && value !== '') {
        completeFields++
      } else {
        issues.push({
          type: 'missing_data',
          description: `Missing or empty value at ${path}`,
          severity: 'medium'
        })
      }

      // Check consistency
      if (this.isConsistentValue(value)) {
        consistentFields++
      } else {
        issues.push({
          type: 'inconsistent_data',
          description: `Inconsistent data format at ${path}`,
          severity: 'low'
        })
      }

      // Check for potential accuracy issues
      if (this.isPotentiallyInaccurate(path, value)) {
        issues.push({
          type: 'accuracy_concern',
          description: `Potentially inaccurate value at ${path}`,
          severity: 'high'
        })
      }
    })

    return {
      completeness: totalFields > 0 ? completeFields / totalFields : 1,
      consistency: totalFields > 0 ? consistentFields / totalFields : 1,
      accuracy: 1 - (issues.filter(i => i.severity === 'high').length / Math.max(totalFields, 1)),
      issues: issues.slice(0, 10)
    }
  }

  /**
   * Private helper methods
   */
  private static getEmptySummary(): ResultSummary {
    return {
      overview: 'No results available for analysis',
      keyFindings: [],
      dataStructure: {
        type: 'primitive',
        size: 0,
        depth: 0,
        complexity: 'low'
      },
      insights: [],
      recommendations: ['Process the document to generate results'],
      metadata: {
        processingTime: 0,
        dataQuality: 0,
        completeness: 0
      }
    }
  }

  private static analyzeDataStructure(data: any): ResultSummary['dataStructure'] {
    const size = this.calculateDataSize(data)
    const depth = this.calculateDepth(data)
    const type = Array.isArray(data) ? 'array' : typeof data === 'object' ? 'object' : 'primitive'
    
    let complexity: 'low' | 'medium' | 'high' = 'low'
    if (size > 100 || depth > 5) complexity = 'high'
    else if (size > 20 || depth > 3) complexity = 'medium'

    return { type, size, depth, complexity }
  }

  private static extractKeyFindings(data: any): string[] {
    const findings: string[] = []
    
    if (Array.isArray(data)) {
      findings.push(`Contains ${data.length} items`)
      if (data.length > 0) {
        const itemTypes = new Set(data.map(item => typeof item))
        findings.push(`Item types: ${Array.from(itemTypes).join(', ')}`)
      }
    } else if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data)
      findings.push(`Contains ${keys.length} properties`)
      
      // Find interesting patterns
      const textFields = keys.filter(key => typeof data[key] === 'string')
      const numberFields = keys.filter(key => typeof data[key] === 'number')
      const arrayFields = keys.filter(key => Array.isArray(data[key]))
      
      if (textFields.length > 0) findings.push(`${textFields.length} text fields`)
      if (numberFields.length > 0) findings.push(`${numberFields.length} numeric fields`)
      if (arrayFields.length > 0) findings.push(`${arrayFields.length} array fields`)
    }

    return findings.slice(0, 5)
  }

  private static generateInsights(data: any, task: Task): ResultSummary['insights'] {
    const insights: ResultSummary['insights'] = []

    // Pattern detection
    if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data)
      
      // Look for common patterns
      const dateFields = keys.filter(key => 
        typeof data[key] === 'string' && this.isDateString(data[key])
      )
      
      if (dateFields.length > 0) {
        insights.push({
          type: 'pattern',
          description: `Found ${dateFields.length} date field(s): ${dateFields.join(', ')}`,
          confidence: 0.8,
          data: dateFields
        })
      }

      // Look for potential issues
      const emptyFields = keys.filter(key => 
        data[key] === null || data[key] === undefined || data[key] === ''
      )
      
      if (emptyFields.length > keys.length * 0.3) {
        insights.push({
          type: 'anomaly',
          description: `High number of empty fields (${emptyFields.length}/${keys.length})`,
          confidence: 0.7
        })
      }
    }

    // Processing insights
    if (task.actual_cost && task.estimated_cost) {
      const costDiff = Math.abs(task.actual_cost - task.estimated_cost) / task.estimated_cost
      if (costDiff > 0.2) {
        insights.push({
          type: 'highlight',
          description: `Processing cost ${costDiff > 0 ? 'exceeded' : 'was lower than'} estimate by ${(costDiff * 100).toFixed(1)}%`,
          confidence: 0.9
        })
      }
    }

    return insights
  }

  private static generateRecommendations(data: any, task: Task): string[] {
    const recommendations: string[] = []

    // Data structure recommendations
    if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data)
      const emptyFields = keys.filter(key => 
        data[key] === null || data[key] === undefined || data[key] === ''
      )

      if (emptyFields.length > 0) {
        recommendations.push(`Consider reprocessing to fill ${emptyFields.length} empty fields`)
      }

      if (keys.length > 50) {
        recommendations.push('Consider using structured export formats for large datasets')
      }
    }

    // Processing recommendations
    if (task.actual_cost && task.actual_cost > 0.1) {
      recommendations.push('Consider optimizing processing settings to reduce costs')
    }

    if (!recommendations.length) {
      recommendations.push('Results look good - no specific recommendations')
    }

    return recommendations.slice(0, 3)
  }

  private static generateOverview(task: Task, structure: ResultSummary['dataStructure'], findings: string[]): string {
    const filename = task.original_filename || 'document'
    const complexity = structure.complexity
    const size = structure.size

    let overview = `Analysis of ${filename} completed successfully. `
    
    if (complexity === 'high') {
      overview += `This is a complex document with ${size} data points across ${structure.depth} levels. `
    } else if (complexity === 'medium') {
      overview += `This document contains moderate complexity with ${size} data points. `
    } else {
      overview += `This is a simple document with ${size} data points. `
    }

    if (findings.length > 0) {
      overview += `Key characteristics: ${findings.slice(0, 2).join(', ')}.`
    }

    return overview
  }

  private static analyzeMetadata(task: Task): ResultSummary['metadata'] {
    const processingTime = task.completed_at && task.created_at 
      ? new Date(task.completed_at).getTime() - new Date(task.created_at).getTime()
      : 0

    const quality = this.analyzeDataQuality(task.results)

    return {
      processingTime,
      dataQuality: (quality.completeness + quality.consistency + quality.accuracy) / 3,
      completeness: quality.completeness
    }
  }

  private static traverseObject(obj: any, callback: (path: string, value: any, depth?: number) => void, path = '', depth = 0) {
    if (obj === null || obj === undefined) return

    callback(path, obj, depth)

    if (typeof obj === 'object' && !Array.isArray(obj)) {
      Object.keys(obj).forEach(key => {
        const newPath = path ? `${path}.${key}` : key
        this.traverseObject(obj[key], callback, newPath, depth + 1)
      })
    } else if (Array.isArray(obj)) {
      obj.forEach((item, index) => {
        const newPath = `${path}[${index}]`
        this.traverseObject(item, callback, newPath, depth + 1)
      })
    }
  }

  private static calculateDataSize(data: any): number {
    if (data === null || data === undefined) return 0
    if (typeof data !== 'object') return 1
    
    if (Array.isArray(data)) {
      return data.reduce((sum, item) => sum + this.calculateDataSize(item), 0)
    }
    
    return Object.keys(data).reduce((sum, key) => sum + this.calculateDataSize(data[key]), 0) + 1
  }

  private static calculateDepth(data: any, currentDepth = 0): number {
    if (data === null || data === undefined || typeof data !== 'object') {
      return currentDepth
    }

    if (Array.isArray(data)) {
      return Math.max(...data.map(item => this.calculateDepth(item, currentDepth + 1)), currentDepth)
    }

    const depths = Object.values(data).map(value => this.calculateDepth(value, currentDepth + 1))
    return Math.max(...depths, currentDepth)
  }

  private static calculateImportance(path: string, value: any, depth: number): number {
    let importance = 0.5

    // Path-based importance
    if (path.includes('id') || path.includes('name') || path.includes('title')) importance += 0.3
    if (path.includes('error') || path.includes('warning')) importance += 0.2
    if (path.includes('result') || path.includes('output')) importance += 0.2

    // Value-based importance
    if (typeof value === 'string' && value.length > 10) importance += 0.1
    if (typeof value === 'number' && value !== 0) importance += 0.1
    if (Array.isArray(value) && value.length > 0) importance += 0.2

    // Depth penalty
    importance -= depth * 0.1

    return Math.max(0, Math.min(1, importance))
  }

  private static generateDescription(path: string, value: any): string {
    if (path.includes('id')) return 'Identifier field'
    if (path.includes('name') || path.includes('title')) return 'Name or title field'
    if (path.includes('date') || path.includes('time')) return 'Date/time field'
    if (path.includes('count') || path.includes('total')) return 'Count or total value'
    if (Array.isArray(value)) return `Array with ${value.length} items`
    if (typeof value === 'object') return 'Object containing structured data'
    if (typeof value === 'string') return 'Text content'
    if (typeof value === 'number') return 'Numeric value'
    return 'Data field'
  }

  private static isDateString(str: string): boolean {
    return !isNaN(Date.parse(str)) && str.match(/\d{4}-\d{2}-\d{2}/) !== null
  }

  private static isConsistentValue(value: any): boolean {
    // Simple consistency check - in a real implementation, this would be more sophisticated
    if (typeof value === 'string') return value.trim().length > 0
    if (typeof value === 'number') return !isNaN(value) && isFinite(value)
    return true
  }

  private static isPotentiallyInaccurate(path: string, value: any): boolean {
    // Simple accuracy check - in a real implementation, this would be more sophisticated
    if (typeof value === 'number' && (value < 0 && path.includes('count'))) return true
    if (typeof value === 'string' && value.includes('error') && !path.includes('error')) return true
    return false
  }
}