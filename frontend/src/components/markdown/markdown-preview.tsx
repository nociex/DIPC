"use client"

import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'

interface MarkdownPreviewProps {
  content: string
  className?: string
  onScroll?: (scrollTop: number) => void
}

export function MarkdownPreview({ 
  content, 
  className,
  onScroll 
}: MarkdownPreviewProps) {
  const processedContent = useMemo(() => {
    // Handle empty content
    if (!content.trim()) {
      return "开始编辑以查看预览..."
    }
    return content
  }, [content])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    onScroll?.(e.currentTarget.scrollTop)
  }

  return (
    <div 
      className={cn(
        "h-full overflow-auto bg-card border rounded-md shadow-sm",
        className
      )}
      onScroll={handleScroll}
    >
      <div className="p-4">
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
            // Custom heading components with better styling
            h1: ({ children, ...props }) => (
              <h1 className="text-2xl font-bold mb-4 mt-6 first:mt-0 text-foreground border-b pb-2" {...props}>
                {children}
              </h1>
            ),
            h2: ({ children, ...props }) => (
              <h2 className="text-xl font-semibold mb-3 mt-5 first:mt-0 text-foreground border-b pb-1" {...props}>
                {children}
              </h2>
            ),
            h3: ({ children, ...props }) => (
              <h3 className="text-lg font-semibold mb-2 mt-4 first:mt-0 text-foreground" {...props}>
                {children}
              </h3>
            ),
            h4: ({ children, ...props }) => (
              <h4 className="text-base font-semibold mb-2 mt-3 first:mt-0 text-foreground" {...props}>
                {children}
              </h4>
            ),
            h5: ({ children, ...props }) => (
              <h5 className="text-sm font-semibold mb-1 mt-2 first:mt-0 text-foreground" {...props}>
                {children}
              </h5>
            ),
            h6: ({ children, ...props }) => (
              <h6 className="text-xs font-semibold mb-1 mt-2 first:mt-0 text-foreground" {...props}>
                {children}
              </h6>
            ),
            // Custom paragraph styling
            p: ({ children, ...props }) => (
              <p className="mb-4 text-foreground leading-relaxed" {...props}>
                {children}
              </p>
            ),
            // Custom list styling
            ul: ({ children, ...props }) => (
              <ul className="mb-4 ml-6 list-disc space-y-1" {...props}>
                {children}
              </ul>
            ),
            ol: ({ children, ...props }) => (
              <ol className="mb-4 ml-6 list-decimal space-y-1" {...props}>
                {children}
              </ol>
            ),
            li: ({ children, ...props }) => (
              <li className="text-foreground" {...props}>
                {children}
              </li>
            ),
            // Custom blockquote styling
            blockquote: ({ children, ...props }) => (
              <blockquote className="border-l-4 border-primary/30 pl-4 py-2 mb-4 bg-muted/30 italic text-muted-foreground" {...props}>
                {children}
              </blockquote>
            ),
            // Custom code styling
            code: ({ children, ...props }) => (
              <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground" {...props}>
                {children}
              </code>
            ),
            // Custom pre styling for code blocks
            pre: ({ children, ...props }) => (
              <pre className="bg-muted p-3 rounded-md mb-4 overflow-x-auto" {...props}>
                {children}
              </pre>
            ),
            // Custom table styling
            table: ({ children, ...props }) => (
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full border-collapse border border-border" {...props}>
                  {children}
                </table>
              </div>
            ),
            thead: ({ children, ...props }) => (
              <thead className="bg-muted/50" {...props}>
                {children}
              </thead>
            ),
            th: ({ children, ...props }) => (
              <th className="border border-border px-3 py-2 text-left font-semibold text-foreground" {...props}>
                {children}
              </th>
            ),
            td: ({ children, ...props }) => (
              <td className="border border-border px-3 py-2 text-foreground" {...props}>
                {children}
              </td>
            ),
            // Custom link styling
            a: ({ children, href, ...props }) => (
              <a 
                href={href} 
                className="text-primary hover:text-primary/80 underline underline-offset-2" 
                target="_blank" 
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            ),
            // Custom strong/bold styling
            strong: ({ children, ...props }) => (
              <strong className="font-semibold text-foreground" {...props}>
                {children}
              </strong>
            ),
            // Custom emphasis/italic styling
            em: ({ children, ...props }) => (
              <em className="italic text-foreground" {...props}>
                {children}
              </em>
            ),
            // Custom horizontal rule styling
            hr: ({ ...props }) => (
              <hr className="my-6 border-border" {...props} />
            ),
          }}
        >
          {processedContent}
        </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}