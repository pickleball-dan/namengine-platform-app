const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const mdPath = path.join(__dirname, 'docs', 'namengine-provisional-patent.md');
const outPath = path.join(__dirname, 'docs', 'namengine-provisional-patent.pdf');

const md = fs.readFileSync(mdPath, 'utf8');

// Simple markdown → HTML conversion (headings, bold, tables, lists, code, hr)
function mdToHtml(text) {
  return text
    // Escape HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headings
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // HR
    .replace(/^---$/gm, '<hr>')
    // Blockquote
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    // Table rows - handle | col | col | format
    .replace(/^\|(.+)\|$/gm, (line) => {
      const cells = line.split('|').slice(1, -1);
      if (cells.every(c => /^[-: ]+$/.test(c))) return '<tr class="sep"></tr>';
      return '<tr>' + cells.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
    })
    // Unordered list items
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Ordered list items
    .replace(/^\d+\. (.+)$/gm, '<oli>$1</oli>')
    // Paragraphs - double newlines become breaks
    .replace(/\n\n/g, '</p><p>')
    // Single newline
    .replace(/\n/g, '<br>');
}

// Better approach: process block by block
function convertMd(text) {
  const lines = text.split('\n');
  let html = '';
  let inTable = false;
  let inUl = false;
  let inOl = false;
  let tableHeader = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Headings
    if (/^#### /.test(line)) { closeLists(); html += `<h4>${inline(line.slice(5))}</h4>\n`; continue; }
    if (/^### /.test(line)) { closeLists(); html += `<h3>${inline(line.slice(4))}</h3>\n`; continue; }
    if (/^## /.test(line)) { closeLists(); html += `<h2>${inline(line.slice(3))}</h2>\n`; continue; }
    if (/^# /.test(line)) { closeLists(); html += `<h1>${inline(line.slice(2))}</h1>\n`; continue; }

    // HR
    if (/^---$/.test(line.trim())) { closeLists(); html += '<hr>\n'; continue; }

    // Blockquote
    if (/^> /.test(line)) { closeLists(); html += `<blockquote>${inline(line.slice(2))}</blockquote>\n`; continue; }

    // Table
    if (/^\|/.test(line)) {
      const cells = line.split('|').slice(1, -1).map(c => c.trim());
      if (cells.every(c => /^[-: ]+$/.test(c))) {
        if (!tableHeader) { tableHeader = true; }
        continue; // skip separator row
      }
      if (!inTable) {
        closeLists();
        inTable = true;
        html += '<table>\n';
        // First row is header
        html += '<thead><tr>' + cells.map(c => `<th>${inline(c)}</th>`).join('') + '</tr></thead>\n<tbody>\n';
        tableHeader = false;
      } else {
        html += '<tr>' + cells.map(c => `<td>${inline(c)}</td>`).join('') + '</tr>\n';
      }
      continue;
    } else if (inTable) {
      html += '</tbody></table>\n';
      inTable = false;
      tableHeader = false;
    }

    // UL
    if (/^- /.test(line)) {
      if (!inUl) { closeOl(); html += '<ul>\n'; inUl = true; }
      html += `<li>${inline(line.slice(2))}</li>\n`;
      continue;
    } else if (inUl && line.trim() !== '') {
      html += '</ul>\n'; inUl = false;
    } else if (inUl && line.trim() === '') {
      html += '</ul>\n'; inUl = false;
    }

    // OL
    if (/^\d+\. /.test(line)) {
      if (!inOl) { closeUl(); html += '<ol>\n'; inOl = true; }
      html += `<li>${inline(line.replace(/^\d+\. /, ''))}</li>\n`;
      continue;
    } else if (inOl && line.trim() !== '') {
      html += '</ol>\n'; inOl = false;
    } else if (inOl && line.trim() === '') {
      html += '</ol>\n'; inOl = false;
    }

    // Blank line
    if (line.trim() === '') { html += '<br>\n'; continue; }

    // Regular paragraph line
    html += `<p>${inline(line)}</p>\n`;
  }

  closeLists();
  if (inTable) html += '</tbody></table>\n';

  return html;

  function closeUl() { if (inUl) { html += '</ul>\n'; inUl = false; } }
  function closeOl() { if (inOl) { html += '</ol>\n'; inOl = false; } }
  function closeLists() { closeUl(); closeOl(); }
}

function inline(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>');
}

const body = convertMd(md);

const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    font-family: 'Times New Roman', Times, serif;
    font-size: 12pt;
    line-height: 1.6;
    color: #111;
    max-width: 750px;
    margin: 0 auto;
    padding: 40px 60px;
  }
  h1 { font-size: 16pt; margin-top: 28px; margin-bottom: 8px; border-bottom: 2px solid #333; padding-bottom: 4px; }
  h2 { font-size: 14pt; margin-top: 24px; margin-bottom: 6px; border-bottom: 1px solid #aaa; padding-bottom: 2px; }
  h3 { font-size: 13pt; margin-top: 18px; margin-bottom: 4px; }
  h4 { font-size: 12pt; margin-top: 14px; margin-bottom: 2px; font-style: italic; }
  p { margin: 6px 0; }
  ul, ol { margin: 6px 0 6px 24px; }
  li { margin: 3px 0; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th { background: #eee; border: 1px solid #bbb; padding: 6px 10px; text-align: left; font-size: 11pt; }
  td { border: 1px solid #ccc; padding: 5px 10px; font-size: 11pt; }
  code { font-family: Courier New, monospace; font-size: 10pt; background: #f4f4f4; padding: 1px 4px; border-radius: 2px; }
  blockquote { border-left: 4px solid #ccc; margin: 10px 0; padding: 6px 16px; color: #555; background: #fafafa; }
  hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
  strong { font-weight: bold; }
  em { font-style: italic; }
  a { color: #1a0dab; }
</style>
</head>
<body>
${body}
</body>
</html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.pdf({
    path: outPath,
    format: 'Letter',
    margin: { top: '0.75in', bottom: '0.75in', left: '0.75in', right: '0.75in' },
    printBackground: true,
  });
  await browser.close();
  console.log('PDF written to:', outPath);
})();
