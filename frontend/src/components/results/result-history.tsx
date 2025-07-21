"use client"

import { useState, useMemo, useCallback } from 'react'
import { 
  History, 
  Clock, 
  GitBranch, 
  Eye, 
  Download, 
  GitCompare,
  Star,
  StarOff,
  Tag,
  Calendar,
  User,
  FileText,
  Trash2,
  RotateCcw
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { useToast } from '@/components/ui/use-toast'
import { useI18n } from '@/lib/i18n/context'
import type { Task } from '@/types'

interface ResultVersion {
  id: string
  taskId: string
  version: number
  timestamp: Date
  results: any
  metadata: {
    processingTime: number
    cost: number
    configuration: any
    userNotes?: string
    tags: string[]
    starred: boolean
  }
  changes?: {
    added: string[]
    modified: string[]
    removed: string[]
  }
}

interface ResultHistoryProps {
  task: Task
  versions?: ResultVersion[]
  onVersionSelect?: (version: ResultVersion) => void
  onVersionCompare?: (versions: ResultVersion[]) => void
  onVersionRestore?: (version: ResultVersion) => void
  onVersionDelete?: (version: ResultVersion) => void
  onClose?: () => void
  className?: string
}

export function ResultHistory({ 
  task, 
  versions: providedVersions = [], 
  onVersionSelect,
  onVersionCompare,
  onVersionRestore,
  onVersionDelete,
  onClose, 
  className 
}: ResultHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedVersions, setSelectedVersions] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'timestamp' | 'version' | 'cost'>('timestamp')
  const [filterBy, setFilterBy] = useState<'all' | 'starred' | 'tagged'>('all')
  const [showChangesOnly, setShowChangesOnly] = useState(false)
  
  const { t } = useI18n()
  const { toast } = useToast()

  // Generate mock versions if none provided (for demo purposes)
  const mockVersions = useMemo((): ResultVersion[] => {
    if (providedVersions.length > 0) return providedVersions
    
    // Create mock version history based on the current task
    const baseVersion: ResultVersion = {
      id: `${task.id}-v1`,
      taskId: task.id,
      version: 1,
      timestamp: new Date(task.created_at),
      results: task.results,
      metadata: {
        processingTime: 45000,
        cost: task.actual_cost || 0.025,
        configuration: task.options || {},
        tags: ['initial', 'auto-generated'],
        starred: false
      }
    }

    const versions: ResultVersion[] = [baseVersion]

    // Add some mock historical versions
    if (task.results) {
      const version2: ResultVersion = {
        id: `${task.id}-v2`,
        taskId: task.id,
        version: 2,
        timestamp: new Date(Date.now() - 86400000), // 1 day ago
        results: { ...task.results, processed_at: new Date(Date.now() - 86400000).toISOString() },
        metadata: {
          processingTime: 52000,
          cost: 0.032,
          configuration: { ...task.options, quality: 'high' },
          userNotes: 'Reprocessed with higher quality settings',
          tags: ['reprocessed', 'high-quality'],
          starred: true
        },
        changes: {
          added: ['metadata.quality_score'],
          modified: ['processed_at', 'configuration.quality'],
          removed: []
        }
      }

      const version3: ResultVersion = {
        id: `${task.id}-v3`,
        taskId: task.id,
        version: 3,
        timestamp: new Date(Date.now() - 43200000), // 12 hours ago
        results: task.results,
        metadata: {
          processingTime: 38000,
          cost: 0.019,
          configuration: { ...task.options, optimization: true },
          userNotes: 'Optimized processing pipeline',
          tags: ['optimized', 'cost-effective'],
          starred: false
        },
        changes: {
          added: ['optimization_metrics'],
          modified: ['processing_time', 'cost'],
          removed: ['temporary_data']
        }
      }

      versions.push(version2, version3)
    }

    return versions
  }, [task, providedVersions])

  // Filter and sort versions
  const filteredVersions = useMemo(() => {
    let filtered = mockVersions

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(version => 
        version.metadata.userNotes?.toLowerCase().includes(query) ||
        version.metadata.tags.some(tag => tag.toLowerCase().includes(query)) ||
        version.version.toString().includes(query)
      )
    }

    // Apply category filter
    if (filterBy === 'starred') {
      filtered = filtered.filter(version => version.metadata.starred)
    } else if (filterBy === 'tagged') {
      filtered = filtered.filter(version => version.metadata.tags.length > 0)
    }

    // Apply changes filter
    if (showChangesOnly) {
      filtered = filtered.filter(version => version.changes)
    }

    // Sort versions
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'version':
          return b.version - a.version
        case 'cost':
          return a.metadata.cost - b.metadata.cost
        case 'timestamp':
        default:
          return b.timestamp.getTime() - a.timestamp.getTime()
      }
    })

    return filtered
  }, [mockVersions, searchQuery, filterBy, showChangesOnly, sortBy])

  const toggleVersionSelection = useCallback((versionId: string) => {
    setSelectedVersions(prev => 
      prev.includes(versionId) 
        ? prev.filter(id => id !== versionId)
        : [...prev, versionId]
    )
  }, [])

  const handleCompareSelected = useCallback(() => {
    const versionsToCompare = mockVersions.filter(v => selectedVersions.includes(v.id))
    if (versionsToCompare.length >= 2) {
      onVersionCompare?.(versionsToCompare)
    } else {
      toast({
        title: t('common.error'),
        description: 'Select at least 2 versions to compare',
        variant: 'destructive'
      })
    }
  }, [selectedVersions, mockVersions, onVersionCompare, toast, t])

  const toggleStar = useCallback(async (version: ResultVersion) => {
    // In a real implementation, this would make an API call
    toast({
      title: t('common.success'),
      description: version.metadata.starred ? 'Removed from favorites' : 'Added to favorites'
    })
  }, [toast, t])

  const formatDuration = (ms: number): string => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
  }

  const formatTimestamp = (date: Date): string => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = diffMs / (1000 * 60 * 60)
    const diffDays = diffHours / 24

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${Math.floor(diffHours)} hours ago`
    if (diffDays < 7) return `${Math.floor(diffDays)} days ago`
    
    return date.toLocaleDateString()
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Result History
            </CardTitle>
            <CardDescription>
              {filteredVersions.length} version{filteredVersions.length !== 1 ? 's' : ''} of {task.original_filename || task.id.slice(0, 8) + '...'}
            </CardDescription>
          </div>
          
          <div className="flex items-center space-x-2">
            {selectedVersions.length >= 2 && (
              <Button variant="outline" size="sm" onClick={handleCompareSelected}>
                <GitCompare className="h-4 w-4 mr-2" />
                Compare ({selectedVersions.length})
              </Button>
            )}
            
            {onClose && (
              <Button variant="outline" size="sm" onClick={onClose}>
                ×
              </Button>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-4 pt-4">
          <div className="flex-1 relative">
            <Input
              placeholder="Search versions, notes, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="timestamp">Recent</SelectItem>
              <SelectItem value="version">Version</SelectItem>
              <SelectItem value="cost">Cost</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={filterBy} onValueChange={(value: any) => setFilterBy(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="starred">Starred</SelectItem>
              <SelectItem value="tagged">Tagged</SelectItem>
            </SelectContent>
          </Select>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="changes-only"
              checked={showChangesOnly}
              onCheckedChange={(checked) => setShowChangesOnly(checked === true)}
            />
            <label htmlFor="changes-only" className="text-sm">
              Changes only
            </label>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4 max-h-96 overflow-auto">
          {filteredVersions.map((version, index) => (
            <Card key={version.id} className="p-4">
              <div className="flex items-start space-x-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    checked={selectedVersions.includes(version.id)}
                    onCheckedChange={() => toggleVersionSelection(version.id)}
                  />
                  
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-medium text-blue-600">
                      v{version.version}
                    </div>
                    {index < filteredVersions.length - 1 && (
                      <div className="w-px h-8 bg-gray-200 mt-2" />
                    )}
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">Version {version.version}</span>
                      <Badge variant="outline" className="text-xs">
                        {formatTimestamp(version.timestamp)}
                      </Badge>
                      {version.metadata.starred && (
                        <Star className="h-4 w-4 text-yellow-500 fill-current" />
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleStar(version)}
                      >
                        {version.metadata.starred ? (
                          <StarOff className="h-4 w-4" />
                        ) : (
                          <Star className="h-4 w-4" />
                        )}
                      </Button>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onVersionSelect?.(version)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      
                      {onVersionRestore && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onVersionRestore(version)}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      )}
                      
                      {onVersionDelete && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onVersionDelete(version)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  {/* Version metadata */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-muted-foreground mb-3">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatDuration(version.metadata.processingTime)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <span>$</span>
                      <span>{version.metadata.cost.toFixed(3)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Calendar className="h-3 w-3" />
                      <span>{version.timestamp.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <FileText className="h-3 w-3" />
                      <span>{Object.keys(version.results || {}).length} keys</span>
                    </div>
                  </div>
                  
                  {/* User notes */}
                  {version.metadata.userNotes && (
                    <p className="text-sm text-gray-700 mb-2">
                      {version.metadata.userNotes}
                    </p>
                  )}
                  
                  {/* Tags */}
                  {version.metadata.tags.length > 0 && (
                    <div className="flex items-center space-x-1 mb-2">
                      <Tag className="h-3 w-3 text-muted-foreground" />
                      <div className="flex flex-wrap gap-1">
                        {version.metadata.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Changes summary */}
                  {version.changes && (
                    <div className="bg-gray-50 rounded p-2 text-xs">
                      <div className="flex items-center space-x-1 mb-1">
                        <GitBranch className="h-3 w-3" />
                        <span className="font-medium">Changes:</span>
                      </div>
                      <div className="space-y-1">
                        {version.changes.added.length > 0 && (
                          <div className="text-green-600">
                            + {version.changes.added.length} added: {version.changes.added.slice(0, 3).join(', ')}
                            {version.changes.added.length > 3 && '...'}
                          </div>
                        )}
                        {version.changes.modified.length > 0 && (
                          <div className="text-blue-600">
                            ~ {version.changes.modified.length} modified: {version.changes.modified.slice(0, 3).join(', ')}
                            {version.changes.modified.length > 3 && '...'}
                          </div>
                        )}
                        {version.changes.removed.length > 0 && (
                          <div className="text-red-600">
                            - {version.changes.removed.length} removed: {version.changes.removed.slice(0, 3).join(', ')}
                            {version.changes.removed.length > 3 && '...'}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
          
          {filteredVersions.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <History className="h-12 w-12 mx-auto mb-4" />
              <p>No versions found matching your criteria</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}