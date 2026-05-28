import { request } from '@/utils/request'

export interface Role {
  id: number
  name: string
  code: string
  description: string | null
  origin: number
  oid: number
  ds_id: number
  create_time: number
}

export interface RoleListResult {
  items: Role[]
  total: number
  page: number
  page_size: number
}

export interface RoleCreate {
  name: string
  code: string
  description?: string | null
  oid?: number
}

export interface RoleUpdate {
  id: number
  name?: string
  code?: string
  description?: string | null
  oid?: number
}

export interface RoleUser {
  id: number
  name: string
  account: string
  email: string
}

export const roleApi = {
  list: (page: number = 1, pageSize: number = 20, keyword?: string, ds_id?: number, oid?: number) =>
    request.get<RoleListResult>('/system/role', {
      params: { page, page_size: pageSize, keyword: keyword || undefined, ds_id, oid },
    }),
  all: (oid?: number) => request.get<Role[]>('/system/role/all', {
    params: { oid },
  }),
  detail: (id: number) => request.get<Role>(`/system/role/${id}`),
  create: (data: RoleCreate) => request.post('/system/role', data),
  update: (data: RoleUpdate) => request.put('/system/role', data),
  delete: (id: number) => request.delete(`/system/role/${id}`),
  getUsers: (id: number) => request.get<RoleUser[]>(`/system/role/${id}/users`),
  assignUsers: (id: number, user_ids: number[]) =>
    request.post(`/system/role/${id}/users`, { user_ids }),
  removeUsers: (id: number, user_ids: number[]) =>
    request.delete(`/system/role/${id}/users`, { data: { user_ids } }),
}
