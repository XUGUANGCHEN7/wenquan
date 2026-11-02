import { createRouter, createWebHistory } from "vue-router"
import { canAccess } from "./access"
import { useAuthStore } from "../stores/auth"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: () => import("../views/LoginView.vue"), meta: { public: true } },
    { path: "/", name: "dashboard", component: () => import("../views/DashboardView.vue") },
    { path: "/tickets", name: "tickets", component: () => import("../views/TicketsView.vue"), meta: { roles: ["frontdesk", "admin"] } },
    { path: "/rooms", name: "rooms", component: () => import("../views/RoomsView.vue"), meta: { roles: ["frontdesk", "admin"] } },
    { path: "/dining", name: "dining", component: () => import("../views/DiningView.vue"), meta: { roles: ["merchant", "frontdesk", "admin"] } },
    { path: "/access", name: "access", component: () => import("../views/AccessView.vue"), meta: { roles: ["frontdesk", "admin"] } },
    { path: "/wallet", name: "wallet", component: () => import("../views/WalletView.vue"), meta: { roles: ["finance", "admin"] } },
    { path: "/exceptions", name: "exceptions", component: () => import("../views/ExceptionsView.vue"), meta: { roles: ["frontdesk", "finance", "admin"] } },
    { path: "/reports", name: "reports", component: () => import("../views/ReportsView.vue"), meta: { roles: ["finance", "admin"] } },
    { path: "/merchants", name: "merchants", component: () => import("../views/MerchantMenuView.vue"), meta: { roles: ["admin"] } },
    { path: "/settings", name: "settings", component: () => import("../views/SettingsView.vue"), meta: { roles: ["admin"] } },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.name === "login" && auth.loggedIn) return { name: "dashboard" }
    return true
  }
  if (!auth.loggedIn) return { name: "login", query: { redirect: to.fullPath } }
  if (!canAccess(to.meta.roles, auth.role)) return { name: "dashboard" }
  return true
})

export default router
