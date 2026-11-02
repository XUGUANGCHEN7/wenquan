<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "./stores/auth"
import { canAccess, type Role } from "./router/access"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const roleNames: Record<Role, string> = { frontdesk: "前台核验", merchant: "接单商家", finance: "财务", admin: "管理员" }
const items: Array<{ path: string; label: string; mark: string; roles?: Role[] }> = [
  { path: "/", label: "运营总览", mark: "总" },
  { path: "/tickets", label: "票券核验", mark: "票", roles: ["frontdesk", "admin"] },
  { path: "/rooms", label: "私汤房态", mark: "房", roles: ["frontdesk", "admin"] },
  { path: "/dining", label: "商家出餐", mark: "餐", roles: ["merchant", "frontdesk", "admin"] },
  { path: "/access", label: "手牌柜位", mark: "牌", roles: ["frontdesk", "admin"] },
  { path: "/wallet", label: "会员账本", mark: "账", roles: ["finance", "admin"] },
  { path: "/exceptions", label: "异常看板", mark: "异", roles: ["frontdesk", "finance", "admin"] },
  { path: "/reports", label: "日结报表", mark: "报", roles: ["finance", "admin"] },
  { path: "/merchants", label: "商家商品", mark: "商", roles: ["admin"] },
  { path: "/settings", label: "规则配置", mark: "设", roles: ["admin"] },
]
const navigation = computed(() => items.filter((item) => canAccess(item.roles, auth.role)))
const showShell = computed(() => auth.loggedIn && route.name !== "login")

function logout() {
  auth.logout()
  router.push({ name: "login" })
}
</script>

<template>
  <div v-if="showShell" class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span>SHUNAN</span><strong>蜀南温泉</strong><small>运营工作台 · 一期</small></div>
      <nav><RouterLink v-for="item in navigation" :key="item.path" :to="item.path" class="nav-link">
        <span class="nav-mark">{{ item.mark }}</span>{{ item.label }}
      </RouterLink></nav>
      <div class="sidebar-foot"><span class="mode-dot" />开发环境 · Mock 支付与设备</div>
    </aside>
    <main class="main-panel">
      <header class="topbar">
        <div><span class="breadcrumb">SHUNAN HOT SPRING / OPERATIONS</span></div>
        <div class="operator"><span>{{ roleNames[auth.role!] }}</span><button class="link-button" @click="logout">退出</button></div>
      </header>
      <RouterView />
    </main>
  </div>
  <RouterView v-else />
</template>
