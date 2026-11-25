<script setup>
import { ref } from "vue"
import { onHide, onLoad, onShow, onUnload } from "@dcloudio/uni-app"
import config from "../../config.js"
import { request } from "../../utils/api.js"
import { getToken, redirectToLogin } from "../../utils/session.js"
import OrderCodeRow from "../../components/OrderCodeRow.vue"
import OrderQrImage from "../../components/OrderQrImage.vue"
import { createOrderDetailModel } from "./detail-state.js"

const model = createOrderDetailModel({ request, getToken, allowExamples: config.development })
const { state, presentation: order } = model
const refundOpen = ref(false), refundReason = ref(""), refundBusy = ref(false), refundError = ref("")
const qrError = ref(false)
let id = "", example = false
onLoad(options => { id = typeof options.id === "string" ? options.id : ""; example = options.example === "1" })
onShow(() => model.load(id, { example }))
onHide(model.invalidate)
onUnload(model.invalidate)
function reload() { model.load(id, { example }) }
function moneyText(value) { return value === "待确认" ? value : `¥${value}` }
function timeText(value) {
  if (!value) return "—"
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`)
  if (Number.isNaN(date.getTime())) return "—"
  return new Date(date.getTime() + 8 * 3600000).toISOString().slice(0, 19).replace("T", " ")
}
function slotText(value) { return value ? String(value).replace("T", " ").slice(0, 16) : "待确认" }
function contact() { uni.showToast({ title: "请前往前台或拨打园区公示电话", icon: "none" }) }
function login() { redirectToLogin(`/pages/orders/detail?id=${encodeURIComponent(id)}`) }
async function submitRefund() {
  if (refundBusy.value) return
  refundBusy.value = true; refundError.value = ""
  try {
    const application = await model.submitRefund(refundReason.value)
    if (application) { refundOpen.value = false; uni.showToast({ title: state.exampleMode ? "示例申请已演示" : "申请已提交，等待审核", icon: "none" }) }
  } catch (error) { refundError.value = error.message || "申请失败，请重试" }
  finally { refundBusy.value = false }
}
</script>

<template>
  <view class="page order-detail-page">
    <view v-if="state.exampleMode" class="orders-example-note">示例订单 · 非真实购买记录，编号不能用于前台核销</view>
    <view v-if="state.loading" class="orders-empty"><view class="orders-loading" /><text class="orders-empty-copy">正在读取订单详情…</text></view>
    <view v-else-if="state.guest" class="orders-empty"><text class="orders-empty-title">登录后查看订单详情</text><button class="orders-primary" @tap="login">登录 / 注册</button></view>
    <view v-else-if="state.error" class="orders-empty"><text class="orders-empty-title">订单详情暂不可用</text><text class="orders-empty-copy">{{ state.error }}</text><button class="orders-primary" @tap="reload">重新加载</button></view>
    <template v-else-if="order">
      <view class="detail-status-panel">
        <image class="detail-status-background" src="/static/orders/status-banner.jpg" mode="aspectFill" />
        <view class="detail-status-copy">
          <text class="detail-status-title sn-serif">{{ order.statusLabel }}</text>
          <text v-if="order.statusCaption" class="detail-status-caption">{{ order.statusCaption }}</text>
        </view>
      </view>

      <view v-if="order.qrCodeText && !state.exampleMode" class="detail-panel detail-qr">
        <text class="detail-section-title">入场核验二维码</text>
        <view class="detail-qr-code"><OrderQrImage :key="order.qrCodeText" :text="order.qrCodeText" @error="qrError = true" /></view>
        <text class="detail-product-spec">请向前台出示，扫码查看本订单及票券</text>
        <text class="detail-product-spec">核对并勾选后由前台确认核销</text>
        <text v-if="qrError" class="order-refund-error">二维码暂未生成，请使用下方订单编号查询</text>
      </view>

      <view class="detail-panel detail-product">
        <image v-if="order.image" class="detail-product-image" :src="order.image" mode="aspectFill" />
        <view class="detail-product-copy"><text class="detail-product-title sn-serif">{{ order.title }}</text><text class="detail-product-spec">{{ order.specification }}</text><text class="detail-product-spec">商品数量 {{ order.quantityLabel }}</text><text v-if="order.date" class="detail-product-spec">{{ order.date }}</text></view>
      </view>

      <view class="detail-panel"><text class="detail-section-title">订单编号</text><OrderCodeRow label="订单编号" :code="order.order_no" /></view>

      <view v-if="order.hasVouchers" class="detail-panel detail-vouchers">
        <text class="detail-section-title">{{ order.order_type === 'PRIVATE' ? '预约凭证' : '票券凭证' }}</text>
        <template v-if="order.order_type === 'TICKET'">
          <view v-for="ticket in order.tickets" :key="ticket.ticket_no" class="detail-voucher">
            <view class="detail-voucher-meta"><text>{{ ticket.categoryLabel }}</text><text class="detail-voucher-status" :class="{ 'is-used': ticket.status !== 'UNUSED' }">{{ ticket.statusLabel }}</text></view>
            <OrderCodeRow :label="'票券 ' + ticket.index" :code="ticket.ticket_no" />
          </view>
        </template>
        <template v-else-if="order.order_type === 'PRIVATE'">
          <view v-if="order.ticket_no" class="detail-voucher"><OrderCodeRow label="私汤票券编号" :code="order.ticket_no" /><text class="detail-product-spec">{{ order.voucher_status === 'USED' ? '已核销，再次核销会失败' : '待使用' }}</text></view>
          <view v-if="order.booking_id" class="detail-voucher"><OrderCodeRow label="预约编号" :code="order.booking_id" /></view>
        </template>
      </view>

      <view v-if="order.order_type === 'PRIVATE'" class="detail-panel">
        <text class="detail-section-title">预约信息</text>
        <view v-if="order.visit_date" class="detail-info-row"><text>预约日期</text><text>{{ order.visit_date }}</text></view>
        <view v-if="order.start_at" class="detail-info-row"><text>预约开始</text><text>{{ slotText(order.start_at) }}</text></view>
        <view v-if="order.end_at" class="detail-info-row"><text>预约结束</text><text>{{ slotText(order.end_at) }}</text></view>
        <view v-if="order.room_type || order.room_type_name" class="detail-info-row"><text>房型</text><text>{{ order.room_type_name || order.room_type }}</text></view>
        <view class="detail-info-row"><text>分房信息</text><text>{{ order.summary }}</text></view>
      </view>

      <view v-if="order.order_type === 'RECHARGE'" class="detail-panel">
        <text class="detail-section-title">储值信息</text>
        <view class="detail-info-row"><text>充值金额</text><text>{{ moneyText(order.principalAmount) }}</text></view>
        <view v-if="Number.isInteger(order.gift_cents)" class="detail-info-row"><text>赠送余额</text><text>{{ moneyText(order.giftAmount) }}</text></view>
        <view class="detail-info-row"><text>实际到账金额</text><text>{{ moneyText(order.creditedAmount) }}</text></view>
        <view class="detail-info-row"><text>充值状态</text><text>{{ order.statusLabel }}</text></view>
      </view>

      <view class="detail-panel">
        <text class="detail-section-title">支付及订单时间</text>
        <view class="detail-info-row"><text>订单金额</text><text>{{ order.amount === '—' ? '待确认' : '¥' + order.amount }}</text></view>
        <view class="detail-info-row"><text>实付金额</text><text>{{ moneyText(order.paidAmount) }}</text></view>
        <view class="detail-info-row"><text>支付方式</text><text>{{ order.paymentLabel }}</text></view>
        <view class="detail-info-row"><text>下单时间</text><text>{{ timeText(order.created_at) }}</text></view>
        <view class="detail-info-row"><text>支付时间</text><text>{{ order.paid_at ? timeText(order.paid_at) : '未支付' }}</text></view>
        <view v-if="order.day_type" class="detail-info-row"><text>适用日期</text><text>{{ order.day_type === 'HOLIDAY' ? '周六、周日及后台配置的节假日' : '非节假日的周一至周五' }}</text></view>
        <view v-if="order.day_type" class="detail-info-row"><text>有效期</text><text>{{ order.valid_until ? timeText(order.valid_until) : '付款后30天内有效' }}</text></view>
        <view v-if="order.admission_error && order.status === 'PAID'" class="detail-info-row"><text>入园提示</text><text>{{ order.admission_error.message }}</text></view>
      </view>

      <view class="detail-panel detail-actions">
        <button class="detail-contact-button" @tap="contact">联系客服</button>
        <button v-if="order.canRefund" class="detail-refund-button" @tap="refundOpen = true; refundError = ''">申请退款</button>
      </view>
      <view v-if="refundOpen && order.canRefund" class="detail-panel order-refund-form">
        <text>申请整单退款</text><text class="order-detail-hint">提交后等待审核，审核期间暂停核销。</text>
        <textarea v-model="refundReason" class="order-refund-reason" maxlength="500" placeholder="请填写退款原因" />
        <text v-if="refundError" class="order-refund-error">{{ refundError }}</text>
        <view class="order-refund-actions"><button class="order-detail-button" :disabled="refundBusy" @tap="refundOpen = false">取消</button><button class="order-detail-button" :disabled="refundBusy" @tap="submitRefund">{{ refundBusy ? '正在提交…' : '提交申请' }}</button></view>
      </view>
    </template>
  </view>
</template>

<style>
@import "./style.css";
@import "./detail.css";
</style>
