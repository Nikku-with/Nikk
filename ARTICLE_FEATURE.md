# 📜 Telegram Article / Rich Text Editor — poori knowledge

> Ye doc un screenshots ke baare me hai jo tumne bheje: **Add title · table · checklist ·
> toggle block · math · Article button**. Sab kuch verified hai Telethon 1.45 (layer 229) ke
> against — guess nahi.

---

## 1. Sabse pehle: "Article" kya hai?

**Telegram me "Article" ek alag message type nahi hai.**

Composer me jo **Article** button hai (attachment sheet me: Gallery · File · Location · **Article** · Contact),
wo **Rich Text Editor** kholta hai. Us editor se jo message jata hai, protocol me wo:

```
message#... message:string="" media:... rich_message:flags2.13?RichMessage
```

Matlab:

| App me dikhta hai | Protocol me |
|---|---|
| Article / Rich Text Editor | `message.rich_message` |
| Article editor ka content | `RichMessage.blocks = Vector<PageBlock>` |
| Bhejne ka API | `messages.sendMessage(rich_message=InputRichMessage)` |
| Bot API me | `sendRichMessage` (Bot API 10.1, 11 June 2026) |

**Isliye:** "article feature use karna" = `rich_message` bhejna. Do naam, ek hi cheez. ✅

Timeline:
- **June 11, 2026** — Bot API 10.1, bots ke liye `sendRichMessage` (bots ko premium nahi chahiye)
- **July 14, 2026** — Premium users ko visual Rich Text Editor (32,768 chars, tables, inline media)
- **Aug 24, 2026** — Bot API 10.3, rich message ke andar buttons

---

## 2. Editor ka har button → TL me kya

Ye tumhare screenshot wala toolbar hai. Left se right:

| Composer me | TL constructor | Field |
|---|---|---|
| **Add title** (bada title) | `PageBlockTitle` | `text` |
| Heading 1–6 | `PageBlockHeading1` … `PageBlockHeading6` | `text` |
| Subtitle | `PageBlockSubtitle` | `text` |
| Kicker (chhota upar wala) | `PageBlockKicker` | `text` |
| Header / Subheader | `PageBlockHeader` / `PageBlockSubheader` | `text` |
| Paragraph | `PageBlockParagraph` | `text` |
| **Table** (grid icon) | `PageBlockTable` | `title`, `rows`, `bordered`, `striped`, `compact` |
| Table row | `PageTableRow` | `cells` |
| Table cell | `PageTableCell` | `text`, `header`, `colspan`, `rowspan`, `align_center`, `align_right`, `valign_middle`, `valign_bottom` |
| **Merge Cells / Insert / Delete** | `colspan` / `rowspan` | cell level |
| **Alignment** (6 icons) | `align_center`, `align_right`, `valign_middle`, `valign_bottom` | cell level |
| Highlight column | koi direct TL field nahi — `header=True` (bold) ya `striped=True` se effect |
| **Bulleted list** | `PageBlockList` + `PageListItemText` | `items` |
| **Numbered list** | `PageBlockOrderedList` + `PageListOrderedItemText` | `items`, `type`, `start`, `reversed` |
| **Checklist** ☑ | `PageListItemText(checkbox=True, checked=True/False)` | flags |
| **Toggle block** | `PageBlockDetails` (`open=False`) | `blocks`, `title`, `open` |
| Quote | `PageBlockBlockquote` | `text`, `caption`, `collapsed` |
| Pull quote | `PageBlockPullquote` | `text`, `caption` |
| **Code block** | `PageBlockPreformatted` | `text`, `language` |
| Inline code | `TextFixed` | `text` |
| **Math (Σ)** | `PageBlockMath(source="…")` · inline → `TextMath(source="…")` | |
| Divider | `PageBlockDivider` | — |
| **Photo inline** | `PageBlockPhoto(photo_id=…)` + `InputRichMessage.photos=[InputPhoto]` | |
| Video inline | `PageBlockVideo(video_id=…)` | |
| Audio inline | `PageBlockAudio(audio_id=…)` | |
| Document inline | `PageBlockDocument(document_id=…)` | |
| Gallery / slideshow | `PageBlockCollage` / `PageBlockSlideshow` | |
| Caption | `PageCaption(text=…, credit=…)` | |
| **Buttons** (blue/green/red) | `PageBlockButtonRow` + `PageButton` + `RichButtonStyle(bg_primary/bg_success/bg_danger/link)` | |
| **Premium emoji** text ke andar | `TextCustomEmoji(document_id=…, alt="🔥")` | |
| Bold / Italic / Strike / Underline / Spoiler | `TextBold` / `TextItalic` / `TextStrike` / `TextUnderline` / `TextSpoiler` | |
| Link | `TextUrl(text=…, url=…, webpage_id=0)` | |
| Mention / hashtag / cashtag | `TextMention` / `TextHashtag` / `TextCashtag` | |
| Author + date | `PageBlockAuthorDate` | |
| Footer | `PageBlockFooter` | |
| AI thinking block | `PageBlockThinking` | |

RichText ko jodne ke liye: **`TextConcat(texts=[…])`** — ek se zyada node ek hi line me.

---

## 3. Limits (server-side, verified)

| Cheez | Limit |
|---|---|
| Characters | **32,768** UTF-8 (normal message 4,096) |
| Blocks | **500** (nested bhi gin ke) |
| Nesting | **16** levels |
| Media attachments | **50** |
| Table columns | **20** |
| Custom emoji / message | ~**100** |

---

## 4. Premium chahiye ya nahi?

| Kaun | Article bhej sakta hai? |
|---|---|
| **Premium user account** | ✅ haan |
| **Normal user account** | ❌ nahi (`inputMessageRichMessage` reject) |
| **Bot account** | ✅ haan — bots ko premium nahi chahiye |
| Padhna / receive karna | ✅ sab kar sakte hain, premium ki zaroorat nahi |

Isliye bot me: premium hai → article; nahi hai → normal text (fallback).

---

## 5. Bot me kaise use karein

### Commands

```
.article                     → help card
.article <text>              → seedha article
.article md <markdown>       → server khud parse karega
.article html <html>         → server khud parse karega
.article demo                → sample
.article read                → reply kiye article ko text me nikalo
.article edit <text>         → existing message ko article banao
.article draft <text>        → live typing preview (stream)
.article check               → premium + support check
.article stop                → draft rok do
```

Kisi bhi message pe **reply + `.article`** → wahi text article ban jayega.
**Photo pe reply** → article ke andar cover photo lag jayegi.

### Syntax (composer ke buttons ka shortcut)

```
@title ⚡ NIK VAULT ⚡        ← Add title
@kick new drop                ← kicker
@sub premium collection       ← subtitle

# Heading 1        ## Heading 2        ### Heading 3

|Plan|Price|                 ← table
|---|---|
|[r]Basic|₹99|               ← [r] right  [c] center  [m] middle  [b] bottom
|[c]merged <<2||              ← <<2 = colspan 2,  ^^2 = rowspan 2

- bullet
- [x] checklist done
- [ ] checklist pending

1. numbered
2. list

> quote line
```python
code block
```
$$E = mc^2$$                  ← math
::: Toggle title
andar chhupa text
:::
---
**bold**  *italic*  ~~strike~~  ||spoiler||  `inline code`  $inline math$  [link](https://…)

[[btn:blue]] 🪶 WATCH NOW 🪶 | https://t.me/…
[[btn:green]] 🪶 JOIN FREE 🪶 | https://t.me/…
[[btn:red]] 🪶 VIP 🪶 | https://t.me/…
```

### Premium templates (`vault` / `menu` / `drop` / `links`)

```
.article tpl vault ⚡ MY VAULT ⚡ | url1 | url2 | url3
.design vault ⚡ MY VAULT ⚡ | url1 | url2      ← short alias
```

### Code level (agar khud likhna ho)

```python
from telethon.tl import types, functions

rich = types.InputRichMessage(blocks=[
    types.PageBlockTitle(text=types.TextPlain("⚡ NIK VAULT ⚡")),
    types.PageBlockParagraph(text=types.TextConcat(texts=[
        types.TextPlain("Premium "),
        types.TextCustomEmoji(document_id=6237962044889373292, alt="⚡"),
    ])),
    types.PageBlockTable(
        title=types.TextEmpty(),
        rows=[types.PageTableRow(cells=[
            types.PageTableCell(header=True, text=types.TextPlain("Plan")),
            types.PageTableCell(header=True, align_right=True,
                                text=types.TextPlain("Price")),
        ])],
        bordered=True, striped=True),
    types.PageBlockButtonRow(buttons=[
        types.PageButton(
            text=types.TextPlain("🪶 WATCH NOW 🪶"),
            type=types.InlineButtonTypeUrl(url="https://t.me/Nikkkwa"),
            style=types.RichButtonStyle(bg_primary=True)),
    ]),
])

await client(functions.messages.SendMessageRequest(
    peer=peer, message="", rich_message=rich, random_id=random.getrandbits(62)))
```

**Zaroori:** `message=""` (khaali string) — content sirf `rich_message` me jata hai.

---

## 6. Poora bot UI article-engine pe

`eor()` ek central hub hai jahan se saare 251 commands render hote hain. Wahan
`_ui_render()` lagaya gaya hai:

```
plain rail panel  →  PageBlockTitle (masthead)
                     PageBlockHeading2 (section)
                     PageBlockTable (command rows)
                     PageBlockDivider
                     PageBlockButtonRow (coloured)
                     + premium emoji TextCustomEmoji
```

- account premium → har card article ban jata hai
- premium nahi → purana plain UI (koi break nahi)
- force: `.richui on` / `.richui off` ya env `RICH_UI=1`

---

## 7. Kya nahi ho sakta

| Cheez | Status |
|---|---|
| Bot se composer **kholna** | ❌ impossible — editor client-side UI hai |
| Article ko normal text me convert karna | ✅ `PageBlock*` → text flatten (`.article read`) |
| Ek article me 100+ custom emoji | ⚠️ ~100 ke baad server plain kar deta hai |
| Normal message ko rich me edit karna | ✅ `messages.editMessage(rich_message=…)` |
| Rich ko wapas normal text karna | ✅ `editMessage(message="…")` |

---

## 8. Media + Article (naya)

Ab media alag attachment nahi — **article ke andar inline** jata hai (jaise composer me
Gallery/File se photo/article ke beech lagana).

| Command | Kaise jata hai |
|---|---|
| `.music <song>` | `PageBlockTitle` + `PageBlockPhoto` (album art) + `PageBlockAudio` + table + buttons |
| `.yt / .ig / .pt / .fb` | photo → `PageBlockPhoto`, video → `PageBlockVideo`, baaki → `PageBlockDocument` |
| `.article` (photo/video/audio/doc pe reply) | wahi media article ke sabse upar inline |

Har media article me: title · subtitle · media · info table · coloured buttons · footer.
Agar rich path fail ho (non-premium / server reject) → purana normal `send_file` fallback
chal jata hai, koi message lost nahi hota.

Code:

```python
await rich_media(event, path, kind="audio", title="Song",
                 subtitle="🎶 now playing",
                 rows=[("duration", "3:20"), ("size", "4.1 mb")],
                 audio={"duration": 200, "title": "Song", "performer": "Nik"},
                 cover="/tmp/art.jpg",
                 buttons=[("🪶 SUPPORT 🪶", "https://t.me/Nikkkwa", "green")])
```

### Lists → tables

Jab rich UI on hai, har list (`.savelist`, `.filters`, `.noteslist`, `.listbots`,
`.gbanlist`, `.gmutelist`, `.getmute`, `.vlist`, `.staff` …) apne aap **2-column table**
me badal jaati hai — ye `_ui_blocks()` ka `‣` → `PageTableRow` conversion hai, command
code chhedne ki zaroorat nahi.

---

## 9. ⛔ Server rule — ye blocks bhejne pe error aata hai

`RICH_MESSAGE_BLOCK_UNSUPPORTED` ka asli kaaran. Ye blocks **sirf Instant View
pages** ke liye hain — bot ke rich message me bhejte hi poora message reject:

| Block | Allowed? | Replacement |
|---|---|---|
| `PageBlockTitle` | ❌ | `PageBlockHeading1` |
| `PageBlockSubtitle` | ❌ | `PageBlockParagraph` (italic) |
| `PageBlockHeader` / `Subheader` | ❌ | `PageBlockHeading3` |
| `PageBlockKicker` | ❌ | `PageBlockParagraph` (bold) |
| `PageBlockAuthorDate` | ❌ | `PageBlockParagraph` |
| `PageBlockCover` | ❌ | andar ka block seedha |
| `PageBlockRelatedArticles` | ❌ | drop |

Source: telegram-bot-api `td/td/telegram/WebPageBlock.cpp`.

Code me `_sanitize_blocks()` hai — koi bhi path se galat block aaya to
automatically allowed shape me convert ho jata hai (nesting ke andar bhi).
Isliye ab `RICH_MESSAGE_BLOCK_UNSUPPORTED` nahi aayega.

---

## 10. Text style — thoda bold

Body copy `sc()` se guzarti hai. Default `TEXT_BOLD=1` — text bold sans
(`𝗺𝗲𝗻𝘂`) me aata hai, is liye poori UI thodi heavy/bold lagti hai.
Purana small-caps (`ᴍᴇɴᴜ`) chahiye to env me `TEXT_BOLD=0` set karo.

Headers `sb()` / `hdr()` pe bold pehle se tha — ab body bhi match karti hai.

## 11. Emoji budget

Har section ka apna emoji (`CAT_STYLE`: icon = header + alternate rows,
alt = beech ke rows), `row()` me bullet alternate hota hai, `kv()` diamond,
`note()` dot. Isse emoji har line pe nahi aate — sirf jahan value add karti hai.

## 12. Table rows — lines hamesha

`_ui_blocks()` ab har card ki **har line** ko table row banata hai jisme
`‣` / `▶` / `›` / `→` separator ho — rail (`┃│`) ho ya na ho. Isse
`.status` jaisi cards (jo `hr()` + `_sr()` use karti hain) bhi bordered
table me render hoti hain, lines gayab nahi hoti.

* `hr()` / `────` → `PageBlockDivider`
* chhoti ALL-CAPS line → `PageBlockHeading3`
* 1 row wali table → ek spacer row add hoti hai taaki border dikhe

## 13. Reaction lock

`AR_LOCK["chat:user"] = {"items": [...], "name": "sad"}` → `arlock.json`.
`@bot.on(events.NewMessage(incoming=True))` har naye msg pe check karta hai
aur wahi payload (`ReactionCustomEmoji` / `ReactionEmoji` mix) bhej deta hai.
`.ar off` / `.sar` se clear. Self react `SELF_REACT` (global) → `selfreact.json`.

## 14. Rich message aliasing (spam fix)

Plain message ko rich me edit karna Telegram allow nahi karta, isliye pehli
baar naya rich message bhejna padta hai. `_RICH_ALIAS[(chat, cmd_msg_id)]`
us naye id ko yaad rakhta hai — aage ki saari `.edit()` calls usi message pe
jaati hain. Edit phir bhi fail ho to us chat me 60 sec rich band (`_RICH_OFF`).

## 15. Render engine v6 (Round 16)

**Ek font.** `_rt()` ke shuru me `_plainify()` chalta hai — math-alphanumeric
blocks (`𝓝𝗡𝙉`) NFKC se ASCII ban jaate hain, small-caps reverse-map se.
Isliye rich card me sirf Telegram ka default font + asli `Heading1/2/3`
bold dikhta hai. Plain (non-rich) mode jaisa tha waisa hi hai.

**Har line ek block.** `_ui_blocks()` rules:

| Line | Block |
|---|---|
| `┏━ masthead` / `╭─` | `PageBlockHeading1` |
| `┗━━` / `────` | `PageBlockDivider` |
| `▰ section ▰` / `〔 X 〕` | `PageBlockHeading2` |
| `‣ ▶ › → ➤ »` wali line | `PageTableRow` (2 cell) |
| chhoti ALL-CAPS line | `PageBlockHeading3` |
| baaki | `PageBlockParagraph` |

* Table ka `title=TextEmpty()` (Telethon me `None` serialize nahi hota).
* **Koi spacer/khali row nahi** — wahi "khali boxes" dikha raha tha.

**Mixing band.** `_UiMsg.edit()` sirf rich edit karta hai; fail ho to purana
content rehta hai, plain text card ke andar nahi ghusega. Loader / flash /
done animation `plain=True` pe chalte hain (sasta + reliable).

**Duplicate band.** Plan-B naya rich message bhejne ke baad purana message
`bot.delete_messages` se uda diya jata hai, phir `_RICH_ALIAS[(chat, mid)]`
naya id yaad rakhta hai — agli edits usi message pe.

## 16. Prefix optional + animation commands

`_dispatch()` me agar text `.` se shuru nahi hota to **pehla word** hi command
maana jata hai (case-insensitive):

```
.hy   hy   Hy      → sab .hy
```

Guard: bina-prefix sirf `OWNER_ID` ya apne account (`event.out`) se — warna
group me "ban"/"id" jaisa normal word galti se chal jayega. Sudo ke liye
bina-prefix band hai. Env `NOPREFIX=0` se poora feature off.

**Plain-mode contextvar.** `_PLAIN_MODE` true hone pe `eor()` rich bilkul
skip karta hai. `PLAIN_CMDS = {hy, love, love1-5, lovestory, fun1-8}` —
ye frame-by-frame animation karte hain (`play_frames`, `cmd_hy`), rich card
me har frame naya article banata tha isliye animation ruk jaati thi.
`ghost` / `echo` / `filereply` check bhi `_looks_like_cmd()` use karte hain
taaki prefix-less command ko normal message na samjhein.

## 17. Duplicate card ka asli reason (Round 18)

`messages.SendMessageRequest` ka return **`Updates`** hota hai (`Message` nahi),
usme `.id` attribute nahi hota. Pehle code:

```python
new_id = int(getattr(sent, "id", 0) or 0)   # → 0
if new_id: ...
_RICH_OFF[chat] = ...; return None           # → eor() plain fallback karta tha
```

…matlab rich card **bhej diya gaya tha**, par function `None` return karta tha
aur `eor()` fallback me `event.reply()` chal jaata tha → **do message**
(ek rich, ek plain — bilkul wahi jo screenshot me tha).

Fix:

* `_sent_msg_id(sent)` — `sent.id` → `sent.updates` me `UpdateMessageID.id`
  → `update.message.id` → (last resort) `get_messages(chat, limit=1)`.
* agar id phir bhi na mile to `_RICH_DONE` sentinel return hota hai →
  `eor()` us case me plain fallback **nahi** karta.
* `_LAST_CARD[(chat, msg_id)] = (text_hash, card_id, ts)` — 6 sec ke andar
  same text same command message pe → naya card nahi.

### Font map bug

`_SC_TAB` me `q` ke liye `Q` likha tha (typo, hona chahiye `ǫ`), aur
`_UNTRANSLIT` ki small-caps string me `x` chhoot gaya tha → `y` ka reverse
mapping `x` ban gaya, isliye `ye→xe`, `by→bx`, `diya→dixa`.

## 18. Loader / codeblock / empty-box rules (Round 19)

### Loader
`load_card(phase, text, i, pct)` — 2 line card:

```
🔍  searching  freaked out
⠸  ▰▰▰▱▱▱▱▱▱▱   34%
```

Phases: `search 🔍 ⠋⠙⠹…` · `fetch 📡 ⣾⣽⣻…` · `down ⬇️ ▁▃▄▅▆▇█` ·
`convert 🎛 ◐◓◑◒` · `send 🚀 ←↖↑↗→↘↓↙` · `save 💾 ⠈⠐⠠⢀⡀⠄⠂⠁`.
`_music_loader` 0.8 s pe tick karta hai, bar 95% pe rukta hai (100% sirf
kaam poore hone pe), `stop` set hote hi ruk jaata hai.

### Code block
`_ui_codeish()` — line agar `.` se shuru ho, <=44 chars, aur pehla word koi
command (ya `<...>` placeholder) ho → `PageBlockPreformatted` (monospace).
Iske upar wali chhoti label line (`words se search`) → `PageBlockHeading3`.

### Khali box zero
1. Table sirf tab jab **2+ rows** hon. 1 row → paragraph
   (`▫ key → value`), kyunki single-row bordered table khali dabbe jaisi
   dikhti hai.
2. Cell kabhi khali nahi — `_ui_cell()` `" "` fallback deta hai.
3. `test_boxes.py` — saari 268 commands chalake har card ke blocks check
   karta hai (empty cell / 1-row table / fake font / empty codeblock).

## 19. v9 — design final (font + `⇒` panel + red button)

**Font.** `_rt()` ab font characters nahi hatata. `_plainify()` sirf
classification (`_ui_caps`, `_ui_codeish`) ke liye chalta hai. Isliye card me
wahi premium look aata hai jo commands bhejti hain (𝓝𝓲𝓴 𝓤𝓼𝓮𝓻𝓫𝓸𝓽, ᴍᴇɴᴜ,
𝗠𝗨𝗦𝗜𝗖), aur preview HTML bhi wahi dikhata hai.

**Blockquote panel (`⇒`).** Jo line table row nahi ban sakti
(koi `‣ ▶ › →` separator nahi) wo `PageBlockBlockquote` me jaati hai,
har line `⇒ ` se shuru. Consecutive lines ek hi quote me merge hoti hain.
Ek hi row wali table bhi yahin aati hai — `⇒ left · right` — is liye
"khali dabba" kabhi nahi banta.
(`PageBlockBlockquote` me `caption` required hai — `TextEmpty()` bhejte hain.)

**Code block.** `.cmd ...` (<=44 chars) → `PageBlockPreformatted`.

**Buttons.** OWNER = `RichButtonStyle(bg_danger=True)` + dono custom emoji.

**Loader emoji.** Sirf pack me maujood emoji: 👀 🔮 ⬇️ 🪄 ✈️ 📌 — isliye
loader bhi premium custom emoji ke saath aata hai.
