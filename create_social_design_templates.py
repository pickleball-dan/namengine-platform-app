from pathlib import Path
import html
import textwrap

OUT = Path('design-references/social-launch/batch1-canva-templates')
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    'ink': '#0D2540',
    'cream': '#FBF8F1',
    'paper': '#FFFFFF',
    'muted': '#607086',
    'line': '#DDE3EC',
    # Social templates use stronger in-app accent values so small Canva/social
    # previews feel consistent with the product UI.
    'coral': '#FF5233',
    'teal': '#0F8F73',
    'gold': '#B9860B',
    'blush': '#F7DAD6',
    'sage': '#DDEBDD',
}

VERTICAL_PALETTES = {
    'baby': {
        'accent': '#FF5233',
        'deep': '#E1421F',
        'soft': '#F7DAD6',
        'label': 'Baby',
    },
    'pet': {
        'accent': '#F2B84B',
        'deep': '#7A5000',
        'support': '#2F9486',
        'soft': '#FFF3D2',
        'label': 'Pet',
    },
    'business': {
        'accent': '#29344F',
        'deep': '#162C58',
        'support': '#0F8F73',
        'soft': '#E7ECF6',
        'label': 'Business',
    },
}

def esc(s):
    return html.escape(str(s), quote=True)

def svg_wrap(w, h, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="100%" height="100%" fill="{COLORS['cream']}"/>
  <circle cx="{w-120}" cy="130" r="220" fill="{COLORS['blush']}" opacity="0.50"/>
  <circle cx="90" cy="{h-120}" r="210" fill="{COLORS['sage']}" opacity="0.48"/>
  {body}
</svg>'''

def text(x, y, s, size=44, weight=500, fill=None, anchor='start', family="Inter, Arial, sans-serif", style=''):
    fill = fill or COLORS['ink']
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" {style}>{esc(s)}</text>'

def tspan_lines(x, y, lines, size, line_height=1.16, weight=700, fill=None, family="Georgia, 'Times New Roman', serif", italic=False, anchor='start'):
    fill = fill or COLORS['ink']
    style = 'font-style="italic"' if italic else ''
    spans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else size * line_height
        spans.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" {style}>{"".join(spans)}</text>'

def wrapped(x, y, s, chars, size, line_height=1.18, weight=700, fill=None, family="Georgia, 'Times New Roman', serif", italic=False):
    lines = textwrap.wrap(s, width=chars, break_long_words=False)
    return tspan_lines(x, y, lines, size, line_height, weight, fill, family, italic)

def serif(x, y, s, size=72, weight=700, fill=None, anchor='start', italic=False):
    return text(x, y, s, size, weight, fill, anchor, "Georgia, 'Times New Roman', serif", 'font-style="italic"' if italic else '')

def logo(x=60, y=56, scale=0.30):
    # Exact NamEngine Baby logo geometry/proportions from static/images/namengine-baby.svg.
    # Scale the whole 1500x240 lockup together; do not rebuild the wordmark manually.
    return f'''
    <g transform="translate({x},{y}) scale({scale})">
      <rect width="1500" height="240" fill="none"/>
      <g transform="translate(20,20)">
        <path d="M110 10 C52 10 10 47 10 103 C10 153 45 188 92 196 L74 224 L119 198 C177 197 220 160 220 103 C220 56 184 20 137 12" fill="none" stroke="{COLORS['ink']}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        <text x="116" y="156" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="132" font-weight="700" fill="{COLORS['ink']}">n</text>
        <path d="M164 24 C164 10 182 4 192 16 C203 4 221 10 221 24 C221 40 192 58 192 58 C192 58 164 40 164 24Z" fill="{COLORS['coral']}"/>
      </g>
      <text x="275" y="150" font-family="Georgia, 'Times New Roman', serif" font-size="110" font-weight="700" fill="{COLORS['ink']}">NamEngine</text>
      <text x="930" y="150" font-family="Georgia, 'Times New Roman', serif" font-size="110" font-weight="700" fill="{COLORS['coral']}">Baby</text>
    </g>
    '''

def pill(x, y, w, h, label, fill=None, size=25):
    fill = fill or COLORS['paper']
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" stroke="{COLORS["line"]}"/><text x="{x+w/2}" y="{y+h/2+size*0.35}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="{size}" font-weight="800" fill="{COLORS["ink"]}">{esc(label)}</text>'

def card(x, y, w, h, rx=34, fill=None):
    fill = fill or COLORS['paper']
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="rgba(13,37,64,0.12)"/>'

def write_svg(name, w, h, body):
    p = OUT / f'{name}.svg'
    p.write_text(svg_wrap(w, h, body), encoding='utf-8')
    return p

# Core templates
write_svg('template-01-reel-text-card-9x16', 1080, 1920, f'''
{logo(70,70,0.34)}
{tspan_lines(90,390,['Finding names', 'isn’t the problem.'],84,1.16)}
{tspan_lines(90,620,['Finding', 'YOUR name is.'],92,1.14,fill=COLORS['coral'],italic=True)}
{card(90,930,900,420,38)}
{text(140,1010,'Most naming tools give you more names.',37,800)}
{text(140,1090,'NamEngine is built to understand',37,500,COLORS['muted'])}
{text(140,1150,'what actually fits your taste.',37,500,COLORS['muted'])}
{pill(140,1260,260,72,'Taste-first',COLORS['sage'])}{pill(430,1260,270,72,'Curated',COLORS['blush'])}
''')

write_svg('template-02-if-you-love-carousel-4x5',1080,1350, f'''
{logo(60,56,0.30)}
{text(76,240,'IF YOU LOVE',30,900,COLORS['muted'])}
{serif(76,368,'Theodore',116)}
{text(80,450,'but want something less common…',38,650)}
{card(70,548,940,565,34)}
{serif(120,640,'Frederick',54)}{pill(690,594,210,56,'old-soul',COLORS['sage'],23)}
{text(120,712,'substantial, traditional, nickname-rich',29,600,COLORS['muted'])}
{serif(120,815,'Arthur',54)}{pill(690,769,210,56,'storied',COLORS['blush'],23)}
{text(120,887,'classic, sturdy, quietly serious',29,600,COLORS['muted'])}
{serif(120,990,'Edmund',54)}{pill(690,944,210,56,'grounded',COLORS['sage'],23)}
{text(120,1062,'literary, rooted, less expected',29,600,COLORS['muted'])}
{text(76,1242,'Save this if Theodore is on your list.',30,800)}
''')

write_svg('template-03-would-you-split-poll-9x16',1080,1920, f'''
{logo(70,70,0.34)}
{text(90,275,'WOULD YOU NAME THEM',31,900,COLORS['muted'])}
{serif(90,420,'Arthur',96)}
{text(540,420,'or',38,900,COLORS['coral'],anchor='middle')}
{serif(990,420,'August?',96,anchor='end')}
{card(82,570,430,760,42)}
{serif(150,760,'Arthur',76)}
{pill(145,850,250,64,'sturdy',COLORS['sage'])}
{pill(145,935,250,64,'storied',COLORS['blush'])}
{pill(145,1020,250,64,'classic')}
{card(568,570,430,760,42)}
{serif(630,760,'August',76)}
{pill(635,850,250,64,'warm',COLORS['blush'])}
{pill(635,935,250,64,'polished',COLORS['sage'])}
{pill(635,1020,250,64,'grand')}
{text(540,1510,'No overthinking. Which one?',46,900,anchor='middle')}
''')

write_svg('template-04-name-dna-explainer-9x16',1080,1920, f'''
{logo(70,70,0.34)}
{text(90,290,'NAME DNA',34,900,COLORS['coral'])}
{serif(90,470,'Margot',128)}
{text(95,550,'vintage and modern at the same time',36,700,COLORS['muted'])}
{card(90,720,900,145,28)}{text(140,810,'Rooted in Margaret',40,800)}
{card(90,910,900,145,28)}{text(140,1000,'Clean final “o” sound',40,800)}
{card(90,1100,900,145,28)}{text(140,1190,'Tailored, stylish, warm',40,800)}
{card(90,1290,900,145,28)}{text(140,1380,'Distinctive without being difficult',40,800)}
{text(90,1650,'What does Margot feel like to you?',42,900)}
''')

write_svg('template-05-nobodys-talking-feature-4x5',1080,1350, f'''
{logo(60,56,0.30)}
{text(76,225,'NOBODY’S TALKING ABOUT',30,900,COLORS['muted'])}
{serif(76,400,'Conrad',130)}
{card(70,520,940,500,36)}
{text(120,610,'Established without feeling overexposed.',34,800)}
{text(120,700,'Strong, but not harsh.',34,800)}
{text(120,790,'Traditional, but not predictable.',34,800)}
{text(120,880,'Grounded, intelligent, quietly distinctive.',34,800)}
{pill(120,1085,210,62,'classic',COLORS['sage'])}{pill(355,1085,245,62,'substantial',COLORS['blush'])}{pill(625,1085,250,62,'less obvious')}
{text(76,1240,'Would you add Conrad to the list?',31,800)}
''')

write_svg('template-06-sunday-name-list-4x5',1080,1350, f'''
{logo(60,56,0.30)}
{text(76,225,'SUNDAY NAME LIST',30,900,COLORS['coral'])}
{tspan_lines(76,350,['Classic names','beyond the obvious'],82,1.14)}
{card(76,560,420,560,34)}{card(584,560,420,560,34)}
{serif(130,650,'Celia',52)}{serif(130,740,'Louisa',52)}{serif(130,830,'Beatrice',52)}{serif(130,920,'Harriet',52)}{serif(130,1010,'Susannah',52)}
{serif(640,650,'Arthur',52)}{serif(640,740,'Frederick',52)}{serif(640,830,'Edmund',52)}{serif(640,920,'Conrad',52)}{serif(640,1010,'Hugo',52)}
{text(540,1240,'Rooted. Wearable. Less obvious.',34,800,anchor='middle')}
''')

# Day-specific covers with manual safe line breaks.
days = [
    {
        'name': 'day-01-why-namengine-exists-preview',
        'a': ['Finding names', 'isn’t the problem.'],
        'b': ['Finding', 'YOUR name is.'],
        'body': f"""{text(126,875,'NamEngine understands why names work.',34,800)}
        {text(126,948,'Taste-first. Personal. Curated.',29,650,COLORS['muted'])}
        {pill(126,1018,220,58,'warm',COLORS['blush'],23)}{pill(370,1018,250,58,'editorial',COLORS['sage'],23)}{pill(645,1018,230,58,'saveable',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-02-if-you-love-theodore-preview',
        'a': ['If you love'],
        'b': ['Theodore'],
        'body': f"""{text(126,870,'Try names with the same old-soul warmth.',32,800)}
        {serif(126,958,'Arthur · Frederick · Edmund',40)}
        {pill(126,1018,220,58,'warm',COLORS['blush'],23)}{pill(370,1018,250,58,'classic',COLORS['sage'],23)}{pill(645,1018,230,58,'less common',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-03-arthur-august-preview',
        'a': ['Arthur'],
        'b': ['or August?'],
        'body': f"""{text(126,870,'Two classics. Very different energy.',32,800)}
        {serif(126,958,'Arthur = sturdy  ·  August = warm',38)}
        {pill(126,1018,220,58,'vote',COLORS['blush'],23)}{pill(370,1018,250,58,'compare',COLORS['sage'],23)}{pill(645,1018,230,58,'save',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-04-name-dna-margot-preview',
        'a': ['Name DNA:'],
        'b': ['Margot'],
        'body': f"""{text(126,870,'Vintage roots. Modern shape.',32,800)}
        {text(126,942,'Tailored, stylish, and warm without trying too hard.',28,650,COLORS['muted'])}
        {pill(126,1018,220,58,'vintage',COLORS['blush'],23)}{pill(370,1018,250,58,'modern',COLORS['sage'],23)}{pill(645,1018,230,58,'tailored',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-05-conrad-preview',
        'a': ['Nobody’s talking', 'about'],
        'b': ['Conrad'],
        'body': f"""{text(126,870,'Established without feeling overexposed.',32,800)}
        {text(126,942,'Strong, traditional, and quietly distinctive.',28,650,COLORS['muted'])}
        {pill(126,1018,220,58,'classic',COLORS['blush'],23)}{pill(370,1018,250,58,'substantial',COLORS['sage'],23)}{pill(645,1018,230,58,'rare',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-06-popularity-debate-preview',
        'a': ['Would popularity', 'stop you'],
        'b': ['from using it?'],
        'body': f"""{text(126,870,'A name can be common and still be yours.',32,800)}
        {text(126,942,'Fit matters more than rank alone.',28,650,COLORS['muted'])}
        {pill(126,1018,220,58,'debate',COLORS['blush'],23)}{pill(370,1018,250,58,'taste',COLORS['sage'],23)}{pill(645,1018,230,58,'fit',COLORS['paper'],23)}""",
    },
    {
        'name': 'day-07-classic-list-preview',
        'a': ['Ten classic names'],
        'b': ['beyond the obvious'],
        'card_y': 760,
        'card_h': 410,
        'body': f"""{text(126,835,'Girls',24,900,COLORS['muted'])}
        {text(596,835,'Boys',24,900,COLORS['muted'])}
        {serif(126,902,'Celia',38)}
        {serif(126,960,'Louisa',38)}
        {serif(126,1018,'Beatrice',38)}
        {serif(126,1076,'Harriet',38)}
        {serif(126,1134,'Susannah',38)}
        {serif(596,902,'Arthur',38)}
        {serif(596,960,'Frederick',38)}
        {serif(596,1018,'Edmund',38)}
        {serif(596,1076,'Conrad',38)}
        {serif(596,1134,'Hugo',38)}""",
    },
]
for day in days:
    card_y = day.get('card_y', 790)
    card_h = day.get('card_h', 300)
    write_svg(day['name'],1080,1350, f'''
    {logo(60,56,0.30)}
    {tspan_lines(76,360,day['a'],78,1.12)}
    {tspan_lines(76,610,day['b'],82,1.12,fill=COLORS['coral'],italic=True)}
    {card(76,card_y,928,card_h,36)}
    {day['body']}
    {text(76,1240,'@namengine.APP',30,900)}
    ''')

(OUT/'README.md').write_text('''# NamEngine Batch 1 Canva Template Pack

These SVGs are Canva-importable reference templates and mockups. Generated with safer text wrapping and compact logo spacing.

## Core templates
1. template-01-reel-text-card-9x16.svg
2. template-02-if-you-love-carousel-4x5.svg
3. template-03-would-you-split-poll-9x16.svg
4. template-04-name-dna-explainer-9x16.svg
5. template-05-nobodys-talking-feature-4x5.svg
6. template-06-sunday-name-list-4x5.svg

## Day previews
- day-01 through day-07 SVGs are first-pass visual directions for Batch 1.
''', encoding='utf-8')

print(f'Wrote {len(list(OUT.glob("*.svg")))} SVG files to {OUT.resolve()}')
