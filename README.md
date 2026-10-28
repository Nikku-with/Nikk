# ♛ NIK USERBOT

Single-file Telethon userbot — **Global** mode · **268 commands** · mobile-safe UI

`.m1 … .m24` menus · owner + sudo access · sub-userbots · free AI · rob/kill automation

---

## 🆕 Naya kya hai (v9) — font wapas, `⇒` panel, red OWNER

| # | Change |
|---|---|
| 1 | **Font wapas** — `_plainify` sirf pehchaan ke liye; card me asli font (𝓝𝓲𝓴 𝓤𝓼𝓮𝓻𝓫𝓸𝓽 · ᴍᴇɴᴜ · 𝗠𝗨𝗦𝗜𝗖) hi jaata hai. Preview me bhi wahi dikhta hai. |
| 2 | **Jo table me nahi aata → Blockquote (`⇒` panel)** — img1/img6 jaisa: har line `⇒ text`, Telegram ka left accent bar. 1-row table bhi yahin chali jaati hai. |
| 3 | **Command examples → code block** — `.music freaked out`, `.c 12345` monospace me, upar label heading. |
| 4 | **OWNER button ab RED** (pehle blue tha). |
| 5 | **Loader emoji ab premium packs se** — 👀 searching · 🔮 fetching · ⬇️ downloading · 🪄 converting · ✈️ sending · 📌 saving (sab custom emoji ban jaate hain). |

## 🆕 Naya kya hai (v8) — prefix/glockmsg toggles + stylish loader + zero empty boxes

| # | Change |
|---|---|
| 1 | **`.prefix on/off`** — `on` = dot zaroori, `off` = `.hy` / `hy` / `Hy` teeno. State `prefix.json` me save, turant lagu. |
| 2 | **`.glockmsg on/off`** — lock message **poore bot** me on/off (sab chats). |
| 3 | **`.lockmsg on/off`** — ab **per-chat** (sirf jis chat me command chali). Global master alag. |
| 4 | **Naya loader** — `🔍 searching / 📡 fetching / ⬇️ downloading / 🎛 converting / 🚀 sending / 💾 saving` + braille/blocks/arrows spinner + `▰▰▰▱▱▱` progress bar with % — `.music`, `.yt/.ig/.pt/.fb`, `.vsave` sab me. |
| 5 | **Code blocks** — jo line `.` se shuru ho aur command example ho (`.music freaked out`) wo **monospace code block** me render hoti hai; labels (`words se search`) heading ban jaate hain. |
| 6 | **Khali box zero** — 1-row table ab box nahi banti (paragraph ban jaati hai), empty cell kabhi nahi. **292 cards scan: 0 problem.** |
| 7 | **Rich retry** — send fail ho to custom emoji documents ke bina dobara bhejta hai (poora card plain hone ke bajaye), doc cooldown 600s → 45s. |

## 🆕 Naya kya hai (v7.1) — duplicate card + spelling fix

| # | Change |
|---|---|
| 1 | **Double message fix (asli bug)** — `SendMessageRequest` `Updates` deta hai (usme `.id` nahi hota), isliye rich msg bhejne ke baad code id na milne pe **plain fallback bhi** kar deta tha → ek command pe 2 card. Ab id `UpdateMessageID` se nikalta hai, aur id na mile to plain fallback **bilkul nahi**. |
| 2 | **Duplicate guard** — wahi text usi command message pe 6 sec ke andar dobara aaye to naya card nahi banta (purana edit/hi rehta hai). |
| 3 | **Font/spelling bug** — small-caps table me `q` galat tha (`Q`) aur reverse-map me `x` chhoot gaya tha, jisse **`ye` → `xe`, `by` → `bx`, `diya` → `dixa`** ho raha tha. Ab sahi: `ye`, `by`, `diya`, `quick`. |

## 🆕 Naya kya hai (v7) — prefix optional + animation commands plain

| # | Change |
|---|---|
| 1 | **Prefix optional** — `.hy` / `hy` / `Hy` teeno same. Koi bhi command bina `.` chalti hai (sirf owner / apne account se, taaki group me normal word galti se na chale). Band karna ho: env `NOPREFIX=0`. |
| 2 | **`.hy` `.love` `.love1-5` `.lovestory` `.fun1-8` ab rich text use nahi karte** — ye frame-by-frame animation wale hain, rich edit unhe atka deta tha. Baaki saari commands waisi hi (rich card). |

## 🆕 Naya kya hai (v6) — clean render engine

| # | Change |
|---|---|
| 1 | **Rich card = ek hi font** — `.status`, menu, `.ar`, music sab me fake-font (small-caps/mono/script) hata diya: rich mode me **normal Telegram font + real bold headings**. |
| 2 | **Lines fix (root cause)** — har line jisme `‣ ▶ › →` ho ab **table row** banti hai; `────` → divider; ALL-CAPS line → heading. Khali cell / spacer row **poori tarah hata** (wahi "khali boxes" the). |
| 3 | **Rich + plain mixing band** — rich card ke andar plain text kabhi nahi ghusega. Animation/loader messages jaan-boojh ke plain rehte hain (fast + reliable edit). |
| 4 | **Duplicate card fix** — plan-B ke baad purana message **pakka delete** (pehle delete fail hone pe dono reh jaate the). |
| 5 | **`.music` animation wapas + sahi timing** — `▰▱▱▱▱` har 1 sec, `fetching → sending` do phase; animation **MP3 poora send hone tak** chalti hai, phir gayab. |
| 6 | **`.vsave` animation** — save/convert hone tak wahi bar. |
| 7 | **`.ar` 100% react** — retry + custom emoji fail hone pe **unicode fallback**, watcher ka throttle hataya. |
| 8 | **Menu complete** — 265 commands, 0 missing (`.r`, `.article`, `.killall` add + `.m24` VC). |
| 9 | **Garbage code out** — 6 dead helpers/vars hataye, file ke top pe **FILE MAP** index. |

## 🆕 Naya kya hai (v5) — reaction LOCK + fixes

| # | Change |
|---|---|
| 1 | **`.ar <combo>` = LOCK** — kisi ke msg pe reply karke `.ar sad` → turant react + **us user ke har naye msg pe wahi 3 emoji** (us chat me) jab tak band na karo. |
| 2 | **`.ar <emoji>`** (unicode like `.ar 🔥`) — pack ki zarurat nahi, seedha single reaction + lock. "pack nahi bana" error gaya. |
| 3 | **`.ar off`** — is chat ke saare locks band. **`.sar`** bhi sab off karta hai. |
| 4 | **`.selfar <combo>`** — mere khud ke messages pe react (global). **`.selfsar`** / `.sar` — band. |
| 5 | **`.r`** — 3 emoji poore hote hi combo save + **saved msg 2 sec me auto delete**. Adhura combo `.ar <name>` se bhi chalega (auto-save). |
| 6 | **`.requests` / `.approve` / `.deny`** — join requests list + approve/deny (`all` ya number se). Purana `GetChatInviteImportersRequest` error fix (`offset_user`). |
| 7 | **Rich table lines fix** — `.status` jaise cards ki har row ab table-row banti hai (pehle paragraph thi → lines nahi aati thi). `‣ ▶ › →` sab separator. |
| 8 | **Sudo spam fix** — edit fail hone pe pehle har update naya message bhejta tha; ab naya id yaad rehta hai → **ek hi card edit hota hai**. |
| 9 | **`.music` purana `▰▱▱▱▱` animation wapas** (1 sec tick). |
| 10 | **Purge fix** — `.purge 50` → `50/50` report; `.purgeme` default = **saare** apne messages + exact count (deleted / skipped). |
| 11 | **Text wapas purana** — `sc()` dobara small-caps (ᴀʙᴄ). `TEXT_BOLD=1` se bold. |
| 12 | **CHANNEL button hataya** — har card pe sirf `OWNER` (dono custom emoji). |

## 🆕 Naya kya hai (v4)

| # | Change |
|---|---|
| 1 | **`.ar <combo>` — reaction combo** — 3 custom emoji **ek saath** ek hi message pe: `cry · sad · aww · lol · kiss`. Reply / `@user` / user-id pe lock; bina arg = latest unread. |
| 2 | **`.ar <emoji-id>`** — seedha single instant reaction (bina combo banane ke). |
| 3 | **`.makear <name>` → `.r <emoji|id>` ×1–3 (60 s)** → auto save → `.ar <name>` se use, `.rem <name>` se hatao. Presets protected. |
| 4 | **`.rembots @user / all`** — saved bots hatao (`.addbots` ka ulta). |
| 5 | **`.lockmsg on/off`** — lock message spam band; off pe non-sudo ko chup-chaap ignore. |
| 6 | **`.check <cmd>`** — command kya karta hai, kahan chalta hai, aliases, owner/group/reply flags + **live state** (lockmsg, antidel, ar combos, vc slots…). |
| 7 | **Buttons** — `SUPPORT` hataya; `OWNER` button dono taraf custom emoji (`5452012007865738264` / `5452073790970292239`); CHANNEL sirf alag URL ho tab. |
| 8 | **Speed** — `.music` / download ab instant: heavy loader nahi, pehla edit 1.2 s me; source/original/support rows hataye. |
| 9 | **Text thoda bold** — body `sc()` ab bold-sans deta hai (`TEXT_BOLD=0` se purana small-caps). |

## 🆕 Naya kya hai (v3)

| # | Change |
|---|---|
| 1 | **`.m22` — Baka Automation** add hua (11 commands): `.setbot .baka .rob .kill .auto .autooff .roboff .killoff .stoprob .resetdone .solve` |
| 2 | **`.setgame` → `.setbot`** — ab group me kaam karta hai (pehle sirf DM), inline buttons wala setup |
| 3 | **`.rob` / `.kill` / `.auto` ka naya logic** — newest→oldest target, skip self/owner/bots/done, balance probe, retry, verify-code handling |
| 4 | **Menu me missing commands add** — `.list`, `.admins` (`.m14`), `.rob .kill .auto …` (`.m22`) |
| 5 | **Hataye gaye** — `.arviyom`, `.sarviyom`, `.replyyorichi`, `.syorichi` |
| 6 | **`.music` bina link** — words se search → audio/voice note (`.song .play .mp3` aliases) |
| 7 | **UI fix** — display-width aware (emoji se border tootna band) + naya `rail` style |
| 8 | **`.addbot` rewrite** — phone normalize, 2FA, `.resend`, `.cancelbot`, `.delbot`, restart pe auto-connect |

### 🆕 Naye commands — quick reference

| Command | Kaam | Kahan |
|---|---|---|
| `.setbot @im_bakabot` | automation bot set + buttons setup | `.m22` |
| `.baka` | automation status + rules | `.m22` |
| `.rob [amt]` | group ke sab users ko rob | `.m22` |
| `.kill [amt]` | group ke sab users ko kill | `.m22` |
| `.auto [amt]` | balance check → rob / kill / dono / skip | `.m22` |
| `.autooff` `.roboff` `.killoff` `.stoprob` | workers band karo | `.m22` |
| `.resetdone` | done list clear | `.m22` |
| `.solve <code>` | bot ki verification code bhejo | `.m22` |
| `.list sudo` · `.list bots` | sudo / saved bots list | `.m14` |
| `.admins` | sudo list (short) | `.m14` |
| `.resend` | login code dobara bhejo | `.m15` |
| `.cancelbot` | adhura login chhodo | `.m15` |
| `.delbot <num>/all` | subbot hatao | `.m15` |
| `.user` | connected userbots list | `.m15` |
| `.music words` / `.song` / `.play` / `.mp3` | bina link song search | `.m13` |

Purani details → [`FIXES.md`](FIXES.md)

---

## Setup

```bash
pip install -r requirements.txt
```

ffmpeg (voice note ke liye — optional):

```bash
sudo apt install -y ffmpeg
```

Config **env variables** se aata hai (hardcode karne ki zarurat nahi):

```bash
export API_ID=123456          # my.telegram.org
export API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export OWNER_ID=8742036730    # @userinfobot se apna id
export SESSION=nik            # session file name ya StringSession
```

Agar env set nahi hai to file ke upar wale default values use honge.

```bash
python Nik_userbot.py
```

Pehli baar phone number + OTP maangega, phir **`nik.session`** ban jayegi.
**Session file ko kabhi commit mat karna** (`.gitignore` me hai).

---

## Menus

Menu ek saath nahi bheja jata — **alag alag menu hain** (total **184** menu entries):

| Command | Category | Commands |
|---|---|---|
| `.m5` | group mod | 24 |
| `.m6` | fun | 8 |
| `.m7` | tools | 9 |
| `.m8` | global | 6 |
| `.m9` | protection | 8 |
| `.m10` | blacklist | 8 |
| `.m11` | broadcast | 5 |
| `.m12` | messaging | 14 |
| `.m13` | auto | 18 |
| `.m14` | media | 6 |
| `.m15` | ai & sudo | 5 |
| `.m16` | bot manager | 12 |
| `.m17` | raid | 15 |
| `.m18` | spam | 9 |
| `.m19` | gc tools | 3 |
| `.m20` | notes | 5 |
| `.m21` | stories | 14 |
| `.m22` | core | 9 |
| `.m23` | baka automation | 11 |
| `.m24` | voice chat | 11 |
| `.fullmenu` | saare 3 pages ek saath (3 messages) | — |
| `.menu` / `.help` | index — kaunsa `.mN` kis cheez ka hai | — |
| `.help <command>` | us command ki detail + guides | — |

* `.m1` … `.m4` → **pages** (189 commands, 4 messages)
* `.m5` … `.m24` → **har category ka alag menu**
* `.fullmenu` → sab pages ek saath
* `.help addbot` / `.help music` / `.help c` / `.help p` / `.help user` / `.help delbot` → detailed guides

> 🔒 = owner-only command

---

## 📦 `.m22` — Baka Automation (rob / kill bots)

Kisi bhi economy bot (jaise **@im_bakabot**) ko group me automate karta hai.

### Setup (ek baar)

```bash
.setbot @im_bakabot        # @ / bina @ / t.me/… — teeno chalenge
```

Bina value ke `.setbot` bhejo → **inline buttons** wala setup panel:

| Button | Kya karta hai |
|---|---|
| `prefix / . !` | bot ka command prefix |
| `mode reply / mention / plain` | rob-kill kaise bheja jaye |
| `delay 2s / 3s / 5s` | do actions ke beech gap |
| `probe on/off` | pehle balance check kare ya na |
| `amount all` | full balance |
| `✅ save` / `⏭ skip` | save karo ya chhodo |

Text se bhi (jo button me nahi hai):

```bash
.setbot prefix /          .setbot mode reply
.setbot delay 3           .setbot probe off
.setbot amount all        .setbot fallback both
.setbot rob rob           .setbot kill kill
.setbot bal bal
```

| Config | Matlab | Default |
|---|---|---|
| `prefix` | bot commands ka prefix | `/` |
| `mode` | `reply` = victim ke msg pe reply · `mention` = `@user` · `plain` | `reply` |
| `amount` | `all` ya fixed number | `all` |
| `delay` | har action ke baad gap (sec) | `2.5` |
| `probe` | pehle `.bal` check kare | `on` |
| `rob` / `kill` / `bal` | bot ke actual command naam | `rob` / `kill` / `bal` |
| `fallback` | probe fail ho to: `both` / `rob` / `kill` / `skip` | `both` |

### Chalana (jis GC me karna hai wahan bhejo)

```bash
.rob             # sabko rob · full balance
.rob 500         # fixed 500
.kill            # sabko kill
.kill 500        # fixed 500
.auto            # balance check → rob / kill / dono / skip
.auto 500        # same · fixed amount
.autooff         # auto band
.roboff          # rob worker band
.killoff         # kill worker band
.stoprob         # sab band
.resetdone       # done list clear (dobara sabko target)
.solve 1234      # bot ne verification maangi → code bhejo
.baka            # status + rules
```

### Logic

```
target : every real user (newest → oldest)
skip   : self · owner(sub + main) · bots · already done
amt    : all balance (ya .rob <amt>)

coins + alive   → rob + kill
coins + dead    → rob only
no coins + alive → kill only
no coins + dead  → skip
probe fail       → fallback setting

stop : .autooff · .stoprob
```

* `reply` mode me user ka **last cached message** reply ke liye use hota hai;
  cache me na ho to `@username` mention fallback.
* `protection` / `failed` / `insufficient` detect hone pe **apna message delete + retry**.
* Bot **verify/captcha** maange to engine rukta hai, `.solve <code>` maangta hai.
* Live progress panel (robbed / killed / skipped / failed) — ek hi message edit hota hai.
* Done list `data/baka_done.json` me · config `data/baka.json` me.

---

## 🎵 Media — `.music` bina link

```bash
.music freaked out                 # words se YouTube search
.music kesariya                    # gaana
.music https://youtu.be/xxxx       # link bhi chalega
.yt freaked out                    # video (words ya link)
```

* Search → `ytsearch1:` → **audio-only (m4a)** download (video nahi)
* ffmpeg ho to **voice note (ogg/opus)**, warna audio file
* Telegram me **file ka naam song ka title hota hai** (`dl_1792…_WkTos` nahi)
* Aliases: `.song` `.play` `.mp3` · guide → `.help music`

| Command | Kya karta hai |
|---|---|
| `.yt` | YouTube video (link ya words) |
| `.ig` `.pt` `.fb` | Instagram / Pinterest / Facebook download |
| `.music` `.song` `.play` `.mp3` | song search → voice note / audio |

---

## 🎤 Voice Chat — `.m24`

Group me VC start karo, saved MP3 bajao, queue lagao.

| Command | Kaam |
|---|---|
| `.startvc` | group me vc start karo |
| `.endvc` | vc band · sab ke liye |
| `.vstop` | stream roko + left |
| `.vsave` | reply mp3 save · auto no. |
| `.vsave 3` | slot 3 me save · overwrite |
| `.vlist` | saari saved files naam sath |
| `.vplay` | mp3 pe reply → direct play |
| `.vplay 1` | saved file bajao |
| `.vplay 1,2,3` | ek ke baad ek · queue |
| `.vget 2` | file chat me bhejo · preview |
| `.vdelete 2` | slot delete |
| `.m24` | poora VC menu |

**Kaise use kare**

```text
0. direct:        MP3 pe reply → .vplay      (turant bajega)
1. group me:      .startvc
2. MP3 pe reply:  .vsave            → #1 save
3. dusri file:    .vsave            → #2 save
4. bajao:         .vplay 1,2        → queue me chalega
5. preview:       .vget 2           → file chat me aa jayegi
6. band:          .vstop  ya  .endvc
```

* `.vsave 3` → seedha slot **3** me (overwrite)
* `.vsave 2,3,4` → ek hi file 3 slots me
* `.vplay all` → saari saved files
* `.vlist` → number · naam · duration · size
* **temp files** (direct play) stream khatam hote hi **auto delete** — sirf `.vsave` wali files rehti hain

**Requirements** (VC ke liye):

```bash
pip install py-tgcalls
sudo apt install ffmpeg
```

> `pytgcalls` na ho to `.vplay` clear error deta hai (crash nahi).
> `.vplay` pehle check karta hai VC live hai ya nahi — nahi hai to `.startvc` bolta hai.

---

## 🤖 Bot manager — `.addbot` (sub-userbots)

```bash
.addbot +919876543210     # +91 / 91 / 0091 · spaces-dashes sab chalega
.c 12345                  # code (spaces bhi: .c 1 2 3 4 5)
.p mera_password          # sirf 2FA wale accounts
```

| Command | Kya karta hai |
|---|---|
| `.addbot <number>` | naya userbot login shuru (code bhejta hai) |
| `.c <code>` | login complete · alias `.code` |
| `.p <password>` | 2FA password |
| `.resend` | naya code bhejo · alias `.rcode` |
| `.cancelbot` | adhura login chhod do · alias `.cc` |
| `.user` | connected bots + pending + time left |
| `.delbot <number>` / `.delbot all` | subbot hatao (session delete) · alias `.removebot` |
| `.addbots @b1 @b2` | sirf bot usernames save |
| `.listbots` / `.invitebots` / `.promotebots` | saved bots se kaam |

* Login hote hi us account pe **poora dispatcher** lag jata hai → us account se bhi
  `.m1`, `.music`, `.rob` sab chalta hai.
* Session `sub_<number>.session` me save · restart pe **auto-connect**.
* Code na aaye to 1–2 min wait karke `.resend` — Telegram third-party client me
  code kabhi app ke andar bhejta hai.

---

## 📜 Saare commands (category-wise)

> 🔒 = owner-only · `(alias)` likhi rows usi command ka shortcut hain

### `.m5` — group mod  (24 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.kick` | user nikaalo | — |
| `.delkick` | kick + msg udao | — |
| `.ban` | ban | — |
| `.delban` | ban + msg udao | — |
| `.unban` | unban | — |
| `.mute` | mute · m / mute | `m` |
| `.delmute` | mute + msg udao | — |
| `.unmute` | unmute · sm | `sm` |
| `.tmute` | timed mute `10m/2h` | — |
| `.getmute` | muted list | — |
| `.staff` | admin list | — |
| `.promote` | admin banao | — |
| `.fullpromote` | full rights | — |
| `.demote` | admin hatao | — |
| `.title` | custom tag/title | — |
| `.pin` | pin | — |
| `.unpin` | unpin / all | — |
| `.group` | title / desc | — |
| `.tagall` | sabko tag | — |
| `.banall` 🔒 | sabko ban | — |
| `.lock` | lock <type> | — |
| `.unlock` | unlock <type> | — |
| `.locks` | active locks | — |
| `.slock` | super lock · sab mute | — |

### `.m6` — fun  (8 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.tictactoe` | game shuru | — |
| `.ttt` | move `1-9` | — |
| `.rps` | rock-paper-scissor | — |
| `.roll` | dice roll | — |
| `.flip` | coin toss | — |
| `.fact` | random fact | — |
| `.bomb` | bomb animation | — |
| `.love` | heart animation | — |

### `.m7` — tools  (9 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.tts` | text → audio | — |
| `.qrcode` | text → qr | — |
| `.fancy` | fancy fonts | — |
| `.style` | style convert | — |
| `.emoji` | emoji decore | — |
| `.calc` | calculator | — |
| `.weather` | mosam | — |
| `.ip` | ip lookup | — |
| `.short` | url shorten | — |

### `.m8` — global  (6 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.gban` 🔒 | sab chats me ban | — |
| `.ungban` 🔒 | gban hatao | — |
| `.gbanlist` 🔒 | gban list | — |
| `.gmute` 🔒 | sab chats me mute | `gm` |
| `.ungmute` 🔒 | gmute hatao | `gunmute` |
| `.gmutelist` 🔒 | gmute list | — |

### `.m9` — protection  (8 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.antidel` | anti-delete on/off | — |
| `.watchspam` | spam guard `3 5` | — |
| `.unwatchspam` | spam guard off | — |
| `.setgpfp` 🔒 | group photo set | — |
| `.autogpfp` 🔒 | photo rotate `10` | — |
| `.stopgpfp` 🔒 | rotation band | — |
| `.rlock` | reply-trigger lock | — |
| `.srlock` | reply lock hatao | — |

### `.m10` — blacklist  (8 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.addbl` | blacklist + | — |
| `.delbl` | blacklist − | — |
| `.listbl` | blacklist list | — |
| `.add-bcdb` 🔒 | broadcast db + | — |
| `.del-bcdb` 🔒 | broadcast db − | — |
| `.list-bcdb` | broadcast db | — |
| `.join` 🔒 | link se join | — |
| `.leave` 🔒 | chat chhodo | — |

### `.m11` — broadcast  (5 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.gcast` 🔒 | sab groups me | — |
| `.ucast` 🔒 | sab users ko | — |
| `.bc` 🔒 | group/all/private/db | — |
| `.autobc` 🔒 | add/on/off/get/del/delay | — |
| `.autofw` 🔒 | add/on/off/get/del/delay | — |

### `.m12` — messaging  (14 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.hy` | stylish greeting | — |
| `.del` | replied msg udao | — |
| `.forward` | msg aage bhejo | — |
| `.save` | channel me seve | — |
| `.savelist` | saved list | — |
| `.fwd` | saved wapas | — |
| `.delsave` | saved delete | — |
| `.setchannel` | save channel set | — |
| `.purge` | reply/<n>/1-999999 | — |
| `.purgeme` | apne msg · `<n>`/`all` | — |
| `.delmine` | apne sab msg | — |
| `.filter` | word auto-reply | — |
| `.filters` | filter list | — |
| `.unfilter` | filter hatao | — |

### `.m13` — auto  (14 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.autoread` | group/private/all on-off | — |
| `.areply` | pm auto-reply | — |
| `.stopareply` | auto-reply band | — |
| `.arreply` | user auto-reply | — |
| `.sarreply` | user reply band | — |
| `.afk` | afk mode | — |
| `.unafk` | afk off | — |
| `.ghost` | apne msg auto-del | — |
| `.echo` | repeat user | — |
| `.unecho` | repeat band | — |
| `.ar` | auto-react (emoji) | `art` |
| `.sar` | auto-react band | `sart` |
| `.art` | auto-reaction | — |
| `.sart` | reaction band | — |

### `.m14` — media  (6 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.yt` | youtube download | — |
| `.ig` | instagram download | — |
| `.pt` | pinterest download | — |
| `.fb` | facebook download | — |
| `.music` | song words/link → mp3 | `mp3`, `play`, `song` |
| `.song` | music alias · auto search | `mp3`, `play` |

### `.m15` — ai & sudo  (5 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.ai` | free ai · koi api key nahi | — |
| `.sudo` 🔒 | sudo banao · addadmin | `addadmin` |
| `.delsudo` 🔒 | sudo hatao · deladmin | `deladmin` |
| `.list` 🔒 | `.list sudo` / `.list bots` | — |
| `.admins` 🔒 | sudo list (alias) | — |

### `.m16` — bot manager  (11 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.addbot` 🔒 | new userbot login `+91…` | — |
| `.c` 🔒 | login code `12345` | `code` |
| `.p` 🔒 | 2fa password | — |
| `.user` 🔒 | connected bots list | — |
| `.resend` 🔒 | code dobara bhejo | `rcode` |
| `.cancelbot` 🔒 | adha login chhodo | `cc` |
| `.delbot` 🔒 | bot remove `+91…/all` | `removebot` |
| `.addbots` 🔒 | @bot1 @bot2 save | — |
| `.listbots` | saved bots | — |
| `.invitebots` 🔒 | bots invite | — |
| `.promotebots` 🔒 | bots promote | — |

### `.m17` — raid  (15 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.reply` | reply raid on | — |
| `.sreply` | reply raid off | — |
| `.rr` | rr raid (🤣) | — |
| `.srr` | rr off | — |
| `.flag` | flag raid | — |
| `.sflag` | flag off | — |
| `.hrr` | heart raid | — |
| `.shrr` | heart off | — |
| `.replygod` | burst raid | — |
| `.sgod` | burst off | — |
| `.nikreply` | <count> <text> | `replynik` |
| `.nik` | sab raid band | `nikstop` |
| `.raidstopall` | everything stop | `stopall` |
| `.stopall` | everything stop | — |
| `.gali` | gali spam <n> | — |

### `.m18` — spam  (9 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.spray` 🔒 | loop message | — |
| `.dspray` 🔒 | loop band | `sspam` |
| `.sspam` 🔒 | loop band (alias) | — |
| `.spam` | <n> <text> | — |
| `.mspam` | <n> media | — |
| `.delayspam` | <delay> <n> <text> | — |
| `.d` | <sec> <text> | — |
| `.purgeall` 🔒 | poori chat udao (sab) | — |
| `.stop` | tagall band | — |

### `.m19` — gc tools  (3 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.fastgc` 🔒 | set <title {emoji}> / stop | — |
| `.copy` 🔒 | profile clone · cp | `cp` |
| `.normal` 🔒 | profile restore · nrml | `nrml` |

### `.m20` — notes  (5 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.notesadd` | note save | — |
| `.noteslist` | note dekho | — |
| `.notesdelete` | note udao | — |
| `.banner` | menu banner set | — |
| `.rembanner` | banner hatao | — |

### `.m21` — stories  (14 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.love1` | college love | — |
| `.love2` | insta love | — |
| `.love3` | office love | — |
| `.love4` | distance love | — |
| `.love5` | shaadi love | — |
| `.lovestory` | classic story | — |
| `.fun1` | chai story | — |
| `.fun2` | exam story | — |
| `.fun3` | cricket story | — |
| `.fun4` | udhaar story | — |
| `.fun5` | flirt story | — |
| `.fun6` | thug life | — |
| `.fun7` | mummy daant | — |
| `.fun8` | sasta nasha | — |

### `.m22` — core  (9 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.menu` | poora command map | — |
| `.alive` | bot status + uptime | — |
| `.ping` | response speed | — |
| `.status` | full runtime report | — |
| `.uptime` | kitna chal rha hai | — |
| `.id` | id grabber · dm auto | — |
| `.info` | user profile · dm auto | — |
| `.help` | quick guide | — |
| `.speed` | animation speed | — |

### `.m23` — baka automation  (11 commands)

| Command | Kya karta hai | Aliases |
|---|---|---|
| `.setbot` 🔒 | auto bot set · setup | `setgame` |
| `.baka` 🔒 | status + rules | `automation`, `bakastatus` |
| `.rob` 🔒 | rob all · `.rob 500` fixed | — |
| `.kill` 🔒 | kill all · `.kill 500` fixed | — |
| `.auto` 🔒 | bal check → rob/kill | — |
| `.autooff` 🔒 | auto band | — |
| `.roboff` 🔒 | rob band | — |
| `.killoff` 🔒 | kill band | — |
| `.stoprob` 🔒 | sab worker band | — |
| `.resetdone` 🔒 | done list clear | — |
| `.solve` 🔒 | verify code `1234` | — |


---

## 🔎 A–Z index

`add-bcdb` 🔒 · `addbl` · `addbot` 🔒 · `addbots` 🔒 · `admins` 🔒 · `afk` · `ai` · `alive` · `antidel` · `ar` (art) · `areply` · `arreply` · `auto` 🔒 · `autobc` 🔒 · `autofw` 🔒 · `autogpfp` 🔒 · `autooff` 🔒 · `autoread` · `baka` 🔒 (automation, bakastatus) · `ban` · `banall` 🔒 · `banner` · `bc` 🔒 · `bomb` · `c` 🔒 (code) · `calc` · `cancelbot` 🔒 (cc) · `copy` 🔒 (cp) · `d` · `del` · `del-bcdb` 🔒 · `delayspam` · `delban` · `delbl` · `delbot` 🔒 (removebot) · `delkick` · `delmine` · `delmute` · `delsave` · `delsudo` 🔒 (deladmin) · `demote` · `dspray` 🔒 (sspam) · `echo` · `emoji` · `endvc` (vcend) · `fact` · `fancy` · `fastgc` 🔒 · `fb` · `filter` · `filters` · `flag` · `flip` · `forward` · `fullpromote` · `fun1` · `fun2` · `fun3` · `fun4` · `fun5` · `fun6` · `fun7` · `fun8` · `fwd` · `gali` · `gban` 🔒 · `gbanlist` 🔒 · `gcast` 🔒 · `getmute` · `ghost` · `gmute` 🔒 (gm) · `gmutelist` 🔒 · `group` · `help` · `hrr` · `hy` · `id` · `ig` · `info` · `invitebots` 🔒 · `ip` · `join` 🔒 · `kick` · `kill` 🔒 · `killall` 🔒 (killeverything, killtasks) · `killoff` 🔒 · `leave` 🔒 · `list` 🔒 · `list-bcdb` · `listbl` · `listbots` · `lock` · `locks` · `love` · `love1` · `love2` · `love3` · `love4` · `love5` · `lovestory` · `menu` · `mspam` · `music` (mp3, play, song) · `mute` (m) · `nik` (nikstop) · `nikreply` (replynik) · `normal` 🔒 (nrml) · `notesadd` · `notesdelete` · `noteslist` · `p` 🔒 · `pin` · `ping` · `promote` · `promotebots` 🔒 · `pt` · `purge` · `purgeall` 🔒 · `purgeme` · `qrcode` · `raidstopall` (stopall) · `rembanner` · `reply` · `replygod` · `resend` 🔒 (rcode) · `resetdone` 🔒 · `rlock` · `rob` 🔒 · `roboff` 🔒 · `roll` · `rps` · `rr` · `sar` (sart) · `sarreply` · `save` · `savelist` · `setbot` 🔒 (setgame) · `setchannel` · `setgpfp` 🔒 · `sflag` · `sgod` · `short` · `shrr` · `slock` · `solve` 🔒 · `spam` · `speed` · `spray` 🔒 · `sreply` · `srlock` · `srr` · `staff` · `startvc` (vcstart) · `status` · `stop` · `stopareply` · `stopgpfp` 🔒 · `stoprob` 🔒 · `style` · `sudo` 🔒 (addadmin) · `tagall` · `tictactoe` · `title` · `tmute` · `tts` · `ttt` · `ucast` 🔒 · `unafk` · `unban` · `unecho` · `unfilter` · `ungban` 🔒 · `ungmute` 🔒 (gunmute) · `unlock` · `unmute` (sm) · `unpin` · `unwatchspam` · `uptime` · `user` 🔒 · `vdelete` (vdel) · `vget` (vpreview) · `vlist` (voicelist) · `vplay` (voiceplay) · `vsave` (voicesave) · `vstop` (vcstop) · `watchspam` · `weather` · `yt`

---

## AI — free, koi API key nahi

`.ai <sawaal>` chalata hai **Pollinations ke anonymous (free) tier** pe:

* **Koi API key / signup / paisa nahi** — seedha kaam karta hai
* Model: `openai-fast` (env `AI_MODEL` se badal sakte ho)
* Persona: **NIK — Hinglish roast boy**
* Reply ke saath bhi chalega: kisi msg pe reply kar ke `.ai`

```bash
export AI_MODEL=openai-fast     # optional
export AI_URL=""                # optional: apna endpoint
```

---

## 🔒 Owner-only commands (51)

Ye sirf `OWNER_ID` wala account chala sakta hai (sudo users nahi):

`add-bcdb` · `addbot` · `addbots` · `admins` · `auto` · `autobc` · `autofw` · `autogpfp` · `autooff` · `baka` · `banall` · `bc` · `c` · `cancelbot` · `copy` · `del-bcdb` · `delbot` · `delsudo` · `dspray` · `fastgc` · `gban` · `gbanlist` · `gcast` · `gmute` · `gmutelist` · `invitebots` · `join` · `kill` · `killall` · `killoff` · `leave` · `list` · `normal` · `p` · `promotebots` · `purgeall` · `resend` · `resetdone` · `rob` · `roboff` · `setbot` · `setgpfp` · `solve` · `spray` · `stopgpfp` · `stoprob` · `sudo` · `ucast` · `ungban` · `ungmute` · `user`

> Baaki saari commands owner + sudo dono chala sakte hain.

---

## Notes

* **`.purgeall`** — **ek hi kaam: poori chat saaf**. Koi count nahi leta
  (`.purgeall 10` bhejo to guide dega). `.purgeall stop` = beech me rok do.
* **`.purge <n>`** — last n messages (1 se 999999 tak).
  **`.purge 1-999999`** — message-id range wale sab.
* **`.purgeme [n|all]`** — is chat me apne messages (default 20, `all` = sab).
  Server search khaali/partial aaye to poora history scan karta hai.
* **`.delmine [n] [@chat]`** — us chat ke apne **saare** messages (same scan logic).
* **`.kick` / `.ban` / `.mute` bina @username** — reply karo, **ya** naam tap karke
  mention karo (`MessageEntityMentionName` → `user_id`), `.kick 123456789` bhi chalega.
* **`.lock` ka result** auto-delete nahi hota (baaki commands ka hota hai).
* **`.purge`** — reply ke saath: replied msg ke niche ka sab. Bina reply: `.purge 200`.
* **`.purgeme <n>`** is chat me apne n messages · **`.delmine [n] [@chat]`** — saare.
* **`.lock <type>` / `.slock`** — `.lock all` aur `.slock` sab members ko mute bhi;
  locked chat me non-admin ka msg **0.3s** me delete. Types: `all msg text media photo
  video document sticker gif audio voice link forward command inline poll contact
  location game dice webpage`
* **`.status`** — bold sections + sirf `─────` separator (mobile pe cut nahi hota).
* **`.info` / `.id`** — reply, `@username`, ya kuch nahi (DM auto-detect).
* Har **status/progress** message ~**3 sec** me auto-delete.
* **`.fwd`** — saved messages me bhejta hai (`.save` se store, `.fwd <n>` se wapas).
* **`.speed <seconds>`** — story animation speed (default `1.6s`).
* **`.nikreply <count> <text>`** (reply ke saath) — N baar wo text · band → `.nik`
* **`.ghost on 30`** — apne outgoing messages 30s me auto-delete (commands chhod kar).
* **Access**: owner + sudo users. Baaki logon ko auto-delete hone wala
  "owner / sudo only" reply.

---

## 🎨 UI

Do styles — default **rail** (mobile-safe, right border hi nahi):

```
┏━ 👑 𝓝𝓲𝓴 𝓤𝓼𝓮𝓻𝓫𝓸𝓽 🔥
┃
┃ 👑 OWNER   ‣ @Nikkkwa
┃ ▰ 🤖 BOT MANAGER ▰ 11
┃  ⚡ addbot   ‣ naya userbot login
┃  ⭐ delbot   ‣ bot hatao
┃
┃ 🔸 powered by @Nikkkwa
┗━━━━━━━━━━━━━━━━━━

har section ka apna custom-emoji (packs se) · emoji ke around gap
```

```bash
export UI_STYLE=box      # purana │ … │ box (ab width-aware, tootega nahi)
```

---

## Files

| File | Kya hai |
|---|---|
| `Nik_userbot.py` | poora bot (single file) |
| `nik.session` | Telegram session (**commit mat karna**) |
| `sub_<number>.session` | login kiye hue sub-userbots |
| `data/` | runtime state (admins, filters, blacklist, gban, locks, baka config…) |
| `data/baka.json` | `.m22` automation config |
| `data/baka_done.json` | rob/kill done list |
| `data/vsave.json` + `data/vsave/` | saved MP3 slots (VC) |
| `FIXES.md` | v2 / v3 changelog (detail me) |

```bash
python Nik_userbot.py          # start
```

> ⚠️ Ye userbot hai — Telegram ToS ke against ho sakta hai. Apna risk.
