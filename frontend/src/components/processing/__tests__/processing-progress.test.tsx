import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ProcessingProgress from '../processing-progress'
import { I18nProvider } from '@/lib/i18n/context'
import { ProcessingTask } from '@/types/processing'
import { TaskStatus } from '@/types'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

const mockTask: ProcessingTask = {
  id: 'test-task-1',
  fileName: 'test-document.pdf',
  originalFilename: 'test-document.pdf',
  fileSize: 1024000,
  status: TaskStatus.PROCESSING,
  progress: 45,
  currentStep: 'Document Analysis',
  currentStepIndex: 1,
  totalSteps: 4,
  steps: [
    {
      id: 'step-1',
      name: 'File Upload',
      description: 'Uploading file to server',
      status: 'completed',
      progress: 100,
      startTime: new Date('2024-01-01T10:00:00Z'),
      endTime: new Date('2024-01-01T10:01:00Z'),
      duration: 60
    },
    {
      id: 'step-2',
      name: 'Document Analysis',
      description: 'Analyzing document structure',
      status: 'active',
      progress: 45,
      startTime: new Date('2024-01-01T10:01:00Z')
    },
    {
      id: 'step-3',
      name: 'Content Extraction',
      description: 'Extracting text and data',
      status: 'pending',
      progress: 0
    },
    {
      id: 'step-4',
      name: 'Completion',
      description: 'Finalizing results',
      status: 'pending',
      progress: 0
    }
  ],
  startTime: new Date('2024-01-01T10:00:00Z'),
  lastUpdate: new Date('2024-01-01T10:02:30Z'),
  estimatedTimeRemaining: 120,
  estimatedTotalTime: 300,
  throughput: 8533,
  processedBytes: 460800,
  retryCount: 0,
  maxRetries: 3,
  estimatedCost: 0.15,
  options: {
    enableVectorization: true,
    storagePolicy: 'temporary',
    maxCostLimit: 1.0,
    llmProvider: 'openai',
    qualityLevel: 'balanced',
    priority: 'normal'
  }
}

const mockProps = {
  tasks: [mockTask],
  showDetailedProgress: false,
  onToggleDetails: jest.fn(),
  onTaskAction: jest.fn(),
}

describe('ProcessingProgress', () => {
  const renderWithI18n = (component: React.ReactElement) => {
    return render(
      <I18nProvider>
        {component}
      </I18nProvider>
    )
  }

  it('renders processing progress component', () => {
    renderWithI18n(<ProcessingProgress {...mockProps} />)
    
    expect(screen.getByText('Real-time Processing')).toBeInTheDocument()
    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
  })

  it('displays task statistics correctly', () => {
    renderWithI18n(<ProcessingProgress {...mockProps} />)
    
    expect(screen.getByText('1')).toBeInTheDocument() // Active tasks count
    expect(screen.getByText('0')).toBeInTheDocument() // Completed tasks count
  })

  it('shows progress bar with correct percentage', () => {
    renderWithI18n(<ProcessingProgress {...mockProps} />)
    
    expect(screen.getByText('45%')).toBeInTheDocument()
  })

  it('displays file size and status', () => {
    renderWithI18n(<ProcessingProgress {...mockProps} />)
    
    expect(screen.getByText(/1.0 MB/)).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('calls onToggleDetails when toggle button is clicked', () => {
    renderWithI18n(<ProcessingProgress {...mockProps} />)
    
    const toggleButton = screen.getByText('Show Details')
    toggleButton.click()
    
    expect(mockProps.onToggleDetails).toHaveBeenCalled()
  })

  it('displays empty state when no tasks', () => {
    const emptyProps = { ...mockProps, tasks: [] }
    renderWithI18n(<ProcessingProgress {...emptyProps} />)
    
    expect(screen.getByText('No processing tasks')).toBeInTheDocument()
  })
})