// 真机预览使用运行后端的电脑局域网 IP；模拟器自动使用本机回环地址。
const lanApiBase = "http://192.168.43.235:8000/api/v1"

function runningInDevtools() {
  try {
    if (typeof uni === "undefined") return false
    if (uni.getDeviceInfo) return uni.getDeviceInfo().platform === "devtools"
    return Boolean(uni.getSystemInfoSync) && uni.getSystemInfoSync().platform === "devtools"
  } catch (error) {
    return false
  }
}

export default {
  apiBase: runningInDevtools() ? "http://127.0.0.1:8000/api/v1" : lanApiBase,
  development: true,
  devToken: "dev-member",
  memberId: "member-demo",
}
