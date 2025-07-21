import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from '@/components/ui/toaster'
import { I18nProvider } from '@/lib/i18n/context'
import { SkipLinks } from '@/components/layout/skip-links'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Document Intelligence & Parsing Center',
  description: 'AI-powered document processing and analysis platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <I18nProvider>
          <SkipLinks />
          <div className="min-h-screen bg-background">
            {children}
          </div>
          <Toaster />
          <div 
            aria-live="polite" 
            aria-atomic="true" 
            className="sr-only"
            id="aria-live-region"
          />
        </I18nProvider>
      </body>
    </html>
  )
}