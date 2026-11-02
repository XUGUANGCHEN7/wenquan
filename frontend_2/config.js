// 真机预览必须使用运行后端的电脑局域网 IP，手机不能访问 127.0.0.1。
// 电脑 Wi-Fi/IP 变化时，同步修改 lanApiBase 并重启后端。
const lanApiBase = "http://192.168.43.235:8000/api/v1"
function runningInDevtools() {
  try {
    if (typeof wx === "undefined") return false
    if (wx.getDeviceInfo) return wx.getDeviceInfo().platform === "devtools"
    return Boolean(wx.getSystemInfoSync) && wx.getSystemInfoSync().platform === "devtools"
  } catch (error) {
    return false
  }
}

module.exports = {
  apiBase: runningInDevtools() ? "http://127.0.0.1:8000/api/v1" : lanApiBase,
  development: true,
  devRoomCode: "ROOM-01"
}
