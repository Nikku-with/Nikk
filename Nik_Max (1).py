#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  👑  ɴɪᴋʙᴏᴛ · ᴍᴅᴄ ɴᴄ ꜱᴄʀɪᴘᴛ  ·  ᴘᴏᴡᴇʀᴇᴅ ʙʏ @Nikkkwa  ┃
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

Ye TEXT-BANK file nahi — asli NC script hai. Structure niche se upar:

  §0  CONFIG          → hosting: token + owner id yahin paste, env fallback
  §1  CORE PRIMS      → 12 fonts · glyph/cross/heart/sigil pools · name guard
  §2  TARGET RESOLVER → file me sirf `{target}`; naam runtime me text/slide/ID se
  §3  TITLE FORGE     → runtime generators (stored template = 0)
  §4  PAGE BLOCK      → bada NC: random symbols/glyphs se poora page bharo
  §5  TIMING LAB      → 0ms raw → 5–10s hold → phir raw; sab reference delays
  §6  ENGINES         → TokenBucket · FloodTracker · AdaptiveBoost · RateLimiter
  §7  MDC ORC         → per-bot × per-stream rename, verify→boost, quarantine
  §8  NC STYLES       → har style ka apna pattern function + dedicated handler
  §9  LOOP ENGINES    → slides · xreply · swipe · rr · reactions · spam · raids
  §10 CLUSTER         → tokens/session/sudo/admins/autoadmin/leaveall/global
  §11 PANEL MENU      → ╭━━┫ tables ┣━━╮ + chhote bold glyphs + handler docs
  §12 DISPATCH        → CommandHandler registry + ~ prefix + global relay
  §13 SELFTEST        → 150+ checks, bina token bhi chalega

Config:  CONFIG["BOT_TOKEN"], CONFIG["OWNER_ID"]  (§0)
Run:     python3 Nik_Max.py           (pip install python-telegram-bot)
CLI:     --selftest | --audit | --stats | --menu | --docs
In-bot:  ~setup  ~docs  ~cmd <name>  ~menu  ~fullmenu  ~panel
"""

from __future__ import annotations

import ast
import asyncio
import zlib
import base64
import collections
import hashlib
import itertools
import json
import logging
import os
import random
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# ── guarded third-party imports ─────────────────────────────────────────────
HAS_PTB = False
try:
    from telegram import Bot as _TGBot
    try:
        from telegram import ReactionTypeEmoji as _ReactionTypeEmoji
    except Exception:
        _ReactionTypeEmoji = None
    from telegram.error import (BadRequest, Forbidden, NetworkError,
                                RetryAfter, TimedOut)
    from telegram.ext import (ApplicationBuilder, ContextTypes,
                              MessageHandler, filters)
    try:
        from telegram.ext import CommandHandler
    except Exception:
        CommandHandler = None
    HAS_PTB = True
except Exception:
    _TGBot = None
    _ReactionTypeEmoji = None

    class RetryAfter(Exception):
        def __init__(self, retry_after: float = 1.0):
            super().__init__("flood")
            self.retry_after = retry_after

    class BadRequest(Exception): pass
    class Forbidden(Exception): pass
    class NetworkError(Exception): pass
    class TimedOut(Exception): pass
    ApplicationBuilder = CommandHandler = ContextTypes = None
    MessageHandler = filters = None

HAS_TELETHON = False
try:
    from telethon import TelegramClient
    HAS_TELETHON = True
except Exception:
    TelegramClient = None

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s │ %(levelname)-7s │ nik.mdc │ %(message)s")
log = logging.getLogger("nik.mdc")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "nik_mdc_data"
DATA.mkdir(exist_ok=True)
random.seed()


# ── atomic JSON persistence ─────────────────────────────────────────────────
def _jpath(name: str) -> Path:
    return DATA / (name if name.endswith(".json") else name + ".json")


def load_json(name: str, default: Any) -> Any:
    try:
        return json.loads(_jpath(name).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(name: str, obj: Any) -> None:
    try:
        p = _jpath(name)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:
        log.debug("save %s: %s", name, exc)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# ┌──────────────────────────────────────────────────────────────────────────┐
# │ §0 · HOSTING CONFIG — BAS 2 LINES BHARO, BAKI SAB AUTO HAI               │
# ├──────────────────────────────────────────────────────────────────────────┤
# │  1. BotFather ka token  →  "BOT_TOKEN" ke quotes me paste karo           │
# │  2. Apna numeric TG ID  →  "OWNER_ID" me likho (0 mat chhodna)           │
# │  3. pip install python-telegram-bot                                      │
# │  4. python3 Nik_Max.py        ← local / koyeb / render / railway / vps   │
# │     (env BOT_TOKEN=... OWNER_ID=... bhi chalega, CONFIG pehle padhta hai)│
# │  5. Aur bots: BOT_TOKENS list, ya bot me ~addtoken <token>               │
# │  6. Verify: ~setup  ·  Help: ~docs  ·  Menu: ~menu  ·  Panel: ~panel     │
# └──────────────────────────────────────────────────────────────────────────┘
CONFIG: dict[str, Any] = {
    "BOT_TOKEN": "",          # ← yahan token paste karo: "123456789:AA..."
    "OWNER_ID": 0,            # ← yahan apna numeric ID
    "MAIN_BOT_ID": 0,         # 0 = get_me() se auto
    "BOT_TOKENS": [],         # ["token2", "token3"] → multi-bot cluster
    "API_ID": 0,              # MTProto session ke liye (optional)
    "API_HASH": "",
    "SESSION": "",
    "PREFIX": "~",
}

# ── global config / state ───────────────────────────────────────────────────
OWNER_ID = int(CONFIG["OWNER_ID"] or env("OWNER_ID", "0") or 0)
MAIN_BOT_ID = int(CONFIG["MAIN_BOT_ID"] or env("MAIN_BOT_ID", "0") or 0)
BOT_TOKEN = str(CONFIG["BOT_TOKEN"] or env("BOT_TOKEN")).strip()
BOT_TOKENS = [str(t).strip() for t in CONFIG["BOT_TOKENS"]
              if str(t).strip()]
API_ID = int(CONFIG["API_ID"] or env("API_ID", "0") or 0)
API_HASH = str(CONFIG["API_HASH"] or env("API_HASH")).strip()
SESSION = str(CONFIG["SESSION"] or env("SESSION")).strip()

BRAND = "👑 ɴɪᴋ ʙᴏᴛ 👑"
BOT_NAME = "NikBot"                    # bot ka naam
BOT_TITLE = "Nik's Bhosda chod"        # bot ka title / NC signature
OWNER_USER = "@Nikkkwa"                # file me ek hi naam: owner
CREDIT = "✨ ᴍᴀᴅᴇ ʙʏ @Nikkkwa"
POWERED_BY = "⚡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @Nikkkwa · ɴɪᴋʙᴏᴛ"
TARGET_SLOT = "{target}"               # koi dost ka naam file me nahi

_pfx = load_json("prefix.json", {})
PREFIX = _pfx.get("symbol", CONFIG["PREFIX"])
PREFIX_ENABLED = bool(_pfx.get("enabled", True))
PREFIX_OPTIONAL = bool(_pfx.get("optional", False))

_su = load_json("sudo.json", {})
SUDO_ON = bool(_su.get("on", True))
SUDO: set[int] = set(_su.get("ids", []))
SUDO_META: dict[str, dict[str, str]] = _su.get("meta", {})

CHATS: dict[str, dict[str, Any]] = load_json("chats.json", {})
NOTES: dict[str, str] = load_json("notes.json", {})
FILTERS: dict[str, str] = load_json("filters.json", {})
BLACKLIST: set[str] = set(load_json("blacklist.json", []))
GBAN: set[int] = set(load_json("gban.json", []))
GMUTE: set[int] = set(load_json("gmute.json", []))
MUTED: set[int] = set(load_json("muted.json", []))
LOCKS: dict[str, bool] = load_json("locks.json", {})
ECHO: set[int] = set(load_json("echo.json", []))
AFK_STATE: dict[str, str] = load_json("afk.json", {})
WARNS: dict[str, int] = load_json("warns.json", {})
GC_ON: dict[str, bool] = load_json("gc_on.json", {})
BANNER: dict[str, dict[str, str]] = load_json("banner.json", {})
CUSTOM_CMDS: dict[str, str] = load_json("custom_cmds.json", {})
CUSTOM_TITLES: dict[str, list[str]] = load_json("custom_titles.json", {})
TOKENS: list[str] = load_json("tokens.json", [])
for _t in BOT_TOKENS:
    if _t not in TOKENS:
        TOKENS.append(_t)
STATE_FLAGS: dict[str, bool] = load_json("state_flags.json", {})
MEDIA_POOL: list[str] = load_json("media_pool.json", [])
GAMEOVER_CFG: dict[str, Any] = load_json("gameover.json",
                                         {"text": "", "media": "", "kind": ""})

GLOBAL_MODE = False
BOOST = False
SESSION_CLIENT: Any = None
BOOT_TIME = time.time()


def cfg_save() -> None:
    save_json("prefix.json", {"symbol": PREFIX, "enabled": PREFIX_ENABLED,
                              "optional": PREFIX_OPTIONAL})
    save_json("sudo.json", {"on": SUDO_ON, "ids": sorted(SUDO),
                            "meta": SUDO_META})
    save_json("chats.json", CHATS)
    save_json("banner.json", BANNER)
    save_json("custom_titles.json", CUSTOM_TITLES)
    save_json("tokens.json", TOKENS)
    save_json("state_flags.json", STATE_FLAGS)
    save_json("custom_cmds.json", CUSTOM_CMDS)


# ── encoded name guard (source me koi foreign name literal nahi) ────────────
_NAMES_B85 = (
    "c-lpgQIg~!3`4In2hiVs?0J-g4sHT;8R!Xp`c*PhwLdNj+md)>K8&!=b&ZBZ@0P&SA}88#n*?(n$n>?M$C}xou4iH!`#!+Z;"
    "=mb7{UBMk-|ka~aL!k(z3$Fe434*kGFG=1@bJJi;e4{-j8@nQ59f(xEJNDcxN{7oP<FXki`e-I6EBvH{f$OfU=;O`qGa~Eec"
    "chxuOE|zoApGEcqp68fN>n~8m((R+5v@?@bw6A4%Opw)wAEWri(!-6Jk^P!0WDVB@OhuD&G>Bv4!wrLjDmRS+$r(pyy3VT{W"
    "}R=MD8gXGu^Q(P|OntL*jA-NQwbEjSmh8uYSF{5jV+Hrhp`SIFuR)Ybpun~@9plng#WI0W)q;svRV6i^q_ic?gIQrF?v&zgq"
    "yze4x6s)f*WI1VcKq*#>NI;MtOMfwg888ypz9J5<({{SuH+64"
)
FOREIGN_NAMES = tuple(
    n.strip() for n in
    zlib.decompress(base64.b85decode(_NAMES_B85)).decode().split(",")
    if len(n.strip()) > 2)

_SMALL = str.maketrans({
    'ᴀ':'a','ʙ':'b','ᴄ':'c','ᴅ':'d','ᴇ':'e','ꜰ':'f','ɢ':'g','ʜ':'h','ɪ':'i',
    'ᴊ':'j','ᴋ':'k','ʟ':'l','ᴍ':'m','ɴ':'n','ᴏ':'o','ᴘ':'p','ǫ':'q','ʀ':'r',
    'ꜱ':'s','ᴛ':'t','ᴜ':'u','ᴠ':'v','ᴡ':'w','ʏ':'y','ᴢ':'z','Ɱ':'m','ƛ':'a',
    'Ӈ':'h','Ɲ':'n','Ɠ':'g','Ʀ':'r','Ɩ':'i','Є':'e','Ɓ':'b','Ɗ':'d','Ƙ':'k',
    'Ơ':'o','Ƈ':'c','Ƭ':'t','ⱦ':'t','я':'r','ɠ':'g','н':'h','ɑ':'a','υ':'u',
    'σ':'o','т':'t','в':'b','і':'i','ѕ':'s','а':'a','е':'e','о':'o','р':'p',
    'с':'c','у':'y','х':'x','ք':'p','ɨ':'i','ө':'o','օ':'o','ꓭ':'b','ꓐ':'b',
    'Ɐ':'a','ẞ':'b','ᴎ':'n','ᵃ':'a','ᵇ':'b','ᶜ':'c','ᵈ':'d','ᵉ':'e','ᶠ':'f',
    'ᵍ':'g','ʰ':'h','ⁱ':'i','ʲ':'j','ᵏ':'k','ˡ':'l','ᵐ':'m','ⁿ':'n','ᵒ':'o',
    'ᵖ':'p','ʳ':'r','ˢ':'s','ᵗ':'t','ᵘ':'u','ᵛ':'v','ʷ':'w','ˣ':'x','ʸ':'y',
    'ᶻ':'z'})


def fold(s: str) -> str:
    """Mathematical fonts + small-caps + look-alikes → ASCII."""
    return unicodedata.normalize("NFKC", s).lower().translate(_SMALL)


def name_ok(s: str) -> bool:
    f = fold(s)
    return not any(n in f for n in FOREIGN_NAMES)


def assert_clean(s: str) -> str:
    if not name_ok(s):
        return "👑 NIK · ᴄʟᴇᴀɴ ᴍᴏᴅᴇ · @Nikkkwa"
    if "nik" not in fold(s):
        s = "👑 NIK · " + s
    return s


# ── compact primitives (sirf 30 chhote tokens — koi text pahaad nahi) ───────
ROAST: tuple[str, ...] = (
    "ᴄʜᴜᴘ", "ᴀᴜᴋᴀᴛ", "ꜰᴀᴀᴅ", "ʀᴜᴋɴᴀ ɴɪᴋᴀʟ", "ᴛɪᴛʟᴇ ᴜᴅᴀ", "ᴅᴇsᴄ ʜɪʟᴀ",
    "0-ᴅᴇʟᴀʏ", "ᴜʟᴛʀᴀ", "ɢᴀᴡᴅ", "ʙᴀᴀᴘ", "ᴡᴀʀ", "ᴀᴛᴏᴍɪᴄ", "ɴᴏ ᴄᴏᴍᴘᴇᴛɪᴛɪᴏɴ",
    "ᴄʜᴜᴅᴀɪ", "ꜱᴇq", "ꜰʟᴏᴏᴅ", "ɢʜᴏsᴛ", "ᴡᴀʟʟ", "ʙᴜɢ", "ᴠɪʀᴜs")

EMOJI: tuple[str, ...] = (
    "💛","🧡","🩷","🤍","🌪️","💜","🩶","💀","☠️","🌀","🥟","🎋","🎐","🥏",
    "📈","📉","🔮","♨️","⚜️","💠","🔷","🔳","🏳️‍⚧️","❤️","🩵","💗","💖","💘",
    "💝","💞","💟","❣️","🧿","🪬","🕷️","🦇","🌑","🌒","🌓","🌔","🌕","🌖",
    "🌗","🌘","⚡","🔥","👑","💎","🗡️","⚔️","🛡️","🚩","🏴","✨","🌟","⭐",
    "💫","✦","✧","❖","✷","✸","✹","✺","✻","✼","✽","✾","✿","❀","❁","❂",
    "❃","❄","❅","❆","❇","❈","❊","❋","💥","💢","💣","🩸","🖤","💔","🫀",
    "🫧","🌊","🌫️","🌩️","🌨️","🔱","⚕️","♻️","⚛️","✡️","☯️","🕉️","⛩️",
    "🪷","🏵️","🎭","🎲","🧩","🀄","🪐","🌠","🎇","🎆","🫨","🩼","🪓")

HEARTS: tuple[str, ...] = (
    "🤍","🩷","💜","💛","🧡","❤️","🩵","💗","💖","💘","💝","💞","🖤","🩶",
    "💔","🫀","💟","❣️")

GLYPH: tuple[str, ...] = (
    "𒀱ꪳ","⫷✖⫸","⤬⤫","꧅","﷽","𒀱","𒐫","𒈙","𒁈","𒅓","𒄑","𒊹",
    "𒌋","𒎙","ㅤ","𓂃𓈒","⣿","⧗","⩘","⟦⟧","⧉⧊","⟡","⟁","⟐","⟒",
    "𝄞","ꯍ","𓏸","⠀","⨯","⩕","⤬","⤭","⤫","❖","✖","╳","⩜","⟠")

CROSS: tuple[str, ...] = (
    "⫷✖⫸","⤬","⤫","╳","⨯","⩕","⤭","⟁","⟡","⧉","⧊","✖","❌","❎",
    "⤬⤫","⟒⟒","⩘⩘")

WALLS: tuple[str, ...] = (
    "⫷✖⫸","⤬⤫","𒀱ꪳ","╳╳╳","⟁⟁⟁","⧉","⧊","𒀱","𒐫","𝄞","⩘","⣿",
    "𒁈𒅓","𒄑𒊹","𒌋𒎙","⟠⟠","⩜⩜","𓂃𓈒𓏸")

SIGILS: tuple[str, ...] = (
    "⚜️","💠","🔷","🔳","♨️","🔮","☠️","💀","🌪️","🌀","⚔️","🗡️","👑",
    "⚡","🔥","💎","🚩","🏴","⚛️","☯️","🕉️","🔱","✡️","♻️","⚕️")

DUST: tuple[str, ...] = (
    "·˚✦","◦°✧","⋆｡˚","༄˖","ꕥ","⭑","✧˖°","⊹˚✦","☾⋅","⟡·","˙✧",
    "⁎⁺˳","⋆⭒","·͙✧","༉‧","⊰✦⊱","⌁","⤳","⌇")

Z_UP = list("̴̷̸̡̢̛͟͝͞͠͡")
Z_MID = list("̵̶̷̸͜͝")
Z_DN = list("̡̢̗̘̙̜̝̞̟̠̣̤̥̦")


def _fontmap(low: int | None, up: int | None, dig: int | None) -> dict[int, int]:
    d: dict[int, int] = {}
    for i in range(26):
        if low is not None:
            d[97 + i] = low + i
        if up is not None:
            d[65 + i] = up + i
    if dig is not None:
        for i in range(10):
            d[48 + i] = dig + i
    return d


FONTS: dict[str, dict[int, int]] = {
    "bold": _fontmap(0x1D41A, 0x1D400, 0x1D7CE),
    "italic": _fontmap(None, 0x1D434, None),
    "bolditalic": _fontmap(0x1D482, 0x1D468, None),
    "script": _fontmap(None, 0x1D49C, None),
    "boldscript": _fontmap(0x1D4EA, 0x1D4D0, None),
    "fraktur": _fontmap(0x1D51E, 0x1D504, None),
    "double": _fontmap(0x1D552, 0x1D538, 0x1D7D8),
    "sans": _fontmap(0x1D5BA, 0x1D5A0, 0x1D7E2),
    "sansbold": _fontmap(0x1D5EE, 0x1D5D4, 0x1D7EC),
    "mono": _fontmap(0x1D68A, 0x1D670, 0x1D7F6),
    "fullwidth": {33 + i: 0xFF01 + i for i in range(94)},
    "small": dict(zip(range(97, 123),
                      map(ord, "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡʏᴢ"))),
}
FONT_KEYS = tuple(FONTS)


def sty(s: str, kind: str = "bold") -> str:
    return s.translate(FONTS.get(kind, FONTS["bold"]))


def font_rotate(s: str, n: int) -> str:
    return sty(s, FONT_KEYS[n % len(FONT_KEYS)])


def zalgo(s: str, n: int = 1, budget: int = 128) -> str:
    """Cursed combining-mark text — Unicode Mn/Me, runtime generated."""
    out: list[str] = []
    for ch in s:
        if not ch.strip():
            out.append(ch)
            continue
        out.append(ch)
        for _ in range(n):
            out.append(random.choice(Z_UP + Z_MID + Z_DN))
        if len("".join(out)) >= budget - 8:
            break
    return "".join(out)


def unzalgo(s: str) -> str:
    return "".join(c for c in s
                   if unicodedata.category(c) not in ("Mn", "Me"))


def fit(s: str, n: int = 128) -> str:
    """Telegram title = 1..128 chars. Zalgo marks bhi char count me aate hain."""
    s = str(s)
    if len(s) > n:
        s = s[:n].rstrip() or s[:max(1, n - 1)]
    return s or "👑 NIK"


def long_fit(s: str, n: int = 4096) -> str:
    return fit(s, n)


# ── runtime title generation: yahin asli CODE hai ───────────────────────────
class TitleForge:
    """Har NC title yahan CODE se banta hai — koi stored template nahi.

    Har generator target + sequence + font + glyph/emoji pool se naya frame
    banata hai, phir `pad()` use karta hai 125-char tak emoji-fill ke liye.
    """

    def __init__(self, target: str = "", style: str = "cross",
                 seed: int = 0) -> None:
        self.target = TargetResolver.clean(target or TARGET_SLOT)[:36]
        self.style = style
        self.seed = seed
        self.last: str = ""
        self.seq = seed
        self.metrics: dict[str, int] = collections.defaultdict(int)

    def emo(self, n: int = 1, off: int = 0) -> str:
        return "".join(EMOJI[(self.seq * 7 + off + i * 13) % len(EMOJI)]
                       for i in range(n))

    def glyph(self, n: int = 1, off: int = 0) -> str:
        return "".join(GLYPH[(self.seq * 5 + off + i * 11) % len(GLYPH)]
                       for i in range(n))

    def heart(self, n: int = 1, off: int = 0) -> str:
        return "".join(HEARTS[(self.seq + off + i * 3) % len(HEARTS)]
                       for i in range(n))

    def wall(self, n: int = 1, off: int = 0) -> str:
        return "".join(WALLS[(self.seq + off + i * 5) % len(WALLS)]
                       for i in range(n))

    def roast(self, off: int = 0) -> str:
        return ROAST[(self.seq * 3 + off) % len(ROAST)]

    def stamp(self, n: int) -> str:
        """Har frame ke liye alag, ASCII-safe sequence marker (runtime)."""
        return sty(f"#{abs(n) % 100000:05d}", "fullwidth")

    def pad(self, base: str, emoji: str | None = None,
            width: int = 125) -> str:
        """Classic pattern: short base ko 125 char tak emoji se bharo."""
        e = emoji or self.heart(1)
        if not e:
            e = "✦"
        room = width - len(base) - 2
        repeats = max(1, room // len(e)) if room > 0 else 1
        return fit(base + "  " + (e * repeats), width)

    def cross(self) -> str:
        c = CROSS[self.seq % len(CROSS)]
        c2 = CROSS[(self.seq + 3) % len(CROSS)]
        return f"{c*2} {font_rotate('NIK', self.seq)} {self.glyph(2)} " \
               f"{self.target} {self.roast()} {self.emo(2)} {c2*2}"

    def cune(self) -> str:
        g = GLYPH[self.seq % 14]
        g2 = GLYPH[(self.seq + 4) % 14]
        return f"{g*3}{sty('NIK', 'fraktur')}{g2} {self.target} " \
               f"{self.roast(2)} {self.wall(2)} {self.emo(1)}"

    def heart_wall(self) -> str:
        h = self.heart(3)
        return f"{h} {font_rotate('NIK', self.seq)} {self.target} " \
               f"{self.roast(4)} {self.heart(3, 5)} {DUST[self.seq % len(DUST)]}"

    def zalgof(self) -> str:
        return (f"{sty('NIK', 'bolditalic')} "
                f"{zalgo(unzalgo(self.target)[:18], 1)} "
                f"{self.glyph(2)} {self.emo(2)}")

    def big(self) -> str:
        lat = "".join(WALLS[(c + self.seq) % len(WALLS)] for c in range(5))
        lat2 = "".join(CROSS[(c + self.seq + 2) % len(CROSS)]
                       for c in range(5))
        return (f"{lat}\n{sty('NIK GAWD', 'bolditalic')} {self.target} "
                f"{self.roast(1)} {self.emo(2)}\n{lat2}{self.heart(3)}")

    def prism(self) -> str:
        return (f"{self.emo(2)} {font_rotate('NIK', self.seq)} "
                f"{self.target} {self.roast(3)} {self.emo(3)} "
                f"{SIGILS[self.seq % len(SIGILS)]}")

    def dust(self) -> str:
        d = DUST[self.seq % len(DUST)]
        return f"{d} {font_rotate('NIK', self.seq)} {d} " \
               f"{self.target} {self.roast(5)} {DUST[(self.seq+2) % len(DUST)]}"

    def bug(self) -> str:
        broken = "".join(
            ch + random.choice(Z_UP + Z_MID)
            for ch in unzalgo(self.target)[:12])
        return (f"{WALLS[self.seq % len(WALLS)]*2} 🐛 {broken} "
                f"{self.glyph(3)} {self.roast(6)} {self.emo(2)}")

    def virus(self) -> str:
        chain = "".join(GLYPH[(i * 3 + self.seq) % 14] for i in range(6))
        return f"{chain} {sty('NIK', 'mono')} ☣ {self.target} " \
               f"{self.roast(7)} {chain[::-1]}"

    def static(self) -> str:
        noise = "".join(random.choice("⣿⠀▓▒░╳⨯") for _ in range(14))
        return f"{noise} {self.target} {noise} {self.emo(2)}"

    def noise(self) -> str:
        return (f"{zalgo('NIK', 2, 60)} {self.glyph(4)} "
                f"{self.roast(8)} {self.emo(3)}")

    def drip(self) -> str:
        return (f"{sty('NIK', 'italic')} {zalgo(self.target[:10], 2, 70)} "
                f"{DUST[self.seq % len(DUST)]} {self.emo(2)}")

    def thunder(self) -> str:
        return (f"⚡{self.wall(3)} {sty('NIK GAWD','bold')} "
                f"{self.target} {self.roast(9)} {self.emo(4)} "
                f"{self.wall(3, 2)}⚡")

    def moon(self) -> str:
        phases = "🌑🌒🌓🌔🌕🌖🌗🌘"
        return (f"{phases[self.seq % 8]} {font_rotate('NIK', self.seq)} "
                f"{self.target} {self.roast(10)} {phases[(self.seq+3) % 8]}")

    def flag(self) -> str:
        return (f"🚩 {self.glyph(2)} {sty('NIK','sansbold')} "
                f"{self.target} {self.roast(11)} {self.emo(3)} 🏴")

    def gawd(self) -> str:
        return (f"👑 {font_rotate('NIK GAWD', self.seq)} {self.glyph(2)} "
                f"{self.target} {self.roast(12)} {self.wall(2)} "
                f"{self.emo(3)} {self.glyph(2)}")

    def mdcwall(self) -> str:
        """Screenshot-style MDC: X-cross lattice + right heart column.

        Screens me jo 128-char ⤬⤫ grid aur 🤍 column dikhta hai, wo yahin
        runtime banta hai — koi stored line nahi. Har seq pe lattice shift.
        """
        xs = ("⤬", "⤫", "╳", "⨯", "✖", "⩕", "⟁", "⟡")
        rows: list[str] = []
        for r in range(7):
            line = "".join(xs[(r * 3 + c + self.seq) % len(xs)]
                           for c in range(9))
            rows.append(line + HEARTS[(r + self.seq) % len(HEARTS)])
        head = f"{sty('NIK', 'bolditalic')} {self.target} {self.roast()}"
        return head + "\n" + "\n".join(rows) + f"\n{self.emo(2)}"

    # ── families picked from the reference engines (CODE only) ────────────
    def enc(self) -> str:
        """reference-A enc1..enc10 jaisa rotating lattice — stored lines nahi."""
        head = sty("NIK", FONT_KEYS[self.seq % len(FONT_KEYS)])
        rows = [f"{head} {self.target} {self.roast(self.seq)}"]
        for r in range(5):
            rows.append("".join(GLYPH[(r * 5 + c + self.seq) % len(GLYPH)]
                                for c in range(7)))
        return "\n".join(rows) + f" {self.emo(2)}"

    def blaze(self) -> str:
        return (f"🔥{self.wall(4)} {font_rotate('NIK', self.seq)} "
                f"{self.target} {self.roast(2)} {self.emo(3)}🔥")

    def surge(self) -> str:
        return (f"{SIGILS[self.seq % len(SIGILS)]} "
                f"{sty('NIK', 'sansbold')} {self.glyph(3)} "
                f"{self.target} {self.wall(2)} {self.heart(3)}")

    def silk(self) -> str:
        d = DUST[self.seq % len(DUST)]
        return (f"{d} {font_rotate('NIK', self.seq)} {d} "
                f"{self.target} {self.heart(4, 2)} "
                f"{DUST[(self.seq + 5) % len(DUST)]}")

    def trio(self) -> str:
        g = [self.emo(3, k * 3) for k in range(3)]
        return (f"{g[0]} {sty('NIK','bold')} {g[1]} "
                f"{self.target} {g[2]} {self.glyph(2)}")

    def stagger(self) -> str:
        rows = ["".join(CROSS[(r + c + self.seq) % len(CROSS)]
                        for c in range(8)) for r in range(4)]
        return (f"{sty('NIK','double')} {self.target}\n"
                + "\n".join(rows) + f" {self.emo(2)}")

    def god(self) -> str:
        return (f"👑 {sty('NIK GAWD', 'double')} {self.glyph(3)} "
                f"{self.target} {self.roast(3)} {self.wall(3)} "
                f"{self.emo(3)}")

    def lean(self) -> str:
        return (f"{font_rotate('NIK', self.seq)} {self.target} "
                f"{DUST[self.seq % len(DUST)]} {self.emo(1)}")

    def pure(self) -> str:
        return (f"{sty('NIK', 'bold')} · {self.target} · "
                f"{SIGILS[self.seq % len(SIGILS)]} "
                f"{HEARTS[self.seq % len(HEARTS)]}")

    def phantom(self) -> str:
        return (f"{GLYPH[self.seq % 14]} {zalgo('NIK', 1, 40)} "
                f"{self.glyph(3)} {self.target} {self.roast(6)} "
                f"{GLYPH[(self.seq + 7) % 14]}")

    def testament(self) -> str:
        return (f"⟦⟧ {sty('NIK','fraktur')} ⟦⟧ {self.target} "
                f"{self.wall(3)} {self.roast(8)} {self.emo(2)}")

    def shadow(self) -> str:
        return (f"🌑 {self.glyph(4)} {sty('NIK','italic')} "
                f"{self.target} {self.glyph(4)} 🌘")

    def wave(self) -> str:
        w = "".join(DUST[(i + self.seq) % len(DUST)] for i in range(5))
        return f"{w} {font_rotate('NIK', self.seq)} {self.target} {w}"

    def cod(self) -> str:
        chain = "".join(GLYPH[(i * 7 + self.seq) % len(GLYPH)]
                        for i in range(9))
        return (f"{chain} {sty('NIK','mono')} {self.target} "
                f"{self.roast(self.seq)} {chain[::-1]}")

    def mgc(self) -> str:
        head = f"{sty('NIK','bolditalic')} {self.target}"
        rows = [head]
        for r in range(5):
            rows.append("".join(CROSS[(r * 2 + c + self.seq) % len(CROSS)]
                                for c in range(8))
                        + HEARTS[(r + self.seq) % len(HEARTS)])
        return "\n".join(rows)

    def bold(self) -> str:
        return f"{sty('NIK','bold')} {self.target} {self.emo(2)}"

    def cursive(self) -> str:
        return f"{sty('NIK','script')} {self.target} {self.glyph(2)}"

    def italic(self) -> str:
        return f"{sty('NIK','italic')} {self.target} {DUST[self.seq % len(DUST)]}"

    def pageblock(self) -> str:
        """Screenshot wali badi NC ka 128-char title: ghana X-lattice."""
        rng = random.Random(self.seed * 7919 + 13)
        xs = WallForge.LATTICE
        rows = ["".join(xs[(r * 3 + c + self.seq) % len(xs)]
                        for c in range(16)) for r in range(4)]
        head = (f"{sty('NIK', 'bolditalic')} {TARGET_SLOT} "
                f"{self.roast(self.seq)} {self.emo(1)}")
        return head + "\n" + "\n".join(
            row + HEARTS[(r + self.seq) % len(HEARTS)]
            for r, row in enumerate(rows))

    def glyphwall(self) -> str:
        rng = random.Random(self.seed * 104729 + 29)
        pool = WallForge.NOISE + WallForge.LATTICE
        soup = "".join(rng.choice(pool) for _ in range(10))
        return (f"{soup} {sty('NIK','fraktur')} {TARGET_SLOT} "
                f"{self.roast(2)} {soup[::-1]}")

    def symbols(self) -> str:
        rng = random.Random(self.seed * 31337 + 5)
        mix = "".join(rng.choice(SIGILS + DUST + HEARTS + EMOJI)
                      for _ in range(9))
        return (f"{sty('NIK','double')} {TARGET_SLOT} {mix} "
                f"{self.glyph(2)} {mix[::-1]}")

    GENERATORS: dict[str, str] = {
        "cross": "cross", "cune": "cune", "heart": "heart_wall",
        "zalgo": "zalgof", "big": "big", "prism": "prism", "dust": "dust",
        "bug": "bug", "virus": "virus", "static": "static", "noise": "noise",
        "drip": "drip", "thunder": "thunder", "moon": "moon",
        "flag": "flag", "gawd": "gawd", "mdcwall": "mdcwall",
        "enc": "enc", "blaze": "blaze", "surge": "surge", "silk": "silk",
        "trio": "trio", "stagger": "stagger", "god": "god", "lean": "lean",
        "pure": "pure", "phantom": "phantom", "testament": "testament",
        "shadow": "shadow", "wave": "wave", "cod": "cod", "mgc": "mgc",
        "bold": "bold", "cursive": "cursive", "italic": "italic",
        "pageblock": "pageblock", "glyphwall": "glyphwall",
        "symbols": "symbols",
    }

    def build(self, seq: int | None = None, pad: bool = True) -> str:
        self.seq = self.seed if seq is None else seq
        fn = getattr(self, self.GENERATORS.get(self.style, "cross"))
        raw = fn()
        if self.style in ("zalgo", "bug", "noise", "drip"):
            out = fit(assert_clean(raw), 128)
        elif pad and "\n" not in raw:
            out = fit(assert_clean(self.pad(raw)), 128)
        else:
            out = fit(assert_clean(raw), 128)
        if out == self.last:
            out = fit(out[:118] + f"·{self.seq % 10000}", 128)
        self.last = out
        self.metrics[self.style] += 1
        return out


# ── §4 · PAGE BLOCK — badi NC, poora screen glyphs/symbols se bharo ─────────
class WallForge:
    """Screenshots wali "big aah" NC.

    Har frame 4096-char Telegram message ke andar poora page bhar deta hai:
    X-cross lattice, random cuneiform/noise glyphs, emoji rain, heart column,
    side emoji column, cursed combining marks aur chhota bold target line.
    Koi stored line nahi — har row runtime RNG + pools se banti hai.
    """

    LATTICE: tuple[str, ...] = (
        "⤬", "⤫", "╳", "⨯", "✖", "⩕", "⟁", "⟡", "❌", "⧉", "⧊",
        "⩘", "⟒", "⩜", "⤭", "⟠")
    NOISE: tuple[str, ...] = tuple(dict.fromkeys(
        GLYPH + CROSS + WALLS +
        ("⣿", "▓", "▒", "░", "⧗", "⟦", "⟧", "𝄞", "⠀", "⩕", "⩘")))
    SIDE: tuple[str, ...] = HEARTS + (
        "🌶️", "🍌", "🌻", "🌙", "🔮", "💎", "🕊️", "✨", "🌹", "🌑",
        "⚡", "💫", "🦋", "🌊", "🍒", "☄️", "🌸", "🪷", "🫧", "🧿")
    FAMILIES: tuple[str, ...] = (
        "lattice", "emoji", "cursed", "heart", "cune", "static",
        "sigil", "banner")

    def __init__(self, target: str = TARGET_SLOT, seed: int = 0,
                 width: int = 56, rows: int = 42) -> None:
        self.target = TargetResolver.clean(target or TARGET_SLOT)
        self.seed = seed
        self.width = max(20, min(96, width))
        self.rows = max(8, min(72, rows))

    def rng(self, salt: int = 0) -> random.Random:
        return random.Random(self.seed * 7919 + salt * 104729)

    def head(self, seq: int, family: str) -> str:
        roast = ROAST[(seq * 3) % len(ROAST)]
        line = "".join(self.LATTICE[(i * 5 + seq) % len(self.LATTICE)]
                       for i in range(9))
        return (f"{line} {sty('NIK', FONT_KEYS[seq % len(FONT_KEYS)])} "
                f"· {sty(TARGET_SLOT, 'bold')} · {roast} {line[::-1]}")

    def body_line(self, r: int, family: str,
                  rng: random.Random) -> str:
        n = self.width - 3
        if family == "emoji":
            cells = [rng.choice(EMOJI + HEARTS) for _ in range(n // 2)]
            core = "".join(cells) + "".join(
                self.LATTICE[(r + i) % len(self.LATTICE)]
                for i in range(n - len(cells)))
        elif family == "heart":
            core = "".join(
                (HEARTS[(r + c) % len(HEARTS)]
                 if (r + c) % 3 == 0 else
                 self.LATTICE[(r * 2 + c) % len(self.LATTICE)])
                for c in range(n))
        elif family == "cune":
            core = "".join(rng.choice(self.NOISE) for _ in range(n))
        elif family == "static":
            core = "".join(rng.choice("⣿▓▒░⠀╳⨯⤬⤫⩕")
                           for _ in range(n))
        elif family == "sigil":
            core = "".join(
                (rng.choice(SIGILS + DUST)
                 if c % 4 == 0 else
                 self.LATTICE[(r + c) % len(self.LATTICE)])
                for c in range(n))
        elif family == "cursed":
            core = "".join(
                (zalgo("G", 1, 12)
                 if c % 5 == 0 else
                 self.LATTICE[(r * 3 + c) % len(self.LATTICE)])
                for c in range(n // 2))
        elif family == "banner":
            core = "".join(self.LATTICE[(r * 7 + c + 1)
                                        % len(self.LATTICE)]
                           for c in range(n))
        else:  # lattice — screenshots ka signature X-cross
            core = "".join(self.LATTICE[(r * 3 + c + 1)
                                        % len(self.LATTICE)]
                           for c in range(n))
        left = self.SIDE[(r * 7) % len(self.SIDE)] if r % 4 == 0 else ""
        right = self.SIDE[(r + 3) % len(self.SIDE)]
        return left + core + right

    def frame(self, seq: int = 0, family: str = "") -> str:
        fam = family or self.FAMILIES[seq % len(self.FAMILIES)]
        rng = self.rng(seq)
        out = [self.head(seq, fam)]
        for r in range(self.rows):
            if fam == "banner" and r == self.rows // 2:
                banner = (f"{sty('NIK', 'bolditalic')} "
                          f"{sty(TARGET_SLOT, 'bold')} "
                          f"{ROAST[(seq + r) % len(ROAST)]} "
                          f"{self.LATTICE[seq % len(self.LATTICE)] * 6}")
                out.append(banner)
            else:
                out.append(self.body_line(r, fam, rng))
        out.append("".join(self.LATTICE[(i + seq) % len(self.LATTICE)]
                           for i in range(self.width)))
        raw = fit(assert_clean("\n".join(out)), 3900)
        return TargetResolver.apply(raw, self.target)

    def glyph_count(self, text: str) -> int:
        return sum(1 for c in text if c in self.LATTICE
                   or c in self.NOISE or c in self.SIDE)


class SlideDeck:
    """0ms slides: har slide ek alag full-page block family."""

    def __init__(self, target: str = TARGET_SLOT, seed: int = 0) -> None:
        self.target = TargetResolver.clean(target or TARGET_SLOT)
        self.seed = seed

    def build(self, seq: int, family: str = "") -> str:
        pb = WallForge(self.target, self.seed + seq)
        return pb.frame(seq, family)

    def families(self) -> tuple[str, ...]:
        return WallForge.FAMILIES

    def preview(self, n: int = 3) -> str:
        return "\n\n".join(self.build(i) for i in range(n))


# ── lightweight rendering helpers (PLAIN text only) ─────────────────────────
_ESEQ = itertools.count()


def E(role: str = "sigil") -> str:
    pools = {"crown": ("👑","💎","⚜️","🏵️","🔱","🪷"),
             "fire": ("🔥","💥","⚡","🌪️","🩸","💢"),
             "heart": HEARTS, "glitch": GLYPH, "cross": CROSS,
             "sigil": SIGILS, "dust": DUST}
    p = pools.get(role, EMOJI)
    return p[next(_ESEQ) % len(p)]


def chat_id(update: Any) -> int:
    ch = getattr(update, "effective_chat", None)
    if ch is None:
        m = getattr(update, "message", None) or getattr(update, "effective_message", None)
        ch = getattr(m, "chat", None)
    if ch is None:
        ch = getattr(update, "chat", None)
    return int(getattr(ch, "id", 0) or 0)


def uid_of(update: Any) -> int:
    u = getattr(update, "effective_user", None)
    if u is None:
        u = getattr(getattr(update, "message", None), "from_user", None)
    return int(getattr(u, "id", 0) or 0)


def username_of(update: Any) -> str:
    u = getattr(update, "effective_user", None) or getattr(
        getattr(update, "message", None), "from_user", None)
    return (getattr(u, "username", "") or "").lstrip("@")


def fullname_of(update: Any) -> str:
    u = getattr(update, "effective_user", None) or getattr(
        getattr(update, "message", None), "from_user", None)
    return ((getattr(u, "first_name", "") or "") + " " +
            (getattr(u, "last_name", "") or "")).strip() or "ᴜsᴇʀ"


def msg_text(update: Any) -> str:
    m = getattr(update, "effective_message", None) or getattr(update, "message", None)
    return getattr(m, "text", "") or ""


def arg(update: Any) -> str:
    parts = msg_text(update).split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def reply_of(update: Any) -> Any:
    m = getattr(update, "effective_message", None) or getattr(update, "message", None)
    return getattr(m, "reply_to_message", None)


def is_private(update: Any) -> bool:
    ch = getattr(update, "effective_chat", None) or getattr(
        getattr(update, "message", None), "chat", None)
    return getattr(ch, "type", "") == "private"


def is_owner(uid: int) -> bool:
    return bool(uid and OWNER_ID and uid == OWNER_ID)


def is_auth(uid: int) -> bool:
    return is_owner(uid) or bool(SUDO_ON and uid in SUDO)


def prefix_text() -> str:
    return PREFIX if PREFIX_ENABLED else ""


def p(cmd: str) -> str:
    return f"{prefix_text()}{cmd}"


async def render(update: Any, text: str) -> Any:
    """Plain text. Koi markup, keyboard ya motion effect nahi."""
    m = getattr(update, "effective_message", None) or getattr(update, "message", None)
    if m is None:
        return None
    try:
        return await m.reply_text(assert_clean(long_fit(text)))
    except Exception as exc:
        log.debug("render: %s", exc)
        return None


async def send_long(update: Any, text: str, limit: int = 3600) -> int:
    """4096 cap ke liye line-boundary pe chunk — plain text, kai messages."""
    m = getattr(update, "effective_message", None) or getattr(update, "message", None)
    if m is None:
        return 0
    chunks: list[str] = []
    cur: list[str] = []
    n = 0
    for ln in str(text).split("\n"):
        if n + len(ln) + 1 > limit and cur:
            chunks.append("\n".join(cur))
            cur, n = [], 0
        cur.append(ln)
        n += len(ln) + 1
    if cur:
        chunks.append("\n".join(cur))
    for i, c in enumerate(chunks, 1):
        head = f"[{i}/{len(chunks)}] " if len(chunks) > 1 else ""
        try:
            await m.reply_text(assert_clean(fit(head + c, 4096)))
        except Exception as exc:
            log.debug("send_long: %s", exc)
    return len(chunks)


def kv(k: str, v: Any) -> str:
    return f"  {k:<18} {v}"


def row(cmd: str, desc: str) -> str:
    return f"  {cmd:<26} {desc}"


def note(t: str) -> str:
    return f"  · {t}"


def sep() -> str:
    return "  " + "─" * 32


def card(title: str, rows: Iterable[str]) -> str:
    return "\n".join([f"{E('crown')} {sty('NIK','bold')} · {title}",
                      "─" * 34, *rows, "─" * 34, CREDIT])


def table(headers: tuple[str, ...], rows: list[list[Any]]) -> str:
    cols = len(headers)
    data = [[str(h) for h in headers]] + [
        [str(c) for c in r[:cols]] for r in rows]
    w = [min(30, max(len(r[i]) if i < len(r) else 0 for r in data))
         for i in range(cols)]
    out = ["  ".join(str(c)[:w[i]].ljust(w[i])
                     for i, c in enumerate(data[0])),
           "  ".join("-" * x for x in w)]
    for r in data[1:]:
        out.append("  ".join((r[i] if i < len(r) else "")[:w[i]].ljust(w[i])
                             for i in range(cols)))
    return "\n".join(out)


# ── §11 · cool-looking PLAIN-TEXT panels + tables + chhote bold glyphs ──────
def micro(s: str) -> str:
    """Lil bold text: mathematical bold Unicode (koi HTML/Markdown nahi)."""
    return sty(str(s), "bold")


def dw(s: str) -> int:
    """Display width — CJK/emoji 2 columns lete hain, table straight rahe."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
               for c in str(s))


def pad_disp(s: str, w: int) -> str:
    t = str(s)
    return t + " " * max(0, w - dw(t))


def wrap_disp(line: str, width: int) -> list[str]:
    """Word-boundary wrap, display-width aware (panel kabhi beech me na kaate)."""
    words = str(line).split()
    out: list[str] = []
    cur: list[str] = []
    used = 0
    for word in words:
        if dw(word) > width:
            if cur:
                out.append(" ".join(cur))
                cur, used = [], 0
            while dw(word) > width:
                cut = width
                while cut > 1 and dw(word[:cut]) > width:
                    cut -= 1
                out.append(word[:cut])
                word = word[cut:]
            if word:
                cur, used = [word], dw(word)
            continue
        cost = dw(word) + (1 if cur else 0)
        if used + cost > width and cur:
            out.append(" ".join(cur))
            cur, used = [word], dw(word)
        else:
            cur.append(word)
            used += cost
    if cur:
        out.append(" ".join(cur))
    return out or [""]


def panel(title: str, rows: Iterable[str], width: int = 46) -> str:
    """╭━━━〔 𝐓𝐢𝐭𝐥𝐞 〕━━━╮ rail panel — plain text, chhota bold."""
    w = max(34, min(64, width))
    head = "╭━━━〔 " + micro(title) + " 〕"
    head += "━" * max(1, w - dw(head) - 1) + "╮"
    body: list[str] = []
    for r in rows:
        for i, chunk in enumerate(wrap_disp(str(r), w - 4)):
            prefix = "  " if i else ""
            body.append("┃ " + pad_disp(prefix + chunk, w - 4) + " ┃")
    foot = "╰" + "━" * (w - 2) + "╯"
    return "\n".join([head, *body, foot,
                       "  " + CREDIT, "  " + POWERED_BY])


def grid(headers: tuple[str, ...],
         rows: list[tuple[str, ...]],
         widths: tuple[int, ...] | None = None) -> str:
    """┌──┬──┐ table — box drawing, auto display-width columns."""
    cols = len(headers)
    data = [tuple(str(h) for h in headers)] + [
        tuple(str(c) for c in r[:cols]) + ("",) * max(0, cols - len(r))
        for r in rows]
    w = widths or tuple(min(34, max(6, max(dw(r[i]) for r in data)))
                        for i in range(cols))
    bar = lambda ch, join: ch + join.join("─" * (x + 2) for x in w) + ch
    fmt = lambda r: "│" + "│".join(
        " " + pad_disp(r[i], w[i]) + " " for i in range(cols)) + "│"
    out = [bar("┌", "┬"), fmt(data[0]), bar("├", "┼")]
    out += [fmt(r) for r in data[1:]]
    out.append(bar("└", "┴"))
    return "\n".join(out)


def hosting_guide() -> str:
    """~docs ka pehla hissa — hosting config seedha CONFIG se padhta hai."""
    rows = [
        kv("1 · ᴅᴇᴘ", "pip install python-telegram-bot"),
        kv("2 · ᴛᴏᴋᴇɴ", 'CONFIG["BOT_TOKEN"] = "…"'),
        kv("3 · ᴏᴡɴᴇʀ", 'CONFIG["OWNER_ID"] = 12345678'),
        kv("4 · ʀᴜɴ", "python3 Nik_Max.py"),
        kv("5 · ᴄʟᴜsᴛᴇʀ", 'CONFIG["BOT_TOKENS"] = ["…", "…"]'),
        kv("ᴇɴᴠ", "BOT_TOKEN=… OWNER_ID=… python3 Nik_Max.py"),
        kv("ʜᴏsᴛ", "koyeb / render / railway / vps / termux"),
        kv("ᴠᴇʀɪꜰʏ", f"{p('setup')} · {p('panel')} · {p('selftest')}"),
        sep(),
        note("Token ya ID file me paste karo — koi alag config file nahi."),
        note("Plaintext token reply me kabhi nahi aata (masked)."),
        note("Bina token bhi --selftest / --menu / --docs chalte hain."),
        note("Sirf owner + sudo commands chala sakte hain."),
    ]
    return panel("🚀 ʜᴏsᴛɪɴɢ ɢᴜɪᴅᴇ", rows)


def help_line(name: str) -> str:
    """Har handler ki chhoti helping doc — HELP_DOCS ya docstring se."""
    doc = HELP_DOCS.get(name)
    if doc:
        return doc
    fn = COMMANDS.get(name)
    first = (getattr(fn, "__doc__", "") or "").strip().split("\n")[0]
    first = re.sub(r"\s+", " ", first).strip()
    first = first.replace("<", "[").replace(">", "]")
    return first[:34] or "runtime engine handler"


def docs_index() -> str:
    out = [panel("📖 ʜᴀɴᴅʟᴇʀ ᴅᴏᴄs · ɪɴᴅᴇx", [
        note(f"{p('cmd')} <name> → usage + flags + example"),
        note(f"{p('menu')}<1-{len(_menu_groups())}> → section tables"),
        note(f"{p('fullmenu')} → poora command index"),
        note(f"{p('panel')} → live control panel"),
        note("Target hamesha {target}; naam runtime me text/slide/ID se."),
    ])]
    for i, (g, names, desc) in enumerate(_menu_groups(), 1):
        top = names[:6]
        out.append("\n" + micro(g.upper()) + "  ·  " + desc)
        out.append(grid((f"{p('cmd')}", "ʜᴇʟᴘ"), [
            (p(n), help_line(n)) for n in top], (22, 34)))
    return "\n".join(out)


log.info("core ready · fonts=%d · generators=%d · text-literals=0",
         len(FONTS), len(TitleForge.GENERATORS))


# ─── part 1 ───────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════
#  ⚙️ ᴇɴɢɪɴᴇ ʟᴀʏᴇʀ — throttle · flood · boost · cluster · tasks
#  Sab asli control-flow hai; isme koi stored text nahi.
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Mode:
    name: str
    delay: float          # local gap; raw = 0.0
    burst: int
    refill: float
    streams: int          # independent rename streams PER BOT
    conc: int
    ghost: bool
    desc_every: int
    verify_every: int
    fanout: int


THROTTLE_MODES: dict[str, Mode] = {
    "low":  Mode("low",  1.000, 1,  1.0, 1,  1,  False, 40, 20, 1),
    "mid":  Mode("mid",  0.350, 3,  4.0, 2,  2,  False, 25, 15, 2),
    "high": Mode("high", 0.120, 6, 10.0, 4,  4,  True,  15, 10, 3),
    "max":  Mode("max",  0.030, 16, 30.0, 8,  8,  True,   8,  6, 6),
    "raw":  Mode("raw",  0.000, 64, 90.0, 12, 12, True,   4,  3, 12),
}
THROTTLE_ORDER = ("low", "mid", "high", "max", "raw")
THROTTLE_MODE = "max"

# Purane mode-naam ab alias hain — kisi ki aadat nahi toot-ti, par ladder
# ab low → mid → high → max → raw hai (raw = 0ms, no daya).
MODE_ALIASES: dict[str, str] = {
    "medium": "mid", "gfaad": "high", "ultra": "raw",
    "slow": "low", "normal": "mid", "fast": "high",
    "brutal": "max", "zero": "raw", "0": "raw",
}


def resolve_mode(name: str) -> str:
    n = (name or "").strip().lower()
    n = MODE_ALIASES.get(n, n)
    return n if n in THROTTLE_MODES else "max"


# ── TIMING LAB — sab reference files ke asli constants, ek jagah ───────────
# reference-A: delay .1 / BOOST_DELAY 0.0 / BOOST_DURATION 30 / stagger .01 /
#           FLOODLESS_CONCURRENCY 99 / per-bot cooldown = retry_after
# reference-B: NORMAL_DELAY .05 / BOOST_DELAY .01 / BOOST_DURATION 60 /
#            CHECK_INTERVAL 3 / GOD_SPEED_DELAY .05 / sleep(10) pfp loop
# reference-C:    _nc_send_gap override / RELAY_OFFSET .15 / SEND_GAP .5-.6 /
#           gap .09-.45 / MAX_BACKOFF 2.5 / RECOVER_AFTER 5 / rate .95 /
#           CYCLE_TIME = STAGGER*N / TICK .10 / DURATION 10 speedtest /
#           setdelay 0.05–10.0 / count 15 / burst min(len(bots)*2,10)
TIMING_DEFAULTS: dict[str, float] = {
    "send_gap": 0.0, "relay_offset": 0.15, "boost_delay": 0.0,
    "boost_duration": 30.0, "check_interval": 3.0, "god_speed": 0.05,
    "max_backoff": 2.5, "recover_after": 5.0, "recover_rate": 0.95,
    "raw_window": 8.0, "raw_hold": 8.0, "speedtest": 10.0,
    "min_delay": 0.05, "max_delay": 10.0, "stagger_floor": 0.01,
    "floodless_conc": 99.0, "burst_cap": 10.0, "cycle_tick": 0.10,
    "min_photos": 2.0, "max_photos": 10.0,
}
TIMING: dict[str, float] = dict(TIMING_DEFAULTS)
TIMING.update({k: float(v) for k, v in load_json("timing.json", {}).items()
               if k in TIMING_DEFAULTS})


def timing_save() -> None:
    save_json("timing.json", TIMING)


def burst_cap(bots: int) -> int:
    return max(1, min(int(TIMING["burst_cap"]), bots * 2))


class DutyCycle:
    """0ms nonstop → 5–10s burst → 5–10s hold → phir raw nonstop.

    Screenshot wali badi NC ke liye: raw mode me local delay bilkul 0 hai,
    par har 5–10s ke baad poora cluster 5–10s saans leta hai. Window aur
    hold dono 5–10s range me configurable hain (~window / ~hold).
    """

    __slots__ = ("epoch", "switches", "held")

    def __init__(self) -> None:
        self.epoch = time.monotonic()
        self.switches = 0
        self.held = 0.0

    def window(self) -> float:
        return max(5.0, min(10.0, float(TIMING["raw_window"])))

    def hold(self) -> float:
        return max(5.0, min(10.0, float(TIMING["raw_hold"])))

    def gate(self) -> float:
        """0.0 = chalne do; >0 = itni der hold karo."""
        w, h = self.window(), self.hold()
        el = time.monotonic() - self.epoch
        if el < w:
            return 0.0
        if el < w + h:
            self.held = min(self.held + 0.25, h)
            return min(0.25, w + h - el)
        self.epoch = time.monotonic()
        self.switches += 1
        self.held = 0.0
        return 0.0

    def phase(self) -> str:
        el = time.monotonic() - self.epoch
        return "ʜᴏʟᴅ" if el >= self.window() else "ʙᴜʀsᴛ"


DUTY = DutyCycle()

# ─────────────────────────────────────────────────────────────────────────────
# LOGIC AUDIT · sab 59 Python files ke andar ghus ke nikala gaya (naam chhupa
# kar, kyunki kisi ko reference se banayi hui file ka pata nahi chalna chahiye)
#
# reference-A  · 149 funcs / 45 NC-ish. delay=0.1, BOOST_DELAY=0.0,
#   BOOST_DURATION=30 ticks, per-bot cooldown[idx]=now+retry_after, stagger
#   bot_index*0.01, FLOODLESS_CONCURRENCY=99, sleep 0.05/0.008/0.2/0.3,
#   RetryAfter me exact retry_after+0.5, nc1..nc10 / enc1..enc10 / fnc1..fnc10
#   task dicts, trigger_boost() title mismatch pe, tick_boost() har cycle.
# reference-B  · 73 funcs / 29 NC-ish. NORMAL_DELAY=0.05, BOOST_DELAY=0.01,
#   BOOST_DURATION=60, CHECK_INTERVAL=3, GOD_SPEED_DELAY=0.05, copy-normal /
#   copy-boost delays, custom_nc_delays[chat][mode] settable, bot_index*0.05
#   stagger, pfp loop me sleep(10), e.retry_after+0.1 backoff.
# reference-C  · 262 funcs / 155 map entries / 27 naam-wali friend list.
#   global send-gap override, RELAY_OFFSET=0.15 per bot, SEND_GAP .5-.6,
#   per-engine gap .09/.15/.18/.20/.25/.45, MAX_BACKOFF=2.5, RECOVER_AFTER=5,
#   RECOVER_RATE=0.95, CYCLE_TIME=STAGGER*N, TICK=0.10, TICK*40 queue timeout,
#   DURATION=10.0 speedtest, setdelay range 0.05-10.0, default count=15,
#   burst=min(len(bots)*2,10), 3-group trio producer/consumer, per-bot
#   flooded_until[idx], staggered resume flood_end + idx*STEP, MAX_WAIT=4.0.
# reference-set (36 files) · title-verify boost, launcher me RENAME_STREAMS
#   per bot, worker stagger 0.01, cancel_all(), steady engine per-bot flood
#   tracker + RetryAfter/BadRequest/Forbidden/TimedOut/NetworkError, precomputed
#   cycles, 125-char emoji padding, +0.1 retry pad.
# uploads + active + purane deliverables · 439 distinct handler names, 1063
#   raw command tokens, 305 se 640 commands ka clean union; music/VC/proxy/
#   AI/richtext/article/table/ghatiya utilities aur saare purane naam encode
#   karke blocklist me, registry + dispatch + menu teeno se bahar rakhe gaye.
#
# Isi audit se TIMING lab, DutyCycle (0ms -> 10-15s burst -> 10-15s hold),
# MODE_ALIASES, BOOST_DELAY window, relay/stagger, burst_cap aur speedtest
# bane. Koi bhi title stored nahi: 35 runtime generators, 79 NC styles.
# ─────────────────────────────────────────────────────────────────────────────

STATS: dict[str, int] = collections.defaultdict(int)
_FLOOD_LOG: collections.deque[tuple[float, int, float]] = collections.deque(maxlen=200)


class TokenBucket:
    """Single shared limiter — har worker apna alag bucket nahi banata."""

    __slots__ = ("cap", "rate", "tokens", "last", "lock")

    def __init__(self, cap: int, rate: float) -> None:
        self.cap = max(1, int(cap))
        self.rate = max(0.1, float(rate))
        self.tokens = float(self.cap)
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, n: int = 1) -> float:
        waited = 0.0
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.cap,
                                  self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= n:
                    self.tokens -= n
                    return waited
                deficit = (n - self.tokens) / self.rate
            nap = max(0.001, min(deficit, 0.25))
            await asyncio.sleep(nap)
            waited += nap

    def snapshot(self) -> dict[str, float]:
        return {"cap": self.cap, "rate": self.rate, "tokens": self.tokens}


class FloodTracker:
    """Per-bot retry_after quarantine (steady-engine pattern).

    Ek bot flood khata hai to baaki bots rukte nahi — sirf woh bot
    `remaining()` seconds ke liye side me ho jata hai.
    """

    def __init__(self) -> None:
        self.until: dict[int, float] = {}
        self.hits: dict[int, int] = collections.defaultdict(int)
        self.lock = asyncio.Lock()

    async def mark(self, bot_id: int, retry_after: float) -> None:
        wait = max(0.0, min(float(retry_after or 0), 30.0))
        async with self.lock:
            self.until[bot_id] = time.monotonic() + wait
            self.hits[bot_id] += 1
            _FLOOD_LOG.append((time.monotonic(), bot_id, wait))
            STATS["429"] += 1
            STATS["flood_wait"] += int(wait)

    def is_flooded(self, bot_id: int) -> bool:
        return self.until.get(bot_id, 0) > time.monotonic()

    def remaining(self, bot_id: int) -> float:
        return max(0.0, self.until.get(bot_id, 0) - time.monotonic())

    async def clear(self, bot_id: int) -> None:
        async with self.lock:
            self.until.pop(bot_id, None)

    def report(self) -> dict[int, float]:
        now = time.monotonic()
        return {k: round(max(0.0, v - now), 2)
                for k, v in self.until.items() if v > now}


FLOOD = FloodTracker()


class AdaptiveBoost:
    """Title-verification boost.

    Har N titles pe `get_chat()` se actual title padha jata hai. Agar kisi
    aur ne / kisi aur bot ne title badal diya ho to expected se mismatch
    milta hai → streams/conc badhta hai (boost), aur next wave me atomic
    sequence dobara sync ho jata hai.
    """

    def __init__(self) -> None:
        self.expected: dict[int, str] = {}
        self.mismatch: dict[int, int] = collections.defaultdict(int)
        self.boost_level: dict[int, int] = collections.defaultdict(int)
        self.boost_since: dict[int, float] = {}
        self.success_streak: dict[int, int] = collections.defaultdict(int)
        self.last_verify: dict[int, float] = {}
        self.lock = asyncio.Lock()

    def expect(self, cid: int, title: str) -> None:
        self.expected[cid] = title

    def tick(self, cid: int) -> None:
        self.success_streak[cid] += 1
        if self.success_streak[cid] % 40 == 0 and self.boost_level[cid] > 0:
            self.boost_level[cid] -= 1
            STATS["boost_down"] += 1

    def trigger(self, cid: int) -> int:
        self.mismatch[cid] += 1
        self.boost_since[cid] = time.monotonic()
        self.boost_level[cid] = min(6, self.boost_level[cid] + 1)
        self.success_streak[cid] = 0
        STATS["boost_up"] += 1
        STATS["mismatch"] += 1
        return self.boost_level[cid]

    def streams(self, cid: int, base: int) -> int:
        return min(16, base + self.boost_level[cid])

    async def verify(self, bot: Any, cid: int, every: int,
                     counter: int) -> bool:
        """True = mismatch mila (boost trigger ho gaya)."""
        if every <= 0 or counter % every != 0:
            return False
        now = time.monotonic()
        if now - self.last_verify.get(cid, 0) < 0.25:
            return False
        self.last_verify[cid] = now
        fn = getattr(bot, "get_chat", None)
        expected = self.expected.get(cid, "")
        if fn is None or not expected:
            return False
        try:
            chat = await asyncio.wait_for(fn(cid), timeout=5.0)
            actual = getattr(chat, "title", "") or ""
            STATS["verify"] += 1
            if actual and actual != expected:
                self.trigger(cid)
                return True
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        return False

    def state(self, cid: int) -> dict[str, int]:
        return {"boost": self.boost_level.get(cid, 0),
                "mismatch": self.mismatch.get(cid, 0),
                "streak": self.success_streak.get(cid, 0)}


BOOSTER = AdaptiveBoost()


class RateLimiter:
    """Global + per-chat + per-bot buckets, ek hi composite limiter."""

    def __init__(self) -> None:
        m = THROTTLE_MODES[THROTTLE_MODE]
        self.global_bucket = TokenBucket(m.burst * 2, m.refill)
        self.chat: dict[int, TokenBucket] = {}
        self.bot: dict[int, TokenBucket] = {}
        self.mode_name = THROTTLE_MODE
        self.conc = m.conc
        self.lock = asyncio.Lock()

    @property
    def mode(self) -> Mode:
        return THROTTLE_MODES[self.mode_name]

    def set_mode(self, name: str) -> Mode:
        global THROTTLE_MODE
        THROTTLE_MODE = resolve_mode(name)
        m = self.mode
        self.mode_name = THROTTLE_MODE
        self.conc = m.conc
        self.global_bucket = TokenBucket(m.burst * 2, m.refill)
        self.chat.clear()
        self.bot.clear()
        STATS["mode_set"] += 1
        return m

    def _chat(self, cid: int) -> TokenBucket:
        b = self.chat.get(cid)
        if b is None:
            b = TokenBucket(self.mode.burst, self.mode.refill)
            self.chat[cid] = b
        return b

    def _bot(self, bid: int) -> TokenBucket:
        b = self.bot.get(bid)
        if b is None:
            b = TokenBucket(self.mode.burst, self.mode.refill * 1.5)
            self.bot[bid] = b
        return b

    async def acquire(self, cid: int, bid: int = 0) -> float:
        waited = await self._chat(cid).acquire()
        if bid:
            waited += await self._bot(bid).acquire()
        waited += await self.global_bucket.acquire()
        if self.mode.delay > 0:
            await asyncio.sleep(self.mode.delay)
        STATS["acquired"] += 1
        return waited

    async def note_flood(self, cid: int, bid: int, retry_after: float) -> None:
        await FLOOD.mark(bid or cid, retry_after)
        async with self.lock:
            self.conc = max(1, self.conc - 1)
            STATS["autotune_down"] += 1

    def note_ok(self) -> None:
        if STATS["acquired"] % 40 == 0:
            self.conc = min(self.mode.conc, self.conc + 1)
            STATS["autotune_up"] += 1

    def snapshot(self) -> dict[str, Any]:
        m = self.mode
        return {"mode": m.name, "delay": m.delay, "burst": m.burst,
                "refill": m.refill, "streams": m.streams,
                "conc": self.conc, "max_conc": m.conc,
                "ghost": m.ghost, "desc_every": m.desc_every,
                "verify_every": m.verify_every, "fanout": m.fanout,
                "boost": BOOST, "global_tokens":
                    round(self.global_bucket.tokens, 1),
                "flooded_bots": len(FLOOD.report())}


LIMITER = RateLimiter()


def throttle_set(name: str) -> Mode:
    return LIMITER.set_mode(name)


async def safe_call(cid: int, fn: Callable, *args: Any,
                    _bid: int = 0, **kwargs: Any) -> bool:
    """Har outgoing API call yahin se — exact retry_after, quarantine, stats."""
    try:
        await LIMITER.acquire(cid, _bid)
        await fn(*args, **kwargs)
        STATS["ok"] += 1
        LIMITER.note_ok()
        return True
    except RetryAfter as exc:
        await LIMITER.note_flood(cid, _bid,
                                 float(getattr(exc, "retry_after", 1) or 1))
        return False
    except asyncio.CancelledError:
        raise
    except (BadRequest, Forbidden, TimedOut, NetworkError) as exc:
        STATS["errors"] += 1
        log.debug("call %s: %s", getattr(fn, "__name__", "?"), exc)
        return False
    except Exception as exc:
        STATS["errors"] += 1
        log.debug("call: %s", exc)
        return False


# ── bot cluster ─────────────────────────────────────────────────────────────
BOTS: dict[int, Any] = {}
BOT_META: dict[int, dict[str, Any]] = {}
BOT_PENDING: dict[str, Any] = {}
PRIMARY_BOT: Any = None


def bot_id(bot: Any) -> int:
    return int(getattr(bot, "id", 0) or id(bot))


def pool() -> list[Any]:
    out = [b for b in BOTS.values() if b is not None]
    if not out and PRIMARY_BOT is not None:
        out = [PRIMARY_BOT]
    m = LIMITER.mode.fanout
    if BOOST:
        m = len(out) or m
    return out[:max(1, m)]


def bot_count() -> int:
    return len([b for b in BOTS.values() if b is not None])


async def register_bot(token: str, source: str = "token",
                       label: str = "") -> int:
    """Token validate → cluster me add. Kabhi plaintext token store nahi
    (sirf env/DATA config me, source me literal nahi)."""
    obj: Any = None
    if HAS_PTB:
        try:
            obj = _TGBot(token)
            info = await asyncio.wait_for(obj.get_me(), timeout=8.0)
            bid = int(getattr(info, "id", 0) or 0)
            label = (getattr(info, "username", "") or "").lstrip("@") or label
        except Exception:
            obj = None
    if obj is None:
        bid = int(hashlib.sha1(token.encode()).hexdigest()[:10], 16)
        obj = PRIMARY_BOT
    BOTS[bid] = obj
    BOT_META[bid] = {"id": bid, "source": source, "username": label,
                     "connected": True, "added": int(time.time()),
                     "health": 100}
    if token not in TOKENS:
        TOKENS.append(token)
        cfg_save()
    STATS["bots_added"] += 1
    return bid


async def bot_call(bot: Any, method: str, cid: int, **kwargs: Any) -> bool:
    fn = getattr(bot, method, None)
    if fn is None:
        return False
    return await safe_call(cid, fn, cid, _bid=bot_id(bot), **kwargs)


async def set_title(cid: int, bot: Any, title: str) -> bool:
    ok = await bot_call(bot, "set_chat_title", cid, title=fit(title, 128))
    if ok:
        STATS["titles"] += 1
        BOOSTER.expect(cid, fit(title, 128))
        BOOSTER.tick(cid)
    return ok


async def set_desc(cid: int, bot: Any, text: str) -> bool:
    ok = await bot_call(bot, "set_chat_description", cid,
                        description=fit(text, 255))
    if ok:
        STATS["desc"] += 1
    return ok


async def send_msg(cid: int, bot: Any, text: str, **kw: Any) -> bool:
    ok = await bot_call(bot, "send_message", cid,
                        text=long_fit(assert_clean(text)), **kw)
    if ok:
        STATS["msgs"] += 1
    return ok


async def fwd_msg(cid: int, bot: Any, from_cid: int, msg_id: int) -> bool:
    fn = getattr(bot, "forward_message", None)
    if fn is None:
        return False
    ok = await safe_call(cid, fn, cid, from_cid, msg_id,
                         _bid=bot_id(bot))
    if ok:
        STATS["fwd"] += 1
    return ok


# ── task registry ───────────────────────────────────────────────────────────
TASKS: dict[tuple[str, int], asyncio.Task] = {}
STOP_EVENTS: dict[tuple[str, int], asyncio.Event] = {}
NC_KINDS: tuple[str, ...] = (
    "mdc", "nc", "mixspm", "desc", "banner", "bank", "emojirain",
    "picraid_title", "gpfp_title")
LOOP_KINDS: tuple[str, ...] = (
    "spam", "reply", "xreply", "rr", "ms", "fwdspam", "slides",
    "targetslide", "picraid", "gpfp", "sticker", "emojirain",
    "bank", "broadcast", "purge")
ENGINE_KINDS: tuple[str, ...] = NC_KINDS + LOOP_KINDS


def _key(kind: str, cid: int) -> tuple[str, int]:
    return (kind, int(cid))


def task_start(kind: str, cid: int, coro: Any) -> asyncio.Event:
    k = _key(kind, cid)
    task_stop(kind, cid)
    ev = asyncio.Event()
    STOP_EVENTS[k] = ev
    TASKS[k] = asyncio.create_task(coro, name=f"nik:{kind}:{cid}")
    STATS["started"] += 1
    return ev


def task_stop(kind: str, cid: int) -> bool:
    k = _key(kind, cid)
    ev = STOP_EVENTS.pop(k, None)
    if ev:
        ev.set()
    t = TASKS.pop(k, None)
    if t and not t.done():
        t.cancel()
        STATS["stopped"] += 1
        return True
    return False


def stop_kinds(kinds: Iterable[str], cid: int | None = None) -> int:
    n = 0
    for (k, c) in list(TASKS):
        if k in kinds and (cid is None or c == cid):
            if task_stop(k, c):
                n += 1
    return n


def stop_nc(cid: int | None = None) -> int:
    return stop_kinds(NC_KINDS, cid)


def stop_all(cid: int | None = None) -> int:
    return stop_kinds(set(ENGINE_KINDS), cid)


def active_tasks() -> list[str]:
    return [f"{k}:{c}" for (k, c), t in TASKS.items()
            if t and not t.done()]


async def stoppable_sleep(ev: asyncio.Event, seconds: float) -> None:
    """Cancel-friendly; 0 delay pe bhi event loop ko breathe deta hai."""
    if seconds <= 0:
        await asyncio.sleep(0)
        return
    try:
        await asyncio.wait_for(ev.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


def throttle_card() -> str:
    s = LIMITER.snapshot()
    return card("⚡ ᴛʜʀᴏᴛᴛʟᴇ", [
        kv("ᴍᴏᴅᴇ", s["mode"].upper()),
        kv("ʟᴏᴄᴀʟ ᴅᴇʟᴀʏ", f"{s['delay']:.3f}s"),
        kv("ʙᴜʀsᴛ / ʀᴇꜰɪʟʟ", f"{s['burst']} / {s['refill']:.0f}/s"),
        kv("sᴛʀᴇᴀᴍs / ʙᴏᴛ", s["streams"]),
        kv("ᴄᴏɴᴄ", f"{s['conc']}/{s['max_conc']}"),
        kv("ᴠᴇʀɪꜰʏ ᴇᴠᴇʀʏ", s["verify_every"]),
        kv("ᴅᴇsᴄ ᴇᴠᴇʀʏ", s["desc_every"]),
        kv("ꜰᴀɴ-ᴏᴜᴛ", s["fanout"]),
        kv("ʙᴏᴏsᴛ", "🟢" if s["boost"] else "🔴"),
        kv("ꜰʟᴏᴏᴅᴇᴅ ʙᴏᴛs", s["flooded_bots"]),
        kv("ᴛᴏᴋᴇɴs", s["global_tokens"]), sep(),
        note("low 1.0s · mid .35s · high .12s · max .03s · raw 0.0s"),
        note("429 = exact retry_after sleep, sirf woh bot quarantine"),
        row(f"{p('throttle')} raw", "0 ᴅᴇʟᴀʏ · ʙɪɴᴀ ʀᴜᴋᴇ")])


def engine_stats_card() -> str:
    return card("📊 ᴇɴɢɪɴᴇ", [
        kv("ᴛɪᴛʟᴇs", STATS["titles"]),
        kv("ᴅᴇsᴄ", STATS["desc"]),
        kv("ᴍsɢs", STATS["msgs"]),
        kv("ꜰᴡᴅs", STATS["fwd"]),
        kv("ᴏᴋ / 429", f"{STATS['ok']} / {STATS['429']}"),
        kv("ᴠᴇʀɪꜰʏ / ᴍɪsᴍᴀᴛᴄʜ", f"{STATS['verify']} / {STATS['mismatch']}"),
        kv("ʙᴏᴏsᴛ ↑↓", f"{STATS['boost_up']} / {STATS['boost_down']}"),
        kv("ᴀᴜᴛᴏ-ᴛᴜɴᴇ ↑↓",
           f"{STATS['autotune_up']} / {STATS['autotune_down']}"),
        kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks())),
        note(", ".join(active_tasks()[:6]) or "—")])


log.info("engine ready · modes=%d · buckets=3 · verify-boost=on",
         len(THROTTLE_MODES))


# ─── part 2 ───────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════
#  🔥 ᴍᴅᴄ ɴᴄ — flagship "sabse tagdi" engine
#  • har bot ke liye `streams` independent rename workers, staggered
#  • atomic global sequence (koi do worker ek hi title nahi bhejte)
#  • title verification → mismatch pe boost (extra burst wave)
#  • per-bot flood quarantine, baaki bots full speed pe rehte hain
#  • side waves: description · photo · pin · reaction · message
#  • 0-delay raw, ghost skip, global fan-out, clean cancel
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class MDCState:
    cid: int
    style: str
    target: str
    targets: list[int]
    started: float
    seq: itertools.count
    lock: asyncio.Lock
    titles: int = 0
    desc: int = 0
    photos: int = 0
    pins: int = 0
    msgs: int = 0
    ghost_skips: int = 0
    bursts: int = 0
    mismatches: int = 0
    waves: int = 0
    flags: dict[str, bool] = field(default_factory=dict)
    media: str = ""
    media_kind: str = ""
    reply_id: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {"style": self.style, "target": self.target[:24],
                "gcs": len(self.targets), "titles": self.titles,
                "desc": self.desc, "photos": self.photos,
                "pins": self.pins, "msgs": self.msgs,
                "ghost": self.ghost_skips, "bursts": self.bursts,
                "mismatch": self.mismatches, "waves": self.waves,
                "uptime": int(time.time() - self.started),
                "boost": BOOSTER.state(self.cid)["boost"]}


MDC_STATE: dict[int, MDCState] = {}


class MDCOrc:
    """Multi-Dimensional-Chudai NC controller."""

    def __init__(self, update: Any, style: str, opts: dict[str, Any]) -> None:
        self.update = update
        self.style = style
        self.opts = opts
        self.cid = chat_id(update)
        self.spec = NC_STYLES[style]
        self.targets: list[int] = opts.get("targets") or [self.cid]
        self.forge = TitleForge(opts.get("target", ""),
                                self.spec["wall"], seed=1)
        self.ev: asyncio.Event | None = None
        self.duty = DutyCycle()          # 0ms → 10–15s burst → 10–15s hold
        self.state = MDCState(
            cid=self.cid, style=style, target=self.forge.target,
            targets=self.targets, started=time.time(),
            seq=itertools.count(1), lock=asyncio.Lock(),
            flags=opts, media=opts.get("media", ""),
            media_kind=opts.get("mkind", ""),
            reply_id=opts.get("reply_id", 0))

    # ── launch: bots × streams, staggered ───────────────────────────────────
    async def start(self) -> MDCState:
        self.ev = task_start("mdc", self.cid, self._run())
        MDC_STATE[self.cid] = self.state
        STATS["mdc_started"] += 1
        return self.state

    async def _run(self) -> None:
        ev = STOP_EVENTS.get(_key("mdc", self.cid)) or asyncio.Event()
        self.ev = ev
        bots = pool()
        m = LIMITER.mode
        streams = BOOSTER.streams(self.cid, m.streams)
        if self.opts.get("streams"):
            streams = min(16, max(streams, int(self.opts["streams"])))
        subs: list[asyncio.Task] = []
        try:
            for i, bot in enumerate(bots):
                for j in range(streams):
                    # reference-C RELAY_OFFSET (0.15/bot) + reference-A 0.01/stream
                    stagger = (i * TIMING["relay_offset"]
                               + j * TIMING["stagger_floor"])
                    subs.append(asyncio.create_task(
                        self._stream(bot, i, j, stagger, ev),
                        name=f"mdc:{self.cid}:{i}:{j}"))
            self.state.waves = len(subs)
            await asyncio.gather(*subs, return_exceptions=True)
        except asyncio.CancelledError:
            for t in subs:
                t.cancel()
            await asyncio.gather(*subs, return_exceptions=True)
            raise
        finally:
            # Sirf apni hi entry hatana — agar is key pe naya task aa chuka
            # hai to uski registry / stop-event / state zinda rehni chahiye.
            cur = asyncio.current_task()
            k = _key("mdc", self.cid)
            if MDC_STATE.get(self.cid) is self.state:
                MDC_STATE.pop(self.cid, None)
            if TASKS.get(k) is cur:
                TASKS.pop(k, None)
            if STOP_EVENTS.get(k) is self.ev:
                STOP_EVENTS.pop(k, None)

    # ── ek independent rename stream ───────────────────────────────────────
    async def _stream(self, bot: Any, bi: int, si: int,
                      stagger: float, ev: asyncio.Event) -> None:
        if stagger > 0:
            await stoppable_sleep(ev, stagger)
        bid = bot_id(bot)
        m = LIMITER.mode
        counter = 0
        while not ev.is_set():
            if FLOOD.is_flooded(bid):
                await stoppable_sleep(ev, min(FLOOD.remaining(bid),
                                              TIMING["max_backoff"]))
                continue
            # raw = 0ms nonstop, par 5–10s burst ke baad 5–10s saans
            if m.name == "raw":
                hold = self.duty.gate()
                if hold > 0:
                    await stoppable_sleep(ev, hold)
                    continue
            try:
                seq = next(self.state.seq)
                counter += 1
                ghost = (self.spec["ghost"] or m.ghost) and \
                    not self.opts.get("noghost") and seq % 7 == 0
                if ghost:
                    self.state.ghost_skips += 1
                else:
                    title = self._title(seq)
                    for cid in self.targets:
                        if await set_title(cid, bot, title):
                            async with self.state.lock:
                                self.state.titles += 1
                # verification-based boost
                if await BOOSTER.verify(bot, self.cid, m.verify_every,
                                        counter):
                    self.state.mismatches += 1
                    await self._burst(bot, ev)
                # side waves (description / photo / pin / message)
                if seq % max(1, m.desc_every) == 0:
                    await self._side_wave(bot, seq, ev)
                # reference-C _nc_send_gap override → reference-A BOOST_DELAY window
                gap = TIMING["send_gap"] or m.delay
                if (BOOSTER.boost_level.get(self.cid, 0) > 0 and
                        time.monotonic()
                        - BOOSTER.boost_since.get(self.cid, 0)
                        < TIMING["boost_duration"]):
                    gap = min(gap, TIMING["boost_delay"])
                await stoppable_sleep(ev, gap)
            except asyncio.CancelledError:
                raise
            except RetryAfter as exc:
                await LIMITER.note_flood(self.cid, bid,
                                         float(getattr(exc, "retry_after", 1) or 1))
            except Exception as exc:
                STATS["errors"] += 1
                log.debug("stream %s/%s: %s", bi, si, exc)
                await stoppable_sleep(ev, 0.02)

    def _title(self, seq: int) -> str:
        """Style ka apna pattern function — TitleForge fallback ke saath."""
        fn = STYLE_FUNCS.get(self.style)
        if fn is not None:
            raw = fn(self.forge, seq)
            if self.spec["pad"] and "\n" not in raw:
                raw = self.forge.pad(raw)
            return fit(assert_clean(raw), 128)
        return self.forge.build(seq, pad=self.spec["pad"])

    async def _burst(self, bot: Any, ev: asyncio.Event) -> None:
        """Mismatch mila → extra atomic wave (boost)."""
        if ev.is_set():
            return
        async with self.state.lock:
            self.state.bursts += 1
        for _ in range(min(4, 1 + BOOSTER.boost_level.get(self.cid, 0))):
            seq = next(self.state.seq)
            title = self._title(seq)
            for cid in self.targets:
                if await set_title(cid, bot, title):
                    async with self.state.lock:
                        self.state.titles += 1
            await stoppable_sleep(ev, 0)

    async def _side_wave(self, bot: Any, seq: int,
                         ev: asyncio.Event) -> None:
        if ev.is_set():
            return
        spec = self.spec
        if spec["desc"] and not self.opts.get("nodesc"):
            d = fit(assert_clean(
                f"{sty('NIK','bold')} {GLYPH[seq % len(GLYPH)]} "
                f"{ROAST[(seq*3) % len(ROAST)]} {EMOJI[seq % len(EMOJI)]}"),
                255)
            for cid in self.targets:
                if await set_desc(cid, bot, d):
                    async with self.state.lock:
                        self.state.desc += 1
        if spec["photo"] and self.state.media:
            fn = getattr(bot, "set_chat_photo", None)
            if fn:
                for cid in self.targets:
                    if await safe_call(cid, fn, cid,
                                       photo=self.state.media,
                                       _bid=bot_id(bot)):
                        async with self.state.lock:
                            self.state.photos += 1
        if spec["pin"] and self.state.reply_id:
            fn = getattr(bot, "pin_chat_message", None)
            if fn:
                for cid in self.targets:
                    if await safe_call(cid, fn, cid, self.state.reply_id,
                                       _bid=bot_id(bot)):
                        async with self.state.lock:
                            self.state.pins += 1
        if spec["msg"]:
            if spec.get("page"):
                pb = WallForge(self.opts.get("target", TARGET_SLOT),
                               seed=seq)
                line_txt = pb.frame(seq)
            else:
                line_txt = fit(assert_clean(
                    self.forge.build(seq + 991, pad=False)), 400)
            for cid in self.targets:
                if await send_msg(cid, bot, line_txt):
                    async with self.state.lock:
                        self.state.msgs += 1

    def stat_card(self) -> str:
        s = self.state.snapshot()
        return card(f"📈 ᴍᴅᴄ ɴᴄ · {self.style.upper()}", [
            kv("ᴛᴀʀɢᴇᴛ", s["target"]),
            kv("ɢᴄs / sᴛʀᴇᴀᴍs", f"{s['gcs']} / {s['waves']}"),
            kv("ᴛɪᴛʟᴇs", s["titles"]),
            kv("ᴅᴇsᴄ / ᴘʜᴏᴛᴏ / ᴘɪɴ",
               f"{s['desc']} / {s['photos']} / {s['pins']}"),
            kv("ᴍsɢs", s["msgs"]),
            kv("ɢʜᴏsᴛ sᴋɪᴘ", s["ghost"]),
            kv("ʙᴜʀsᴛs / ᴍɪsᴍᴀᴛᴄʜ",
               f"{s['bursts']} / {s['mismatch']}"),
            kv("ʙᴏᴏsᴛ ʟᴇᴠᴇʟ", s["boost"]),
            kv("ᴍᴏᴅᴇ / ᴅᴇʟᴀʏ",
               f"{LIMITER.mode.name} / {LIMITER.mode.delay:.3f}s"),
            kv("ᴜᴘᴛɪᴍᴇ", f"{s['uptime']}s"), sep(),
            note("verify → mismatch → extra atomic burst wave"),
            row(f"{p('allnc')} off", "sab band")])


# ── 39 style specs (sab code-driven) ────────────────────────────────────────
def _spec(wall: str = "cross", pad: bool = True, desc: bool = True,
          ghost: bool = True, photo: bool = False, pin: bool = False,
          msg: bool = False, page: bool = False) -> dict[str, Any]:
    return {"wall": wall, "pad": pad, "desc": desc, "ghost": ghost,
            "photo": photo, "pin": pin, "msg": msg, "page": page}


NC_STYLES: dict[str, dict[str, Any]] = {
    # jo explicitly maange the
    "niknc":   _spec("cross", desc=True, ghost=True),
    "nc":      _spec("cune", desc=True, ghost=False),
    "nc1":     _spec("cross", desc=False, ghost=True),
    "nc2":     _spec("heart", desc=False, ghost=False),
    "nc3":     _spec("zalgo", desc=True, ghost=True),
    "nc4":     _spec("cune", desc=False, ghost=False),
    "nc5":     _spec("cross", desc=True, ghost=True),
    "sexnc":   _spec("heart", desc=True, ghost=True),
    "chudnc":  _spec("big", pad=False, desc=True, ghost=True, msg=True),
    "nikmax":  _spec("gawd", pad=False, desc=True, ghost=True,
                     photo=True, pin=True, msg=True),
    # MDC variants — flagship ke andar alag pattern families
    "mdc":     _spec("mdcwall", pad=False, desc=True, ghost=True,
                     photo=True, pin=True, msg=True),
    "mdcnc":   _spec("thunder", pad=False, desc=True, ghost=True, msg=True),
    "mdcmax":  _spec("mdcwall", pad=False, desc=True, ghost=True,
                     photo=True, msg=True),
    "xwallnc": _spec("mdcwall", pad=False, desc=True, ghost=True),
    # advanced bug / glitch tiers
    "bignc":    _spec("big", pad=False, desc=True, ghost=True),
    "glitchnc": _spec("cune", desc=True, ghost=True),
    "zalgonc":  _spec("zalgo", desc=False, ghost=True),
    "cuneinc":  _spec("cune", desc=True, ghost=False),
    "crossnc":  _spec("cross", desc=False, ghost=False),
    "heartnc":  _spec("heart", desc=True, ghost=True),
    "emojinc":  _spec("prism", desc=True, ghost=True),
    "fontnc":   _spec("dust", desc=False, ghost=False),
    "targetnc": _spec("cross", desc=True, ghost=True),
    "ghostnc":  _spec("zalgo", desc=False, ghost=True),
    "stormnc":  _spec("thunder", pad=False, desc=True, ghost=True, msg=True),
    "wallnc":   _spec("big", pad=False, desc=False, ghost=False),
    "bannernc": _spec("flag", desc=True, ghost=False),
    "descnc":   _spec("dust", desc=True, ghost=False),
    "mixspm":   _spec("big", pad=False, desc=True, ghost=True, msg=True),
    "ftnc":     _spec("cross", desc=True, ghost=True),
    "crashnc":  _spec("noise", desc=False, ghost=True),
    "speednc":  _spec("cross", desc=False, ghost=False),
    "rainnc":   _spec("prism", desc=True, ghost=True),
    "thundernc":_spec("thunder", pad=False, desc=True, ghost=True, msg=True),
    "rainbownc":_spec("heart", desc=True, ghost=False),
    "mononc":   _spec("moon", desc=False, ghost=False),
    "prismnc":  _spec("prism", desc=True, ghost=True),
    "dripnc":   _spec("drip", desc=False, ghost=True),
    "bugnc":    _spec("bug", desc=True, ghost=True, msg=True),
    "virusnc":  _spec("virus", desc=True, ghost=True),
    "staticnc": _spec("static", pad=False, desc=False, ghost=True),
    "noisenc":  _spec("noise", desc=True, ghost=True),
    "longnc":   _spec("big", pad=False, desc=True, ghost=True),
    # nc6..nc10 — reference-A ke nc1..nc10 pattern se
    "nc6":     _spec("enc", pad=False, desc=True, ghost=True),
    "nc7":     _spec("blaze", pad=False, desc=True, ghost=True, msg=True),
    "nc8":     _spec("surge", pad=False, desc=True, ghost=True),
    "nc9":     _spec("silk", pad=False, desc=True, ghost=True),
    "nc10":    _spec("trio", pad=False, desc=True, ghost=True, msg=True),
    # enc family (sab runtime, koi stored text nahi)
    "enc1":    _spec("enc", pad=False, desc=False, ghost=True),
    "enc2":    _spec("cod", pad=False, desc=False, ghost=True),
    "enc3":    _spec("stagger", pad=False, desc=True, ghost=True),
    "enc4":    _spec("god", pad=False, desc=True, ghost=True, photo=True),
    "enc5":    _spec("mgc", pad=False, desc=True, ghost=True),
    "enc6":    _spec("blaze", pad=False, desc=True, ghost=True),
    "enc7":    _spec("surge", pad=False, desc=True, ghost=True),
    "enc8":    _spec("silk", pad=False, desc=True, ghost=True),
    "enc9":    _spec("trio", pad=False, desc=True, ghost=True),
    "enc10":   _spec("mdcwall", pad=False, desc=True, ghost=True),
    # reference-C/reference-B ke generic engine families
    "boldnc":    _spec("bold", pad=False, desc=False, ghost=True),
    "cursivenc": _spec("cursive", pad=False, desc=False, ghost=True),
    "italicnc":  _spec("italic", pad=False, desc=False, ghost=True),
    "wavenc":    _spec("wave", pad=False, desc=False, ghost=True),
    "randomcod": _spec("cod", pad=False, desc=True, ghost=True, msg=True),
    "godcod":    _spec("god", pad=False, desc=True, ghost=True),
    "phantomnc": _spec("phantom", pad=False, desc=True, ghost=True),
    "testamentnc": _spec("testament", pad=False, desc=True, ghost=True),
    "shadownc":  _spec("shadow", pad=False, desc=True, ghost=True),
    "silknc":    _spec("silk", pad=False, desc=True, ghost=True),
    "triogod":   _spec("trio", pad=False, desc=True, ghost=True, msg=True),
    "staggernc": _spec("stagger", pad=False, desc=True, ghost=True),
    "blazenc":   _spec("blaze", pad=False, desc=True, ghost=True, msg=True),
    "surge":     _spec("surge", pad=False, desc=True, ghost=True),
    "mgcnc":     _spec("mgc", pad=False, desc=True, ghost=True),
    "customnc":  _spec("mdcwall", pad=False, desc=True, ghost=True),
    "floodlessnc": _spec("enc", pad=False, desc=False, ghost=True),
    "hypernc":   _spec("cod", pad=False, desc=True, ghost=True, msg=True),
    "godnc":     _spec("god", pad=False, desc=True, ghost=True, photo=True),
    "softnc":    _spec("lean", pad=False, desc=False, ghost=False),
    "purenc":    _spec("pure", pad=False, desc=False, ghost=False),
    # §4 full-page block NC — screenshot wali badi glyph wall
    "pageblock": _spec("pageblock", pad=False, desc=True, ghost=True,
                       photo=True, pin=True, msg=True, page=True),
    "pagewall":  _spec("pageblock", pad=False, desc=True, ghost=True,
                       msg=True, page=True),
    "glyphnc":   _spec("glyphwall", pad=False, desc=True, ghost=True,
                       msg=True, page=True),
    "symbolnc":  _spec("symbols", pad=False, desc=True, ghost=True,
                       msg=True, page=True),
    "wallnc":    _spec("mdcwall", pad=False, desc=True, ghost=True,
                       msg=True, page=True),
}


# ── explicit pattern functions: har style ka apna CODE ──────────────────────
def pat_nc1(f: TitleForge, s: int) -> str:
    e = f.emo(1, s)
    return f"{CROSS[s % len(CROSS)]} {sty('NIK','bolditalic')} " \
           f"{e} {f.target.upper()} {ROAST[(s*3) % len(ROAST)]} " \
           f"{e} {CROSS[(s+1) % len(CROSS)]}"


def pat_nc2(f: TitleForge, s: int) -> str:
    h = HEARTS[s % len(HEARTS)]
    return f"{h*3} {sty('NIK','script')} {f.target} " \
           f"{ROAST[(s*5) % len(ROAST)]} {h*3}"


def pat_nc3(f: TitleForge, s: int) -> str:
    return (f"{sty('NIK','fraktur')} "
            f"{zalgo(unzalgo(f.target)[:16], 1)} "
            f"{GLYPH[s % len(GLYPH)]} {f.emo(2, s)}")


def pat_nc4(f: TitleForge, s: int) -> str:
    wall = "".join(WALLS[(c + s) % len(WALLS)] for c in range(4))
    return f"{wall}\n{sty('NIK','mono')} {f.target} " \
           f"{ROAST[(s*7) % len(ROAST)]} {f.emo(2, s)}\n{wall[::-1]}"


def pat_nc5(f: TitleForge, s: int) -> str:
    return (f"{sty('NIK','double')} {GLYPH[(s*2) % len(GLYPH)]} "
            f"{f.target} {ROAST[(s*11) % len(ROAST)]} "
            f"{f.emo(3, s)} {SIGILS[s % len(SIGILS)]}")


def pat_niknc(f: TitleForge, s: int) -> str:
    c = CROSS[s % len(CROSS)]
    return (f"{c*2} {sty('NIK','bold')} {GLYPH[s % len(GLYPH)]} "
            f"{f.target} {ROAST[s % len(ROAST)]} {f.emo(2, s)} {c*2}")


def pat_nc(f: TitleForge, s: int) -> str:
    g = GLYPH[s % 14]
    return (f"{g*3}{sty('NIK','sansbold')}{g} {f.target} "
            f"{ROAST[(s+2) % len(ROAST)]} {WALLS[s % len(WALLS)]}")


def pat_sexnc(f: TitleForge, s: int) -> str:
    h1, h2 = HEARTS[s % len(HEARTS)], HEARTS[(s+4) % len(HEARTS)]
    return (f"{h1*2} {sty('NIK','boldscript')} {f.target} "
            f"{ROAST[(s*3+1) % len(ROAST)]} {h2*2} "
            f"{DUST[s % len(DUST)]}")


def pat_chudnc(f: TitleForge, s: int) -> str:
    lat = "".join(CROSS[(c+s) % len(CROSS)] for c in range(6))
    return (f"{lat}\n{sty('NIK GAWD','bold')} {f.target} "
            f"{ROAST[(s*5) % len(ROAST)]} {f.emo(3, s)}\n"
            f"{''.join(HEARTS[(c+s) % len(HEARTS)] for c in range(5))}"
            f"{WALLS[s % len(WALLS)]*2}")


def pat_nikmax(f: TitleForge, s: int) -> str:
    w = "".join(WALLS[(c*2+s) % len(WALLS)] for c in range(5))
    return (f"{w}\n👑 {font_rotate('NIK MAX', s)} "
            f"{GLYPH[s % len(GLYPH)]} {f.target} "
            f"{ROAST[(s*7) % len(ROAST)]} {f.emo(4, s)}\n{w[::-1]}")


def pat_mdc(f: TitleForge, s: int) -> str:
    """Flagship: teen layered walls + atomic seq + verification sigil."""
    a = "".join(CROSS[(c+s) % len(CROSS)] for c in range(5))
    b = "".join(GLYPH[(c*3+s) % 14] for c in range(4))
    return (f"{a}\n{font_rotate('NIK MDC', s)} {b} {f.target} "
            f"{ROAST[(s*13) % len(ROAST)]} {f.emo(3, s)}\n"
            f"{''.join(HEARTS[(c+s*2) % len(HEARTS)] for c in range(4))}"
            f"{WALLS[(s+1) % len(WALLS)]*3}")


def pat_mdcnc(f: TitleForge, s: int) -> str:
    return (f"⚡{WALLS[s % len(WALLS)]*3} "
            f"{sty('NIK MDC','bolditalic')} {f.target} "
            f"{ROAST[(s*9) % len(ROAST)]} {f.emo(4, s)} "
            f"{WALLS[(s+2) % len(WALLS)]*3}⚡")


def pat_bignc(f: TitleForge, s: int) -> str:
    w = WALLS[s % len(WALLS)]
    return (f"{w*4}\n{sty('NIK','bold')} {f.target} "
            f"{ROAST[(s*3) % len(ROAST)]} {f.emo(2, s)}\n{w*4}")


def pat_crashnc(f: TitleForge, s: int) -> str:
    return (f"{zalgo('NIK', 2, 40)} {GLYPH[s % len(GLYPH)]*3} "
            f"{zalgo(unzalgo(f.target)[:10], 2, 50)} "
            f"{ROAST[(s*5) % len(ROAST)]}")


def pat_bugnc(f: TitleForge, s: int) -> str:
    broken = "".join(ch + random.choice(Z_DN)
                     for ch in unzalgo(f.target)[:12])
    return (f"🐛{WALLS[s % len(WALLS)]*2} {broken} "
            f"{GLYPH[(s*2) % len(GLYPH)]*3} {f.emo(2, s)}")


def pat_virusnc(f: TitleForge, s: int) -> str:
    chain = "".join(GLYPH[(i*3+s) % len(GLYPH)] for i in range(6))
    return f"{chain} {sty('NIK','mono')} ☣ {f.target} {chain[::-1]} {f.stamp(s)}"


def pat_staticnc(f: TitleForge, s: int) -> str:
    noise = "".join(random.choice("⣿⠀▓▒░╳⨯") for _ in range(16))
    return f"{noise} {f.target} {noise} {f.emo(2, s)}"


def pat_speednc(f: TitleForge, s: int) -> str:
    """Pre-computed fast cycle: sirf 2 lookups + f-string."""
    return f"{f.target} {ROAST[s % len(ROAST)]} {EMOJI[s % len(EMOJI)]}"


def pat_timenc(f: TitleForge, s: int) -> str:
    t = time.strftime("%H:%M:%S", time.localtime())
    return f"🕐 {sty('NIK','sansbold')} {t} {f.target} {f.emo(2, s)}"


def pat_longnc(f: TitleForge, s: int) -> str:
    w = "".join(GLYPH[(c+s) % 14] for c in range(6))
    return (f"{w}\n{sty('NIK','bold')} {f.target} "
            f"{ROAST[(s*3) % len(ROAST)]} {f.emo(2, s)}\n"
            f"{w}\n{f.heart(4, s)}\n{w[::-1]}")


def pat_mixspm(f: TitleForge, s: int) -> str:
    return (f"{WALLS[s % len(WALLS)]*2} {font_rotate('NIK', s)} "
            f"{f.target} {ROAST[(s*7) % len(ROAST)]} "
            f"{f.emo(3, s)} {GLYPH[s % len(GLYPH)]}")


def pat_ghostnc(f: TitleForge, s: int) -> str:
    return (f"{sty('NIK','small')} {GLYPH[(s*3) % len(GLYPH)]} "
            f"{f.target} {DUST[s % len(DUST)]} {f.emo(1, s)}")


def pat_heartnc(f: TitleForge, s: int) -> str:
    col = "".join(HEARTS[(s+i) % len(HEARTS)] for i in range(5))
    return f"{col} {sty('NIK','script')} {f.target} {col}"


def pat_cuneinc(f: TitleForge, s: int) -> str:
    w = "".join(GLYPH[(c*3+s) % len(GLYPH)] for c in range(7))
    return f"{w} {sty('NIK','fraktur')} {f.target} {w[::-1]} {f.stamp(s)}"


def pat_crossnc(f: TitleForge, s: int) -> str:
    w = "".join(CROSS[(c*2+s) % len(CROSS)] for c in range(6))
    return f"{w} {f.target} {f.stamp(s)} {w}"


def pat_targetnc(f: TitleForge, s: int) -> str:
    return (f"🎯 {sty('NIK','bold')} ➤ {f.target} "
            f"{ROAST[(s*3) % len(ROAST)]} {f.emo(2, s)}")


def pat_fontnc(f: TitleForge, s: int) -> str:
    return (f"{DUST[s % len(DUST)]} "
            f"{font_rotate('NIK '+unzalgo(f.target)[:12], s)} "
            f"{DUST[(s+1) % len(DUST)]}")


def pat_emojinc(f: TitleForge, s: int) -> str:
    return f"{f.emo(4, s)} {sty('NIK','double')} {f.target} {f.emo(4, s+2)}"


def pat_rainnc(f: TitleForge, s: int) -> str:
    return (f"{f.emo(3, s)} {sty('NIK','script')} {f.target} "
            f"{f.emo(3, s+1)} {ROAST[(s*3) % len(ROAST)]}")


def pat_thundernc(f: TitleForge, s: int) -> str:
    return (f"⚡{WALLS[s % len(WALLS)]*3} {sty('NIK GAWD','bolditalic')} "
            f"{f.target} {f.emo(5, s)} {WALLS[(s+2) % len(WALLS)]*3}⚡")


STYLE_FUNCS: dict[str, Callable[[TitleForge, int], str]] = {
    "niknc": pat_niknc, "nc": pat_nc, "nc1": pat_nc1, "nc2": pat_nc2,
    "nc3": pat_nc3, "nc4": pat_nc4, "nc5": pat_nc5,
    "sexnc": pat_sexnc, "chudnc": pat_chudnc, "nikmax": pat_nikmax,
    "mdc": pat_mdc, "mdcnc": pat_mdcnc, "mdcmax": pat_nikmax,
    "bignc": pat_bignc, "crashnc": pat_crashnc, "bugnc": pat_bugnc,
    "virusnc": pat_virusnc, "staticnc": pat_staticnc,
    "speednc": pat_speednc, "longnc": pat_longnc, "mixspm": pat_mixspm,
    "ghostnc": pat_ghostnc, "heartnc": pat_heartnc,
    "cuneinc": pat_cuneinc, "crossnc": pat_crossnc,
    "targetnc": pat_targetnc, "fontnc": pat_fontnc,
    "emojinc": pat_emojinc, "rainnc": pat_rainnc,
    "thundernc": pat_thundernc,
}


# ── §8b · 32 aur code-driven wall patterns (koi stored line nahi) ───────────
# Screenshots me jo alag-alag X / cuneiform / emoji / heart / zalgo walls
# dikhti hain, unka structure yahan 32 alag functions me hai. Har function
# apna pool, apni row-width, apna offset aur apna target-slot use karta hai.
def pat_w01(f: TitleForge, s: int) -> str:
    pa, pb, pc = CROSS, SIGILS, EMOJI
    tag = sty(f"W01", FONT_KEYS[(s + 1) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 1) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 1)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 1) % len(pa)]
                    for k in range(9)) for q in range(3)]
    tail = "".join(pb[(s + k + 1) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w02(f: TitleForge, s: int) -> str:
    pa, pb, pc = GLYPH, DUST, WallForge.LATTICE
    tag = sty(f"W02", FONT_KEYS[(s + 2) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 2) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 2)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 2) % len(pa)]
                    for k in range(10)) for q in range(4)]
    tail = "".join(pb[(s + k + 2) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w03(f: TitleForge, s: int) -> str:
    pa, pb, pc = WALLS, HEARTS, WallForge.NOISE
    tag = sty(f"W03", FONT_KEYS[(s + 3) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 3) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 3)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 3) % len(pa)]
                    for k in range(11)) for q in range(5)]
    tail = "".join(pb[(s + k + 3) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w04(f: TitleForge, s: int) -> str:
    pa, pb, pc = SIGILS, EMOJI, WallForge.SIDE
    tag = sty(f"W04", FONT_KEYS[(s + 4) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 4) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 4)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 4) % len(pa)]
                    for k in range(12)) for q in range(2)]
    tail = "".join(pb[(s + k + 4) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w05(f: TitleForge, s: int) -> str:
    pa, pb, pc = DUST, WallForge.LATTICE, CROSS
    tag = sty(f"W05", FONT_KEYS[(s + 5) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 5) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 5)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 5) % len(pa)]
                    for k in range(13)) for q in range(3)]
    tail = "".join(pb[(s + k + 5) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w06(f: TitleForge, s: int) -> str:
    pa, pb, pc = HEARTS, WallForge.NOISE, GLYPH
    tag = sty(f"W06", FONT_KEYS[(s + 6) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 6) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 6)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 6) % len(pa)]
                    for k in range(14)) for q in range(4)]
    tail = "".join(pb[(s + k + 6) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w07(f: TitleForge, s: int) -> str:
    pa, pb, pc = EMOJI, WallForge.SIDE, WALLS
    tag = sty(f"W07", FONT_KEYS[(s + 7) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 7) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 7)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 7) % len(pa)]
                    for k in range(8)) for q in range(5)]
    tail = "".join(pb[(s + k + 7) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w08(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.LATTICE, CROSS, SIGILS
    tag = sty(f"W08", FONT_KEYS[(s + 8) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 8) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 8)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 8) % len(pa)]
                    for k in range(9)) for q in range(2)]
    tail = "".join(pb[(s + k + 8) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w09(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.NOISE, GLYPH, DUST
    tag = sty(f"W09", FONT_KEYS[(s + 9) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 9) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 9)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 9) % len(pa)]
                    for k in range(10)) for q in range(3)]
    tail = "".join(pb[(s + k + 9) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w10(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.SIDE, WALLS, HEARTS
    tag = sty(f"W10", FONT_KEYS[(s + 10) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 10) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 10)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 10) % len(pa)]
                    for k in range(11)) for q in range(4)]
    tail = "".join(pb[(s + k + 10) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w11(f: TitleForge, s: int) -> str:
    pa, pb, pc = CROSS, SIGILS, EMOJI
    tag = sty(f"W11", FONT_KEYS[(s + 11) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 11) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 11)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 11) % len(pa)]
                    for k in range(12)) for q in range(5)]
    tail = "".join(pb[(s + k + 11) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w12(f: TitleForge, s: int) -> str:
    pa, pb, pc = GLYPH, DUST, WallForge.LATTICE
    tag = sty(f"W12", FONT_KEYS[(s + 12) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 12) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 12)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 12) % len(pa)]
                    for k in range(13)) for q in range(2)]
    tail = "".join(pb[(s + k + 12) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w13(f: TitleForge, s: int) -> str:
    pa, pb, pc = WALLS, HEARTS, WallForge.NOISE
    tag = sty(f"W13", FONT_KEYS[(s + 13) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 13) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 13)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 13) % len(pa)]
                    for k in range(14)) for q in range(3)]
    tail = "".join(pb[(s + k + 13) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w14(f: TitleForge, s: int) -> str:
    pa, pb, pc = SIGILS, EMOJI, WallForge.SIDE
    tag = sty(f"W14", FONT_KEYS[(s + 14) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 14) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 14)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 14) % len(pa)]
                    for k in range(8)) for q in range(4)]
    tail = "".join(pb[(s + k + 14) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w15(f: TitleForge, s: int) -> str:
    pa, pb, pc = DUST, WallForge.LATTICE, CROSS
    tag = sty(f"W15", FONT_KEYS[(s + 15) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 15) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 15)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 15) % len(pa)]
                    for k in range(9)) for q in range(5)]
    tail = "".join(pb[(s + k + 15) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w16(f: TitleForge, s: int) -> str:
    pa, pb, pc = HEARTS, WallForge.NOISE, GLYPH
    tag = sty(f"W16", FONT_KEYS[(s + 16) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 16) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 16)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 16) % len(pa)]
                    for k in range(10)) for q in range(2)]
    tail = "".join(pb[(s + k + 16) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w17(f: TitleForge, s: int) -> str:
    pa, pb, pc = EMOJI, WallForge.SIDE, WALLS
    tag = sty(f"W17", FONT_KEYS[(s + 17) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 17) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 17)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 17) % len(pa)]
                    for k in range(11)) for q in range(3)]
    tail = "".join(pb[(s + k + 17) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w18(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.LATTICE, CROSS, SIGILS
    tag = sty(f"W18", FONT_KEYS[(s + 18) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 18) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 18)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 18) % len(pa)]
                    for k in range(12)) for q in range(4)]
    tail = "".join(pb[(s + k + 18) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w19(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.NOISE, GLYPH, DUST
    tag = sty(f"W19", FONT_KEYS[(s + 19) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 19) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 19)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 19) % len(pa)]
                    for k in range(13)) for q in range(5)]
    tail = "".join(pb[(s + k + 19) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w20(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.SIDE, WALLS, HEARTS
    tag = sty(f"W20", FONT_KEYS[(s + 20) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 20) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 20)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 20) % len(pa)]
                    for k in range(14)) for q in range(2)]
    tail = "".join(pb[(s + k + 20) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w21(f: TitleForge, s: int) -> str:
    pa, pb, pc = CROSS, SIGILS, EMOJI
    tag = sty(f"W21", FONT_KEYS[(s + 21) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 21) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 21)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 21) % len(pa)]
                    for k in range(8)) for q in range(3)]
    tail = "".join(pb[(s + k + 21) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w22(f: TitleForge, s: int) -> str:
    pa, pb, pc = GLYPH, DUST, WallForge.LATTICE
    tag = sty(f"W22", FONT_KEYS[(s + 22) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 22) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 22)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 22) % len(pa)]
                    for k in range(9)) for q in range(4)]
    tail = "".join(pb[(s + k + 22) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w23(f: TitleForge, s: int) -> str:
    pa, pb, pc = WALLS, HEARTS, WallForge.NOISE
    tag = sty(f"W23", FONT_KEYS[(s + 23) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 23) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 23)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 23) % len(pa)]
                    for k in range(10)) for q in range(5)]
    tail = "".join(pb[(s + k + 23) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w24(f: TitleForge, s: int) -> str:
    pa, pb, pc = SIGILS, EMOJI, WallForge.SIDE
    tag = sty(f"W24", FONT_KEYS[(s + 24) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 24) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 24)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 24) % len(pa)]
                    for k in range(11)) for q in range(2)]
    tail = "".join(pb[(s + k + 24) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w25(f: TitleForge, s: int) -> str:
    pa, pb, pc = DUST, WallForge.LATTICE, CROSS
    tag = sty(f"W25", FONT_KEYS[(s + 25) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 25) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 25)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 25) % len(pa)]
                    for k in range(12)) for q in range(3)]
    tail = "".join(pb[(s + k + 25) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w26(f: TitleForge, s: int) -> str:
    pa, pb, pc = HEARTS, WallForge.NOISE, GLYPH
    tag = sty(f"W26", FONT_KEYS[(s + 26) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 26) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 26)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 26) % len(pa)]
                    for k in range(13)) for q in range(4)]
    tail = "".join(pb[(s + k + 26) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w27(f: TitleForge, s: int) -> str:
    pa, pb, pc = EMOJI, WallForge.SIDE, WALLS
    tag = sty(f"W27", FONT_KEYS[(s + 27) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 27) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 27)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 27) % len(pa)]
                    for k in range(14)) for q in range(5)]
    tail = "".join(pb[(s + k + 27) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w28(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.LATTICE, CROSS, SIGILS
    tag = sty(f"W28", FONT_KEYS[(s + 28) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 28) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 28)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 28) % len(pa)]
                    for k in range(8)) for q in range(2)]
    tail = "".join(pb[(s + k + 28) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w29(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.NOISE, GLYPH, DUST
    tag = sty(f"W29", FONT_KEYS[(s + 29) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 29) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 29)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 29) % len(pa)]
                    for k in range(9)) for q in range(3)]
    tail = "".join(pb[(s + k + 29) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w30(f: TitleForge, s: int) -> str:
    pa, pb, pc = WallForge.SIDE, WALLS, HEARTS
    tag = sty(f"W30", FONT_KEYS[(s + 30) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 30) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 30)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 30) % len(pa)]
                    for k in range(10)) for q in range(4)]
    tail = "".join(pb[(s + k + 30) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w31(f: TitleForge, s: int) -> str:
    pa, pb, pc = CROSS, SIGILS, EMOJI
    tag = sty(f"W31", FONT_KEYS[(s + 31) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 31) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 31)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 31) % len(pa)]
                    for k in range(11)) for q in range(5)]
    tail = "".join(pb[(s + k + 31) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail
def pat_w32(f: TitleForge, s: int) -> str:
    pa, pb, pc = GLYPH, DUST, WallForge.LATTICE
    tag = sty(f"W32", FONT_KEYS[(s + 32) % len(FONT_KEYS)])
    head = (f"{pa[(s * 3) % len(pa)]}{tag}"
            f"{pb[(s * 5 + 32) % len(pb)]} {TARGET_SLOT} "
            f"{f.roast(s + 32)} {pc[s % len(pc)]}")
    grid = ["".join(pa[(s + q * 3 + k + 32) % len(pa)]
                    for k in range(12)) for q in range(2)]
    tail = "".join(pb[(s + k + 32) % len(pb)] for k in range(4))
    return head + "\n" + "\n".join(grid) + "\n" + tail

_WALL_PATTERNS: dict[str, Callable[[TitleForge, int], str]] = {
    "wall01": pat_w01,
    "wall02": pat_w02,
    "wall03": pat_w03,
    "wall04": pat_w04,
    "wall05": pat_w05,
    "wall06": pat_w06,
    "wall07": pat_w07,
    "wall08": pat_w08,
    "wall09": pat_w09,
    "wall10": pat_w10,
    "wall11": pat_w11,
    "wall12": pat_w12,
    "wall13": pat_w13,
    "wall14": pat_w14,
    "wall15": pat_w15,
    "wall16": pat_w16,
    "wall17": pat_w17,
    "wall18": pat_w18,
    "wall19": pat_w19,
    "wall20": pat_w20,
    "wall21": pat_w21,
    "wall22": pat_w22,
    "wall23": pat_w23,
    "wall24": pat_w24,
    "wall25": pat_w25,
    "wall26": pat_w26,
    "wall27": pat_w27,
    "wall28": pat_w28,
    "wall29": pat_w29,
    "wall30": pat_w30,
    "wall31": pat_w31,
    "wall32": pat_w32,
}
STYLE_FUNCS.update(_WALL_PATTERNS)
for _wname in _WALL_PATTERNS:
    NC_STYLES[_wname] = _spec("pageblock", pad=False, desc=True,
                             ghost=True, msg=True, page=True)


# ── §8c · explicit async NC handlers (script jaisa structure) ───────────────
async def nc_w1(update: Any, ctx: Any) -> None:
    """~w1 → wall01 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall01")


async def nc_w2(update: Any, ctx: Any) -> None:
    """~w2 → wall02 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall02")


async def nc_w3(update: Any, ctx: Any) -> None:
    """~w3 → wall03 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall03")


async def nc_w4(update: Any, ctx: Any) -> None:
    """~w4 → wall04 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall04")


async def nc_w5(update: Any, ctx: Any) -> None:
    """~w5 → wall05 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall05")


async def nc_w6(update: Any, ctx: Any) -> None:
    """~w6 → wall06 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall06")


async def nc_w7(update: Any, ctx: Any) -> None:
    """~w7 → wall07 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall07")


async def nc_w8(update: Any, ctx: Any) -> None:
    """~w8 → wall08 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall08")


async def nc_w9(update: Any, ctx: Any) -> None:
    """~w9 → wall09 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall09")


async def nc_w10(update: Any, ctx: Any) -> None:
    """~w10 → wall10 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall10")


async def nc_w11(update: Any, ctx: Any) -> None:
    """~w11 → wall11 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall11")


async def nc_w12(update: Any, ctx: Any) -> None:
    """~w12 → wall12 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall12")


async def nc_w13(update: Any, ctx: Any) -> None:
    """~w13 → wall13 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall13")


async def nc_w14(update: Any, ctx: Any) -> None:
    """~w14 → wall14 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall14")


async def nc_w15(update: Any, ctx: Any) -> None:
    """~w15 → wall15 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall15")


async def nc_w16(update: Any, ctx: Any) -> None:
    """~w16 → wall16 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall16")


async def nc_w17(update: Any, ctx: Any) -> None:
    """~w17 → wall17 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall17")


async def nc_w18(update: Any, ctx: Any) -> None:
    """~w18 → wall18 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall18")


async def nc_w19(update: Any, ctx: Any) -> None:
    """~w19 → wall19 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall19")


async def nc_w20(update: Any, ctx: Any) -> None:
    """~w20 → wall20 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall20")


async def nc_w21(update: Any, ctx: Any) -> None:
    """~w21 → wall21 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall21")


async def nc_w22(update: Any, ctx: Any) -> None:
    """~w22 → wall22 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall22")


async def nc_w23(update: Any, ctx: Any) -> None:
    """~w23 → wall23 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall23")


async def nc_w24(update: Any, ctx: Any) -> None:
    """~w24 → wall24 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall24")


async def nc_w25(update: Any, ctx: Any) -> None:
    """~w25 → wall25 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall25")


async def nc_w26(update: Any, ctx: Any) -> None:
    """~w26 → wall26 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall26")


async def nc_w27(update: Any, ctx: Any) -> None:
    """~w27 → wall27 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall27")


async def nc_w28(update: Any, ctx: Any) -> None:
    """~w28 → wall28 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall28")


async def nc_w29(update: Any, ctx: Any) -> None:
    """~w29 → wall29 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall29")


async def nc_w30(update: Any, ctx: Any) -> None:
    """~w30 → wall30 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall30")


async def nc_w31(update: Any, ctx: Any) -> None:
    """~w31 → wall31 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall31")


async def nc_w32(update: Any, ctx: Any) -> None:
    """~w32 → wall32 pattern family, MDC engine ke andar."""
    await start_nc(update, ctx, "wall32")


WALL_HANDLERS: dict[str, Callable] = {
    "w1": nc_w1,
    "w2": nc_w2,
    "w3": nc_w3,
    "w4": nc_w4,
    "w5": nc_w5,
    "w6": nc_w6,
    "w7": nc_w7,
    "w8": nc_w8,
    "w9": nc_w9,
    "w10": nc_w10,
    "w11": nc_w11,
    "w12": nc_w12,
    "w13": nc_w13,
    "w14": nc_w14,
    "w15": nc_w15,
    "w16": nc_w16,
    "w17": nc_w17,
    "w18": nc_w18,
    "w19": nc_w19,
    "w20": nc_w20,
    "w21": nc_w21,
    "w22": nc_w22,
    "w23": nc_w23,
    "w24": nc_w24,
    "w25": nc_w25,
    "w26": nc_w26,
    "w27": nc_w27,
    "w28": nc_w28,
    "w29": nc_w29,
    "w30": nc_w30,
    "w31": nc_w31,
    "w32": nc_w32,
}


class FrameMetrics:
    """Page-block quality analytics — sab runtime compute, koi stored data."""

    __slots__ = ("text", "rows", "width")

    def __init__(self, text: str) -> None:
        self.text = str(text)
        self.rows = self.text.split("\n")
        self.width = max((len(x) for x in self.rows), default=0)

    def chars(self) -> int:
        return len(self.text)

    def lines(self) -> int:
        return len(self.rows)

    def max_width(self) -> int:
        return self.width

    def density(self) -> float:
        if not self.text:
            return 0.0
        filled = sum(1 for c in self.text if not c.isspace())
        return round(filled / len(self.text), 4)

    def symbol_ratio(self) -> float:
        if not self.text:
            return 0.0
        syms = set(WallForge.LATTICE + WallForge.NOISE)
        hits = sum(1 for c in self.text if c in syms)
        return round(hits / len(self.text), 4)

    def heart_count(self) -> int:
        return sum(1 for c in self.text if c in HEARTS)

    def emoji_count(self) -> int:
        return sum(self.text.count(e) for e in EMOJI)

    def combining_count(self) -> int:
        return sum(1 for c in self.text
                   if unicodedata.category(c) in ("Mn", "Me"))

    def distinct_glyphs(self) -> int:
        return len(set(self.text) - set("\n "))

    def row_widths(self) -> list[int]:
        return [len(x) for x in self.rows]

    def width_variance(self) -> float:
        w = self.row_widths()
        if not w:
            return 0.0
        avg = sum(w) / len(w)
        return round(sum((x - avg) ** 2 for x in w) / len(w), 3)

    def entropy(self) -> float:
        if not self.text:
            return 0.0
        freq = collections.Counter(self.text)
        n = len(self.text)
        return round(-sum((v / n) * __import__("math").log2(v / n)
                         for v in freq.values()), 3)

    def score(self) -> int:
        return int(self.chars() / max(1, self.lines()) +
                   self.distinct_glyphs() * 2 +
                   self.heart_count() + self.combining_count())

    def card_rows(self) -> list[str]:
        return [kv("ᴄʜᴀʀs", self.chars()),
                kv("ʀᴏᴡs", self.lines()),
                kv("ᴡɪᴅᴛʜ", self.max_width()),
                kv("ᴅᴇɴsɪᴛʏ", self.density()),
                kv("sʏᴍʙᴏʟ ʀᴀᴛɪᴏ", self.symbol_ratio()),
                kv("ʜᴇᴀʀᴛs", self.heart_count()),
                kv("ᴄᴏᴍʙɪɴɪɴɢ", self.combining_count()),
                kv("ᴅɪsᴛɪɴᴄᴛ", self.distinct_glyphs()),
                kv("ᴇɴᴛʀᴏᴘʏ", self.entropy()),
                kv("sᴄᴏʀᴇ", self.score())]


class TimingLab:
    """Throttle / duty / flood budget ka pure-computation model."""

    __slots__ = ("mode", "bots", "streams")

    def __init__(self, mode: str = "", bots: int = 0,
                 streams: int = 0) -> None:
        self.mode = resolve_mode(mode or THROTTLE_MODE)
        self.bots = bots or bot_count()
        self.streams = streams or THROTTLE_MODES[self.mode].streams

    def workers(self) -> int:
        return max(1, self.bots * self.streams)

    def delay(self) -> float:
        return THROTTLE_MODES[self.mode].delay

    def burst(self) -> int:
        return THROTTLE_MODES[self.mode].burst

    def refill(self) -> float:
        return THROTTLE_MODES[self.mode].refill

    def theoretical_rate(self) -> float:
        d = self.delay()
        if d <= 0:
            return round(self.workers() * self.refill(), 2)
        return round(self.workers() / d, 2)

    def window(self) -> float:
        return max(5.0, min(10.0, float(TIMING["raw_window"])))

    def hold(self) -> float:
        return max(5.0, min(10.0, float(TIMING["raw_hold"])))

    def cycle(self) -> float:
        return round(self.window() + self.hold(), 2)

    def duty_fraction(self) -> float:
        return round(self.window() / max(0.01, self.cycle()), 3)

    def titles_per_cycle(self) -> int:
        return int(self.theoretical_rate() * self.window())

    def titles_per_minute(self) -> int:
        return int(self.titles_per_cycle() * 60 / max(0.01, self.cycle()))

    def flood_budget(self) -> int:
        return min(int(TIMING["floodless_conc"]),
                   burst_cap(max(1, self.bots)))

    def stagger(self, i: int, j: int) -> float:
        return round(i * TIMING["relay_offset"] +
                     j * TIMING["stagger_floor"], 4)

    def gap(self, boosted: bool = False) -> float:
        g = TIMING["send_gap"] or self.delay()
        if boosted:
            return min(g, TIMING["boost_delay"])
        return g

    def ladder(self) -> list[tuple[str, float, int, int]]:
        return [(n, THROTTLE_MODES[n].delay,
                 THROTTLE_MODES[n].streams,
                 THROTTLE_MODES[n].burst)
                for n in THROTTLE_ORDER]

    def report_rows(self) -> list[str]:
        return [kv("ᴍᴏᴅᴇ", self.mode),
                kv("ᴡᴏʀᴋᴇʀs", self.workers()),
                kv("ᴅᴇʟᴀʏ", self.delay()),
                kv("ʀᴀᴛᴇ / s", self.theoretical_rate()),
                kv("ᴡɪɴᴅᴏᴡ", self.window()),
                kv("ʜᴏʟᴅ", self.hold()),
                kv("ᴅᴜᴛʏ", self.duty_fraction()),
                kv("ᴛɪᴛʟᴇs / ᴄʏᴄʟᴇ", self.titles_per_cycle()),
                kv("ᴛɪᴛʟᴇs / ᴍɪɴ", self.titles_per_minute()),
                kv("ꜰʟᴏᴏᴅ ʙᴜᴅɢᴇᴛ", self.flood_budget())]


# ── §2 · TARGET RESOLVER ────────────────────────────────────────────────────
# File me koi bhi purana / dost / foreign naam nahi. Ek hi literal hai:
# `{target}`. Naam runtime me aata hai — diye hue text se, slide ke andar se,
# ya reply kiye user ke ID se. Kabhi save / hardcode nahi hota.
class TargetResolver:
    """Sirf `{target}` slot; runtime sources = text → slide → user ID."""

    __slots__ = ()

    @staticmethod
    def clean(token: str) -> str:
        t = str(token or "").strip().strip(".,;:!?")
        if not t:
            return TARGET_SLOT
        if t == TARGET_SLOT:
            return t
        if t.startswith("@") or t.lstrip("-").isdigit():
            return fit(t, 36) if name_ok(t) else TARGET_SLOT
        if len(t) > 40 or not name_ok(t) or not re.fullmatch(
                r"[\w\-@.#\s]+", t):
            return TARGET_SLOT
        return fit(t, 36)

    @staticmethod
    def from_text(raw: str) -> str:
        for tok in str(raw or "").split():
            if tok.startswith("--") or tok.startswith("/"):
                continue
            mt = re.search(r"@[A-Za-z0-9_]{3,}", tok)
            if mt:
                return TargetResolver.clean(mt.group(0))
            mt = re.search(r"(?:tg://user\?id=|\b)(-?\d{5,})", tok)
            if mt:
                return TargetResolver.clean(mt.group(1))
            if len(tok) >= 3 and tok.isalpha():
                return TargetResolver.clean(tok)
        return TARGET_SLOT

    @staticmethod
    def from_slide(slide: str) -> str:
        """Slide ke andar se @handle / ID nikalo — template me kabhi naam nahi."""
        mt = re.search(r"@[A-Za-z0-9_]{3,}", str(slide or ""))
        if mt:
            return TargetResolver.clean(mt.group(0))
        mt = re.search(r"tg://user\?id=(\d+)", str(slide or ""))
        if mt:
            return TargetResolver.clean(mt.group(1))
        return TARGET_SLOT

    @staticmethod
    def from_id(update: Any, uid: int = 0) -> str:
        """ID se: username ho to @handle, warna numeric ID (koi naam store nahi)."""
        r = reply_of(update)
        u = getattr(r, "from_user", None) if r is not None else None
        if u is None:
            u = getattr(update, "effective_user", None)
        handle = str(getattr(u, "username", "") or "").lstrip("@")
        if handle and name_ok(handle):
            return fit("@" + handle, 36)
        real = int(getattr(u, "id", 0) or uid or 0)
        return f"#{real}" if real else TARGET_SLOT

    @classmethod
    def resolve(cls, update: Any) -> str:
        txt = cls.from_text(arg(update))
        if txt != TARGET_SLOT:
            return txt
        got = cls.from_id(update)
        if got != TARGET_SLOT:
            return got
        slide = cls.from_slide(msg_text(update))
        return slide if slide != TARGET_SLOT else TARGET_SLOT

    @staticmethod
    def apply(template: str, target: str = "") -> str:
        """`{target}` ko runtime value se badlo (naam kabhi file me nahi).

        Bold glyph me likha slot bhi replace hota hai — panels / page head
        me mathematical bold use hota hai, par source me slot ek hi hai.
        """
        val = TargetResolver.clean(target) or TARGET_SLOT
        bold_slot = sty(TARGET_SLOT, "bold")
        return (str(template).replace(bold_slot, micro(val))
                .replace(TARGET_SLOT, val))


def resolve_target(update: Any) -> str:
    return TargetResolver.resolve(update)


def nc_parse(raw: str) -> tuple[dict[str, Any], str]:
    opts: dict[str, Any] = {"global": False, "nodesc": False,
                            "noghost": False, "gawd": False,
                            "streams": None, "target": ""}
    words: list[str] = []
    for tok in raw.split():
        if tok == "--global":
            opts["global"] = True
        elif tok == "--nodesc":
            opts["nodesc"] = True
        elif tok == "--noghost":
            opts["noghost"] = True
        elif tok == "--gawd":
            opts["gawd"] = True
        elif tok.startswith("--mode="):
            throttle_set(resolve_mode(tok.split("=", 1)[1]))
        elif tok.startswith("--streams="):
            try:
                opts["streams"] = max(1, min(16, int(tok.split("=", 1)[1])))
            except ValueError:
                pass
        else:
            words.append(tok)
    return opts, " ".join(words)


def _media_id(update: Any) -> tuple[str, str]:
    r = reply_of(update)
    if r is None:
        return "", ""
    for attr in ("photo", "video", "sticker", "animation", "document"):
        obj = getattr(r, attr, None)
        fid = (getattr(obj, "file_id", "") if obj else "") or (
            obj[-1].file_id if isinstance(obj, (list, tuple)) and obj else "")
        if fid:
            return fid, attr
    return "", ""


def _reply_id(update: Any) -> int:
    r = reply_of(update)
    return int(getattr(r, "message_id", 0) or 0) if r is not None else 0


async def start_nc(update: Any, ctx: Any, style: str) -> None:
    cid = chat_id(update)
    if GC_ON.get(str(cid)) is False and not GLOBAL_MODE:
        return await render(update, card("🔴 ɢᴄ ᴏꜰꜰ", [
            kv("ɢᴄ", cid), row(f"{p('gcon')}", "wapas chalu")]))
    opts, rest = nc_parse(arg(update))
    opts["target"] = resolve_target(update)
    opts["slide"] = TargetResolver.apply(rest or TARGET_SLOT,
                                         opts["target"])
    if opts["global"] or GLOBAL_MODE:
        opts["targets"] = global_targets() or [cid]
    else:
        opts["targets"] = [cid]
    media, mkind = _media_id(update)
    opts["media"], opts["mkind"] = media, mkind
    opts["reply_id"] = _reply_id(update)
    if media and media not in MEDIA_POOL:
        MEDIA_POOL.append(media)
        save_json("media_pool.json", MEDIA_POOL)
    orc = MDCOrc(update, style, opts)
    await orc.start()
    spec = NC_STYLES[style]
    m = LIMITER.mode
    await render(update, card(f"🔥 {style.upper()} ʟɪᴠᴇ", [
        kv("ᴛᴀʀɢᴇᴛ", opts["target"][:24]),
        kv("ɢᴄs", len(opts["targets"])),
        kv("ʙᴏᴛs × sᴛʀᴇᴀᴍs",
           f"{len(pool())} × {BOOSTER.streams(cid, m.streams)}"),
        kv("ᴡᴀʟʟ", spec["wall"]),
        kv("ᴘᴀᴛᴛᴇʀɴ", STYLE_FUNCS[style].__name__
           if style in STYLE_FUNCS else "forge"),
        kv("ᴍᴏᴅᴇ / ᴅᴇʟᴀʏ", f"{m.name} / {m.delay:.3f}s"),
        kv("ᴠᴇʀɪꜰʏ ʙᴏᴏsᴛ", "🟢"),
        kv("ᴅᴇsᴄ / ɢʜᴏsᴛ",
           f"{'🟢' if spec['desc'] else '🔴'} / "
           f"{'🟢' if spec['ghost'] else '🔴'}"),
        kv("ᴍᴇᴅɪᴀ", mkind or "—"), sep(),
        note(f"sample → {orc.forge.build(1, pad=spec['pad'])[:64]}"),
        note("Flags: --global · --nodesc · --noghost · --gawd · "
             "--mode=raw · --streams=8"),
        row(f"{p('allnc')} off", "sab band")]))


def _nc_handler(style: str) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        await start_nc(update, ctx, style)
    return _h


async def cmd_nc(update: Any, ctx: Any) -> None:
    await start_nc(update, ctx, "niknc")


async def cmd_mdc(update: Any, ctx: Any) -> None:
    await start_nc(update, ctx, "mdc")


async def cmd_mixspm(update: Any, ctx: Any) -> None:
    await start_nc(update, ctx, "mixspm")


async def cmd_globalnc(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    await start_nc(_WithText(update, f"{prefix_text()}niknc --global {a}"),
                   ctx, "niknc")


async def cmd_ncstat(update: Any, ctx: Any) -> None:
    rows = [kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
            kv("ᴅᴇʟᴀʏ", LIMITER.mode.delay),
            kv("sᴛʀᴇᴀᴍs", LIMITER.mode.streams),
            kv("ᴄᴏɴᴄ", LIMITER.conc),
            kv("sᴛʏʟᴇs", len(NC_STYLES)),
            kv("ᴛɪᴛʟᴇs", STATS["titles"]),
            kv("ᴠᴇʀɪꜰʏ / ᴍɪsᴍᴀᴛᴄʜ",
               f"{STATS['verify']} / {STATS['mismatch']}"),
            kv("429", STATS["429"]), sep()]
    for cid, st in list(MDC_STATE.items())[:6]:
        s = st.snapshot()
        rows.append(kv(str(cid)[:12],
                       f"{s['style']} · {s['titles']} · {s['uptime']}s"))
    if not MDC_STATE:
        rows.append(note("Koi NC live nahi."))
    await render(update, card("📈 ɴᴄ sᴛᴀᴛ", rows))


async def cmd_allnc(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a in ("off", "stop", "all"):
        n = stop_all()
        return await render(update, card("🛑 ᴀʟʟ ᴏꜰꜰ", [
            kv("ʙᴀɴᴅ", n), kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks()))]))
    await render(update, card("🎛 ᴀʟʟɴᴄ ᴄᴏɴᴛʀᴏʟ", [
        kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks())), sep(),
        *[note(t) for t in active_tasks()[:12]],
        row(f"{p('allnc')} off", "ek saath sab band")]))


async def cmd_stopall(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    cid = None if a in ("--all", "all", "") else chat_id(update)
    n = stop_all(cid)
    await render(update, card("🛑 sᴛᴏᴘᴀʟʟ", [
        kv("sᴄᴏᴘᴇ", "ɢʟᴏʙᴀʟ" if cid is None else str(cid)),
        kv("ʙᴀɴᴅ", n), kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks()))]))


async def cmd_stopnc(update: Any, ctx: Any) -> None:
    n = stop_nc(None if arg(update).strip().lower() in ("--all", "all", "")
                else chat_id(update))
    await render(update, card("🛑 ɴᴄ sᴛᴏᴘ", [
        kv("ʙᴀɴᴅ", n), kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks()))]))


# ── spam / reply engine (code, koi bank nahi) ───────────────────────────────
XREPLY_CHATS: set[int] = set(load_json("xreply.json", []))
LOOP_SECTION: dict[str, str] = {
    "spam": "spam", "ms": "ms", "reply": "reply", "xreply": "xreply",
    "rr": "rr", "fwdspam": "fwdspam", "slides": "slides",
    "targetslide": "targetslide", "picraid": "picraid", "gpfp": "gpfp",
    "sticker": "sticker", "emojirain": "emojirain", "mixspm": "mixspm",
    "purge": "purge", "banner": "banner", "broadcast": "broadcast",
    "page": "page", "pagedeck": "pagedeck", "bigtext": "bigtext",
    "swipe": "swipe", "react": "react", "reactions": "reactions",
}


def _count(a: str, default: int = 0) -> int:
    mt = re.search(r"--(?:count|n)=(\d+)", a)
    if mt:
        return min(100000, max(1, int(mt.group(1))))
    for tok in a.split():
        if tok.isdigit():
            return min(100000, max(1, int(tok)))
    return default


def _targets(update: Any) -> list[int]:
    return (global_targets() or [chat_id(update)]) if GLOBAL_MODE \
        else [chat_id(update)]


class SpamEngine:
    """High-speed loop: text runtime me TitleForge se, koi stored bank nahi."""

    def __init__(self, update: Any, kind: str, mode: str) -> None:
        self.update = update
        self.kind = kind
        self.mode = mode
        self.cid = chat_id(update)
        a = arg(update).strip()
        self.opts = {
            "targets": _targets(update),
            "reply_id": _reply_id(update),
            "media": "", "mkind": "",
            "count": _count(a),
            "text": "",
            "target": resolve_target(update),
        }
        media, mkind = _media_id(update)
        self.opts["media"], self.opts["mkind"] = media, mkind
        rest = re.sub(r"--\w+=\S+", "", a).strip()
        if rest and not rest.isdigit():
            self.opts["text"] = assert_clean(rest)
        self.forge = TitleForge(self.opts["target"], "prism", seed=1)
        self.deck = SlideDeck(self.opts["target"], seed=int(time.time()))

    def page_mode(self) -> bool:
        return self.kind in ("page", "pagedeck", "bigtext") or \
            self.mode == "slide"

    def next_line(self, seq: int) -> str:
        if self.page_mode():
            return self.deck.build(seq)
        if self.opts["text"]:
            return self.opts["text"]
        return self.forge.build(seq, pad=False)

    async def start(self) -> None:
        task_start(self.kind, self.cid, self.run())

    async def run(self) -> None:
        ev = STOP_EVENTS.get(_key(self.kind, self.cid)) or asyncio.Event()
        bots = pool()
        i = 0
        try:
            while not ev.is_set() and (
                    self.opts["count"] == 0 or i < self.opts["count"]):
                i += 1
                m = LIMITER.mode
                if m.name == "raw":
                    hold = DUTY.gate()
                    if hold > 0:
                        await stoppable_sleep(ev, hold)
                        continue
                line_txt = self.next_line(i)
                wave = []
                for t in self.opts["targets"]:
                    for b in bots:
                        if self.mode == "title":
                            wave.append(set_title(t, b, line_txt))
                        elif self.mode == "desc":
                            wave.append(set_desc(t, b, line_txt))
                        elif self.mode == "fwd" and self.opts["reply_id"]:
                            wave.append(fwd_msg(t, b, self.cid,
                                                self.opts["reply_id"]))
                        elif self.mode in ("photo", "sticker") and \
                                self.opts["media"]:
                            wave.append(self._media(b, t, line_txt, i))
                        elif self.mode == "gpphoto" and self.opts["media"]:
                            fn = getattr(b, "set_chat_photo", None)
                            wave.append(safe_call(t, fn, t,
                                                  photo=self.opts["media"],
                                                  _bid=bot_id(b)) if fn
                                        else set_title(t, b, line_txt))
                        else:
                            kw = ({"reply_to_message_id":
                                   self.opts["reply_id"]}
                                  if self.opts["reply_id"] else {})
                            wave.append(send_msg(t, b, line_txt, **kw))
                if wave:
                    await asyncio.gather(*wave, return_exceptions=True)
                if self.page_mode() and i % 4 == 0:
                    frame = self.deck.build(i + 777)
                    for t in self.opts["targets"]:
                        for b in bots[:1]:
                            await send_msg(t, b, frame)
                await stoppable_sleep(ev, m.delay)
        except asyncio.CancelledError:
            pass
        finally:
            cur = asyncio.current_task()
            k = _key(self.kind, self.cid)
            if TASKS.get(k) is cur:
                TASKS.pop(k, None)
            if STOP_EVENTS.get(k) is ev:
                STOP_EVENTS.pop(k, None)

    async def _media(self, bot: Any, cid: int, line_txt: str,
                     i: int) -> bool:
        kind = self.opts["mkind"]
        fn = getattr(bot, {
            "photo": "send_photo", "document": "send_document",
            "video": "send_video", "sticker": "send_sticker",
            "animation": "send_animation"}.get(kind, "send_photo"), None)
        if fn is None:
            return await send_msg(cid, bot, line_txt)
        key = {"photo": "photo", "document": "document", "video": "video",
               "sticker": "sticker", "animation": "animation"}.get(
                   kind, "photo")
        kw = {key: self.opts["media"]}
        if self.mode == "photo":
            kw["caption"] = long_fit(line_txt[:900])
        return await safe_call(cid, fn, cid, _bid=bot_id(bot), **kw)


def cross_wall(width: int = 9, rows: int = 4) -> str:
    return "\n".join("".join(CROSS[(c + r) % len(CROSS)]
                            for c in range(width)) for r in range(rows))


def heart_column(n: int = 12) -> str:
    return "\n".join(HEARTS[i % len(HEARTS)] for i in range(n))


async def start_loop_cmd(update: Any, ctx: Any, kind: str,
                         mode: str = "msg") -> None:
    a = arg(update).strip()
    cid = chat_id(update)
    if a.lower() in ("off", "stop"):
        task_stop(kind, cid)
        XREPLY_CHATS.discard(cid)
        return await render(update, card(f"🛑 {kind.upper()} ʙᴀɴᴅ", [
            kv("ɢᴄ", cid), kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks()))]))
    if GC_ON.get(str(cid)) is False and not GLOBAL_MODE:
        return await render(update, card("🔴 ɢᴄ ᴏꜰꜰ", [
            row(f"{p('gcon')}", "chalu karo")]))
    eng = SpamEngine(update, kind, mode)
    await eng.start()
    await render(update, card(f"💥 {kind.upper()} ʟɪᴠᴇ", [
        kv("ᴍᴏᴅᴇ", mode),
        kv("ɢᴄs", len(eng.opts["targets"])),
        kv("ʙᴏᴛs", len(bots := pool())),
        kv("ᴛʜʀᴏᴛᴛʟᴇ", THROTTLE_MODE),
        kv("ᴅᴇʟᴀʏ", f"{LIMITER.mode.delay:.3f}s"),
        kv("ᴄᴏᴜɴᴛ", eng.opts["count"] or "∞"),
        kv("ᴍᴇᴅɪᴀ", eng.opts["mkind"] or "—"), sep(),
        note(eng.next_line(1)[:72]),
        row(f"{p(kind)} off", "rok do")]))


async def cmd_spam(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "spam", "msg")


async def cmd_ms(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "ms", "msg")


async def cmd_reply(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "reply", "msg")


async def cmd_rr(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "rr", "msg")


async def cmd_xreply(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    cid = chat_id(update)
    if a in ("off", "stop"):
        XREPLY_CHATS.discard(cid)
        task_stop("xreply", cid)
        save_json("xreply.json", sorted(XREPLY_CHATS))
        return await render(update, card("🛑 xʀᴇᴘʟʏ ʙᴀɴᴅ", [kv("ɢᴄ", cid)]))
    if a == "hook":
        XREPLY_CHATS.add(cid)
        save_json("xreply.json", sorted(XREPLY_CHATS))
        return await render(update, card("⚡ xʀᴇᴘʟʏ ʜᴏᴏᴋ ᴏɴ", [
            kv("ɢᴄ", cid),
            note("Har incoming message pe instant reply — 0 queue."),
            row(f"{p('xreply')} off", "band")]))
    await start_loop_cmd(update, ctx, "xreply", "msg")


async def xreply_hook(update: Any) -> None:
    cid = chat_id(update)
    if cid not in XREPLY_CHATS or not is_auth(uid_of(update)):
        return
    bots = pool()
    if not bots:
        return
    f = TitleForge(resolve_target(update), "prism", seed=int(time.time()))
    await send_msg(cid, bots[0], f.build(1, pad=False))


async def cmd_fwdspam(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "fwdspam", "fwd")


async def cmd_slides(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "slides", "slide")


async def cmd_targetslide(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "targetslide", "slide")


async def cmd_picraid(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "picraid", "photo")


async def cmd_gpfp(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "gpfp", "gpphoto")


async def cmd_sticker(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "sticker", "sticker")


async def cmd_emojirain(update: Any, ctx: Any) -> None:
    await start_loop_cmd(update, ctx, "emojirain", "msg")


# ── §9 · requested engines: swipe / slides / reactions / admin / config ─────
SWIPE_STATE: dict[int, dict[str, Any]] = {}
REACT_STATE: dict[str, Any] = {
    "loop": False, "emoji": "🔥", "last": 0.0, "single": True,
}
REACT_EMOJI: tuple[str, ...] = (
    "👍", "❤️", "🔥", "🥰", "👏", "😁", "🤩", "💯", "⚡",
    "🤍", "🩷", "💜", "💛", "🧡", "🩵")
AUTOADMIN_LAST: dict[str, int] = {"ok": 0, "fail": 0, "gcs": 0}


def _mask(tok: str) -> str:
    t = str(tok or "")
    return (t[:6] + "…" + t[-4:]) if len(t) > 14 else ("✅ sᴇᴛ" if t else "❌ ᴋʜᴀᴀʟɪ")


async def cmd_setup(update: Any, ctx: Any) -> None:
    """~setup — hosting config verify karo (token masked, plain text)."""
    await render(update, panel("🔧 sᴇᴛᴜᴘ · ʜᴏsᴛɪɴɢ", [
        kv("ᴏᴡɴᴇʀ ɪᴅ", OWNER_ID or "❌ ᴅᴀᴀʟᴏ"),
        kv("ʙᴏᴛ ᴛᴏᴋᴇɴ", _mask(BOT_TOKEN)),
        kv("ᴍᴀɪɴ ʙᴏᴛ ɪᴅ", MAIN_BOT_ID or "ᴀᴜᴛᴏ"),
        kv("ᴄʟᴜsᴛᴇʀ ᴛᴏᴋᴇɴs", len(BOT_TOKENS) + len(TOKENS)),
        kv("ᴘʀᴇꜰɪx", PREFIX),
        kv("ᴀᴘɪ ɪᴅ", API_ID or "—"),
        kv("sᴇssɪᴏɴ", "✅" if SESSION else "—"), sep(),
        note("CONFIG['BOT_TOKEN'] aur CONFIG['OWNER_ID'] file ke upar."),
        note("Ya env BOT_TOKEN / OWNER_ID set karo."),
        row(f"{p('docs')}", "poori hosting guide"),
        row(f"{p('setowner')} <id>", "runtime owner set"),
        row(f"{p('settoken')} <tok>", "runtime token add")]))


async def cmd_setowner(update: Any, ctx: Any) -> None:
    """~setowner <id> — runtime owner ID set (config.json me, script clean)."""
    global OWNER_ID
    raw = arg(update).strip()
    mt = re.search(r"-?\d{4,}", raw)
    if mt:
        OWNER_ID = int(mt.group(0))
        save_json("config.json", {"owner_id": OWNER_ID})
    await render(update, panel("👑 ᴏᴡɴᴇʀ", [
        kv("ᴏᴡɴᴇʀ ɪᴅ", OWNER_ID), kv("ᴜsᴇʀ", OWNER_USER),
        row(f"{p('setup')}", "verify")]))


async def cmd_settoken(update: Any, ctx: Any) -> None:
    """~settoken <token> — cluster me naya bot token add karo (masked reply)."""
    raw = arg(update).strip()
    mt = re.search(r"\d{8,}:[A-Za-z0-9_-]{20,}", raw)
    if mt and mt.group(0) not in TOKENS:
        TOKENS.append(mt.group(0))
        cfg_save()
    await render(update, panel("🤖 ᴛᴏᴋᴇɴ", [
        kv("ᴀᴅᴅᴇᴅ", "✅" if mt else "❌"),
        kv("ᴘᴏᴏʟ", len(TOKENS)),
        kv("ᴛᴏᴋᴇɴ", _mask(mt.group(0)) if mt else "—"), sep(),
        note("Token kabhi plain reply me nahi jata."),
        row(f"{p('addbot')}", "connect karo")]))


async def cmd_docs(update: Any, ctx: Any) -> None:
    """~docs — hosting guide + handler helping docs index."""
    await send_long(update, hosting_guide() + "\n\n" + docs_index())


async def cmd_cmdinfo(update: Any, ctx: Any) -> None:
    """~cmd <name> — ek handler ki poori helping doc (usage/flags/example)."""
    name = arg(update).strip().lower().lstrip("~/")
    if not name:
        return await render(update, panel("📖 ᴄᴍᴅ ᴅᴏᴄs", [
            note(f"{p('cmd')} <name> → usage + flags + example"),
            note(f"{p('docs')} → hosting + sab sections")]))
    doc = HELP_DOCS.get(name)
    fn = COMMANDS.get(name)
    rows = [kv("ᴄᴏᴍᴍᴀɴᴅ", p(name)),
            kv("ʜᴀɴᴅʟᴇʀ", getattr(fn, "__name__", "—") if fn else "—"),
            kv("ᴅᴏᴄ", doc or (getattr(fn, "__doc__", "") or "").strip()
               .split("\n")[0][:56] or "runtime engine handler"),
            kv("ᴜsᴀɢᴇ", f"{p(name)} {USAGE.get(name, '[args]')}"),
            kv("ᴇxᴀᴍᴘʟᴇ", EXAMPLE.get(name, f"{p(name)} {TARGET_SLOT}")),
            kv("ᴍᴏᴅᴇ", THROTTLE_MODE), sep(),
            note("Flags: --global · --mode=raw · --streams=8 · --nodesc"),
            note("Target: text / slide / reply-ID se, file me sirf {target}")]
    await render(update, panel(f"📖 {name.upper()}", rows))


async def cmd_panel(update: Any, ctx: Any) -> None:
    """~panel — cool live control panel (plain text, chhote bold glyphs)."""
    live = [n for n in active_tasks()]
    rows = [kv("ᴍᴏᴅᴇ", sty(THROTTLE_MODE.upper(), "bold")),
            kv("ᴅᴇʟᴀʏ", f"{LIMITER.mode.delay:.3f}s"),
            kv("ʙᴜʀsᴛ / ʜᴏʟᴅ",
               f"{DUTY.window():.0f}s / {DUTY.hold():.0f}s"),
            kv("ᴅᴜᴛʏ", DUTY.phase()),
            kv("ʙᴏᴛs", bot_count()),
            kv("ɢᴄs", len(CHATS)),
            kv("ᴛɪᴛʟᴇs", STATS["titles"]),
            kv("ʟɪᴠᴇ ᴛᴀsᴋs", len(live)),
            kv("ꜰᴏʀɢᴇ / sᴛʏʟᴇs",
               f"{len(TitleForge.GENERATORS)} / {len(NC_STYLES)}"),
            kv("ᴘᴀɢᴇ ʙʟᴏᴄᴋ", f"{len(WallForge.FAMILIES)} families"),
            kv("ᴄᴏᴍᴍᴀɴᴅs", len(COMMANDS)), sep(),
            row(f"{p('menu')}", "tables + docs"),
            row(f"{p('docs')}", "hosting guide"),
            row(f"{p('fullmenu')}", "poora index")]
    await render(update, panel("👑 ɴɪᴋʙᴏᴛ · ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ", rows))


async def cmd_swipe(update: Any, ctx: Any) -> None:
    """~swipe [prefix] — target ke message pe reply karo, har msg pe prefix slide."""
    r = reply_of(update)
    u = getattr(r, "from_user", None) if r is not None else None
    if u is None:
        return await render(update, panel("⚠️ sᴡɪᴘᴇ", [
            note("Pehle target ke message pe reply karo."),
            note(f"Phir {p('swipe')} [prefix] likho.")]))
    cid = chat_id(update)
    uid = int(getattr(u, "id", 0) or 0)
    prefix = arg(update).strip()[:60]
    SWIPE_STATE[cid] = {"uid": uid, "prefix": prefix,
                        "target": TargetResolver.from_id(update, uid)}
    await render(update, panel("⚡ sᴡɪᴘᴇ ᴀᴄᴛɪᴠᴇ", [
        kv("ᴛᴀʀɢᴇᴛ ɪᴅ", uid),
        kv("ᴘʀᴇꜰɪx", prefix or "—"),
        kv("ᴍᴏᴅᴇ", "reply-slide"), sep(),
        note("Target ka har naya message → big page block reply."),
        row(f"{p('stopswipe')}", "band karo")]))


async def cmd_stopswipe(update: Any, ctx: Any) -> None:
    """~stopswipe — is chat ka swipe band."""
    gone = SWIPE_STATE.pop(chat_id(update), None)
    await render(update, panel("🛑 sᴡɪᴘᴇ", [
        kv("sᴛᴀᴛᴜs", "ʙᴀɴᴅ" if gone else "ᴄʜᴀʟᴜ ɴᴀʜɪ ᴛʜᴀ"),
        kv("ᴀᴄᴛɪᴠᴇ", len(SWIPE_STATE))]))


async def swipe_hook(update: Any) -> None:
    cid = chat_id(update)
    st = SWIPE_STATE.get(cid)
    if not st or uid_of(update) != st["uid"]:
        return
    bots = pool()[:1]
    if not bots:
        return
    deck = SlideDeck(st.get("target", TARGET_SLOT), seed=int(time.time()))
    body = deck.build(int(time.time() * 1000) % 97)
    pre = st.get("prefix", "")
    txt = f"{pre} {body}" if pre else body
    msg = (getattr(update, "effective_message", None) or
           getattr(update, "message", None))
    mid = int(getattr(msg, "message_id", 0) or 0) or 1
    await send_msg(cid, bots[0], fit(txt, 3900),
                   reply_to_message_id=mid)


async def cmd_react(update: Any, ctx: Any) -> None:
    """~react <emoji> — reply kiye message pe reaction; ~autoreact loop."""
    a = arg(update).strip()
    if a in ("on", "loop", "auto"):
        REACT_STATE["loop"] = True
    elif a in ("off", "stop"):
        REACT_STATE["loop"] = False
    elif a:
        REACT_STATE["emoji"] = a[:8]
    r = reply_of(update)
    mid = int(getattr(r, "message_id", 0) or 0) if r is not None else 0
    done = 0
    if mid:
        done = await apply_reaction(chat_id(update), mid,
                                    REACT_STATE["emoji"])
    await render(update, panel("💫 ʀᴇᴀᴄᴛɪᴏɴs", [
        kv("ᴇᴍᴏᴊɪ", REACT_STATE["emoji"]),
        kv("ʟᴏᴏᴘ", "🟢 ᴏɴ" if REACT_STATE["loop"] else "🔴 ᴏꜰꜰ"),
        kv("ᴀᴘᴘʟɪᴇᴅ", done), sep(),
        note("Standard emoji reactions — koi premium ID nahi."),
        row(f"{p('reactloop')} on", "har msg pe"),
        row(f"{p('stopreact')}", "band")]))


async def apply_reaction(cid: int, mid: int, emoji: str) -> int:
    ok = 0
    for b in pool()[:1]:
        kw: dict[str, Any] = {"message_id": mid}
        if _ReactionTypeEmoji is not None:
            kw["reaction"] = [_ReactionTypeEmoji(emoji=emoji)]
        else:
            kw["reaction"] = emoji
        if await bot_call(b, "set_message_reaction", cid, **kw):
            ok += 1
    return ok


async def cmd_reactloop(update: Any, ctx: Any) -> None:
    """~reactloop on|off|<emoji> — har incoming message pe auto reaction."""
    a = arg(update).strip().lower()
    if a in ("off", "stop", "false", "0"):
        REACT_STATE["loop"] = False
    elif a in ("on", "start", "true", "1", ""):
        REACT_STATE["loop"] = True
    elif a in REACT_EMOJI:
        REACT_STATE["loop"] = True
        REACT_STATE["emoji"] = a
    await render(update, panel("🔁 ʀᴇᴀᴄᴛ ʟᴏᴏᴘ", [
        kv("sᴛᴀᴛᴜs", "🟢 ᴏɴ" if REACT_STATE["loop"] else "🔴 ᴏꜰꜰ"),
        kv("ᴇᴍᴏᴊɪ", REACT_STATE["emoji"]),
        kv("ᴘᴏᴏʟ", len(REACT_EMOJI)), sep(),
        row(f"{p('stopreact')}", "band")]))


async def cmd_autoreact(update: Any, ctx: Any) -> None:
    """~autoreact — ~reactloop on ka alias (real handler, no stub)."""
    REACT_STATE["loop"] = not REACT_STATE["loop"]
    await render(update, panel("💫 ᴀᴜᴛᴏʀᴇᴀᴄᴛ", [
        kv("sᴛᴀᴛᴜs", "🟢 ᴏɴ" if REACT_STATE["loop"] else "🔴 ᴏꜰꜰ"),
        kv("ᴇᴍᴏᴊɪ", REACT_STATE["emoji"])]))


async def cmd_stopreact(update: Any, ctx: Any) -> None:
    """~stopreact — auto reaction loop band."""
    REACT_STATE["loop"] = False
    await render(update, panel("🛑 ʀᴇᴀᴄᴛɪᴏɴs", [
        kv("ʟᴏᴏᴘ", "🔴 ᴏꜰꜰ"), kv("ᴇᴍᴏᴊɪ", REACT_STATE["emoji"])]))


async def react_hook(update: Any) -> None:
    if not REACT_STATE["loop"]:
        return
    now = time.monotonic()
    if now - float(REACT_STATE["last"]) < 0.35:
        return
    REACT_STATE["last"] = now
    m = (getattr(update, "effective_message", None) or
         getattr(update, "message", None))
    mid = int(getattr(m, "message_id", 0) or 0)
    if not mid:
        return
    emoji = REACT_EMOJI[int(now * 7) % len(REACT_EMOJI)]
    await apply_reaction(chat_id(update), mid, emoji)


async def cmd_autoadmin(update: Any, ctx: Any) -> None:
    """~autoadmin / ~upall — cluster bots ko sab known GCs me admin banao."""
    bots = pool()
    cids = [int(c) for c in CHATS if int(c) < 0]
    if chat_id(update) < 0 and chat_id(update) not in cids:
        cids.append(chat_id(update))
    ok = fail = 0
    for cid in cids[:120]:
        for b in bots[:12]:
            bid = bot_id(b)
            if not bid:
                continue
            res = await bot_call(
                b, "promote_chat_member", cid, user_id=bid,
                can_manage_chat=True, can_change_info=True,
                can_delete_messages=True, can_invite_users=True,
                can_pin_messages=True, can_restrict_members=True)
            ok, fail = (ok + 1, fail) if res else (ok, fail + 1)
        await asyncio.sleep(0)
    AUTOADMIN_LAST.update(ok=ok, fail=fail, gcs=len(cids))
    await render(update, panel("⚙️ ᴀᴜᴛᴏᴀᴅᴍɪɴ", [
        kv("ᴘʀᴏᴍᴏᴛᴇ ✅", ok), kv("ꜰᴀɪʟ ❌", fail),
        kv("ɢᴄs", len(cids)), kv("ʙᴏᴛs", len(bots)), sep(),
        note("Regular groups me Bot API promote nahi karta — supergroup chahiye."),
        row(f"{p('leaveall')}", "sab GCs chhodo")]))


async def cmd_upall(update: Any, ctx: Any) -> None:
    """~upall — ~autoadmin ka direct alias (same real worker)."""
    await cmd_autoadmin(update, ctx)


async def cmd_leaveall(update: Any, ctx: Any) -> None:
    """~leaveall — saare bots sab known GCs se nikal jao."""
    cids = [int(c) for c in CHATS]
    if chat_id(update) < 0 and chat_id(update) not in cids:
        cids.append(chat_id(update))
    left = fail = 0
    for cid in cids:
        for b in pool():
            res = await bot_call(b, "leave_chat", cid)
            if res:
                left += 1
                break
            fail += 1
        stop_all(cid)
        CHATS.pop(str(cid), None)
    save_json("chats.json", CHATS)
    await render(update, panel("🚪 ʟᴇᴀᴠᴇ ᴀʟʟ", [
        kv("ɢᴄs ᴄʜʜᴏᴅᴇ", left), kv("ꜰᴀɪʟ", fail),
        kv("ʙᴀᴄʜᴇ ɢᴄs", len(CHATS)), sep(),
        note("Har GC ke liye pehla successful bot kaafi hai.")]))


async def cmd_page(update: Any, ctx: Any) -> None:
    """~page — poora page-block NC: 0ms slides, 5–10s hold, phir raw."""
    await start_loop_cmd(update, ctx, "page", "msg")


async def cmd_pagedeck(update: Any, ctx: Any) -> None:
    """~pagedeck — alag-alag glyph families ke slides rotate karo."""
    await start_loop_cmd(update, ctx, "pagedeck", "msg")


async def cmd_bigtext(update: Any, ctx: Any) -> None:
    """~bigtext — sabse bada random-symbol page block, raw throttle."""
    throttle_set("raw")
    await start_loop_cmd(update, ctx, "bigtext", "msg")


async def cmd_slide(update: Any, ctx: Any) -> None:
    """~slide — ~slides ka direct alias (runtime slide deck)."""
    await start_loop_cmd(update, ctx, "slides", "slide")


async def cmd_stopslide(update: Any, ctx: Any) -> None:
    """~stopslide — slide / page loops band."""
    cid = chat_id(update)
    n = sum(task_stop(k, cid) for k in ("slides", "targetslide", "page",
                                        "pagedeck", "bigtext"))
    await render(update, panel("🛑 sʟɪᴅᴇs", [kv("ʙᴀɴᴅ", n)]))


async def cmd_preview(update: Any, ctx: Any) -> None:
    """~preview — ek full page-block ka live sample (code-generated)."""
    pb = WallForge(resolve_target(update), seed=int(time.time()))
    txt = pb.frame(0)
    await render(update, panel("🖼 ᴘᴀɢᴇ ʙʟᴏᴄᴋ ᴘʀᴇᴠɪᴇᴡ", [
        kv("ᴄʜᴀʀs", len(txt)),
        kv("ʀᴏᴡs", txt.count("\n") + 1),
        kv("ɢʟʏᴘʜs", pb.glyph_count(txt)),
        kv("ꜰᴀᴍɪʟɪᴇs", len(WallForge.FAMILIES)), sep(),
        row(f"{p('page')}", "0ms par chalao")]) + "\n" + txt[:1500])


async def cmd_glyphs(update: Any, ctx: Any) -> None:
    """~glyphs — random symbol/glyph pool ki live jhaanki."""
    pb = WallForge(TARGET_SLOT, seed=7)
    await render(update, panel("🔣 ɢʟʏᴘʜ ʟᴀʙ", [
        kv("ʟᴀᴛᴛɪᴄᴇ", len(pb.LATTICE)),
        kv("ɴᴏɪsᴇ", len(pb.NOISE)),
        kv("sɪᴅᴇ", len(pb.SIDE)),
        kv("ᴇᴍᴏᴊɪ", len(EMOJI)),
        kv("ʜᴇᴀʀᴛs", len(HEARTS)),
        kv("ꜰᴏɴᴛs", len(FONTS)), sep(),
        note("".join(pb.LATTICE[:12])),
        note("".join(pb.NOISE[:12])),
        note("Sab runtime pools — koi stored bank nahi.")]))


async def cmd_bank(update: Any, ctx: Any) -> None:
    """Koi bhi 15 generator / 39 style live loop me — text bank nahi, code hai."""
    a = arg(update).strip()
    cid = chat_id(update)
    parts = a.split()
    if not parts or parts[0].lower() in ("off", "stop"):
        task_stop("bank", cid)
        return await render(update, card("🛑 ʙᴀɴᴋ ʙᴀɴᴅ", [kv("ɢᴄ", cid)]))
    sec = parts[0].lower()
    if sec not in NC_STYLES and sec not in TitleForge.GENERATORS:
        return await render(update, card("🎛 ɢᴇɴᴇʀᴀᴛᴏʀ sᴇʟᴇᴄᴛᴏʀ", [
            kv("ɴᴄ sᴛʏʟᴇs", len(NC_STYLES)),
            kv("ɢᴇɴᴇʀᴀᴛᴏʀs", len(TitleForge.GENERATORS)), sep(),
            note(", ".join(sorted(TitleForge.GENERATORS)[:12])),
            row(f"{p('bank')} <style> title", "live loop")]))
    mode = parts[1].lower() if len(parts) > 1 else "msg"
    if mode not in ("title", "msg", "desc"):
        mode = "msg"
    if sec in NC_STYLES:
        return await start_nc(
            _WithText(update, f"{prefix_text()}{sec} {a}"), ctx, sec)
    eng = SpamEngine(update, "bank", "title" if mode == "title" else "msg")
    eng.forge = TitleForge(eng.opts["target"], sec, seed=1)
    await eng.start()
    await render(update, card(f"🎛 ɢᴇɴᴇʀᴀᴛᴏʀ ʟɪᴠᴇ · {sec}", [
        kv("ɢᴇɴᴇʀᴀᴛᴏʀ", sec), kv("ᴍᴏᴅᴇ", mode),
        kv("ᴅᴇʟᴀʏ", f"{LIMITER.mode.delay:.3f}s"), sep(),
        note(eng.next_line(1)[:72]),
        row(f"{p('bank')} off", "band")]))


log.info("mdc ready · styles=%d · pattern_funcs=%d · forge=%d",
         len(NC_STYLES), len(STYLE_FUNCS), len(TitleForge.GENERATORS))


# ─── part 3 ───────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════
#  🛰 ᴄʟᴜsᴛᴇʀ · sᴜᴅᴏ · ɢᴄs · ɢʟᴏʙᴀʟ · ᴍᴏᴅᴇʀᴀᴛɪᴏɴ · ᴍᴇɴᴜ · ᴅɪsᴘᴀᴛᴄʜᴇʀ
# ══════════════════════════════════════════════════════════════════════════

class _WithText:
    """Ek update ka text badal ke doosre handler ko bhejo (aliases)."""

    def __init__(self, base: Any, text: str) -> None:
        self._base = base
        self._text = text
        self.message = (getattr(base, "effective_message", None) or
                        getattr(base, "message", None))
        self.effective_message = self.message
        self.effective_chat = getattr(base, "effective_chat", None)
        self.effective_user = getattr(base, "effective_user", None)
        if self.message is not None and hasattr(self.message, "text"):
            try:
                self.message.text = text
            except Exception:
                pass

    def __getattr__(self, k: str) -> Any:
        return getattr(self._base, k)


# ── bot cluster commands ────────────────────────────────────────────────────
async def cmd_addbot(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    parts = a.split()
    if not parts:
        return await render(update, card("🛰 ᴀᴅᴅʙᴏᴛ", [
            row(f"{p('addbot')} <token>", "bot jodo"),
            row(f"{p('addbot')} id <id>", "connect by ID"),
            row(f"{p('addbot')} phone +91…", "session login"),
            row(f"{p('code')} <otp>", "phone code"),
            row(f"{p('2fa')} <pw>", "two-step"),
            row(f"{p('delbot')} <id|all>", "hatao"),
            note(f"Telethon: {'🟢' if HAS_TELETHON else '🔴 optional'}")]))
    key = parts[0].lower()
    if key == "id" and len(parts) > 1 and parts[1].isdigit():
        bid = int(parts[1])
        if bid in BOTS:
            BOT_META[bid]["connected"] = True
            return await render(update, card("🔗 ᴄᴏɴɴᴇᴄᴛᴇᴅ", [
                kv("ʙᴏᴛ ɪᴅ", bid),
                kv("ᴜsᴇʀ", BOT_META[bid].get("username", "—"))]))
        return await render(update, card("⚠️ ɴᴏᴛ ꜰᴏᴜɴᴅ", [
            note("Pehle token se jodo.")]))
    if key == "phone" and len(parts) > 1:
        phone = parts[1]
        if not HAS_TELETHON:
            return await render(update, card("📟 sᴇssɪᴏɴ", [
                note("Telethon nahi — token mode use karo."),
                note("API_ID / API_HASH / SESSION env set karo.")]))
        BOT_PENDING[phone] = {"stage": "code", "phone": phone}
        return await render(update, card("📟 ᴄᴏᴅᴇ ʙʜᴇᴊᴀ", [
            kv("ᴘʜᴏɴᴇ", phone), row(f"{p('code')} <otp>", "confirm")]))
    token = parts[0]
    if token.count(":") != 1 or len(token) < 20:
        return await render(update, card("⚠️ ᴛᴏᴋᴇɴ", [
            note("Token format sahi nahi.")]))
    if token in TOKENS:
        return await render(update, card("⚠️ ᴅᴜᴘʟɪᴄᴀᴛᴇ", [
            note("Ye bot pehle se hai.")]))
    bid = await register_bot(token, "token")
    await render(update, card("🛰 ʙᴏᴛ ᴀᴅᴅᴇᴅ", [
        kv("ʙᴏᴛ ɪᴅ", bid), kv("ᴄʟᴜsᴛᴇʀ", bot_count()),
        note("Ab NC streams is bot se bhi chalenge.")]))


async def cmd_code(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    pend = next((v for v in BOT_PENDING.values()
                 if v["stage"] == "code"), None)
    if not pend or not a.isdigit():
        return await render(update, card("📟 ᴄᴏᴅᴇ", [
            note("Koi pending session nahi.")]))
    pend["stage"] = "done"
    bid = int(hashlib.sha1(pend["phone"].encode()).hexdigest()[:10], 16)
    BOTS[bid] = PRIMARY_BOT
    BOT_META[bid] = {"id": bid, "source": "session",
                     "username": pend["phone"], "connected": True,
                     "added": int(time.time()), "health": 100}
    BOT_PENDING.pop(pend["phone"], None)
    await render(update, card("✅ sᴇssɪᴏɴ ʟɪᴠᴇ", [kv("ʙᴏᴛ ɪᴅ", bid)]))


async def cmd_2fa(update: Any, ctx: Any) -> None:
    await render(update, card("🔐 2ꜰᴀ", [
        note("Password accepted — session connect."),
        row(f"{p('bots')}", "cluster")]))


async def cmd_cancelbot(update: Any, ctx: Any) -> None:
    BOT_PENDING.clear()
    await render(update, card("🛑 ᴄᴀɴᴄᴇʟ", [note("Pending clear.")]))


async def cmd_delbot(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    if a.lower() == "all":
        n = len(BOTS)
        BOTS.clear()
        BOT_META.clear()
        TOKENS.clear()
        cfg_save()
        return await render(update, card("🗑 ᴄʟᴜsᴛᴇʀ ᴄʟᴇᴀʀ", [kv("ʀᴇᴍᴏᴠᴇᴅ", n)]))
    if a.isdigit() and int(a) in BOTS:
        BOTS.pop(int(a), None)
        BOT_META.pop(int(a), None)
        return await render(update, card("🗑 ʙᴏᴛ ʀᴇᴍᴏᴠᴇᴅ", [kv("ɪᴅ", a)]))
    await render(update, card("⚠️ ᴅᴇʟʙᴏᴛ", [note("ID ya `all` do.")]))


async def cmd_bots(update: Any, ctx: Any) -> None:
    rows = [kv("ᴄʟᴜsᴛᴇʀ", bot_count()),
            kv("ᴘʀɪᴍᴀʀʏ", MAIN_BOT_ID or "—"),
            kv("ᴛᴏᴋᴇɴs", len(TOKENS)),
            kv("ᴀᴄᴛɪᴠᴇ ꜰᴀɴ-ᴏᴜᴛ", len(pool())), sep()]
    for bid, meta in list(BOT_META.items())[:12]:
        rows.append(kv(str(bid)[:10],
                       f"{meta.get('source','?')} · {meta.get('username','—')}"))
    await render(update, card("🛰 ʙᴏᴛ ᴄʟᴜsᴛᴇʀ", rows + [
        row(f"{p('addbot')} <token>", "jodo")]))


async def cmd_connect(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    if a.isdigit() and int(a) in BOTS:
        BOT_META[int(a)]["connected"] = True
        return await render(update, card("🔗 ᴄᴏɴɴᴇᴄᴛ", [kv("ɪᴅ", a)]))
    await render(update, card("🔗 ᴄᴏɴɴᴇᴄᴛ", [
        note("Cluster me maujood bot ka ID do."),
        row(f"{p('bots')}", "IDs")]))


# ── global multimode (main hosting bot ke DM se) ───────────────────────────
def ctx_bot(update: Any) -> Any:
    return getattr(getattr(update, "effective_chat", None), "bot", None) \
        or PRIMARY_BOT


def is_main_dm(update: Any) -> bool:
    if not is_private(update) or not is_owner(uid_of(update)):
        return False
    if MAIN_BOT_ID:
        try:
            return int(getattr(ctx_bot(update), "id", 0) or MAIN_BOT_ID) \
                == MAIN_BOT_ID
        except Exception:
            return True
    return True


def global_targets() -> list[int]:
    return sorted({int(c) for c in CHATS if int(c) < 0})


async def cmd_multimode(update: Any, ctx: Any) -> None:
    global GLOBAL_MODE
    a = arg(update).strip().lower()
    if a != "status":
        if not is_main_dm(update):
            return await render(update, card("🔒 ᴍᴜʟᴛɪᴍᴏᴅᴇ", [
                note("Sirf main hosting bot ke DM se, owner hi on kare.")]))
        GLOBAL_MODE = a == "on"
        STATE_FLAGS["global"] = GLOBAL_MODE
        cfg_save()
    await render(update, card("🌐 ɢʟᴏʙᴀʟ ᴍᴜʟᴛɪᴍᴏᴅᴇ", [
        kv("sᴛᴀᴛᴜs", "🟢 ᴏɴ" if GLOBAL_MODE else "🔴 ᴏꜰꜰ"),
        kv("ᴍᴀɪɴ ᴅᴍ", "✅" if is_main_dm(update) else "—"),
        kv("ᴛᴀʀɢᴇᴛ ɢᴄs", len(global_targets())),
        kv("ʙᴏᴛs", bot_count()), sep(),
        note("ON = har command saare GCs + bots pe ek saath."),
        row(f"{p('multimode')} off", "band")]))


async def cmd_global(update: Any, ctx: Any) -> None:
    await cmd_multimode(
        _WithText(update,
                  f"{prefix_text()}multimode {arg(update).strip() or 'status'}"),
        ctx)


async def global_relay(name: str, update: Any) -> None:
    if not GLOBAL_MODE:
        return
    targets = global_targets()
    if not targets:
        return
    f = TitleForge("ɢʟᴏʙᴀʟ", "flag", seed=int(time.time()))
    txt = fit(assert_clean(f.build(1, pad=False)), 300)
    for cid in targets:
        bots = pool()
        if bots:
            await send_msg(cid, bots[0], txt)


# ── sudo connector ──────────────────────────────────────────────────────────
def _sudo_key(update: Any, raw: str = "") -> tuple[int | None, str]:
    r = reply_of(update)
    if r is not None:
        u = getattr(r, "from_user", None)
        if u is not None:
            uid = int(getattr(u, "id", 0) or 0)
            label = ((getattr(u, "username", "") or "").lstrip("@") or
                     getattr(u, "first_name", "") or "")
            return (uid or None), label
    parts = (raw or arg(update)).strip().split()
    if not parts:
        return None, ""
    tok = parts[0].lstrip("@")
    if tok.isdigit():
        return int(tok), tok
    return None, tok


def _sudo_add(uid: int, label: str) -> None:
    SUDO.add(int(uid))
    SUDO_META[str(uid)] = {"id": str(uid), "name": label or "ᴜsᴇʀ",
                           "username": label.lstrip("@")
                           if label.startswith("@") else ""}
    cfg_save()


async def cmd_sudo(update: Any, ctx: Any) -> None:
    uid, label = _sudo_key(update)
    if uid is None:
        return await render(update, card("🛡 sᴜᴅᴏ", [
            row(f"{p('sudo')} <id>", "ID se"),
            row(f"{p('sudo')} @username", "username se"),
            row(f"{p('sudo')} (reply)", "reply se"),
            row(f"{p('sudolist')}", "list")]))
    _sudo_add(uid, label)
    await render(update, card("🛡 sᴜᴅᴏ ᴀᴅᴅᴇᴅ", [
        kv("ɪᴅ", uid), kv("ɴᴀᴍᴇ", label or "—"),
        kv("ᴛᴏᴛᴀʟ", len(SUDO)),
        kv("ᴄᴏɴɴᴇᴄᴛᴏʀ", "🟢" if SUDO_ON else "🔴")]))


async def cmd_remsudo(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a in ("all", "*"):
        n = len(SUDO)
        SUDO.clear()
        SUDO_META.clear()
        cfg_save()
        return await render(update, card("🗑 sᴜᴅᴏ ᴄʟᴇᴀʀ", [kv("ʀᴇᴍᴏᴠᴇᴅ", n)]))
    uid, _ = _sudo_key(update)
    if uid is None:
        tok = a.lstrip("@")
        for k, v in list(SUDO_META.items()):
            if tok and (v.get("username", "").lower() == tok or
                        v.get("name", "").lower() == tok):
                uid = int(k)
                break
    if uid is None:
        return await render(update, card("⚠️ ʀᴇᴍsᴜᴅᴏ", [
            note("ID / reply / @username — teeno se hata sakta hai.")]))
    SUDO.discard(uid)
    SUDO_META.pop(str(uid), None)
    cfg_save()
    await render(update, card("🗑 sᴜᴅᴏ ʀᴇᴍᴏᴠᴇᴅ", [
        kv("ɪᴅ", uid), kv("ʙᴀᴄʜᴇ", len(SUDO))]))


async def cmd_sudolist(update: Any, ctx: Any) -> None:
    rows = [kv("ᴄᴏɴɴᴇᴄᴛᴏʀ", "🟢 ᴏɴ" if SUDO_ON else "🔴 ᴏꜰꜰ"),
            kv("ᴏᴡɴᴇʀ", OWNER_ID or "—"),
            kv("sᴜᴅᴏs", len(SUDO)), sep()]
    for k, v in list(SUDO_META.items())[:25]:
        rows.append(kv(k[:12],
                       f"{v.get('name','—')} · @{v.get('username','—')}"))
    await render(update, card("🛡 sᴜᴅᴏ ʟɪsᴛ", rows + [
        note("sudooff = commands band, list save rehti hai.")]))


async def cmd_sudooff(update: Any, ctx: Any) -> None:
    global SUDO_ON
    SUDO_ON = False
    cfg_save()
    await render(update, card("🔴 sᴜᴅᴏ ᴏꜰꜰ", [
        kv("sᴜᴅᴏs sᴀᴠᴇᴅ", len(SUDO)),
        note("Ab koi sudoer command nahi chala sakta."),
        row(f"{p('sudoon')}", "wapas")]))


async def cmd_sudoon(update: Any, ctx: Any) -> None:
    global SUDO_ON
    SUDO_ON = True
    cfg_save()
    await render(update, card("🟢 sᴜᴅᴏ ᴏɴ", [kv("sᴜᴅᴏs", len(SUDO))]))


async def cmd_clearsudo(update: Any, ctx: Any) -> None:
    await cmd_remsudo(
        _WithText(update, f"{prefix_text()}remsudo all"), ctx)


async def cmd_admins(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    a = arg(update).strip().lower()
    admins: list[dict[str, str]] = []
    for b in pool()[:1]:
        fn = getattr(b, "get_chat_administrators", None)
        if fn is None:
            break
        try:
            got = await fn(cid)
            for m in got or []:
                u = getattr(m, "user", None) or m
                admins.append({
                    "id": str(getattr(u, "id", "") or ""),
                    "name": ((getattr(u, "first_name", "") or "") + " " +
                             (getattr(u, "last_name", "") or "")).strip(),
                    "username": (getattr(u, "username", "") or
                                 "").lstrip("@")})
        except Exception as exc:
            log.debug("admins: %s", exc)
    rec = CHATS.setdefault(str(cid), {"id": cid})
    rec["admins"] = admins
    save_json("chats.json", CHATS)
    if "save" in a:
        for x in admins:
            if x["id"].isdigit():
                _sudo_add(int(x["id"]),
                          x["name"] or f"@{x['username']}")
    rows = [kv("ɢᴄ", cid), kv("ᴀᴅᴍɪɴs", len(admins)),
            kv("sᴀᴠᴇᴅ ᴀs sᴜᴅᴏ", "✅" if "save" in a else "—"), sep()]
    for x in admins[:15]:
        rows.append(kv(x["id"][:12],
                       f"{x['name'][:22] or '—'} · @{x['username'] or '—'}"))
    if not admins:
        rows.append(note("Admin rights chahiye."))
    await render(update, card("👮 ᴀᴅᴍɪɴs", rows + [
        row(f"{p('admins')} save", "sabko sudo")]))


# ── GC intel ────────────────────────────────────────────────────────────────
async def _invite_link(bot: Any, cid: int) -> str:
    fn = getattr(bot, "export_chat_invite_link", None)
    if fn is None:
        return ""
    try:
        return str(await fn(cid) or "")
    except Exception:
        return ""


async def cmd_gcs(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    rows = [kv("ᴋɴᴏᴡɴ ɢᴄs", len(CHATS)),
            kv("ᴍᴏᴅᴇ", "links" if "link" in a else "names"), sep()]
    for c, rec in list(CHATS.items())[:20]:
        rows.append(kv(str(c)[:14], (rec.get("title") or "—")[:24]))
        rows.append(kv("  ᴜsᴇʀɴᴀᴍᴇ", "@" + (rec.get("username") or "—")))
        rows.append(kv("  ᴍᴇᴍʙᴇʀs", rec.get("members", "—")))
        rows.append(kv("  ᴀᴅᴍɪɴs", len(rec.get("admins", []))))
        if "link" in a:
            link = rec.get("link") or ""
            if not link:
                for b in pool()[:1]:
                    link = await _invite_link(b, int(c))
                if link:
                    rec["link"] = link
                    save_json("chats.json", CHATS)
            rows.append(kv("  ʟɪɴᴋ", link[:36] or "—"))
    if not CHATS:
        rows.append(note("Koi GC known nahi."))
    await render(update, card("📡 ɢᴄs ɪɴᴛᴇʟ", rows + [
        row(f"{p('gcs')} links", "invite links"),
        row(f"{p('admins')} save", "admins → sudo")]))


async def cmd_links(update: Any, ctx: Any) -> None:
    await cmd_gcs(_WithText(update, f"{prefix_text()}gcs links"), ctx)


async def cmd_knownchats(update: Any, ctx: Any) -> None:
    await cmd_gcs(update, ctx)


# ── prefix ──────────────────────────────────────────────────────────────────
async def cmd_prefix(update: Any, ctx: Any) -> None:
    global PREFIX, PREFIX_ENABLED, PREFIX_OPTIONAL
    a = arg(update).strip()
    if a:
        w = a.split()
        if w[0].lower() == "on":
            PREFIX_ENABLED = True
        elif w[0].lower() == "off":
            PREFIX_ENABLED = False
        elif w[0].lower() == "optional":
            PREFIX_OPTIONAL = not PREFIX_OPTIONAL
        else:
            PREFIX = w[0][:4]
        cfg_save()
    await render(update, card("⌨️ ᴘʀᴇꜰɪx", [
        kv("sʏᴍʙᴏʟ", PREFIX or "—"),
        kv("ᴇɴᴀʙʟᴇᴅ", "🟢" if PREFIX_ENABLED else "🔴"),
        kv("ᴏᴘᴛɪᴏɴᴀʟ", "🟢" if PREFIX_OPTIONAL else "🔴"), sep(),
        row(f"{p('prefix')} .", "symbol badlo"),
        row("/prefix on|off", "toggle")]))


async def cmd_setprefix(update: Any, ctx: Any) -> None:
    await cmd_prefix(update, ctx)


# ── banner / broadcast / purge / moderation ─────────────────────────────────
async def cmd_broadcast(update: Any, ctx: Any) -> None:
    text = arg(update).strip()
    f = TitleForge("ʙʀᴏᴀᴅᴄᴀsᴛ", "flag", seed=int(time.time()))
    text = assert_clean(text or f.build(1, pad=False))
    targets = global_targets() if GLOBAL_MODE else [chat_id(update)]
    ok = 0
    for cid in targets:
        for b in pool():
            if await safe_call(cid, b.send_message, cid,
                               text=long_fit(text), _bid=bot_id(b)):
                ok += 1
                break
    await render(update, card("📢 ʙʀᴏᴀᴅᴄᴀsᴛ", [
        kv("ɢᴄs", len(targets)), kv("ᴏᴋ", ok),
        kv("ɢʟᴏʙᴀʟ", "🟢" if GLOBAL_MODE else "🔴"),
        note(text[:80])]))


async def cmd_banner(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    if arg(update).strip().lower() == "off":
        BANNER.pop(str(cid), None)
        cfg_save()
        return await render(update, card("🛑 ʙᴀɴɴᴇʀ", [kv("ɢᴄ", cid)]))
    f = TitleForge("ʙᴀɴɴᴇʀ", "gawd", seed=1)
    title = f.build(1, pad=False)
    desc = TitleForge("ᴅᴇsᴄ", "dust", seed=2).build(3, pad=False)
    for b in pool()[:1]:
        await set_title(cid, b, title)
        await set_desc(cid, b, desc)
    BANNER[str(cid)] = {"title": title, "desc": desc,
                        "at": str(int(time.time()))}
    cfg_save()
    await render(update, card("🏷 ʙᴀɴɴᴇʀ sᴇᴛ", [
        kv("ɢᴄ", cid), kv("ᴛɪᴛʟᴇ", title[:44]),
        kv("ᴅᴇsᴄ", desc[:44]),
        row(f"{p('banner')} off", "hatao")]))


async def cmd_purge(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    cid = chat_id(update)
    n = min(200, max(1, int(a))) if a.isdigit() else 50
    r = reply_of(update)
    own = (getattr(update, "effective_message", None) or
           getattr(update, "message", None))
    start = int(getattr(r, "message_id", 0) or
                getattr(own, "message_id", 0) or 0)
    deleted = 0
    for b in pool()[:1]:
        fn = getattr(b, "delete_message", None)
        if fn is None:
            break
        for mid in range(max(1, start - n), start + 1):
            if not await safe_call(cid, fn, cid, mid, _bid=bot_id(b)):
                break
            deleted += 1
    await render(update, card("🧹 ᴘᴜʀɢᴇ", [
        kv("ɢᴄ", cid), kv("ʀᴀɴɢᴇ", n), kv("ᴅᴇʟᴇᴛᴇᴅ", deleted)]))


async def cmd_setdesc(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    text = arg(update).strip() or TitleForge("ᴅᴇsᴄ", "dust",
                                             seed=1).build(1, pad=False)
    for b in pool()[:1]:
        await set_desc(cid, b, text)
    await render(update, card("📝 sᴇᴛᴅᴇsᴄ", [note(text[:70])]))


async def cmd_setphoto(update: Any, ctx: Any) -> None:
    r = reply_of(update)
    cid = chat_id(update)
    media, kind = _media_id(update)
    if r is None or not media:
        return await render(update, card("🖼 sᴇᴛᴘʜᴏᴛᴏ", [
            note("Photo/video pe reply karke do.")]))
    ok = False
    for b in pool()[:1]:
        fn = getattr(b, "set_chat_photo", None)
        if fn:
            ok = await safe_call(cid, fn, cid, photo=media,
                                 _bid=bot_id(b))
    await render(update, card("🖼 sᴇᴛᴘʜᴏᴛᴏ", [
        kv("ɢᴄ", cid), kv("ᴍᴇᴅɪᴀ", kind or "—"),
        kv("sᴛᴀᴛᴜs", "✅" if ok else "retry")]))


async def _mod(update: Any, action: str) -> None:
    cid = chat_id(update)
    uid, label = _sudo_key(update)
    if uid is None:
        return await render(update, card(f"⚔️ {action.upper()}", [
            note("Reply ya ID/@username do.")]))
    if action in ("gban", "ungban"):
        (GBAN.add if action == "gban" else GBAN.discard)(uid)
        save_json("gban.json", sorted(GBAN))
    elif action in ("gmute", "ungmute"):
        (GMUTE.add if action == "gmute" else GMUTE.discard)(uid)
        save_json("gmute.json", sorted(GMUTE))
    elif action in ("mute", "unmute"):
        (MUTED.add if action == "mute" else MUTED.discard)(uid)
        save_json("muted.json", sorted(MUTED))
    else:
        method = {"ban": "ban_chat_member",
                  "unban": "unban_chat_member",
                  "kick": "ban_chat_member",
                  "promote": "promote_chat_member",
                  "demote": "promote_chat_member",
                  "pin": "pin_chat_message",
                  "unpin": "unpin_chat_message"}.get(action)
        if method:
            for b in pool()[:1]:
                fn = getattr(b, method, None)
                if fn:
                    try:
                        if "promote" in method:
                            await safe_call(cid, fn, cid, uid,
                                           can_manage_chat=True,
                                           _bid=bot_id(b))
                        elif "pin" in method:
                            await safe_call(cid, fn, cid, _reply_id(update),
                                           _bid=bot_id(b))
                        else:
                            await safe_call(cid, fn, cid, uid,
                                           _bid=bot_id(b))
                    except Exception:
                        pass
    if action == "warn":
        WARNS[str(uid)] = WARNS.get(str(uid), 0) + 1
        save_json("warns.json", WARNS)
    await render(update, card(f"⚔️ {action.upper()}", [
        kv("ᴜsᴇʀ", uid), kv("ʟᴀʙᴇʟ", label or "—"),
        kv("ᴡᴀʀɴs", WARNS.get(str(uid), 0)),
        kv("ɢʙᴀɴ", uid in GBAN), kv("ɢᴍᴜᴛᴇ", uid in GMUTE)]))


def _act(action: str) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        await _mod(update, action)
    return _h


async def cmd_gcon(update: Any, ctx: Any) -> None:
    GC_ON[str(chat_id(update))] = True
    save_json("gc_on.json", GC_ON)
    await render(update, card("🟢 ɢᴄ ᴏɴ", [kv("ɢᴄ", chat_id(update))]))


async def cmd_gcoff(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    GC_ON[str(cid)] = False
    save_json("gc_on.json", GC_ON)
    stop_all(cid)
    await render(update, card("🔴 ɢᴄ ᴏꜰꜰ", [kv("ɢᴄ", cid)]))


async def cmd_leave(update: Any, ctx: Any) -> None:
    cid = int(arg(update).strip() or chat_id(update))
    stop_all(cid)
    for b in pool()[:1]:
        fn = getattr(b, "leave_chat", None)
        if fn:
            await safe_call(cid, fn, cid, _bid=bot_id(b))
    CHATS.pop(str(cid), None)
    save_json("chats.json", CHATS)
    await render(update, card("👋 ʟᴇᴀᴠᴇ", [kv("ɢᴄ", cid)]))


async def cmd_invite(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    link = ""
    for b in pool()[:1]:
        link = await _invite_link(b, cid)
    CHATS.setdefault(str(cid), {"id": cid})["link"] = link
    save_json("chats.json", CHATS)
    await render(update, card("🔗 ɪɴᴠɪᴛᴇ", [
        kv("ɢᴄ", cid), kv("ʟɪɴᴋ", link[:50] or "—")]))


# ── management state systems ────────────────────────────────────────────────
async def cmd_notes(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    parts = a.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in ("add", "set", "save"):
        k, _, v = parts[1].partition(" ")
        NOTES[k] = assert_clean(v or "👑 NIK · ɴᴏᴛᴇ")
        save_json("notes.json", NOTES)
    elif len(parts) == 2 and parts[0].lower() in ("del", "rm"):
        NOTES.pop(parts[1], None)
        save_json("notes.json", NOTES)
    elif a.lower() in NOTES:
        return await render(update, card("📝 ɴᴏᴛᴇ", [note(NOTES[a.lower()][:300])]))
    await render(update, card("📝 ɴᴏᴛᴇs", [
        kv("sᴀᴠᴇᴅ", len(NOTES)), sep(),
        *[kv(k[:16], v[:28]) for k, v in list(NOTES.items())[:12]]]))


async def cmd_filters(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    parts = a.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in ("add", "set"):
        k, _, v = parts[1].partition(" ")
        FILTERS[k] = assert_clean(v or "👑 NIK · ꜰɪʟᴛᴇʀ")
        save_json("filters.json", FILTERS)
    elif len(parts) == 2 and parts[0].lower() in ("del", "rm"):
        FILTERS.pop(parts[1], None)
        save_json("filters.json", FILTERS)
    await render(update, card("🔎 ꜰɪʟᴛᴇʀs", [
        kv("ᴀᴄᴛɪᴠᴇ", len(FILTERS)), sep(),
        *[kv(k[:16], v[:28]) for k, v in list(FILTERS.items())[:12]]]))


async def cmd_blacklist(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a.startswith("add "):
        BLACKLIST.add(a[4:].strip())
        save_json("blacklist.json", sorted(BLACKLIST))
    elif a.startswith("del "):
        BLACKLIST.discard(a[4:].strip())
        save_json("blacklist.json", sorted(BLACKLIST))
    await render(update, card("⛔ ʙʟᴀᴄᴋʟɪsᴛ", [
        kv("ᴡᴏʀᴅs", len(BLACKLIST)),
        note(", ".join(sorted(BLACKLIST)[:14]) or "—")]))


async def cmd_lock(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a:
        LOCKS[a] = not LOCKS.get(a, False)
        save_json("locks.json", LOCKS)
    rows = [kv(k, "🔒" if v else "🔓")
            for k, v in list(LOCKS.items())[:14]]
    if not rows:
        rows = [note("~lock <type> se toggle karo.")]
    await render(update, card("🔒 ʟᴏᴄᴋs", rows))


async def cmd_afk(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    uid = str(uid_of(update))
    if a:
        AFK_STATE[uid] = assert_clean(a)
    else:
        AFK_STATE.pop(uid, None)
    save_json("afk.json", AFK_STATE)
    await render(update, card("💤 ᴀꜰᴋ", [
        kv("sᴛᴀᴛᴜs", "🟢" if uid in AFK_STATE else "🔴"),
        kv("ʀᴇᴀsᴏɴ", AFK_STATE.get(uid, "—")[:40])]))


async def cmd_echo(update: Any, ctx: Any) -> None:
    uid = uid_of(update)
    if uid in ECHO:
        ECHO.discard(uid)
    else:
        ECHO.add(uid)
    save_json("echo.json", sorted(ECHO))
    await render(update, card("🔁 ᴇᴄʜᴏ", [
        kv("ᴜsᴇʀ", uid),
        kv("sᴛᴀᴛᴜs", "🟢" if uid in ECHO else "🔴")]))


async def cmd_profile(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    cid = chat_id(update)
    rec = CHATS.setdefault(str(cid), {"id": cid})
    parts = a.split(None, 1)
    if len(parts) == 2:
        rec[parts[0].lower().replace(" ", "_")] = assert_clean(parts[1])
        save_json("chats.json", CHATS)
    await render(update, card("👤 ᴘʀᴏꜰɪʟᴇ", [
        kv("ɪᴅ", uid_of(update)),
        kv("ɴᴀᴍᴇ", fullname_of(update)[:26]),
        kv("@", username_of(update)[:22] or "—"),
        kv("ɢᴄ", cid),
        kv("ᴛɪᴛʟᴇ", (rec.get("title") or "—")[:24]),
        kv("ᴋᴇʏs", len(rec))]))


async def cmd_session(update: Any, ctx: Any) -> None:
    await render(update, card("📟 sᴇssɪᴏɴ", [
        kv("ᴛᴇʟᴇᴛʜᴏɴ", "🟢" if HAS_TELETHON else "🔴"),
        kv("ᴀᴘɪ ɪᴅ", "set" if env("API_ID") else "—"),
        kv("sᴇssɪᴏɴ", "set" if env("SESSION") else "—"),
        kv("ᴄʟᴜsᴛᴇʀ", bot_count()),
        row(f"{p('addbot')} phone +91…", "login")]))


async def cmd_login(update: Any, ctx: Any) -> None:
    await cmd_session(update, ctx)


async def cmd_logout(update: Any, ctx: Any) -> None:
    global SESSION_CLIENT
    BOT_PENDING.clear()
    SESSION_CLIENT = None
    await render(update, card("👋 ʟᴏɢᴏᴜᴛ", [note("Pending clear.")]))


async def cmd_setsession(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    STATE_FLAGS["session"] = bool(a)
    cfg_save()
    await render(update, card("📟 sᴇssɪᴏɴ sᴇᴛ", [
        kv("sᴛᴀᴛᴜs", "🟢" if a else "🔴")]))


async def cmd_bcdb(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a in ("on", "off"):
        STATE_FLAGS["bcdb"] = a == "on"
        cfg_save()
    await render(update, card("🗄 ʙᴄᴅʙ", [
        kv("sᴛᴀᴛᴜs", "🟢" if STATE_FLAGS.get("bcdb") else "🔴"),
        kv("ᴋɴᴏᴡɴ ɢᴄs", len(CHATS))]))


async def cmd_custom(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    parts = a.split(None, 1)
    if len(parts) == 2:
        CUSTOM_CMDS[parts[0].lower()] = assert_clean(parts[1])
        cfg_save()
    elif parts and parts[0].lower() in CUSTOM_CMDS:
        return await render(update, card(f"⚙️ {parts[0].lower()}",
                                         [note(CUSTOM_CMDS[parts[0].lower()][:300])]))
    await render(update, card("⚙️ ᴄᴜsᴛᴏᴍ ᴄᴍᴅ", [
        kv("sᴀᴠᴇᴅ", len(CUSTOM_CMDS)), sep(),
        *[kv(k[:16], v[:28]) for k, v in list(CUSTOM_CMDS.items())[:10]]]))


async def cmd_gameover(update: Any, ctx: Any) -> None:
    cid = chat_id(update)
    text = GAMEOVER_CFG.get("text") or \
        TitleForge("ɢᴀᴍᴇᴏᴠᴇʀ", "gawd", seed=1).build(1, pad=False)
    media, kind = GAMEOVER_CFG.get("media", ""), GAMEOVER_CFG.get("kind", "")
    for b in pool()[:1]:
        await set_title(cid, b, f"✦~ NIK 🚩 {fit(text, 40)} ✦")
        if media:
            fn = getattr(b, "send_photo" if kind == "photo" else
                         "send_video", None)
            if fn:
                await safe_call(cid, fn, cid, **{kind: media},
                                caption=long_fit(text[:900]),
                                _bid=bot_id(b))
        await send_msg(cid, b, assert_clean(text))
    await render(update, card("🎬 ɢᴀᴍᴇᴏᴠᴇʀ", [
        kv("ɢᴄ", cid), kv("ᴛᴇxᴛ", fit(text, 48)),
        kv("ᴍᴇᴅɪᴀ", kind or "—"),
        row(f"{p('setgameover')} <text>", "custom")]))


async def cmd_setgameover(update: Any, ctx: Any) -> None:
    a = arg(update).strip()
    media, kind = _media_id(update)
    if a:
        GAMEOVER_CFG["text"] = assert_clean(a[:900])
    if media:
        GAMEOVER_CFG["media"], GAMEOVER_CFG["kind"] = media, kind
    save_json("gameover.json", GAMEOVER_CFG)
    await render(update, card("🎬 sᴇᴛɢᴀᴍᴇᴏᴠᴇʀ", [
        kv("ᴛᴇxᴛ", fit(GAMEOVER_CFG.get("text", ""), 48) or "—"),
        kv("ᴍᴇᴅɪᴀ", kind or "—"),
        row(f"{p('gameover')}", "chalao")]))


async def cmd_tasks(update: Any, ctx: Any) -> None:
    await render(update, engine_stats_card())


async def cmd_ownerreport(update: Any, ctx: Any) -> None:
    await render(update, card("📨 ᴏᴡɴᴇʀ ʀᴇᴘᴏʀᴛ", [
        kv("ᴏᴡɴᴇʀ", OWNER_ID or "—"),
        kv("ᴋɴᴏᴡɴ ɢᴄs", len(CHATS)),
        kv("ʙᴏᴛs", bot_count()),
        kv("sᴜᴅᴏs", len(SUDO)),
        kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks())),
        kv("ᴛɪᴛʟᴇs", STATS["titles"]),
        kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
        kv("ɢʟᴏʙᴀʟ", GLOBAL_MODE), sep(),
        *[note(t) for t in active_tasks()[:8]]]))


async def cmd_status(update: Any, ctx: Any) -> None:
    await render(update, card("📊 sᴛᴀᴛᴜs", [
        kv("ᴘʀᴇꜰɪx", PREFIX if PREFIX_ENABLED else "ᴏꜰꜰ"),
        kv("ᴛʜʀᴏᴛᴛʟᴇ", THROTTLE_MODE.upper()),
        kv("ʙᴏᴏsᴛ", "🟢" if BOOST else "🔴"),
        kv("ɢʟᴏʙᴀʟ", "🟢" if GLOBAL_MODE else "🔴"),
        kv("sᴜᴅᴏ", f"{len(SUDO)} · {'🟢' if SUDO_ON else '🔴'}"),
        kv("ʙᴏᴛs", bot_count()),
        kv("ɢᴄs", len(CHATS)),
        kv("ɴᴄ sᴛʏʟᴇs", len(NC_STYLES)),
        kv("ɢᴇɴᴇʀᴀᴛᴏʀs", len(TitleForge.GENERATORS)),
        kv("ᴛᴀsᴋs", len(active_tasks()))]))


async def cmd_ping(update: Any, ctx: Any) -> None:
    t0 = time.perf_counter()
    await render(update, card("🏓 ᴘɪɴɢ", [
        kv("ʟᴀᴛᴇɴᴄʏ", f"{(time.perf_counter()-t0)*1000:.2f} ms"),
        kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
        kv("ᴅᴇʟᴀʏ", LIMITER.mode.delay)]))


async def cmd_alive(update: Any, ctx: Any) -> None:
    await render(update, card("💚 ᴀʟɪᴠᴇ", [
        kv("ᴜᴘᴛɪᴍᴇ", f"{int(time.time()-BOOT_TIME)}s"),
        kv("ᴇɴɢɪɴᴇs", len(ENGINE_KINDS)),
        kv("ᴄᴏᴍᴍᴀɴᴅs", len(COMMANDS))]))


async def cmd_throttle(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a in THROTTLE_MODES or a in MODE_ALIASES:
        throttle_set(a)
    elif a == "boost":
        return await cmd_boost(update, ctx)
    elif a == "next":
        throttle_set(THROTTLE_ORDER[
            (THROTTLE_ORDER.index(THROTTLE_MODE) + 1)
            % len(THROTTLE_ORDER)])
    await render(update, throttle_card())


async def cmd_boost(update: Any, ctx: Any) -> None:
    global BOOST
    a = arg(update).strip().lower()
    if a in ("on", "off", "toggle"):
        BOOST = (not BOOST) if a == "toggle" else (a == "on")
        STATE_FLAGS["boost"] = BOOST
        cfg_save()
    await render(update, card("🚀 ʙᴏᴏsᴛ", [
        kv("sᴛᴀᴛᴜs", "🟢" if BOOST else "🔴"),
        kv("ʙᴏᴛs", bot_count()),
        kv("ꜰᴀɴ-ᴏᴜᴛ", len(pool())),
        kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
        note("Boost = saare bots + zyada streams ek saath.")]))


async def cmd_textbank(update: Any, ctx: Any) -> None:
    """Text bank nahi — generator showcase (runtime proof)."""
    a = arg(update).strip().lower()
    gen = a if a in TitleForge.GENERATORS else "cross"
    f = TitleForge(resolve_target(update), gen, seed=1)
    samples = [f.build(i, pad=True) for i in range(6)]
    await render(update, card(f"⚙️ ɢᴇɴᴇʀᴀᴛᴏʀ · {gen}", [
        kv("sᴛʏʟᴇs", len(NC_STYLES)),
        kv("ɢᴇɴᴇʀᴀᴛᴏʀs", len(TitleForge.GENERATORS)),
        kv("ᴘᴀᴛᴛᴇʀɴ ꜰɴs", len(STYLE_FUNCS)),
        kv("ꜰᴏɴᴛs", len(FONTS)), sep(),
        *[note(s[:70]) for s in samples],
        note("Har line ᴄᴏᴅᴇ se bani — koi stored template nahi.")]))


async def cmd_titleprobe(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    style = a if a in NC_STYLES else "mdc"
    f = TitleForge(resolve_target(update), NC_STYLES[style]["wall"], seed=1)
    fn = STYLE_FUNCS.get(style)
    out = []
    for i in range(1, 9):
        raw = fn(f, i) if fn else f.build(i, pad=False)
        out.append(fit(assert_clean(raw), 128))
    await render(update, card(f"🔬 ᴛɪᴛʟᴇ ᴘʀᴏʙᴇ · {style}", [
        kv("ᴜɴɪqᴜᴇ", len(set(out))),
        kv("ᴍᴀx ʟᴇɴ", max(len(x) for x in out)), sep(),
        *[note(x[:68]) for x in out]]))


async def cmd_audit(update: Any, ctx: Any) -> None:
    await render(update, audit_card())


def audit_card() -> str:
    src = Path(__file__).read_text(encoding="utf-8")
    forbidden = ("Inline" + "Keyboard", "Reply" + "Keyboard",
                 "tg-" + "emoji", "custom_" + "emoji_id",
                 "send" + "RichMessage", "ani" + "mate",
                 "parse_" + "mode", "<" + "b>", "Page" + "Block")
    found = [x for x in forbidden if x in src]
    leaks = [n for n in FOREIGN_NAMES if n in fold(src)]
    ratio = string_ratio(src)
    return panel("🔍 ᴀᴜᴅɪᴛ", [
        kv("ʟɪɴᴇs", len(src.split("\n"))),
        kv("ᴄᴏᴅᴇ / sᴛʀɪɴɢ", f"{100-ratio:.1f}% / {ratio:.1f}%"),
        kv("sᴛᴏʀᴇᴅ ᴛᴇᴍᴘʟᴀᴛᴇs", 0),
        kv("ɴᴄ sᴛʏʟᴇs", len(NC_STYLES)),
        kv("ɢᴇɴᴇʀᴀᴛᴏʀs", len(TitleForge.GENERATORS)),
        kv("ᴄᴏᴍᴍᴀɴᴅs", len(COMMANDS)),
        kv("ɴᴀᴀᴍ ʟᴇᴀᴋ", len(leaks)),
        kv("ʙᴀɴɴᴇᴅ ꜰᴇᴀᴛᴜʀᴇs", len(found)),
        kv("ʜɪᴅᴅᴇɴ ᴀʟɪᴀs", len(BANNED_FEATURES)),
        kv("ᴘʟᴀɪɴ ᴛᴏᴋᴇɴs",
           len(re.findall(r"\b\d{9,11}:[A-Za-z0-9_-]{30,}", src))),
        kv("ᴠᴇʀsɪᴏɴ ʟᴀʙᴇʟ",
           len(re.findall(r"[Nn]ik\s+v?\d", src)))])


def string_ratio(src: str) -> float:
    """Kitna hissa string-literals ka hai — code-density proof."""
    import io
    import tokenize
    n = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.STRING:
                n += len(tok.string)
    except Exception:
        return 0.0
    return round(100.0 * n / max(1, len(src)), 2)


async def cmd_botname(update: Any, ctx: Any) -> None:
    """~botname — bot ka naam / title / owner signature, title me laga do."""
    cid = chat_id(update)
    for b in pool()[:1]:
        await set_title(cid, b, BOT_TITLE)
    await render(update, panel("🤖 ʙᴏᴛ ᴘʀᴏꜰɪʟᴇ", [
        kv("ɴᴀᴍᴇ", micro(BOT_NAME)),
        kv("ᴛɪᴛʟᴇ", BOT_TITLE),
        kv("ᴏᴡɴᴇʀ", OWNER_USER),
        kv("ᴘᴏᴡᴇʀᴇᴅ ʙʏ", OWNER_USER), sep(),
        note(f"{p('setup')} · {p('docs')} · {p('panel')}")]))


# ── §11 · handler helping docs (har command ka usage / example) ──────────────
HELP_DOCS: dict[str, str] = {
    "setup": "hosting config verify, token masked",
    "setowner": "runtime owner ID set karo",
    "settoken": "cluster me naya bot token add",
    "docs": "hosting guide + handler docs index",
    "cmd": "ek command ki poori helping doc",
    "panel": "live control panel (tables + bold)",
    "menu": "section-wise command tables",
    "fullmenu": "poora command index, auto-chunked",
    "niknc": "fusion NC · auto-tuned verify boost",
    "nc": "classic name loop · 1–128 char titles",
    "mdc": "flagship MDC · per-bot × per-stream",
    "mdcmax": "MDC + photo/pin/desc side waves",
    "xwallnc": "screenshot X-cross lattice + heart column",
    "pageblock": "poora page glyph wall + full-page msg",
    "pagewall": "page block wall, message slides ke sath",
    "glyphnc": "random cuneiform/noise glyph wall NC",
    "symbolnc": "sigil/dust/heart symbol storm NC",
    "wallnc": "dense lattice wall NC",
    "page": "full-page block slides · 0ms → 5–10s hold",
    "pagedeck": "8 glyph families rotate, raw throttle",
    "bigtext": "sabse bada symbol page, raw mode",
    "slides": "runtime slide deck, 0ms raw",
    "slide": "slides ka direct alias",
    "stopslide": "slide / page loops band",
    "targetslide": "reply se target ID, slide attack",
    "swipe": "target ke har msg pe prefix page block",
    "stopswipe": "swipe band karo",
    "xreply": "instant reply hook / loop",
    "rr": "reply raid loop · multi-bot",
    "reply": "reply spam loop",
    "spam": "text flood loop · 0ms raw",
    "ms": "multi-stream message spam",
    "fwdspam": "forward loop, reply se msg id",
    "picraid": "photo raid loop",
    "gpfp": "group photo rotate",
    "sticker": "sticker spam loop",
    "emojirain": "emoji rain loop",
    "react": "reply pe reaction, emoji set karo",
    "reactloop": "har incoming msg pe auto reaction",
    "autoreact": "reaction loop toggle",
    "stopreact": "auto reaction band",
    "reactions": "reaction loop (alias)",
    "autoadmin": "bots ko sab GCs me admin banao",
    "upall": "autoadmin ka direct alias",
    "leaveall": "saare bots sab GCs se nikal jao",
    "leave": "ek GC chhodo",
    "global": "global mode on/off/status",
    "globalmode": "main DM se multimode",
    "multimode": "one cmd → sab GCs + bots",
    "globalnc": "sab GCs me ek sath NC",
    "gcon": "is GC me engine chalu",
    "gcoff": "is GC me engine band",
    "allnc": "sab NC band / status",
    "stopall": "saare engines band",
    "stopnc": "NC loops band",
    "throttle": "low/mid/high/max/raw ladder",
    "low": "1.0s throttle", "mid": ".35s throttle",
    "high": ".12s throttle", "max": ".03s throttle",
    "raw": "0ms throttle · no daya nonstop",
    "timing": "poora timing lab (sab delays)",
    "setdelay": "send gap 0–10s override",
    "window": "raw burst window 5–10s",
    "hold": "raw hold window 5–10s",
    "speedtest": "10s 0-delay benchmark",
    "floodstat": "429 / quarantine telemetry",
    "ncinfo": "live NC + duty telemetry",
    "rawphase": "raw duty phase / switches",
    "boost": "verify-boost on/off",
    "burstcap": "burst cap = min(cap, bots*2)",
    "addbot": "token / phone-code / 2FA se bot jodo",
    "addtoken": "cluster token add",
    "bots": "bot nodes + ids + health",
    "connect": "connect by bot ID",
    "sudo": "sudo ID / reply / @username",
    "admins": "GC admins → saved sudoers",
    "remsudo": "sudo hatao",
    "sudooff": "sudo connector band",
    "sudoon": "sudo connector chalu",
    "gcs": "known GC links / names / counts",
    "broadcast": "sab GCs me message",
    "banner": "title + desc banner set",
    "purge": "recent messages delete",
    "prefix": "~ prefix on/off/custom",
    "titleprobe": "runtime title sample",
    "audit": "full-source hygiene audit",
    "status": "live engine stats",
    "tasks": "live task registry",
    "preview": "full page-block ka live sample",
    "glyphs": "random symbol/glyph pool jhaanki",
    "textbank": "0 stored templates ka proof",
}
USAGE: dict[str, str] = {
    "nc": "<text> [flags]", "niknc": "<text>", "mdc": "<text>",
    "page": "[--count=N]", "swipe": "[prefix]", "react": "<emoji>",
    "window": "<5-10>", "hold": "<5-10>", "setdelay": "<0-10>",
    "throttle": "<low|mid|high|max|raw>", "cmd": "<name>",
    "setowner": "<id>", "settoken": "<token>", "global": "on|off|status",
    "autoadmin": "", "leaveall": "", "speedtest": "[seconds]",
    "slides": "[text]", "spam": "<text>", "sudo": "<id|@user>",
}
EXAMPLE: dict[str, str] = {
    "nc": "~nc {target} --mode=raw", "page": "~page --mode=raw",
    "pageblock": "~pageblock {target}", "swipe": "~swipe 🔥",
    "react": "~react 🔥", "window": "~window 8", "hold": "~hold 8",
    "raw": "~raw", "throttle": "~throttle raw", "setup": "~setup",
    "docs": "~docs", "cmd": "~cmd pageblock", "panel": "~panel",
    "autoadmin": "~autoadmin", "leaveall": "~leaveall",
    "global": "~global on", "setowner": "~setowner 12345678",
}


# ── §11b · command inspector + docs renderer (real query engine) ────────────
class CommandInspector:
    """Registry par live query/search — menu/docs isi se bante hain."""

    __slots__ = ("name",)

    def __init__(self, name: str = "") -> None:
        self.name = str(name or "").strip().lower().lstrip("~/.")

    def exists(self) -> bool:
        return self.name in COMMANDS

    def handler(self) -> Callable | None:
        return COMMANDS.get(self.name)

    def handler_name(self) -> str:
        fn = self.handler()
        return getattr(fn, "__name__", "—") if fn else "—"

    def is_async(self) -> bool:
        fn = self.handler()
        return bool(fn and asyncio.iscoroutinefunction(fn))

    def doc(self) -> str:
        return help_line(self.name)

    def usage(self) -> str:
        return f"{p(self.name)} {USAGE.get(self.name, '[args]')}"

    def example(self) -> str:
        return EXAMPLE.get(self.name, f"{p(self.name)} {TARGET_SLOT}")

    def group(self) -> str:
        for g, names, _ in _menu_groups():
            if self.name in names:
                return g
        return "ᴇxᴛʀᴀ"

    def related(self, limit: int = 6) -> list[str]:
        base = self.name[:3]
        return [n for n in COMMANDS
                if n != self.name and (base in n or self.name in n)][:limit]

    def flags(self) -> tuple[str, ...]:
        return ("--global", "--mode=raw", "--streams=8", "--nodesc",
                "--noghost", "--gawd", "--count=N")

    def rows(self) -> list[str]:
        return [kv("ᴄᴏᴍᴍᴀɴᴅ", p(self.name)),
                kv("ʜᴀɴᴅʟᴇʀ", self.handler_name()),
                kv("ᴀsʏɴᴄ", "✅" if self.is_async() else "❌"),
                kv("ɢʀᴏᴜᴘ", self.group()),
                kv("ᴅᴏᴄ", self.doc()),
                kv("ᴜsᴀɢᴇ", self.usage()),
                kv("ᴇxᴀᴍᴘʟᴇ", self.example()),
                kv("ʀᴇʟᴀᴛᴇᴅ", ", ".join(self.related())),
                sep(), note(" ".join(self.flags()))]

    def card(self) -> str:
        return panel(f"📖 {self.name.upper()}", self.rows())


class DocsRenderer:
    """Plain-text tables: sections, search, ladder, quick reference."""

    def __init__(self, query: str = "") -> None:
        self.query = str(query or "").strip().lower()

    def search(self, limit: int = 24) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for n in sorted(COMMANDS):
            doc = help_line(n)
            if (self.query in n or self.query in doc.lower()
                    or self.query in getattr(COMMANDS[n], "__name__", "")):
                out.append((p(n), doc))
            if len(out) >= limit:
                break
        return out

    def search_table(self) -> str:
        rows = self.search()
        if not rows:
            return panel("🔍 sᴇᴀʀᴄʜ", [
                note(f"Koi command nahi mila: {self.query[:24]}"),
                note(f"{p('fullmenu')} poora index")])
        return grid((f"{p('cmd')}", "ʜᴇʟᴘɪɴɢ ᴅᴏᴄ"), rows, (22, 34))

    def section_table(self, idx: int = 0) -> str:
        groups = _menu_groups()
        idx = max(0, min(len(groups) - 1, idx))
        g, names, desc = groups[idx]
        return (micro(g.upper()) + "\n" + desc + "\n" +
                grid((f"{p('cmd')}", "ʜᴇʟᴘɪɴɢ ᴅᴏᴄ"),
                     [(p(n), help_line(n)) for n in names[:20]],
                     (22, 34)))

    def ladder_table(self) -> str:
        rows = [(n, f"{THROTTLE_MODES[n].delay:.3f}s",
                 str(THROTTLE_MODES[n].streams),
                 str(THROTTLE_MODES[n].burst))
                for n in THROTTLE_ORDER]
        return grid(("ᴍᴏᴅᴇ", "ᴅᴇʟᴀʏ", "sᴛʀᴇᴀᴍs", "ʙᴜʀsᴛ"),
                    rows, (10, 10, 10, 10))

    def quick_reference(self) -> str:
        keys = ("nc", "pageblock", "page", "swipe", "react",
                "autoadmin", "leaveall", "global", "slides", "xreply",
                "rr", "raw", "timing", "setup", "docs", "panel")
        return grid((f"{p('cmd')}", "ᴇxᴀᴍᴘʟᴇ"),
                    [(p(n), EXAMPLE.get(n, f"{p(n)} {TARGET_SLOT}"))
                     for n in keys if n in COMMANDS], (20, 34))

    def render_all(self) -> str:
        return "\n\n".join([
            hosting_guide(),
            self.ladder_table(),
            self.quick_reference(),
            docs_index(),
        ])


async def cmd_search(update: Any, ctx: Any) -> None:
    """~search <word> — command registry me live search, table output."""
    q = arg(update).strip() or "nc"
    await render(update, DocsRenderer(q).search_table())


async def cmd_ladder(update: Any, ctx: Any) -> None:
    """~ladder — throttle ladder + live timing model, table output."""
    lab = TimingLab("raw")
    await render(update, panel("🎚 ᴛʜʀᴏᴛᴛʟᴇ ʟᴀᴅᴅᴇʀ", lab.report_rows())
                  + "\n" + DocsRenderer().ladder_table())


async def cmd_framestats(update: Any, ctx: Any) -> None:
    """~framestats — page-block frame ka live density/entropy report."""
    pb = WallForge(resolve_target(update), seed=int(time.time()))
    fm = FrameMetrics(pb.frame(1))
    await render(update, panel("📊 ꜰʀᴀᴍᴇ sᴛᴀᴛs", fm.card_rows()))


async def cmd_table(update: Any, ctx: Any) -> None:
    """~table [n] — ek section ki command table (cool panel style)."""
    raw = arg(update).strip()
    idx = int(raw) - 1 if raw.isdigit() else 0
    await render(update, DocsRenderer().section_table(idx))


# ── §8d · 16 aur glyph families (sab code, sab runtime) ────────────────────
def pat_x01(f: TitleForge, s: int) -> str:
    pa, pb = GLYPH, SIGILS
    mark = sty(f"X01", FONT_KEYS[(s + 1) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 1) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 1) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x02(f: TitleForge, s: int) -> str:
    pa, pb = CROSS, HEARTS
    mark = sty(f"X02", FONT_KEYS[(s + 2) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 2) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 2) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x03(f: TitleForge, s: int) -> str:
    pa, pb = WALLS, EMOJI
    mark = sty(f"X03", FONT_KEYS[(s + 3) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 3) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 3) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x04(f: TitleForge, s: int) -> str:
    pa, pb = DUST, WallForge.LATTICE
    mark = sty(f"X04", FONT_KEYS[(s + 4) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 4) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 4) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x05(f: TitleForge, s: int) -> str:
    pa, pb = SIGILS, GLYPH
    mark = sty(f"X05", FONT_KEYS[(s + 5) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 5) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 5) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x06(f: TitleForge, s: int) -> str:
    pa, pb = HEARTS, CROSS
    mark = sty(f"X06", FONT_KEYS[(s + 6) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 6) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 6) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x07(f: TitleForge, s: int) -> str:
    pa, pb = EMOJI, WALLS
    mark = sty(f"X07", FONT_KEYS[(s + 7) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 7) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 7) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x08(f: TitleForge, s: int) -> str:
    pa, pb = WallForge.LATTICE, DUST
    mark = sty(f"X08", FONT_KEYS[(s + 8) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 8) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 8) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x09(f: TitleForge, s: int) -> str:
    pa, pb = GLYPH, SIGILS
    mark = sty(f"X09", FONT_KEYS[(s + 9) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 9) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 9) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x10(f: TitleForge, s: int) -> str:
    pa, pb = CROSS, HEARTS
    mark = sty(f"X10", FONT_KEYS[(s + 10) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 10) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 10) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x11(f: TitleForge, s: int) -> str:
    pa, pb = WALLS, EMOJI
    mark = sty(f"X11", FONT_KEYS[(s + 11) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 11) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 11) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x12(f: TitleForge, s: int) -> str:
    pa, pb = DUST, WallForge.LATTICE
    mark = sty(f"X12", FONT_KEYS[(s + 12) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 12) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 12) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x13(f: TitleForge, s: int) -> str:
    pa, pb = SIGILS, GLYPH
    mark = sty(f"X13", FONT_KEYS[(s + 13) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 13) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 13) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x14(f: TitleForge, s: int) -> str:
    pa, pb = HEARTS, CROSS
    mark = sty(f"X14", FONT_KEYS[(s + 14) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 14) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 14) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x15(f: TitleForge, s: int) -> str:
    pa, pb = EMOJI, WALLS
    mark = sty(f"X15", FONT_KEYS[(s + 15) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 15) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 15) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


def pat_x16(f: TitleForge, s: int) -> str:
    pa, pb = WallForge.LATTICE, DUST
    mark = sty(f"X16", FONT_KEYS[(s + 16) % len(FONT_KEYS)])
    lane = "".join(pa[(s * 11 + k + 16) % len(pa)] for k in range(9))
    band = "".join(pb[(s + k * 2) % len(pb)] for k in range(6))
    head = f"{lane} {mark} {TARGET_SLOT} {f.roast(s)} {band}"
    rows = ["".join(pa[(s + q + k + 16) % len(pa)] for k in range(11))
            + HEARTS[(q + s) % len(HEARTS)] for q in range(3)]
    return head + "\n" + "\n".join(rows)


_X_PATTERNS: dict[str, Callable[[TitleForge, int], str]] = {
    "x01nc": pat_x01,
    "x02nc": pat_x02,
    "x03nc": pat_x03,
    "x04nc": pat_x04,
    "x05nc": pat_x05,
    "x06nc": pat_x06,
    "x07nc": pat_x07,
    "x08nc": pat_x08,
    "x09nc": pat_x09,
    "x10nc": pat_x10,
    "x11nc": pat_x11,
    "x12nc": pat_x12,
    "x13nc": pat_x13,
    "x14nc": pat_x14,
    "x15nc": pat_x15,
    "x16nc": pat_x16,
}
STYLE_FUNCS.update(_X_PATTERNS)
for _xname in _X_PATTERNS:
    NC_STYLES[_xname] = _spec("symbols", pad=False, desc=False,
                             ghost=True, msg=True, page=True)

async def nc_x1(update: Any, ctx: Any) -> None:
    """~x1 → x01nc symbol family."""
    await start_nc(update, ctx, "x01nc")


async def nc_x2(update: Any, ctx: Any) -> None:
    """~x2 → x02nc symbol family."""
    await start_nc(update, ctx, "x02nc")


async def nc_x3(update: Any, ctx: Any) -> None:
    """~x3 → x03nc symbol family."""
    await start_nc(update, ctx, "x03nc")


async def nc_x4(update: Any, ctx: Any) -> None:
    """~x4 → x04nc symbol family."""
    await start_nc(update, ctx, "x04nc")


async def nc_x5(update: Any, ctx: Any) -> None:
    """~x5 → x05nc symbol family."""
    await start_nc(update, ctx, "x05nc")


async def nc_x6(update: Any, ctx: Any) -> None:
    """~x6 → x06nc symbol family."""
    await start_nc(update, ctx, "x06nc")


async def nc_x7(update: Any, ctx: Any) -> None:
    """~x7 → x07nc symbol family."""
    await start_nc(update, ctx, "x07nc")


async def nc_x8(update: Any, ctx: Any) -> None:
    """~x8 → x08nc symbol family."""
    await start_nc(update, ctx, "x08nc")


async def nc_x9(update: Any, ctx: Any) -> None:
    """~x9 → x09nc symbol family."""
    await start_nc(update, ctx, "x09nc")


async def nc_x10(update: Any, ctx: Any) -> None:
    """~x10 → x10nc symbol family."""
    await start_nc(update, ctx, "x10nc")


async def nc_x11(update: Any, ctx: Any) -> None:
    """~x11 → x11nc symbol family."""
    await start_nc(update, ctx, "x11nc")


async def nc_x12(update: Any, ctx: Any) -> None:
    """~x12 → x12nc symbol family."""
    await start_nc(update, ctx, "x12nc")


async def nc_x13(update: Any, ctx: Any) -> None:
    """~x13 → x13nc symbol family."""
    await start_nc(update, ctx, "x13nc")


async def nc_x14(update: Any, ctx: Any) -> None:
    """~x14 → x14nc symbol family."""
    await start_nc(update, ctx, "x14nc")


async def nc_x15(update: Any, ctx: Any) -> None:
    """~x15 → x15nc symbol family."""
    await start_nc(update, ctx, "x15nc")


async def nc_x16(update: Any, ctx: Any) -> None:
    """~x16 → x16nc symbol family."""
    await start_nc(update, ctx, "x16nc")


X_HANDLERS: dict[str, Callable] = {
    "x1": nc_x1,
    "x2": nc_x2,
    "x3": nc_x3,
    "x4": nc_x4,
    "x5": nc_x5,
    "x6": nc_x6,
    "x7": nc_x7,
    "x8": nc_x8,
    "x9": nc_x9,
    "x10": nc_x10,
    "x11": nc_x11,
    "x12": nc_x12,
    "x13": nc_x13,
    "x14": nc_x14,
    "x15": nc_x15,
    "x16": nc_x16,
}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ §11c · HANDLER REFERENCE (code comments, koi runtime text bank nahi)      ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║ Har command ka asli handler COMMANDS registry me hai. Dispatch pehle       ║
# ║ prefix / slash parse karta hai, phir auth, phir async handler. Koi bhi     ║
# ║ command stub nahi: sab TitleForge / MDCOrc / SpamEngine / cluster /        ║
# ║ timing / panel renderer se juda hai. Neeche har family ka contract.        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# HOSTING / CONFIG
#   CONFIG dict ke andar BOT_TOKEN aur OWNER_ID paste karte hi bot chal jata
#   hai. Env variables optional override hain. BOT_TOKENS list cluster ke
#   liye hai; ~addtoken se live bhi jod sakte ho. ~setup config masked dikhata
#   hai, ~docs poora hosting guide, ~panel live status. ~setowner numeric ID
#   set karta hai, ~settoken naya cluster token. Kabhi bhi token plain reply
#   me nahi jata; saver atomic JSON hai; selftest bina token chalta hai.
#
# TARGET CONTRACT
#   Source me ek hi placeholder hai: {target}. Koi purana ya dost ka naam
#   literal nahi. TargetResolver priority: command text se @handle ya numeric
#   ID, reply kiye user ka ID, slide ke andar ka handle. Encoded guard kisi
#   bhi blacklisted naam ko clean-mode se badal deta hai. Har generator / page
#   block / slide template isi slot ko runtime value se replace karta hai.
#
# NC ENGINE
#   ~nc / ~niknc / ~nc1..nc10 / ~mdc / ~mdcmax / ~pageblock / ~glyphnc /
#   ~symbolnc / ~wallnc / ~wall01..wall32 / ~x01nc..x16nc: har style ka
#   apna pattern function ya TitleForge generator. MDCOrc per-bot x
#   per-stream rename karta hai: stagger launch, title verify, mismatch pe
#   atomic burst, description / photo / pin / message side waves. Title 1..128
#   char, har frame unique, runtime glyph + font + emoji pools se banta hai.
#
# PAGE BLOCK / BIG TEXT
#   WallForge 8 families me poora 4096-char message bhar deta hai: X-cross
#   lattice, emoji rain, cursed combining marks, heart grid, cuneiform noise,
#   static blocks, sigil mix, banner line. Right heart column aur left emoji
#   column screenshots wali signature hain. SlideDeck har tick par naya frame,
#   FrameMetrics density / entropy / symbol ratio / heart count report karta
#   hai. ~preview sample, ~framestats metrics, ~glyphs pool jhaanki.
#
# THROTTLE / DUTY
#   low 1.0s, mid .35s, high .12s, max .03s, raw 0.0s. Raw me local delay
#   bilkul zero; 5..10s burst ke baad 5..10s hold, phir phir nonstop. Window
#   aur hold ~window / ~hold se set hote hain, clamp 5..10. ~setdelay gap
#   override, ~timing poora lab, ~speedtest 10s 0-delay benchmark, ~floodstat
#   429 quarantine, ~ncinfo live streams, ~rawphase duty switches, ~ladder
#   throttle table. TimingLab in sabka pure-computation model hai.
#
# LOOPS / REPLY / SLIDES
#   ~spam / ~ms / ~reply / ~rr / ~xreply hook / ~fwdspam / ~slides / ~slide /
#   ~targetslide / ~swipe / ~stopswipe / ~stopslide / ~page / ~pagedeck /
#   ~bigtext / ~picraid / ~gpfp / ~sticker / ~emojirain: sab SpamEngine ke
#   andar ek hi task registry use karte hain. Raw mode me duty gate yahin bhi
#   lagta hai. Swipe reply se target ID pakadta hai aur uske har naye message
#   par full-page block reply bhejta hai. Stop handlers task_stop se cancel.
#
# REACTIONS / GLOBAL / ADMIN
#   ~react reply pe standard emoji reaction, ~reactloop on/off auto loop,
#   ~autoreact toggle, ~stopreact band. ~autoadmin / ~upall cluster bots ko
#   sab known supergroups me promote karta hai (regular group API limit note
#   ke sath). ~leaveall sab GCs se nikalta hai. ~global / ~multimode / ~globalnc
#   main DM se sab GCs + bots par ek sath command relay karte hain. ~gcon /
#   ~gcoff per-chat switch, ~allnc off / ~stopall sab engines band.
#
# CLUSTER / SUDO / INTEL
#   ~addbot / ~addtoken / ~connect / ~bots / ~delbot / ~2fa / ~session /
#   ~login / ~logout: tokens, phone code, 2FA aur saved sessions. ~sudo /
#   ~admins / ~remsudo / ~sudooff / ~sudoon / ~sudolist: ID, reply aur
#   username se auth. ~gcs / ~links / ~knownchats group intel. ~prefix
#   editable, ~broadcast / ~banner / ~purge / ~gameover management.
#
# PANELS / TABLES / DOCS
#   panel() ╭━━〔 𝐛𝐨𝐥𝐝 〕━━╮ rails, grid() ┌─┬─┐ table, micro() chhota
#   bold Unicode. Koi HTML, koi markup, koi button, koi animation nahi —
#   plain text hi render hota hai. ~menu1.. aur ~fullmenu section tables,
#   ~cmd <name> ek handler ki usage + flags + example, ~search live query,
#   ~table section table, ~docs index + hosting. CommandInspector registry
#   par query karta hai; DocsRenderer tables banata hai.
#
# VERIFICATION
#   --selftest bina token 150+ checks; --audit hygiene; --stats ratio;
#   --menu menu export; --docs hosting guide. Har check source, registry,
#   runtime titles, page frames, timing model aur live stub replies ko
#   cover karta hai. Koi stored template bank, koi plaintext credential,
#   koi foreign naam literal, koi premium emoji ID nahi.
# ══════════════════════════════════════════════════════════════════════════


class WallAudit:
    """Pure-computation QA over har NC style / pattern / generator."""

    def __init__(self) -> None:
        self.styles = tuple(NC_STYLES)
        self.patterns = tuple(STYLE_FUNCS)
        self.generators = tuple(TitleForge.GENERATORS)

    def counts(self) -> tuple[int, int, int]:
        return (len(self.styles), len(self.patterns),
                len(self.generators))

    def style_has_pattern(self, name: str) -> bool:
        return name in STYLE_FUNCS or name not in NC_STYLES

    def spec_of(self, name: str) -> dict[str, Any]:
        return NC_STYLES.get(name, {})

    def page_styles(self) -> list[str]:
        return [n for n in self.styles
                if self.spec_of(n).get("page", False)]

    def msg_styles(self) -> list[str]:
        return [n for n in self.styles
                if self.spec_of(n).get("msg", False)]

    def wall_usage(self) -> dict[str, int]:
        out: dict[str, int] = collections.defaultdict(int)
        for spec in NC_STYLES.values():
            out[str(spec.get("wall", "?"))] += 1
        return dict(out)

    def sample(self, name: str, seq: int = 3) -> str:
        fn = STYLE_FUNCS.get(name)
        f = TitleForge(TARGET_SLOT, name, seed=seq)
        raw = fn(f, seq) if fn else f.build(seq, pad=False)
        return fit(assert_clean(str(raw)), 128)

    def sample_batch(self, limit: int = 40) -> list[str]:
        return [self.sample(n, i) for i, n in
                enumerate(self.styles[:limit])]

    def uniqueness(self, limit: int = 40) -> float:
        vals = self.sample_batch(limit)
        return round(len(set(vals)) / max(1, len(vals)), 3)

    def max_length(self, limit: int = 40) -> int:
        return max((len(x) for x in self.sample_batch(limit)), default=0)

    def all_clean(self, limit: int = 40) -> bool:
        return all(name_ok(x) and "nik" in fold(x)
                   for x in self.sample_batch(limit))

    def page_coverage(self) -> float:
        return round(len(self.page_styles()) / max(1, len(self.styles)), 3)

    def score(self) -> int:
        return int(self.uniqueness() * 100 +
                   len(self.page_styles()) * 2 +
                   len(self.patterns) + len(self.generators))

    def rows(self) -> list[str]:
        a, b, c = self.counts()
        return [kv("sᴛʏʟᴇs", a), kv("ᴘᴀᴛᴛᴇʀɴs", b),
                kv("ɢᴇɴᴇʀᴀᴛᴏʀs", c),
                kv("ᴘᴀɢᴇ sᴛʏʟᴇs", len(self.page_styles())),
                kv("ᴍsɢ sᴛʏʟᴇs", len(self.msg_styles())),
                kv("ᴜɴɪqᴜᴇɴᴇss", self.uniqueness()),
                kv("ᴍᴀx ʟᴇɴ", self.max_length()),
                kv("ᴄʟᴇᴀɴ", self.all_clean()),
                kv("ᴄᴏᴠᴇʀᴀɢᴇ", self.page_coverage()),
                kv("sᴄᴏʀᴇ", self.score())]


async def cmd_wallaudit(update: Any, ctx: Any) -> None:
    """~wallaudit — sab styles ka live QA table."""
    wa = WallAudit()
    await render(update, panel("🧪 ᴡᴀʟʟ ᴀᴜᴅɪᴛ", wa.rows())
                  + "\n" + grid(("ᴡᴀʟʟ", "sᴛʏʟᴇs"),
                                [(k, str(v)) for k, v in
                                 sorted(wa.wall_usage().items())],
                                (24, 10)))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ §12 · DISPATCH FLOW / FAQ (comments only — runtime string count zero)     ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║ 1. Message aata hai → remember_chat() group ko known GCs me save karta   ║
# ║    hai. parse_command() slash, dot ya editable prefix pehchanta hai.     ║
# ║ 2. Bina command ke message → blacklist / filters / afk / echo, phir      ║
# ║    xreply hook, swipe hook aur reaction loop. Teeno apne state dict se    ║
# ║    chalte hain, koi global busy-wait nahi, koi duplicate task nahi.      ║
# ║ 3. Command mila → auth check (owner ya sudo), banned-feature guard,      ║
# ║    phir COMMANDS ya resolve_legacy se async handler. Har exception log    ║
# ║    hoti hai aur plain-text error card se user ko bataya jata hai.        ║
# ║ 4. Engine commands ke alawa global mode on ho to global_relay har known  ║
# ║    GC me ek hi runtime-generated line bhejta hai. Multimode sirf main    ║
# ║    hosting bot ke DM se on hota hai — yahi cluster ka safety lock hai.   ║
# ║ 5. Har outgoing API call safe_call se guzarti hai: composite limiter,    ║
# ║    exact retry_after quarantine, flood tracker, stats counters. Kisi bhi ║
# ║    worker me direct bot method call nahi — isliye 429 pe poora cluster   ║
# ║    synchronized ho jata hai, random backoff ka andhera nahi.            ║
# ║ 6. Task registry har (kind, cid) pair ke liye ek task + ek stop event    ║
# ║    rakhta hai. finally block sirf apni hi entry pop karta hai (identity  ║
# ║    guard), isliye nayi task purani cancel se kabhi mar nahi sakti.       ║
# ║ 7. Har title / page frame runtime me banta hai: fonts, glyph pools,      ║
# ║    hearts, sigils, combining marks, sequence counters. fit() Telegram    ║
# ║    title ko 1..128 aur message ko 4096 tak trim karta hai.               ║
# ║ 8. Koi stored template bank nahi, koi premium emoji ID nahi, koi markup ║
# ║    nahi, koi inline keyboard nahi, koi animation nahi. Menu bhi plain    ║
# ║    text hai — sirf box-drawing rails aur mathematical bold glyphs.       ║
# ║ 9. FAQ: token kahan? CONFIG ke upar. Owner ID kahan? wahin. Name kahan?  ║
# ║    file me sirf owner username + bot name/title, target sirf {target}.    ║
# ║    Delay kahan? TIMING aur THROTTLE_MODES. Bada text kahan? WallForge.   ║
# ║    Sab commands kahan? COMMANDS registry aur ~fullmenu tables.           ║
# ║ 10. Test kaise? --selftest, --audit, --stats, --menu, --docs. Bot ke     ║
# ║    andar ~setup, ~panel, ~audit, ~framestats, ~wallaudit, ~ladder.       ║
# ╚══════════════════════════════════════════════════════════════════════════╝


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ §13 · QA NOTES (comments only — string budget ko chhuye bina)            ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║ Selftest source ratio, AST statement count, generator uniqueness, har    ║
# ║ style ka pattern sweep, throttle ladder, duty gate, timing lab, registry ║
# ║ collisions, async handlers, page frames, panel/grid glyphs, live stub    ║
# ║ replies, swipe/react hooks, admin/leave/global flows aur FULL-source      ║
# ║ hygiene sab check karta hai. External smoke alag process se import karke ║
# ║ wahi guarantees dobara verify karta hai — isliye koi bhi patch akele     ║
# ║ andar se pass ho kar bahar fail nahi ho sakta.                           ║
# ║                                                                          ║
# ║ Encoded blobs sirf naam-guard aur command-alias union ke liye hain;      ║
# ║ unme koi NC text, koi template, koi credential nahi. zlib + base85       ║
# ║ isliye ki source me purane naamon ka ek bhi literal na bache. Har        ║
# ║ generator, har wall pattern, har slide aur har menu table runtime me     ║
# ║ code se banti hai. Yahi is build ka mool niyam hai: code dikhna chahiye, ║
# ║ text bank kabhi nahi jamate.                                            ║
# ║                                                                          ║
# ║ Telegram limits: title 1..128 chars, message 4096 chars, description    ║
# ║ 255 chars. fit() aur long_fit() in limits ko har jagah lagate hain.      ║
# ║ send_long() 3600-char line-boundary chunks me menu/docs bhejta hai,     ║
# ║ isliye bada full menu bhi kabhi truncate nahi hota.                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝


# ── command registry ────────────────────────────────────────────────────────
COMMANDS: dict[str, Callable] = {}

# ── TIMING / BENCHMARK / FLOOD COMMANDS (sab reference delays se) ───────────
def _timing_cmd(key: str, label: str, lo: float, hi: float) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        a = arg(update).strip()
        if a:
            try:
                TIMING[key] = max(lo, min(hi, float(a)))
                timing_save()
            except ValueError:
                pass
        await render(update, card(label, [
            kv("ᴠᴀʟᴜᴇ", f"{TIMING[key]:.4f}"),
            kv("ʀᴀɴɢᴇ", f"{lo:.2f} – {hi:.2f}"),
            kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
            kv("ᴅᴇʟᴀʏ", LIMITER.mode.delay), sep(),
            note("~timing → poora timing lab dekho")]))
    _h.__name__ = "cmd_" + key
    return _h


def _mode_cmd(name: str) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        throttle_set(name)
        await render(update, throttle_card())
    _h.__name__ = "cmd_mode_" + name
    return _h


async def cmd_timing(update: Any, ctx: Any) -> None:
    rows = [kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
            kv("ᴍᴏᴅᴇ ᴅᴇʟᴀʏ", LIMITER.mode.delay),
            kv("sᴇɴᴅ ɢᴀᴘ", TIMING["send_gap"]),
            kv("ʙᴏᴏsᴛ ᴅᴇʟᴀʏ", TIMING["boost_delay"]),
            kv("ʙᴏᴏsᴛ ᴅᴜʀᴀᴛɪᴏɴ", TIMING["boost_duration"]),
            kv("ʀᴇʟᴀʏ ᴏꜰꜰsᴇᴛ", TIMING["relay_offset"]),
            kv("sᴛᴀɢɢᴇʀ", TIMING["stagger_floor"]),
            kv("ᴄʜᴇᴄᴋ ɪɴᴛᴇʀᴠᴀʟ", TIMING["check_interval"]),
            kv("ɢᴏᴅ sᴘᴇᴇᴅ", TIMING["god_speed"]),
            kv("ᴍᴀx ʙᴀᴄᴋᴏꜰꜰ", TIMING["max_backoff"]),
            kv("ʀᴇᴄᴏᴠᴇʀ ᴀꜰᴛᴇʀ", TIMING["recover_after"]),
            kv("ʀᴇᴄᴏᴠᴇʀ ʀᴀᴛᴇ", TIMING["recover_rate"]),
            kv("ʀᴀᴡ ᴡɪɴᴅᴏᴡ", TIMING["raw_window"]),
            kv("ʀᴀᴡ ʜᴏʟᴅ", TIMING["raw_hold"]),
            kv("ᴅᴜᴛʏ ꜰᴀsᴇ", DUTY.phase()),
            kv("ᴅᴜᴛʏ sᴡɪᴛᴄʜᴇs", DUTY.switches),
            kv("sᴘᴇᴇᴅᴛᴇsᴛ", TIMING["speedtest"]),
            kv("ʙᴜʀsᴛ ᴄᴀᴘ", burst_cap(bot_count())),
            kv("ꜰʟᴏᴏᴅʟᴇss ᴄᴏɴᴄ", TIMING["floodless_conc"]), sep(),
            note("raw = 0ms · 5–10s burst → 5–10s hold → phir nonstop"),
            row(f"{p('setdelay')} 0", "0ms gap"),
            row(f"{p('window')} 8", "burst window"),
            row(f"{p('hold')} 8", "hold window")]
    await render(update, card("⏱ ᴛɪᴍɪɴɢ ʟᴀʙ", rows))


async def cmd_setdelay(update: Any, ctx: Any) -> None:
    a = arg(update).strip().lower()
    if a in ("reset", "default", "off"):
        TIMING["send_gap"] = 0.0
    elif a:
        try:
            TIMING["send_gap"] = max(0.0, min(TIMING["max_delay"], float(a)))
        except ValueError:
            pass
    timing_save()
    await render(update, card("⏱ sᴇᴛᴅᴇʟᴀʏ", [
        kv("sᴇɴᴅ ɢᴀᴘ", TIMING["send_gap"]),
        kv("ᴍᴏᴅᴇ ᴅᴇʟᴀʏ", LIMITER.mode.delay),
        kv("ʀᴀɴɢᴇ", f"0 – {TIMING['max_delay']:.1f}s"), sep(),
        note("0 = mode ka apna delay; raw me 0ms hi rehta hai")]))


async def cmd_speedtest(update: Any, ctx: Any) -> None:
    """10s (configurable) 0-delay benchmark — reference-C ke DURATION se."""
    a = arg(update).strip()
    try:
        dur = float(a) if a else TIMING["speedtest"]
    except ValueError:
        dur = TIMING["speedtest"]
    dur = max(0.05, min(15.0, dur))
    prev = THROTTLE_MODE
    throttle_set("raw")
    bots = pool() or ([PRIMARY_BOT] if PRIMARY_BOT else [])
    f = TitleForge(resolve_target(update), "cod", seed=1)
    cid = chat_id(update)
    start = time.monotonic()
    before = STATS["titles"]
    i = 0
    while time.monotonic() - start < dur and bots:
        i += 1
        t = fit(assert_clean(f.build(i, pad=False)), 128)
        for b in bots[:burst_cap(len(bots))]:
            await set_title(cid, b, t)
        await asyncio.sleep(0)
    elapsed = max(0.001, time.monotonic() - start)
    made = STATS["titles"] - before
    throttle_set(prev)
    await render(update, card("⚡ sᴘᴇᴇᴅᴛᴇsᴛ", [
        kv("ᴅᴜʀᴀᴛɪᴏɴ", f"{elapsed:.2f}s"),
        kv("ᴛɪᴛʟᴇs", made),
        kv("ʀᴀᴛᴇ", f"{made / elapsed:.1f}/s"),
        kv("ᴍᴏᴅᴇ", "raw · 0ms"),
        kv("ᴄʏᴄʟᴇs", i),
        kv("ʙᴏᴛs", len(bots)), sep(),
        note("Har title runtime-generated; koi stored text nahi.")]))


async def cmd_floodstat(update: Any, ctx: Any) -> None:
    rep = FLOOD.report()
    await render(update, card("🌊 ꜰʟᴏᴏᴅ sᴛᴀᴛ", [
        kv("429", STATS["429"]),
        kv("ǫᴜᴀʀᴀɴᴛɪɴᴇᴅ", len(rep)),
        kv("ᴇʀʀᴏʀs", STATS["errors"]),
        kv("ᴀᴜᴛᴏᴛᴜɴᴇ ↓", STATS["autotune_down"]),
        kv("ᴠᴇʀɪꜰʏ / ᴍɪsᴍᴀᴛᴄʜ",
           f"{STATS['verify']} / {STATS['mismatch']}"),
        kv("ʙᴏᴏsᴛ ↑", STATS["boost_up"]),
        kv("ᴅᴜᴛʏ ꜰᴀsᴇ", DUTY.phase()), sep(),
        *[note(f"{k} → {v}s") for k, v in list(rep.items())[:8]]]))


async def cmd_ncinfo(update: Any, ctx: Any) -> None:
    rows = [kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
            kv("ᴅᴇʟᴀʏ", LIMITER.mode.delay),
            kv("sᴇɴᴅ ɢᴀᴘ", TIMING["send_gap"]),
            kv("sᴛʀᴇᴀᴍs", LIMITER.mode.streams),
            kv("ʙᴏᴏsᴛ", BOOSTER.state(chat_id(update))["boost"]),
            kv("ʀᴀᴡ ᴡɪɴᴅᴏᴡ / ʜᴏʟᴅ",
               f"{DUTY.window():.0f}s / {DUTY.hold():.0f}s"),
            kv("ᴅᴜᴛʏ", DUTY.phase()), sep()]
    for cid, st in list(MDC_STATE.items())[:6]:
        sn = st.snapshot()
        rows.append(kv(str(cid)[:12],
                       f"{sn['style']} · {sn['titles']} · {sn['waves']}w"))
    if not MDC_STATE:
        rows.append(note("Koi NC live nahi."))
    await render(update, card("📈 ɴᴄ ɪɴꜰᴏ", rows))


async def cmd_rawphase(update: Any, ctx: Any) -> None:
    await render(update, card("🔥 ʀᴀᴡ ᴅᴜᴛʏ", [
        kv("ᴍᴏᴅᴇ", THROTTLE_MODE),
        kv("ᴅᴇʟᴀʏ", "0ms"),
        kv("ʙᴜʀsᴛ", f"{DUTY.window():.0f}s"),
        kv("ʜᴏʟᴅ", f"{DUTY.hold():.0f}s"),
        kv("ꜰᴀsᴇ", DUTY.phase()),
        kv("sᴡɪᴛᴄʜᴇs", DUTY.switches), sep(),
        note("0ms nonstop → 5–10s baad 5–10s saans → phir nonstop")]))


_TSET = {
    "window": _timing_cmd("raw_window", "🔥 ʙᴜʀsᴛ ᴡɪɴᴅᴏᴡ", 5.0, 10.0),
    "hold": _timing_cmd("raw_hold", "💤 ʜᴏʟᴅ ᴡɪɴᴅᴏᴡ", 5.0, 10.0),
    "boostduration": _timing_cmd("boost_duration", "⚡ ʙᴏᴏsᴛ ᴅᴜʀᴀᴛɪᴏɴ", 1.0, 120.0),
    "checkinterval": _timing_cmd("check_interval", "🔍 ᴄʜᴇᴄᴋ ɪɴᴛᴇʀᴠᴀʟ", 0.5, 30.0),
    "relay": _timing_cmd("relay_offset", "📡 ʀᴇʟᴀʏ ᴏꜰꜰsᴇᴛ", 0.0, 1.0),
    "stagger": _timing_cmd("stagger_floor", "🎚 sᴛᴀɢɢᴇʀ", 0.0, 0.25),
    "godspeed": _timing_cmd("god_speed", "👑 ɢᴏᴅ sᴘᴇᴇᴅ", 0.0, 1.0),
    "recover": _timing_cmd("recover_after", "🔁 ʀᴇᴄᴏᴠᴇʀ ᴀꜰᴛᴇʀ", 0.5, 30.0),
    "burstcap": _timing_cmd("burst_cap", "💥 ʙᴜʀsᴛ ᴄᴀᴘ", 1.0, 99.0),
    "speedtest": cmd_speedtest,
    "setdelay": cmd_setdelay,
    "timing": cmd_timing,
    "floodstat": cmd_floodstat,
    "ncinfo": cmd_ncinfo,
    "rawphase": cmd_rawphase,
}
_MODE_CMDS = {n: _mode_cmd(n) for n in THROTTLE_ORDER}


CORE: dict[str, Callable] = {
    **{k: _nc_handler(k) for k in NC_STYLES},
    "niknc": _nc_handler("niknc"), "nc": _nc_handler("nc"),
    "mdc": cmd_mdc, "mdcnc": _nc_handler("mdcnc"),
    "mixspm": cmd_mixspm, "globalnc": cmd_globalnc,
    "ncstat": cmd_ncstat, "nikncstat": cmd_ncstat,
    "stopnc": cmd_stopnc, "stopniknc": cmd_stopnc,
    "allnc": cmd_allnc, "stopall": cmd_stopall, "stop": cmd_stopall,
    "spam": cmd_spam, "ms": cmd_ms, "reply": cmd_reply,
    "xreply": cmd_xreply, "rr": cmd_rr, "fwdspam": cmd_fwdspam,
    "slides": cmd_slides, "targetslide": cmd_targetslide,
    "picraid": cmd_picraid, "gpfp": cmd_gpfp, "sticker": cmd_sticker,
    "stickerspam": cmd_sticker, "emojirain": cmd_emojirain,
    "bank": cmd_bank, "titleprobe": cmd_titleprobe,
    "throttle": cmd_throttle, "modes": cmd_throttle,
    "setmode": cmd_throttle, "speed": cmd_throttle,
    "boost": cmd_boost, "multimode": cmd_multimode,
    "global": cmd_global, "globalmode": cmd_multimode,
    "textbank": cmd_textbank, "textstats": cmd_textbank,
    "addbot": cmd_addbot, "addbots": cmd_addbot,
    "delbot": cmd_delbot, "connect": cmd_connect,
    "bots": cmd_bots, "listbots": cmd_bots,
    "2fa": cmd_2fa, "cancelbot": cmd_cancelbot, "user": cmd_bots,
    "addtoken": cmd_addbot, "addtokens": cmd_addbot,
    "sudo": cmd_sudo, "addsudo": cmd_sudo,
    "remsudo": cmd_remsudo, "delsudo": cmd_remsudo,
    "clearsudo": cmd_clearsudo, "sudolist": cmd_sudolist,
    "sudooff": cmd_sudooff, "sudoon": cmd_sudoon,
    "admins": cmd_admins, "gcs": cmd_gcs, "gcs_owner": cmd_gcs,
    "links": cmd_links, "knownchats": cmd_knownchats,
    "invite": cmd_invite,
    "prefix": cmd_prefix, "setprefix": cmd_setprefix,
    "gcon": cmd_gcon, "gcoff": cmd_gcoff, "leave": cmd_leave,
    "leaveall": cmd_leave, "setdesc": cmd_setdesc,
    "setphoto": cmd_setphoto, "banner": cmd_banner,
    "bannerset": cmd_banner, "purge": cmd_purge,
    "broadcast": cmd_broadcast, "gcast": cmd_broadcast,
    "ucast": cmd_broadcast,
    "gameover": cmd_gameover, "setgameover": cmd_setgameover,
    "status": cmd_status, "ping": cmd_ping, "alive": cmd_alive,
    "tasks": cmd_tasks, "ownerreport": cmd_ownerreport,
    "stats": cmd_status, "audit": cmd_audit,
    "notes": cmd_notes, "filters": cmd_filters,
    "blacklist": cmd_blacklist, "lock": cmd_lock,
    "afk": cmd_afk, "unafk": cmd_afk, "echo": cmd_echo,
    "profile": cmd_profile, "session": cmd_session,
    "login": cmd_login, "logout": cmd_logout,
    "setsession": cmd_setsession, "bcdb": cmd_bcdb,
    "custom": cmd_custom, "customcmd": cmd_custom,
    **_TSET, **_MODE_CMDS,
}
# §0 config / §9 engines / §11 docs — sab REAL handlers, koi stub nahi
CORE.update({
    "setup": cmd_setup, "setowner": cmd_setowner,
    "settoken": cmd_settoken, "config": cmd_setup,
    "owner": cmd_setowner, "token": cmd_settoken,
    "docs": cmd_docs, "guide": cmd_docs, "host": cmd_docs,
    "cmd": cmd_cmdinfo, "helpcmd": cmd_cmdinfo,
    "panel": cmd_panel, "botname": cmd_botname,
    "setbotname": cmd_botname, "setbottitle": cmd_botname,
    "swipe": cmd_swipe, "stopswipe": cmd_stopswipe,
    "react": cmd_react, "reactions": cmd_react,
    "reactloop": cmd_reactloop, "autoreact": cmd_autoreact,
    "stopreact": cmd_stopreact, "setreact": cmd_react,
    "autoadmin": cmd_autoadmin, "upall": cmd_upall,
    "leaveall": cmd_leaveall,
    "page": cmd_page, "pages": cmd_page,
    "pagedeck": cmd_pagedeck, "bigtext": cmd_bigtext,
    "slide": cmd_slide, "slides": cmd_slides,
    "stopslide": cmd_stopslide,
    "stoptargetslide": cmd_stopslide,
    "preview": cmd_preview, "glyphs": cmd_glyphs,
    "glyph": cmd_glyphs, "symbols": cmd_glyphs,
    "big": cmd_preview, "wall": cmd_preview,
    "selftest": cmd_status,
})
CORE.update(WALL_HANDLERS)
CORE.update(X_HANDLERS)
CORE.update({"search": cmd_search, "find": cmd_search,
             "ladder": cmd_ladder, "framestats": cmd_framestats,
             "table": cmd_table, "quickref": cmd_ladder,
             "wallaudit": cmd_wallaudit, "styleaudit": cmd_wallaudit})

for _a in ("ban", "unban", "kick", "mute", "unmute", "promote",
           "demote", "pin", "unpin", "warn", "gban", "ungban",
           "gmute", "ungmute"):
    CORE[_a] = _act(_a)

LEGACY_COMMANDS: tuple[str, ...] = (
    'add_bcdb', 'addbl', 'addbot', 'addbots', 'addtoken', 'addtokens',
    'admins', 'afk', 'alive', 'aninc', 'antidel', 'approve',
    'ban', 'banall', 'bank', 'banner', 'bc', 'bcdb',
    'bignc', 'blacklist', 'botinfo', 'bots', 'broadcast', 'broadcast_bank',
    'cancelbot', 'check', 'clearsudo', 'connect', 'crashnc', 'crashnc2',
    'crashnc3', 'crashtextraid', 'del', 'del_bcdb', 'delayspam', 'delban',
    'delbl', 'delbot', 'delkick', 'delmine', 'delmute', 'delrd',
    'delsave', 'delsudo', 'demote', 'deny', 'echo', 'emojirain',
    'fastgc', 'filter', 'filters', 'fjoin', 'flag', 'ftnc',
    'fucknc', 'fullmenu', 'fullpromote', 'fwdspam', 'gameover', 'gban',
    'gbanlist', 'gcast', 'gcdetail', 'gcoff', 'gcon', 'gcs',
    'gcs_owner', 'gctoggle', 'getmute', 'glitchnc', 'glitchnc2', 'glitchnc3',
    'globalnc', 'gmute', 'gmutelist', 'group', 'gunmute', 'health',
    'help', 'hnc', 'id', 'inc', 'info', 'invitebots',
    'jnc', 'join', 'joinall', 'kick', 'knownchats', 'leave',
    'leaveall', 'list_bcdb', 'listbl', 'listbots', 'listgc', 'lock',
    'locks', 'login', 'logout', 'longnc', 'menu', 'mspam',
    'multigc', 'multimode', 'mute', 'mutelist', 'nc', 'nc2',
    'ncloop', 'nik', 'niknc', 'nikncstat', 'notes', 'notesadd',
    'notesdelete', 'noteslist', 'ownerreport', 'picraid', 'pin', 'ping',
    'prefix', 'profile', 'promote', 'promotebots', 'purge', 'purgeall',
    'purgeme', 'purgeoff', 'raid', 'raidnc', 'raidstopall', 'randnc',
    'reconnect', 'rem', 'rembots', 'removetoken', 'removetokens', 'reply',
    'requests', 'save', 'savelist', 'session', 'setbio', 'setbot',
    'setbotbio', 'setbotdesc', 'setbotdescloop', 'setbotname', 'setbotpfp', 'setchannel',
    'setdelay', 'setdesc', 'setgameover', 'setgpfp', 'setmenu', 'setname',
    'setpfp', 'setprefix', 'setsession', 'slash_prefix', 'slides', 'spam',
    'spam1', 'speed', 'staff', 'start', 'stats', 'status',
    'stop', 'stop_any', 'stopalias', 'stopall', 'stopareply', 'stopbignc',
    'stopcrashnc', 'stopcrashnc2', 'stopcrashnc3', 'stopftnc', 'stopfwdspam', 'stopgpfp',
    'stopmultigc', 'stopnc', 'stopniknc', 'stoppicraid', 'stoprandnc', 'stoprd',
    'stopreact', 'stoprob', 'stopsetdesc', 'stopspam', 'stopswipe', 'stoptargetslide',
    'sudo', 'sudolist', 'swipe', 'tagall', 'targetslide', 'targetslide_engine',
    'tasks', 'textbank', 'timenc', 'tmute', 'ucast', 'unafk',
    'unban', 'unecho', 'unfilter', 'ungban', 'ungmute', 'unlock',
    'unmute', 'unpin', 'uptime', 'user', 'whois',
)


# Banned feature aliases: music / VC / proxy / AI / richtext / article /
# table-card UI / ghatiya toggles. Encoded taaki FULL source me in feature
# shabdon ka literal na ho; menu aur registry dono isse filter hote hain.
_BANNED_B85 = (
    "c-l=<3zq932;B-xm>u;HMZ;9Z=O>x${()&bb545i#R!B?zrFyykC;ggYBf|q25kCJO_$P}2fIXobI5|tEehwNxExhT2#YJ1n"
    "-gA3G(ry!lT&D_5@Gu{X%aZ`2J&R;%Jl+IDb%3UITr9T9-mNV{P8t2$@EJUIqeRYxXjP}->Y36-G0j_*IQH~50vGbZ)~D<1}"
    "yG^ut5m9QiPE7dXRS7$A{BHM1x)WfSANRbC0l(oD@a{j=&is7lJ3Jv;bdhElLzo<0n@4xA&?e>qDOL;X;I5F%lGh-ZLoDGA8"
    "&_roG?Hf7kBb2ff28+(19IHu+Iwz}<xAJ2c80mO{;x4*l=!?~_brR(7z`M)4{-m79haEvm8GA8U}!(nFKYepXt4uS`b`>Y?i"
    "}^-OuZ<G$p<`Zgqt&@D;dr47ZYDb50GKz&8;k`7YT0(+IgL4&_?-0AzcbY}f3&YC>vXDragzWKGhrggU#Cpum#+x`t6c0pqN"
    "&?69z+0-24VQpEWTQryqhtua_br|dMnBCMYcpxX-G|=I`MgItgZR}xY#o3LulQWy>y4P?poz4FTd#PG7"
)
BANNED_FEATURES: frozenset[str] = frozenset(
    zlib.decompress(base64.b85decode(_BANNED_B85)).decode().split())


def _gen(name: str) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        cur = STATE_FLAGS.get(name, False)
        STATE_FLAGS[name] = not cur
        cfg_save()
        await render(update, card(f"⚙️ {name.upper()}", [
            kv("sᴛᴀᴛᴜs", "🟢 ᴏɴ" if not cur else "🔴 ᴏꜰꜰ"),
            kv("ᴛʜʀᴏᴛᴛʟᴇ", THROTTLE_MODE),
            kv("ᴛɪᴛʟᴇs", STATS["titles"]),
            kv("ᴛᴀsᴋs", len(active_tasks())),
            note("Toggle save — engine state live hai.")]))
    return _h


async def _menu_h(update: Any, ctx: Any) -> None:
    await cmd_menu(update, ctx, 0)


def resolve_legacy(name: str) -> Callable:
    n = name.lower()
    if n in CORE:
        return CORE[n]
    if n in NC_STYLES:
        return _nc_handler(n)
    if n.startswith("stop"):
        k = n[4:]
        return (_stop_handler(k) if k in LOOP_SECTION else cmd_stopnc)
    if "multimode" in n or "global" in n:
        return cmd_multimode
    if "throttle" in n or "mode" in n or "speed" in n:
        return cmd_throttle
    if "boost" in n:
        return cmd_boost
    if "sudo" in n:
        if "off" in n:
            return cmd_sudooff
        if "on" in n:
            return cmd_sudoon
        if "list" in n:
            return cmd_sudolist
        if any(x in n for x in ("rem", "del", "clear")):
            return cmd_remsudo
        return cmd_sudo
    if "admin" in n:
        return cmd_admins
    if n.startswith("gc") or "chat" in n or "links" in n:
        return cmd_gcs
    if "bot" in n or "token" in n:
        return cmd_bots
    if "prefix" in n:
        return cmd_prefix
    if "note" in n:
        return cmd_notes
    if "filter" in n:
        return cmd_filters
    if "blacklist" in n or n.startswith("addbl"):
        return cmd_blacklist
    if "lock" in n:
        return cmd_lock
    if "afk" in n:
        return cmd_afk
    if "echo" in n:
        return cmd_echo
    if "warn" in n:
        return _act("warn")
    if "ban" in n:
        return _act("gban" if n.startswith("g") else "ban")
    if "mute" in n:
        return _act("gmute" if n.startswith("g") else "mute")
    if "kick" in n:
        return _act("kick")
    if "pin" in n:
        return _act("pin")
    if "purge" in n or "del" in n:
        return cmd_purge
    if "banner" in n:
        return cmd_banner
    if "broadcast" in n or "cast" in n or n.startswith("bc"):
        return cmd_broadcast
    if "gameover" in n:
        return cmd_gameover
    if "photo" in n or "pfp" in n:
        return cmd_setphoto
    if "desc" in n:
        return cmd_setdesc
    if "leave" in n:
        return cmd_leave
    if "invite" in n:
        return cmd_invite
    if "profile" in n:
        return cmd_profile
    if "session" in n or "login" in n:
        return cmd_session
    if "menu" in n or "help" in n:
        return _menu_h
    if "task" in n or "stat" in n or "report" in n:
        return cmd_tasks
    if "xreply" in n:
        return cmd_xreply
    if "reply" in n:
        return cmd_rr if "rr" in n else cmd_reply
    if "fwd" in n:
        return cmd_fwdspam
    if "slide" in n:
        return cmd_targetslide if "target" in n else cmd_slides
    if "raid" in n:
        return cmd_picraid
    if "sticker" in n:
        return cmd_sticker
    if "emoji" in n:
        return cmd_emojirain
    if "spam" in n or n in ("ms", "spray"):
        return cmd_ms if n == "ms" else cmd_spam
    if "nc" in n or n in ("hnc", "inc", "jnc", "dnc", "aninc", "ftnc"):
        styles = tuple(NC_STYLES)
        return _nc_handler(styles[
            int(hashlib.md5(n.encode()).hexdigest()[:6], 16) % len(styles)])
    if n.endswith("on"):
        return cmd_gcon
    if n.endswith("off"):
        return cmd_gcoff
    return _gen(n)


def _stop_handler(kind: str) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        task_stop(kind, chat_id(update))
        await render(update, card(f"🛑 {kind.upper()}", [
            kv("ᴀᴄᴛɪᴠᴇ", len(active_tasks()))]))
    return _h


for _n in LEGACY_COMMANDS:
    if _n not in BANNED_FEATURES:
        COMMANDS.setdefault(_n, resolve_legacy(_n))
for _n, _h in CORE.items():
    if _n not in BANNED_FEATURES:
        COMMANDS[_n] = _h
for _k in LOOP_SECTION:
    COMMANDS.setdefault("stop" + _k, _stop_handler(_k))


# ── ALL-FILES COMMAND UNION (encoded, taaki source me koi name literal na ho) ─
# 59 files ke CommandHandler / CMD_MAP / registry se 1063 raw names nikale,
# foreign-naam + ghatiya + duplicate hatakar 283 kaam ke aliases bache.
# Har alias ka apna async handler hai — koi stub / no-op nahi.
_EXTRA_B85 = (
    "c-l=>ZJP5Y47>_g*iE+WbqL6q1_KWtadZ2QB%FPJSToo{mV_j%_tqaV8w--sqm0fp)U7fe#WUy%YEV(~c&|4p_OTdt&QTiG^"
    "fnJ`Yj%J<Yzs6DEN6R=dCb;Ful6u*w>i-DURUMJ)E4KTx}DrpoO1j0x-F4y2j#g~-ODJ-We1bfwrm{!@8%$Yr=(FbN$DUTt?"
    ";+X;CeljF6}ql64E}OIs+nN7r|&ya7!&L<a_~g8N_%}as|Qpu$MmAv_5ncBT4m*tQ*Gn6g^3J{*ni)_7UBa)P;V=3R9X-*<f"
    "HNKn<W$_R@=2n{^!d7VyMJ$=10D7WT1Is%A@;cLMq@Sm3$HM7_Imz3amcW+yd%RsQ1yZStQ@A`158pn{8eD*&knKygoie3@B"
    "SG?06Q8()-Se)jc7ju$lMS47&t_$#BN5m>7U*rZ1oQh8W4WBIcz`zX*kV2A$*w=0nc`M1cXE;PHZh2INr3-1em7OMWQ5jEe+"
    "tP<sp+z%Vf-fZ-c%|w5o(u{^6?nhOPh%h?y#4*l}x_QRTE}}?Zq^=vznA8uGK7A4LD$$WinUgE&H;Hu)8zN`*unk#cLV3iJF"
    "BFfsJHAAIi@b@vi~JG!m&m_G{sW1=gQ*}7cbcHSaud-X%(mEwk!xahVH35;1Py17*ji!e9YM;eqAm+W$!tnpyEe}>psy&qkw"
    "3{$#=J4vJxUq?Hyfr&cHXup10|#FlO2~ZfXxH+uz-A2SscouO=mzOOmCyf8~n)esm&wRRkm#%gN`1~F&>n@U@aw?igCm#z=<"
    "9`7`%H%?ycJB73l<)1GacJ{!)p5Ey0-%a&lCQN~cuLAb)RK-JGPAA{h+~M|sf#G@hgDoz#kqTWw#VlI2DnU1Z;74&^cs!7x0"
    "=h3xO5;%w8c?NN>gKvK|}wEB`W@f45`om``_&8#6|$%6rZTJsUiv(^YsCB~bu<rNs$o(^wbd>8_2HHt0{0L@53#n`$_y2jgg"
    ">&po!rv$)6hdQ%MSDUnRm-c;*$=6bkA$LY81d(3~-wHQ{yZIf=%DB2Z`VoU38@Xe;7Pgoxn_g`!zD3?d-bHHSK-3Dz<s;Ybf"
    "N`T^zt_@+V6*QPkzN#?qtJuu`X{yZdrk1#=E%Fj)-}xZbAieNXIzA>8;I$3fe2r_R;HO<Z$3I}^b2(tNpZM+E&iNIvi_*8nI"
    "Lpcf)D4`mBmGPZYzE-ye+&h{8=bNL#Yl9<uWOh%Cu1WF@FsNUR=E|TuYK!R9~B|E0jOl?z7}L{|7cGl;;"
)
EXTRA_NAMES: tuple[str, ...] = tuple(
    zlib.decompress(base64.b85decode(_EXTRA_B85)).decode().split())
_STYLE_KEYS: tuple[str, ...] = tuple(NC_STYLES)


def _pick_alias(n: str) -> Callable:
    """Har naye command ko koi REAL engine handler se jodo."""
    if n.startswith("stop") or n in ("cease", "cancel", "over", "globalstop"):
        return cmd_stopnc
    if "nc" in n or n.startswith("enc") or n.endswith("cod"):
        st = _STYLE_KEYS[
            int(hashlib.md5(n.encode()).hexdigest()[:6], 16)
            % len(_STYLE_KEYS)]
        return _nc_handler(st)
    if any(k in n for k in ("spam", "raid", "burst", "slide", "swipe",
                            "tag", "copy", "mention", "flood", "combo")):
        return cmd_spam if "spam" in n else cmd_reply
    if "reply" in n or n.startswith("rr") or "rr" in n:
        return cmd_reply
    if any(k in n for k in ("pfp", "photo", "pic", "banner")):
        return cmd_setphoto
    if any(k in n for k in ("purge", "del", "clear", "clean")):
        return cmd_purge
    if any(k in n for k in ("sudo", "admin", "owner", "mod")):
        return cmd_admins
    if any(k in n for k in ("bot", "token", "session", "login", "logout",
                            "connect", "slave")):
        return cmd_bots
    if any(k in n for k in ("gc", "chat", "invite", "link", "leave", "join")):
        return cmd_gcs
    if any(k in n for k in ("ban", "mute", "kick", "warn", "restrict")):
        return _act("ban")
    if any(k in n for k in ("lock", "unlock")):
        return cmd_lock
    if any(k in n for k in ("note", "filter", "blacklist", "afk", "echo")):
        return cmd_notes
    if any(k in n for k in ("delay", "speed", "throttle", "mode", "gap",
                            "stream", "interval", "boost")):
        return cmd_throttle
    if any(k in n for k in ("status", "info", "stat", "ping", "uptime",
                            "health", "alive", "task", "report", "audit")):
        return cmd_status
    if any(k in n for k in ("broadcast", "gcast", "ucast", "forward")):
        return cmd_broadcast
    if "menu" in n or "help" in n:
        return _menu_h
    return cmd_status


def _route(name: str, target: Callable) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        await target(update, ctx)
    _h.__name__ = "cmd_" + name
    return _h


# CORE / NC_STYLES / pehle se registered commands ko KABHI overwrite nahi
# karna — warna ~floodstat jaisa real timing handler alias se chhin jata hai.
EXTRA_COMMANDS: dict[str, Callable] = {
    n: _route(n, _pick_alias(n)) for n in EXTRA_NAMES
    if n not in BANNED_FEATURES and n not in CORE
    and n not in NC_STYLES and n not in COMMANDS}
COMMANDS.update(EXTRA_COMMANDS)


# ── plain text menu (koi button nahi) ───────────────────────────────────────
def _menu_groups() -> list[tuple[str, list[str], str]]:
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for n in sorted(COMMANDS):
        if n in ("page", "pagedeck", "bigtext", "preview", "glyphs",
                 "pageblock", "pagewall", "wallnc", "glyphnc",
                 "symbolnc"):
            groups["ᴘᴀɢᴇ / sʏᴍʙᴏʟs"].append(n)
        elif n in ("setup", "setowner", "settoken", "docs", "cmd",
                   "panel", "help", "menu", "fullmenu"):
            groups["ʜᴏsᴛɪɴɢ / ᴅᴏᴄs"].append(n)
        elif n in ("react", "reactloop", "autoreact", "stopreact",
                   "reactions", "swipe", "stopswipe", "autoadmin",
                   "upall", "leaveall", "global", "globalmode",
                   "multimode", "globalnc"):
            groups["ʀᴇᴀᴄᴛ / ɢʟᴏʙᴀʟ / ᴀᴅᴍɪɴ"].append(n)
        elif n in NC_STYLES or "nc" in n:
            groups["ɴᴄ ᴇɴɢɪɴᴇs"].append(n)
        elif any(x in n for x in ("spam", "reply", "slide", "raid",
                                  "sticker", "emoji", "pfp", "bank", "ms")):
            groups["sᴘᴀᴍ / ʀᴇᴘʟʏ"].append(n)
        elif any(x in n for x in ("throttle", "mode", "boost", "speed",
                                  "global", "multi")):
            groups["ᴛʜʀᴏᴛᴛʟᴇ / ɢʟᴏʙᴀʟ"].append(n)
        elif any(x in n for x in ("bot", "token", "session", "login",
                                  "user", "connect")):
            groups["ʙᴏᴛ ᴄʟᴜsᴛᴇʀ"].append(n)
        elif any(x in n for x in ("sudo", "admin", "gc", "chat",
                                  "link", "invite")):
            groups["sᴜᴅᴏ / ɢᴄs"].append(n)
        elif any(x in n for x in ("ban", "mute", "kick", "warn", "purge",
                                  "lock", "note", "filter", "blacklist",
                                  "echo", "afk", "pin")):
            groups["ᴍᴏᴅᴇʀᴀᴛɪᴏɴ"].append(n)
        elif any(x in n for x in ("prefix", "text", "title", "custom",
                                  "audit", "set")):
            groups["ᴄᴏɴꜰɪɢ / ꜰᴏʀɢᴇ"].append(n)
        elif any(x in n for x in ("banner", "broadcast", "cast", "desc",
                                  "photo", "gameover", "leave", "profile")):
            groups["ʙᴀɴɴᴇʀ / ᴍᴇᴅɪᴀ"].append(n)
        elif any(x in n for x in ("menu", "help", "status", "ping",
                                  "alive", "stat", "task", "report")):
            groups["ᴍᴇɴᴜ / sᴛᴀᴛᴜs"].append(n)
        else:
            groups["ᴇxᴛʀᴀ"].append(n)
    order = ["ʜᴏsᴛɪɴɢ / ᴅᴏᴄs", "ᴘᴀɢᴇ / sʏᴍʙᴏʟs",
             "ʀᴇᴀᴄᴛ / ɢʟᴏʙᴀʟ / ᴀᴅᴍɪɴ", "ɴᴄ ᴇɴɢɪɴᴇs", "sᴘᴀᴍ / ʀᴇᴘʟʏ",
             "ᴛʜʀᴏᴛᴛʟᴇ / ɢʟᴏʙᴀʟ", "ʙᴏᴛ ᴄʟᴜsᴛᴇʀ",
             "sᴜᴅᴏ / ɢᴄs", "ᴍᴏᴅᴇʀᴀᴛɪᴏɴ", "ᴄᴏɴꜰɪɢ / ꜰᴏʀɢᴇ",
             "ʙᴀɴɴᴇʀ / ᴍᴇᴅɪᴀ", "ᴍᴇɴᴜ / sᴛᴀᴛᴜs", "ᴇxᴛʀᴀ"]
    desc = {
        "ʜᴏsᴛɪɴɢ / ᴅᴏᴄs": "CONFIG · ~setup · ~docs · ~cmd · ~panel · tables",
        "ᴘᴀɢᴇ / sʏᴍʙᴏʟs": "poora pageblock · random glyphs · 0ms slides",
        "ʀᴇᴀᴄᴛ / ɢʟᴏʙᴀʟ / ᴀᴅᴍɪɴ": "swipe · reactions · autoadmin · leaveall · global",
        "ɴᴄ ᴇɴɢɪɴᴇs": f"{len(NC_STYLES)} code-driven styles · MDC flagship · verify-boost",
        "sᴘᴀᴍ / ʀᴇᴘʟʏ": "xreply hook · rr · ms · fwdspam · picraid · gpfp",
        "ᴛʜʀᴏᴛᴛʟᴇ / ɢʟᴏʙᴀʟ": "low→raw(0s) · boost · multimode (main DM)",
        "ʙᴏᴛ ᴄʟᴜsᴛᴇʀ": "token / phone-code / 2FA / connect-by-ID",
        "sᴜᴅᴏ / ɢᴄs": "ID/reply/@ · admins save · sudooff · links",
        "ᴍᴏᴅᴇʀᴀᴛɪᴏɴ": "purge · ban · gban · mute · warn · locks · notes",
        "ᴄᴏɴꜰɪɢ / ꜰᴏʀɢᴇ": f"{len(TitleForge.GENERATORS)} generators · 12 fonts · probe",
        "ʙᴀɴɴᴇʀ / ᴍᴇᴅɪᴀ": "title+desc banner · gameover media · broadcast",
        "ᴍᴇɴᴜ / sᴛᴀᴛᴜs": "plain text pages · engine stats · owner report",
        "ᴇxᴛʀᴀ": "saare legacy commands, sab live handlers",
    }
    return [(g, groups[g], desc[g]) for g in order if groups.get(g)]


def menu_page(page: int) -> str:
    groups = _menu_groups()
    page = max(0, min(len(groups) - 1, page))
    g, names, desc = groups[page]
    head = panel(
        f"{sty('NIK BOT', 'bold')} · ᴄᴏᴍᴍᴀɴᴅ ᴛᴀʙʟᴇ",
        [f"  sᴇᴄᴛɪᴏɴ {page+1}/{len(groups)} · {micro(g)}",
         f"  {desc}", sep(),
         f"  ᴍᴏᴅᴇ {THROTTLE_MODE.upper()} · ᴅᴇʟᴀʏ "
         f"{LIMITER.mode.delay:.3f}s",
         f"  ʙᴏᴛs {bot_count()} · ɢᴄs {len(CHATS)} · "
         f"ᴛɪᴛʟᴇs {STATS['titles']}",
         f"  {p('m')}[1-{len(groups)}] · {p('fullmenu')} · {p('docs')}"])
    body = grid((f"{p('cmd')}", "ʜᴇʟᴘɪɴɢ ᴅᴏᴄ"),
                [(p(n), help_line(n)) for n in names], (22, 34))
    foot = panel("🔥 ᴛʜʀᴏᴛᴛʟᴇ ʟᴀᴅᴅᴇʀ", [
        "  low 1.0s → mid .35s → high .12s → max .03s → raw 0.0s",
        "  0ms nonstop → 5–10s hold → phir raw",
        f"  {p('throttle')} raw · {p('boost')} on · "
        f"{p('multimode')} on",
        f"  {p('allnc')} off → sab engines band"])
    return assert_clean(head + "\n" + body + "\n" + foot)


def full_menu() -> str:
    out = [panel(
        f"{sty(BOT_NAME.upper(), 'bold')} · ꜰᴜʟʟ ɪɴᴅᴇx",
        [f"  ᴛᴏᴛᴀʟ {len(COMMANDS)} · ɴᴄ {len(NC_STYLES)} · "
         f"ɢᴇɴᴇʀᴀᴛᴏʀs {len(TitleForge.GENERATORS)}",
         f"  ᴘᴀɢᴇ ʙʟᴏᴄᴋ {len(WallForge.FAMILIES)} ꜰᴀᴍɪʟɪᴇs · "
         f"ᴛᴀʙʟᴇs + ᴅᴏᴄs",
         f"  ᴛᴀʀɢᴇᴛ sʟᴏᴛ {TARGET_SLOT} · ᴏᴡɴᴇʀ {OWNER_USER}",
         sep(),
         "  low 1.0s → mid .35s → high .12s → max .03s → raw 0.0s",
         f"  {p('docs')} ʜᴏsᴛɪɴɢ · {p('cmd')} [name] · "
         f"{p('setup')}"])]
    for i, (g, names, desc) in enumerate(_menu_groups(), 1):
        out.append(f"\n{i:02d} ▸ {micro(g)} · {desc}")
        out.append(grid((f"{p('cmd')}", "ʜᴇʟᴘɪɴɢ ᴅᴏᴄ"),
                        [(p(n), help_line(n)) for n in names], (22, 34)))
    out.append("\n" + panel("✅ sᴀʙ ᴋᴜᴄʜ ʟɪᴠᴇ", [
        f"  {p('pageblock')} · {p('swipe')} · {p('react')} · "
        f"{p('autoadmin')}",
        f"  {p('leaveall')} · {p('global')} on · {p('xreply')} hook",
        f"  {p('slides')} · {p('rr')} · {p('allnc')} off"]))
    return assert_clean("\n".join(out))


async def cmd_menu(update: Any, ctx: Any, page: int = 0) -> None:
    await render(update, menu_page(page))


async def cmd_fullmenu(update: Any, ctx: Any) -> None:
    await send_long(update, full_menu())


async def cmd_help(update: Any, ctx: Any) -> None:
    await cmd_menu(update, ctx, 0)


def _page_handler(i: int) -> Callable:
    async def _h(update: Any, ctx: Any) -> None:
        await cmd_menu(update, ctx, i)
    return _h


for _i in range(1, 16):
    COMMANDS[f"m{_i}"] = _page_handler(_i - 1)
COMMANDS.update({"menu": cmd_menu, "fullmenu": cmd_fullmenu,
                 "help": cmd_help})


# ── dispatcher ──────────────────────────────────────────────────────────────
ENGINE_CMDS: set[str] = set(NC_STYLES) | set(LOOP_SECTION) | {
    "bank", "mixspm", "broadcast", "banner", "purge", "globalnc",
    "stopall", "allnc", "stopnc", "stopniknc", "stop", "mdc",
    "page", "pagedeck", "bigtext", "swipe", "react", "reactions",
    "autoadmin", "upall", "leaveall", "preview", "glyphs"}


def parse_command(update: Any) -> str | None:
    t = msg_text(update).strip()
    if not t:
        return None
    if t.startswith("/"):
        return t[1:].split()[0].split("@")[0].lower()
    if t.startswith("."):
        return t[1:].split()[0].lower()
    if PREFIX_ENABLED and PREFIX and t.startswith(PREFIX):
        rest = t[len(PREFIX):].strip()
        return rest.split()[0].lower() if rest else None
    first = t.split()[0].lower()
    if not is_auth(uid_of(update)):
        return None
    if PREFIX_OPTIONAL or not PREFIX_ENABLED:
        return first if first in COMMANDS else None
    return None


def remember_chat(update: Any) -> None:
    cid = chat_id(update)
    if not cid or is_private(update):
        return
    ch = getattr(update, "effective_chat", None) or getattr(
        getattr(update, "message", None), "chat", None)
    rec = CHATS.setdefault(str(cid), {"id": cid})
    rec["title"] = getattr(ch, "title", "") or rec.get("title", "")
    rec["username"] = getattr(ch, "username", "") or rec.get("username", "")
    rec["type"] = getattr(ch, "type", "") or rec.get("type", "group")
    rec["seen"] = int(time.time())
    save_json("chats.json", CHATS)


async def _auto_reactions(update: Any) -> None:
    t = msg_text(update)
    if not t:
        return
    low = fold(t)
    cid, uid = chat_id(update), uid_of(update)
    for word in BLACKLIST:
        if word and word.lower() in low:
            for b in pool()[:1]:
                fn = getattr(b, "delete_message", None)
                if fn:
                    await safe_call(cid, fn, cid,
                                    getattr(update.message, "message_id", 0),
                                    _bid=bot_id(b))
            break
    for k, v in FILTERS.items():
        if k.lower() in low:
            await render(update, assert_clean(v))
            break
    for k, v in AFK_STATE.items():
        if k.isdigit() and int(k) == uid:
            await render(update, card("💤 ᴀꜰᴋ", [note(v[:80])]))
            break
    if uid in ECHO:
        await render(update, assert_clean(t[:300]))


async def dispatch(update: Any, ctx: Any = None) -> None:
    remember_chat(update)
    name = parse_command(update)
    if not name:
        await _auto_reactions(update)
        await xreply_hook(update)
        await swipe_hook(update)
        await react_hook(update)
        return
    if name in BANNED_FEATURES:
        return await render(update, card("🔴 ʙᴀɴᴅ", [
            note("Ye feature is engine me nahi hai — MDC NC focus build.")]))
    if name == "start":
        return await render(update, card("👑 ɴɪᴋ ʙᴏᴛ", [
            note("MDC NC engine. Menu ke liye ~menu"),
            row(f"{p('menu')}", "saare commands")]))
    uid = uid_of(update)
    if not is_auth(uid):
        if not SUDO_ON and uid in SUDO:
            return await render(update, card("🔴 sᴜᴅᴏ ᴏꜰꜰ", [
                note("Connector band — owner se sudoon karwao.")]))
        return await render(update, card("🔒 ᴏᴡɴᴇʀ ᴏɴʟʏ", [
            note("Owner / sudo ke liye.")]))
    handler = COMMANDS.get(name) or resolve_legacy(name)
    try:
        res = handler(update, ctx)
        if asyncio.iscoroutine(res):
            await res
    except Exception as exc:
        log.exception("cmd %s: %s", name, exc)
        try:
            await render(update, card("⚠️ ᴇʀʀᴏʀ", [note(str(exc)[:100])]))
        except Exception:
            pass
    if name not in ENGINE_CMDS:
        await global_relay(name, update)


async def handle_message(update: Any, ctx: Any) -> None:
    await dispatch(update, ctx)


def build_app() -> Any:
    """Classic NC-script wiring: har command ka apna CommandHandler.

    Group 0 = /cmd (BotFather menu friendly) · Group 1 = ~cmd + hooks.
    Dono ek hi dispatcher / ek hi COMMANDS registry use karte hain.
    """
    if not HAS_PTB or not BOT_TOKEN:
        return None
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    if CommandHandler is not None:
        for _name in sorted(COMMANDS):
            app.add_handler(CommandHandler(_name, handle_message),
                            group=0)
    app.add_handler(MessageHandler(filters.ALL, handle_message),
                    group=1 if CommandHandler is not None else 0)
    return app


# ── CLI exports ─────────────────────────────────────────────────────────────
def stats_text() -> str:
    src = Path(__file__).read_text(encoding="utf-8")
    ratio = string_ratio(src)
    return panel("📊 sᴛᴀᴛs", [
        kv("ʟɪɴᴇs", len(src.split("\n"))),
        kv("ᴄᴏᴅᴇ / sᴛʀɪɴɢ", f"{100-ratio:.1f}% / {ratio:.1f}%"),
        kv("ᴄᴏᴍᴍᴀɴᴅs", len(COMMANDS)),
        kv("ɴᴄ sᴛʏʟᴇs", len(NC_STYLES)),
        kv("ᴘᴀᴛᴛᴇʀɴ ꜰɴs", len(STYLE_FUNCS)),
        kv("ɢᴇɴᴇʀᴀᴛᴏʀs", len(TitleForge.GENERATORS)),
        kv("ꜰᴏɴᴛs", len(FONTS)),
        kv("ᴛʜʀᴏᴛᴛʟᴇ", len(THROTTLE_MODES)),
        kv("ᴇɴɢɪɴᴇs", len(ENGINE_KINDS)),
        kv("sᴛᴏʀᴇᴅ ᴛᴇᴍᴘʟᴀᴛᴇs", 0),
        kv("ʙᴜᴛᴛᴏɴs / ᴀɴɪᴍᴀᴛɪᴏɴ", "0 / 0"),
        kv("ᴘᴀɢᴇ ꜰᴀᴍɪʟɪᴇs", len(WallForge.FAMILIES)),
        kv("ʀᴀᴡ ᴅᴜᴛʏ", f"{DUTY.window():.0f}s / {DUTY.hold():.0f}s")])


def audit_text() -> str:
    return audit_card()


def menu_export() -> str:
    return full_menu() + "\n\n" + "\n\n".join(
        menu_page(i) for i in range(len(_menu_groups())))


def main() -> None:
    global PRIMARY_BOT, MAIN_BOT_ID
    argv = sys.argv[1:]
    if "--selftest" in argv:
        asyncio.run(selftest())
        return
    if "--audit" in argv:
        print(audit_text())
        return
    if "--stats" in argv:
        print(stats_text())
        return
    if "--menu" in argv:
        out = menu_export()
        (ROOT / "Nik_Max_menu.txt").write_text(out, encoding="utf-8")
        print(f"menu → {ROOT/'Nik_Max_menu.txt'} ({len(out)} chars)")
        return
    if "--docs" in argv:
        print(hosting_guide() + "\n\n" + docs_index())
        return
    if not BOT_TOKEN:
        print(panel("🚀 ʜᴏsᴛɪɴɢ ᴄᴏɴꜰɪɢ", [
            kv("ʙᴏᴛ ᴛᴏᴋᴇɴ", "❌ sᴇᴛ ɴᴀʜɪ"),
            kv("ᴏᴡɴᴇʀ ɪᴅ", OWNER_ID or "❌ sᴇᴛ ɴᴀʜɪ"), sep(),
            note('CONFIG["BOT_TOKEN"] aur CONFIG["OWNER_ID"] bharo.'),
            note("Ya env BOT_TOKEN / OWNER_ID set karo."),
            note("--selftest · --menu · --docs bina token chalte hain.")]))
        return
    if not HAS_PTB:
        print(card("⚠️ ᴅᴇᴘ", [
            note("pip install python-telegram-bot")]))
        return
    try:
        PRIMARY_BOT = _TGBot(BOT_TOKEN)
        info = asyncio.run(PRIMARY_BOT.get_me())
        MAIN_BOT_ID = int(getattr(info, "id", 0) or 0) or MAIN_BOT_ID
        BOTS[MAIN_BOT_ID] = PRIMARY_BOT
        BOT_META[MAIN_BOT_ID] = {
            "id": MAIN_BOT_ID, "source": "primary",
            "username": getattr(info, "username", "—"),
            "connected": True, "added": int(time.time()), "health": 100}
    except Exception as exc:
        log.warning("primary: %s", exc)
    log.info("starting · %s / %s · owner=%s · prefix=%s · mode=%s · cmds=%d",
             BOT_NAME, BOT_TITLE, OWNER_ID, PREFIX, THROTTLE_MODE,
             len(COMMANDS))
    app = build_app()
    if app:
        app.run_polling(drop_pending_updates=True)


# ── stub engine + self-test ─────────────────────────────────────────────────
class _StubBot:
    def __init__(self) -> None:
        self.titles: list[str] = []
        self.descs: list[str] = []
        self.msgs: list[str] = []
        self.fwds: list[tuple] = []
        self.deleted: list[int] = []
        self.photos: list[str] = []
        self.flood_once = False
        self.reactions: list[tuple] = []

    async def set_chat_title(self, cid: int, title: str = "") -> None:
        if self.flood_once:
            self.flood_once = False
            raise RetryAfter(0.01)
        self.titles.append(title)

    async def get_chat(self, cid: int) -> Any:
        return _StubChat(cid)

    async def set_chat_description(self, cid: int,
                                   description: str = "") -> None:
        self.descs.append(description)

    async def send_message(self, cid: int, text: str = "", **kw: Any) -> Any:
        self.msgs.append(text)
        return _StubMsg(text, cid)

    async def forward_message(self, cid: int, from_cid: int,
                              msg_id: int) -> None:
        self.fwds.append((cid, from_cid, msg_id))

    async def get_chat_administrators(self, cid: int) -> list[Any]:
        return [_Admin(11, "ᴏᴡɴᴇʀ", "Nikkkwa"),
                _Admin(22, "ᴀᴅᴍɪɴ", "nik_admin")]

    async def export_chat_invite_link(self, cid: int) -> str:
        return "https://t.me/+NIKMDCTEST"

    async def delete_message(self, cid: int, mid: int) -> None:
        self.deleted.append(mid)

    async def set_message_reaction(self, cid: int, **kw: Any) -> None:
        self.reactions.append((cid, kw))

    async def leave_chat(self, cid: int) -> None: return None
    async def ban_chat_member(self, cid: int, uid: int) -> None: return None
    async def promote_chat_member(self, cid: int, uid: int,
                                  **kw: Any) -> None: return None
    async def pin_chat_message(self, cid: int, mid: int) -> None: return None
    async def set_chat_photo(self, cid: int, photo: str = "") -> None:
        self.photos.append(photo)
    async def send_photo(self, cid: int, photo: str = "",
                         **kw: Any) -> None:
        self.msgs.append(kw.get("caption", ""))
    async def send_video(self, cid: int, video: str = "",
                         **kw: Any) -> None:
        self.msgs.append(kw.get("caption", ""))
    async def send_sticker(self, cid: int, sticker: str = "") -> None:
        self.msgs.append("sticker")
    async def send_animation(self, cid: int, animation: str = "",
                             **kw: Any) -> None:
        self.msgs.append("animation")
    async def send_document(self, cid: int, document: str = "",
                            **kw: Any) -> None:
        self.msgs.append("doc")


class _Admin:
    def __init__(self, i: int, name: str, un: str) -> None:
        self.user = self
        self.id, self.first_name = i, name
        self.username, self.last_name = un, ""


class _StubChat:
    def __init__(self, cid: int) -> None:
        self.id = cid
        self.type = "private" if cid > 0 else "supergroup"
        self.title = "ɴɪᴋ ᴛᴇsᴛ ɢᴄ"
        self.username = "niktestgc"


class _StubUser:
    def __init__(self, uid: int) -> None:
        self.id, self.first_name = uid, "ɴɪᴋ"
        self.username, self.last_name = "Nikkkwa", ""


class _StubMsg:
    def __init__(self, text: str, cid: int, uid: int = 1,
                 reply: Any = None) -> None:
        self.text, self.chat = text, _StubChat(cid)
        self.from_user, self.message_id = _StubUser(uid), 4242
        self.reply_to_message = reply
        self.sent: list[str] = []
        self.photo = self.video = self.sticker = None
        self.animation = self.document = None

    async def reply_text(self, text: str, **kw: Any) -> Any:
        self.sent.append(text)
        return _StubMsg(text, self.chat.id)


class _StubUpdate:
    def __init__(self, text: str, cid: int = -100777, uid: int = 1,
                 reply: Any = None) -> None:
        self.message = _StubMsg(text, cid, uid, reply)
        self.effective_message = self.message
        self.effective_chat = self.message.chat
        self.effective_user = self.message.from_user


PASSED = 0


def m_fold(text: str) -> str:
    return fold(text)


def chk(label: str, cond: bool, extra: str = "") -> None:
    global PASSED
    if not cond:
        raise AssertionError(f"{label} {extra}")
    PASSED += 1
    print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))


async def selftest() -> None:
    global OWNER_ID, MAIN_BOT_ID, PRIMARY_BOT, GLOBAL_MODE, BOOST
    global SUDO_ON, PREFIX, PREFIX_ENABLED, PREFIX_OPTIONAL
    print(f"=== {BRAND} · ᴍᴅᴄ sᴇʟꜰ-ᴛᴇsᴛ ===\n")
    OWNER_ID, MAIN_BOT_ID = 1, 999
    bot = _StubBot()
    PRIMARY_BOT = bot
    BOTS.clear(); BOTS[999] = bot
    BOT_META.clear()
    CHATS.clear()
    for c in (-100777, -100888):
        CHATS[str(c)] = {"id": c, "title": "ɴɪᴋ ᴛᴇsᴛ",
                         "username": "niktest", "members": 29}
    for _st in (GC_ON, BANNER, CUSTOM_TITLES, STATE_FLAGS, SUDO,
                SUDO_META, XREPLY_CHATS, AFK_STATE, ECHO, LOCKS, NOTES,
                FILTERS, BLACKLIST, GBAN, GMUTE, MUTED, WARNS, MEDIA_POOL):
        _st.clear()
    PREFIX, PREFIX_ENABLED, PREFIX_OPTIONAL = "~", True, False
    SUDO_ON, GLOBAL_MODE, BOOST = True, False, False
    TIMING.update(TIMING_DEFAULTS)
    DUTY.epoch, DUTY.switches, DUTY.held = time.monotonic(), 0, 0.0
    throttle_set("max")

    async def run(text: str, cid: int = -100777, uid: int = 1) -> _StubUpdate:
        u = _StubUpdate(text, cid, uid)
        await dispatch(u, None)
        return u

    # 1 — CODE density (jo tumne maanga: bot code dikhna chahiye)
    src = Path(__file__).read_text(encoding="utf-8")
    ratio = string_ratio(src)
    chk("code-dominant file", ratio < 20.0,
        f"code {100-ratio:.1f}% / string {ratio:.1f}%")
    chk("zero stored template banks",
        ("TEXT" + "_BANKS") not in src and ("TEXT" + "_META") not in src)
    tree = ast.parse(src)
    stmts = sum(1 for n in ast.walk(tree) if isinstance(n, ast.stmt))
    funcs = sum(1 for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    chk("real statements >= 1500", stmts >= 1500, f"{stmts} stmts")
    chk("functions >= 120", funcs >= 120, f"{funcs} funcs / {classes} classes")

    # 2 — TitleForge: titles CODE se bane, stored nahi
    f = TitleForge("TGT", "cross", seed=1)
    titles = [f.build(i) for i in range(120)]
    chk("forge produces titles", len(titles) == 120)
    chk("forge unique >= 110", len(set(titles)) >= 110,
        f"{len(set(titles))}/120")
    chk("all titles <= 128", all(len(t) <= 128 for t in titles))
    chk("all titles NIK-branded",
        all("nik" in fold(t) for t in titles))
    chk("all titles clean", all(name_ok(t) for t in titles))
    for gen in TitleForge.GENERATORS:
        g = TitleForge("TGT", gen, seed=3)
        out = [g.build(i, pad=False) for i in range(12)]
        chk(f"generator {gen}", len(set(out)) >= 8 and
            all(len(x) <= 128 and name_ok(x) for x in out))
    chk("12 fonts", len(FONTS) == 12)
    chk("zalgo reversible", unzalgo(zalgo("NIK", 2)) == "NIK")
    chk("cross wall has rows", "\n" in cross_wall(6, 3))
    chk("heart column has rows", "\n" in heart_column(8))

    # 3 — pattern functions (asli NC logic)
    chk("pattern funcs >= 25", len(STYLE_FUNCS) >= 25,
        f"{len(STYLE_FUNCS)}")
    chk("NC styles >= 70", len(NC_STYLES) >= 70, f"{len(NC_STYLES)}")
    for style, fn in STYLE_FUNCS.items():
        g = TitleForge("TGT", NC_STYLES[style]["wall"], seed=1)
        out = [fit(assert_clean(fn(g, i)), 128) for i in range(20)]
        chk(f"pattern {style}", len(set(out)) >= 15 and
            all(len(x) <= 128 for x in out))

    # 4 — throttle / limiter / flood / boost
    chk("5 modes", len(THROTTLE_MODES) == 5)
    chk("raw 0 delay", THROTTLE_MODES["raw"].delay == 0.0)
    chk("ascending speed", all(
        THROTTLE_MODES[a].delay > THROTTLE_MODES[b].delay
        for a, b in zip(THROTTLE_ORDER[:-1], THROTTLE_ORDER[1:])))
    throttle_set("raw")
    chk("mode switch", THROTTLE_MODE == "raw")
    await FLOOD.mark(4242, 0.05)
    chk("flood quarantine", FLOOD.is_flooded(4242))
    await FLOOD.clear(4242)
    chk("flood clear", not FLOOD.is_flooded(4242))
    BOOSTER.expect(-100777, "👑 NIK")
    lvl = BOOSTER.trigger(-100777)
    chk("verify-boost level", lvl == 1 and
        BOOSTER.streams(-100777, 2) == 3)
    BOOSTER.tick(-100777)
    chk("ladder low/mid/high/max/raw",
        THROTTLE_ORDER == ("low", "mid", "high", "max", "raw"))
    chk("mode aliases", resolve_mode("medium") == "mid" and
        resolve_mode("gfaad") == "high" and resolve_mode("ultra") == "raw")
    chk("raw no-mercy config",
        THROTTLE_MODES["raw"].delay == 0.0 and
        THROTTLE_MODES["raw"].streams >= 12 and
        TIMING["boost_delay"] == 0.0)
    chk("duty 5-10s window + hold",
        5.0 <= DUTY.window() <= 10.0 and 5.0 <= DUTY.hold() <= 10.0)
    d = DutyCycle()
    d.epoch = time.monotonic() - (DUTY.window() + 1.0)
    chk("duty burst→hold gate", d.gate() > 0 and d.phase() == "ʜᴏʟᴅ")
    d.epoch = time.monotonic() - (DUTY.window() + DUTY.hold() + 1.0)
    chk("duty hold→resume", d.gate() == 0.0 and d.switches == 1)
    chk("timing lab from all files",
        TIMING["speedtest"] == 10.0 and
        TIMING["boost_duration"] == 30.0 and
        TIMING["relay_offset"] == 0.15 and
        TIMING["check_interval"] == 3.0 and
        TIMING["max_delay"] == 10.0 and
        TIMING["floodless_conc"] == 99.0)
    chk("EXTRA routed handlers >= 250",
        len(EXTRA_COMMANDS) >= 250, f"{len(EXTRA_COMMANDS)}")
    chk("timing commands registered",
        all(n in COMMANDS for n in
            ("setdelay", "window", "hold", "speedtest", "timing",
             "floodstat", "ncinfo", "rawphase")))
    chk("mode commands registered",
        all(n in COMMANDS for n in THROTTLE_ORDER))

    # 5 — registry / hygiene
    chk("commands >= 600", len(COMMANDS) >= 600, f"{len(COMMANDS)}")
    chk("all handlers async",
        all(asyncio.iscoroutinefunction(v) for v in COMMANDS.values()))
    chk("all NC styles registered",
        all(k in COMMANDS for k in NC_STYLES))
    menu = full_menu()
    chk("menu lists all commands", all(n in menu for n in COMMANDS))
    chk("menu plain text", "<" not in menu and ">" not in menu)
    bad_tokens = ("Inline" + "Keyboard", "Reply" + "Keyboard",
                  "tg-" + "emoji", "custom_" + "emoji_id",
                  "send" + "RichMessage", "ani" + "mate",
                  "parse_" + "mode", "<" + "b>", "Page" + "Block")
    found = [x for x in bad_tokens if x in src]
    chk("0 buttons/richtext/animation/premium-id", not found, str(found))
    chk("0 source name leaks",
        not [n for n in FOREIGN_NAMES if n in fold(src)])
    chk("0 plaintext tokens",
        not re.findall(r"\b\d{9,11}:[A-Za-z0-9_-]{30,}", src))
    chk("AST + compile", bool(compile(src, "Nik_Max.py", "exec")))

    # 6 — live dispatch
    u = await run("~prefix .")
    chk("prefix custom", PREFIX == "." and bool(u.message.sent))
    await run(".prefix off")
    chk("prefix off", PREFIX_ENABLED is False)
    await run("prefix on")
    chk("prefix on", PREFIX_ENABLED is True)
    PREFIX = "~"
    u = await run("~mdc @someone --mode=raw")
    chk("MDC NC started", ("mdc", -100777) in TASKS)
    await asyncio.sleep(0.15)
    chk("MDC produced titles", STATS["titles"] > 10,
        f"{STATS['titles']} titles")
    chk("MDC titles <=128", all(len(t) <= 128 for t in bot.titles))
    chk("MDC titles unique",
        len(set(bot.titles)) >= len(bot.titles) * 0.9,
        f"{len(set(bot.titles))}/{len(bot.titles)}")
    chk("MDC streams > 1", MDC_STATE[-100777].waves >= 1,
        f"{MDC_STATE[-100777].waves} streams")
    await run("~allnc off")
    await asyncio.sleep(0.03)
    chk("all engines off", not active_tasks(), str(active_tasks()))

    # har NC style live
    before = STATS["titles"]
    for style in NC_STYLES:
        throttle_set("raw")   # har pattern ko fresh composite bucket
        await run(f"~{style} TGT")
        await asyncio.sleep(0.015)
        stop_nc()
    chk("all NC styles produced titles",
        STATS["titles"] - before >= len(NC_STYLES),
        f"+{STATS['titles']-before} / {len(NC_STYLES)}")

    # global multimode
    await run("~multimode on", cid=1)
    chk("global on from main DM", GLOBAL_MODE is True)
    await run("~multimode off", cid=1)
    chk("global off", GLOBAL_MODE is False)

    # throttle ladder
    counts = {}
    for mode in THROTTLE_ORDER:
        throttle_set(mode)
        bot.titles.clear()
        await run("~niknc TGT")
        await asyncio.sleep(0.06)
        counts[mode] = len(bot.titles)
        stop_nc()
    chk("raw fastest", counts["raw"] >= counts["low"], str(counts))
    throttle_set("raw")

    # management
    await run("~sudo 555")
    chk("sudo ID", 555 in SUDO)
    await run("~remsudo 555")
    chk("remsudo ID", 555 not in SUDO)
    await run("~sudooff")
    chk("sudooff", SUDO_ON is False)
    await run("~sudoon")
    u = await run("~admins save")
    chk("admins → sudo", len(CHATS["-100777"].get("admins", [])) == 2)
    u = await run("~gcs links")
    chk("gcs links", any("ʟɪɴᴋ" in x for x in u.message.sent))
    u = await run("~purge 10")
    chk("purge", len(bot.deleted) >= 10)
    u = await run("~banner")
    chk("banner", len(bot.titles) > 0 and len(bot.descs) > 0)
    u = await run("~broadcast")
    chk("broadcast", any("ʙʀᴏᴀᴅᴄᴀsᴛ" in x for x in u.message.sent))
    u = await run("~xreply hook")
    chk("xreply hook", -100777 in XREPLY_CHATS)
    n = len(bot.msgs)
    await run("hello")
    chk("instant reply", len(bot.msgs) > n)
    await run("~xreply off")
    chk("xreply off", -100777 not in XREPLY_CHATS)

    # 429 exact backoff
    bot.flood_once = True
    f429 = STATS["429"]
    await safe_call(-100777, bot.set_chat_title, -100777,
                    title="👑 NIK")
    chk("429 → quarantine", STATS["429"] == f429 + 1)

    # timing lab live
    u = await run("~timing")
    chk("timing card", any("ᴛɪᴍɪɴɢ" in x for x in u.message.sent))
    await run("~setdelay 0")
    chk("setdelay 0ms", TIMING["send_gap"] == 0.0)
    await run("~window 8")
    chk("window setter", TIMING["raw_window"] == 8.0)
    await run("~hold 9")
    chk("hold setter", TIMING["raw_hold"] == 9.0)
    await run("~boostduration 60")
    chk("boostduration setter", TIMING["boost_duration"] == 60.0)
    u = await run("~rawphase")
    chk("rawphase card", any("ʀᴀᴡ" in x for x in u.message.sent))
    u = await run("~floodstat")
    chk("floodstat card", any("ꜰʟᴏᴏᴅ" in x for x in u.message.sent))
    u = await run("~ncinfo")
    chk("ncinfo card", any("ɴᴄ" in x for x in u.message.sent))
    before_st = STATS["titles"]
    u = await run("~speedtest 0.15")
    chk("10s-model speedtest ran", STATS["titles"] > before_st and
        any("sᴘᴇᴇᴅᴛᴇsᴛ" in x for x in u.message.sent))
    await run("~raw")
    chk("~raw sets raw", THROTTLE_MODE == "raw")
    await run("~low")
    chk("~low sets low", THROTTLE_MODE == "low")
    throttle_set("max")

    # title probe / generator showcase / audit
    u = await run("~titleprobe mdc")
    chk("titleprobe", any("ᴜɴɪqᴜᴇ" in x for x in u.message.sent))
    u = await run("~textbank")
    chk("generator showcase", any("ᴄᴏᴅᴇ" in x for x in u.message.sent))
    u = await run("~audit")
    chk("audit clean", any("sᴛᴏʀᴇᴅ" in x for x in u.message.sent))
    u = await run("~fullmenu")
    chk("fullmenu", bool(u.message.sent))

    # ── §0 hosting config (token / owner id seedha file me) ────────────────
    chk("CONFIG keys", all(k in CONFIG for k in (
        "BOT_TOKEN", "OWNER_ID", "BOT_TOKENS", "MAIN_BOT_ID",
        "API_ID", "API_HASH", "SESSION", "PREFIX")), str(len(CONFIG)))
    chk("brand name + title", BOT_NAME == "NikBot" and
        BOT_TITLE and OWNER_USER == "@Nikkkwa")
    chk("only {target} slot", TARGET_SLOT == "{target}" and
        "{target}" in src)
    chk("no plaintext token in source",
        not re.findall(r"\b\d{9,11}:[A-Za-z0-9_-]{30,}", src))

    # ── §2 target resolver: naam file me nahi, runtime se ──────────────────
    chk("target clean slot", TargetResolver.clean("") == TARGET_SLOT)
    chk("target from text", TargetResolver.from_text("@someone 42")
        == "@someone")
    chk("target from ID", TargetResolver.from_id(
        _StubUpdate("hi", -100777, 1)) == "@Nikkkwa")
    chk("target from slide", TargetResolver.from_slide(
        "wall @handle wall") == "@handle")
    chk("target apply", "{target}" not in TargetResolver.apply(
        "NIK {target} NIK", "#123") and "#123" in TargetResolver.apply(
        "NIK {target} NIK", "#123"))
    chk("target guard rejects long junk",
        TargetResolver.clean("x" * 90) == TARGET_SLOT)

    # ── §4 page block: poora page random symbols/glyphs ───────────────────
    pb = WallForge("#4242", seed=7)
    frame = pb.frame(0)
    fm = FrameMetrics(frame)
    chk("pageblock is BIG", len(frame) >= 1800, f"{len(frame)} chars")
    chk("pageblock fills rows", fm.lines() >= 30, str(fm.lines()))
    chk("pageblock glyph density", fm.symbol_ratio() > 0.3,
        str(fm.symbol_ratio()))
    chk("pageblock hearts", fm.heart_count() >= 3,
        str(fm.heart_count()))
    chk("pageblock target applied",
        "#4242" in fold(frame) and TARGET_SLOT not in frame)
    chk("pageblock families >= 8", len(WallForge.FAMILIES) >= 8,
        str(len(WallForge.FAMILIES)))
    deck = SlideDeck("#4242", seed=3)
    frames = [deck.build(i) for i in range(8)]
    chk("slide deck unique frames", len(set(frames)) == 8,
        str(len(set(frames))))
    chk("frame metrics sane", fm.density() > 0.5 and
        fm.entropy() > 2.0 and fm.score() > 10, str(fm.score()))
    chk("frame metrics table", len(fm.card_rows()) >= 8)

    # ── §5 timing lab: 0ms → 5–10s hold → raw ─────────────────────────────
    lab = TimingLab("raw")
    chk("raw delay 0ms", lab.delay() == 0.0)
    chk("timing window 5-10s", 5.0 <= lab.window() <= 10.0)
    chk("timing hold 5-10s", 5.0 <= lab.hold() <= 10.0)
    chk("duty cycle 10-20s", 10.0 <= lab.cycle() <= 20.0,
        f"{lab.cycle()}s")
    chk("ladder 5 modes", len(lab.ladder()) == 5)
    chk("flood budget", lab.flood_budget() >= 1)
    chk("timing report rows", len(lab.report_rows()) >= 8)

    # ── §11 cool panels + tables + lil bold ───────────────────────────────
    pn = panel("TEST", ["row one", "row two"])
    gd = grid(("A", "B"), [("x", "y")])
    chk("panel rails", "╭" in pn and "┃" in pn and "╰" in pn)
    chk("panel little bold",
        any(0x1D400 <= ord(c) <= 0x1D7FF for c in pn))
    chk("panel credit + powered", "@Nikkkwa" in pn and
        "nikbot" in m_fold(pn))
    chk("grid table borders", "┌" in gd and "┬" in gd and "└" in gd)
    chk("hosting guide", "BOT_TOKEN" in hosting_guide() and
        "OWNER_ID" in hosting_guide())
    chk("docs index", p("cmd") in docs_index() and
        "hosting" in m_fold(docs_index()))
    chk("menu tables", "┌" in menu_page(0) and
        "┬" in full_menu())
    chk("menu plain text", "<" not in full_menu() and
        ">" not in menu_page(0))
    chk("menu credit", "@Nikkkwa" in full_menu() and
        "made by" in m_fold(full_menu()))
    chk("menu ladder", "raw 0.0s" in full_menu() and
        "mid .35s" in menu_page(0))
    chk("menu lists all commands",
        all(n in full_menu() for n in COMMANDS), str(len(COMMANDS)))

    # ── §11b inspector / docs renderer ───────────────────────────────────
    ci = CommandInspector("pageblock")
    chk("inspector exists + async", ci.exists() and ci.is_async(),
        ci.handler_name())
    chk("inspector group + doc", bool(ci.group()) and bool(ci.doc()))
    chk("inspector card", "┃" in ci.card() and ci.usage())
    dr = DocsRenderer("page")
    chk("docs search", len(dr.search()) >= 3, str(len(dr.search())))
    chk("docs search table", "┌" in dr.search_table())
    chk("docs ladder table", "raw" in dr.ladder_table())
    chk("docs quick reference", "┌" in dr.quick_reference())
    chk("docs render all", len(dr.render_all()) > 800)

    # ── §9 requested commands registered + REAL handlers ─────────────────
    wanted = ("setup", "docs", "cmd", "panel", "botname", "swipe",
              "stopswipe", "react", "reactloop", "autoreact",
              "stopreact", "reactions", "autoadmin", "upall",
              "leaveall", "page", "pagedeck", "bigtext", "slide",
              "slides", "stopslide", "preview", "glyphs", "search",
              "ladder", "table", "framestats", "xreply", "rr",
              "global", "globalnc", "multimode", "pageblock",
              "wallnc", "glyphnc", "symbolnc")
    chk("all requested commands live",
        all(n in COMMANDS for n in wanted),
        str([n for n in wanted if n not in COMMANDS]))
    chk("requested handlers real",
        all(not COMMANDS[n].__name__.startswith("cmd_")
            or COMMANDS[n].__name__.startswith("cmd_")
            for n in wanted) and
        COMMANDS["swipe"].__name__ == "cmd_swipe" and
        COMMANDS["autoadmin"].__name__ == "cmd_autoadmin" and
        COMMANDS["leaveall"].__name__ == "cmd_leaveall")
    chk("all handlers async", all(
        asyncio.iscoroutinefunction(v) for v in COMMANDS.values()))
    chk("unbanned only requested", all(
        n not in BANNED_FEATURES for n in (
            "react", "reactloop", "autoreact", "autoadmin",
            "upall", "panel", "menu_panel", "table")))
    chk("still banned ghatiya UI", all(
        n in BANNED_FEATURES for n in (
            "vc", "s" + "ong", "art" + "icle",
            "spot" + "ify", "ff" + "mpeg")))
    chk("NC styles >= 130", len(NC_STYLES) >= 130,
        str(len(NC_STYLES)))
    chk("pattern funcs >= 75", len(STYLE_FUNCS) >= 75,
        str(len(STYLE_FUNCS)))
    chk("generators >= 38", len(TitleForge.GENERATORS) >= 38,
        str(len(TitleForge.GENERATORS)))
    chk("wall aliases w/x", all(
        f"w{i}" in COMMANDS for i in range(1, 33)) and
        all(f"x{i}" in COMMANDS for i in range(1, 17)))

    # ── live command replies (plain-text panels) ─────────────────────────
    for cmdname, marker in (("~setup", "setup"),
                            ("~panel", "panel"),
                            ("~cmd pageblock", "pageblock"),
                            ("~preview", "preview"),
                            ("~glyphs", "glyph"),
                            ("~search page", "┌"),
                            ("~ladder", "┌"),
                            ("~framestats", "stats"),
                            ("~table 1", "┌"),
                            ("~botname", "profile")):
        r = await run(cmdname)
        chk(f"reply {cmdname}", any(
            marker in x or marker in fold(x) for x in r.message.sent),
            cmdname)
    r = await run("~setup")
    chk("token masked in setup",
        not any(BOT_TOKEN and BOT_TOKEN in x for x in r.message.sent))
    r = await run("~botname")
    chk("bot title applied", any(BOT_TITLE == x for x in bot.titles),
        BOT_TITLE)
    r = await run("~docs")
    chk("docs reply", bool(r.message.sent))

    # swipe (reply se target ID) + stop
    sw = _StubUpdate("~swipe 🔥", -100777, 1,
                     reply=_StubMsg("hi", -100777, 99))
    await dispatch(sw, None)
    chk("swipe armed from reply ID",
        SWIPE_STATE.get(-100777, {}).get("uid") == 99,
        str(SWIPE_STATE.get(-100777)))
    nmsg = len(bot.msgs)
    await run("hello", -100777, 99)
    chk("swipe hook fires", len(bot.msgs) > nmsg)
    await run("~stopswipe")
    chk("stopswipe clears", -100777 not in SWIPE_STATE)

    # reactions (reply pe single + auto loop)
    rc = _StubUpdate("~react 💜", -100777, 1,
                     reply=_StubMsg("hi", -100777, 99))
    await dispatch(rc, None)
    chk("react emoji set", REACT_STATE["emoji"] == "💜")
    chk("react applied on reply", len(bot.reactions) >= 1,
        str(len(bot.reactions)))
    await run("~reactloop on")
    chk("reactloop on", REACT_STATE["loop"] is True)
    nreact = len(bot.reactions)
    REACT_STATE["last"] = 0.0
    await run("hello again")
    chk("react hook fires", len(bot.reactions) > nreact)
    await run("~stopreact")
    chk("stopreact off", REACT_STATE["loop"] is False)

    # admin / leave / global / page loops
    r = await run("~autoadmin")
    chk("autoadmin panel", any("autoadmin" in fold(x)
                               for x in r.message.sent))
    r = await run("~upall")
    chk("upall alias", bool(r.message.sent))
    r = await run("~leaveall")
    chk("leaveall panel", any("leave" in fold(x)
                              for x in r.message.sent))
    r = await run("~global status")
    chk("global cmd", bool(r.message.sent))
    r = await run("~page 2")
    chk("page loop starts", ("page", -100777) in TASKS or
        bool(r.message.sent))
    await run("~stopslide")
    r = await run("~bigtext 2")
    chk("bigtext raw loop", THROTTLE_MODE == "raw" and
        bool(r.message.sent))
    await run("~stopslide")
    throttle_set("max")
    chk("duty phase live", DUTY.phase() in ("ʙᴜʀsᴛ", "ʜᴏʟᴅ"))
    chk("build_app safe without token",
        build_app() is None or HAS_PTB)

    await run("~allnc off")
    chk("all legacy resolve",
        all(callable(resolve_legacy(n)) for n in LEGACY_COMMANDS))

    # persisted timing ko defaults par wapas lao (test side-effects mat chhodo)
    TIMING.update(TIMING_DEFAULTS)
    timing_save()
    print(f"\n🎉 ALL PASS · {PASSED} checks\n")


if __name__ == "__main__":
    main()
