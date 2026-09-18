# Push NamEngine launch content using temp JSON files
$DB = "3c0c8498-b23f-817b-9b89-c79ece48db31"
$tmp = "$env:TEMP\ntn_payload.json"

function Patch($id, $obj) {
    $obj | ConvertTo-Json -Depth 10 -Compress | Set-Content $tmp -Encoding UTF8
    $r = Get-Content $tmp -Raw | ntn api "v1/pages/$id" -X PATCH 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host "PATCH OK: $id" } else { Write-Host "PATCH FAIL: $id | $r" }
}

function Create($obj) {
    $obj | ConvertTo-Json -Depth 10 -Compress | Set-Content $tmp -Encoding UTF8
    $r = Get-Content $tmp -Raw | ntn api v1/pages -X POST 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host "CREATE OK: $(($r | ConvertFrom-Json).id)" } else { Write-Host "CREATE FAIL: $r" }
}

$IGT = @(@{id="4f1ff3f9-9a8e-405b-b288-a0d464433160"},@{id="8926985a-70e4-4dcd-8308-ce236bf6b4a7"})
$ALL = @(@{id="213b7ae7-c32b-4b58-b987-899271025070"},@{id="408ca4bb-c297-445d-ad82-d3f41a0d886c"},@{id="d3978a95-6882-423c-a7a7-a629e35dbddd"})
$Baby = @(@{id="213b7ae7-c32b-4b58-b987-899271025070"})
$Pet  = @(@{id="408ca4bb-c297-445d-ad82-d3f41a0d886c"})
$Biz  = @(@{id="d3978a95-6882-423c-a7a7-a629e35dbddd"})
$BabyPet = @(@{id="213b7ae7-c32b-4b58-b987-899271025070"},@{id="408ca4bb-c297-445d-ad82-d3f41a0d886c"})

Write-Host "=== Updating existing posts ==="

Patch "3c0c8498-b23f-8121-a037-d05c45496141" @{properties=@{Date=@{date=@{start="2026-09-10"}};Vertical=@{multi_select=$ALL};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-8125-a04e-fc47f1517885" @{properties=@{Date=@{date=@{start="2026-09-12"}};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-8192-98cd-e3e14897e049" @{properties=@{Date=@{date=@{start="2026-09-19"}};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-8149-9d28-d0dd34eef35f" @{properties=@{Date=@{date=@{start="2026-09-24"}};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-8160-bf97-fcf17c6dfc41" @{properties=@{Date=@{date=@{start="2026-09-26"}};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-818f-9b96-c8ae255bf115" @{properties=@{Date=@{date=@{start="2026-10-03"}};Platform=@{multi_select=$IGT}}}
Patch "3c0c8498-b23f-81ef-95e5-c360913d1d93" @{properties=@{Date=@{date=@{start="2026-10-10"}};Vertical=@{multi_select=$BabyPet};Platform=@{multi_select=$IGT}}}

Write-Host "`n=== Creating 8 new posts ==="

function Title($t) { @{title=@(@{text=@{content=$t}})} }
function RT($t)    { @{rich_text=@(@{text=@{content=$t}})} }
function Sel($id)  { @{select=@{id=$id}} }
function Stat($id) { @{status=@{id=$id}} }

$REV = "2213dbe6-64fa-4c89-aacb-c36e4390dcd8"
$OA  = "39f33c37-bc3d-4398-ae4c-d62f9d39ebb0"
$OS  = "e586dee5-ea63-4f65-b939-da1863b13914"
$OP  = "76b61fea-60f8-4d69-80db-0a0c3f7f32ec"
$OAu = "eab55774-a9a1-472a-8515-285cd288b7f0"

# Post 0 - Sep 8
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Post 0 - We're Live: NamEngine for Baby, Pet, and Business"
    Date=@{date=@{start="2026-09-08"}};Vertical=@{multi_select=$ALL};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OA
    CTA=RT "Try your free first list at nam-engine.com."
    Notes=RT "Hook: Finding names isn't the problem. Finding YOUR name is. Caption: NamEngine is live today for Baby, Pet, and Business names. Free first list, full access for $4.99. Reel VO: The problem is never that there aren't enough options. There are thousands. The problem is finding the one that feels like it already belonged to you."
}}

# Day 3 - Pet - Sep 15
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 3 - If You Love Milo But Want Something Less Common"
    Date=@{date=@{start="2026-09-15"}};Vertical=@{multi_select=$Pet};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OS
    CTA=RT "Save this list, or try a free first pet name list at nam-engine.com."
    Notes=RT "Hook: If you love Milo but want something a little less expected. Five alternatives with similar warmth: Otis, Remy, Arlo, Nico, Hugo. Reel VO: If you love the name Milo for a pet, you are not alone. It is friendly and easy to say, which is exactly why it is everywhere. Try Otis, Remy, Arlo, Nico, or Hugo instead - they keep the charm but give you more room to make it yours."
}}

# Day 4 - Business - Sep 17
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 4 - The Business Name Gut Check"
    Date=@{date=@{start="2026-09-17"}};Vertical=@{multi_select=$Biz};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OAu
    CTA=RT "Find your business name through NamEngine at nam-engine.com."
    Notes=RT "Hook: You know a great business name when you hear one. Here's what makes it stick. Three checks: 1. Easy to say. 2. Easy to spell. 3. Carries meaning without explaining itself. Reel VO: You can usually feel when a business name works before you can explain why. It sounds clean, easy to repeat, with meaning built in but not dragging the whole pitch deck behind it."
}}

# Day 6 - Pet - Sep 22
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 6 - Nobody's Talking About: Luna Alternatives"
    Date=@{date=@{start="2026-09-22"}};Vertical=@{multi_select=$Pet};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OS
    CTA=RT "Save the list, then try a free pet name list at nam-engine.com."
    Notes=RT "Hook: Luna is everywhere. These are the alternatives nobody mentions. Five alternatives: Wren, Vesper, Cleo, Sable, Isadora. All keep the soft celestial mood with more room to feel personal. Reel VO: Luna is everywhere because it works. But if you want the Luna feeling without the Luna popularity, try Wren, Vesper, Cleo, Sable, or Isadora."
}}

# Day 9 - Pet - Sep 29
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 9 - The Name That Almost Wasn't"
    Date=@{date=@{start="2026-09-29"}};Vertical=@{multi_select=$Pet};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OP
    CTA=RT "Comment the almost-name and the name that stuck. Try NamEngine for your free first pet name list."
    Notes=RT "Hook: What name did you almost give your pet before the real one stuck? Examples: Olive became Goose. Jasper became Beans. Daisy became Mabel. Apollo became Sock. Reel VO: Every pet has an almost-name. The name you picked before their actual personality showed up and ruined your plan."
}}

# Day 10 - Business - Oct 1
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 10 - Name DNA: Stripe"
    Date=@{date=@{start="2026-10-01"}};Vertical=@{multi_select=$Biz};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OAu
    CTA=RT "Try NamEngine for a free first business name list at nam-engine.com."
    Notes=RT "Hook: Name DNA: Why Stripe works as a business name. Sound: short, crisp, one syllable. Shape: linear, clean, a mark or band. Signal: suggests speed and order without trapping the company. What it avoids: no forced tech spelling, no generic pay construction. Reel VO: Stripe works because it does not over-explain itself. A good business name points in the right direction without trapping the company inside one feature."
}}

# Day 12 - Pet - Oct 6
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 12 - Sunday Pet Name List: Not the Obvious Ones"
    Date=@{date=@{start="2026-10-06"}};Vertical=@{multi_select=$Pet};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OS
    CTA=RT "Save this Sunday list, or try your free first pet name list at nam-engine.com."
    Notes=RT "Hook: Pet names that feel considered, not generic. The list: Mabel, Otis, Cleo, Bowie, Fig, Winnie, Sable, Hugo, Pippa, Rune. Reel VO: Pet names that feel considered, not generic. The best pet names are easy to say but still feel like they belong to one specific animal, not every dog park and every list on the internet."
}}

# Day 13 - Business - Oct 8
Create @{parent=@{database_id=$DB};properties=@{
    "Post Title"=Title "Day 13 - Would You Name Your Brand This?"
    Date=@{date=@{start="2026-10-08"}};Vertical=@{multi_select=$Biz};Platform=@{multi_select=$IGT}
    Status=Stat $REV;Objective=Sel $OP
    CTA=RT "Comment your vote: Meridian Coffee or The Daily Press. Build your own at nam-engine.com."
    Notes=RT "Hook: Meridian Coffee vs. The Daily Press - which one would you go to? Meridian Coffee: polished, calm, slightly elevated. The Daily Press: familiar, active, community-based. One says refined pause. The other says everyday ritual. Vote in the comments. Reel VO: Same category, totally different feeling. You are not just choosing words. You are choosing the promise people feel before they ever walk in."
}}

Write-Host "`n=== Done === 15 posts total. Launch Sep 8, daily through Oct 10."
