import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import * as vue from 'vue'
import * as money from '../src/utils/money.js'
import * as navigation from '../src/pages/orders/navigation.js'

const slots = [0,1,2].map(i => ({ slot_index: i, start: ['10:00','12:30','15:00'][i], end: ['12:00','14:30','17:00'][i], available: 2 }))
const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return { promise, resolve } }
function page(overrides = {}) {
  let load
  const posts = [], pays = [], navigated = [], errors = []
  globalThis.uni = { showToast() {}, showModal: o => o.success?.(), navigateTo: o => navigated.push(o.url) }
  const defaults = async (path, options) => {
    if (path === '/rooms/dates') return { dates: [{ value: '2026-11-18', available: false }, { value: '2026-11-19', available: true }, { value: '2026-11-20', available: true }] }
    if (path.startsWith('/rooms/slots')) return { slots: structuredClone(slots), unit_price_cents: 12300 }
    if (path.startsWith('/rooms/availability')) return { available: 2, amount_cents: path.split('slots=')[1].split(',').length * 12300 }
    posts.push(options.data); return { id: 'REAL-ID', order_no: 'REAL-NO', amount_cents: 24600 }
  }
  const api = { request: overrides.request || defaults, payOrder: async (...args) => { pays.push(args); return overrides.pay ? overrides.pay(...args) : { status: 'PAID' } }, showError: e => errors.push(e) }
  const { descriptor } = parse(fs.readFileSync(new URL('../src/pages/private-room/index.vue', import.meta.url), 'utf8'))
  const code = transformSync(compileScript(descriptor, { id: 'private' }).content, { loader: 'js', format: 'cjs' }).code
  const module = { exports: {} }
  new Function('require','module','exports',code)(name => name === 'vue' ? vue : name === '@dcloudio/uni-app' ? { onLoad: f => { load = f } } : name.endsWith('/api') ? api : name.endsWith('/navigation') ? navigation : money, module, module.exports)
  return { state: module.exports.default.setup({}, { expose() {} }), load: () => load(), posts, pays, navigated, errors }
}
test('private booking selects server date, quotes continuous slots, and submits real indices and ID', async () => {
  const p = page(); await p.load(); const s = p.state
  assert.equal(s.selectedDate.value, '2026-11-19'); assert.equal(s.canSubmit.value, false)
  await s.selectSlot(0); await s.selectSlot(2)
  assert.deepEqual(s.selected.value, [0,1,2]); assert.equal(s.total.value, '369.00')
  await s.selectSlot(1); await s.selectSlot(2)
  s.selectPayment('BALANCE'); await s.submit()
  assert.deepEqual(p.posts[0].slot_indices, [1,2]); assert.equal(p.posts[0].visit_date, '2026-11-19')
  assert.equal('amount_cents' in p.posts[0], false)
  assert.deepEqual(p.pays[0], ['REAL-NO','BALANCE']); assert.match(p.navigated[0], /id=REAL-ID/)
})
test('sold-out gaps are rejected and date changes clear the previous selection', async () => {
  const p = page(); await p.load(); const s = p.state
  s.slots.value[1].available = 0; await s.selectSlot(0); await s.selectSlot(2)
  assert.deepEqual(s.selected.value, [0]); await s.selectDate(2)
  assert.deepEqual(s.selected.value, []); assert.equal(s.quote.value, null)
})
test('late slot response cannot overwrite the selected date', async () => {
  const older = deferred(), newer = deferred(); let count = 0
  const p = page({ request: path => path === '/rooms/dates' ? Promise.resolve({ dates: [{ value:'2026-11-19', available:true },{ value:'2026-11-20', available:true }] }) : ++count === 1 ? older.promise : newer.promise })
  const loading = p.load(); await Promise.resolve(); const switching = p.state.selectDate(1)
  newer.resolve({ slots: [{...slots[0], start:'NEW'}], unit_price_cents: 200 }); await switching
  older.resolve({ slots: [{...slots[0], start:'OLD'}], unit_price_cents: 100 }); await loading
  assert.equal(p.state.slots.value[0].start, 'NEW')
})
test('payment failure retries the same order and concurrent taps do not create another booking', async () => {
  const pending = deferred(); let attempt = 0
  const p = page({ pay: async () => { if (++attempt === 1) { await pending.promise; throw new Error('pay failed') } return { status:'PAID' } } })
  await p.load(); await p.state.selectSlot(0)
  const first = p.state.submit(); await Promise.resolve(); await p.state.submit()
  assert.equal(p.posts.length, 1); pending.resolve(); await first; await p.state.submit()
  assert.equal(p.posts.length, 1); assert.equal(p.pays.length, 2)
})
test('zero continuous inventory prevents submit even when individual slots have rooms', async () => {
  const p = page(); await p.load(); await p.state.selectSlot(0)
  p.state.quote.value = { available:0, amount_cents:0 }
  await p.state.submit(); assert.equal(p.posts.length, 0)
})
