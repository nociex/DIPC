"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function MainContent() {
  return (
    <main className="flex-1 container py-8">
      <div className="grid gap-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold tracking-tight">
            Welcome to DIPC
          </h2>
          <p className="text-muted-foreground">
            Upload and process documents with AI-powered intelligence
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Upload Documents</CardTitle>
              <CardDescription>
                Upload individual files or ZIP archives for batch processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Drag and drop files or click to browse. Supports PDF, images, and more.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Configure Processing</CardTitle>
              <CardDescription>
                Set vectorization options and storage policies
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Control costs and processing options for your documents.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Monitor Tasks</CardTitle>
              <CardDescription>
                Track processing status and view results
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Real-time updates on document processing and downloadable results.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}