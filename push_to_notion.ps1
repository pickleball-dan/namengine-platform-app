# Push NamEngine launch content to Notion Content Calendar

$DB_ID = "3c0c8498-b23f-817b-9b89-c79ece48db31"

$VERTICAL_BABY     = "213b7ae7-c32b-4b58-b987-899271025070"
$VERTICAL_PET      = "408ca4bb-c297-445d-ad82-d3f41a0d886c"
$VERTICAL_BUSINESS = "d3978a95-6882-423c-a7a7-a629e35dbddd"
$PLATFORM_IG       = "4f1ff3f9-9a8e-405b-b288-a0d464433160"
$PLATFORM_TIKTOK   = "8926985a-70e4-4dcd-8308-ce236bf6b4a7"
$STATUS_REVIEW     = "2213dbe6-64fa-4c89-aacb-c36e4390dcd8"
$OBJ_AWARENESS     = "39f33c37-bc3d-4398-ae4c-d62f9d39ebb0"
$OBJ_SAVES         = "e586dee5-ea63-4f65-b939-da1863b13914"
$OBJ_PARTICIP      = "76b61fea-60f8-4d69-80db-0a0c3f7f32ec"
$OBJ_AUTHORITY     = "eab55774-a9a1-472a-8515-285cd288b7f0"

function Invoke-NotionPatch($page_id, $properties) {
    $body = @{ properties = $properties } | ConvertTo-Json -Depth 10 -Compress
    $out = ntn api "v1/pages/$page_id" -X PATCH --data $body 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Host "PATCH OK: $page_id" }
    else { Write-Host "PATCH FAIL: $page_id | $($out | Select-Object -First 1)" }
}

function Invoke-NotionCreate($properties) {
    $body = @{ parent = @{ database_id = $DB_ID }; properties = $properties } | ConvertTo-Json -Depth 10 -Compress
    $out = ntn api v1/pages -X POST --data $body 2>&1
    if ($LASTEXITCODE -eq 0) {
        $id = ($out | ConvertFrom-Json).id
        Write-Host "CREATE OK: $id"
        return $id
    } else {
        Write-Host "CREATE FAIL: $($out | Select-Object -First 1)"
        return $null
    }
}

function tp($text) { @{ title = @(@{ text = @{ content = $text } }) } }
function dp($date) { @{ date = @{ start = $date } } }
function vp($ids)  { @{ multi_select = @($ids | ForEach-Object { @{ id = $_ } }) } }
function pp($ids)  { @{ multi_select = @($ids | ForEach-Object { @{ id = $_ } }) } }
function sp($id)   { @{ status = @{ id = $id } } }
function op($id)   { @{ select = @{ id = $id } } }
function rtp($text){ @{ rich_text = @(@{ text = @{ content = $text.Substring(0, [Math]::Min($text.Length,1999)) } }) } }

$ALL = @($VERTICAL_BABY, $VERTICAL_PET, $VERTICAL_BUSINESS)
$IGT = @($PLATFORM_IG, $PLATFORM_TIKTOK)

# Existing page IDs
$E1  = "3c0c8498-b23f-8121-a037-d05c45496141"  # Why NamEngine Exists
$E2  = "3c0c8498-b23f-8125-a04e-fc47f1517885"  # If You Love Theodore
$E8  = "3c0c8498-b23f-8160-bf97-fcf17c6dfc41"  # Arthur or August
$E5  = "3c0c8498-b23f-8192-98cd-e3e14897e049"  # Name DNA: Margot
$E11 = "3c0c8498-b23f-818f-9b96-c8ae255bf115"  # Conrad
$E14 = "3c0c8498-b23f-81ef-95e5-c360913d1d93"  # Popularity Debate
$E7  = "3c0c8498-b23f-8149-9d28-d0dd34eef35f"  # Sunday Name List

Write-Host "=== Updating existing posts ==="

Invoke-NotionPatch $E1  @{ Date=(dp "2026-09-10"); Vertical=(vp $ALL); Platform=(pp $IGT) }
Invoke-NotionPatch $E2  @{ Date=(dp "2026-09-12"); Platform=(pp $IGT) }
Invoke-NotionPatch $E5  @{ Date=(dp "2026-09-19"); Platform=(pp $IGT) }
Invoke-NotionPatch $E7  @{ Date=(dp "2026-09-24"); Platform=(pp $IGT) }
Invoke-NotionPatch $E8  @{ Date=(dp "2026-09-26"); Platform=(pp $IGT) }
Invoke-NotionPatch $E11 @{ Date=(dp "2026-10-03"); Platform=(pp $IGT) }
Invoke-NotionPatch $E14 @{ Date=(dp "2026-10-10"); Vertical=(vp @($VERTICAL_BABY,$VERTICAL_PET)); Platform=(pp $IGT) }

Write-Host "`n=== Creating new posts ==="

# Post 0 — We're Live — Sep 8
Invoke-NotionCreate @{
    "Post Title" = tp "Post 0 — We're Live: NamEngine for Baby, Pet, and Business"
    Date         = dp "2026-09-08"
    Vertical     = vp $ALL
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_AWARENESS
    CTA          = rtp "Try your free first list at nam-engine.com."
    Notes        = rtp "Hook: Finding names isn't the problem. Finding YOUR name is.`n`nCaption: A name has to do more than sound good. It has to feel right in your mouth. Fit the life it's entering. Carry a little meaning without explaining itself.`n`nNamEngine is live today for three kinds of naming decisions:`n- Baby names with depth, style, and emotional fit`n- Pet names that feel personal, not pulled from the same top-ten list`n- Business names that sound credible before you explain the idea`n`nStart with a free first list. Unlock the full experience for $4.99.`n`nnam-engine.com`n`nReel VO: Naming is strange because the problem is never that there aren't enough options. There are thousands. The problem is finding the one that feels like it already belonged to you."
}

# Day 3 — If You Love Milo (Pet) — Sep 15
Invoke-NotionCreate @{
    "Post Title" = tp "Day 3 — If You Love Milo But Want Something Less Common"
    Date         = dp "2026-09-15"
    Vertical     = vp @($VERTICAL_PET)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_SAVES
    CTA          = rtp "Save this list, or try a free first pet name list at nam-engine.com."
    Notes        = rtp "Hook: If you love Milo but want something a little less expected.`n`nCaption: Milo works for a reason — warm, easy, playful without being silly. Five alternatives:`nOtis — gentle, soulful, and slightly old-record-store charming.`nRemy — quick, clever, and polished.`nArlo — relaxed, musical, and sunny.`nNico — crisp, affectionate, and effortlessly cool.`nHugo — sturdy, warm, and a little storybook.`n`nFinding names isn't the problem. Finding YOUR name is.`n`nReel VO: If you love the name Milo for a pet, you're not alone. Try Otis, Remy, Arlo, Nico, or Hugo instead — they keep the charm but give you more room to make it yours."
}

# Day 4 — Business Name Gut Check — Sep 17
Invoke-NotionCreate @{
    "Post Title" = tp "Day 4 — The Business Name Gut Check"
    Date         = dp "2026-09-17"
    Vertical     = vp @($VERTICAL_BUSINESS)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_AUTHORITY
    CTA          = rtp "Find your business name through NamEngine at nam-engine.com."
    Notes        = rtp "Hook: You know a great business name when you hear one. Here's what makes it stick.`n`nCaption: A strong business name usually doesn't need a paragraph of defense.`n1. Easy to say — if people hesitate, they will avoid saying it.`n2. Easy to spell — a clever name no one can type is expensive.`n3. Carries meaning without explaining itself — the best names suggest a world.`n`nFinding names isn't the problem. Finding YOUR name is.`n`nReel VO: You can usually feel when a business name works before you can explain why. It sounds clean. Easy to repeat. A little meaning built in, but it doesn't try to carry the whole business plan."
}

# Day 6 — Nobody's Talking About: Luna (Pet) — Sep 22
Invoke-NotionCreate @{
    "Post Title" = tp "Day 6 — Nobody's Talking About: Luna Alternatives"
    Date         = dp "2026-09-22"
    Vertical     = vp @($VERTICAL_PET)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_SAVES
    CTA          = rtp "Save the list, then try a free pet name list at nam-engine.com."
    Notes        = rtp "Hook: Luna is everywhere. These are the alternatives nobody mentions.`n`nCaption: Luna has the whole package — soft sound, celestial meaning, easy spelling, a little mystery. Five alternatives that keep the mood:`nWren — small, graceful, nature-led.`nVesper — evening-toned, elegant, quietly dramatic.`nCleo — bright, feline, clever, full of personality.`nSable — sleek, dark, soft-edged.`nIsadora — romantic, elaborate, wearable with Izzy as nickname.`n`nReel VO: Luna is everywhere because it works. But if you want the Luna feeling without the Luna popularity, try Wren, Vesper, Cleo, Sable, or Isadora."
}

# Day 9 — The Name That Almost Wasn't (Pet) — Sep 29
Invoke-NotionCreate @{
    "Post Title" = tp "Day 9 — The Name That Almost Wasn't"
    Date         = dp "2026-09-29"
    Vertical     = vp @($VERTICAL_PET)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_PARTICIP
    CTA          = rtp "Comment the almost-name and the name that stuck. Try NamEngine for your free first pet name list."
    Notes        = rtp "Hook: What name did you almost give your pet before the real one stuck?`n`nCaption: Pet names have a funny way of revealing themselves late. Maybe they were almost:`n- Olive before they became Goose`n- Jasper before they became Beans`n- Daisy before they became Mabel`n- Apollo before they became Sock`n`nTell us: what name did you almost give your pet before the real one stuck?`n`nReel VO: Every pet has an almost-name. The name you had picked before their actual personality showed up and ruined your plan."
}

# Day 10 — Name DNA: Stripe (Business) — Oct 1
Invoke-NotionCreate @{
    "Post Title" = tp "Day 10 — Name DNA: Stripe"
    Date         = dp "2026-10-01"
    Vertical     = vp @($VERTICAL_BUSINESS)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_AUTHORITY
    CTA          = rtp "Try NamEngine for a free first business name list at nam-engine.com."
    Notes        = rtp "Hook: Name DNA: Why Stripe works as a business name.`n`nCaption: Stripe is a strong name because it does not try to explain payments in the obvious way.`nSound: Short, crisp, one syllable. Easy to say, easy to remember.`nShape: A stripe is a mark, a band, a line of movement — visual structure.`nSignal: Suggests speed, order, and clarity without trapping the company inside one feature.`nWhat it avoids: No forced tech spelling, no generic pay construction.`n`nReel VO: Stripe works because it doesn't over-explain itself. Short, crisp, visual. A good business name points in the right direction without trapping the company inside one feature."
}

# Day 12 — Sunday Pet Name List — Oct 6
Invoke-NotionCreate @{
    "Post Title" = tp "Day 12 — Sunday Pet Name List: Not the Obvious Ones"
    Date         = dp "2026-10-06"
    Vertical     = vp @($VERTICAL_PET)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_SAVES
    CTA          = rtp "Save this Sunday list, or try your free first pet name list at nam-engine.com."
    Notes        = rtp "Hook: Pet names that feel considered, not generic.`n`nCaption: This week's list:`n1. Mabel — soft, vintage, deeply lovable.`n2. Otis — soulful, sturdy, sweet.`n3. Cleo — clever, bright, expressive.`n4. Bowie — stylish, musical, confident.`n5. Fig — small, warm, quietly funny.`n6. Winnie — affectionate, sunny.`n7. Sable — sleek, elegant, mysterious.`n8. Hugo — charming, storybook-warm.`n9. Pippa — upbeat, brisk, full of motion.`n10. Rune — spare, atmospheric, quietly magical.`n`nReel VO: Pet names that feel considered, not generic: Mabel, Otis, Cleo, Bowie, Fig, Winnie, Sable, Hugo, Pippa, and Rune."
}

# Day 13 — Would You Name Your Brand This? (Business) — Oct 8
Invoke-NotionCreate @{
    "Post Title" = tp "Day 13 — Would You Name Your Brand This?"
    Date         = dp "2026-10-08"
    Vertical     = vp @($VERTICAL_BUSINESS)
    Platform     = pp $IGT
    Status       = sp $STATUS_REVIEW
    Objective    = op $OBJ_PARTICIP
    CTA          = rtp "Comment your vote: Meridian Coffee or The Daily Press. Build your own at nam-engine.com."
    Notes        = rtp "Hook: Meridian Coffee vs. The Daily Press — which one would you go to?`n`nCaption: Same category. Very different signals.`nMeridian Coffee: polished, calm, slightly elevated. Suggests craft and a serious espresso program.`nThe Daily Press: familiar, active, community-based. Suggests routine and morning rituals.`nOne says: refined pause. The other says: everyday ritual.`n`nVote in the comments: Meridian Coffee or The Daily Press.`n`nReel VO: Same category, totally different feeling. That's the point of naming: you're not just choosing words. You're choosing the promise people feel before they ever walk in."
}

Write-Host "`n=== Done === 15 posts: 7 updated + 8 created. Sep 8 — Oct 10."
