import { request } from '@/utils/request'

export const getList = () => request.post('/ds_permission/list')
export const savePermissions = (data: any) => request.post('/ds_permission/save', data)
export const delPermissions = (id: any) => request.post(`/ds_permission/delete/${id}`)

// Rule targets (role_list / dept_list) API
// Note: IDs may be strings for large integers (>2^53-1) due to json-bigint storeAsString
export interface RuleTargets {
  roles: (number | string)[]
  departments: (number | string)[]
}

export interface RuleTargetsResponse {
  rule_id: number | string
  roles: (number | string)[]
  departments: (number | string)[]
}

export const updateRuleTargets = (ruleId: number, data: RuleTargets) =>
  request.put(`/permission-rule/${ruleId}/targets`, data)

export const getRuleTargets = (ruleId: number) =>
  request.get(`/permission-rule/${ruleId}/targets`)

export const getAllRuleTargets = () =>
  request.get('/permission-rule/targets')
