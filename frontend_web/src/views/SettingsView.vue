<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api } from "../api"
import { formatMoney, parseYuanToCents } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface Config { key: string; value: number; description: string }
interface Activity { id: string; name: string; principal_cents: number; gift_cents: number; active?: boolean }
interface MenuItem { id: string; name: string; price_cents: number; stock: number | null; available: boolean; description: string }
interface ConfigMeta { label: string; description: string; money: boolean }
const configMeta: Record<string, ConfigMeta> = {
  private_slot_price_cents: { label: "私汤基础价", description: "一场 120 分钟私汤的基础价格，单位：元。", money: true },
  deposit_amount_cents: { label: "手牌押金", description: "每枚手牌单独收取的押金，具体金额待业务方确认，单位：元。", money: true },
  extension_price_cents: { label: "加钟价格", description: "每办理一次加钟的收费价格，单位：元。", money: true },
  extension_minutes: { label: "加钟时长", description: "每次加钟延长的时长，单位：分钟。", money: false },
}
const configs = ref<Config[]>([])
const configDrafts = ref<Record<string, string>>({})
const activities = ref<Activity[]>([])
const menu = ref<MenuItem[]>([])
const loading = ref(true)
const error = ref("")
const notice = ref("")
const visitDate = ref(new Date(Date.now() + 86400000).toISOString().slice(0, 10))
const adultYuan = ref("29.00")
const childYuan = ref("29.00")
const activityForm = ref({ id: "", name: "", principalYuan: "200.00", giftYuan: "20.00", active: true })
const selectedActivityId = ref("")
const menuItemId = ref("")
const menuDraft = ref({ priceYuan: "0.00", stock: 0, available: true, description: "" })
const qrId = ref("qr-01")
const qrActive = ref(true)

function isMoneyConfig(item: Config) {
  return item.key.endsWith("_cents") || configMeta[item.key]?.money === true
}
function configLabel(item: Config) {
  return configMeta[item.key]?.label ?? "其他配置项"
}
function configDescription(item: Config) {
  return configMeta[item.key]?.description ?? "未登记说明的配置项，请核对后再修改。"
}
function syncConfigDrafts() {
  configDrafts.value = Object.fromEntries(configs.value.map((item) => [
    item.key, isMoneyConfig(item) ? formatMoney(item.value) : String(item.value),
  ]))
}
function normalizeYuan(value: string) {
  const cents = parseYuanToCents(value)
  return cents === null ? value : formatMoney(cents)
}
function normalizeConfigDraft(item: Config) {
  configDrafts.value[item.key] = normalizeYuan(configDrafts.value[item.key] ?? "")
}

async function load() {
  loading.value = true; error.value = ""
  try {
    const [configsData, activitiesData, menuData] = await Promise.all([
      api.get<Config[]>("/admin/config"), api.get<Activity[]>("/catalog/recharge-activities"), api.get<MenuItem[]>("/dining/menu"),
    ])
    configs.value = configsData; activities.value = activitiesData; menu.value = menuData; syncConfigDrafts()
    if (!menuItemId.value && menu.value.length) selectMenu(menu.value[0].id)
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "配置读取失败" }
  finally { loading.value = false }
}

function showError(cause: unknown, fallback = "保存失败") {
  error.value = cause instanceof Error ? cause.message : fallback
}

async function saveConfig(item: Config) {
  error.value = ""; notice.value = ""
  const cents = isMoneyConfig(item) ? parseYuanToCents(configDrafts.value[item.key] ?? "") : null
  const minutes = isMoneyConfig(item) ? null : Number(configDrafts.value[item.key])
  if (isMoneyConfig(item) && cents === null) { error.value = `${configLabel(item)}金额格式不正确，请输入元，最多两位小数`; return }
  if (!isMoneyConfig(item) && (!Number.isInteger(minutes) || (minutes ?? 0) < 0)) { error.value = `${configLabel(item)}必须是非负整数`; return }
  const value = isMoneyConfig(item) ? cents! : minutes!
  try {
    await api.post(`/admin/config/${item.key}`, { value, description: configDescription(item) })
    item.value = value
    configDrafts.value[item.key] = isMoneyConfig(item) ? formatMoney(value) : String(value)
    notice.value = `${configLabel(item)}已更新并写入审计`
  } catch (cause) { showError(cause) }
}
async function savePrice() {
  error.value = ""; notice.value = ""
  const adultCents = parseYuanToCents(adultYuan.value)
  const childCents = parseYuanToCents(childYuan.value)
  if (adultCents === null || childCents === null) { error.value = "票价格式不正确，请输入元，最多两位小数"; return }
  try {
    await api.post(`/admin/ticket-prices/${visitDate.value}`, { adult_cents: adultCents, child_cents: childCents, is_holiday: true, note: "管理员手工维护节假日价格" })
    notice.value = "票种价格已更新"
  } catch (cause) { showError(cause) }
}
function selectActivity(id: string) {
  selectedActivityId.value = id
  const found = activities.value.find((item) => item.id === id)
  activityForm.value = found ? {
    id: found.id, name: found.name, principalYuan: formatMoney(found.principal_cents),
    giftYuan: formatMoney(found.gift_cents), active: found.active ?? true,
  } : { id: "", name: "", principalYuan: "200.00", giftYuan: "20.00", active: true }
}
async function saveActivity() {
  error.value = ""; notice.value = ""
  const principalCents = parseYuanToCents(activityForm.value.principalYuan)
  const giftCents = parseYuanToCents(activityForm.value.giftYuan)
  if (!activityForm.value.name.trim()) { error.value = "请填写活动名称"; return }
  if (principalCents === null || giftCents === null) { error.value = "充值金额格式不正确，请输入元，最多两位小数"; return }
  if (principalCents <= 0) { error.value = "充值本金必须大于 0 元"; return }
  try {
    const result = await api.post<Activity>("/admin/recharge-activities", {
      id: activityForm.value.id || null, name: activityForm.value.name.trim(),
      principal_cents: principalCents, gift_cents: giftCents, active: activityForm.value.active,
    })
    notice.value = `充值活动 ${result.name} 已保存`; await load()
  } catch (cause) { showError(cause) }
}
function selectMenu(id: string) {
  menuItemId.value = id
  const item = menu.value.find((entry) => entry.id === id)
  if (item) menuDraft.value = { priceYuan: formatMoney(item.price_cents), stock: item.stock ?? 0, available: item.available, description: item.description }
}
async function saveMenu() {
  error.value = ""; notice.value = ""
  const priceCents = parseYuanToCents(menuDraft.value.priceYuan)
  if (priceCents === null) { error.value = "菜品价格格式不正确，请输入元，最多两位小数"; return }
  if (!Number.isInteger(menuDraft.value.stock) || menuDraft.value.stock < 0) { error.value = "库存必须是非负整数"; return }
  try {
    await api.post(`/admin/menu-items/${menuItemId.value}`, {
      price_cents: priceCents, stock: menuDraft.value.stock,
      available: menuDraft.value.available, description: menuDraft.value.description,
    })
    notice.value = "菜品价格与库存已更新"; await load()
  } catch (cause) { showError(cause) }
}
async function saveQr(reprint: boolean) {
  try { const result = await api.post<{ code: string; version: number; active: boolean }>(`/admin/room-codes/${qrId.value}`, { active: qrActive.value, reprint }); notice.value = `${result.code} 已${result.active ? "启用" : "停用"}，版本 ${result.version}` }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "保存失败" }
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="管理员专用 · 服务端统一规则" title="商业规则配置" description="只维护已确认字段；金额以元录入并保留两位小数，取消政策、部分退款公式与押金扣押规则不会由页面自行补充。" />
  <p v-if="notice" class="success-note">{{ notice }}</p>
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
    <div class="settings-grid">
      <section class="panel"><div class="panel-head"><h2>基础价格与时长</h2></div>
        <div v-for="item in configs" :key="item.key" class="config-row"><div><strong>{{ configLabel(item) }}</strong><small>{{ configDescription(item) }}</small></div><input v-if="isMoneyConfig(item)" v-model="configDrafts[item.key]" type="text" inputmode="decimal" placeholder="0.00" aria-label="金额（元）" @blur="normalizeConfigDraft(item)" /><input v-else v-model="configDrafts[item.key]" type="number" min="0" step="1" aria-label="整数" /><button class="mini-button" @click="saveConfig(item)">保存</button></div>
      </section>
      <section class="panel"><div class="panel-head"><h2>节假日票种价格</h2></div>
        <form class="form-stack" @submit.prevent="savePrice"><label>日期<input v-model="visitDate" type="date" /></label><div class="form-row"><label>成人票价（元）<input v-model="adultYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="adultYuan = normalizeYuan(adultYuan)" /></label><label>儿童票价（元）<input v-model="childYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="childYuan = normalizeYuan(childYuan)" /></label></div><button class="button secondary">保存当日规则</button></form>
      </section>
      <section class="panel"><div class="panel-head"><h2>充值活动（充本金赠余额）</h2></div>
        <select :value="selectedActivityId" @change="selectActivity(($event.target as HTMLSelectElement).value)"><option value="">新建活动</option><option v-for="item in activities" :key="item.id" :value="item.id">{{ item.name }} · 本金 ¥{{ formatMoney(item.principal_cents) }}，赠 ¥{{ formatMoney(item.gift_cents) }}</option></select>
        <form class="form-stack compact-form" @submit.prevent="saveActivity"><label>活动名称<input v-model="activityForm.name" /></label><div class="form-row"><label>本金（元）<input v-model="activityForm.principalYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="activityForm.principalYuan = normalizeYuan(activityForm.principalYuan)" /></label><label>赠送余额（元）<input v-model="activityForm.giftYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="activityForm.giftYuan = normalizeYuan(activityForm.giftYuan)" /></label></div><label class="check-row"><input v-model="activityForm.active" type="checkbox" />启用活动</label><button class="button secondary">保存充值活动</button></form>
      </section>
      <section class="panel"><div class="panel-head"><h2>菜单价格与库存</h2></div>
        <select :value="menuItemId" @change="selectMenu(($event.target as HTMLSelectElement).value)"><option v-for="item in menu" :key="item.id" :value="item.id">{{ item.name }} · ¥{{ formatMoney(item.price_cents) }}</option></select>
        <form class="form-stack compact-form" @submit.prevent="saveMenu"><label>价格（元）<input v-model="menuDraft.priceYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="menuDraft.priceYuan = normalizeYuan(menuDraft.priceYuan)" /></label><label>库存<input v-model.number="menuDraft.stock" type="number" min="0" step="1" /></label><label>描述<textarea v-model="menuDraft.description" rows="2" /></label><label class="check-row"><input v-model="menuDraft.available" type="checkbox" />可售</label><button class="button secondary">保存菜品</button></form>
      </section>
      <section class="panel wide"><div class="panel-head"><h2>房间码</h2></div>
        <div class="form-row"><label>房间码记录编号<input v-model="qrId" /></label><label class="check-row"><input v-model="qrActive" type="checkbox" />启用</label></div>
        <div class="button-row"><button class="button secondary" @click="saveQr(false)">保存启用状态</button><button class="button primary" @click="saveQr(true)">保存并重印（版本 +1）</button></div>
        <p class="hint">房间码仅定位送餐房号，不证明访客在场，也不授予会员余额权限。</p>
      </section>
    </div>
  </DataState>
</template>
