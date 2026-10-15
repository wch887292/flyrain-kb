import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, profile, changePassword as apiChangePassword } from '@/api/user'
import type { User } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref<User | null>(null)
  const mustChangePassword = ref(false)

  // 角色（用户态未加载时回退到本地持久化角色，避免菜单闪烁）
  const role = computed(
    () => user.value?.role || localStorage.getItem('user_role') || ''
  )

  async function login(username: string, password: string) {
    const data = await apiLogin(username, password)
    token.value = data.access
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    mustChangePassword.value = !!data.must_change_password
    await fetchProfile()
  }

  async function fetchProfile() {
    user.value = await profile()
    if (user.value?.role) localStorage.setItem('user_role', user.value.role)
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    await apiChangePassword(oldPassword, newPassword)
    mustChangePassword.value = false
  }

  function logout() {
    token.value = ''
    user.value = null
    mustChangePassword.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
  }

  return { token, user, role, mustChangePassword, login, fetchProfile, changePassword, logout }
})
