<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api } from "../api"
import { formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface Report { report_date: string; ticket_revenue_cents: number; private_revenue_cents: number; dining_revenue_cents: number; extension_revenue_cents: number; recharge_principal_cents: number; recharge_gift_cents: number; unrefunded_deposit_cents: number; deposit_is_revenue: boolean }
const day = ref(new Date().toISOString().slice(0, 10))
const report = ref<Report | null>(null)
const loading = ref(false)
const error = ref("")

async function load() {
  loading.value = true; error.value = ""
  try { report.value = await api.get<Report>(`/operations/reports/daily?report_date=${day.value}`) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "报表读取失败" }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <PageHeader eyebrow="DAILY SETTLEMENT" title="日结与财务边界" description="收入、充值本金/赠送与未退押金分开展示；押金不视为票款收入。">
    <input v-model="day" type="date" class="inline-input" /><button class="button primary compact" @click="load">查询日结</button>
  </PageHeader>
  <DataState :loading="loading" :error="error" :empty="!report" @retry="load">
    <section v-if="report" class="metric-grid">
      <article class="metric-card"><span>票券收入</span><strong>{{ formatMoney(report.ticket_revenue_cents) }}</strong><small>仅已支付订单</small></article>
      <article class="metric-card"><span>私汤收入</span><strong>{{ formatMoney(report.private_revenue_cents) }}</strong><small>含预约成交快照</small></article>
      <article class="metric-card"><span>点餐收入</span><strong>{{ formatMoney(report.dining_revenue_cents) }}</strong><small>支付且可送达后入队</small></article>
      <article class="metric-card"><span>加钟收入</span><strong>{{ formatMoney(report.extension_revenue_cents) }}</strong><small>设备确认后延长使用</small></article>
      <article class="metric-card warning"><span>充值本金</span><strong>{{ formatMoney(report.recharge_principal_cents) }}</strong><small>负债，不是当日收入</small></article>
      <article class="metric-card warning"><span>充值赠送</span><strong>{{ formatMoney(report.recharge_gift_cents) }}</strong><small>与本金分账</small></article>
      <article class="metric-card warning"><span>未退押金</span><strong>{{ formatMoney(report.unrefunded_deposit_cents) }}</strong><small>逐枚独立责任，非收入</small></article>
    </section>
    <section v-if="report" class="panel"><div class="panel-head"><h2>待人工确认事项</h2></div><ul class="task-list"><li><span>01</span><div><strong>微信渠道对账差异</strong><p>本期报表先展示业务事实；真实商户账单导入与差异记录待微信能力确认。</p></div></li><li><span>02</span><div><strong>退款状态</strong><p>受理、处理中、成功、异常分开维护，App 不把受理显示为退款成功。</p></div></li></ul></section>
  </DataState>
</template>
