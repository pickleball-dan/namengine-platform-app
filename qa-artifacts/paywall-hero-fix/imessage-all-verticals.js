const { chromium } = require('playwright');
const path = require('path');

const verticals = [
  {
    label: 'baby',
    img: '../../static/images/baby/namengine-baby-share.png',
    title: 'A NamEngine Baby name list, ready to explore',
    msg: 'Check out these baby names 🍼',
    bg: '#1c1c1e',
  },
  {
    label: 'pet',
    img: '../../static/images/pet/namengine-pet-share-current.png',
    title: 'A NamEngine Pet name list, ready to explore',
    msg: 'Found some great pet names 🐾',
    bg: '#1c1c1e',
  },
  {
    label: 'business',
    img: '../../static/images/business/namengine-business-share-current.png',
    title: 'A NamEngine Business name list, ready to explore',
    msg: 'Shortlist of business names 💼',
    bg: '#1c1c1e',
  },
];

function html(v) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:${v.bg};display:flex;flex-direction:column;align-items:flex-end;
    justify-content:flex-end;padding:24px 16px 32px;min-height:100vh;
    font-family:-apple-system,"SF Pro Text",sans-serif;gap:6px;}
  .bubble{background:#007AFF;color:white;padding:10px 14px;border-radius:18px 18px 4px 18px;
    font-size:16px;max-width:260px;}
  .card{width:260px;background:#2c2c2e;border-radius:14px;overflow:hidden;
    border:1px solid rgba(255,255,255,0.08);}
  .card img{width:100%;display:block;aspect-ratio:1200/630;object-fit:cover;}
  .meta{padding:8px 12px 10px;}
  .site{font-size:11px;color:#8e8e93;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px;}
  .title{font-size:13px;font-weight:600;color:#fff;line-height:1.3;}
  .time{font-size:11px;color:#636366;text-align:right;margin-top:2px;}
  </style></head><body>
  <div class="card">
    <img src="${v.img}">
    <div class="meta">
      <div class="site">nam-engine.com</div>
      <div class="title">${v.title}</div>
    </div>
  </div>
  <div class="bubble">${v.msg}</div>
  <div class="time">6:58 PM</div>
  </body></html>`;
}

(async () => {
  const br = await chromium.launch();
  for (const v of verticals) {
    const ctx = await br.newContext({ viewport: { width: 393, height: 852 } });
    const pg = await ctx.newPage();
    const tmpPath = `qa-artifacts/paywall-hero-fix/imessage-${v.label}.html`;
    const fs = require('fs');
    fs.writeFileSync(tmpPath, html(v));
    await pg.goto('file://' + path.resolve(tmpPath), { waitUntil: 'domcontentloaded' });
    await pg.waitForTimeout(400);
    await pg.screenshot({ path: `qa-artifacts/paywall-hero-fix/imessage-${v.label}.png` });
    console.log(v.label, 'done');
    await ctx.close();
  }
  await br.close();
})();
