const test=require('node:test'),assert=require('node:assert/strict');
const {parseCSV,accounts}=require('../src/cyberstudio/web/static/polish-core.js');
test('CSV preserves quoted commas, escaped quotes, BOM, CRLF and embedded newlines',()=>{
 const csv=parseCSV('\uFEFFAccount,System,Notes\r\n"alice, ops",Clinic,"a ""quote""\nand a line"\r\n');assert.deepEqual(csv.headers,['Account','System','Notes']);assert.deepEqual(csv.rows,[['alice, ops','Clinic','a "quote"\nand a line']]);
});
test('inventory mapping uses explicit booleans and leaves unknown dates absent',()=>{
 const csv=parseCSV('Username,Application,Elevated,Last use\nalice,Clinic,yes,2026-01-01\nbob,Directory,0,');assert.deepEqual(accounts(csv,{account:0,system:1,privileged:2,last_seen:3}),[{account:'alice',system:'Clinic',privileged:true,last_seen:'2026-01-01'},{account:'bob',system:'Directory',privileged:false}]);assert.equal(accounts(csv,{account:0,system:1})[0].privileged,false);
});
test('malformed, ragged, duplicate-header and empty CSV inputs are rejected',()=>{
 for(const text of ['a,b\n"unclosed,b','a,b\nx,y,z','a,A\nx,y','a,\nx,y','a,b\n"x"junk,y','a,b',''])assert.throws(()=>parseCSV(text));
});
test('mapping rejects repeated columns, invalid dates, unknown booleans and blank required values',()=>{
 for(const [text,mapping] of [['a,b\nx,y',{account:0,system:0}],['a,b,c\nx,y,perhaps',{account:0,system:1,privileged:2}],['a,b,c\nx,y,2026-02-30',{account:0,system:1,last_seen:2}],['a,b\n,y',{account:0,system:1}]])assert.throws(()=>accounts(parseCSV(text),mapping));
});
test('file and row limits are enforced before import',()=>{
 assert.throws(()=>parseCSV('x'.repeat(2*1024*1024+1)));assert.throws(()=>parseCSV('a,b\n'+Array.from({length:1001},()=> 'x,y').join('\n')));assert.equal(parseCSV('a,b\n'+Array.from({length:1000},()=> 'x,y').join('\n')).rows.length,1000);
});
test('HTML and SQL-shaped account names remain literal data',()=>{
 const csv=parseCSV('account,system\n<b>alice</b>,Clinic\nDROP TABLE users;,Directory');assert.equal(accounts(csv,{account:0,system:1})[0].account,'<b>alice</b>');assert.equal(accounts(csv,{account:0,system:1})[1].account,'DROP TABLE users;');
});
