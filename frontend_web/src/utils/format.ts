export function formatMoney(cents: number): string {
  const value = Number.isInteger(cents) ? cents : 0
  const sign = value < 0 ? "-" : ""
  const absolute = Math.abs(value)
  return `${sign}${Math.trunc(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`
}

export function parseYuanToCents(value: string | number): number | null {
  const normalized = String(value).trim()
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) return null
  const [yuan, fraction = ""] = normalized.split(".")
  const cents = Number(yuan) * 100 + Number(fraction.padEnd(2, "0"))
  return Number.isSafeInteger(cents) ? cents : null
}

const statuses: Record<string, string> = {
  FREE: "空闲", ACTIVE: "使用中", IN_USE: "使用中", PENDING_CLEANING: "待清洁",
  CLEANING: "清洁中", COMPLETED: "已完成", MAINTENANCE: "维护中", PAID: "已支付",
  PENDING: "待处理", SUCCESS: "成功", FAILED: "失败", UNKNOWN: "结果未知",
  QUEUED: "待接单", ACCEPTED: "已接单", PREPARING: "制作中", DELIVERED: "已送达",
  EXCEPTION: "人工异常", CONFLICT: "占用冲突", BOUND: "已绑定", ISSUING: "发卡中",
  RESERVED: "已预占", AVAILABLE: "可用", QUARANTINED: "隔离待处理", RETURNED: "已归还",
  CLEARED: "已清卡", CLEAR_FAILED: "清卡失败", REFUND_PENDING: "退款处理中",
}

export function statusText(status: string): string {
  return statuses[status] ?? status
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
}
