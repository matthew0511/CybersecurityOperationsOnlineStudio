/* Isolated browser acceptance: real application HTML/JS/CSS with synthetic API responses. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const platformCatalog=JSON.parse(execFileSync('python',['-c',"import json;from cyberstudio.web.platform.catalog import features,modules;from cyberstudio.web.platform.connectors import PROVIDERS;from cyberstudio.web.platform.reporting import TEMPLATES;from cyberstudio.web.platform.documentation import documentation;print(json.dumps(dict(features=features(),modules=modules(),providers=PROVIDERS,report_templates=TEMPLATES,role='owner',docs=documentation())))"],{env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'}));
const staticRoot=path.resolve('src/cyberstudio/web/static');
const questions=JSON.parse(execFileSync('python',['-c',"import json;from cyberstudio.questionnaires import THIRD_PARTY_QUESTIONS;print(json.dumps([dict(code=c,prompt=p,rationale='',version=0,visible=True,section=('HIPAA' if 8<=int(c[-3:])<=15 else 'Questions'),evidence=[]) for c,p,d in THIRD_PARTY_QUESTIONS]))"],{env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'}));
const org='test-org',assessment='test-assessment';let saved=0,brandingSaved=0;
const branding={display_name:'Synthetic Brand',tagline:'Board reporting',primary_color:'112C3A',accent_color:'0C827D',footer_note:'Confidential',has_logo:false,can_edit:true};
const logoPng=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAFAAAAAeCAYAAAC7Q5mxAAAAXklEQVR4nO3QQQ3AMBDAsK7Ij/nGoXlUk2wEUZ418y6O7dsBf2dgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRgZGBkYGRg9AGiqQI7hC0r+AAAAABJRU5ErkJggg==','base64');
const task={id:'task1',title:'Synthetic remediation',owner:'owner',status:'open',due_date:'2099-01-01',created_at:'2026-10-31T00:00:00'};
const state={role:'owner',settings:{brand_name:'Synthetic Brand',accent:'#097f7a'},preferences:{onboarding_dismissed:false},members:[{username:'owner',installation_role:'owner'}],assessments:[],notifications:[],actions:[{type:'task',id:'task1',title:task.title,owner:'owner',due:'2099-01-01',days:100,status:'open'}],snapshots:[{day:'2026-10-31',metrics:{exposure_total:0,open_risks:0,high_critical:0,open_tasks:1,done_tasks:0,verified_controls:0,applicable_controls:0}}]};
const methods={list_organizations:[{id:org,name:'Synthetic Org'}],board_snapshot:{},list_risks:[],list_tasks:[task],vendors:[],findings:[],frameworks:[],implementations:[],evidence:[],list_assessments:[{id:assessment,title:'Synthetic supplier questionnaire',status:'draft',framework_label:'Third-party risk assessment — Default (60 questions), v1'}],list_templates:[],board_reports:[]};
(async()=>{const browser=await chromium.launch({headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1440,height:1000}});global.testPage=page;let errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url()),p=url.pathname;const json=value=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});let body={};try{body=req.postDataJSON()||{};}catch{}
if(p==='/api/platform/catalog')return json(platformCatalog);
if(p==='/api/platform/'+org+'/ai/overview')return json({cases:[],counts:{},note:'Synthetic configuration-bound governance readiness'});
if(p==='/api/platform/ai/reference')return json(JSON.parse(fs.readFileSync(path.join(staticRoot,'../platform/ai_reference.json'),'utf8')));
if(p==='/api/platform/documentation')return json(platformCatalog.docs);
if(p==='/api/security')return json({username:'owner',role:'owner',mfa_enabled:false,security_key_ready:true,sessions:[],entra_configured:false});
if(p==='/api/platform/'+org+'/overview')return json({counts:[],executions:[],quarantine:[],editions:[],role:'owner'});
if(p==='/api/platform/'+org+'/integrations')return json({providers:platformCatalog.providers,connections:[],jobs:[]});
if(p.startsWith('/api/platform/')&&(p.includes('/records/')||p.includes('/choices/')||p.endsWith('/integrations')||p.endsWith('/jobs')))return json([]);
if(p==='/api/me')return json({username:'owner',csrf:'test',role:'owner'});
if(p==='/api/operations')return json({create_assessment:{write:true,fields:[{name:'org',required:true,kind:'string'},{name:'title',required:true,kind:'string'},{name:'scope',required:false,kind:'string',default:''},{name:'template_id',required:false,kind:'string',default:null}]}});
if(p.startsWith('/api/call/')){const method=p.split('/').pop();return json({result:methods[method]||[]});}
if(p==='/api/report-branding/'+org){if(req.method()==='POST'){brandingSaved++;branding.display_name='Board Identity';branding.has_logo=true;}return json(branding);}
if(p==='/api/report-branding/'+org+'/logo')return route.fulfill({status:200,contentType:'image/png',body:logoPng});
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
const file=p==='/'?'index.html':p==='/documentation'?'documentation.html':p.replace('/static/','');const full=path.join(staticRoot,file);if(!full.startsWith(staticRoot)||!fs.existsSync(full))return route.fulfill({status:404,body:'Not found'});return route.fulfill({status:200,contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(full)});
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
await page.locator('[data-page=reports]').click();await page.getByLabel('Report display name',{exact:true}).fill('Board Identity');await page.getByLabel('Organization logo',{exact:false}).setInputFiles({name:'logo.png',mimeType:'image/png',buffer:logoPng});await page.getByRole('button',{name:'Save report branding',exact:true}).click();await page.getByText('Report branding saved. New PDF and Excel downloads will use this identity.',{exact:true}).waitFor();assert.equal(brandingSaved,1);
await page.getByLabel('Theme',{exact:true}).selectOption('dark');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
await page.keyboard.press('Control+k');await page.locator('#xp-dialog input[type=search]').fill('remediation');await page.getByRole('button',{name:'Task · Synthetic remediation',exact:true}).waitFor();await page.locator('#xp-dialog').getByRole('button',{name:'Close',exact:true}).click();
await page.getByRole('button',{name:'Workspace hub',exact:true}).click();await page.getByRole('button',{name:'Team & invitations',exact:true}).click();await page.getByRole('heading',{name:'Create an invitation',exact:true}).waitFor();
await page.getByRole('button',{name:'Program center',exact:true}).click();await page.getByLabel('Program module',{exact:true}).waitFor();
await page.getByRole('button',{name:'Create record',exact:true}).click();await page.getByRole('dialog').getByLabel('Title',{exact:true}).fill('Synthetic office');await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
await page.getByRole('button',{name:'App integrations',exact:true}).click();await page.getByRole('heading',{name:'Connected applications',exact:true}).waitFor();
await page.getByRole('button',{name:'AI Governance',exact:true}).click();await page.getByRole('button',{name:'Read source guidance',exact:true}).click();await page.getByLabel('Search AI governance reference',{exact:true}).fill('agentic');assert.ok(await page.locator('.ai-reference details:visible').count()>0);await page.getByRole('button',{name:'Registers',exact:true}).click();await page.getByLabel('AI governance register',{exact:true}).selectOption('ai_decision');await page.getByRole('button',{name:'Create record',exact:true}).click();await page.getByRole('dialog').getByLabel('Delegated authority and required concurrence',{exact:true}).waitFor();await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
await page.getByRole('button',{name:'Account security',exact:true}).click();await page.getByRole('button',{name:'Begin authenticator enrollment',exact:true}).waitFor();
if(process.env.AXE_MODULE){await page.addScriptTag({path:require.resolve(process.env.AXE_MODULE)});const results=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));assert.deepEqual(results.violations.filter(v=>['critical','serious'].includes(v.impact)).map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);}
await page.goto('https://studio.test/documentation');await page.getByText('50. Recycle bin and restoration',{exact:true}).waitFor();await page.getByLabel('Search documentation',{exact:true}).fill('authenticator');assert.ok(await page.locator('[data-searchable]:visible').count()>0);
await page.goto('https://studio.test/');await page.waitForFunction(()=>typeof XP!=='undefined'&&XP.state?.role==='owner');
await page.getByRole('button',{name:'Workspace hub',exact:true}).click();await page.getByRole('button',{name:'Actions',exact:true}).waitFor();await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Actions',exact:true}).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'Mobile viewport must not overflow horizontally');
assert.equal(saved,1);assert.deepEqual(errors,[]);await page.screenshot({path:'/tmp/studio-experience-ui.png',fullPage:true});console.log('EXPERIENCE_BROWSER_ACCEPTANCE_PASSED: branding, questionnaire autosave/conditions/review, board status, reports, themes, search, invitations, program modules, integrations, security, WCAG automated serious/critical gate, fifty-feature documentation, original-Hub AI governance reference/registers and mobile layout');await browser.close();
})().catch(async e=>{console.error(e);if(global.testPage)console.error((await global.testPage.locator('body').innerText()).slice(-12000));process.exit(1);});

