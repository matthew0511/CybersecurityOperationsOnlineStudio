const {test}=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../src/cyberstudio/web/static/ui-core.js');
const today=new Date(2026,9,31);
test('aging excludes completed work and keeps missing dates distinct',()=>{
 const bins=ui.aging([{status:'open',due_date:'2026-10-30'},{status:'blocked',due_date:'2026-10-01'},{status:'open'},{status:'done',due_date:'2020-01-01'},{status:'open',due_date:'2026-10-31'}],today);
 assert.deepEqual(bins.map(b=>b.value),[1,1,1,0,1]);
 assert.equal(ui.daysUntil('bad',today),null);
});
test('framework progress uses scoped applicable items only',()=>{
 assert.deepEqual(ui.frameworkProgress({key:'a'},[{framework_key:'a',status:'verified'},{framework_key:'a',status:'implemented'},{framework_key:'a',status:'not_applicable'},{framework_key:'b',status:'verified'}]),{total:3,applicable:2,verified:1,implemented:2,percent:50});
 assert.equal(ui.frameworkProgress({key:'empty'},[]).percent,0);
});
test('search and status filters combine; numeric sorting keeps empty values last',()=>{
 const rows=[{title:'Risk 10',score:10,status:'open'},{title:'Risk 2',score:2,status:'open'},{title:'Risk 3',status:'done'},{title:'Risk 4',status:'open'}];
 assert.deepEqual(ui.selectRows(rows,{query:'risk',status:'open',sort:'score',direction:'desc'}).map(r=>r.title),['Risk 10','Risk 2','Risk 4']);
 assert.deepEqual(ui.selectRows(rows,{sort:'title'}).map(r=>r.title),['Risk 2','Risk 3','Risk 4','Risk 10']);
 assert.equal(rows[0].title,'Risk 10');
});
test('monthly risk counts use actual creation dates across year boundaries',()=>{
 const data=ui.monthlyNewRisks([{created_at:'2025-12-01'},{created_at:'2026-01-02'},{created_at:'2025-01-01'},{}],new Date(2026,0,15));
 assert.equal(data.length,6);assert.equal(data[4].key,'2025-12');assert.equal(data[4].value,1);assert.equal(data[5].value,1);
});
