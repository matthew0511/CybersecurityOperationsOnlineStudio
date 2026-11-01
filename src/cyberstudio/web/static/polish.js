'use strict';
const UX={categories:{
 Assurance:['Validation & evidence','Business impact','Vulnerabilities','Integration health','Assurance & productivity'],
 Governance:['Access reviews','Exceptions & changes','Data governance','Workflow builder','Customer & auditor portal','Automation history'],
 Resilience:['Acquisitions','Recovery exercises'],Planning:['Investment planning','PQC readiness']
}};
UX.group=key=>/^(title|version_label|method_version)$/.test(key)?'Basics':/owner|approver|reviewer|assignee|due_on|review_on|expires_on|from_user|to_user/.test(key)?'Ownership & review':/evidence|result|retest|verification|calculated|observations|sample|checks/.test(key)?'Evidence & validation':'Scope & implementation';
UX.empty=(target,title,description,action)=>{const state=node('div',undefined,'ux-empty');state.append(icon('layers'),node('h3',title),node('p',description));if(action)state.append(button(action.label,action.run,''));target.append(state);};
UX.status=value=>{
 const label=UI.label(value||'unknown'),state=node('span',label,'badge ux-status');
 const tone=['pass','verified','completed','approved','succeeded','authenticated','ready'].includes(value)?'success':['fail','failed','expired','rejected','dead_letter','test_failed'].includes(value)?'danger':['unknown','not_tested','pending','partial','overdue','not_due'].includes(value)?'warning':'neutral';state.classList.add(tone);return state;
};
P.table=(target,rows,fields,open)=>{
 if(!rows.length){UX.empty(target,'Nothing to display yet','Records will appear here as your team adds and reviews work.');return;}
 const wrap=node('div',undefined,'table-wrap ux-table-wrap'),table=node('table',undefined,'ux-table');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',(target.querySelector('h3,h2')?.textContent||'Records')+' table');
 const thead=node('thead'),head=node('tr');for(const key of fields){const th=node('th',UI.label(key));th.scope='col';head.append(th);}thead.append(head);table.append(thead);const body=node('tbody');
 for(const row of rows){const tr=node('tr');for(const [i,key] of fields.entries()){
  const td=node('td'),value=key==='status'?(row.effective_status||row[key]):row[key];if(i===0&&open)td.append(button(display(value),()=>open(row),'small-link'));
  else if(['status','effective_status','outcome','authentication','latest_job'].includes(key))td.append(UX.status(value));
  else if(typeof value==='number'){td.className='ux-number';td.textContent=new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(value);}
  else if(typeof value==='boolean')td.textContent=value?'Yes':'No';else if(/(_at|_on|date)$/.test(key)&&value){const time=node('time',dateLabel(value));time.dateTime=String(value);td.append(time);td.className='ux-date';}
  else td.textContent=value===null||value===undefined||value===''?'Not recorded':display(value);tr.append(td);
 }body.append(tr);}table.append(body);wrap.append(table);target.append(wrap);
};
P.form=async(title,definitions,values,submit,description)=>{
 const form=node('form',undefined,'ux-form'),sections=node('div'),controls={},groups=new Map();if(description)form.append(node('p',description,'muted'));
 const error=node('p',undefined,'form-error');error.setAttribute('role','alert');const actions=node('div',undefined,'ux-form-actions'),save=node('button','Save changes');save.type='submit';const dialog=P.dialog(title,form);actions.append(button('Cancel',()=>dialog.close(),'secondary'),save);form.append(sections,error,actions);save.disabled=true;
 try{for(const [key,definition] of Object.entries(definitions)){
  const group=UX.group(key);if(!groups.has(group)){const fieldset=node('fieldset',undefined,'ux-form-section'),legend=node('legend',group),grid=node('div',undefined,'field-grid');fieldset.append(legend,grid);groups.set(group,grid);sections.append(fieldset);}
  const value=values?.[key];
  const control=await P.field(key,definition,value);if(definition.required)control.label.append(node('small','Required','ux-required'));groups.get(group).append(control.label);controls[key]=control;
 }save.disabled=false;}catch(e){error.textContent=e.message;}
 form.onsubmit=async event=>{event.preventDefault();save.disabled=true;save.textContent='Saving…';error.textContent='';try{const data=Object.fromEntries(Object.entries(controls).map(([key,c])=>[key,c.get()]).filter(([,v])=>v!==undefined));await submit(data);dialog.close();}catch(e){error.textContent=e.message;}finally{save.disabled=false;save.textContent='Save changes';}};return dialog;
};
P.recordFields=async record=>{
 const root=node('div',undefined,'ux-record-fields'),fields=P.catalog?.modules[record.kind]?.fields||{},sections=new Map();
 for(const [key,value] of Object.entries(record.data||{})){
  if(['approved_by','approved_at','approval_version'].includes(key))continue;
  const group=UX.group(key);if(!sections.has(group)){const section=node('section',undefined,'ux-record-section'),dl=node('dl',undefined,'detail-grid');section.append(node('h3',group),dl);root.append(section);sections.set(group,dl);}
  const definition=fields[key],item=node('div',undefined,'detail-field'),dd=node('dd');item.append(node('dt',definition?.label||UI.label(key)),dd);
  if(definition&&['reference','references'].includes(definition.type)){
   let choices=[];try{choices=await P.options(definition.ref);}catch{}
   for(const id of Array.isArray(value)?value:[value]){const choice=choices.find(c=>c.id===id),label=choice?.title||'Related record unavailable';if(!choice){dd.append(node('span',label));continue;}
    dd.append(button(label,async()=>{try{if(definition.ref.startsWith('legacy:')){const kind=definition.ref.split(':')[1],methods={risk:'list_risks',task:'list_tasks',vendor:'vendors',assessment:'list_assessments',evidence:'evidence',finding:'findings',initiative:'initiatives',change:'changes'},method=methods[kind];if(!method)throw Error('Open this item in its source register.');const items=await read(method),row=items.find(r=>r.id===id);if(!row)throw Error('The related record is unavailable.');await details(row,method);}else await P.showRecord({id});}catch(e){P.note(e.message,true);}},'small-link'));
   }
  }else if(typeof value==='object')dd.append(structured(value));else if(['result','retest','post_result','vendor_readiness'].includes(key))dd.append(UX.status(value));else if(definition?.type==='date'||definition?.type==='datetime')dd.textContent=value?dateLabel(value):'Not recorded';else dd.textContent=typeof value==='boolean'?(value?'Yes':'No'):display(value);
  sections.get(group).append(item);
 }
 const technical=node('details',undefined,'technical');technical.append(node('summary','Technical details'),node('pre',JSON.stringify({id:record.id,kind:record.kind,version:record.version,data:record.data},null,2)));root.append(technical);return root;
};
const uxModules=P.modules;P.modules=async box=>{await uxModules(box);const empty=box.querySelector('.ux-empty');if(empty){const definition=P.catalog.modules[P.kind],name=definition?.title||'records';empty.replaceChildren(icon('layers'),node('h3','Start with '+name.toLowerCase()),node('p','Create a record, assign responsibility, and add supporting evidence when available.'),button('Create your first record',()=>P.edit(),''));box.querySelector('.pl-actions>button')?.classList.add('secondary');if(P.catalog.role==='viewer'){empty.querySelector('button')?.remove();const create=box.querySelector('.pl-actions>button');if(create)create.hidden=true;}}};
UX.inventory=record=>{
 const box=node('div',undefined,'ux-import'),intro=node('p','Choose a CSV, map its columns, then review the first 10 rows before importing. Up to 1,000 accounts; no passwords or tokens.'),fileLabel=node('label','Account inventory CSV'),file=node('input');file.type='file';file.accept='.csv,text/csv';file.setAttribute('aria-label','Account inventory CSV');fileLabel.append(file);
 const stages=node('ol',undefined,'ux-import-steps');for(const text of ['Choose file','Map columns','Review & import'])stages.append(node('li',text));const mappings=node('div',undefined,'field-grid'),preview=node('div'),error=node('p',undefined,'form-error');error.setAttribute('role','alert');const actions=node('div',undefined,'ux-form-actions'),importButton=button('Import reviewed accounts',async()=>{
  if(!prepared)return;importButton.disabled=true;error.textContent='';try{const result=await P.send('/operations/'+record.id+'/run',{version:record.version,accounts:prepared});P.note(result.created+' account reviews created. Existing accounts were skipped.');dialog.close();P.choices.clear();await OPS.render();}catch(e){error.textContent=e.message;importButton.disabled=false;}
 },'');importButton.disabled=true;let prepared=null;let generation=0;
 const dialog=P.dialog('Import access inventory',box);actions.append(button('Cancel',()=>dialog.close(),'secondary'),importButton);box.append(intro,stages,fileLabel,mappings,preview,error,actions);
 file.onchange=async()=>{
  const current=++generation;prepared=null;importButton.disabled=true;mappings.replaceChildren();preview.replaceChildren();error.textContent='';const selected=file.files[0];if(!selected)return;
  try{
   if(selected.size>2*1024*1024)throw Error('Choose a CSV up to 2 MiB.');const csv=StudioCSV.parseCSV(await selected.text());if(current!==generation)return;const selectors={};
   const refresh=()=>{prepared=null;importButton.disabled=true;preview.replaceChildren();error.textContent='';try{const mapping=Object.fromEntries(Object.entries(selectors).map(([k,s])=>[k,Number(s.value)]));prepared=StudioCSV.accounts(csv,mapping);preview.append(node('h3',prepared.length+' accounts ready for review'),node('p','Showing '+Math.min(10,prepared.length)+' of '+prepared.length+' rows. Unmapped privileged access defaults to No; an unmapped last-use date stays unknown.'));P.table(preview,prepared.slice(0,10),['account','system','privileged','last_seen']);importButton.disabled=false;}catch(e){error.textContent=e.message;}};
   for(const [key,title] of [['account','Account'],['system','System'],['privileged','Privileged access (optional)'],['last_seen','Last use (optional)']]){
    const label=node('label',title),select=node('select');select.setAttribute('aria-label',title+' column');select.append(new Option(key==='account'||key==='system'?'Choose a column':'Not mapped','-1'));csv.headers.forEach((h,i)=>select.append(new Option(h,String(i))));const index=csv.headers.findIndex(h=>h.toLowerCase().replace(/[\s-]/g,'_')===key);select.value=String(index);select.onchange=refresh;selectors[key]=select;label.append(select);mappings.append(label);
   }refresh();
  }catch(e){error.textContent=e.message;}
 };
};
const uxRun=OPS.run;OPS.run=record=>record.kind==='op_campaign'?UX.inventory(record):uxRun(record);
const uxOverview=OPS.overview;OPS.overview=async box=>{await uxOverview(box);const report=[...box.querySelectorAll('button')].find(b=>b.textContent==='Freeze operational report');report?.classList.remove('secondary');};
OPS.navigation=(host,role)=>{
 const nav=node('nav',undefined,'ux-ops-navigation');nav.setAttribute('aria-label','Operations secondary pages');const group=Object.keys(UX.categories).find(k=>UX.categories[k].includes(OPS.tab));
 for(const name of ['Overview',...Object.keys(UX.categories)]){const b=button(name,()=>{OPS.tab=name==='Overview'?'Overview':UX.categories[name].filter(t=>t!=='Integration health'||role==='owner')[0];OPS.render();},name===(group||'Overview')?'':'secondary');b.classList.add('ux-category-button');b.setAttribute('aria-pressed',String(name===(group||'Overview')));nav.append(b);}
 const areaLabel=node('label','Area','ux-category-select'),area=node('select');area.setAttribute('aria-label','Operations area');for(const name of ['Overview',...Object.keys(UX.categories)])area.append(new Option(name,name));area.value=group||'Overview';area.onchange=()=>{OPS.tab=area.value==='Overview'?'Overview':UX.categories[area.value].filter(t=>t!=='Integration health'||role==='owner')[0];OPS.render();};areaLabel.append(area);nav.append(areaLabel);
 if(group){const label=node('label','Section'),select=node('select');select.setAttribute('aria-label','Operations section');for(const title of UX.categories[group])if(title!=='Integration health'||role==='owner')select.append(new Option(title,title));select.value=OPS.tab;select.onchange=()=>{OPS.tab=select.value;OPS.render();};label.append(select);nav.append(label);}host.append(nav);
};
OPS.help['Access reviews']='Create a campaign with an enabled reviewer and deadline. Open it to import a CSV inventory, map columns and review the preview. The assigned reviewer records retain/revoke decisions. Revoke decisions require removal verification before completion.';
// Customer branding leads the header; protected owner attribution remains intact.
const uxBrand=XP.applyBrand;XP.applyBrand=()=>{uxBrand();$('workspace').querySelector('.header-context')?.classList.add('ux-brand-context');};
