import { computed, reactive, watch } from "vue"

export interface TicketItem { ticket_no: string; category: string; price_cents: number; status: string; can_admit: boolean }
export interface TicketOrderLookup {
  order_no: string; order_type: string; status: string; amount_cents: number
  payment_method: string | null; created_at: string; paid_at: string | null; visit_date?: string
  member: { nickname: string; phone_masked: string } | null; tickets?: TicketItem[]
  refund_application?: { status: string } | null
  day_type?: string | null; valid_until?: string | null; admission_error?: { code: string; message: string } | null
  private_booking?: { booking_id: string; ticket_no: string | null; voucher_status: string | null; booking_status: string; visit_date: string; start_at: string; end_at: string }
}
export interface BatchPayload { order_no: string; ticket_nos: string[]; request_id: string; reason: string }
export interface BatchResult { order_no: string; admitted_count: number; remaining_tickets: number; admitted_at: string; admissions: { ticket_no: string; admission_id: string }[] }
interface Transport { lookup(code: string): Promise<TicketOrderLookup>; admit(payload: BatchPayload): Promise<BatchResult> }

export function normalizeCode(raw: string) {
  const text = raw.trim()
  try {
    const parsed = JSON.parse(text) as Record<string, unknown> | null
    const value = parsed?.order_no ?? parsed?.orderNo ?? parsed?.ticket_no ?? parsed?.ticketNo
    if (typeof value === "string" && value.trim()) return value.trim()
  } catch { /* Scanner may send plain text. */ }
  try {
    const url = new URL(text)
    return url.searchParams.get("order_no") || url.searchParams.get("orderNo") || url.searchParams.get("ticket_no") || text
  } catch { return text }
}

export function createTicketVerification(transport: Transport, makeRequestId: () => string = () => crypto.randomUUID()) {
  const state = reactive({ code: "", reason: "前台人工核对票券与身份", busy: false, lookupBusy: false,
    error: "", notice: "", order: null as TicketOrderLookup | null, loadedCode: "", selected: [] as string[], results: [] as BatchResult[] })
  let generation = 0
  let pending: { signature: string; id: string } | null = null
  const eligibleTickets = computed(() => {
    if (state.order?.order_type !== "TICKET" || state.order.status !== "PAID" || state.order.refund_application?.status === "PENDING") return []
    return (state.order.tickets || []).filter(ticket => ticket.can_admit && ticket.status === "UNUSED")
  })
  const selectedTickets = computed(() => eligibleTickets.value.filter(ticket => state.selected.includes(ticket.ticket_no)))
  const canSubmit = computed(() => !state.busy && !state.lookupBusy && !!state.loadedCode && normalizeCode(state.code) === state.loadedCode
    && selectedTickets.value.length > 0 && selectedTickets.value.length === state.selected.length && new Set(state.selected).size === state.selected.length)

  const dispose = watch(() => state.code, () => {
    generation++
    state.order = null; state.loadedCode = ""; state.selected = []; state.lookupBusy = false
    state.error = ""; state.notice = ""; pending = null
  }, { flush: "sync" })

  async function lookup() {
    const value = normalizeCode(state.code)
    if (!value) return
    const requestGeneration = ++generation
    state.lookupBusy = true; state.error = ""; state.order = null; state.selected = []; state.loadedCode = ""
    try {
      const order = await transport.lookup(value)
      if (requestGeneration !== generation || normalizeCode(state.code) !== value) return
      state.order = order; state.loadedCode = value
      if (order.order_type !== "TICKET") state.error = "该订单不是公共票订单；私汤请到私汤核验页面处理"
    } catch (cause) {
      if (requestGeneration === generation) state.error = cause instanceof Error ? cause.message : "订单查询失败"
    } finally { if (requestGeneration === generation) state.lookupBusy = false }
  }

  function selectAll(value: boolean) { state.selected = value ? eligibleTickets.value.map(ticket => ticket.ticket_no) : [] }

  async function admit() {
    if (!canSubmit.value || !state.order) { state.error = "请先查询订单并勾选可核销票券"; return }
    const orderNo = state.order.order_no
    const sourceCode = state.loadedCode
    const ticketNos = [...state.selected].sort()
    const reason = state.reason.trim()
    if (!reason) { state.error = "请填写核验原因"; return }
    const signature = JSON.stringify([orderNo, ticketNos, reason])
    if (pending?.signature !== signature) pending = { signature, id: makeRequestId() }
    state.busy = true; state.error = ""; state.notice = ""
    try {
      const result = await transport.admit({ order_no: orderNo, ticket_nos: ticketNos, request_id: pending.id, reason })
      pending = null
      state.results.unshift(result)
      if (normalizeCode(state.code) === sourceCode) await lookup()
      state.notice = `订单 ${result.order_no} 核销成功 ${result.admitted_count} 张，剩余未核销 ${result.remaining_tickets} 张`
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "核销请求失败"
      const status = (cause as { status?: number })?.status
      if (status && status >= 400 && status < 500) {
        pending = null
        if (normalizeCode(state.code) === sourceCode) await lookup()
        state.error = `${message}；请核对刷新后的状态并重新勾选。`
      } else state.error = `${message}；结果可能尚未返回，可保持勾选并重试，请勿放行未确认的票券。`
    } finally { state.busy = false }
  }
  return { state, eligibleTickets, selectedTickets, canSubmit, lookup, selectAll, admit, dispose }
}
