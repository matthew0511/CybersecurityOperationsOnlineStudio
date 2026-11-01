'use strict';
const AI={tab:'Overview',reference:null};
// Render captured Markdown with DOM text nodes. Source text never becomes HTML or code.
AI.inline=(target,text)=>{
 const pattern=/\[([^\]]+)\]\(([^)]+)\)/g;let at=0;
 for(const match of text.matchAll(pattern)){
  target.append(document.createTextNode(text.slice(at,match.index).replace(/\*\*/g,'')));
  let url;try{url=new URL(match[2]);}catch{}
  if(url&&url.protocol==='https:'){const a=node('a',match[1].replace(/\*\*/g,''));a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';target.append(a);}else target.append(document.createTextNode(match[1]));
  at=match.index+match[0].length;
 }
 target.append(document.createTextNode(text.slice(at).replace(/\*\*/g,'')));
};
AI.markdown=(target,body)=>{
 const lines=body.split('\n');let list=null;
 for(let i=0;i<lines.length;i++){
  const text=lines[i].trim();if(!text||/^<\/?aside>/.test(text)){list=null;continue;}
  if(text.startsWith('|')){
   const wrap=node('div',undefined,'table-wrap'),table=node('table');let first=true;
   while(i<lines.length&&lines[i].trim().startsWith('|')){
    const line=lines[i].trim();if(!/^\|[\s:|\-]+\|$/.test(line)){
     const tr=node('tr');for(const value of line.slice(1,-1).split(/(?<!\\)\|/)){const cell=node(first?'th':'td');if(first)cell.scope='col';AI.inline(cell,value.trim());tr.append(cell);}table.append(tr);first=false;
    }i++;
   }i--;wrap.append(table);target.append(wrap);list=null;continue;
  }
  const heading=text.match(/^(#{3,6})\s+(.*)/);if(heading){const h=node('h3');AI.inline(h,heading[2]);target.append(h);list=null;continue;}
  const bullet=text.match(/^(?:[-*]|\d+\.)\s+(.*)/);if(bullet){if(!list){list=node('ul');target.append(list);}const li=node('li');AI.inline(li,bullet[1]);list.append(li);continue;}
  list=null;const p=node('p');AI.inline(p,text);target.append(p);
 }
};
AI.referenceView=async box=>{
 if(!AI.reference)AI.reference=await api('/api/platform/ai/reference');
 const ref=AI.reference;box.append(node('p',ref.notice,'ai-reference-notice'),node('p','Source: Cybersecurity Operations Hub → AI Governance · snapshot '+ref.snapshot_date+' · '+ref.program_owner));
 const search=node('input');search.type='search';search.placeholder='Search clinical review, agent permissions, retirement…';search.setAttribute('aria-label','Search AI governance reference');box.append(search);
 const container=node('div',undefined,'ai-reference');box.append(container);
 for(const section of ref.sections){const details=node('details'),summary=node('summary',section.title);details.append(summary);AI.markdown(details,section.body);container.append(details);}
 search.oninput=()=>{const query=search.value.trim().toLowerCase();for(const d of container.children){d.hidden=!!query&&!d.textContent.toLowerCase().includes(query);if(query&&!d.hidden)d.open=true;}};
};
AI.report=()=>P.form('Freeze AI governance report',{format:{label:'Export format',type:'select',options:['pdf','xlsx','pptx'],required:true},commentary:P.basic('Management commentary','textarea')},{format:'pdf'},async values=>{
 const edition=await P.send('/editions',{...values,template:'ai_governance'}),content=node('div');content.append(node('p','Frozen edition saved with source data, branding and integrity hash.'),P.link('Download AI governance report',edition.download_url));if(edition.preview_url)content.append(P.link('Preview the same PDF edition',edition.preview_url));P.dialog('AI report ready',content);
},'Current recorded evidence and release holds; no historical approval or compliance is inferred.');
AI.overview=async box=>{
 const state=await P.get('/ai/overview');box.append(node('p',state.note,'ai-reference-notice'));
 const cards=node('div',undefined,'cards');for(const [title,value] of [['AI use cases',state.cases.length],['Currently authorized',state.cases.filter(c=>c.authorization!=='not_authorized').length],['Cases with release holds',state.cases.filter(c=>c.blockers.length).length],['High / critical cases',state.cases.filter(c=>['high','critical'].includes(c.risk_tier)).length]])cards.append(metric(title,value,'Current selected organization','shield'));box.append(cards);
 const actions=node('div',undefined,'pl-actions');actions.append(button('Register an AI use case',()=>{AI.tab='Registers';P.kind='ai_use_case';AI.render();},'secondary'),button('Freeze AI board report',AI.report,'secondary'),button('Read source guidance',()=>{AI.tab='Source reference';AI.render();},'secondary'));box.append(actions);
 for(const item of state.cases){const card=P.box(item.title,'Accountable owner: '+item.owner+' · '+UI.label(item.risk_tier)+' risk · review '+dateLabel(item.review_on));card.append(badge(item.authorization),node('p',item.ready_for_human_release_review?'Ready for independent release review. No automatic approval.':item.blockers.length+' release holds'));
  if(item.blockers.length){const ul=node('ul');for(const hold of item.blockers)ul.append(node('li',hold));card.append(ul);}
  card.append(button('Open use-case record',()=>P.showRecord({id:item.id}),'secondary'));if(item.decision_id)card.append(button('Open release decision',()=>P.showRecord({id:item.decision_id}),'secondary'));box.append(card);
 }if(!state.cases.length)box.append(node('p','Start with a specific AI feature and workflow. Source examples have not been imported as live approvals.','empty'));
};
AI.registers=async box=>{
 if(!P.kind.startsWith('ai_'))P.kind='ai_use_case';await P.modules(box);
 const select=box.querySelector('select[aria-label="Program module"]');select.setAttribute('aria-label','AI governance register');
 for(const option of [...select.options])if(!option.value.startsWith('ai_'))option.remove();select.value=P.kind;
 box.prepend(node('p','Records are linked within this organization. Draft → In progress → Completed records document reviews/tests. Decisions and exceptions require Draft → Submitted → independent Approved before activation.','muted'));
};
AI.render=async()=>{
 $('page-title').textContent='AI Governance';$('page-description').textContent='Purpose, evidence and accountable decisions for every AI use case.';$('section-label').textContent='AI Governance';$('cards').replaceChildren();$('insights').replaceChildren();$('insights').hidden=true;$('records-panel').hidden=true;$('special').hidden=false;$('open-action').hidden=true;
 const host=$('special');host.replaceChildren();
 try{
  if(!org){host.append(node('p','Choose an organization to manage AI governance.'));return;}
  P.catalog=await api('/api/platform/catalog');const tabs=node('div',undefined,'pl-tabs');for(const tab of ['Overview','Registers','Source reference']){const b=button(tab,()=>{AI.tab=tab;AI.render();},AI.tab===tab?'':'secondary');b.setAttribute('aria-pressed',String(AI.tab===tab));tabs.append(b);}host.append(tabs);
  const box=P.box(AI.tab==='Source reference'?'Original Hub AI governance reference':AI.tab);host.append(box);await ({Overview:AI.overview,Registers:AI.registers,'Source reference':AI.referenceView}[AI.tab])(box);
 }catch(e){host.replaceChildren(P.box('AI governance could not be loaded',e.message),button('Retry',AI.render,'secondary'));}
};
const aiPreviousRender=P.render;P.render=(...args)=>page==='ai'?AI.render():aiPreviousRender(...args);
const aiPreviousLoad=load;load=(...args)=>page==='ai'?AI.render():aiPreviousLoad(...args);
pages.ai=['AI Governance','Use-case oversight, evidence and scoped decisions.',[''],[],'shield'];
const aiNav=button('AI Governance',()=>navigate('ai'),'','shield');aiNav.dataset.page='ai';aiNav.title='AI Governance';aiNav.querySelector('span').className='nav-text';
const governanceAnchor=$('navigation').querySelector('[data-page="changes"]');if(governanceAnchor)governanceAnchor.after(aiNav);else $('navigation').append(aiNav);
