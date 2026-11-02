<script setup lang="ts">
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"
import type { Role } from "../router/access"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref<Role | null>(null)
const error = ref("")
const cards: Array<{ role: Role; title: string; desc: string; mark: string }> = [
  { role: "frontdesk", title: "前台核验", desc: "人工验票、到店分房、手牌与柜位操作", mark: "前" },
  { role: "merchant", title: "接单商家", desc: "查看已付款且可送达的点餐，更新制作与送达", mark: "商" },
  { role: "finance", title: "财务", desc: "本金/赠送流水、退款异常、日结与对账", mark: "财" },
  { role: "admin", title: "管理员", desc: "全量运营权限、配置、审计与异常处理", mark: "管" },
]
const defaults: Record<Role, string> = { frontdesk: "/", merchant: "/dining", finance: "/reports", admin: "/" }

async function login(role: Role) {
  loading.value = role
  error.value = ""
  try {
    await auth.login(role)
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : defaults[role]
    await router.push(redirect)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "登录失败"
  } finally { loading.value = null }
}
</script>

<template>
  <main class="login-page">
    <section class="login-story">
      <span class="eyebrow">SHUNAN HOT SPRING · PHASE ONE</span>
      <h1>让每一次到店，<br />都有可核验的事实。</h1>
      <p>统一会员、票券、私汤库存、储值账本与设备任务的运营中枢。价格、余额和支付状态只由服务端决定。</p>
      <div class="story-note"><strong>模拟环境</strong><span>开发登录、微信支付与设备均为明确标注的 Mock，不代表真实商户或硬件联调成功。</span></div>
    </section>
    <section class="login-panel">
      <span class="eyebrow">SELECT OPERATOR ROLE</span>
      <h2>选择工作台角色</h2>
      <div class="role-grid">
        <button v-for="card in cards" :key="card.role" class="role-card" :disabled="loading !== null" @click="login(card.role)">
          <span class="role-mark">{{ card.mark }}</span><strong>{{ card.title }}</strong><small>{{ card.desc }}</small>
          <span class="role-action">{{ loading === card.role ? "正在进入…" : "进入工作台 →" }}</span>
        </button>
      </div>
      <p v-if="error" class="form-error">{{ error }}</p>
      <p class="login-foot">正式环境必须替换为受控的身份服务与角色授权，不保留静态开发令牌。</p>
    </section>
  </main>
</template>
