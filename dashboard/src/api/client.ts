import axios from 'axios'
import type {
  Trace,
  OperationStats,
  LatencyMetrics,
  ErrorStats,
  ErrorDetail,
  Span
} from '../types'

// Support both development (relative /api via proxy) and production (absolute URL via env)
const API_BASE = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
})

export const api = {
  // Spans API
  getSpans: (filters?: Record<string, any>) => 
    client.get<Span[]>('/spans', { params: filters }),
  
  // Traces API
  getTraces: (filters?: Record<string, any>) =>
    client.get<Trace[]>('/traces', { params: filters }),
  
  getTrace: (traceId: string) =>
    client.get<Trace>(`/traces/${traceId}`),
  
  // Operations API
  getOperations: (filters?: Record<string, any>) =>
    client.get<OperationStats[]>('/operations', { params: filters }),
  
  // Metrics API
  getLatencyMetrics: (operation?: string) =>
    client.get<LatencyMetrics>('/metrics/latency', { params: { operation } }),
  
  getLatencySlowest: (limit: number = 10) =>
    client.get<OperationStats[]>('/metrics/latency/slowest', { params: { limit } }),
  
  // Errors API
  getErrors: (filters?: Record<string, any>) =>
    client.get<ErrorStats[]>('/errors', { params: filters }),
  
  getErrorStats: () =>
    client.get<ErrorStats>('/errors/stats'),
  
  getRecentErrors: (limit: number = 20) =>
    client.get<ErrorDetail[]>('/errors/recent', { params: { limit } }),
}

export default client
