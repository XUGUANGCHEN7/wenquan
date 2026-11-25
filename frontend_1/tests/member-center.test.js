import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import * as vue from 'vue'
import * as money from '../src/utils/money.js'
import * as orders from '../src/pages/orders/model.js'
import * as navigation from '../src/pages/orders/navigation.js'

function mount(page, api, session) {
  let show, load
  const { descriptor } = parse(fs.readFileSync(new URL(`../src/pages/${page}/index.vue`, import.meta.url), 'utf8'))
  const code = transformSync(compileScript(descriptor,{ id:'member' }).content,{ loader:'js',format:'cjs' }).code
  const module = { exports:{} }
  new Function('require','module','exports',code)(name => {
    if (name === 'vue') return vue
    if (name === '@dcloudio/uni-app') return { onShow:f => { show=f },onLoad:f => { load=f },onHide(){},onUnload(){} }
    if (name.endsWith('/api') || name.endsWith('/api.js')) return api
    if (name.endsWith('/session.js')) return session
    if (name.endsWith('/model.js')) return orders
    if (name.endsWith('/navigation.js')) return navigation
    if (name.endsWith('/examples.js')) return { getOrderExamples:()=>[] }
    if (name.endsWith('/money')) return money
    if (name.endsWith('/config')) return { development:true }
    return {}
  },module,module.exports)
  return { state:module.exports.default.setup({}, { expose(){} }),show:()=>show(),load:options=>load(options) }
}
function env() {
  const storage = new Map(), moves=[], calls=[]; let token='real-token'
  globalThis.uni = { setStorageSync:(k,v)=>storage.set(k,v),getStorageSync:k=>storage.get(k),removeStorageSync:k=>storage.delete(k),navigateTo:o=>moves.push(o.url),switchTab:o=>moves.push(o.url),setNavigationBarTitle(){},showToast(){},showModal:o=>o.success({confirm:true}) }
  const session={getToken:()=>token,clearSession:()=>{token=''},saveSession(){},redirectToLogin:url=>moves.push('login:'+url)}
  const api={request:async(path)=>{calls.push(path); if(path==='/members/me')return{nickname:'真实昵称',phone_masked:'138****1234'}; if(path==='/wallet/balance')return{available_cents:7400}; return{}},showError(){}}
  return { storage,moves,calls,session,api,setToken:v=>{token=v} }
}
test('member center uses real profile and wallet; guest requests no protected data and hides balance',async()=>{
  const e=env(),p=mount('mine',e.api,e.session); await p.show()
  assert.equal(p.state.profile.value.nickname,'真实昵称'); assert.equal(p.state.balance.value,'74.00')
  e.setToken('');e.calls.length=0;await p.show()
  assert.equal(p.state.loggedIn.value,false);assert.equal(p.state.balance.value,null);assert.equal(e.calls.length,0)
})
test('balance failure never displays a fake zero and expired auth removes member display',async()=>{
  const e=env(); e.api.request=async path=>{if(path==='/wallet/balance')throw Error('网络中断');return{nickname:'真实昵称'}}
  const p=mount('mine',e.api,e.session);await p.show();assert.equal(p.state.balance.value,null);assert.match(p.state.balanceError.value,/网络中断/)
  e.api.request=async()=>{e.setToken('');throw Error('expired')};await p.show();assert.equal(p.state.loggedIn.value,false)
})
test('member entries retain category, wallet details and login return destinations',async()=>{
  const e=env(),p=mount('mine',e.api,e.session)
  p.state.goOrders('PRIVATE');assert.equal(e.storage.get('member_order_filter'),'PRIVATE');assert.equal(e.moves.pop(),'/pages/orders/index')
  p.state.goWallet(true);assert.equal(e.moves.pop(),'/pages/wallet/transactions')
  e.setToken('');p.state.goService('security');assert.match(e.moves.pop(),/returnTo=.*member-service/)
  p.state.goService('notice');assert.equal(e.moves.pop(),'/pages/member-service/index?section=notice')
})
test('logout requires confirmation; failure keeps session and success clears it',async()=>{
  const e=env(),p=mount('member-service',e.api,e.session);await p.load({section:'security'})
  uni.showModal=o=>o.success({confirm:false});await p.state.logout();assert.equal(e.calls.includes('/auth/logout'),false)
  uni.showModal=o=>o.success({confirm:true});e.api.request=async()=>{throw Error('offline')};await p.state.logout();assert.equal(e.session.getToken(),'real-token')
  e.api.request=async()=>({});await p.state.logout();assert.equal(e.session.getToken(),'');assert.equal(e.moves.pop(),'/pages/mine/index')
})
test('order entry consumes category and refund/card filters without changing status meanings',async()=>{
  const e=env();e.api.request=async path=>path==='/orders'?[
    {id:'t',order_no:'T',order_type:'TICKET',status:'PAID'},
    {id:'p',order_no:'P',order_type:'PRIVATE',business_id:'B',status:'PAID'},
    {id:'r',order_no:'R',order_type:'RECHARGE',status:'REFUNDED'},
  ]:path.startsWith('/tickets/')?{tickets:[{status:'UNUSED',ticket_no:'TV'}]}:{voucher_status:'USED',booking_status:'COMPLETED'}
  const p=mount('orders',e.api,e.session)
  e.storage.set('member_order_filter','PRIVATE');await p.show();assert.equal(p.state.cards.value.length,1);assert.equal(p.state.cards.value[0].order_no,'P')
  e.storage.set('member_order_filter','REFUND');await p.show();assert.deepEqual(p.state.cards.value.map(o=>o.order_no),['R'])
  e.storage.set('member_order_filter','VOUCHERS');await p.show();assert.deepEqual(p.state.cards.value.map(o=>o.order_no),['T'])
  p.state.selectCategory('ALL');assert.equal(p.state.cards.value.length,3)
})
