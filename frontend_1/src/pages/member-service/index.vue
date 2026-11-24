<script setup>
import { ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { request, showError } from "../../utils/api"
import { getToken, clearSession, redirectToLogin } from "../../utils/session.js"

const section = ref("about")
const profile = ref(null)
const loading = ref(false)
const error = ref("")
const loggingOut = ref(false)
const titles = { profile: "个人信息", security: "账户安全", contact: "联系客服", notice: "预约须知", about: "关于我们" }
onLoad(async options => {
  section.value = Object.prototype.hasOwnProperty.call(titles, options.section) ? options.section : "about"
  uni.setNavigationBarTitle({ title: titles[section.value] })
  if (["profile", "security"].includes(section.value)) {
    if (!getToken()) { redirectToLogin(`/pages/member-service/index?section=${section.value}`); return }
    await loadProfile()
  }
})
async function loadProfile() {
  loading.value = true
  error.value = ""
  try { profile.value = await request("/members/me") }
  catch (reason) { error.value = reason.message || "会员信息读取失败"; showError(reason) }
  finally { loading.value = false }
}
function phoneInfo() { uni.navigateTo({ url: "/pages/account-info/index" }) }
async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    const confirmed = await new Promise(resolve => uni.showModal({ title: "确认退出登录？", content: "退出后，订单和会员余额仍会保留在原账户中。", confirmText: "退出登录", success: result => resolve(result.confirm), fail: () => resolve(false) }))
    if (!confirmed) return
    await request("/auth/logout", { method: "POST" })
    clearSession()
    uni.showToast({ title: "已退出登录", icon: "none" })
    uni.switchTab({ url: "/pages/mine/index" })
  } catch (reason) { showError(reason) }
  finally { loggingOut.value = false }
}
</script>
<template>
  <view class="member-service-page">
    <view class="service-panel">
      <text class="service-title">{{ titles[section] }}</text>
      <text v-if="loading" class="service-copy">正在加载会员资料…</text>
      <view v-else-if="error"><text class="service-error">{{ error }}</text><button @tap="loadProfile">重新加载</button></view>
      <template v-else-if="section === 'profile'">
        <view class="info-row"><text>昵称</text><text>{{ profile?.nickname || '未设置' }}</text></view>
        <view class="info-row"><text>手机号</text><text>{{ profile?.phone_masked || '未提供' }}</text></view>
        <view class="info-row"><text>会员身份</text><text>会员</text></view>
        <text class="service-copy">资料修改、手机号变更请联系园区前台核验处理。</text>
        <button class="light-button" @tap="phoneInfo">查看手机号使用说明</button>
      </template>
      <template v-else-if="section === 'security'">
        <view class="info-row"><text>当前手机号</text><text>{{ profile?.phone_masked || '未提供' }}</text></view>
        <text class="service-copy">使用微信登录，无需设置密码。退出登录会撤销当前会话，不会清空余额或删除订单。</text>
        <button class="light-button" @tap="phoneInfo">查看个人信息使用说明</button>
        <button class="logout-button" :disabled="loggingOut" :loading="loggingOut" @tap="logout">退出登录</button>
      </template>
      <template v-else-if="section === 'notice'">
        <text class="service-copy">私汤预约时不选择具体房号，到店后由前台分房，实际使用从前台分房起算。</text>
        <text class="service-copy">连续场次需相邻，作为一个订单预约，仅末场清洁。房间库存、价格和时间以预约页面及服务端最终确认为准。</text>
        <text class="service-copy">待支付预约预占保留15分钟。晚到冲突、取消与退款按现有业务规则由前台协助处理。</text>
        <text class="service-copy">公共浴池门票付款后30天内有效，须符合工作日票或节假日票适用日期；节假日包含周六、周日及后台配置节假日。请在订单详情查看票券及核验二维码。</text>
      </template>
      <template v-else-if="section === 'contact'">
        <text class="service-copy">请联系蜀南温泉园区前台，或拨打园区现场公示的服务电话。</text>
        <text class="service-copy">咨询订单、核销或退款时，可在订单详情复制订单号，供前台查询核对。</text>
      </template>
      <template v-else>
        <text class="service-copy">蜀南温泉会员中心</text>
        <text class="service-copy">为会员提供公共浴池购票、私汤预约、储值余额查询、订单与票券查询服务。</text>
        <button class="light-button" @tap="phoneInfo">个人信息使用说明</button>
      </template>
    </view>
  </view>
</template>
<style scoped>
.member-service-page { min-height: 100vh; box-sizing: border-box; padding: 28rpx; color: #263f38; background: #f8f6f1; }
.service-panel { padding: 30rpx; border-radius: 26rpx; background: #fff; }
.service-title { display: block; margin-bottom: 26rpx; font-size: 32rpx; font-weight: 600; }
.service-copy { display: block; margin: 22rpx 0; font-size: 26rpx; line-height: 1.9; color: #687a70; }
.info-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 24rpx; padding: 24rpx 0; border-bottom: 1rpx solid #eee9df; font-size: 26rpx; }
.info-row > text:last-child { max-width: 70%; text-align: right; overflow-wrap: anywhere; }
.light-button,.logout-button { margin-top: 26rpx; border-radius: 18rpx; font-size: 26rpx; }
.light-button { color: #246b61; background: #edf4ee; }
.logout-button { color: #a34a34; background: #fff5ef; }
button::after { border: 0; }
.service-error { color: #a34a34; font-size: 24rpx; }
</style>
