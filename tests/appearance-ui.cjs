/* Real page styles and browser preference lifecycle; synthetic unauthenticated API responses. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve('src/cyberstudio/web/static');
const routes={'/':'index.html','/documentation':'documentation.html','/account-recovery':'account-recovery.html','/audit-room':'audit-room.html','/invitation':'invitation.html'};
async function serve(context){await context.route('**/*',async route=>{
 const p=new URL(route.request().url()).pathname;
 if(p.startsWith('/api/'))return route.fulfill({status:401,contentType:'application/json',body:'{"detail":"Sign in required"}'});
 const file=routes[p]||p.replace('/static/',''),full=path.resolve(root,file);
 if(!full.startsWith(root+path.sep)||!fs.existsSync(full))return route.fulfill({status:404,body:'Not found'});
 return route.fulfill({status:200,contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(full)});
});}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox'],...(process.env.STUDIO_CHROMIUM_PATH?{executablePath:process.env.STUDIO_CHROMIUM_PATH}:{} )});
 try{
  const context=await browser.newContext({colorScheme:'dark',viewport:{width:1440,height:1000}});await serve(context);
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const url of Object.keys(routes)){
   await page.goto('https://studio.test'+url);await page.getByLabel('Appearance',{exact:true}).waitFor();
   for(const theme of ['light','dark']){
    await page.getByLabel('Appearance',{exact:true}).selectOption(theme);assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
    const colors=await page.evaluate(()=>({bg:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,input:getComputedStyle(document.querySelector('input,select')).color}));
    assert.equal(colors.text,theme==='dark'?'rgb(230, 237, 244)':url==='/'||url==='/invitation'?'rgb(32, 55, 68)':'rgb(23, 53, 67)');
    if(theme==='dark')assert.equal(colors.bg,'rgb(12, 28, 40)');
    await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow on '+url+' in '+theme);await page.setViewportSize({width:1440,height:1000});
   }
  }
  await page.getByLabel('Appearance',{exact:true}).selectOption('light');await page.reload();assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  await page.getByLabel('Appearance',{exact:true}).selectOption('system');await page.emulateMedia({colorScheme:'light'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
  const second=await context.newPage();await second.goto('https://studio.test/account-recovery');await second.getByLabel('Appearance',{exact:true}).selectOption('light');await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');
  await context.close();
  const blocked=await browser.newContext({colorScheme:'dark'});await serve(blocked);await blocked.addInitScript(()=>{Storage.prototype.getItem=()=>{throw Error('Storage disabled');};Storage.prototype.setItem=()=>{throw Error('Storage disabled');};});
  const fallback=await blocked.newPage();await fallback.goto('https://studio.test/account-recovery');await fallback.getByLabel('Appearance',{exact:true}).selectOption('light');assert.equal(await fallback.locator('html').getAttribute('data-theme'),'light');await blocked.close();
  assert.deepEqual(errors,[]);console.log('APPEARANCE_BROWSER_ACCEPTANCE_PASSED: five entry pages, light/dark/system, reload, OS changes, tabs, blocked storage and mobile layout');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
