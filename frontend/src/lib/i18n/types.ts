// Translation key type definitions
export type Language = 'zh' | 'en';

export interface TranslationKeys {
  // Navigation and Layout
  'nav.upload': string;
  'nav.processing': string;
  'nav.results': string;
  'nav.settings': string;
  'nav.language.toggle': string;
  'nav.language.chinese': string;
  'nav.language.english': string;
  
  // File Upload
  'upload.dropzone.title': string;
  'upload.dropzone.subtitle': string;
  'upload.dropzone.dragHere': string;
  'upload.dropzone.orClick': string;
  'upload.progress.uploading': string;
  'upload.progress.analyzing': string;
  'upload.error.fileSize': string;
  'upload.error.fileType': string;
  'upload.error.network': string;
  'upload.button.selectFiles': string;
  'upload.button.startProcessing': string;
  
  // Enhanced Upload - Drag and Drop
  'upload.dropIndicator.title': string;
  'upload.dropIndicator.subtitle': string;
  'upload.dropZone.main': string;
  'upload.dropZone.sidebar': string;
  'upload.dropZone.queue': string;
  'upload.dropZone.batch': string;
  'upload.validation.error': string;
  'upload.validation.warning': string;
  'upload.success.filesAdded': string;
  'upload.success.filesAddedDescription': string;
  'upload.suggestion.compressFile': string;
  'upload.suggestion.convertFile': string;
  'upload.suggestion.shortenFileName': string;
  'upload.suggestion.renameFile': string;
  'upload.warning.longFileName': string;
  'upload.warning.specialCharacters': string;
  'upload.maxFiles': string;
  
  // Multiple Drop Zones
  'upload.dropZone.main.title': string;
  'upload.dropZone.main.description': string;
  'upload.dropZone.batch.title': string;
  'upload.dropZone.batch.description': string;
  'upload.dropZone.queue.title': string;
  'upload.dropZone.queue.description': string;
  'upload.dropZone.sidebar.title': string;
  'upload.dropZone.sidebar.description': string;
  
  // File Analysis
  'upload.analysis.estimatedTime': string;
  'upload.analysis.estimatedCost': string;
  'upload.analysis.complexity': string;
  'upload.analysis.processingSteps': string;
  'upload.analysis.optional': string;
  'upload.analysis.warnings': string;
  'upload.analysis.recommendations': string;
  'upload.analysis.suggestedConfig': string;
  'upload.analysis.hideRecommendations': string;
  'upload.analysis.showRecommendations': string;
  'upload.analysis.useConfig': string;
  'upload.config.vectorization': string;
  'upload.config.storage': string;
  'upload.config.costLimit': string;
  'upload.config.provider': string;
  
  // Batch Upload Management
  'upload.batch.title': string;
  'upload.batch.files': string;
  'upload.batch.config': string;
  'upload.batch.start': string;
  'upload.batch.pause': string;
  'upload.batch.resume': string;
  'upload.batch.completed': string;
  'upload.batch.completedDescription': string;
  'upload.batch.error': string;
  'upload.batch.errorDescription': string;
  'upload.batch.paused': string;
  'upload.batch.pausedDescription': string;
  'upload.batch.resumed': string;
  'upload.batch.resumedDescription': string;
  'upload.batch.retrying': string;
  'upload.batch.retryingDescription': string;
  'upload.batch.totalCost': string;
  'upload.batch.totalTime': string;
  'upload.batch.totalSize': string;
  'upload.batch.overallProgress': string;
  'upload.batch.analysisTitle': string;
  'upload.batch.analysisError': string;
  'upload.batch.analysisErrorDescription': string;
  'upload.batch.fileList': string;
  'upload.batch.retryFailed': string;
  'upload.batch.retryCount': string;

  // Common (additional keys)
  'common.enabled': string;
  'common.disabled': string;
  
  // Processing
  'processing.status.pending': string;
  'processing.status.inProgress': string;
  'processing.status.completed': string;
  'processing.status.failed': string;
  'processing.status.cancelled': string;
  'processing.queue.title': string;
  'processing.progress.estimatedTime': string;
  'processing.progress.currentStep': string;
  
  // Results
  'results.title': string;
  'results.noResults': string;
  'results.export.json': string;
  'results.export.csv': string;
  'results.export.pdf': string;
  'results.export.markdown': string;
  'results.share.link': string;
  'results.search.placeholder': string;
  'results.view.preview': string;
  'results.view.detailed': string;
  'results.view.raw': string;
  
  // Notifications
  'notification.success.upload': string;
  'notification.success.processing': string;
  'notification.error.network': string;
  'notification.error.upload': string;
  'notification.error.processing': string;
  'notification.info.processing': string;
  'notification.info.languageChanged': string;
  
  // Common
  'common.loading': string;
  'common.error': string;
  'common.success': string;
  'common.cancel': string;
  'common.retry': string;
  'common.close': string;
  'common.save': string;
  'common.delete': string;
  'common.edit': string;
  'common.view': string;
  'common.download': string;
  'common.share': string;
  
  // Errors
  'error.generic': string;
  'error.networkConnection': string;
  'error.fileUpload': string;
  'error.processing': string;
  'error.notFound': string;
  'error.unauthorized': string;
  'error.serverError': string;
  
  // Workspace
  'workspace.main': string;
  'workspace.content.main': string;
  'workspace.sidebar.title': string;
  'workspace.sidebar.expand': string;
  'workspace.sidebar.collapse': string;
  'workspace.sidebar.files': string;
  'workspace.sidebar.tasks': string;
  'workspace.sidebar.noFiles': string;
  'workspace.sidebar.noTasks': string;
  'workspace.sidebar.processing': string;
  'workspace.sidebar.active': string;
  'workspace.sidebar.complete': string;
  'workspace.sidebar.task': string;
  
  // Empty State
  'workspace.empty.title': string;
  'workspace.empty.subtitle': string;
  'workspace.empty.selectFiles': string;
  'workspace.empty.orDragDrop': string;
  'workspace.empty.supportedFormats': string;
  'workspace.empty.features.fast.title': string;
  'workspace.empty.features.fast.description': string;
  'workspace.empty.features.secure.title': string;
  'workspace.empty.features.secure.description': string;
  'workspace.empty.features.multilingual.title': string;
  'workspace.empty.features.multilingual.description': string;
  'workspace.empty.quickStart.title': string;
  'workspace.empty.quickStart.step1': string;
  'workspace.empty.quickStart.step2': string;
  'workspace.empty.quickStart.step3': string;
  'workspace.empty.quickStart.learnMore': string;
  'workspace.empty.dropZones.title': string;
  'workspace.empty.dropZones.subtitle': string;
  
  // Uploading State
  'workspace.uploading.title': string;
  'workspace.uploading.subtitle': string;
  'workspace.uploading.files': string;
  'workspace.uploading.completed': string;
  'workspace.uploading.uploading': string;
  'workspace.uploading.failed': string;
  'workspace.uploading.pending': string;
  'workspace.uploading.complete': string;
  'workspace.uploading.overallProgress': string;
  'workspace.uploading.estimates': string;
  'workspace.uploading.estimatedTime': string;
  'workspace.uploading.estimatedCost': string;
  'workspace.uploading.totalSize': string;
  'workspace.uploading.configuration': string;
  'workspace.uploading.processing': string;
  'workspace.uploading.startProcessing': string;
  'workspace.uploading.addMoreFiles': string;
  
  // Processing State
  'workspace.processing.title': string;
  'workspace.processing.subtitle': string;
  'workspace.processing.noTasks': string;
  'workspace.processing.noTasksDescription': string;
  'workspace.processing.uploadFiles': string;
  'workspace.processing.refresh': string;
  'workspace.processing.overallProgress': string;
  'workspace.processing.activeTasks': string;
  'workspace.processing.complete': string;
  'workspace.processing.task': string;
  'workspace.processing.duration': string;
  'workspace.processing.completedTasks': string;
  'workspace.processing.completedIn': string;
  'workspace.processing.failedTasks': string;
  'workspace.processing.failed': string;
  'workspace.processing.unknownError': string;
  'processing.steps.upload': string;
  'processing.steps.analysis': string;
  'processing.steps.extraction': string;
  'processing.steps.vectorization': string;
  'processing.steps.completion': string;
  
  // Real-time Processing
  'processing.realtime.title': string;
  'processing.realtime.overallProgress': string;
  'processing.realtime.activeTasks': string;
  'processing.realtime.completedTasks': string;
  'processing.realtime.failedTasks': string;
  'processing.realtime.queuedTasks': string;
  'processing.realtime.averageTime': string;
  'processing.realtime.totalCost': string;
  'processing.realtime.successRate': string;
  'processing.realtime.throughput': string;
  'processing.realtime.estimatedCompletion': string;
  'processing.realtime.timeRemaining': string;
  'processing.realtime.currentStep': string;
  'processing.realtime.stepProgress': string;
  'processing.realtime.detailedView': string;
  'processing.realtime.compactView': string;
  'processing.realtime.showDetails': string;
  'processing.realtime.hideDetails': string;
  'processing.realtime.pauseTask': string;
  'processing.realtime.resumeTask': string;
  'processing.realtime.cancelTask': string;
  'processing.realtime.retryTask': string;
  'processing.realtime.increasePriority': string;
  'processing.realtime.decreasePriority': string;
  'processing.realtime.taskDetails': string;
  'processing.realtime.processingSpeed': string;
  'processing.realtime.bytesProcessed': string;
  'processing.realtime.retryCount': string;
  'processing.realtime.maxRetries': string;
  'processing.realtime.errorDetails': string;
  'processing.realtime.recoveryActions': string;
  'processing.realtime.autoRetry': string;
  'processing.realtime.manualRetry': string;
  'processing.realtime.skipTask': string;
  'processing.realtime.contactSupport': string;
  'processing.realtime.taskStarted': string;
  'processing.realtime.taskCompleted': string;
  'processing.realtime.taskFailed': string;
  'processing.realtime.taskCancelled': string;
  'processing.realtime.taskPaused': string;
  'processing.realtime.taskResumed': string;
  'processing.realtime.queuePosition': string;
  'processing.realtime.estimatedStart': string;
  'processing.realtime.priority': string;
  'processing.realtime.priorityHigh': string;
  'processing.realtime.priorityNormal': string;
  'processing.realtime.priorityLow': string;
  
  // Results State
  'workspace.results.title': string;
  'workspace.results.subtitle': string;
  'workspace.results.noSelection': string;
  'workspace.results.noSelectionDescription': string;
  'workspace.results.selectTask': string;
  'workspace.results.back': string;
  
  // Upload errors
  'upload.error.noFiles': string;
  
  // Help and Onboarding
  'help.title': string;
  'help.gettingStarted': string;
  'help.uploadFiles': string;
  'help.viewResults': string;
  'onboarding.welcome': string;
  'onboarding.step1': string;
  'onboarding.step2': string;
  'onboarding.step3': string;
  'onboarding.skip': string;
  'onboarding.next': string;
  'onboarding.finish': string;
}

export type TranslationFunction = (key: keyof TranslationKeys, params?: Record<string, any>) => string;

export interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: TranslationFunction;
  isLoading: boolean;
}

export interface I18nServiceConfig {
  defaultLanguage: Language;
  fallbackLanguage: Language;
  storageKey: string;
  detectBrowserLanguage: boolean;
}