'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Wifi, 
  WifiOff, 
  Loader2, 
  AlertCircle, 
  CheckCircle2,
  RefreshCw
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/lib/i18n/context'
import { ConnectionStatus, ConnectionStatusUpdate } from '@/lib/live-updates-service'

export interface ConnectionStatusProps {
  status: ConnectionStatus
  statusUpdate?: ConnectionStatusUpdate
  onReconnect?: () => void
  showDetails?: boolean
  className?: string
}

const ConnectionStatusIndicator: React.FC<ConnectionStatusProps> = ({
  status,
  statusUpdate,
  onReconnect,
  showDetails = false,
  className = ''
}) => {
  const { t } = useI18n()

  const getStatusConfig = (status: ConnectionStatus) => {
    switch (status) {
      case 'connected':
        return {
          icon: CheckCircle2,
          color: 'bg-green-500',
          textColor: 'text-green-700',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          label: 'Connected',
          pulse: false
        }
      case 'connecting':
        return {
          icon: Loader2,
          color: 'bg-blue-500',
          textColor: 'text-blue-700',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          label: 'Connecting',
          pulse: true
        }
      case 'reconnecting':
        return {
          icon: RefreshCw,
          color: 'bg-yellow-500',
          textColor: 'text-yellow-700',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          label: 'Reconnecting',
          pulse: true
        }
      case 'disconnected':
        return {
          icon: WifiOff,
          color: 'bg-gray-500',
          textColor: 'text-gray-700',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          label: 'Disconnected',
          pulse: false
        }
      case 'error':
        return {
          icon: AlertCircle,
          color: 'bg-red-500',
          textColor: 'text-red-700',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          label: 'Connection Error',
          pulse: false
        }
      default:
        return {
          icon: WifiOff,
          color: 'bg-gray-500',
          textColor: 'text-gray-700',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          label: 'Unknown',
          pulse: false
        }
    }
  }

  const config = getStatusConfig(status)
  const Icon = config.icon

  if (!showDetails) {
    // Compact indicator
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="relative">
          <div 
            className={`w-2 h-2 rounded-full ${config.color} ${
              config.pulse ? 'animate-pulse' : ''
            }`}
          />
          {config.pulse && (
            <div 
              className={`absolute inset-0 w-2 h-2 rounded-full ${config.color} animate-ping opacity-75`}
            />
          )}
        </div>
        <span className={`text-xs ${config.textColor}`}>
          {config.label}
        </span>
      </div>
    )
  }

  // Detailed status card
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`${config.bgColor} ${config.borderColor} border rounded-lg p-3 ${className}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Icon 
              className={`h-4 w-4 ${config.textColor} ${
                config.pulse ? 'animate-spin' : ''
              }`}
            />
            {config.pulse && (
              <div 
                className={`absolute inset-0 h-4 w-4 ${config.color} rounded-full animate-ping opacity-20`}
              />
            )}
          </div>
          
          <div>
            <div className={`text-sm font-medium ${config.textColor}`}>
              {config.label}
            </div>
            
            {statusUpdate?.reconnectAttempt && (
              <div className="text-xs text-muted-foreground">
                Attempt {statusUpdate.reconnectAttempt}
              </div>
            )}
            
            {statusUpdate?.lastConnected && status === 'disconnected' && (
              <div className="text-xs text-muted-foreground">
                Last connected: {statusUpdate.lastConnected.toLocaleTimeString()}
              </div>
            )}
            
            {statusUpdate?.error && (
              <div className="text-xs text-red-600 mt-1">
                {statusUpdate.error}
              </div>
            )}
          </div>
        </div>

        {/* Reconnect button for error/disconnected states */}
        {(status === 'error' || status === 'disconnected') && onReconnect && (
          <Button
            variant="outline"
            size="sm"
            onClick={onReconnect}
            className="ml-2"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reconnect
          </Button>
        )}
      </div>

      {/* Connection quality indicator */}
      {status === 'connected' && (
        <div className="mt-2 pt-2 border-t border-green-200">
          <div className="flex items-center gap-2">
            <Wifi className="h-3 w-3 text-green-600" />
            <div className="flex-1">
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((bar) => (
                  <div
                    key={bar}
                    className={`w-1 rounded-full ${
                      bar <= 3 ? 'bg-green-500' : 'bg-green-200'
                    }`}
                    style={{ height: `${bar * 2 + 2}px` }}
                  />
                ))}
              </div>
            </div>
            <span className="text-xs text-green-600">
              Real-time
            </span>
          </div>
        </div>
      )}
    </motion.div>
  )
}

export default ConnectionStatusIndicator

// Floating status indicator for global use
export const FloatingConnectionStatus: React.FC<{
  status: ConnectionStatus
  statusUpdate?: ConnectionStatusUpdate
  onReconnect?: () => void
}> = ({ status, statusUpdate, onReconnect }) => {
  const config = getStatusConfig(status)

  // Only show for non-connected states
  if (status === 'connected') {
    return null
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 100 }}
        className="fixed top-4 right-4 z-50"
      >
        <ConnectionStatusIndicator
          status={status}
          statusUpdate={statusUpdate}
          onReconnect={onReconnect}
          showDetails={true}
          className="shadow-lg"
        />
      </motion.div>
    </AnimatePresence>
  )
}

function getStatusConfig(status: ConnectionStatus) {
  switch (status) {
    case 'connected':
      return {
        icon: CheckCircle2,
        color: 'bg-green-500',
        textColor: 'text-green-700',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        label: 'Connected',
        pulse: false
      }
    case 'connecting':
      return {
        icon: Loader2,
        color: 'bg-blue-500',
        textColor: 'text-blue-700',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        label: 'Connecting',
        pulse: true
      }
    case 'reconnecting':
      return {
        icon: RefreshCw,
        color: 'bg-yellow-500',
        textColor: 'text-yellow-700',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        label: 'Reconnecting',
        pulse: true
      }
    case 'disconnected':
      return {
        icon: WifiOff,
        color: 'bg-gray-500',
        textColor: 'text-gray-700',
        bgColor: 'bg-gray-50',
        borderColor: 'border-gray-200',
        label: 'Disconnected',
        pulse: false
      }
    case 'error':
      return {
        icon: AlertCircle,
        color: 'bg-red-500',
        textColor: 'text-red-700',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        label: 'Connection Error',
        pulse: false
      }
    default:
      return {
        icon: WifiOff,
        color: 'bg-gray-500',
        textColor: 'text-gray-700',
        bgColor: 'bg-gray-50',
        borderColor: 'border-gray-200',
        label: 'Unknown',
        pulse: false
      }
  }
}