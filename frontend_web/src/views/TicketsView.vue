<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
import { useAuthStore } from "../stores/auth"
import PageHeader from "../components/PageHeader.vue"

const auth = useAuthStore()
const ticketNo = ref("")
const reason = ref("前台人工核对票券与身份")
const busy = ref(false)
const error = ref("")
const results = ref<Array<{ ticket: string; message: string; time: string; success: boolean }>>([])

async function admit() {
  if (!ticketNo.value.trim() || busy.value) return
  busy.value = true
  error.value = ""
  try {
    await api.post("/operations/tickets/admit", {
      ticket_no: ticketNo.value.trim(), request_id: crypto.randomUUID(), reason: reason.value,
    })
    results.value.unshift({ ticket: ticketNo.value.trim(), message: "人工核验成功，已记录单次入园", time: new Date().toLocaleTimeString("zh-CN"), success: true })
    ticketNo.value = ""
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "核验失败"
  } finally { busy.value = false }
}
</script>

<template>
  <PageHeader eyebrow="MANUAL ADMISSION" title="票券人工核验" description="一期由前台人工核验，每张门票仅允许一次入园；不接闸机、不实现重复入园。" />
  <div class="two-column">
    <section class="panel">
      <div class="panel-head"><h2>核验票券</h2><span class="operator-tag">{{ auth.role }}</span></div>
      <form class="form-stack" @submit.prevent="admit">
        <label>票券编号<input v-model="ticketNo" autocomplete="off" placeholder="扫描或输入 ticket_no" /></label>
        <label>核验原因 / 记录<textarea v-model="reason" rows="3" maxlength="500" /></label>
        <p class="hint">重复提交同一请求号是幂等的；使用不同请求号再次核验同一票券会被服务端拒绝。</p>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="button primary" :disabled="busy || !ticketNo.trim()">{{ busy ? "正在核验…" : "确认人工入园" }}</button>
      </form>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>本次操作记录</h2><span class="muted">仅显示当前页面</span></div>
      <div v-if="results.length === 0" class="data-state">等待核验票券</div>
      <div v-for="item in results" :key="`${item.ticket}-${item.time}`" class="result-row">
        <span class="result-dot" :class="{ success: item.success }" /><div><strong>{{ item.ticket }}</strong><p>{{ item.message }}</p></div><time>{{ item.time }}</time>
      </div>
    </section>
  </div>
</template>
