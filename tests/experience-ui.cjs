/* Isolated browser acceptance: real application HTML/JS/CSS with synthetic API responses. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const staticRoot=path.resolve('src/cyberstudio/web/static');
const questions=JSON.parse(execFileSync('python',['-c',"import json;from cyberstudio.questionnaires import THIRD_PARTY_QUESTIONS;print(json.dumps([dict(code=c,prompt=p,rationale='',version=0,visible=True,section=('HIPAA' if 8<=int(c[-3:])<=15 else 'Questions'),evidence=[]) for c,p,d in THIRD_PARTY_QUESTIONS]))"],{env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'}));
const org='test-org',assessment='test-assessment';let saved=0;
const task={id:'task1',title:'Synthetic remediation',owner:'owner',status:'open',due_date:'2099-01-01',created_at:'2026-10-31T00:00:00'};
const state={role:'owner',settings:{brand_name:'Synthetic Brand',accent:'#097f7a'},preferences:{onboarding_dismissed:false},members:[{username:'owner',installation_role:'owner'}],assessments:[],notifications:[],actions:[{type:'task',id:'task1',title:task.title,owner:'owner',due:'2099-01-01',days:100,status:'open'}],snapshots:[{day:'2026-10-31',metrics:{exposure_total:0,open_risks:0,high_critical:0,open_tasks:1,done_tasks:0,verified_controls:0,applicable_controls:0}}]};
const methods={list_organizations:[{id:org,name:'Synthetic Org'}],board_snapshot:{},list_risks:[],list_tasks:[task],vendors:[],findings:[],frameworks:[],implementations:[],evidence:[],list_assessments:[{id:assessment,title:'Synthetic supplier questionnaire',status:'draft',framework_label:'Third-party risk assessment — Default (60 questions), v1'}],list_templates:[],board_reports:[]};
(async()=>{const browser=await chromium.launch({headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1440,height:1000}});let errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url()),p=url.pathname;const json=value=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});let body={};try{body=req.postDataJSON()||{};}catch{}
if(p==='/api/me')return json({username:'owner',csrf:'test',role:'owner'});
if(p==='/api/operations')return json({create_assessment:{write:true,fields:[{name:'org',required:true,kind:'string'},{name:'title',required:true,kind:'string'},{name:'scope',required:false,kind:'string',default:''},{name:'template_id',required:false,kind:'string',default:null}]}});
if(p.startsWith('/api/call/')){const method=p.split('/').pop();return json({result:methods[method]||[]});}
if(p==='/api/experience/'+org)return json(state);
if(p.includes('/questionnaire/'))return json({questions,summary:{total:60,applicable:60,answered:0,unanswered:questions.filter(q=>!q.rationale).map(q=>q.code),without_evidence:questions.map(q=>q.code),evidence_needing_review:[],meta:{assessment_id:assessment,state:'draft',reviewer:'owner',vendor_id:null,due_date:'',notes:''}}});
if(p.endsWith('/preferences')){Object.assign(state.preferences,body);return json({});}
if(p.endsWith('/response')){const q=questions.find(q=>q.code===body.code);q.rationale=body.response;q.version++;saved++;return json({saved:true,version:q.version});}
if(p.endsWith('/dependencies')||p.endsWith('/invites'))return json([]);
if(p.endsWith('/task')){Object.assign(task,body);return json({});}
if(p.includes('/search'))return json({results:[{type:'task',id:'task1',title:task.title}]});
if(p.includes('/record/'))return json({record:task,links:[],reviews:[],comments:[]});
if(p.endsWith('/reports/preview'))return json({brand:'Synthetic Brand',organization:'Synthetic Org',period_note:'Current summary; dated records in selected period.',commentary:body.commentary,sections:{summary:[{metric:'open_tasks',value:1}]}});
if(p.startsWith('/api/'))return json({});
const file=p==='/'?'index.html':p.replace('/static/','');const full=path.join(staticRoot,file);if(!full.startsWith(staticRoot)||!fs.existsSync(full))return route.fulfill({status:404,body:'Not found'});return route.fulfill({status:200,contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(full)});
});
await page.goto('https://studio.test/');await page.waitForFunction(()=>typeof XP!=='undefined'&&XP.state?.role==='owner');
assert.equal(await page.locator('.header-context .eyebrow').textContent(),'Synthetic Brand');
await page.getByRole('button',{name:'Assessments',exact:true}).click();
await page.locator('#special select').first().selectOption(assessment);await page.locator('#response-TPR-009').waitFor({state:'attached'});
await page.locator('details.xp-question-section').filter({has:page.locator('#response-TPR-009')}).locator('summary').click();await page.locator('#response-TPR-009').fill('No');await page.waitForFunction(()=>document.getElementById('response-status-TPR-009').textContent==='Saved');
assert.equal(await page.locator('#response-TPR-010').isVisible(),false);
await page.getByLabel('Show questions skipped by follow-up conditions').check();assert.equal(await page.locator('#response-TPR-010').isVisible(),true);
await page.getByLabel('Show questions skipped by follow-up conditions').uncheck();
await page.getByRole('button',{name:'Review completion',exact:true}).click();await page.locator('#xp-dialog').waitFor({state:'visible'});assert.match(await page.locator('#xp-dialog').textContent(),/Unanswered/);await page.locator('#xp-dialog').getByRole('button',{name:'Close',exact:true}).click();
await page.getByRole('button',{name:'Action center',exact:true}).click();await page.getByRole('button',{name:'Work board',exact:true}).click();await page.locator('.xp-kanban').waitFor({state:'visible'});await page.getByLabel('Status for Synthetic remediation').selectOption('in_progress');await page.waitForFunction(()=>document.querySelector('.xp-task select')?.value==='in_progress');
await page.getByRole('button',{name:'Report builder',exact:true}).click();await page.getByLabel('Management commentary').fill('Synthetic commentary');await page.getByRole('button',{name:'Preview report',exact:true}).click();await page.getByText('Preview matches the selected sections and period used for export.').waitFor();
await page.getByLabel('Theme',{exact:true}).selectOption('dark');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
await page.keyboard.press('Control+k');await page.locator('#xp-dialog input[type=search]').fill('remediation');await page.getByRole('button',{name:'Task · Synthetic remediation',exact:true}).waitFor();await page.locator('#xp-dialog').getByRole('button',{name:'Close',exact:true}).click();
await page.getByRole('button',{name:'Team & invitations',exact:true}).click();await page.getByRole('heading',{name:'Create an invitation',exact:true}).waitFor();
await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Actions',exact:true}).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'Mobile viewport must not overflow horizontally');
assert.equal(saved,1);assert.deepEqual(errors,[]);await page.screenshot({path:'/tmp/studio-experience-ui.png',fullPage:true});console.log('EXPERIENCE_BROWSER_ACCEPTANCE_PASSED: branding, questionnaire autosave/conditions/review, board status, report preview, themes, search, invitations, mobile layout');await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
