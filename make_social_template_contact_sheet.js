const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async()=>{
 const dir=path.resolve('design-references/social-launch/batch1-canva-templates');
 const files=fs.readdirSync(dir).filter(f=>f.endsWith('.png')).sort();
 const cards=files.map(f=>`<div class="card"><img src="file:///${path.join(dir,f).replace(/\\/g,'/')}"/><p>${f}</p></div>`).join('');
 const html=`<!doctype html><html><head><style>body{margin:0;background:#fbf8f1;font-family:Arial,sans-serif;color:#0D2540}.wrap{padding:48px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}.card{background:white;border:1px solid #dde3ec;border-radius:18px;padding:16px;box-shadow:0 10px 30px #0d254020}.card img{width:100%;height:420px;object-fit:contain;background:#fbf8f1;border-radius:12px}.card p{font-size:18px;font-weight:700;line-height:1.25}h1{font-family:Georgia,serif;font-size:48px}</style></head><body><div class="wrap"><h1>NamEngine Batch 1 Social Templates</h1><div class="grid">${cards}</div></div></body></html>`;
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1800,height:3000},deviceScaleFactor:1});
 await page.setContent(html,{waitUntil:'load'});
 await page.screenshot({path:path.join(dir,'batch1-contact-sheet.png'),fullPage:true});
 await browser.close();
 console.log(path.join(dir,'batch1-contact-sheet.png'));
})();