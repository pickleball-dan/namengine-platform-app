import pathlib

p = pathlib.Path(r'C:\Users\dnorm\.openclaw\workspace\namengine_platform_app\static\js\baby-intake-polish.js')
content = p.read_text(encoding='utf-8')

old1 = "cultural_context: \"We're narrowing in on the right fit.\","
new1 = "cultural_context: \"\u202are narrowing in on the right fit.\",".replace("\u202are", "\u2019re")

old2 = "cultural_heritage: \"We're discovering the kinds of names you'll love.\","
new2 = "cultural_heritage: \"\u2019re discovering the kinds of names you\u2019ll love.\",".replace("\u2019re", "We\u2019re")

# simpler approach
content = content.replace(
    'cultural_context: "We\'re narrowing in on the right fit.",',
    'cultural_context: "We\u2019re narrowing in on the right fit.",'
).replace(
    "cultural_heritage: \"We're discovering the kinds of names you'll love.\",",
    "cultural_heritage: \"\u2019re discovering the kinds of names you\u2019ll love.\",".replace("\u2019re", "We\u2019re").replace("you\u2019ll", "you\u2019ll")
)

p.write_text(content, encoding='utf-8')
print("done")
