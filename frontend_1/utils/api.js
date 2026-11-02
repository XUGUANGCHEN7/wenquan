const config = require("../config")

function request(path, { method = "GET", data, auth = true } = {}) {
  const token = wx.getStorageSync("member_token") || (config.development ? config.devToken : "")
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${config.apiBase}${path}`,
      method,
      data,
      header: {
        "Content-Type": "application/json",
        ...(auth && token ? { Authorization: `Bearer ${token}` } : {})
      },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data)
        } else {
          const body = response.data || {}
          const error = new Error(body.message || `请求失败（${response.statusCode}）`)
          error.code = body.code || "HTTP_ERROR"
          reject(error)
        }
      },
      fail(error) {
        reject(new Error(error.errMsg || "网络连接失败，请稍后重试"))
      }
    })
  })
}

async function payOrder(orderNo, method) {
  const payment = await request(`/orders/${orderNo}/payments`, {
    method: "POST", data: { method: method.toLowerCase() }
  })
  if (method === "WECHAT") {
    if (!config.development) throw new Error("正式微信支付适配器尚未配置")
    await request(`/payments/${payment.payment_no}/mock-confirm`, { method: "POST" })
  }
  return request(`/orders/${orderNo}`)
}

function showError(error) {
  wx.showToast({ title: (error.message || "操作失败").slice(0, 40), icon: "none", duration: 3000 })
}

module.exports = { request, payOrder, showError }
