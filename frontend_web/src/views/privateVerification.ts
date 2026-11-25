import { computed, reactive, watch } from "vue"
import { normalizeCode, type TicketOrderLookup } from "./ticketVerification"

export interface PrivateResult { room_number: string; room_use_id?: string; status?: string; actual_end_at?: string | null; already_verified?: boolean }
export function createPrivateVerification(transport: { lookup(code: string): Promise<TicketOrderLookup>; verify(payload: { code: string; request_id: string; reason: string }): Promise<PrivateResult> }, makeId: () => string = () => crypto.randomUUID()) {
  const state = reactive({ code: "", reason: "私汤订单前台核验并分房", selected: false, busy: false, lookupBusy: false,
    error: "", notice: "", order: null as TicketOrderLookup | null, result: null as PrivateResult | null, loadedCode: "" })
  let generation = 0, pending: { signature: string; id: string } | null = null
  const eligible = computed(() => state.order?.order_type === "PRIVATE" && state.order.status === "PAID"
    && state.order.private_booking?.booking_status === "CONFIRMED" && state.order.private_booking.voucher_status === "UNUSED"
    && !["PENDING", "APPROVED"].includes(state.order.refund_application?.status || ""))
  const canConfirm = computed(() => eligible.value && state.selected && !state.busy && !state.lookupBusy && !!state.loadedCode && normalizeCode(state.code) === state.loadedCode)
  const stop = watch(() => state.code, () => { generation++; state.order = null; state.selected = false; state.loadedCode = ""; state.lookupBusy = false; pending = null }, { flush: "sync" })
  function dispose() { generation++; stop() }
  async function lookup() {
    const code = normalizeCode(state.code), current = ++generation
    state.order = null; state.selected = false; state.loadedCode = ""; state.error = ""; state.notice = ""
    if (!code) return
    state.lookupBusy = true
    try {
      const order = await transport.lookup(code)
      if (generation !== current) return
      state.order = order; state.loadedCode = code
      if (order.order_type !== "PRIVATE") state.error = "该订单不是私汤订单，请到票券核验页面查询"
    } catch (error) { if (generation === current) state.error = error instanceof Error ? error.message : "订单查询失败" }
    finally { if (generation === current) state.lookupBusy = false }
  }
  async function confirm() {
    if (!canConfirm.value || !state.order) return
    const reason = state.reason.trim()
    if (!reason) { state.error = "请填写核验原因"; return }
    const code = state.order.order_no, signature = JSON.stringify([code, reason]), current = generation
    if (pending?.signature !== signature) pending = { signature, id: makeId() }
    state.busy = true; state.error = ""; state.notice = ""; state.result = null
    try {
      const result = await transport.verify({ code, request_id: pending.id, reason })
      if (generation !== current) return
      pending = null; state.code = ""; state.result = result; state.notice = "核验成功，已记录使用开始时间"
    } catch (error) {
      if (generation !== current) return
      const status = (error as { status?: number })?.status
      if (status && status >= 400 && status < 500) { pending = null; await lookup() }
      state.error = error instanceof Error ? error.message : "核验失败，请重新查询确认"
    } finally { state.busy = false }
  }
  return { state, eligible, canConfirm, lookup, confirm, dispose }
}
