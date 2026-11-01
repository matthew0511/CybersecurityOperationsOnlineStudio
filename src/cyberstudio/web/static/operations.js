'use strict';
const OPS={tab:'Overview',state:null,groups:{
 'Validation & evidence':['op_check','op_evidence','control','test_plan','control_test'],
 'Business impact':['op_link','asset','bia'],
 'Access reviews':['op_campaign','op_access'],
 'Exceptions & changes':['exception','op_change','op_change_result'],
 'Vulnerabilities':['op_vulnerability'],
 'Data governance':['op_processing','evidence_policy'],
 'Acquisitions':['op_acquisition','op_milestone'],
 'Recovery exercises':['op_recovery','runbook','restore_check'],
 'Workflow builder':['op_workflow'],
 'Investment planning':['op_investment'],
 'PQC readiness':['op_crypto']
}};
OPS.run=async record=>{
 try{
  if(record.kind==='op_campaign')return P.form('Import access inventory',{accounts:P.basic('Accounts JSON array: account, system, privileged, last_seen','textarea',true)},{},async body=>{let accounts;try{accounts=JSON.parse(body.accounts);}catch{throw Error('Enter a valid JSON array.');}const result=await P.send('/operations/'+record.id+'/run',{version:record.version,accounts});P.note(result.created+' account reviews created; repeated accounts skipped.');P.choices.clear();OPS.render();},'Maximum 1,000 accounts. Import synthetic or approved account metadata; never passwords. The assigned campaign reviewer must import and decide.');
  const result=await P.send('/operations/'+record.id+'/run',{version:record.version});const box=node('div');box.append(structured(result));P.dialog('Operations action result',box);P.choices.clear();OPS.render();
 }catch(e){P.note(e.message,true);}
};
const opsPreviousShow=P.showRecord;P.showRecord=async row=>{
 await opsPreviousShow(row);
 const record=(await P.get('/record/'+encodeURIComponent(row.id))).record;
 const dialog=[...document.querySelectorAll('dialog.pl-dialog')].at(-1);
 if(dialog&&['op_check','op_campaign','op_acquisition'].includes(record.kind))dialog.querySelector('.pl-actions').prepend(button(record.kind==='op_check'?'Run validation now':record.kind==='op_campaign'?'Import account inventory':'Create Day 1/30/60/90 milestones',()=>OPS.run(record),'secondary'));
 if(dialog&&record.kind==='asset')dialog.querySelector('.pl-actions').prepend(button('Inspect business impact',async()=>{try{const result=await P.get('/operations/impact/'+encodeURIComponent(record.id)),box=node('div');box.append(node('p',result.note));P.table(box,result.affected_assets,['title','type']);for(const link of result.relationships)box.append(button(link.title,()=>P.showRecord(link),'secondary'));P.dialog('Recorded downstream impact',box);}catch(e){P.note(e.message,true);}},'secondary'));
};
OPS.registers=async box=>{
 const allowed=OPS.groups[OPS.tab];if(!allowed.includes(P.kind))P.kind=allowed[0];await P.modules(box);
 const select=box.querySelector('select[aria-label="Program module"]');select.setAttribute('aria-label','Operations register');for(const option of [...select.options])if(!allowed.includes(option.value))option.remove();select.value=P.kind;
 const guide=node('details'),summary=node('summary','How to use this workspace');guide.append(summary,node('p',OPS.help[OPS.tab]||'Create linked records, assign an owner and due date, and retain evidence. Open a record for status changes, history and available actions.'),P.link('Detailed technical documentation','/documentation#operations'));box.prepend(guide);
};
OPS.help={
 'Validation & evidence':'Create a control and link reviewed evidence, then create an evidence, integration freshness or completed-test check. Activate checks for scheduled execution. Missing or stale sources display Unknown. Open a check to run it now.',
 'Access reviews':'Create a campaign with an enabled reviewer and review deadline. Open it to import accounts as a JSON array. The assigned reviewer records retain/revoke decisions. A revoke review needs evidence of removal before completion.',
 'Exceptions & changes':'Exceptions require justification, compensating controls, an independent reviewer and expiration. Change reviews additionally need security impact, testing and rollback. Submit, obtain independent approval, then activate.',
 'Acquisitions':'Create the acquired office and acquisition record. Open the acquisition to generate due-diligence and Day 1/30/60/90 milestones with dates relative to closing. Existing milestones prevent duplicate generation.',
 'Workflow builder':'The owner defines a trigger, internal task or in-app notification, assignee, and independent reviewer. Submit, independently approve with reauthentication, then activate. Runs are deduplicated per rule version, target and UTC day. No external messages or system changes are performed.',
 'Recovery exercises':'Link a BIA and record exercise start, application acceptance and recovered-data timestamps. Verified evidence and application checks are required for a passing result. Actual recovery time and data loss are compared with the selected BIA objectives.',
 'PQC readiness':'Inventory protocols, libraries, certificates and cryptographic prerequisites. Record vendor readiness evidence and migration milestones. The combined planning horizon is an input for prioritization; it does not predict a quantum computer arrival date.'
};
OPS.overview=async box=>{
 const s=OPS.state;box.append(node('p',s.note),button('Open My Work Today',()=>{AS.tab='My Work Today';OPS.tab='Assurance & productivity';OPS.render();},'secondary'));const cards=node('div',undefined,'cards');for(const [name,value] of [['Failed checks',s.checks.filter(r=>r.outcome==='fail').length],['Unknown checks',s.checks.filter(r=>r.outcome==='unknown').length],['Evidence follow-ups',s.evidence_due.length],['Expired exceptions',s.exceptions.filter(r=>r.effective_status==='expired').length]])cards.append(metric(name,value,'Selected organization','shield'));box.append(cards);
 box.append(button('Freeze operational report',()=>P.form('Operational assurance report',{format:{label:'Format',type:'select',options:['pdf','xlsx','pptx'],required:true}},{format:'pdf'},async values=>{const result=await P.send('/editions',{...values,template:'operations'}),content=node('div');content.append(P.link('Download frozen report',result.download_url));P.dialog('Operational report',content);}), 'secondary'));
 box.append(node('h3','Validation results'));P.table(box,s.checks,['title','outcome','reason','observed_at'],P.showRecord);
 box.append(node('h3','Evidence requiring attention'));P.table(box,s.evidence_due,['title','owner','review_on'],P.showRecord);
 box.append(node('h3','Effective exception lifecycle'));P.table(box,s.exceptions,['title','owner','effective_status','expires_on'],P.showRecord);
 box.append(node('h3','Access campaign progress'));P.table(box,s.campaigns||[],['title','total','completed','privileged','inactive','review_on'],P.showRecord);
 box.append(node('h3','Investment scenarios'));P.table(box,s.scenarios,['scenario','total_cost','proposals']);
 const guide=node('details');guide.append(node('summary','All 15 capabilities'));for(const c of s.capabilities)guide.append(node('p',c.number+'. '+c.title));box.append(guide);
};
OPS.render=async()=>{
 $('page-title').textContent='Operations workbench';$('page-description').textContent='Validate controls, coordinate reviews and measure operational readiness.';$('section-label').textContent='Operations workbench';$('cards').replaceChildren();$('insights').replaceChildren();$('insights').hidden=true;$('records-panel').hidden=true;$('special').hidden=false;$('open-action').hidden=true;const host=$('special');host.replaceChildren();
 try{
  if(!org){host.append(node('p','Choose an organization to manage operations.'));return;}
  P.catalog=await api('/api/platform/catalog');OPS.state=await P.get('/operations/overview');const tabs=node('div',undefined,'pl-tabs');tabs.setAttribute('aria-label','Operations secondary pages');
  const titles=['Overview','Assurance & productivity',...Object.keys(OPS.groups),'Customer & auditor portal',...(P.catalog.role==='owner'?['Integration health']:[]),'Automation history'];if(!titles.includes(OPS.tab))OPS.tab='Overview';
  if(OPS.navigation)OPS.navigation(host,P.catalog.role);else{for(const title of titles){const b=button(title,()=>{OPS.tab=title;OPS.render();},OPS.tab===title?'':'secondary');b.setAttribute('aria-pressed',String(OPS.tab===title));tabs.append(b);}host.append(tabs);}const box=P.box(OPS.tab);host.append(box);
  if(OPS.tab==='Overview')await OPS.overview(box);
  else if(OPS.tab==='Assurance & productivity')await AS.render(box);
  else if(OPS.groups[OPS.tab])await OPS.registers(box);
  else if(OPS.tab==='Integration health'){
   box.append(node('p','Authentication tests, pulls and source coverage are separate. Open App integrations to test credentials, review staged data or retry a pull.'));
   P.table(box,OPS.state.integrations,['title','permission_requirements','authentication','enabled','last_success_at','age_hours','latest_job','partial','staged','promoted']);box.append(button('Manage integrations',()=>navigate('integrations'),'secondary'));
  }else if(OPS.tab==='Customer & auditor portal'){
   box.append(node('p','Selected records and evidence only. Invitations expire and can be revoked. Share approved content after reviewing each selected record.'));
   if(P.catalog.role==='owner'){const label=node('label','Program register to share'),select=node('select');for(const [kind,definition] of Object.entries(P.catalog.modules))select.append(new Option(definition.title,kind));select.value=P.kind;select.onchange=()=>{P.kind=select.value;OPS.render();};label.append(select);box.append(label);await P.rooms(box,true);}else box.append(node('p','Ask the installation owner to create a scoped invitation.'));
  }else{for(const run of OPS.state.automation_runs){const card=P.box(run.action,new Date(run.recorded_at).toLocaleString()+' · '+run.actor);card.append(structured(run.snapshot));box.append(card);}if(!OPS.state.automation_runs.length)box.append(node('p','No automation runs recorded.'));}
 }catch(e){host.replaceChildren(P.box('Operations could not be loaded',e.message),button('Retry',OPS.render,'secondary'));}
};
const opsPreviousRender=P.render;P.render=(...args)=>page==='operations'?OPS.render():opsPreviousRender(...args);
const opsPreviousLoad=load;load=(...args)=>page==='operations'?OPS.render():opsPreviousLoad(...args);
pages.operations=['Operations workbench','',[''],[],'layers'];const opsNav=button('Operations workbench',()=>navigate('operations'),'','layers');opsNav.dataset.page='operations';opsNav.title='Operations workbench';opsNav.querySelector('span').className='nav-text';$('navigation').append(opsNav);
