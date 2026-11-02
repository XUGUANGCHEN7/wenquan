<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { api } from "../api"
import { formatMoney, parseYuanToCents } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface Merchant { id: string; name: string; active: boolean; item_count: number }
interface AdminMenuItem {
  id: string; merchant_id: string; merchant_name: string; merchant_active: boolean
  name: string; description: string; category: string; image_url: string
  price_cents: number; stock: number | null; available: boolean
}
interface ItemForm {
  id: string; name: string; category: string; priceYuan: string
  stock: number; imageUrl: string; description: string; available: boolean
}

const merchants = ref<Merchant[]>([])
const items = ref<AdminMenuItem[]>([])
const selectedMerchantId = ref("")
const selectedItemId = ref("")
const merchantForm = ref({ name: "", active: true })
const itemForm = ref<ItemForm>({
  id: "", name: "", category: "热销推荐", priceYuan: "0.00", stock: 0,
  imageUrl: "", description: "", available: true,
})
const unlimitedStock = ref(false)
const loading = ref(true)
const loadError = ref("")
const actionError = ref("")
const notice = ref("")
const merchantSaving = ref(false)
const itemSaving = ref(false)

const selectedMerchant = computed(() => merchants.value.find((item) => item.id === selectedMerchantId.value) ?? null)
const merchantItems = computed(() => items.value.filter((item) => item.merchant_id === selectedMerchantId.value))

function setActionError(cause: unknown, fallback: string) {
  actionError.value = cause instanceof Error ? cause.message : fallback
}
function resetItem() {
  selectedItemId.value = ""
  itemForm.value = {
    id: "", name: "", category: "热销推荐", priceYuan: "0.00", stock: 0,
    imageUrl: "", description: "", available: true,
  }
  unlimitedStock.value = false
}
function newItem() {
  resetItem()
  actionError.value = ""; notice.value = ""
}
function normalizePrice() {
  const cents = parseYuanToCents(itemForm.value.priceYuan)
  if (cents !== null) itemForm.value.priceYuan = formatMoney(cents)
}
function chooseMerchant(merchant: Merchant) {
  selectedMerchantId.value = merchant.id
  merchantForm.value = { name: merchant.name, active: merchant.active }
  resetItem()
}
async function load(preferredMerchantId?: string) {
  loading.value = true; loadError.value = ""
  try {
    const [merchantData, itemData] = await Promise.all([
      api.get<Merchant[]>("/admin/merchants"),
      api.get<AdminMenuItem[]>("/admin/menu-items"),
    ])
    merchants.value = merchantData
    items.value = itemData
    const wanted = preferredMerchantId || selectedMerchantId.value
    const next = merchants.value.find((item) => item.id === wanted) ?? merchants.value[0]
    if (next) chooseMerchant(next)
    else { selectedMerchantId.value = ""; merchantForm.value = { name: "", active: true }; resetItem() }
  } catch (cause) { loadError.value = cause instanceof Error ? cause.message : "商家商品读取失败" }
  finally { loading.value = false }
}
function newMerchant() {
  selectedMerchantId.value = ""
  merchantForm.value = { name: "", active: true }
  resetItem()
  actionError.value = ""; notice.value = ""
}
async function saveMerchant() {
  actionError.value = ""; notice.value = ""
  if (!merchantForm.value.name.trim()) { actionError.value = "请填写商家名称"; return }
  merchantSaving.value = true
  try {
    const saved = selectedMerchantId.value
      ? await api.patch<Merchant>(`/admin/merchants/${selectedMerchantId.value}`, merchantForm.value)
      : await api.post<Merchant>("/admin/merchants", merchantForm.value)
    notice.value = `商家“${saved.name}”已保存`
    await load(saved.id)
  } catch (cause) { setActionError(cause, "商家保存失败") }
  finally { merchantSaving.value = false }
}
async function deleteMerchant() {
  if (!selectedMerchant.value) return
  if (!window.confirm(`确认删除商家“${selectedMerchant.value.name}”？有商品或历史订单时系统会拒绝删除。`)) return
  actionError.value = ""; notice.value = ""
  try {
    await api.delete(`/admin/merchants/${selectedMerchantId.value}`)
    notice.value = "商家已删除"
    selectedMerchantId.value = ""
    await load()
  } catch (cause) { setActionError(cause, "商家删除失败") }
}
function selectItem(item: AdminMenuItem) {
  selectedItemId.value = item.id
  itemForm.value = {
    id: item.id, name: item.name, category: item.category,
    priceYuan: formatMoney(item.price_cents), stock: item.stock ?? 0,
    imageUrl: item.image_url, description: item.description, available: item.available,
  }
  unlimitedStock.value = item.stock === null
  actionError.value = ""
}
async function saveItem() {
  actionError.value = ""; notice.value = ""
  if (!selectedMerchantId.value) { actionError.value = "请先选择或新建商家"; return }
  if (!itemForm.value.name.trim()) { actionError.value = "请填写商品名称"; return }
  const priceCents = parseYuanToCents(itemForm.value.priceYuan)
  if (priceCents === null) { actionError.value = "商品价格格式不正确，请输入元，最多两位小数"; return }
  if (!unlimitedStock.value && (!Number.isInteger(itemForm.value.stock) || itemForm.value.stock < 0)) {
    actionError.value = "库存必须是非负整数"; return
  }
  const payload = {
    merchant_id: selectedMerchantId.value, name: itemForm.value.name.trim(),
    category: itemForm.value.category.trim() || "热销推荐", price_cents: priceCents,
    stock: unlimitedStock.value ? null : itemForm.value.stock,
    image_url: itemForm.value.imageUrl.trim(), description: itemForm.value.description.trim(),
    available: itemForm.value.available,
  }
  itemSaving.value = true
  try {
    if (selectedItemId.value) await api.patch(`/admin/menu-items/${selectedItemId.value}`, payload)
    else await api.post("/admin/menu-items", payload)
    notice.value = `商品“${payload.name}”已保存`
    await load(selectedMerchantId.value)
  } catch (cause) { setActionError(cause, "商品保存失败") }
  finally { itemSaving.value = false }
}
async function deleteItem(item: AdminMenuItem) {
  if (!window.confirm(`确认删除商品“${item.name}”？已有历史订单时系统会拒绝删除。`)) return
  actionError.value = ""; notice.value = ""
  try {
    await api.delete(`/admin/menu-items/${item.id}`)
    notice.value = "商品已删除"
    await load(selectedMerchantId.value)
  } catch (cause) { setActionError(cause, "商品删除失败") }
}

onMounted(() => load())
</script>

<template>
  <PageHeader eyebrow="商家与商品管理" title="商家商品" description="管理员可新增、编辑、停用或删除商家和商品；点餐小程序只展示营业商家，下架或售罄商品不能下单。" />
  <p v-if="notice" class="success-note">{{ notice }}</p>
  <p v-if="actionError" class="form-error page-note">{{ actionError }}</p>
  <DataState :loading="loading" :error="loadError" :empty="false" @retry="load()">
    <div class="settings-grid">
      <section class="panel">
        <div class="panel-head"><h2>商家档案</h2><button class="mini-button" @click="newMerchant">新增商家</button></div>
        <p class="hint">停用商家后，其商品不会出现在点餐小程序；已有商品或历史订单的商家不能直接删除。</p>
        <div class="simple-list">
          <div v-for="merchant in merchants" :key="merchant.id" class="simple-row">
            <span><strong>{{ merchant.name }}</strong><br /><small>{{ merchant.item_count }} 件商品</small></span>
            <span class="operator-tag">{{ merchant.active ? "营业中" : "已停用" }}</span>
            <button class="mini-button" @click="chooseMerchant(merchant)">编辑</button>
          </div>
          <p v-if="merchants.length === 0" class="hint">暂无商家，请先新增。</p>
        </div>
        <form class="form-stack compact-form" @submit.prevent="saveMerchant">
          <label>商家名称<input v-model="merchantForm.name" maxlength="100" placeholder="例如：山泉食坊" /></label>
          <label class="check-row"><input v-model="merchantForm.active" type="checkbox" />营业中（点餐端可见）</label>
          <div class="button-row">
            <button class="button secondary" :disabled="merchantSaving">{{ selectedMerchantId ? "保存商家" : "新增商家" }}</button>
            <button v-if="selectedMerchantId" type="button" class="button danger" @click="deleteMerchant">删除商家</button>
          </div>
        </form>
      </section>

      <section class="panel">
        <div class="panel-head"><h2>商品档案</h2><button class="mini-button" :disabled="!selectedMerchantId" @click="newItem">新增商品</button></div>
        <p class="hint">{{ selectedMerchant ? `当前商家：${selectedMerchant.name}` : "请先在左侧选择或新增商家。" }}</p>
        <div class="simple-list">
          <div v-for="item in merchantItems" :key="item.id" class="simple-row">
            <span><strong>{{ item.name }}</strong><br /><small>{{ item.category }} · ¥{{ formatMoney(item.price_cents) }} · {{ item.stock === null ? "不限库存" : `库存 ${item.stock}` }}</small></span>
            <span class="operator-tag">{{ item.available ? "可售" : "已下架" }}</span>
            <button class="mini-button" @click="selectItem(item)">编辑</button>
            <button class="mini-button danger-text" @click="deleteItem(item)">删除</button>
          </div>
          <p v-if="selectedMerchantId && merchantItems.length === 0" class="hint">该商家暂无商品，可在下方新增。</p>
        </div>
        <form v-if="selectedMerchantId" class="form-stack compact-form" @submit.prevent="saveItem">
          <label>商品名称<input v-model="itemForm.name" maxlength="100" /></label>
          <div class="form-row">
            <label>分类<input v-model="itemForm.category" maxlength="50" /></label>
            <label>价格（元）<input v-model="itemForm.priceYuan" type="text" inputmode="decimal" placeholder="0.00" @blur="normalizePrice" /></label>
          </div>
          <div class="form-row">
            <label>库存<input v-model.number="itemForm.stock" type="number" min="0" step="1" :disabled="unlimitedStock" /></label>
            <label class="check-row"><input v-model="unlimitedStock" type="checkbox" />不限库存</label>
          </div>
          <label>图片地址<input v-model="itemForm.imageUrl" maxlength="500" placeholder="https://…" /></label>
          <label>商品描述<textarea v-model="itemForm.description" rows="2" maxlength="300" /></label>
          <label class="check-row"><input v-model="itemForm.available" type="checkbox" />可售</label>
          <button class="button secondary" :disabled="itemSaving">{{ selectedItemId ? "保存商品" : "新增商品" }}</button>
        </form>
      </section>
    </div>
  </DataState>
</template>
