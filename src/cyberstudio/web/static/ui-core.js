/* Pure presentation calculations, shared by the browser and Node tests. */
(function(root){
  'use strict';
  const labels={org:'Organization',eid:'Evidence',evidence_id:'Evidence',vid:'Vulnerability',tid:'Remediation task',ident:'Record',key:'Framework',framework_key:'Framework',control_code:'Control reference',new_status:'New status',baa_applicability:'BAA applicability',cvss:'CVSS score',sha256:'SHA-256',id:'Record identifier',as_of:'As of',verified_percent:'Verified tracked items',assessed_items:'Applicable tracked items'};
  function label(key){return labels[key]||String(key).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase()).replace(/\bId\b/g,'ID');}
  function daysUntil(value,today=new Date()){
    if(!/^\d{4}-\d{2}-\d{2}/.test(String(value||'')))return null;
    const date=new Date(String(value).slice(0,10)+'T00:00:00Z');
    const current=Date.UTC(today.getFullYear(),today.getMonth(),today.getDate());
    return Number.isFinite(date.getTime())?Math.round((date.getTime()-current)/86400000):null;
  }
  function closed(row){return ['done','completed','closed','mitigated','cancelled','false_positive','retired','verified','not_applicable'].includes(row.status);}
  function statusOf(row){return row.effective_status||row.review_state||row.review_status||row.status||row.review_state||row.severity||row.band||'';}
  function tone(value){const s=String(value||'').toLowerCase();if(['critical','high','fail','failed','rejected','overdue','expired','gap'].includes(s))return'danger';if(['blocked','partial','moderate','medium','pending','planned','missing','in_review','review','not_started','not_assessed','needs_remediation'].includes(s))return'warning';if(['done','completed','verified','pass','implemented','approved','reviewed','mitigated'].includes(s))return'success';return'neutral';}
  function aging(tasks,today=new Date()){
    const bins=[{label:'On time',value:0,tone:'teal'},{label:'1–7 days overdue',value:0,tone:'amber'},{label:'8–30 days overdue',value:0,tone:'orange'},{label:'31+ days overdue',value:0,tone:'red'},{label:'No due date',value:0,tone:'muted'}];
    for(const task of tasks.filter(t=>!closed(t))){const days=daysUntil(task.due_date,today);bins[days===null?4:days>=0?0:days>=-7?1:days>=-30?2:3].value++;}return bins;
  }
  function frameworkProgress(framework,items){const scoped=items.filter(i=>i.framework_key===framework.key),applicable=scoped.filter(i=>i.status!=='not_applicable'),verified=applicable.filter(i=>i.status==='verified').length,implemented=applicable.filter(i=>['implemented','verified'].includes(i.status)).length;return{total:scoped.length,applicable:applicable.length,verified,implemented,percent:applicable.length?Math.round(100*verified/applicable.length):0};}
  function selectRows(rows,state){const query=(state.query||'').trim().toLowerCase();let result=rows.filter(row=>(!query||Object.values(row).some(v=>typeof v!=='object'&&String(v??'').toLowerCase().includes(query)))&&(!state.status||statusOf(row)===state.status));if(state.sort){const collator=new Intl.Collator(undefined,{numeric:true,sensitivity:'base'});result=result.slice().sort((a,b)=>{const av=a[state.sort],bv=b[state.sort];if(av===null||av===undefined||av==='')return bv===null||bv===undefined||bv===''?0:1;if(bv===null||bv===undefined||bv==='')return-1;const order=typeof av==='number'&&typeof bv==='number'?av-bv:collator.compare(String(av),String(bv));return state.direction==='desc'?-order:order;});}return result;}
  function monthlyNewRisks(risks,today=new Date()){const months=Array.from({length:6},(_,i)=>{const d=new Date(today.getFullYear(),today.getMonth()-5+i,1);return{key:d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0'),label:d.toLocaleDateString(undefined,{month:'short'}),value:0};});for(const risk of risks){const m=months.find(v=>String(risk.created_at||'').startsWith(v.key));if(m)m.value++;}return months;}
  const api={label,daysUntil,closed,statusOf,tone,aging,frameworkProgress,selectRows,monthlyNewRisks};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.StudioUI=api;
})(typeof window!=='undefined'?window:globalThis);
