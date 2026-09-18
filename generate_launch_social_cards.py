from pathlib import Path
import html

OUT = Path('design-references/social-launch/day1-7-launch-cards')
OUT.mkdir(parents=True, exist_ok=True)

INK = '#0D2540'
CREAM = '#FBF8F1'
PAPER = '#FFFFFF'
MUTED = '#607086'
CORAL = '#FF5233'
DEEP = '#E1421F'
BLUSH = '#F7DAD6'
SAGE = '#DDEBDD'
TEAL = '#0F8F73'
GOLD = '#B9860B'
LINE = '#DDE3EC'


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size=44, weight=700, fill=INK, anchor='start', family="Inter, Arial, sans-serif", style=''):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" {style}>{esc(s)}</text>'


def serif(x, y, s, size=80, weight=700, fill=INK, anchor='start', italic=False):
    style = 'font-style="italic"' if italic else ''
    return text(x, y, s, size, weight, fill, anchor, "Georgia, 'Times New Roman', serif", style)


def lines(x, y, items, size, lh=1.08, weight=700, fill=INK, family="Georgia, 'Times New Roman', serif", italic=False, anchor='start'):
    style = 'font-style="italic"' if italic else ''
    tspans = []
    for i, item in enumerate(items):
        dy = 0 if i == 0 else round(size * lh, 1)
        tspans.append(f'<tspan x="{x}" dy="{dy}">{esc(item)}</tspan>')
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" {style}>{"".join(tspans)}</text>'


def rect(x, y, w, h, r=36, fill=PAPER, stroke='rgba(13,37,64,0.12)', sw=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def pill(x, y, label, w=None, fill=PAPER, fg=INK, size=26):
    w = w or max(150, len(label) * 16 + 54)
    h = 58
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="29" fill="{fill}" stroke="rgba(13,37,64,0.12)"/><text x="{x+w/2}" y="{y+38}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="{size}" font-weight="900" fill="{fg}">{esc(label)}</text>'


def logo(x=64, y=54, scale=0.25):
    return f'''
    <g transform="translate({x},{y}) scale({scale})">
      <rect width="1500" height="240" fill="none"/>
      <g transform="translate(20,20)">
        <path d="M110 10 C52 10 10 47 10 103 C10 153 45 188 92 196 L74 224 L119 198 C177 197 220 160 220 103 C220 56 184 20 137 12" fill="none" stroke="{INK}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        <text x="116" y="156" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="132" font-weight="700" fill="{INK}">n</text>
        <path d="M164 24 C164 10 182 4 192 16 C203 4 221 10 221 24 C221 40 192 58 192 58 C192 58 164 40 164 24Z" fill="{CORAL}"/>
      </g>
      <text x="275" y="150" font-family="Georgia, 'Times New Roman', serif" font-size="110" font-weight="700" fill="{INK}">NamEngine</text>
      <text x="930" y="150" font-family="Georgia, 'Times New Roman', serif" font-size="110" font-weight="700" fill="{CORAL}">Baby</text>
    </g>'''


def bg(w, h, variant):
    # Premium but louder than the previous quiet cards: big warm fields, editorial dots, and coral emphasis.
    return f'''
    <rect width="100%" height="100%" fill="{CREAM}"/>
    <circle cx="{w-110}" cy="120" r="260" fill="{BLUSH}" opacity="0.78"/>
    <circle cx="94" cy="{h-92}" r="250" fill="{SAGE}" opacity="0.70"/>
    <circle cx="{w*0.78:.0f}" cy="{h*0.78:.0f}" r="115" fill="{CORAL}" opacity="0.10"/>
    <path d="M-40 {h*0.34:.0f} C {w*0.22:.0f} {h*0.24:.0f}, {w*0.52:.0f} {h*0.42:.0f}, {w+40} {h*0.30:.0f}" fill="none" stroke="{CORAL}" stroke-width="4" opacity="0.16"/>
    <path d="M{w-210} {h-250} l22 44 l48 7 l-35 34 l8 48 l-43 -23 l-43 23 l8 -48 l-35 -34 l48 -7 z" fill="{CORAL}" opacity="0.16"/>
    '''


def footer(w, h):
    y = h - (225 if h >= 1600 else 78)
    return f'{text(72, y, "@namengine.app", 32 if h >= 1600 else 30, 950)}{text(w-72, y, "nam-engine.com", 30 if h >= 1600 else 28, 850, MUTED, anchor="end")}'


def shell(w, h, body, variant='a'):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  {bg(w,h,variant)}
  {logo(64,58,0.255 if h < 1600 else 0.30)}
  {body}
  {footer(w,h)}
</svg>'''


def write(name, w, h, body):
    p = OUT / f'{name}.svg'
    p.write_text(shell(w, h, body), encoding='utf-8')


def day1(w, h):
    top = 300 if h < 1600 else 430
    card_y = 760 if h < 1600 else 1065
    return f'''
    {lines(72, top+55, ['You don’t need', '10,000 baby names.'], 78 if h < 1600 else 92, 1.05)}
    {lines(72, top+245 if h < 1600 else top+285, ['You need', 'the right 10.'], 90 if h < 1600 else 116, 1.00, fill=CORAL, italic=True)}
    {rect(72, card_y, w-144, 280 if h < 1600 else 365, 42)}
    {text(120, card_y+72, 'NamEngine is taste-first baby naming.', 35 if h < 1600 else 43, 900)}
    {text(120, card_y+135, 'Less scrolling. More “that’s the one.”', 30 if h < 1600 else 37, 650, MUTED)}
    {pill(120, card_y+190 if h < 1600 else card_y+250, 'curated', fill=BLUSH)}{pill(335, card_y+190 if h < 1600 else card_y+250, 'personal', fill=SAGE)}{pill(550, card_y+190 if h < 1600 else card_y+250, 'saveable')}
    '''


def day2(w, h):
    top = 292 if h < 1600 else 520
    return f'''
    {serif(72, top+48, 'Theodore', 126 if h < 1600 else 156)}
    {text(78, top+112, 'but want less “everyone has it” energy', 34 if h < 1600 else 42, 850, CORAL)}
    {rect(72, top+215, w-144, 470 if h < 1600 else 650, 44)}
    {serif(120, top+315, 'Arthur', 58 if h < 1600 else 76)}{pill(w-330, top+265, 'sturdy', fill=SAGE)}
    {serif(120, top+425, 'Frederick', 58 if h < 1600 else 76)}{pill(w-330, top+375, 'old-soul', fill=BLUSH)}
    {serif(120, top+535, 'Edmund', 58 if h < 1600 else 76)}{pill(w-330, top+485, 'rooted')}
    {text(w/2, top+770 if h >= 1600 else top+755, 'Save this if Theodore is almost right.', 34 if h < 1600 else 44, 950, CORAL, anchor='middle')}
    '''


def day3(w, h):
    top = 300 if h < 1600 else 455
    if h >= 1600:
        card_y = 850
        card_h = 555
        return f'''
        {serif(w/2, top+40, 'Arthur', 136, anchor='middle')}
        {text(w/2, top+120, 'or', 46, 950, CORAL, anchor='middle')}
        {serif(w/2, top+245, 'August?', 136, anchor='middle')}
        {rect(72, card_y, (w-176)/2, card_h, 42, PAPER)}
        {rect((w/2)+16, card_y, (w-176)/2, card_h, 42, PAPER)}
        {text(132, card_y+105, 'Arthur', 68, 950)}
        {text((w/2)+76, card_y+105, 'August', 68, 950)}
        {text(132, card_y+190, 'sturdy', 43, 850, MUTED)}
        {text(132, card_y+270, 'storied', 43, 850, MUTED)}
        {text(132, card_y+350, 'grounded', 43, 850, MUTED)}
        {text((w/2)+76, card_y+190, 'warm', 43, 850, MUTED)}
        {text((w/2)+76, card_y+270, 'polished', 43, 850, MUTED)}
        {text((w/2)+76, card_y+350, 'golden', 43, 850, MUTED)}
        {text(w/2, card_y+card_h+90, 'Same vintage energy. Totally different kid.', 42, 950, INK, anchor='middle')}
        '''
    card_y = top + 260
    card_h = 430
    return f'''
    {serif(72, top+48, 'Arthur', 104)}
    {text(w/2, top+42, 'or', 38, 950, CORAL, anchor='middle')}
    {serif(w-72, top+48, 'August?', 104, anchor='end')}
    {rect(72, card_y, (w-176)/2, card_h, 42, PAPER)}
    {rect((w/2)+16, card_y, (w-176)/2, card_h, 42, PAPER)}
    {text(132, card_y+105, 'Arthur', 52, 950)}
    {text((w/2)+76, card_y+105, 'August', 52, 950)}
    {text(132, card_y+175, 'sturdy', 34, 850, MUTED)}
    {text(132, card_y+240, 'storied', 34, 850, MUTED)}
    {text(132, card_y+305, 'grounded', 34, 850, MUTED)}
    {text((w/2)+76, card_y+175, 'warm', 34, 850, MUTED)}
    {text((w/2)+76, card_y+240, 'polished', 34, 850, MUTED)}
    {text((w/2)+76, card_y+305, 'golden', 34, 850, MUTED)}
    {text(w/2, card_y+card_h+95, 'Same vintage energy. Totally different kid.', 34, 950, INK, anchor='middle')}
    '''


def day4(w, h):
    top = 292 if h < 1600 else 505
    cy = top + 300
    traits = [('VINTAGE', BLUSH), ('TAILORED', SAGE), ('STYLISH', PAPER), ('WARM', BLUSH)]
    trait_svg = ''
    x = 96
    y = cy + 48
    for i, (label, fill) in enumerate(traits):
        row = i // 2
        col = i % 2
        trait_svg += pill(x + col*440, y + row*96, label, 350, fill=fill, size=24)
    return f'''
    {serif(72, top+65, 'Margot', 142 if h < 1600 else 178)}
    {text(78, top+132, 'vintage roots, modern shape', 34 if h < 1600 else 44, 850, MUTED)}
    {rect(72, cy, w-144, 285 if h < 1600 else 405, 44)}
    {trait_svg}
    {text(120, cy+245 if h < 1600 else cy+330, 'Distinctive without being difficult.', 32 if h < 1600 else 42, 900)}
    '''


def day5(w, h):
    top = 292 if h < 1600 else 430
    return f'''
    {lines(72, top+40, ['Conrad is', 'the classic boy name', 'everyone forgot.'], 67 if h < 1600 else 86, 1.03)}
    {rect(72, top+365 if h < 1600 else top+500, w-144, 330 if h < 1600 else 460, 44)}
    {text(120, top+455 if h < 1600 else top+615, 'Established, not overexposed.', 34 if h < 1600 else 46, 900)}
    {text(120, top+535 if h < 1600 else top+720, 'Strong, not harsh.', 34 if h < 1600 else 46, 900)}
    {text(120, top+615 if h < 1600 else top+825, 'Traditional, not predictable.', 34 if h < 1600 else 46, 900)}
    {text(72, top+785 if h < 1600 else top+1065, 'Would you add Conrad to the list?', 36 if h < 1600 else 46, 950, CORAL)}
    '''


def day6(w, h):
    top = 292 if h < 1600 else 420
    card_y = top + 300
    card_h = 390 if h < 1600 else 560
    row1 = card_y + (108 if h < 1600 else 145)
    row2 = card_y + (238 if h < 1600 else 320)
    big = 62 if h < 1600 else 84
    small = 28 if h < 1600 else 36
    return f'''
    {lines(72, top+45, ['Would popularity', 'stop you?'], 90 if h < 1600 else 104, 1.02)}
    {rect(72, card_y, w-144, card_h, 44)}
    {serif(120, row1, 'Common', big, fill=CORAL, italic=True)}
    {text(120, row1+58 if h < 1600 else row1+76, 'does not mean wrong', small, 950, MUTED)}
    {serif(120, row2, 'Rare', big, fill=CORAL, italic=True)}
    {text(120, row2+58 if h < 1600 else row2+76, 'does not mean right', small, 950, MUTED)}
    {text(w-120, row2+58 if h < 1600 else row2+76, 'Fit > rank', small, 950, INK, anchor='end')}
    {text(72, top+805 if h < 1600 else top+1005, 'What’s your rule?', 38 if h < 1600 else 50, 950, CORAL)}
    '''


def day7(w, h):
    top = 292 if h < 1600 else 500
    card_y = top + 300
    card_h = 525 if h < 1600 else 770
    name_size = 40 if h < 1600 else 54
    gap = 58 if h < 1600 else 82
    return f'''
    {lines(72, top+40, ['Classic names', 'that still feel', 'undiscovered.'], 70 if h < 1600 else 90, 1.02)}
    {rect(72, card_y, w-144, card_h, 44)}
    {text(125, card_y+76, 'GIRLS', 24 if h < 1600 else 30, 950, CORAL)}
    {text(595, card_y+76, 'BOYS', 24 if h < 1600 else 30, 950, CORAL)}
    {serif(125, card_y+150, 'Celia', name_size)}
    {serif(125, card_y+150+gap, 'Louisa', name_size)}
    {serif(125, card_y+150+gap*2, 'Beatrice', name_size)}
    {serif(125, card_y+150+gap*3, 'Harriet', name_size)}
    {serif(125, card_y+150+gap*4, 'Susannah', name_size)}
    {serif(595, card_y+150, 'Arthur', name_size)}
    {serif(595, card_y+150+gap, 'Frederick', name_size)}
    {serif(595, card_y+150+gap*2, 'Edmund', name_size)}
    {serif(595, card_y+150+gap*3, 'Conrad', name_size)}
    {serif(595, card_y+150+gap*4, 'Hugo', name_size)}
    {text(w/2, card_y+card_h+75, 'Rooted. Wearable. Less expected.', 32 if h < 1600 else 42, 950, INK, anchor='middle')}
    '''


DAYS = [day1, day2, day3, day4, day5, day6, day7]
for i, fn in enumerate(DAYS, start=1):
    write(f'day-{i:02d}-instagram-4x5-launch', 1080, 1350, fn(1080, 1350))
    write(f'day-{i:02d}-tiktok-9x16-launch', 1080, 1920, fn(1080, 1920))

(OUT / 'README.md').write_text('''# NamEngine Day 1-7 Launch Cards

Local review exports for stronger Instagram 4:5 and TikTok/Reels 9:16 launch cards.

- Instagram files: `day-XX-instagram-4x5-launch.png`
- TikTok/Reels files: `day-XX-tiktok-9x16-launch.png`
- Handle on cards: `@namengine.app`
- Site on cards: `nam-engine.com`

These are local preview assets only until approved.
''', encoding='utf-8')

print(f'Wrote {len(list(OUT.glob("*.svg")))} launch SVGs to {OUT.resolve()}')
