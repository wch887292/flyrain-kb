import request from './request'
import type { User } from '@/types'

export function login(username: string, password: string) {
  return request.post('/users/login/', { username, password })
}

export function register(payload: {
  username: string
  password: string
  email?: string
  nickname?: string
  tenant_name?: string
}) {
  return request.post('/users/register/', payload)
}

export function profile() {
  return request.get<User>('/users/profile/')
}

/** 修改当前用户密码 */
export function changePassword(old_password: string, new_password: string) {
  return request.post('/users/change-password/', { old_password, new_password })
}

/** 管理员：用户列表（扁平数组） */
export function listUsers() {
  return request.get<User[]>('/users/')
}

/** 管理员：新建用户 */
export function createUser(payload: {
  username: string
  password: string
  email?: string
  nickname?: string
  role?: string
  tenant_name?: string
}) {
  return request.post<User>('/users/', payload)
}

/** 管理员：修改用户（角色 / 密码 / 资料） */
export function updateUser(
  id: number,
  payload: {
    email?: string
    nickname?: string
    role?: string
    password?: string
    tenant_name?: string
  }
) {
  return request.put<User>(`/users/${id}/`, payload)
}

/** 管理员：删除用户 */
export function deleteUser(id: number) {
  return request.delete(`/users/${id}/`)
}
