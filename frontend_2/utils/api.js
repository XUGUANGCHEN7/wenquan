const config = require("../config")

function request(path, { method = "GET", data, auth = true } = {}) {
  const token = wx.getStorageSync("dining_member_token")
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${config.apiBase}${path}`, method, data,
      header: { "Content-Type": "application/json", ...(auth && token ? { Authorization: `Bearer ${token}` } : {}) },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) return resolve(response.data)
        const body = response.data || {}
        const error = new Error(body.message || `请求失败（${response.statusCode}）`)
        error.code = body.code || "HTTP_ERROR"
        reject(error)
      },
      fail(error) { reject(new Error(error.errMsg || "网络连接失败，请稍后重试")) }
    })
  })
}

async function loginMember() {
  if (!config.development) throw new Error("正式会员身份核验适配器尚未配置")
  const result = await request("/auth/dev", { method: "POST", data: { role: "member" }, auth: false })
  wx.setStorageSync("dining_member_token", result.access_token)
  return result
}

async function payOrder(orderNo, method) {
  const payment = await request(`/orders/${orderNo}/payments`, { method: "POST", data: { method: method.toLowerCase() } })
  if (method === "WECHAT") {
    if (!config.development) throw new Error("正式微信支付适配器尚未配置")
    await request(`/payments/${payment.payment_no}/mock-confirm`, { method: "POST" })
  }
  return request(`/dining/orders/${orderNo}`)
}

function showError(error) {
  wx.showToast({ title: (error.message || "操作失败").slice(0, 40), icon: "none", duration: 3000 })
}
module.exports = { request, loginMember, payOrder, showError }
