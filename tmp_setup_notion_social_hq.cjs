const token = process.env.NOTION_API_TOKEN;
if (!token) throw new Error('Missing NOTION_API_TOKEN');
const NOTION_VERSION = '2022-06-28';

async function notion(path, method = 'GET', body) {
  const res = await fetch(`https://api.notion.com/v1/${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  if (!res.ok) {
    const msg = json?.message || text || `${res.status} ${res.statusText}`;
    throw new Error(`${method} ${path} failed: ${res.status} ${msg}`);
  }
  return json;
}

function titleText(page) {
  const props = page.properties || {};
  for (const prop of Object.values(props)) {
    if (prop.type === 'title') return (prop.title || []).map(t => t.plain_text || '').join('');
  }
  return '';
}

function rich(text) { return [{ type: 'text', text: { content: text } }]; }
function titleProp() { return { title: {} }; }
function dateProp() { return { date: {} }; }
function richProp() { return { rich_text: {} }; }
function urlProp() { return { url: {} }; }
function numberProp(format='number') { return { number: { format } }; }
function selectProp(options) { return { select: { options: options.map(name => ({ name })) } }; }
function multiSelectProp(options) { return { multi_select: { options: options.map(name => ({ name })) } }; }
function statusProp(options) { return { status: { options: options.map(name => ({ name })) } }; }

async function appendIntro(pageId) {
  await notion(`blocks/${pageId}/children`, 'PATCH', {
    children: [
      { object: 'block', type: 'paragraph', paragraph: { rich_text: rich('Central workspace for planning, producing, reviewing, and tracking NamEngine social launch content across Instagram, TikTok, and Pinterest.') } },
      { object: 'block', type: 'heading_2', heading_2: { rich_text: rich('Launch operating rhythm') } },
      { object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich('Use Content Calendar for dated posts and publishing status.') } },
      { object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich('Use Content Ideas for raw concepts before assigning dates.') } },
      { object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich('Use Production Queue for the copy/assets needed to make each post publishable.') } },
      { object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: rich('Use Metrics / Learnings after posting to capture saves, shares, comments, and taste insights.') } },
    ]
  });
}

async function createDatabase(parentPageId, title, properties) {
  return notion('databases', 'POST', {
    parent: { type: 'page_id', page_id: parentPageId },
    title: rich(title),
    properties,
  });
}

async function main() {
  const search = await notion('search', 'POST', {
    query: 'NamEngine Social Launch HQ',
    filter: { value: 'page', property: 'object' },
    page_size: 10,
  });
  const pages = search.results.filter(r => titleText(r).trim() === 'NamEngine Social Launch HQ');
  if (!pages.length) {
    console.log(JSON.stringify({ ok: false, reason: 'HQ page not found or connection cannot access it', found: search.results.map(r => ({ id: r.id, title: titleText(r), object: r.object })) }, null, 2));
    process.exit(2);
  }
  const page = pages[0];
  const pageId = page.id;

  await appendIntro(pageId);

  const created = [];
  created.push(await createDatabase(pageId, 'Content Calendar', {
    'Post Title': titleProp(),
    'Date': dateProp(),
    'Status': statusProp(['Idea', 'Drafting', 'Needs Review', 'Approved', 'Scheduled', 'Posted']),
    'Platform': multiSelectProp(['Instagram', 'TikTok', 'Pinterest', 'Stories']),
    'Franchise': selectProp(['Name DNA', 'If You Love…', 'Would You Name Them?', 'Nobody’s Talking About…', 'Naming Debate', 'Taste Test', 'Sunday Name List', 'Product Demo']),
    'Objective': selectProp(['Awareness', 'Authority', 'Saves/Shares', 'Participation', 'Product Understanding', 'Conversion']),
    'Vertical': multiSelectProp(['Baby', 'Pet', 'Business']),
    'CTA': richProp(),
    'Asset Link': urlProp(),
    'Notes': richProp(),
  }));

  created.push(await createDatabase(pageId, 'Content Ideas', {
    'Idea': titleProp(),
    'Franchise': selectProp(['Name DNA', 'If You Love…', 'Would You Name Them?', 'Nobody’s Talking About…', 'Naming Debate', 'Taste Test', 'Sunday Name List', 'Product Demo']),
    'Vertical': multiSelectProp(['Baby', 'Pet', 'Business']),
    'Platform Fit': multiSelectProp(['Instagram', 'TikTok', 'Pinterest', 'Stories']),
    'Priority': selectProp(['High', 'Medium', 'Low']),
    'Source / Insight': richProp(),
    'Status': statusProp(['Idea', 'Selected', 'Drafting', 'Needs Review', 'Approved', 'Used']),
  }));

  created.push(await createDatabase(pageId, 'Franchise Templates', {
    'Franchise': titleProp(),
    'Purpose': richProp(),
    'Default Format': multiSelectProp(['Reel', 'TikTok', 'Carousel', 'Story', 'Pinterest Pin']),
    'Hook Pattern': richProp(),
    'Structure': richProp(),
    'Guardrails': richProp(),
    'CTA Style': richProp(),
  }));

  created.push(await createDatabase(pageId, 'Production Queue', {
    'Post / Asset': titleProp(),
    'Related Franchise': selectProp(['Name DNA', 'If You Love…', 'Would You Name Them?', 'Nobody’s Talking About…', 'Naming Debate', 'Taste Test', 'Sunday Name List', 'Product Demo']),
    'Status': statusProp(['Briefed', 'Drafting', 'Needs Design', 'Needs Review', 'Approved', 'Scheduled']),
    'Hook': richProp(),
    'Reel / TikTok Script': richProp(),
    'Carousel Copy': richProp(),
    'Pinterest Copy': richProp(),
    'Design Notes': richProp(),
    'Reviewer Notes': richProp(),
  }));

  created.push(await createDatabase(pageId, 'Metrics / Learnings', {
    'Post': titleProp(),
    'Date Posted': dateProp(),
    'Platform': selectProp(['Instagram', 'TikTok', 'Pinterest', 'Stories']),
    'Franchise': selectProp(['Name DNA', 'If You Love…', 'Would You Name Them?', 'Nobody’s Talking About…', 'Naming Debate', 'Taste Test', 'Sunday Name List', 'Product Demo']),
    'Saves': numberProp(),
    'Shares': numberProp(),
    'Comments / Votes': numberProp(),
    'Profile Visits': numberProp(),
    'Website Visits': numberProp(),
    'Session Starts': numberProp(),
    'Learning': richProp(),
  }));

  const summary = created.map(db => ({ title: db.title?.map(t => t.plain_text).join('') || '', id: db.id, url: db.url }));
  console.log(JSON.stringify({ ok: true, pageId, pageUrl: page.url, created: summary }, null, 2));
}

main().catch(err => {
  console.error(JSON.stringify({ ok: false, error: err.message }, null, 2));
  process.exit(1);
});
