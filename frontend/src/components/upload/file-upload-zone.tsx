"use client"

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

interface FileWithPreview extends File {
  preview?: string
  uploadProgress?: number
  uploadStatus?: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

interface FileUploadZoneProps {
  onFilesSelected: (files: FileWithPreview[]) => void
  maxFiles?: number
  maxSize?: number
  acceptedFileTypes?: string[]
  className?: string
}

export function FileUploadZone({
  onFilesSelected,
  maxFiles = 10,
  maxSize = 100 * 1024 * 1024, // 100MB
  acceptedFileTypes = [
    'application/pdf',
    'image/*',
    'application/zip',
    'application/x-zip-compressed',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  className
}: FileUploadZoneProps) {
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      rejectedFiles.forEach(({ file, errors }) => {
        errors.forEach((error: any) => {
          toast({
            title: "File rejected",
            description: `${file.name}: ${error.message}`,
            variant: "destructive",
          })
        })
      })
    }

    // Process accepted files
    if (acceptedFiles.length > 0) {
      const newFiles: FileWithPreview[] = acceptedFiles.map(file => ({
        ...file,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
        uploadProgress: 0,
        uploadStatus: 'pending' as const
      }))

      const updatedFiles = [...files, ...newFiles].slice(0, maxFiles)
      setFiles(updatedFiles)
      onFilesSelected(updatedFiles)

      toast({
        title: "Files added",
        description: `${acceptedFiles.length} file(s) ready for upload`,
      })
    }
  }, [files, maxFiles, onFilesSelected, toast])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => {
      acc[type] = []
      return acc
    }, {} as Record<string, string[]>),
    maxSize,
    maxFiles,
    multiple: true
  })

  const removeFile = (index: number) => {
    const updatedFiles = files.filter((_, i) => i !== index)
    setFiles(updatedFiles)
    onFilesSelected(updatedFiles)
  }

  const clearAllFiles = () => {
    // Revoke object URLs to prevent memory leaks
    files.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview)
      }
    })
    setFiles([])
    onFilesSelected([])
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop Zone */}
      <Card>
        <CardContent className="p-6">
          <div
            {...getRootProps()}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
            )}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            {isDragActive ? (
              <p className="text-lg font-medium">Drop files here...</p>
            ) : (
              <div className="space-y-2">
                <p className="text-lg font-medium">
                  Drag & drop files here, or click to browse
                </p>
                <p className="text-sm text-muted-foreground">
                  Supports PDF, images, ZIP archives, and documents
                </p>
                <p className="text-xs text-muted-foreground">
                  Max {maxFiles} files, {formatFileSize(maxSize)} per file
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">
                Selected Files ({files.length})
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllFiles}
              >
                Clear All
              </Button>
            </div>

            <div className="space-y-3">
              {files.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center space-x-3 p-3 border rounded-lg"
                >
                  {/* File Icon/Preview */}
                  <div className="flex-shrink-0">
                    {file.preview ? (
                      <img
                        src={file.preview}
                        alt={file.name}
                        className="h-10 w-10 object-cover rounded"
                      />
                    ) : (
                      <File className="h-10 w-10 text-muted-foreground" />
                    )}
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                    
                    {/* Upload Progress */}
                    {file.uploadStatus === 'uploading' && (
                      <Progress 
                        value={file.uploadProgress || 0} 
                        className="mt-2 h-2"
                      />
                    )}
                    
                    {/* Error Message */}
                    {file.uploadStatus === 'error' && (
                      <div className="flex items-center mt-2 text-xs text-destructive">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        {file.error || 'Upload failed'}
                      </div>
                    )}
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center space-x-2">
                    {file.uploadStatus === 'completed' && (
                      <div className="text-green-600">
                        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      className="h-8 w-8 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}