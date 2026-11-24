import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import * as vue from 'vue'
import * as money from '../src/utils/money.js'
function page(request) {
 let show,hide,token='real-member'
 const { descriptor } = parse(fs.readFileSync(new URL('../src/pages/wallet/transactions.vue',import.meta.url),'utf8'))
 const code=transformSync(compileScript(descriptor,{id:'transactions'}).content,{loader:'js',format:'cjs'}).code
 const module={exports:{}}
 new Function('require','module','exports',code)(name=>name==='vue'?vue:name==='@dcloudio/uni-app'?{onShow:fn=>show=fn,onHide:fn=>hide=fn}:name.endsWith('/api')?{request}:name.endsWith('/session.js')?{getToken:()=>token,redirectToLogin(){}}:money,module,module.exports)
 return {state:module.exports.default.setup({}, {expose(){}}),show:()=>show(),hide:()=>hide(),setToken:value=>token=value}
}
test('transaction page uses real ledger deltas, resulting balance and Beijing date',async()=>{
 const p=page(async path=>{assert.equal(path,'/wallet/entries');return [{reference:'RC-REAL',entry_type:'RECHARGE',delta_cents:10000,balance_after_cents:10000,created_at:'2026-11-16T01:00:00'}, {reference:'TK-REAL',entry_type:'CONSUME',delta_cents:-2600,balance_after_cents:7400,created_at:'2026-11-16T02:00:00'}]})
 await p.show();assert.equal(p.state.entries.value[0].delta,'+100.00');assert.equal(p.state.entries.value[1].delta,'-26.00');assert.equal(p.state.entries.value[1].after,'74.00');assert.equal(p.state.entries.value[0].time,'2026-11-16 09:00:00')
})
test('transaction failure supports retry and guest makes no protected query',async()=>{
 let count=0;const p=page(async()=>{if(++count===1)throw Error('offline');return []})
 await p.show();assert.equal(p.state.error.value,'offline');await p.show();assert.equal(p.state.error.value,'');assert.deepEqual(p.state.entries.value,[])
 p.setToken('');await p.show();assert.equal(count,2);assert.equal(p.state.guest.value,true)
})
test('late ledger response cannot reveal records after the page is hidden',async()=>{
 let finish;const p=page(()=>new Promise(resolve=>finish=resolve));const loading=p.show();p.hide();finish([{reference:'old-member',delta_cents:100,balance_after_cents:100}]);await loading;assert.deepEqual(p.state.entries.value,[])
})
