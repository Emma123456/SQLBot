import { request } from '@/utils/request'

export interface Department {
  id: number
  name: string
  code: string
  parent_id: number
  origin: number
  create_time: number
}

export interface DepartmentTreeNode extends Department {
  children: DepartmentTreeNode[]
}

export interface DepartmentCreate {
  name: string
  code: string
  parent_id?: number
}

export interface DepartmentUpdate {
  id: number
  name?: string
  code?: string
  parent_id?: number
}

export interface DepartmentUser {
  id: number
  name: string
  account: string
  email: string
  is_primary: boolean
}

export const departmentApi = {
  tree: () => request.get<DepartmentTreeNode[]>('/system/department/tree'),
  detail: (id: number) => request.get<Department>(`/system/department/${id}`),
  create: (data: DepartmentCreate) => request.post('/system/department', data),
  update: (data: DepartmentUpdate) => request.put('/system/department', data),
  delete: (id: number) => request.delete(`/system/department/${id}`),
  getUsers: (id: number) => request.get<DepartmentUser[]>(`/system/department/${id}/users`),
  assignUsers: (id: number, user_ids: number[], is_primary: boolean = false) =>
    request.post(`/system/department/${id}/users`, { user_ids, is_primary }),
  removeUsers: (id: number, user_ids: number[]) =>
    request.delete(`/system/department/${id}/users`, { data: { user_ids } }),
}
