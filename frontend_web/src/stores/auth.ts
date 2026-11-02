import { defineStore } from "pinia"
import { computed, ref } from "vue"
import { request } from "../api/client"
import type { Role } from "../router/access"

interface LoginResponse {
  access_token: string
  role: Role
  member_id: string | null
  mode: string
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("wenquan_token") ?? "")
  const role = ref<Role | null>((localStorage.getItem("wenquan_role") as Role | null) ?? null)
  const loggedIn = computed(() => Boolean(token.value && role.value))

  async function login(selected: Role) {
    const result = await request<LoginResponse>("/auth/dev", { method: "POST", body: { role: selected } })
    token.value = result.access_token
    role.value = result.role
    localStorage.setItem("wenquan_token", result.access_token)
    localStorage.setItem("wenquan_role", result.role)
  }

  function logout() {
    token.value = ""
    role.value = null
    localStorage.removeItem("wenquan_token")
    localStorage.removeItem("wenquan_role")
  }

  return { token, role, loggedIn, login, logout }
})
