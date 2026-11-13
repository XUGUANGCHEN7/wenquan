<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { api } from "../api"
import { formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface ReportSummary {
  period: string; period_start: string; period_end: string
  ticket_revenue_cents: number; private_revenue_cents: number; dining_revenue_cents: number
  extension_revenue_cents: number; recharge_principal_cents: number
  recharge_gift_cents: number; unrefunded_deposit_cents: number; deposit_is_revenue: boolean
}

const period = ref<"day" | "week" | "month" | "year">("day")
const anchor = ref(new Date().toISOString().slice(0, 10))
const report = ref<ReportSummary | null>(null)
const loading = ref(false)
const error = ref("")
const periodLabel = computed(() => ({ day: "单日", week: "单周", month: "单月", year: "单年" }[period.value]))
const incomeTotal = computed(() => report.value
  ? report.value.ticket_revenue_cents + report.value.private_revenue_cents + report.value.dining_revenue_cents
  : 0)

async function load() {
  loading.value = true; error.value = ""
  try {
    report.value = await api.get<ReportSummary>(`/operations/reports/summary?period=${period.value}&anchor=${anchor.value}`)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "财务报表读取失败" }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <PageHeader eyebrow="FINANCIAL SUMMARY" title="财务汇总" description="按单日、单周、单月或单年查看收入与非收入财务；充值本金、赠送和未退押金单独展示。">
    <select v-model="period" class="inline-input" @change="load"><option value="day">单日</option><option value="week">单周</option><option value="month">单月</option><option value="year">单年</option></select>
    <input v-model="anchor" type="date" class="inline-input" /><button class="button primary compact" @click="load">查询{{ periodLabel }}</button>
  </PageHeader>
  <DataState :loading="loading" :error="error" :empty="!report" @retry="load">
    <p v-if="report" class="page-note">统计区间：{{ report.period_start }} 至 {{ report.period_end }}</p>
    <section v-if="report" class="panel"><div class="panel-head"><h2>收入财务</h2><span class="operator-tag">合计 {{ formatMoney(incomeTotal) }}</span></div>
      <div class="metric-grid compact-metrics">
        <article class="metric-card"><span>公共浴室票券收入</span><strong>{{ formatMoney(report.ticket_revenue_cents) }}</strong><small>已支付票券订单</small></article>
        <article class="metric-card"><span>私汤收入</span><strong>{{ formatMoney(report.private_revenue_cents) }}</strong><small>已支付私汤订单</small></article>
        <article class="metric-card"><span>点餐收入</span><strong>{{ formatMoney(report.dining_revenue_cents) }}</strong><small>已支付且可送达订单</small></article>
        <article class="metric-card"><span>加钟收入</span><strong>{{ formatMoney(report.extension_revenue_cents) }}</strong><small>设备确认后计入</small></article>
      </div>
    </section>
    <section v-if="report" class="panel"><div class="panel-head"><h2>非收入财务</h2><span class="muted">充值与押金不是票款收入</span></div>
      <div class="metric-grid compact-metrics">
        <article class="metric-card warning"><span>充值本金</span><strong>{{ formatMoney(report.recharge_principal_cents) }}</strong><small>会员储值负债</small></article>
        <article class="metric-card warning"><span>充值赠送</span><strong>{{ formatMoney(report.recharge_gift_cents) }}</strong><small>与本金分账</small></article>
        <article class="metric-card warning"><span>未退押金</span><strong>{{ formatMoney(report.unrefunded_deposit_cents) }}</strong><small>{{ report.deposit_is_revenue ? "已计收入" : "逐枚独立责任，非收入" }}</small></article>
      </div>
    </section>
    <section v-if="report" class="panel"><div class="panel-head"><h2>口径提示</h2></div>
      <ul class="task-list">
        <li><span>01</span><div><strong>收入按已支付订单统计</strong><p>退款受理、处理中和失败不会自动从收入中扣减；以渠道确认和财务对账为准。</p></div></li>
        <li><span>02</span><div><strong>充值不是收入</strong><p>本金和赠送余额是会员负债，点餐、票券和私汤消费完成后才形成对应收入。</p></div></li>
        <li><span>03</span><div><strong>押金单独管理</strong><p>未退押金不视为票款收入，必须按每枚手牌独立退款责任处理。</p></div></li>
      </ul>
    </section>
  </DataState>
</template>
