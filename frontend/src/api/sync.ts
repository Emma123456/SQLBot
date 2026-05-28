import { request } from '@/utils/request'

export interface SyncDatasource {
  id: number
  name: string
  db_type: string
  host: string
  port: number
  username: string
  password: string
  database: string
  db_schema: string | null
  enabled: boolean
  cron_expression: string
  oid: number
  create_time: number
}

export interface SyncTableMapping {
  id: number
  ds_id: number
  entity_type: string
  table_name: string
  enabled: boolean
}

export interface SyncLog {
  id: number
  ds_id: number
  status: string
  summary: Record<string, number> | null
  error_message: string | null
  start_time: number
  end_time: number | null
}

export interface SyncLogListResult {
  items: SyncLog[]
  total: number
  page: number
  page_size: number
}

export interface SyncSummary {
  created: number
  updated: number
  deactivated: number
  [key: string]: number
}

export interface SyncExecuteResult {
  success: boolean
  summary: SyncSummary
}

export interface SyncTestResult {
  success: boolean
  message: string
}

export interface SyncDatasourceCreate {
  name: string
  db_type: string
  host: string
  port: number
  username: string
  password: string
  database: string
  db_schema?: string | null
  enabled?: boolean
  cron_expression?: string
  oid?: number
}

export interface SyncDatasourceUpdate {
  id: number
  name?: string
  db_type?: string
  host?: string
  port?: number
  username?: string
  password?: string
  database?: string
  db_schema?: string | null
  enabled?: boolean
  cron_expression?: string
  oid?: number
}

export interface SyncTableMappingUpdate {
  entity_type: string
  table_name: string
  enabled: boolean
}

export const syncApi = {
  // Datasource CRUD
  listDatasources: () => request.get<SyncDatasource[]>('/system/sync/datasource'),
  createDatasource: (data: SyncDatasourceCreate) =>
    request.post<SyncDatasource>('/system/sync/datasource', data),
  updateDatasource: (data: SyncDatasourceUpdate) =>
    request.put<SyncDatasource>('/system/sync/datasource', data),
  deleteDatasource: (id: number) => request.delete(`/system/sync/datasource/${id}`),

  // Connection test
  testConnection: (id: number) =>
    request.post<SyncTestResult>(`/system/sync/datasource/${id}/test`),

  // Table mapping
  getMappings: (id: number) =>
    request.get<SyncTableMapping[]>(`/system/sync/datasource/${id}/mapping`),
  updateMappings: (id: number, data: SyncTableMappingUpdate[]) =>
    request.put(`/system/sync/datasource/${id}/mapping`, data),

  // Execute sync
  executeSync: (id: number) =>
    request.post<SyncExecuteResult>(`/system/sync/datasource/${id}/execute`),

  // Logs
  getLogs: (id: number, page: number = 1, pageSize: number = 20) =>
    request.get<SyncLogListResult>(`/system/sync/datasource/${id}/logs`, {
      params: { page, page_size: pageSize },
    }),

  // Schedule
  updateSchedule: (id: number, cron_expression: string) =>
    request.put(`/system/sync/datasource/${id}/schedule`, { cron_expression }),
}
