const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async()=>{
 const svgPath=path.resolve('static/images/namengine-baby.svg');
 const out=path.resolve('design-references/social-launch/batch1-canva-templates/real-namengine-baby-logo-reference.png');
 const svg=fs.readFileSync(svgPath,'utf8');
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1500,height:240},deviceScaleFactor:1});
 await page.setContent(`<!doctype html><html><body style="margin:0;background:#fbf8f1">${svg}</body></html>`);
 await page.screenshot({path:out,clip:{x:0,y:0,width:1500,height:240}});
 await browser.close();
 console.log(out);
})();
