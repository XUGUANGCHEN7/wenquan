<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "./stores/auth"
import { canAccess, type Role } from "./router/access"

interface NavItem { path: string; label: string; mark: string; roles?: Role[] }
interface NavGroup { label: string; items: NavItem[] }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const roleNames: Record<Role, string> = {
  frontdesk: "前台核验", merchant: "接单商家", finance: "财务", admin: "管理员",
}
const groups: NavGroup[] = [
  {
    label: "前台核验",
    items: [
      { path: "/", label: "运营总览", mark: "总" },
      { path: "/tickets", label: "票券核验", mark: "票", roles: ["frontdesk", "admin"] },
      { path: "/rooms", label: "私汤核验", mark: "汤", roles: ["frontdesk", "admin"] },
    ],
  },
  {
    label: "商家管理",
    items: [
      { path: "/merchants", label: "商家商品", mark: "商", roles: ["admin"] },
      { path: "/dining", label: "接单出餐", mark: "餐", roles: ["merchant", "frontdesk", "admin"] },
    ],
  },
  {
    label: "财务管理",
    items: [
      { path: "/wallet", label: "会员账本", mark: "账", roles: ["finance", "admin"] },
      { path: "/reports", label: "财务汇总", mark: "汇", roles: ["finance", "admin"] },
    ],
  },
  {
    label: "规则配置",
    items: [
      { path: "/settings", label: "价格配置 / 充值活动", mark: "规", roles: ["admin"] },
    ],
  },
  {
    label: "运营辅助",
    items: [
      { path: "/access", label: "手牌柜位", mark: "牌", roles: ["frontdesk", "admin"] },
      { path: "/exceptions", label: "异常看板", mark: "异", roles: ["frontdesk", "finance", "admin"] },
    ],
  },
]
const navigation = computed(() => groups
  .map((group) => ({ ...group, items: group.items.filter((item) => canAccess(item.roles, auth.role)) }))
  .filter((group) => group.items.length > 0))
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
      <nav>
        <template v-for="group in navigation" :key="group.label">
          <p class="nav-group">{{ group.label }}</p>
          <RouterLink v-for="item in group.items" :key="item.path" :to="item.path" class="nav-link">
            <span class="nav-mark">{{ item.mark }}</span>{{ item.label }}
          </RouterLink>
        </template>
      </nav>
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
