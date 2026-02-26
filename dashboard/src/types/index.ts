export interface Span {
  spanId: string
  traceId: string
  operationName: string
  parentId?: string
  startTime: number
  endTime: number
  duration: number
  attributes: Record<string, any>
  events: Event[]
}

export interface Event {
  name: string
  timestamp: number
  attributes?: Record<string, any>
}

export interface Trace {
  traceId: string
  spans: Span[]
  startTime: number
  endTime: number
  duration: number
  spanCount: number
  errorCount: number
}

export interface OperationStats {
  name: string
  callCount: number
  avgDuration: number
  minDuration: number
  maxDuration: number
  errorCount: number
  errorRate: number
}

export interface LatencyMetrics {
  p50: number
  p95: number
  p99: number
  min: number
  max: number
  avg: number
}

export interface ErrorStats {
  totalErrors: number
  errorRate: number
  uniqueOperations: number
  errorsByOperation: Record<string, number>
}

export interface ErrorDetail {
  operationName: string
  errorMessage: string
  stackTrace?: string
}
