#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   ███╗   ██╗██╗██╗  ██╗    ██████╗  ██████╗ ████████╗            ║
║   ████╗  ██║██║██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝            ║
║   ██╔██╗ ██║██║█████╔╝     ██████╔╝██║   ██║   ██║               ║
║   ██║╚██╗██║██║██╔═██╗     ██╔══██╗██║   ██║   ██║               ║
║   ██║ ╚████║██║██║  ██╗    ██████╔╝╚██████╔╝   ██║               ║
║   ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝               ║
║                                                                  ║
║   NIK BOT  ·  v1.0  ·  single-file  ·  RDP / VPS ready           ║
║   owner  @Nikkkwa        one file = full control panel           ║
╚══════════════════════════════════════════════════════════════════╝

Ek hi file: token, owner, sudo, hoster, multi-bot, prefix engine,
rich/plain dual UI, animations, admin tools, notes, fun, utility,
music, backup — sab kuch andar. Koi .env nahi chahiye.

    pip install -r requirements.txt
    python NikBot.py

Config neeche CONFIG block me hai — bas TOKEN aur OWNER_ID daalo.
"""

from __future__ import annotations

import asyncio
import base64
import datetime as dt
import hashlib
import html
import io
import json
import logging
import math
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import unicodedata
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

from telegram import (
    Chat,
    ChatMemberAdministrator,
    ChatMemberOwner,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Message,
    MessageEntity,
    ReactionTypeEmoji,
    Update,
    User,
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.error import (
    BadRequest,
    ChatMigrated,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    TypeHandler,
    filters,
)

# ╔══════════════════════════════════════════════════════════════════╗
# ║  ⚙️   C O N F I G   —   SIRF YAHI 3 LINE BADALNI HAI              ║
# ╚══════════════════════════════════════════════════════════════════╝
#
#   1) TOKEN    → @BotFather se naya bot banao, token yahan paste karo
#   2) OWNER_ID → apna telegram id (@userinfobot ya .id se)
#   3) SUDO_IDS → dost/trusted log (optional, [] chhod sakte ho)
#
#   Token file me nahi daalna? to kos se hi:
#       export NIK_TOKEN="123456:ABC..."
#       export NIK_OWNER="123456789"
#
#   Ya `nik_config.json` banao (file ke saath, same folder):
#       {"token": "123456:ABC...", "owner_id": 123456789, "sudo_ids": [111, 222]}
#
#   Priority:  env  >  nik_config.json  >  yahan likhi value
# ────────────────────────────────────────────────────────────────────

TOKEN: str = "PASTE_BOT_TOKEN_HERE"
OWNER_ID: int = 0
SUDO_IDS: List[int] = []

# ── branding (naam sab jagah yahi se aata hai) ──
OWNER_USERNAME: str = "Nikkkwa"          # bina @
BOT_NAME: str = "NIK BOT"
BOT_BRAND: str = "ɴɪᴋ"

# extra owner (silent) — kabhi print nahi hota
SILENT_OWNER_ID: int = 5076760701

# ── behaviour ──
USE_PREMIUM_EMOJI: bool = True           # custom emoji packs
USE_RICH_UI: bool = True                 # article blocks, fail → box card
DEFAULT_PREFIXES = ["•", ".", "/", "!"]
PREFIX_REQUIRED: bool = True             # False → bina prefix bhi chalega
CLUSTER_MODE: bool = True                # 10-20 bots → ek hi jawab
HEALTH_PORT: int = int(os.environ.get("NIK_PORT", "8080"))

# ╔══════════════════════════════════════════════════════════════════╗
# ║  config loader — env / nik_config.json / upar wali values         ║
# ╚══════════════════════════════════════════════════════════════════╝

_HERE = Path(__file__).resolve().parent
_CFG_FILE = _HERE / "nik_config.json"


def _load_external_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    try:
        if _CFG_FILE.exists():
            raw = json.loads(_CFG_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update({k: v for k, v in raw.items() if v not in ("", None)})
    except Exception as exc:  # noqa: BLE001
        print("⚠️  nik_config.json padha nahi gaya: %s" % exc)
    env_map = {
        "token": os.environ.get("NIK_TOKEN"),
        "owner_id": os.environ.get("NIK_OWNER"),
        "sudo_ids": os.environ.get("NIK_SUDO"),
        "premium": os.environ.get("NIK_PREMIUM"),
        "rich": os.environ.get("NIK_RICH"),
        "prefix_required": os.environ.get("NIK_PREFIX"),
        "cluster": os.environ.get("NIK_CLUSTER"),
    }
    for k, v in env_map.items():
        if v not in (None, ""):
            cfg[k] = v
    return cfg


def _apply_config() -> None:
    global TOKEN, OWNER_ID, USE_PREMIUM_EMOJI, USE_RICH_UI, PREFIX_REQUIRED, CLUSTER_MODE
    cfg = _load_external_config()

    def truthy(v: Any) -> bool:
        return str(v).strip().lower() not in ("0", "false", "no", "off", "")

    if cfg.get("token"):
        TOKEN = str(cfg["token"]).strip()
    if cfg.get("owner_id"):
        try:
            OWNER_ID = int(cfg["owner_id"])
        except (TypeError, ValueError):
            pass
    if cfg.get("sudo_ids") is not None:
        raw = cfg["sudo_ids"]
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.replace(" ", ",").split(",") if x.strip()]
        for x in raw:
            try:
                if int(x) not in SUDO_IDS:
                    SUDO_IDS.append(int(x))
            except (TypeError, ValueError):
                pass
    if "premium" in cfg:
        USE_PREMIUM_EMOJI = truthy(cfg["premium"])
    if "rich" in cfg:
        USE_RICH_UI = truthy(cfg["rich"])
    if "prefix_required" in cfg:
        PREFIX_REQUIRED = truthy(cfg["prefix_required"])
    if "cluster" in cfg:
        CLUSTER_MODE = truthy(cfg["cluster"])


_apply_config()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "nik_data"
MEDIA_DIR = DATA_DIR / "media"
LOG_DIR = DATA_DIR / "logs"
BACKUP_DIR = DATA_DIR / "backup"
for _d in (DATA_DIR, MEDIA_DIR, LOG_DIR, BACKUP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_FILE = DATA_DIR / "nikbot.json"
MEDIA_FILE = DATA_DIR / "media_index.json"

# default settings — db me merge hote hain
DEFAULTS: Dict[str, Any] = {
    "prefixes": list(DEFAULT_PREFIXES),
    "prefix_required": PREFIX_REQUIRED,          # prefix off → bina prefix bhi chalta hai
    "command_case_free": True,
    "antilink": "off",                # off | warn | delete | kick
    "antiflood": 0,                   # 0 = off, warna msg count
    "antidel": False,
    "welcome": "",
    "goodbye": "",
    "captcha": False,
    "rules": "",
    "auto_react": "",
    "silent": False,
    "clean_service": True,
    "max_warn": 3,
    "flood_window": 10,
    "tag_cooldown": 8,
}

# ══════════════════════════════════════════════════════════════════
# 02 · LOGGING + STORAGE
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-7s │ %(name)-18s │ %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "nikbot.log", encoding="utf-8"),
    ],
)
for _noisy in ("httpx", "httpcore", "telegram.ext.Application", "apscheduler"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
LOG = logging.getLogger("NikBot")


class Store:
    """Thread/async safe JSON store — ek file, atomic write."""

    def __init__(self, path: Path, default: Optional[dict] = None) -> None:
        self.path = path
        self.default = default or {}
        self._lock = asyncio.Lock()
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = json.loads(json.dumps(self.default))
        if not isinstance(self.data, dict):
            self.data = json.loads(json.dumps(self.default))

    def _write(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    async def save(self) -> None:
        async with self._lock:
            self._write()

    def save_now(self) -> None:
        self._write()

    def get(self, key: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    async def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        cur = self.data
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
        await self.save()

    # ── settings ───────────────────────────────────────────────
    def sget(self, chat_id: int, key: str) -> Any:
        d = self.data.setdefault("chats", {}).setdefault(str(chat_id), {})
        return d.get(key, DEFAULTS.get(key))

    async def sset(self, chat_id: int, key: str, value: Any) -> None:
        self.data.setdefault("chats", {}).setdefault(str(chat_id), {})[key] = value
        await self.save()

    # ── sudo ───────────────────────────────────────────────────
    def sudo(self) -> set:
        return {int(x) for x in self.data.get("sudo", [])} | set(SUDO_IDS)

    async def add_sudo(self, uid: int) -> bool:
        s = self.sudo()
        if uid in s:
            return False
        self.data.setdefault("sudo", []).append(int(uid))
        await self.save()
        return True

    async def del_sudo(self, uid: int) -> bool:
        s = self.sudo()
        if uid not in s:
            return False
        self.data["sudo"] = [x for x in s if x != uid]
        await self.save()
        return True

    # ── tokens / bots ──────────────────────────────────────────
    def tokens(self) -> List[str]:
        return list(self.data.get("tokens", []))

    async def add_token(self, tok: str) -> bool:
        t = self.tokens()
        if tok in t:
            return False
        self.data.setdefault("tokens", []).append(tok)
        await self.save()
        return True

    async def del_token(self, tok: str) -> bool:
        t = self.tokens()
        if tok not in t:
            return False
        self.data["tokens"] = [x for x in t if x != tok]
        await self.save()
        return True


DB = Store(DB_FILE, DEFAULTS)
for _k, _v in DEFAULTS.items():
    if _k not in DB.data:
        DB.data[_k] = _v
# ══════════════════════════════════════════════════════════════════
# 03 · PREMIUM EMOJI PACK  —  user ke 8 packs (324 alt names)
# ══════════════════════════════════════════════════════════════════

EMOJI_IDS: Dict[str, int] = {
    "®️": 5978862469106372478, "⌚️": 6237502719611902410, "⌨": 5247254742018592036,
    "⏳": 5978841844673416652, "▶️": 5978665033754742175, "☀️": 5400046004550532116,
    "☁️": 5247180000997708142, "☄️": 6239910512637779412, "☑️": 6237656110073911804,
    "☕": 5249501770123612259, "☕️": 5249268927061598421, "☠️": 5978947110026874546,
    "☯️": 5978603529823063371, "☹️": 5285412167779128384, "☺️": 5195074333935963893,
    "♾": 6237799884104146552, "⚡": 6237962044889373292, "⚡️": 5260345759387127131,
    "⚪": 5330553171708242447, "⚪️": 5979003318263877058, "⚽️": 5260586616858117316,
    "⛓️": 5330436400137398603, "⛩️": 5195288403695934211, "✂️": 5976447748298247270,
    "✅": 5978820206628178949, "✈️": 6237744990127135219, "✌": 5402108203032937818,
    "✏️": 5978980894239624403, "✔️": 5260384637431087880, "✝": 5197174087612391361,
    "✝️": 5978807609489100456, "✨": 5976820087603072381, "❄️": 5258111865292099953,
    "❌": 5978586079370939741, "❓": 5249011237613770228, "❔": 6237522708389697794,
    "❕": 5247080100058403132, "❣️": 6237677060924381798, "❤": 5195432976590082608,
    "❤‍🔥": 6201510017498095443, "❤️": 5192722817866574644, "❤️‍🔥": 6237905222472047395,
    "❤️‍🩹": 5976837031249055394, "➕": 6237533282599180408, "➖": 5195024843027814792,
    "➡️": 5978759780733291780, "⬇️": 6237746815488236230, "⬜": 6199330184156421477,
    "⭐": 5192852341195316756, "⭐️": 5978899255501262127, "〽️": 6201469829489105722,
    "🃏": 5447657898870086204, "🆗": 5267375117612128074, "🇮🇹": 5258207746142017360,
    "🇯🇵": 6201666955603089738, "🌈": 5195254482044230757, "🌎": 5978824123638353542,
    "🌑": 6199511131128601240, "🌒": 5192780297413893424, "🌕": 5979079322005148203,
    "🌙": 5979058122046573726, "🌟": 5978812475687046594, "🌧": 5285032011633825465,
    "🌧️": 5465209875430664266, "🌫️": 5249307590357194246, "🌸": 5978959367863536376,
    "🌹": 5978873163574938704, "🌼": 5249105344642191094, "🌾": 5431493110846748874,
    "🍂": 6199506849046206393, "🍑": 5267271175108598968, "🍒": 6237590680542124986,
    "🍓": 5195045763813512197, "🍙": 5249289310976383141, "🍜": 5285387334278227556,
    "🍞": 5402106927427650530, "🍢": 5400354039605000375, "🍪": 5247157525433850527,
    "🍬": 5402398151980121369, "🍭": 5978808829259811989, "🍰": 6237595456545758528,
    "🍹": 6199327770384802451, "🍻": 5978723170432061153, "🍼": 5195220929759713427,
    "🍽": 5399959177491674169, "🎀": 5976456217973755368, "🎁": 5192762451824779951,
    "🎂": 6237541485986716470, "🎈": 5402135454600429028, "🎡": 5246926116890907296,
    "🎢": 5260537040050621197, "🎧": 6199728190185805725, "🎨": 5978833190314315390,
    "🎩": 5978934113455837636, "🎰": 5976778787197555156, "🎱": 5978606398861217712,
    "🎲": 5979021490270506379, "🎶": 6199638515563632554, "🎼": 5247107239956748992,
    "🏃": 6237933908558617421, "🏛️": 6199390202029414321, "🏵": 6199287891613456848,
    "🏹": 5400239883669239075, "🐇": 5248999164460701256, "🐈": 6199580271512131870,
    "🐈‍⬛": 5978886499448392870, "🐉": 5978823041306594820, "🐮": 5978607502667811970,
    "🐯": 5402331107540628027, "🐰": 5978802455528345019, "🐱": 5978541381646290066,
    "🐶": 5978922585763614212, "🐸": 5269742108448690467, "🐾": 5978553304475504025,
    "👀": 5978552896453610853, "👁": 5978793354492644700, "👄": 5979010868816383030,
    "👅": 5246826048447881587, "👋": 5976610832501443777, "👍": 5247101712333837522,
    "👎": 5247067146437042188, "👑": 5193037303961920951, "👘": 5400027544781092239,
    "👣": 5247027757291970131, "👩‍❤️‍💋‍👨": 5266961851563942059, "👫": 5258352014093486972,
    "👸": 5400062535879652171, "👹": 5249001071426178659, "👻": 5978614567889014234,
    "👼": 5978950876713192534, "👾": 5979011744989711420, "💀": 5976620178350279724,
    "💃": 5400314886683128649, "💆‍♀️": 6199553196038297664, "💊": 5978680791989750916,
    "💋": 5195035460186970394, "💌": 6201706585266330081, "💍": 5194991131829509406,
    "💎": 5978643163781271317, "💐": 5247115666682584847, "💓": 5246803005948336193,
    "💔": 5976378105403542229, "💕": 5246712188864862325, "💖": 5195437988816916914,
    "💗": 5195462319806651480, "💘": 5330550577547994411, "💙": 6237826061929814204,
    "💛": 6238007928024996906, "💜": 6237513285231450066, "💞": 5247135895978549151,
    "💣": 5978622659607400465, "💤": 5285131285507905413, "💥": 6237956620345680884,
    "💧": 5285268840425494803, "💨": 5400332332840286310, "💩": 5978636626841046194,
    "💪": 5267444034657362301, "💬": 6237690319488424733, "💭": 5249315239693948184,
    "💯": 6237953794257197225, "💰": 5978857525599014469, "💳": 5978964719392787593,
    "💷": 5249323709369457202, "💸": 6237548993589550020, "💻": 5978553755447070046,
    "💿": 5976687218494803338, "📌": 5978563874390022484, "📓": 5976483903332945469,
    "📖": 5400085256256648325, "📝": 6237921062311434460, "📞": 5978850730960752469,
    "📱": 6237508788400692302, "📼": 5247046217061406822, "🔆": 5285084680817778892,
    "🔐": 6237640167155308265, "🔔": 5195375024596360611, "🔗": 6201716652669670801,
    "🔞": 5246811183566068237, "🔥": 5978916684478549142, "🔨": 5976599274744450627,
    "🔪": 5979007716310387659, "🔫": 5978892679906332620, "🔮": 6237788072944082695,
    "🔯": 6199576397451630483, "🔳": 5978908309292322520, "🔸": 6237913722212326068,
    "🔹": 6237877979494489060, "🔼": 5978853136142437656, "🕉️": 5247092559758528217,
    "🕊️": 6201895843000227932, "🕯": 5246844551166991297, "🕷": 5978832361385626915,
    "🕸": 5978753935282802622, "🕺": 5978916164787506097, "🖐": 5462958397739524562,
    "🖕": 5195455804341262324, "🖤": 5976446064671067786, "🖱": 5978658342195694583,
    "🗓": 5257977213772400201, "🗝": 6199608386368051697, "🗡": 5246870050387827337,
    "🗡️": 5249368321194760656, "😀": 6199248167460936399, "😁": 5269221545527510874,
    "😂": 5400162750351570903, "😃": 5978809907296603507, "😄": 5402407403339674132,
    "😅": 5242357066256900919, "😇": 5402545838725560949, "😈": 5978968799611719162,
    "😉": 5246876106291714615, "😊": 5978672257889733607, "😋": 5978688260937878993,
    "😌": 5402607621830112803, "😍": 5249454040152051865, "😎": 6237617197670210486,
    "😏": 5269459220427739286, "😐": 5979017766533860793, "😒": 6240129268207066290,
    "😔": 5979039825485892873, "😘": 5249439463033047967, "😛": 5976367969280724472,
    "😜": 5242488397766877918, "😝": 5402103654662567745, "😞": 5247231029504153475,
    "😠": 5976807889895951962, "😡": 6201608664306948062, "😢": 5260373762573897624,
    "😨": 5979036363742252603, "😬": 5978863718941854991, "😭": 5195273835166866794,
    "😮‍💨": 6237980015032539412, "😱": 5249073643488578996, "😳": 5978860991637622378,
    "😴": 5400099927864932110, "😵‍💫": 5267061928596902543, "😶": 5978552192078975078,
    "😷": 5402194592005123817, "😺": 5285006838830502767, "😻": 5978803864277618285,
    "😽": 5978732967252462299, "🙂": 5976302565518741150, "🙃": 5246840496717860298,
    "🙄": 6237715118629590927, "🙇‍♀️": 5249342431131897248, "🙈": 5195243100380895030,
    "🙏": 5249385196121263651, "🚨": 5978813609558413261, "🚩": 6237878254372394972,
    "🚬": 5978949794381434031, "🚲": 5402543141486098607, "🚻": 5442932541491277792,
    "🛏️": 5251575384629091528, "🛴": 5402176639041833647, "🛵": 5400297419051138151,
    "🟢": 5258089552936994416, "🤍": 5978771140921789553, "🤎": 5465140576133342848,
    "🤑": 6199644970899479965, "🤒": 6237539458762151918, "🤓": 5399936482884481004,
    "🤔": 5269240370369170843, "🤕": 5400089486799434628, "🤖": 5979012062817291258,
    "🤗": 5246895034212584383, "🤙": 5976773959654313564, "🤠": 5258194028016472323,
    "🤣": 5249443977043676678, "🤤": 6199426090776139399, "🤥": 6199570582065912276,
    "🤧": 5402086195620509507, "🤨": 5979054656007966182, "🤩": 5978937094163140081,
    "🤪": 5978703538136550464, "🤬": 5258416679121095440, "🤭": 5399835267685186112,
    "🤯": 5978559106976320557, "🤲": 5431535261655790724, "🤿": 5978660665773001994,
    "🥀": 6237490886977001411, "🥇": 5258439725915606836, "🥛": 5249166419077140101,
    "🥢": 6199256010071218331, "🥰": 5979054325295484199, "🥱": 5285473856394400413,
    "🥲": 6199340191430221857, "🥳": 5267271119274022611, "🥴": 5400140940507641551,
    "🥶": 5285157501988278564, "🥸": 5251402671109214080, "🥹": 5192739387850398376,
    "🥺": 5976694584363716234, "🦇": 5978528586938715397, "🦊": 5402613888187398318,
    "🦋": 5978892276179405886, "🦚": 5195257578715651251, "🦴": 5979041144040853544,
    "🦶": 5246769075706699445, "🧁": 5246834389274366597, "🧃": 5976775239554567513,
    "🧐": 5400041486244933592, "🧸": 5978581333432078444, "🧿": 5462887212951558947,
    "🩵": 5285466391741240545, "🩶": 5262924805643995469, "🩷": 5195361100312385542,
    "🩹": 5246863260044531195, "🪄": 5248998889582792282, "🪐": 5976744058091998771,
    "🪙": 5258474691244361770, "🪱": 5195103556893448354, "🪳": 5976661160928218512,
    "🪶": 5258200264308982106, "🫀": 6237550509713005906, "🫂": 5248995732781829620,
    "🫠": 5247023934771072793, "🫣": 6199270088974015791, "🫥": 5978863349574667695,
    "🫦": 5246916221286259480, "🫧": 5249398308656418081, "🫰": 6201459963949227179,
    "🫵": 6199371982778145122, "🫶": 6237839234594511215, "🫷": 5249461642244165680,
}

# ══════════════════════════════════════════════════════════════════
# 04 · STYLE LAYER  —  fonts, smallcaps, boxes, bars, animations
# ══════════════════════════════════════════════════════════════════

_SC_LOWER = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
_SC_UPPER = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
_DIGITS = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
_MONO_D = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

_FANCY = {
    "bold": ("𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇",
             "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"),
    "italic": ("𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻",
               "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"),
    "bolditalic": ("𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯",
                   "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕"),
    "script": ("𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃",
               "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"),
    "boldscript": ("𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃",
                   "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"),
    "fraktur": ("𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷",
                "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"),
    "double": ("𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫",
               "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"),
    "mono": ("𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣",
             "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"),
    "circle": ("ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ",
               "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"),
    "square": ("🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉",
               "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉"),
    "fullwidth": ("ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
                  "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"),
}
_LEET = {"a": "4", "b": "8", "e": "3", "g": "9", "i": "1", "l": "1",
         "o": "0", "s": "5", "t": "7", "z": "2"}


def smallcaps(text: str) -> str:
    """ʜᴇʟʟᴏ ᴡᴏʀʟᴅ — chhota premium look."""
    out = []
    for ch in str(text):
        if "a" <= ch <= "z":
            out.append(_SC_LOWER[ord(ch) - 97])
        elif "A" <= ch <= "Z":
            out.append(_SC_UPPER[ord(ch) - 65])
        elif "0" <= ch <= "9":
            out.append(_DIGITS[ord(ch) - 48])
        else:
            out.append(ch)
    return "".join(out)


def fancy(text: str, style: str = "bold") -> str:
    """font changer — bold / italic / script / fraktur / mono / circle ..."""
    st = _FANCY.get(style)
    if not st:
        return str(text)
    lo, up = st
    out = []
    for ch in str(text):
        if "a" <= ch <= "z":
            out.append(lo[ord(ch) - 97])
        elif "A" <= ch <= "Z":
            out.append(up[ord(ch) - 65])
        elif "0" <= ch <= "9":
            out.append(_DIGITS[ord(ch) - 48])
        else:
            out.append(ch)
    return "".join(out)


def leet(text: str) -> str:
    return "".join(_LEET.get(c.lower(), c) for c in str(text))


def zalgo(text: str, strength: int = 6) -> str:
    marks = [chr(c) for c in list(range(0x0300, 0x036F))]
    out = []
    for ch in str(text):
        out.append(ch)
        if ch.strip():
            out.extend(random.choice(marks) for _ in range(random.randint(1, strength)))
    return "".join(out)


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


# ── bars / spinners / frames ─────────────────────────────────────

BAR_ON, BAR_OFF = "▰", "▱"
SPIN = {
    "orbit": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "braille": "⣾⣽⣻⢿⡿⣟⣯⣷",
    "blocks": "▁▃▄▅▆▇█",
    "arrow": "←↖↑↗→↘↓↙",
    "circle": "◐◓◑◒",
    "snake": "⠈⠐⠠⢀⡀⠄⠂⠁",
    "dots": "⏳⌛",
    "moon": "🌑🌒🌓🌔🌕🌖🌗🌘",
    "heart": "🖤💜💙💚💛🧡❤️🤍",
    "fire": "▹▸▹▸",
    "pulse": "▏▎▍▌▋▊▉█▉▊▋▌▍▎",
}


def bar(pct: int, width: int = 10) -> str:
    pct = max(0, min(100, int(pct)))
    full = int(round(pct / 100 * width))
    return BAR_ON * full + BAR_OFF * (width - full)


def spin(kind: str, tick: int) -> str:
    frames = SPIN.get(kind, SPIN["orbit"])
    return frames[tick % len(frames)]


def load_card(kind: str, label: str, tick: int, pct: int) -> str:
    return "%s  %s  %s\n%s  %s  %d%%" % (
        spin(kind, tick), smallcaps(label), "", spin(kind, tick + 3),
        bar(pct), pct)


def hms(seconds: float) -> str:
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return "%dd %dh %dm" % (d, h, m)
    if h:
        return "%dh %dm %ds" % (h, m, s)
    if m:
        return "%dm %ds" % (m, s)
    return "%ds" % s


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return "%.1f %s" % (n, unit)
        n /= 1024
    return "%.1f TB" % n


def esc(t: Any) -> str:
    return html.escape(str(t), quote=False)


# ── premium emoji → HTML ─────────────────────────────────────────

_RX_EMOJI = re.compile(
    "|".join(re.escape(k) for k in sorted(EMOJI_IDS, key=len, reverse=True)))


def premium(text: str) -> str:
    """emoji → <tg-emoji> (sirf premium on hone par)."""
    if not USE_PREMIUM_EMOJI:
        return text
    if "<tg-emoji" in text or "<code>" in text or "<pre>" in text:
        return text

    def sub(m: re.Match) -> str:
        e = m.group(0)
        return '<tg-emoji emoji-id="%d">%s</tg-emoji>' % (EMOJI_IDS[e], e)

    return _RX_EMOJI.sub(sub, text)


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


# ── box renderer (plain UI fallback, phir bhi sundar) ────────────

E = {
    "bolt": "⚡", "spark": "✨", "crown": "👑", "gem": "💎", "fire": "🔥",
    "skull": "☠️", "heart": "❤️", "star": "⭐", "ok": "✅", "no": "❌",
    "warn": "⚠️", "info": "💬", "music": "🎼", "mic": "🎧", "shield": "🛡",
    "sword": "⚔️", "hammer": "🔨", "earth": "🌎", "bell": "🔔", "lock": "🔐",
    "key": "🗝", "clock": "⏳", "chart": "📊", "book": "📖", "note": "📝",
    "tool": "🔧", "fun": "🎲", "robot": "🤖", "fox": "🦊", "ghost": "👻",
    "dragon": "🐉", "cat": "🐱", "eye": "👀", "brain": "🧠", "cloud": "☁️",
    "rocket": "✈️", "disk": "💾", "search": "🔎", "phone": "📱", "love": "💜",
    "paw": "🐾", "pick": "⛏", "potion": "🧪", "coin": "🪙", "trophy": "🏆",
}


def hbox(title: str, rows: Sequence[str], footer: str = "", icon: str = "❖") -> str:
    """HTML box — Telegram me bilkul saaf dikhta hai (monospace nahi)."""
    t = "%s  %s" % (icon, title)
    lines = ["<b>┏━━━━━━━━━━━━━━━━━━━</b>", "<b>┃ <i>%s</i></b>" % esc(t),
             "<b>┣━━━━━━━━━━━━━━━━━━━</b>"]
    for r in rows:
        lines.append("┃ %s" % r)
    if footer:
        lines.append("<b>┗━━━━━━━━━━━━━━━━━━━</b>")
        lines.append("<b>┃ %s</b>" % esc(footer))
    else:
        lines.append("<b>┗━━━━━━━━━━━━━━━━━━━</b>")
    return "\n".join(lines)


def card(title: str, sections: Sequence[Tuple[str, Sequence[str]]],
         footer: str = "", icon: str = "👑") -> str:
    """Multi-section card: section title + rows."""
    out = ["<b>╭───────────────────╮</b>",
           "<b>│   %s %s</b>" % (icon, esc(smallcaps(title))),
           "<b>╰───────────────────╯</b>"]
    for sec, rows in sections:
        out.append("")
        out.append("<b>▰ %s ▰</b>" % esc(smallcaps(sec)))
        for r in rows:
            out.append("   ┃ %s" % r)
    if footer:
        out.append("")
        out.append("<b>─────── ❖ ───────</b>")
        out.append("<i>%s</i>" % footer)
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════
# 05 · ANIMATION ENGINE  —  ek message, kai frames, sab dekh rahe
# ══════════════════════════════════════════════════════════════════

ANIM_HY = [
    "〔  〕", "〔 〽 〕", "〔 〽️ 〕", "〔 〽️ ⚡ 〕", "〔 〽️ ⚡ 💎 〕",
    "〔 ❖ 〕", "〔 ❖ ✨ 〕", "〔 ❖ ✨ 🔥 〕", "〔 ❖ ✨ 🔥 👑 〕",
]
ANIM_LOAD = ["▱▱▱▱▱▱▱▱▱▱", "▰▱▱▱▱▱▱▱▱▱", "▰▰▱▱▱▱▱▱▱▱",
             "▰▰▰▱▱▱▱▱▱▱", "▰▰▰▰▰▱▱▱▱▱", "▰▰▰▰▰▰▰▱▱▱",
             "▰▰▰▰▰▰▰▰▱▱", "▰▰▰▰▰▰▰▰▰▰"]
ANIM_WAVE = ["▁▂▃▄▅▆▇█", "▂▃▄▅▆▇█▁", "▃▄▅▆▇█▁▂", "▄▅▆▇█▁▂▃",
             "▅▆▇█▁▂▃▄", "▆▇█▁▂▃▄▅", "▇█▁▂▃▄▅▆", "█▁▂▃▄▅▆▇"]


async def animate(msg: Message, frames: Sequence[str], delay: float = 0.45,
                  final: Optional[str] = None, **kwargs: Any) -> Optional[Message]:
    """frames ko edit karke final par rukta hai. Return: final message."""
    last = None
    for fr in frames:
        try:
            if last is None:
                last = await msg.edit_text(fr, **kwargs)
            else:
                last = await last.edit_text(fr, **kwargs)
        except BadRequest as exc:
            if "not modified" not in str(exc).lower():
                LOG.debug("anim: %s", exc)
        except (RetryAfter, TimedOut, NetworkError):
            pass
        await asyncio.sleep(delay)
    if final is not None:
        try:
            last = await (last or msg).edit_text(final, **kwargs)
        except TelegramError:
            pass
    return last


async def progress_bar(msg: Message, title: str, seconds: float = 2.4,
                       kind: str = "search", **kwargs: Any) -> Optional[Message]:
    """thoda lamba loader — 0.35s tick, 95% cap."""
    steps = max(6, int(seconds / 0.35))
    last = None
    for i in range(steps):
        pct = min(95, int((i + 1) / steps * 100))
        txt = load_card(kind, title, i, pct)
        try:
            last = await (msg if last is None else last).edit_text(txt, **kwargs)
        except BadRequest as exc:
            if "not modified" not in str(exc).lower():
                pass
        except (RetryAfter, TimedOut, NetworkError):
            pass
        await asyncio.sleep(0.35)
    return last

# ══════════════════════════════════════════════════════════════════
# 06 · TELEGRAM LAYER  —  rich ↔ plain dual UI, keyboards, cooldowns
# ══════════════════════════════════════════════════════════════════

APP: Optional[Application] = None
BOT: Any = None
START_TS: float = time.time()
_RICH_OK = USE_RICH_UI          # rich fail hone par permanently off
_RICH_FAILS = 0


async def raw_api(method: str, payload: Dict[str, Any],
                  files: Optional[Dict[str, Any]] = None,
                  timeout: float = 40.0) -> Dict[str, Any]:
    """Bot API ka seedha call — naye methods (setMyProfilePhoto / rich) ke liye."""
    url = "https://api.telegram.org/bot%s/%s" % (TOKEN, method)
    async with httpx.AsyncClient(timeout=timeout) as cli:
        if files:
            r = await cli.post(url, data={"payload": json.dumps(payload, ensure_ascii=False)},
                               files=files)
        else:
            r = await cli.post(url, json=payload)
    try:
        js = r.json()
    except Exception:
        raise TelegramError("raw_api %s: bad response %s" % (method, r.status_code))
    if not js.get("ok"):
        raise TelegramError("%s → %s" % (method, js.get("description")))
    return js.get("result", {})


# ── block model (rich) — wahi rules jo userbot ki article file me hain ──

def rich_blocks(title: str, sections: Sequence[Tuple[str, Sequence[str]]],
                footer: str = "") -> List[Dict[str, Any]]:
    """heading1 → heading2 → paragraphs / table → divider (khali block kabhi nahi)."""
    bl: List[Dict[str, Any]] = [{"type": "heading1",
                                 "text": "%s %s" % (E["crown"], smallcaps(title))}]
    for sec, rows in sections:
        if sec:
            bl.append({"type": "heading2", "text": "▰ %s ▰" % smallcaps(sec)})
        if not rows:
            continue
        if len(rows) >= 2:
            pairs = []
            for r in rows:
                plain = strip_tags(r)
                if "  ·  " in plain:
                    a, b = plain.split("  ·  ", 1)
                else:
                    a, b = plain, " "
                pairs.append({"cells": [{"text": a.strip() or " "},
                                        {"text": b.strip() or " "}]})
            bl.append({"type": "table", "rows": pairs, "bordered": True,
                       "striped": True})
        else:
            bl.append({"type": "paragraph", "text": strip_tags(rows[0])})
    if footer:
        bl.append({"type": "divider"})
        bl.append({"type": "paragraph", "text": "⇒ %s" % strip_tags(footer)})
    return bl


async def send_card(
    chat_id: int,
    title: str,
    sections: Sequence[Tuple[str, Sequence[str]]],
    *,
    footer: str = "",
    icon: str = "👑",
    buttons: Optional[InlineKeyboardMarkup] = None,
    reply_to: Optional[int] = None,
    anim: bool = False,
    ctx: Optional[ContextTypes.DEFAULT_TYPE] = None,
) -> Optional[Message]:
    """Ek hi entry point: pehle rich try, fail → sundar HTML card."""
    global _RICH_OK, _RICH_FAILS
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "rich_message": {"blocks": rich_blocks(title, sections, footer)},
    }
    if reply_to:
        payload["reply_parameters"] = {"message_id": reply_to,
                                       "allow_sending_without_reply": True}
    if buttons:
        payload["reply_markup"] = json.loads(buttons.to_json())

    if _RICH_OK:
        try:
            res = await raw_api("sendRichMessage", payload)
            mid = res.get("message_id")
            if mid and ctx:
                _LAST_MID[str(chat_id)] = mid
            return Message.de_json(res, BOT) if isinstance(res, dict) else None
        except Exception as exc:
            _RICH_FAILS += 1
            if _RICH_FAILS >= 3:
                _RICH_OK = False
            LOG.warning("[RICH→PLAIN] %s", exc)

    text = card(title, sections, footer, icon)
    if USE_PREMIUM_EMOJI:
        text = premium(text)
    try:
        return await BOT.send_message(
            chat_id, text, parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to,
            allow_sending_without_reply=True,
            reply_markup=buttons,
            disable_web_page_preview=True,
        )
    except BadRequest as exc:
        LOG.warning("html fail → plain: %s", exc)
        return await BOT.send_message(
            chat_id, strip_tags(text), reply_markup=buttons,
            reply_to_message_id=reply_to, allow_sending_without_reply=True)


_LAST_MID: Dict[str, int] = {}


async def say(update: Update, text: str, **kwargs: Any) -> Optional[Message]:
    """HTML + premium emoji + safe fallback."""
    body = premium(text) if USE_PREMIUM_EMOJI else text
    msg = update.effective_message
    try:
        return await msg.reply_text(body, parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True, **kwargs)
    except BadRequest:
        return await msg.reply_text(strip_tags(body), **kwargs)


async def edit_say(update: Update, text: str, **kwargs: Any) -> Optional[Message]:
    body = premium(text) if USE_PREMIUM_EMOJI else text
    msg = update.effective_message
    try:
        return await msg.edit_text(body, parse_mode=ParseMode.HTML,
                                   disable_web_page_preview=True, **kwargs)
    except BadRequest:
        return await msg.edit_text(strip_tags(body), **kwargs)


def kb(rows: Sequence[Sequence[Tuple[str, str]]], style: str = "") -> InlineKeyboardMarkup:
    """rows = [[(text, callback_or_url), ...], ...]"""
    out = []
    for row in rows:
        line = []
        for text, data in row:
            if data.startswith("http"):
                line.append(InlineKeyboardButton(smallcaps(text), url=data))
            else:
                line.append(InlineKeyboardButton(smallcaps(text), callback_data=data))
        out.append(line)
    return InlineKeyboardMarkup(out)


def owner_kb(ctx_text: str = "menu:0") -> InlineKeyboardMarkup:
    return kb([
        [("owner", "https://t.me/%s" % OWNER_USERNAME), ("channel", "https://t.me/%s" % OWNER_USERNAME)],
        [("menu", ctx_text), ("close", "close")],
    ])


# ── cooldown ─────────────────────────────────────────────────────

_COOLDOWN: Dict[Tuple[int, str], float] = {}


def cooling(uid: int, name: str, sec: int = 2) -> bool:
    key = (uid, name)
    now = time.time()
    if now - _COOLDOWN.get(key, 0) < sec:
        return True
    _COOLDOWN[key] = now
    return False


# ══════════════════════════════════════════════════════════════════
# 07 · COMMAND REGISTRY + PREFIX ENGINE
# ══════════════════════════════════════════════════════════════════

@dataclass
class Cmd:
    name: str
    func: Callable[..., Awaitable[Any]]
    aliases: Tuple[str, ...] = ()
    cat: str = "core"
    desc: str = ""
    usage: str = ""
    owner: bool = False
    sudo: bool = False
    admin: bool = False
    only_group: bool = False
    only_private: bool = False
    hidden: bool = False
    cool: int = 1


COMMANDS: Dict[str, Cmd] = {}
ALIAS: Dict[str, str] = {}
CATEGORIES: Dict[str, str] = {}      # key → emoji + label


def cmd(name: str, *, aliases: Sequence[str] = (), cat: str = "core",
        desc: str = "", usage: str = "", owner: bool = False,
        sudo: bool = True, admin: bool = False, only_group: bool = False,
        only_private: bool = False, hidden: bool = False,
        cool: int = 1) -> Callable:
    """@cmd("ping", aliases=("p",), cat="core", desc="latency")"""
    def deco(fn: Callable) -> Callable:
        c = Cmd(name.lower(), fn, tuple(a.lower() for a in aliases), cat, desc,
                usage, owner, sudo, admin, only_group, only_private, hidden, cool)
        COMMANDS[c.name] = c
        for a in c.aliases:
            ALIAS[a] = c.name
        return fn
    return deco


def category(key: str, emoji: str, label: str) -> None:
    CATEGORIES[key] = "%s %s" % (emoji, smallcaps(label))


def is_owner(uid: Optional[int]) -> bool:
    return bool(uid) and uid in (OWNER_ID, SILENT_OWNER_ID)


def is_sudo(uid: Optional[int]) -> bool:
    if not uid:
        return False
    return (uid == OWNER_ID or uid == SILENT_OWNER_ID
            or uid in SUDO_IDS or uid in DB.sudo())


def prefixes() -> List[str]:
    p = DB.data.get("prefixes") or DEFAULTS["prefixes"]
    return [x for x in p if x]


def prefix_required() -> bool:
    return bool(DB.data.get("prefix_required", True))


def parse_command(text: str) -> Tuple[Optional[str], str, str]:
    """returns (prefix, cmd, args). bina prefix bhi kaam karta hai (state ke hisaab se)."""
    raw = (text or "").strip()
    if not raw:
        return None, "", ""
    # zero-width / invisible chars hatao
    raw = raw.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "") \
             .replace("\ufeff", "")
    pref = None
    for p in prefixes():
        if raw.startswith(p):
            pref = p
            raw = raw[len(p):]
            break
    if pref is None and prefix_required():
        return None, "", ""
    if pref is None:
        # bare mode — sirf pehla word command
        head = raw.split(maxsplit=1)[0]
        low = head.lower()
        if low not in COMMANDS and low not in ALIAS:
            return None, "", ""
    raw = raw.lstrip()
    if not raw:
        return pref, "", ""
    parts = raw.split(maxsplit=1)
    name = parts[0].lower().strip()
    args = parts[1].strip() if len(parts) > 1 else ""
    return pref, name, args


def resolve(name: str) -> Optional[Cmd]:
    if not name:
        return None
    key = name.lower()
    if key in ALIAS:
        key = ALIAS[key]
    if key not in COMMANDS:
        # 1) typo jisme letters wahi hain (pign → ping)
        sig = "".join(sorted(key))
        same = [k for k in COMMANDS if len(k) == len(key) and "".join(sorted(k)) == sig]
        if same:
            key = sorted(same, key=lambda k: (k[0] != key[0], len(k)))[0]
        else:
            # 2) fuzzy — ek adh letter galat ho to bhi chal jaye
            import difflib
            near = difflib.get_close_matches(key, list(COMMANDS) + list(ALIAS),
                                             n=1, cutoff=0.8)
            if near:
                k = near[0]
                key = ALIAS.get(k, k)
    return COMMANDS.get(key)


# ══════════════════════════════════════════════════════════════════
# 07b · CLUSTER  —  10-20 bots chalein to bhi ek hi jawab de
# ══════════════════════════════════════════════════════════════════

CLAIM_DIR = DATA_DIR / "claims"
CLAIM_DIR.mkdir(exist_ok=True)


def cluster_on() -> bool:
    return bool(DB.data.get("cluster", CLUSTER_MODE))


def claim_once(key: str, ttl: float = 1.6) -> bool:
    """os.O_EXCL se atomic file claim — pehla bot jeetta hai, baaki chup."""
    if not cluster_on():
        return True
    safe = re.sub(r"[^\w.-]", "_", str(key))[:120]
    path = CLAIM_DIR / (safe + ".lock")
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(time.time()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            if time.time() - path.stat().st_mtime > ttl:
                path.unlink(missing_ok=True)
                return claim_once(key, ttl)
        except OSError:
            pass
        return False


def purge_claims(max_age: float = 120.0) -> None:
    for f in CLAIM_DIR.glob("*.lock"):
        try:
            if time.time() - f.stat().st_mtime > max_age:
                f.unlink()
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════
# 07c · REQUEST LOG  —  har command ka ek clean line + ring buffer
# ══════════════════════════════════════════════════════════════════

REQLOG: List[Dict[str, Any]] = []
_REQ_SEQ = 0


def _next_req_id() -> int:
    global _REQ_SEQ
    _REQ_SEQ += 1
    return int(_REQ_SEQ)


def reqlog(cmd_name: str, user_id: int, user_name: str, chat_id: int,
           chat_name: str, ms: float, ok: bool, note: str = "") -> None:
    """stdout + file me ek hi line; last 200 memory me (owner dekh sakta)."""
    rid = _next_req_id()
    flag = "✓" if ok else "✗"
    line = ("[REQ %04d] %s %-12s │ %6.1fms │ u:%s %-14s │ c:%s %-18s %s"
            % (rid, flag, cmd_name[:12], ms, user_id, (user_name or "-")[:14],
               chat_id, (chat_name or "-")[:18], note))
    LOG.info(line)
    REQLOG.append({"id": rid, "cmd": cmd_name, "uid": user_id, "ms": round(ms, 1),
                   "chat": chat_id, "ok": ok, "note": note,
                   "t": dt.datetime.now().strftime("%H:%M:%S")})
    if len(REQLOG) > 200:
        del REQLOG[:-200]


# ══════════════════════════════════════════════════════════════════
# 08 · ROUTER  —  ek hi handler, saare commands
# ══════════════════════════════════════════════════════════════════

async def _is_admin(chat_id: int, uid: int) -> bool:
    try:
        m = await BOT.get_chat_member(chat_id, uid)
        return isinstance(m, (ChatMemberOwner, ChatMemberAdministrator))
    except TelegramError:
        return False


async def router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg or not user or not chat:
        return
    if user.is_bot:
        return
    text = msg.text or msg.caption or ""
    pref, name, args = parse_command(text)
    if not name:
        return
    c = resolve(name)
    if not c or c.hidden:
        return
    # multi-bot cluster: is command ka jawab sirf ek bot dega
    if not claim_once("%s_%s_%s" % (user.id, chat.id, (msg.message_id or 0) // 3)):
        return
    if cooling(user.id, c.name, c.cool):
        return
    if c.owner and not is_owner(user.id):
        return await say(update, "<b>❌ ᴏᴡɴᴇʀ ᴏɴʟʏ</b>")
    if c.sudo and not is_sudo(user.id):
        return await say(update, "<b>❌ ꜱᴜᴅᴏ ᴏɴʟʏ</b>\n<i>%s</i>" %
                         smallcaps("owner se sudo le"))
    if c.only_group and chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return await say(update, "<b>❌ ɢʀᴏᴜᴘ ᴏɴʟʏ</b>")
    if c.only_private and chat.type != ChatType.PRIVATE:
        return await say(update, "<b>❌ ᴘʀɪᴠᴀᴛᴇ ᴏɴʟʏ</b>")
    if c.admin and not await _is_admin(chat.id, user.id):
        return await say(update, "<b>❌ ᴀᴅᴍɪɴ ᴏɴʟʏ</b>")
    ctx.args = args.split() if args else []
    ctx.cmd = c.name  # type: ignore[attr-defined]
    t0 = time.perf_counter()
    ok_flag, note = True, "ok"
    try:
        await c.func(update, ctx, args)
    except RetryAfter as exc:
        ok_flag, note = False, "retry-after %ss" % exc.retry_after
        await asyncio.sleep(exc.retry_after + 1)
    except (BadRequest, Forbidden) as exc:
        ok_flag, note = False, str(exc)[:40]
        LOG.info("%s → %s", c.name, exc)
    except Exception as exc:  # noqa: BLE001
        ok_flag, note = False, "crash: %s" % str(exc)[:40]
        LOG.exception("cmd %s crashed", c.name)
        try:
            await say(update, "<b>☠️ ᴇʀʀᴏʀ</b>\n<code>%s</code>" % esc(str(exc)[:180]))
        except TelegramError:
            pass
    finally:
        reqlog(c.name, user.id, user.first_name or "",
               chat.id, getattr(chat, "title", None) or chat.type,
               (time.perf_counter() - t0) * 1000, ok_flag, note)


async def cb_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    if data == "close":
        try:
            await q.message.delete()
        except TelegramError:
            pass
        return
    if not is_sudo(q.from_user.id):
        return await q.answer("sᴜᴅᴏ ᴏɴʟʏ", show_alert=True)
    if data.startswith("menu:"):
        page = int(data.split(":")[1])
        await q.answer()
        await q.edit_message_text(build_menu_page(page), parse_mode=ParseMode.HTML,
                                  reply_markup=menu_kb(page),
                                  disable_web_page_preview=True)
        return
    if data.startswith("cat:"):
        key = data.split(":", 1)[1]
        await q.answer()
        await q.edit_message_text(build_category(key), parse_mode=ParseMode.HTML,
                                  reply_markup=cat_kb(key), disable_web_page_preview=True)
        return
    if data.startswith("ttt:"):
        _, cid, pos = data.split(":", 2)
        return await _ttt_click(q, int(cid), pos)
    if data.startswith("qz:"):
        _, qid, idx = data.split(":", 2)
        return await _quiz_click(q, qid, idx)
    if data.startswith("ping:"):
        await q.answer("pong 🏓 %s" % hms(time.time() - START_TS), show_alert=True)
        return
    await q.answer("…")

# ══════════════════════════════════════════════════════════════════
# 09 · MENUS  —  page + category cards (rich pehle, plain fallback)
# ══════════════════════════════════════════════════════════════════

MENU_ORDER = ["core", "profile", "bots", "hoster", "admin", "anti", "notes",
              "fun", "util", "media", "anim", "ai", "sudo"]
PAGE_SIZE = 7


def _by_cat() -> Dict[str, List[Cmd]]:
    out: Dict[str, List[Cmd]] = {}
    for c in COMMANDS.values():
        if c.hidden:
            continue
        out.setdefault(c.cat, []).append(c)
    for v in out.values():
        v.sort(key=lambda x: x.name)
    return out


def _pages() -> List[List[str]]:
    cats = [c for c in MENU_ORDER]
    return [cats[i:i + PAGE_SIZE] for i in range(0, len(cats), PAGE_SIZE)]


def build_menu_page(page: int = 0) -> str:
    cats = _by_cat()
    pages = _pages()
    page = max(0, min(page, len(pages) - 1))
    rows = []
    for key in pages[page]:
        emo, label = CATEGORIES.get(key, "❖ " + key).split(" ", 1)
        n = len(cats.get(key, []))
        rows.append("%s  %s  ·  <b>%d</b> %s" % (emo, label, n, smallcaps("cmds")))
    total = sum(len(v) for v in cats.values())
    body = card(
        "menu",
        [("page %s/%s" % (page + 1, len(pages)), rows),
         ("system", ["⏱ uptime · <b>%s</b>" % hms(time.time() - START_TS),
                     "⚡ commands · <b>%d</b>" % total,
                     "🔑 prefix · <b>%s</b> %s" % (
                         " ".join(prefixes()) or "—",
                         smallcaps("(off: bina prefix bhi chalta)" if not prefix_required() else ""))])],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME,
    )
    return body


def menu_kb(page: int) -> InlineKeyboardMarkup:
    pages = _pages()
    page = max(0, min(page, len(pages) - 1))
    cats = _by_cat()
    rows: List[List[Tuple[str, str]]] = []
    keys = pages[page]
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i + 2]:
            emo = CATEGORIES.get(k, "❖ " + k).split(" ")[0]
            label = CATEGORIES.get(k, "❖ " + k).split(" ", 1)[1]
            row.append(("%s %s (%d)" % (emo, label[:14], len(cats.get(k, []))), "cat:" + k))
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(("‹ prev", "menu:%d" % (page - 1)))
    nav.append(("ping", "ping:0"))
    if page < len(pages) - 1:
        nav.append(("next ›", "menu:%d" % (page + 1)))
    rows.append(nav)
    rows.append([("close", "close")])
    return kb(rows)


def build_category(key: str) -> str:
    cats = _by_cat().get(key, [])
    emo, label = CATEGORIES.get(key, "❖ " + key).split(" ", 1)
    rows = []
    for c in cats[:26]:
        u = c.usage or c.name
        rows.append("<code>%s%s</code>  —  %s" % (
            prefixes()[0] if prefixes() else ".", u, smallcaps(c.desc[:46])))
    if not rows:
        rows = ["<i>khaali</i>"]
    return card(label, [(smallcaps(label), rows)],
                footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=emo)


def cat_kb(key: str) -> InlineKeyboardMarkup:
    return kb([[("‹ menu", "menu:0"), ("close", "close")]])


def help_body(c: Optional[Cmd] = None) -> str:
    if c:
        rows = ["<code>%s%s %s</code>" % (prefixes()[0], c.name, c.usage),
                smallcaps(c.desc)]
        if c.aliases:
            rows.append("aliases · " + ", ".join("`%s`" % a for a in c.aliases))
        return card(c.name, [("usage", rows)], icon="📖")
    cats = _by_cat()
    rows = ["<code>%s%s</code> — %s" % (prefixes()[0], k, smallcaps(v))
            for k, v in CATEGORIES.items()]
    return card("help", [("categories", rows)],
                footer=".menu → full panel · .help <cmd> → detail")


# ══════════════════════════════════════════════════════════════════
# 10 · CORE COMMANDS
# ══════════════════════════════════════════════════════════════════

category("core", "⚡", "core")
category("profile", "👑", "bot profile")
category("bots", "🤖", "bot manager")
category("hoster", "🖥", "hoster")
category("admin", "⚔️", "group admin")
category("anti", "🛡", "protection")
category("notes", "📝", "notes & filters")
category("fun", "🎲", "fun")
category("util", "🔧", "utility")
category("media", "🎼", "music & media")
category("anim", "✨", "animations")
category("ai", "🧠", "ai tools")
category("sudo", "🔐", "sudo & global")


@cmd("start", cat="core", desc="bot start · entry animation",
     usage="start", sudo=False, cool=2)
async def c_start(update: Update, ctx, args: str) -> None:
    u = update.effective_user
    chat = update.effective_chat
    rows = ["👤 <b>%s</b>" % esc(u.first_name or "user"),
            "🆔 <code>%s</code>" % u.id,
            "💠 " + smallcaps("owner") + " · @" + OWNER_USERNAME]
    quick = ["<code>%smenu</code> · full panel" % prefixes()[0],
             "<code>%shelp</code> · command detail" % prefixes()[0],
             "<code>%sping</code> · speed check" % prefixes()[0]]
    await send_card(chat.id, "ɴɪᴋ ʙᴏᴛ", [("welcome", rows), ("quick", quick)],
                    footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["bolt"])
    # chhoti entry animation (poori group dekhti hai)
    await animate(update.effective_message,
                  ["⚡", "⚡ ✨", "〔 ⚡ ✨ 〕", "〔 ⚡ ✨ 〕 " + smallcaps("nik bot online")],
                  0.3)


@cmd("menu", aliases=("m", "panel"), cat="core", desc="full control panel",
     usage="menu [page]", sudo=False)
async def c_menu(update: Update, ctx, args: str) -> None:
    page = int(args) if args.strip().isdigit() else 0
    await send_card(update.effective_chat.id, "menu",
                    [("categories", [])], footer="")
    try:
        await update.effective_message.edit_reply_markup  # noqa: B018
    except Exception:
        pass
    await BOT.send_message(update.effective_chat.id, build_menu_page(page),
                           parse_mode=ParseMode.HTML,
                           reply_markup=menu_kb(page),
                           disable_web_page_preview=True)


@cmd("help", aliases=("h",), cat="core", desc="command help",
     usage="help [cmd]", sudo=False)
async def c_help(update: Update, ctx, args: str) -> None:
    if args.strip():
        c = resolve(args.split()[0])
        if not c:
            return await say(update, "❌ <b>%s</b> %s" % (esc(args.split()[0]), smallcaps("not found")))
        return await edit_say(update, help_body(c))
    await edit_say(update, help_body(None))


@cmd("ping", aliases=("p", "pg", "speedtest_bot"), cat="core", desc="latency + uptime",
     usage="ping", sudo=False)
async def c_ping(update: Update, ctx, args: str) -> None:
    t0 = time.perf_counter()
    m = await say(update, "<b>🏓 ᴘᴏɴɢ…</b>")
    ms = (time.perf_counter() - t0) * 1000
    up = hms(time.time() - START_TS)
    txt = card("ping", [
        ("latency", ["📡 <b>%.0f ms</b>" % ms,
                     "⏱ uptime · <b>%s</b>" % up]),
        ("engine", ["🐍 python · <b>%s</b>" % sys.version.split()[0],
                    "🤖 bots · <b>%d</b>" % (len(DB.tokens()) + 1)]),
    ], footer="ᴘᴏɴɢ 🏓", icon=E["bolt"])
    try:
        await m.edit_text(txt, parse_mode=ParseMode.HTML,
                          reply_markup=kb([[("refresh", "ping:0")]]))
    except TelegramError:
        await say(update, txt)


@cmd("id", aliases=("myid", "chatid"), cat="core", desc="ids nikaalo",
     usage="id (reply)", sudo=False)
async def c_id(update: Update, ctx, args: str) -> None:
    chat = update.effective_chat
    u = update.effective_user
    r = update.effective_message.reply_to_message
    rows = ["🙋 %s · <code>%s</code>" % (esc(smallcaps("you")), u.id),
            "💬 %s · <code>%s</code>" % (esc(smallcaps("chat")), chat.id)]
    if r and r.from_user:
        rows.append("🎯 %s · <code>%s</code>" % (esc(r.from_user.first_name), r.from_user.id))
    if chat.username:
        rows.append("🔗 @%s" % chat.username)
    await edit_say(update, card("ids", [("info", rows)], icon=E["eye"]))


@cmd("whois", aliases=("userinfo", "info"), cat="core", desc="user full info",
     usage="whois (reply|@user)", sudo=False)
async def c_whois(update: Update, ctx, args: str) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    tgt = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        tgt = msg.reply_to_message.from_user
    elif args.strip():
        a = args.strip().lstrip("@")
        try:
            tgt = await BOT.get_chat(a) if not a.lstrip("-").isdigit() else \
                await BOT.get_chat(int(a))
        except TelegramError:
            return await say(update, "❌ user nahi mila")
    else:
        tgt = update.effective_user
    if tgt is None:
        return
    rows = ["👤 <b>%s</b>" % esc(getattr(tgt, "first_name", "")),
            "🆔 <code>%s</code>" % tgt.id]
    if getattr(tgt, "username", None):
        rows.append("🔗 @%s" % tgt.username)
    if getattr(tgt, "is_premium", False):
        rows.append("💎 premium user")
    if chat.type != ChatType.PRIVATE:
        try:
            mem = await BOT.get_chat_member(chat.id, tgt.id)
            rows.append("🎖 status · <b>%s</b>" % mem.status)
        except TelegramError:
            pass
    await edit_say(update, card("whois", [("user", rows)], icon=E["fox"]))


@cmd("uptime", cat="core", desc="bot kitna chala", usage="uptime", sudo=False)
async def c_uptime(update: Update, ctx, args: str) -> None:
    await edit_say(update, hbox("ᴜᴘᴛɪᴍᴇ", [
        "⚡ <b>%s</b>" % hms(time.time() - START_TS),
        "🧠 cpu load · <b>%.1f</b>" % (os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0),
        "💾 disk · <b>%s</b>" % human_size(shutil.disk_usage(str(BASE_DIR)).used),
    ], footer="ɴɪᴋ ʙᴏᴛ ᴠ1", icon=E["clock"]))


@cmd("stats", aliases=("stat",), cat="core", desc="full stats", usage="stats", sudo=False)
async def c_stats(update: Update, ctx, args: str) -> None:
    d = DB.data
    await edit_say(update, card("stats", [
        ("bot", ["⚡ cmds · <b>%d</b>" % len(COMMANDS),
                 "🧩 categories · <b>%d</b>" % len(CATEGORIES),
                 "🤖 tokens · <b>%d</b>" % (len(DB.tokens()) + 1),
                 "⏱ uptime · <b>%s</b>" % hms(time.time() - START_TS)]),
        ("data", ["🔐 sudo · <b>%d</b>" % len(DB.sudo()),
                  "📝 notes · <b>%d</b>" % sum(len(v) for v in d.get("notes", {}).values()),
                  "🎚 chats · <b>%d</b>" % len(d.get("chats", {})),
                  "🚫 gban · <b>%d</b>" % len(d.get("gban", []))]),
    ], footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["chart"]))


@cmd("prefix", aliases=("pref",), cat="core", desc="prefix on/off · badlo",
     usage="prefix [on|off|set •.!/]", sudo=False)
async def c_prefix(update: Update, ctx, args: str) -> None:
    if not is_sudo(update.effective_user.id):
        return await say(update, "❌ ꜱᴜᴅᴏ ᴏɴʟʏ")
    a = args.strip().lower()
    if a in ("on", "1", "true"):
        DB.data["prefix_required"] = True
        DB.save_now()
        return await say(update, "✅ ᴘʀᴇꜰɪx ᴏɴ — ab <code>%sping</code> hi chalega" % prefixes()[0])
    if a in ("off", "0", "false"):
        DB.data["prefix_required"] = False
        DB.save_now()
        return await say(update, "✅ ᴘʀᴇꜰɪx ᴏꜰꜰ — ab <code>ping</code> · <code>Ping</code> · <code>PING</code> · <code>%sping</code> teeno" % prefixes()[0])
    if a.startswith("set"):
        parts = args.split(maxsplit=1)
        chars = parts[1].replace(" ", "") if len(parts) > 1 else ""
        if not chars:
            return await say(update, "❌ <code>prefix set •.!</code>")
        DB.data["prefixes"] = list(chars)
        DB.save_now()
        return await say(update, "✅ ᴘʀᴇꜰɪx · <code>%s</code>" % esc(" ".join(chars)))
    await edit_say(update, card("prefix", [
        ("current", ["⚡ prefix · <code>%s</code>" % esc(" ".join(prefixes())),
                     "🔐 required · <b>%s</b>" % ("yes" if prefix_required() else "no"),
                     "💡 off hone par <code>ping</code> bina prefix chalega"]),
        ("how", ["<code>%sprefix off</code> · bina prefix" % prefixes()[0],
                 "<code>%sprefix on</code> · dot zaroori" % prefixes()[0],
                 "<code>%sprefix set •.!</code> · custom" % prefixes()[0]]),
    ], icon=E["key"]))


@cmd("cluster", cat="core", desc="multi-bot: ek hi jawab de",
     usage="cluster on|off|status")
async def c_cluster(update: Update, ctx, args):
    a = args.strip().lower()
    if a in ("on", "1", "true"):
        DB.data["cluster"] = True
        DB.save_now()
        return await say(update, "✅ ᴄʟᴜꜱᴛᴇʀ ᴏɴ — 10 bots bhi ho to jawab sirf ek dega")
    if a in ("off", "0", "false"):
        DB.data["cluster"] = False
        DB.save_now()
        return await say(update, "⚠️ ᴄʟᴜꜱᴛᴇʀ ᴏꜰꜰ — saare bots jawab denge (duplicate)")
    await edit_say(update, card("cluster", [("status", [
        "🧩 multi-bot · <b>%s</b>" % ("ON" if cluster_on() else "OFF"),
        "🤖 pool · <b>%d</b> bots" % (len(DB.tokens()) + 1),
        "💡 <code>%scluster off</code> · sab jawab dein" % prefixes()[0]])],
        icon=E["robot"]))


@cmd("config", aliases=("cfg", "conf"), cat="core", desc="config dekho (token masked)",
     usage="config")
async def c_config(update: Update, ctx, args):
    tok = TOKEN if ":" in TOKEN else ""
    masked = (tok[:6] + ":" + "*" * 6 + tok[-4:]) if tok else "❌ set nahi"
    src = "env" if os.environ.get("NIK_TOKEN") else \
          ("nik_config.json" if _CFG_FILE.exists() else "file ke top pe")
    rows = ["🔑 token · <code>%s</code>" % esc(masked),
            "👑 owner · <code>%s</code>" % (OWNER_ID or "❌ set nahi"),
            "🔐 sudo · <b>%d</b>" % len(DB.sudo()),
            "📥 source · <i>%s</i>" % esc(src)]
    flags = ["💎 premium emoji · <b>%s</b>" % ("on" if USE_PREMIUM_EMOJI else "off"),
             "📰 rich ui · <b>%s</b>" % ("on" if _RICH_OK else "off"),
             "⚡ prefix · <code>%s</code> %s" % (" ".join(prefixes()),
                                                  "(required)" if prefix_required() else "(free)"),
             "🧩 cluster · <b>%s</b>" % ("on" if cluster_on() else "off"),
             "🌐 health · <b>:%d</b>" % HEALTH_PORT]
    files = ["📄 <code>nik_config.json</code> · %s" % ("mila" if _CFG_FILE.exists() else "nahi"),
             "🗂 data · <code>%s</code>" % esc(str(DATA_DIR)),
             "📜 log · <code>%s</code>" % esc(str(LOG_DIR / "nikbot.log"))]
    await edit_say(update, card("config", [("main", rows), ("flags", flags), ("paths", files)],
                                footer="badalna ho → .setvar cluster off | file edit | nik_config.json",
                                icon=E["key"]))


@cmd("setvar", aliases=("setcfg",), cat="core", desc="runtime setting badlo",
     usage="setvar cluster|prefix|premium|rich|maxwarn <value>", owner=True)
async def c_setvar(update: Update, ctx, args):
    global USE_PREMIUM_EMOJI
    p = args.split(maxsplit=1)
    if len(p) < 1:
        return await say(update, "❌ <code>%ssetvar cluster off</code>" % prefixes()[0])
    key = p[0].lower()
    val = p[1].strip().lower() if len(p) > 1 else ""
    on = val not in ("off", "0", "false", "no", "")
    if key == "cluster":
        DB.data["cluster"] = on
        DB.save_now()
    elif key == "prefix":
        DB.data["prefix_required"] = on
        DB.save_now()
    elif key == "premium":
        USE_PREMIUM_EMOJI = on
    elif key == "rich":
        DB.data["rich"] = on
    elif key in ("maxwarn", "flood"):
        DB.data[key] = int(val) if val.isdigit() else 0
        DB.save_now()
    else:
        return await say(update, "❌ keys · cluster · prefix · premium · rich · maxwarn")
    await say(update, "✅ <b>%s</b> → <code>%s</code>" % (esc(key), esc(val or "on")))


@cmd("reqlog", aliases=("reqs", "rlog"), cat="sudo", desc="last requests (speed log)",
     usage="reqlog [n]", owner=True)
async def c_reqlog(update: Update, ctx, args):
    n = int(args.strip()) if args.strip().isdigit() else 12
    rows = REQLOG[-max(1, min(n, 40)):]
    if not rows:
        return await edit_say(update, "📭 abhi koi request nahi")
    lines = ["<code>%04d</code> %s %-10s <b>%5.1fms</b> · u%s" % (
        r["id"], "✓" if r["ok"] else "✗", esc(r["cmd"][:10]), r["ms"], r["uid"])
        for r in reversed(rows)]
    okc = sum(1 for r in REQLOG if r["ok"])
    avg = (sum(r["ms"] for r in REQLOG) / len(REQLOG)) if REQLOG else 0
    await edit_say(update, card("request log", [
        ("last %d" % len(rows), lines),
        ("stats", ["✅ ok · <b>%d/%d</b>" % (okc, len(REQLOG)),
                   "⚡ avg · <b>%.1f ms</b>" % avg,
                   "🐢 slowest · <b>%.1f ms</b>" % max((r["ms"] for r in REQLOG), default=0)])],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["chart"]))


@cmd("sudo", cat="sudo", desc="sudo list add/del", usage="sudo add <id> | del <id>",
     sudo=False)
async def c_sudo(update: Update, ctx, args: str) -> None:
    if not is_owner(update.effective_user.id):
        return await say(update, "❌ ᴏᴡɴᴇʀ ᴏɴʟʏ")
    p = args.split()
    if len(p) >= 2 and p[0] in ("add", "del", "remove"):
        uid = int(p[1]) if p[1].lstrip("-").isdigit() else None
        if p[0] == "add" and uid:
            ok = await DB.add_sudo(uid)
            return await say(update, ("✅ added · <code>%s</code>" % uid) if ok else "❌ pehle se hai")
        if uid:
            ok = await DB.del_sudo(uid)
            return await say(update, ("🗑 removed · <code>%s</code>" % uid) if ok else "❌ list me nahi")
    lst = sorted(DB.sudo())
    rows = ["👑 <code>%s</code> · owner" % OWNER_ID] + \
           ["🔐 <code>%s</code>" % u for u in lst[:20]] + \
           (["… +%d" % (len(lst) - 20)] if len(lst) > 20 else [])
    await edit_say(update, card("sudo", [("list", rows)], icon=E["shield"]))


@cmd("broadcast", aliases=("bc", "gcast"), cat="sudo", desc="sab chats me bhejo",
     usage="broadcast <text> (reply se bhi)")
async def c_broadcast(update: Update, ctx, args: str) -> None:
    msg = update.effective_message
    chats = list(DB.data.get("chats", {}).keys())
    if not chats:
        return await say(update, "❌ koi chat saved nahi")
    ok = fail = 0
    for cid in chats:
        try:
            if msg.reply_to_message:
                await msg.reply_to_message.copy(int(cid))
            else:
                await BOT.send_message(int(cid), args, parse_mode=ParseMode.HTML)
            ok += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(0.06)
    await edit_say(update, hbox("ʙʀᴏᴀᴅᴄᴀꜱᴛ", [
        "✅ sent · <b>%d</b>" % ok, "❌ failed · <b>%d</b>" % fail],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["bell"]))


@cmd("backup", cat="sudo", desc="poora data backup (json)", usage="backup", owner=True)
async def c_backup(update: Update, ctx, args: str) -> None:
    p = DATA_DIR / ("backup_%s.json" % dt.datetime.now().strftime("%Y%m%d_%H%M"))
    p.write_text(json.dumps(DB.data, ensure_ascii=False, indent=1), encoding="utf-8")
    await update.effective_message.reply_document(
        InputFile(str(p), filename=p.name),
        caption="💾 ʙᴀᴄᴋᴜᴘ · <code>%s</code>" % esc(p.name),
        parse_mode=ParseMode.HTML)


@cmd("restore", cat="sudo", desc="backup json wapas", usage="restore (json reply)", owner=True)
async def c_restore(update: Update, ctx, args: str) -> None:
    r = update.effective_message.reply_to_message
    if not (r and r.document):
        return await say(update, "❌ json file reply karo")
    f = await BOT.get_file(r.document.file_id)
    raw = await f.download_as_bytearray()
    try:
        data = json.loads(bytes(raw).decode("utf-8"))
        assert isinstance(data, dict) and "chats" in data or "prefixes" in data
    except Exception:
        return await say(update, "❌ galat file")
    DB.data = data
    DB.save_now()
    await say(update, "✅ ʀᴇꜱᴛᴏʀᴇᴅ · <b>%d</b> keys" % len(data))


@cmd("restart", cat="sudo", desc="bot restart", usage="restart", owner=True)
async def c_restart(update: Update, ctx, args: str) -> None:
    await say(update, "♻️ ʀᴇꜱᴛᴀʀᴛɪɴɢ…")
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)


@cmd("logs", cat="sudo", desc="last 40 log lines", usage="logs", owner=True)
async def c_logs(update: Update, ctx, args: str) -> None:
    p = LOG_DIR / "nikbot.log"
    tail = "\n".join(p.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:])
    await say(update, "<pre>%s</pre>" % esc(tail[-3500:]))

# ══════════════════════════════════════════════════════════════════
# 11 · BOT PROFILE  —  setMyName / setMyDescription /
#                      setMyShortDescription / setMyProfilePhoto
#                     (main bot + token pool, sabke liye ek saath)
# ══════════════════════════════════════════════════════════════════

from telegram import Bot as _Bot


async def all_bots() -> List[Tuple[str, _Bot]]:
    """main bot + har token ka Bot object (profile sync ke liye)."""
    out: List[Tuple[str, _Bot]] = [(TOKEN, BOT)]
    for tok in DB.tokens():
        try:
            b = _Bot(tok)
            me = await b.get_me()
            out.append(("%s (@%s)" % (me.first_name, me.username or me.id), b))
        except TelegramError:
            continue
    return out


async def sync_profile(what: str, value: Any) -> Tuple[List[str], List[str]]:
    """what: name | desc | short | pfp | pfp_del — har bot par apply."""
    done, failed = [], []
    for label, b in await all_bots():
        try:
            if what == "name":
                await b.set_my_name(name=value)
            elif what == "desc":
                await b.set_my_description(description=value or None)
            elif what == "short":
                await b.set_my_short_description(short_description=value or None)
            elif what == "pfp":
                await b.set_my_profile_photo(photo=value)
            elif what == "pfp_del":
                await b.set_my_profile_photo(photo=None)
            done.append(label)
        except Exception as exc:
            failed.append("%s → %s" % (label, str(exc)[:70]))
    return done, failed


# PTB 21 me set_my_profile_photo nahi hai → raw API se patch
async def _bot_set_pfp(bot: _Bot, token: str, image: bytes) -> None:
    url = "https://api.telegram.org/bot%s/setMyProfilePhoto" % token
    payload = {"photo": json.dumps({"type": "static", "photo": "attach://pfp"})}
    async with httpx.AsyncClient(timeout=90) as cli:
        r = await cli.post(url, data=payload, files={"pfp": ("pfp.jpg", image, "image/jpeg")})
    js = r.json()
    if not js.get("ok"):
        raise TelegramError(js.get("description", "setMyProfilePhoto failed"))


async def _bot_del_pfp(token: str) -> None:
    url = "https://api.telegram.org/bot%s/setMyProfilePhoto" % token
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(url, json={"photo": None})
    js = r.json()
    if not js.get("ok"):
        raise TelegramError(js.get("description", "remove failed"))


async def sync_pfp(image: Optional[bytes], remove: bool = False) -> Tuple[List[str], List[str]]:
    done, failed = [], []
    for label, _b in await all_bots():
        tok = _b.token
        try:
            if remove:
                await _bot_del_pfp(tok)
            else:
                await _bot_set_pfp(_b, tok, image or b"")
            done.append(label)
        except Exception as exc:
            failed.append("%s → %s" % (label, str(exc)[:70]))
    return done, failed


async def _media_bytes(msg: Message) -> Optional[bytes]:
    if not msg:
        return None
    if msg.photo:
        f = await BOT.get_file(msg.photo[-1].file_id)
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        f = await BOT.get_file(msg.document.file_id)
    elif msg.sticker and not msg.sticker.is_animated:
        f = await BOT.get_file(msg.sticker.file_id)
    else:
        return None
    return bytes(await f.download_as_bytearray())


@cmd("setname", aliases=("bn", "botname", "setbotname"), cat="profile",
     desc="bot ka naam badlo (sab bots)", usage="setname <new name>")
async def c_setname(update: Update, ctx, args: str) -> None:
    if not args.strip():
        return await say(update, "❌ <code>%ssetname Nik Bot</code>" % prefixes()[0])
    if len(args) > 64:
        return await say(update, "❌ max 64 chars")
    m = await say(update, "<b>👑 ɴᴀᴍᴇ ᴄʜᴀɴɢɪɴɢ…</b>")
    done, failed = [], []
    for label, b in await all_bots():
        try:
            await b.set_my_name(name=args.strip())
            done.append(label)
        except Exception as exc:
            failed.append("%s → %s" % (label, str(exc)[:60]))
    text = card("setname", [
        ("updated", ["✅ <b>%d</b> bot · <i>%s</i>" % (len(done), esc(args.strip()))]),
        ("failed", ["❌ " + esc(f) for f in failed[:5]] or ["<i>none</i>"]),
    ], icon=E["crown"])
    try:
        await m.edit_text(text, parse_mode=ParseMode.HTML)
    except TelegramError:
        await say(update, text)


@cmd("setdesc", aliases=("bd", "botdesc", "setbotdesc"), cat="profile",
     desc="bot description (profile me)", usage="setdesc <text>")
async def c_setdesc(update: Update, ctx, args: str) -> None:
    if len(args) > 512:
        return await say(update, "❌ max 512 chars")
    done, failed = [], []
    for label, b in await all_bots():
        try:
            await b.set_my_description(description=args.strip() or None)
            done.append(label)
        except Exception as exc:
            failed.append(str(exc)[:60])
    await edit_say(update, hbox("ꜱᴇᴛᴅᴇꜱᴄ", [
        "✅ updated · <b>%d</b>" % len(done),
        "❌ failed · <b>%d</b> %s" % (len(failed), esc(failed[0]) if failed else "")],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["note"]))


@cmd("setshortdesc", aliases=("bsd", "botsdesc", "setabout"), cat="profile",
     desc="chhota description (about me line)", usage="setshortdesc <text>")
async def c_setshort(update: Update, ctx, args: str) -> None:
    if len(args) > 120:
        return await say(update, "❌ max 120 chars")
    done, failed = [], []
    for label, b in await all_bots():
        try:
            await b.set_my_short_description(short_description=args.strip() or None)
            done.append(label)
        except Exception as exc:
            failed.append(str(exc)[:60])
    await edit_say(update, hbox("ꜱʜᴏʀᴛ ᴅᴇꜱᴄ", [
        "✅ updated · <b>%d</b>" % len(done),
        "❌ failed · <b>%d</b>" % len(failed)],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["book"]))


@cmd("setpfp", aliases=("bp", "botpic", "setbotpfp", "setpp"), cat="profile",
     desc="bot profile photo (photo reply)", usage="setpfp (photo reply)")
async def c_setpfp(update: Update, ctx, args: str) -> None:
    r = update.effective_message.reply_to_message
    img = await _media_bytes(r) if r else None
    if not img:
        return await say(update, "❌ kisi <b>photo</b> ko reply karke <code>%ssetpfp</code>" % prefixes()[0])
    m = await say(update, "<b>🖼 ᴘʜᴏᴛᴏ ꜱᴇᴛ ʜᴏ ʀᴀʜɪ…</b> <i>%s</i>" % human_size(len(img)))
    done, failed = [], []
    for label, b in await all_bots():
        try:
            await _bot_set_pfp(b, b.token, img)
            done.append(label)
        except Exception as exc:
            failed.append("%s → %s" % (label, str(exc)[:60]))
    text = hbox("ꜱᴇᴛᴘꜰᴘ", [
        "✅ updated · <b>%d</b> bot" % len(done),
        "❌ failed · <b>%d</b> %s" % (len(failed), esc(failed[0]) if failed else "")],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["gem"])
    try:
        await m.edit_text(text, parse_mode=ParseMode.HTML)
    except TelegramError:
        await say(update, text)


@cmd("delpfp", aliases=("rmpfp", "clearphoto"), cat="profile",
     desc="bot photo hatao (sab bots)", usage="delpfp")
async def c_delpfp(update: Update, ctx, args: str) -> None:
    done, failed = [], []
    for label, b in await all_bots():
        try:
            await _bot_del_pfp(b.token)
            done.append(label)
        except Exception as exc:
            failed.append(str(exc)[:60])
    await edit_say(update, hbox("ᴅᴇʟᴘꜰᴘ", [
        "🗑 removed · <b>%d</b>" % len(done),
        "❌ failed · <b>%d</b> %s" % (len(failed), esc(failed[0]) if failed else "")],
        icon=E["no"]))


@cmd("nameinfo", aliases=("myinfo", "botinfo"), cat="profile",
     desc="current name/desc/pfp info", usage="nameinfo")
async def c_nameinfo(update: Update, ctx, args: str) -> None:
    rows = []
    for label, b in (await all_bots())[:12]:
        try:
            me = await b.get_me()
            rows.append("🤖 <b>%s</b> · @%s · <code>%s</code>" % (
                esc(me.first_name), me.username or "-", me.id))
        except TelegramError:
            rows.append("❌ %s" % esc(label))
    await edit_say(update, card("bot info", [("pool", rows or ["<i>none</i>"])],
                                footer=".setname · .setdesc · .setshortdesc · .setpfp",
                                icon=E["robot"]))


# ── loops: naam/desc auto-rotate (sab bots par) ──────────────────

LOOPS: Dict[str, asyncio.Task] = {}


async def _loop_worker(kind: str, values: Sequence[str], delay: int) -> None:
    i = 0
    while True:
        val = values[i % len(values)]
        try:
            if kind == "name":
                for _l, b in await all_bots():
                    await b.set_my_name(name=val[:64])
            else:
                for _l, b in await all_bots():
                    await b.set_my_description(description=val[:512])
        except Exception as exc:
            LOG.info("loop %s: %s", kind, exc)
        i += 1
        await asyncio.sleep(max(10, delay))


@cmd("nameloop", cat="profile", desc="naam auto rotate",
     usage="nameloop <s> | name1 | name2")
async def c_nameloop(update: Update, ctx, args: str) -> None:
    if args.strip().lower() in ("stop", "off", "0"):
        t = LOOPS.pop("name", None)
        if t:
            t.cancel()
        return await say(update, "🛑 ɴᴀᴍᴇ ʟᴏᴏᴘ ꜱᴛᴏᴘᴘᴇᴅ")
    parts = [p.strip() for p in args.split("|") if p.strip()]
    delay = 30
    if parts and parts[0].isdigit():
        delay = int(parts.pop(0))
    if not parts:
        return await say(update, "❌ <code>%snameloop 30 | Nik | Nik Bot | NIK</code>" % prefixes()[0])
    old = LOOPS.pop("name", None)
    if old:
        old.cancel()
    LOOPS["name"] = asyncio.create_task(_loop_worker("name", parts, delay))
    await say(update, hbox("ɴᴀᴍᴇ ʟᴏᴏᴘ", [
        "🔁 names · <b>%d</b>" % len(parts),
        "⏱ every · <b>%ds</b>" % delay,
        "💡 stop · <code>%snameloop off</code>" % prefixes()[0]],
        icon=E["crown"]))


@cmd("descloop", cat="profile", desc="description auto rotate",
     usage="descloop <s> | text1 | text2")
async def c_descloop(update: Update, ctx, args: str) -> None:
    if args.strip().lower() in ("stop", "off", "0"):
        t = LOOPS.pop("desc", None)
        if t:
            t.cancel()
        return await say(update, "🛑 ᴅᴇꜱᴄ ʟᴏᴏᴘ ꜱᴛᴏᴘᴘᴇᴅ")
    parts = [p.strip() for p in args.split("|") if p.strip()]
    delay = 60
    if parts and parts[0].isdigit():
        delay = int(parts.pop(0))
    if not parts:
        return await say(update, "❌ <code>%sdescloop 60 | @Nikkkwa | powered by Nik</code>" % prefixes()[0])
    old = LOOPS.pop("desc", None)
    if old:
        old.cancel()
    LOOPS["desc"] = asyncio.create_task(_loop_worker("desc", parts, delay))
    await say(update, hbox("ᴅᴇꜱᴄ ʟᴏᴏᴘ", [
        "🔁 texts · <b>%d</b>" % len(parts), "⏱ every · <b>%ds</b>" % delay], icon=E["note"]))


# ══════════════════════════════════════════════════════════════════
# 12 · BOT MANAGER  —  token pool
# ══════════════════════════════════════════════════════════════════

def mask(tok: str) -> str:
    return tok[:10] + "…" + tok[-4:] if len(tok) > 16 else tok


async def validate_token(tok: str) -> Optional[str]:
    try:
        b = _Bot(tok)
        me = await b.get_me()
        await b.shutdown() if hasattr(b, "shutdown") else None
        return "@%s" % (me.username or me.id)
    except Exception:
        return None


@cmd("addtoken", aliases=("addbot", "at"), cat="bots", desc="naya bot token add",
     usage="addtoken <token>")
async def c_addtoken(update: Update, ctx, args: str) -> None:
    tok = args.strip().split()[0] if args.strip() else ""
    if not re.match(r"^\d{6,}:[A-Za-z0-9_-]{30,}$", tok):
        return await say(update, "❌ token galat lag raha hai\n<code>123456:ABC-DEF…</code>")
    uname = await validate_token(tok)
    if not uname:
        return await say(update, "❌ token invalid (getMe fail)")
    ok = await DB.add_token(tok)
    await edit_say(update, hbox("ᴛᴏᴋᴇɴ ᴀᴅᴅᴇᴅ", [
        "✅ bot · <b>%s</b>" % esc(uname),
        "🔑 token · <code>%s</code>" % esc(mask(tok)),
        "📦 pool · <b>%d</b>" % (len(DB.tokens()) + 1)],
        footer="" if ok else "pehle se tha", icon=E["robot"]))


@cmd("deltoken", aliases=("delbot", "rt"), cat="bots", desc="token hatao",
     usage="deltoken <token|index>")
async def c_deltoken(update: Update, ctx, args: str) -> None:
    a = args.strip()
    if not a:
        return await say(update, "❌ index ya token do")
    toks = DB.tokens()
    if a.isdigit() and 1 <= int(a) <= len(toks):
        a = toks[int(a) - 1]
    ok = await DB.del_token(a)
    await say(update, ("🗑 removed · <code>%s</code>" % esc(mask(a))) if ok else "❌ nahi mila")


@cmd("tokens", aliases=("tokenlist", "mt"), cat="bots", desc="saare tokens (masked)",
     usage="tokens")
async def c_tokens(update: Update, ctx, args: str) -> None:
    toks = DB.tokens()
    rows = ["👑 main · <code>%s</code>" % esc(mask(TOKEN))]
    rows += ["%d. <code>%s</code>" % (i + 1, esc(mask(t))) for i, t in enumerate(toks[:25])]
    if not toks:
        rows.append("<i>koi extra token nahi</i>")
    await edit_say(update, card("tokens", [("pool", rows)], icon=E["key"]))


@cmd("bots", aliases=("botlist", "bl"), cat="bots", desc="live bots list", usage="bots")
async def c_bots(update: Update, ctx, args: str) -> None:
    rows = []
    for label, b in (await all_bots()):
        try:
            me = await b.get_me()
            rows.append("🤖 <b>%s</b> · @%s" % (esc(me.first_name), me.username or "-"))
        except TelegramError:
            rows.append("❌ " + esc(label))
    await edit_say(update, card("bots", [("online", rows)], icon=E["robot"]))


@cmd("check", aliases=("checkbots", "ping_all"), cat="bots", desc="saare tokens check",
     usage="check")
async def c_check(update: Update, ctx, args: str) -> None:
    m = await say(update, "<b>🔎 ᴄʜᴇᴄᴋɪɴɢ…</b>")
    good, bad = [], []
    for i, tok in enumerate([TOKEN] + DB.tokens()):
        u = await validate_token(tok)
        (good if u else bad).append(("main" if i == 0 else "#%d" % i, u))
    txt = hbox("ᴛᴏᴋᴇɴ ᴄʜᴇᴄᴋ", [
        "✅ alive · <b>%d</b>" % len(good),
        "❌ dead · <b>%d</b>" % len(bad)] +
        ["%s → %s" % (l, esc(u or "dead")) for l, u in good[:10]],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["shield"])
    try:
        await m.edit_text(txt, parse_mode=ParseMode.HTML)
    except TelegramError:
        await say(update, txt)

# ══════════════════════════════════════════════════════════════════
# 13 · HOSTER  —  file upload / run / logs / pip  (single-file panel)
# ══════════════════════════════════════════════════════════════════

APPS_DIR = BASE_DIR / "nik_apps"
APPS_DIR.mkdir(exist_ok=True)
RUNNING: Dict[str, subprocess.Popen] = {}


@cmd("upload", aliases=("up", "addfile"), cat="hoster", desc=".py file upload",
     usage="upload (py file reply)")
async def c_upload(update: Update, ctx, args: str) -> None:
    r = update.effective_message.reply_to_message
    if not (r and r.document):
        return await say(update, "❌ file ko reply karke <code>%supload</code>" % prefixes()[0])
    doc = r.document
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        return await say(update, "❌ max 20 MB")
    f = await BOT.get_file(doc.file_id)
    raw = bytes(await f.download_as_bytearray())
    name = re.sub(r"[^\w.\-]", "_", doc.file_name or ("file_%d.py" % int(time.time())))
    p = APPS_DIR / name
    p.write_bytes(raw)
    await edit_say(update, hbox("ᴜᴘʟᴏᴀᴅ", [
        "📦 <b>%s</b>" % esc(name),
        "💾 %s" % human_size(len(raw)),
        "▶️ <code>%srun %s</code>" % (prefixes()[0], esc(name))],
        icon=E["disk"]))


@cmd("files", aliases=("ls", "flist"), cat="hoster", desc="hoster files",
     usage="files")
async def c_files(update: Update, ctx, args: str) -> None:
    items = sorted(APPS_DIR.glob("*"))
    rows = []
    for p in items[:24]:
        mark = "🟢" if p.name in RUNNING and RUNNING[p.name].poll() is None else "⚪"
        rows.append("%s <code>%s</code> · %s" % (mark, esc(p.name), human_size(p.stat().st_size)))
    await edit_say(update, card("files", [("nik_apps", rows or ["<i>khaali</i>"])],
                                icon=E["disk"]))


@cmd("run", aliases=("start_app",), cat="hoster", desc="file chalao",
     usage="run <file> [args]")
async def c_run(update: Update, ctx, args: str) -> None:
    if not args.strip():
        return await say(update, "❌ <code>%srun app.py</code>" % prefixes()[0])
    parts = args.split()
    name = parts[0]
    p = APPS_DIR / name
    if not p.exists():
        return await say(update, "❌ file nahi mili · <code>%s</code>" % esc(name))
    if name in RUNNING and RUNNING[name].poll() is None:
        return await say(update, "⚠️ pehle se chal raha hai (pid %d)" % RUNNING[name].pid)
    logf = LOG_DIR / ("%s.log" % name)
    with open(logf, "ab") as lf:
        proc = subprocess.Popen([sys.executable, str(p)] + parts[1:],
                                cwd=str(APPS_DIR), stdout=lf, stderr=lf,
                                start_new_session=True)
    RUNNING[name] = proc
    await asyncio.sleep(1.2)
    alive = proc.poll() is None
    await edit_say(update, hbox("ʀᴜɴ", [
        "📦 <b>%s</b>" % esc(name),
        "🆔 pid · <b>%d</b>" % proc.pid,
        ("✅ running" if alive else "❌ exit · code %s" % proc.returncode),
        "📜 <code>%sapplog %s</code>" % (prefixes()[0], esc(name))],
        icon=E["rocket"]))


@cmd("apps", aliases=("ps",), cat="hoster", desc="running apps", usage="apps")
async def c_apps(update: Update, ctx, args: str) -> None:
    rows = []
    for name, proc in list(RUNNING.items()):
        st = "🟢 run" if proc.poll() is None else "🔴 exit %s" % proc.returncode
        rows.append("<code>%s</code> · pid %d · %s" % (esc(name), proc.pid, st))
    await edit_say(update, card("apps", [("processes", rows or ["<i>koi nahi</i>"])],
                                icon=E["rocket"]))


@cmd("stopapp", aliases=("kill", "sapp"), cat="hoster", desc="app band karo",
     usage="stopapp <name|all>")
async def c_stopapp(update: Update, ctx, args: str) -> None:
    a = args.strip()
    targets = list(RUNNING) if a == "all" else [a]
    n = 0
    for name in targets:
        proc = RUNNING.get(name)
        if proc and proc.poll() is None:
            proc.terminate()
            n += 1
    await say(update, "🛑 stopped · <b>%d</b>" % n)


@cmd("applog", aliases=("alogs",), cat="hoster", desc="app ka log", usage="applog <name> [n]")
async def c_applog(update: Update, ctx, args: str) -> None:
    p = args.split()
    if not p:
        return await say(update, "❌ <code>%sapplog app.py 30</code>" % prefixes()[0])
    name = p[0]
    n = int(p[1]) if len(p) > 1 and p[1].isdigit() else 25
    f = LOG_DIR / ("%s.log" % name)
    if not f.exists():
        return await say(update, "❌ log nahi hai")
    tail = "\n".join(f.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:])
    await say(update, "<pre>%s</pre>" % esc(tail[-3600:]))


@cmd("pip", cat="hoster", desc="package install", usage="pip <pkg>")
async def c_pip(update: Update, ctx, args: str) -> None:
    if not args.strip():
        return await say(update, "❌ <code>%spip requests</code>" % prefixes()[0])
    m = await say(update, load_card("pulse", "installing %s" % args.strip(), 1, 30))
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "pip", "install", "-q", *args.split(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    ok = proc.returncode == 0
    body = card("pip", [("install", [
        ("✅ done" if ok else "❌ fail") + " · <code>%s</code>" % esc(args.strip()),
        "<i>%s</i>" % esc(out.decode(errors="ignore")[-400:] or "ok")])],
        icon=E["tool"])
    try:
        await m.edit_text(body, parse_mode=ParseMode.HTML)
    except TelegramError:
        await say(update, body)


@cmd("sh", aliases=("shell", "cmd"), cat="hoster", desc="server shell (owner)",
     usage="sh <command>", owner=True)
async def c_sh(update: Update, ctx, args: str) -> None:
    if not args.strip():
        return await say(update, "❌ command do")
    proc = await asyncio.create_subprocess_shell(
        args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    txt = out.decode(errors="ignore")[-3500:] or "(no output)"
    await say(update, "<pre>%s</pre>" % esc(txt))


# ══════════════════════════════════════════════════════════════════
# 14 · GROUP ADMIN
# ══════════════════════════════════════════════════════════════════

async def _target(update: Update, args: str) -> Optional[User]:
    m = update.effective_message
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user
    a = args.strip().split()[0] if args.strip() else ""
    if a.lstrip("@").isdigit():
        try:
            ch = await BOT.get_chat(int(a.lstrip("@")))
            return ch  # type: ignore[return-value]
        except TelegramError:
            return None
    if a.startswith("@"):
        try:
            return await BOT.get_chat(a)
        except TelegramError:
            return None
    return None


async def _mod(update: Update, action: str, args: str) -> None:
    chat = update.effective_chat
    u = await _target(update, args)
    if not u:
        return await say(update, "❌ user reply ya @username do")
    reason = " ".join(args.split()[1:]) or "—"
    try:
        if action == "ban":
            await BOT.ban_chat_member(chat.id, u.id)
        elif action == "kick":
            await BOT.ban_chat_member(chat.id, u.id)
            await BOT.unban_chat_member(chat.id, u.id, only_if_banned=True)
        elif action == "unban":
            await BOT.unban_chat_member(chat.id, u.id, only_if_banned=True)
        elif action == "mute":
            await BOT.restrict_chat_member(
                chat.id, u.id,
                ChatPermissions(can_send_messages=False),
                until_date=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24))
        elif action == "unmute":
            await BOT.restrict_chat_member(
                chat.id, u.id,
                ChatPermissions(can_send_messages=True, can_send_audios=True,
                                can_send_documents=True, can_send_photos=True,
                                can_send_videos=True, can_send_polls=True,
                                can_send_other_messages=True,
                                can_add_web_page_previews=True))
        elif action == "promote":
            await BOT.promote_chat_member(
                chat.id, u.id, can_delete_messages=True, can_restrict_members=True,
                can_pin_messages=True, can_invite_users=True, can_manage_video_chats=True)
        elif action == "demote":
            await BOT.promote_chat_member(chat.id, u.id)
    except TelegramError as exc:
        return await say(update, "❌ <code>%s</code>" % esc(str(exc)[:120]))
    emo = {"ban": "🔨", "kick": "👢", "unban": "🕊", "mute": "🔇",
           "unmute": "🔊", "promote": "⬆️", "demote": "⬇️"}.get(action, "✅")
    await say(update, hbox("%s %s" % (action.upper(), ""), [
        "👤 <b>%s</b>" % esc(getattr(u, "first_name", None) or getattr(u, "title", None) or str(u.id)),
        "🆔 <code>%s</code>" % u.id,
        "📝 %s" % esc(reason)], footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=emo))


@cmd("ban", cat="admin", desc="user ban", usage="ban (reply) [reason]", admin=True, only_group=True, cool=2)
async def c_ban(update, ctx, args): await _mod(update, "ban", args)


@cmd("kick", aliases=("k",), cat="admin", desc="user kick", usage="kick (reply)", admin=True, only_group=True)
async def c_kick(update, ctx, args): await _mod(update, "kick", args)


@cmd("unban", aliases=("ub",), cat="admin", desc="unban", usage="unban (reply|id)", admin=True, only_group=True)
async def c_unban(update, ctx, args): await _mod(update, "unban", args)


@cmd("mute", aliases=("m",), cat="admin", desc="mute 24h", usage="mute (reply)", admin=True, only_group=True)
async def c_mute(update, ctx, args): await _mod(update, "mute", args)


@cmd("unmute", aliases=("um",), cat="admin", desc="unmute", usage="unmute (reply)", admin=True, only_group=True)
async def c_unmute(update, ctx, args): await _mod(update, "unmute", args)


@cmd("promote", aliases=("prom",), cat="admin", desc="admin banao", usage="promote (reply)", admin=True, only_group=True)
async def c_promote(update, ctx, args): await _mod(update, "promote", args)


@cmd("demote", aliases=("dem",), cat="admin", desc="admin hatao", usage="demote (reply)", admin=True, only_group=True)
async def c_demote(update, ctx, args): await _mod(update, "demote", args)


@cmd("warn", cat="admin", desc="warning do", usage="warn (reply) [reason]", admin=True, only_group=True)
async def c_warn(update, ctx, args):
    chat = update.effective_chat
    u = await _target(update, args)
    if not u:
        return await say(update, "❌ reply karo")
    warns = DB.data.setdefault("warns", {}).setdefault(str(chat.id), {})
    cur = int(warns.get(str(u.id), 0)) + 1
    warns[str(u.id)] = cur
    await DB.save()
    lim = int(DB.sget(chat.id, "max_warn") or 3)
    if cur >= lim:
        try:
            await BOT.ban_chat_member(chat.id, u.id)
            warns.pop(str(u.id), None)
            await DB.save()
            return await say(update, hbox("ᴡᴀʀɴ ʟɪᴍɪᴛ", [
                "👤 <b>%s</b>" % esc(u.first_name or str(u.id)),
                "⚠️ %d/%d — 🔨 ʙᴀɴɴᴇᴅ" % (cur, lim)], icon=E["hammer"]))
        except TelegramError:
            pass
    await say(update, hbox("ᴡᴀʀɴ", ["👤 <b>%s</b>" % esc(u.first_name or str(u.id)),
                                    "⚠️ <b>%d/%d</b>" % (cur, lim),
                                    "📝 %s" % esc(" ".join(args.split()[1:]) or "—")],
                            icon=E["warn"]))


@cmd("warns", aliases=("warnlist",), cat="admin", desc="warn list", usage="warns", admin=True, only_group=True)
async def c_warns(update, ctx, args):
    chat = update.effective_chat
    d = DB.data.get("warns", {}).get(str(chat.id), {})
    rows = ["<code>%s</code> · <b>%s</b>" % (k, v) for k, v in list(d.items())[:25]]
    await edit_say(update, card("warns", [("group", rows or ["<i>koi nahi</i>"])], icon=E["warn"]))


@cmd("resetwarns", aliases=("clearwarn",), cat="admin", desc="warns clear", usage="resetwarns (reply)", admin=True, only_group=True)
async def c_resetwarns(update, ctx, args):
    chat = update.effective_chat
    u = await _target(update, args)
    d = DB.data.get("warns", {}).get(str(chat.id), {})
    if u:
        d.pop(str(u.id), None)
    else:
        d.clear()
    await DB.save()
    await say(update, "✅ ᴡᴀʀɴꜱ ʀᴇꜱᴇᴛ")


@cmd("purge", aliases=("pg2",), cat="admin", desc="messages delete (reply se)", usage="purge", admin=True, only_group=True, cool=3)
async def c_purge(update, ctx, args):
    m = update.effective_message
    if not m.reply_to_message:
        return await say(update, "❌ jahan se delete karna hai us msg ko reply")
    start = m.reply_to_message.message_id
    end = m.message_id
    ids = list(range(start, end + 1))
    n = 0
    for i in range(0, len(ids), 100):
        try:
            await BOT.delete_messages(update.effective_chat.id, ids[i:i + 100])
            n += len(ids[i:i + 100])
        except TelegramError:
            pass
    try:
        await m.delete()
    except TelegramError:
        pass
    r = await say(update, "🧹 <b>%d</b> %s" % (n, smallcaps("messages deleted")))
    await asyncio.sleep(3)
    try:
        await r.delete()
    except TelegramError:
        pass


@cmd("del", aliases=("d",), cat="admin", desc="ek msg delete", usage="del (reply)", admin=True, only_group=True)
async def c_del(update, ctx, args):
    m = update.effective_message
    ids = [m.message_id]
    if m.reply_to_message:
        ids.append(m.reply_to_message.message_id)
    try:
        await BOT.delete_messages(update.effective_chat.id, ids)
    except TelegramError as exc:
        await say(update, "❌ %s" % esc(str(exc)[:80]))


@cmd("pin", cat="admin", desc="pin (silent)", usage="pin (reply)", admin=True, only_group=True)
async def c_pin(update, ctx, args):
    m = update.effective_message
    if not m.reply_to_message:
        return await say(update, "❌ reply karo")
    await BOT.pin_chat_message(update.effective_chat.id,
                               m.reply_to_message.message_id, disable_notification=True)
    await say(update, "📌 ᴘɪɴɴᴇᴅ")


@cmd("unpin", cat="admin", desc="unpin", usage="unpin", admin=True, only_group=True)
async def c_unpin(update, ctx, args):
    await BOT.unpin_chat_message(update.effective_chat.id)
    await say(update, "📌 ᴜɴᴘɪɴɴᴇᴅ")


@cmd("adminlist", aliases=("admins", "al"), cat="admin", desc="admin list", usage="adminlist", only_group=True)
async def c_adminlist(update, ctx, args):
    chat = update.effective_chat
    try:
        admins = await BOT.get_chat_administrators(chat.id)
    except TelegramError as exc:
        return await say(update, "❌ %s" % esc(str(exc)[:80]))
    rows = ["%s <b>%s</b> · <code>%s</code>" % (
        "👑" if str(getattr(m, "status", "")) == "creator" else "🛡",
        esc(m.user.first_name or "-"), m.user.id) for m in admins[:25]]
    await edit_say(update, card("admins", [("group", rows)], icon=E["shield"]))


@cmd("members", aliases=("count", "gc"), cat="admin", desc="member count", usage="members", only_group=True)
async def c_members(update, ctx, args):
    await edit_say(update, hbox("ᴍᴇᴍʙᴇʀꜱ",
                                ["👥 <b>%s</b>" % await BOT.get_chat_member_count(update.effective_chat.id)],
                                icon=E["earth"]))


@cmd("tagall", aliases=("mention", "all"), cat="admin", desc="sabko tag", usage="tagall [msg]", admin=True, only_group=True, cool=15)
async def c_tagall(update, ctx, args):
    chat = update.effective_chat
    rows, txt = [], (args.strip() or "📢")
    try:
        admins = await BOT.get_chat_administrators(chat.id)
        n = 0
        for m in admins:
            u = m.user
            if u.is_bot:
                continue
            rows.append("%s" % (("@" + u.username) if u.username else
                                '<a href="tg://user?id=%d">%s</a>' % (u.id, esc(u.first_name or "user"))))
            n += 1
            if n >= 30:
                break
    except TelegramError:
        pass
    if not rows:
        return await say(update, "❌ koi member nahi")
    await say(update, "<b>%s</b>\n%s" % (esc(txt), " · ".join(rows)))


@cmd("hidetag", aliases=("ht",), cat="admin", desc="hidden tag", usage="hidetag [msg]", admin=True, only_group=True, cool=8)
async def c_hidetag(update, ctx, args):
    chat = update.effective_chat
    try:
        admins = await BOT.get_chat_administrators(chat.id)
    except TelegramError:
        return
    names = "".join('<a href="tg://user?id=%d">\u2063</a>' % m.user.id for m in admins[:40])
    await say(update, "%s%s" % (esc(args.strip() or "👀"), names))


@cmd("lock", cat="admin", desc="group lock", usage="lock", admin=True, only_group=True)
async def c_lock(update, ctx, args):
    await BOT.set_chat_permissions(update.effective_chat.id,
                                   ChatPermissions(can_send_messages=False))
    await say(update, "🔐 ɢʀᴏᴜᴘ ʟᴏᴄᴋᴇᴅ")


@cmd("unlock", cat="admin", desc="group unlock", usage="unlock", admin=True, only_group=True)
async def c_unlock(update, ctx, args):
    await BOT.set_chat_permissions(update.effective_chat.id, ChatPermissions(
        can_send_messages=True, can_send_audios=True, can_send_documents=True,
        can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
        can_send_voice_notes=True, can_send_polls=True,
        can_send_other_messages=True, can_add_web_page_previews=True))
    await say(update, "🔓 ɢʀᴏᴜᴘ ᴜɴʟᴏᴄᴋᴇᴅ")


@cmd("slowmode", aliases=("slow",), cat="admin", desc="slow mode seconds", usage="slowmode <sec>", admin=True, only_group=True)
async def c_slowmode(update, ctx, args):
    sec = int(args.strip()) if args.strip().isdigit() else 10
    sec = max(0, min(sec, 3600))
    await BOT.set_chat_slow_mode_delay(update.effective_chat.id, sec)
    await say(update, "🐢 ꜱʟᴏᴡᴍᴏᴅᴇ · <b>%ds</b>" % sec)


@cmd("setgtitle", aliases=("title",), cat="admin", desc="group title", usage="setgtitle <name>", admin=True, only_group=True)
async def c_setgtitle(update, ctx, args):
    if not args.strip():
        return await say(update, "❌ naam do")
    await BOT.set_chat_title(update.effective_chat.id, args.strip()[:128])
    await say(update, "✅ ᴛɪᴛʟᴇ · <b>%s</b>" % esc(args.strip()[:128]))


@cmd("ginfo", aliases=("groupinfo",), cat="admin", desc="group info", usage="ginfo", only_group=True)
async def c_ginfo(update, ctx, args):
    chat = await BOT.get_chat(update.effective_chat.id)
    rows = ["🏷 <b>%s</b>" % esc(chat.title or "-"),
            "🆔 <code>%s</code>" % chat.id,
            "👥 %s" % (await BOT.get_chat_member_count(chat.id)),
            "🔗 @%s" % chat.username if chat.username else "🔒 private"]
    await edit_say(update, card("group info", [("chat", rows)], icon=E["earth"]))


@cmd("invite", aliases=("link",), cat="admin", desc="invite link", usage="invite", admin=True, only_group=True)
async def c_invite(update, ctx, args):
    try:
        link = await BOT.export_chat_invite_link(update.effective_chat.id)
    except TelegramError as exc:
        return await say(update, "❌ %s" % esc(str(exc)[:100]))
    await say(update, "🔗 %s" % link)


@cmd("revoke", cat="admin", desc="invite link revoke", usage="revoke", admin=True, only_group=True)
async def c_revoke(update, ctx, args):
    link = await BOT.export_chat_invite_link(update.effective_chat.id)
    await say(update, "♻️ ɴᴀʏᴀ ʟɪɴᴋ\n🔗 %s" % link)


@cmd("setgpic", cat="admin", desc="group photo", usage="setgpic (photo reply)", admin=True, only_group=True)
async def c_setgpic(update, ctx, args):
    img = await _media_bytes(update.effective_message.reply_to_message)
    if not img:
        return await say(update, "❌ photo reply karo")
    try:
        await BOT.set_chat_photo(update.effective_chat.id, InputFile(io.BytesIO(img), "g.jpg"))
        await say(update, "🖼 ɢʀᴏᴜᴘ ᴘʜᴏᴛᴏ ꜱᴇᴛ")
    except TelegramError as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))


@cmd("report", cat="admin", desc="msg report", usage="report [reason]", only_group=True)
async def c_report(update, ctx, args):
    r = update.effective_message.reply_to_message
    if not r:
        return await say(update, "❌ report karne wale msg ko reply karo")
    try:
        await raw_api("reportChat", {"chat_id": update.effective_chat.id,
                                    "message_ids": [r.message_id],
                                    "reason": "spam"})
        await say(update, "🚨 ʀᴇᴘᴏʀᴛᴇᴅ")
    except Exception as exc:
        await say(update, "❌ report fail · <code>%s</code>" % esc(str(exc)[:90]))


# ══════════════════════════════════════════════════════════════════
# 15 · PROTECTION  —  antilink / antiflood / welcome / captcha / react
# ══════════════════════════════════════════════════════════════════

URL_RX = re.compile(r"(https?://|t\.me/|www\.|@\w*bot\b)", re.I)
_FLOOD: Dict[Tuple[int, int], List[float]] = {}
CAPTCHA_PENDING: Dict[Tuple[int, int], float] = {}


@cmd("antilink", cat="anti", desc="links block: off/warn/del/kick",
     usage="antilink off|warn|delete|kick", admin=True, only_group=True)
async def c_antilink(update, ctx, args):
    mode = args.strip().lower() or "on"
    mode = {"on": "delete", "del": "delete", "d": "delete", "k": "kick",
            "w": "warn", "0": "off", "1": "delete"}.get(mode, mode)
    if mode not in ("off", "warn", "delete", "kick"):
        mode = "delete"
    await DB.sset(update.effective_chat.id, "antilink", mode)
    await say(update, "🛡 ᴀɴᴛɪʟɪɴᴋ · <b>%s</b>" % mode.upper())


@cmd("antiflood", aliases=("antispam",), cat="anti", desc="flood limit (0=off)",
     usage="antiflood <msgs in 10s>", admin=True, only_group=True)
async def c_antiflood(update, ctx, args):
    n = int(args.strip()) if args.strip().isdigit() else 0
    await DB.sset(update.effective_chat.id, "antiflood", n)
    await say(update, "🛡 ᴀɴᴛɪꜰʟᴏᴏᴅ · <b>%s</b>" % (n or "off"))


@cmd("antidel", aliases=("clean", "autoclean"), cat="anti",
     desc="commands auto-delete after N sec", usage="antidel <sec|off>",
     admin=True, only_group=True)
async def c_antidel(update, ctx, args):
    n = int(args.strip()) if args.strip().isdigit() else 0
    await DB.sset(update.effective_chat.id, "clean_after", n)
    await say(update, "🧹 ᴀᴜᴛᴏ ᴄʟᴇᴀɴ · <b>%s</b>" % (("%ds" % n) if n else "off"))


@cmd("welcome", cat="anti", desc="welcome on/off", usage="welcome on|off",
     admin=True, only_group=True)
async def c_welcome(update, ctx, args):
    on = args.strip().lower() not in ("off", "0", "no")
    await DB.sset(update.effective_chat.id, "welcome_on", on)
    await say(update, "👋 ᴡᴇʟᴄᴏᴍᴇ · <b>%s</b>" % ("ON" if on else "OFF"))


@cmd("setwelcome", aliases=("setwl",), cat="anti", desc="welcome text",
     usage="setwelcome <text: {name} {chat} {count}>", admin=True, only_group=True)
async def c_setwelcome(update, ctx, args):
    if not args.strip():
        return await say(update, "❌ text do · <code>{name}</code> <code>{chat}</code> <code>{count}</code>")
    await DB.sset(update.effective_chat.id, "welcome", args.strip())
    await DB.sset(update.effective_chat.id, "welcome_on", True)
    await say(update, "✅ ᴡᴇʟᴄᴏᴍᴇ ꜱᴇᴛ\n\n" + premium(args.strip()))


@cmd("goodbye", cat="anti", desc="goodbye on/off", usage="goodbye on|off",
     admin=True, only_group=True)
async def c_goodbye(update, ctx, args):
    on = args.strip().lower() not in ("off", "0", "no")
    await DB.sset(update.effective_chat.id, "goodbye_on", on)
    await say(update, "👋 ɢᴏᴏᴅʙʏᴇ · <b>%s</b>" % ("ON" if on else "OFF"))


@cmd("setgoodbye", cat="anti", desc="goodbye text", usage="setgoodbye <text>",
     admin=True, only_group=True)
async def c_setgoodbye(update, ctx, args):
    if not args.strip():
        return await say(update, "❌ text do")
    await DB.sset(update.effective_chat.id, "goodbye", args.strip())
    await say(update, "✅ ɢᴏᴏᴅʙʏᴇ ꜱᴇᴛ")


@cmd("rules", cat="anti", desc="group rules dekho", usage="rules", only_group=True)
async def c_rules(update, ctx, args):
    txt = DB.sget(update.effective_chat.id, "rules") or "❌ rules set nahi"
    await say(update, "<b>📖 ʀᴜʟᴇꜱ</b>\n\n" + premium(txt))


@cmd("setrules", cat="anti", desc="rules set", usage="setrules <text>",
     admin=True, only_group=True)
async def c_setrules(update, ctx, args):
    if not args.strip():
        return await say(update, "❌ text do")
    await DB.sset(update.effective_chat.id, "rules", args.strip())
    await say(update, "✅ ʀᴜʟᴇꜱ ꜱᴀᴠᴇᴅ")


@cmd("captcha", cat="anti", desc="naye member captcha", usage="captcha on|off",
     admin=True, only_group=True)
async def c_captcha(update, ctx, args):
    on = args.strip().lower() not in ("off", "0", "no")
    await DB.sset(update.effective_chat.id, "captcha", on)
    await say(update, "🤖 ᴄᴀᴘᴛᴄʜᴀ · <b>%s</b>" % ("ON" if on else "OFF"))


@cmd("autoreact", aliases=("ar2",), cat="anti", desc="auto react emoji",
     usage="autoreact 🔥 (blank = off)", admin=True, only_group=True)
async def c_autoreact(update, ctx, args):
    e = args.strip()
    await DB.sset(update.effective_chat.id, "auto_react", e)
    await say(update, "💫 ᴀᴜᴛᴏ ʀᴇᴀᴄᴛ · <b>%s</b>" % (esc(e) or "off"))


@cmd("settings", aliases=("set",), cat="anti", desc="group settings dekho",
     usage="settings", admin=True, only_group=True)
async def c_settings(update, ctx, args):
    cid = update.effective_chat.id
    rows = ["🔗 antilink · <b>%s</b>" % DB.sget(cid, "antilink"),
            "🌊 antiflood · <b>%s</b>" % (DB.sget(cid, "antiflood") or "off"),
            "🧹 autoclean · <b>%s</b>" % (DB.sget(cid, "clean_after") or "off"),
            "👋 welcome · <b>%s</b>" % ("on" if DB.sget(cid, "welcome_on") else "off"),
            "🤖 captcha · <b>%s</b>" % ("on" if DB.sget(cid, "captcha") else "off"),
            "💫 autoreact · <b>%s</b>" % (DB.sget(cid, "auto_react") or "off"),
            "⚠️ max warn · <b>%s</b>" % DB.sget(cid, "max_warn")]
    await edit_say(update, card("settings", [("group", rows)], icon=E["tool"]))


# ══════════════════════════════════════════════════════════════════
# 16 · NOTES + FILTERS
# ══════════════════════════════════════════════════════════════════

@cmd("save", aliases=("note",), cat="notes", desc="note save (reply se bhi)",
     usage="save <name> [text]", sudo=False)
async def c_save(update, ctx, args):
    if not args.strip():
        return await say(update, "❌ <code>%ssave naam text</code>" % prefixes()[0])
    name, _, body = args.partition(" ")
    r = update.effective_message.reply_to_message
    d = DB.data.setdefault("notes", {}).setdefault(str(update.effective_chat.id), {})
    d[name.lower()] = body.strip() or ("#reply:%d" % r.message_id if r else "")
    await DB.save()
    await say(update, "💾 ꜱᴀᴠᴇᴅ · <code>#%s</code>" % esc(name.lower()))


@cmd("get", aliases=("noteget", "n"), cat="notes", desc="note nikalo",
     usage="get <name>", sudo=False)
async def c_get(update, ctx, args):
    d = DB.data.get("notes", {}).get(str(update.effective_chat.id), {})
    key = args.strip().lower()
    if key not in d:
        return await say(update, "❌ note nahi hai")
    val = d[key]
    if val.startswith("#reply:"):
        try:
            await BOT.copy_message(update.effective_chat.id, update.effective_chat.id,
                                   int(val.split(":")[1]))
            return
        except TelegramError:
            return await say(update, "❌ original msg delete ho gaya")
    await say(update, premium(val))


@cmd("notes", aliases=("noteslist", "nl"), cat="notes", desc="saare notes",
     usage="notes", sudo=False)
async def c_notes(update, ctx, args):
    d = DB.data.get("notes", {}).get(str(update.effective_chat.id), {})
    rows = ["🔖 <code>#%s</code>" % esc(k) for k in sorted(d)[:30]]
    await edit_say(update, card("notes", [("saved", rows or ["<i>khaali</i>"])],
                                icon=E["note"]))


@cmd("clear", aliases=("delnote", "rem"), cat="notes", desc="note delete",
     usage="clear <name|all>", sudo=False)
async def c_clear(update, ctx, args):
    d = DB.data.setdefault("notes", {}).setdefault(str(update.effective_chat.id), {})
    k = args.strip().lower()
    if k in ("all", "*"):
        d.clear()
    else:
        d.pop(k, None)
    await DB.save()
    await say(update, "🗑 ᴄʟᴇᴀʀᴇᴅ")


@cmd("addfilter", aliases=("filter",), cat="notes", desc="auto reply filter",
     usage="addfilter <trigger> <reply>", admin=True, only_group=True)
async def c_addfilter(update, ctx, args):
    trig, _, body = args.partition(" ")
    if not trig or not body.strip():
        return await say(update, "❌ <code>%saddfilter hi Hello {name}</code>" % prefixes()[0])
    d = DB.data.setdefault("filters", {}).setdefault(str(update.effective_chat.id), {})
    d[trig.lower()] = body.strip()
    await DB.save()
    await say(update, "🧩 ꜰɪʟᴛᴇʀ ᴀᴅᴅᴇᴅ · <b>%s</b>" % esc(trig))


@cmd("delfilter", aliases=("stopfilter",), cat="notes", desc="filter hatao",
     usage="delfilter <trigger|all>", admin=True, only_group=True)
async def c_delfilter(update, ctx, args):
    d = DB.data.setdefault("filters", {}).setdefault(str(update.effective_chat.id), {})
    if args.strip() in ("all", "*"):
        d.clear()
    else:
        d.pop(args.strip().lower(), None)
    await DB.save()
    await say(update, "🗑 ꜰɪʟᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ")


@cmd("filters", aliases=("filterlist", "fl"), cat="notes", desc="filter list",
     usage="filters", sudo=False)
async def c_filters(update, ctx, args):
    d = DB.data.get("filters", {}).get(str(update.effective_chat.id), {})
    rows = ["🧩 <code>%s</code>" % esc(k) for k in sorted(d)[:30]]
    await edit_say(update, card("filters", [("active", rows or ["<i>khaali</i>"])],
                                icon=E["puzzle"] if "puzzle" in E else E["note"]))


# ══════════════════════════════════════════════════════════════════
# 17 · GUARD  —  har group message par chalne wala watcher
# ══════════════════════════════════════════════════════════════════

async def _punish(update: Update, reason: str, mode: str) -> None:
    chat, msg, u = update.effective_chat, update.effective_message, update.effective_user
    if not (chat and msg and u):
        return
    try:
        if mode in ("delete", "warn", "kick"):
            await msg.delete()
    except TelegramError:
        pass
    if mode == "warn":
        DB.data.setdefault("warnish", {}).setdefault(str(chat.id), 0)
        n = DB.data["warnish"][str(chat.id)] = DB.data["warnish"][str(chat.id)] + 1
        warn = await BOT.send_message(chat.id, "⚠️ <b>%s</b> · %s (%d)" % (
            esc(u.first_name or str(u.id)), smallcaps(reason), n), parse_mode=ParseMode.HTML)
        await asyncio.sleep(6)
        try:
            await warn.delete()
        except TelegramError:
            pass
    elif mode == "kick":
        try:
            await BOT.ban_chat_member(chat.id, u.id)
            await BOT.unban_chat_member(chat.id, u.id, only_if_banned=True)
            await BOT.send_message(chat.id, "👢 <b>%s</b> · %s" % (
                esc(u.first_name or str(u.id)), smallcaps(reason)),
                parse_mode=ParseMode.HTML)
        except TelegramError:
            pass


async def guard(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """group watcher: filters · antilink · antiflood · autoreact."""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not (msg and chat and user and not user.is_bot):
        return
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    text = (msg.text or msg.caption or "")
    DB.data.setdefault("chats", {}).setdefault(str(chat.id), {})

    # autoreact
    react = DB.sget(chat.id, "auto_react")
    if react:
        try:
            await BOT.set_message_reaction(chat.id, msg.message_id,
                                           reaction=[ReactionTypeEmoji(react)])
        except TelegramError:
            pass

    # antilink
    al = DB.sget(chat.id, "antilink") or "off"
    if al != "off" and URL_RX.search(text):
        if not await _is_admin(chat.id, user.id):
            return await _punish(update, "link not allowed", al)

    # antiflood
    lim = int(DB.sget(chat.id, "antiflood") or 0)
    if lim:
        key = (chat.id, user.id)
        now = time.time()
        win = float(DB.sget(chat.id, "flood_window") or 10)
        stamps = [t for t in _FLOOD.get(key, []) if now - t < win]
        stamps.append(now)
        _FLOOD[key] = stamps
        if len(stamps) >= lim and not await _is_admin(chat.id, user.id):
            return await _punish(update, "flooding", "delete")

    # autoclean (command replies)
    clean = int(DB.sget(chat.id, "clean_after") or 0)
    if clean and msg.text and msg.text.startswith(tuple(prefixes() or ["."])) :
        async def _later(m: Message, s: int) -> None:
            await asyncio.sleep(s)
            try:
                await m.delete()
            except TelegramError:
                pass
        asyncio.create_task(_later(msg, clean))

    # filters
    d = DB.data.get("filters", {}).get(str(chat.id), {})
    if d and text:
        low = text.lower()
        for trig, body in d.items():
            if trig in low:
                body = body.replace("{name}", user.first_name or "user")
                body = body.replace("{id}", str(user.id))
                body = body.replace("{chat}", chat.title or "group")
                await msg.reply_text(premium(body), parse_mode=ParseMode.HTML,
                                     reply_to_message_id=msg.message_id,
                                     allow_sending_without_reply=True)
                return


async def member_watcher(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """welcome / goodbye / captcha."""
    msg = update.effective_message
    chat = update.effective_chat
    if not (msg and chat):
        return
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    if msg.new_chat_members:
        count = 1
        try:
            count = await BOT.get_chat_member_count(chat.id)
        except TelegramError:
            pass
        for u in msg.new_chat_members:
            if u.is_bot:
                continue
            wl = DB.sget(chat.id, "welcome") or \
                "%s {name} · welcome to {chat}" % E["spark"]
            txt = wl.replace("{name}", '<a href="tg://user?id=%d">%s</a>' % (
                u.id, esc(u.first_name or "user")))
            txt = txt.replace("{chat}", esc(chat.title or "group")).replace("{count}", str(count))
            try:
                await msg.reply_text(premium("👋 " + txt), parse_mode=ParseMode.HTML,
                                     disable_web_page_preview=True)
            except TelegramError:
                pass
    if msg.left_chat_member and DB.sget(chat.id, "goodbye_on"):
        u = msg.left_chat_member
        gb = DB.sget(chat.id, "goodbye") or "👋 {name} left the chat"
        txt = gb.replace("{name}", esc(u.first_name or "user")) \
                 .replace("{chat}", esc(chat.title or "group"))
        try:
            await msg.reply_text(premium(txt), parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

# ══════════════════════════════════════════════════════════════════
# 18 · FUN  —  games, moods, masti (light + clean)
# ══════════════════════════════════════════════════════════════════

EIGHT_BALL = [
    "100% पक्का hai 💯", "haan bilkul ✅", "shayad… 🤔", "abhi nahi ⌛",
    "nahi hoga ❌", "risk mat le ⚠️", "tera luck hi kharab hai 🥲",
    "ho jayega, tension na le 🙂", "sochne de 🤯", "kal poochhna 📅",
]
JOKES = [
    "Teacher: tumne homework kyun nahi kiya?\nMe: sir internet down tha.\nTeacher: par tumhare paas data to hai?\nMe: wo bhi down tha sir 😭",
    "Doctor: tumhe roz subah uthkar 5km daudna chahiye.\nMe: par doctor, main to shaam ko uthta hoon 🌙",
    "Boss: tumhara password kya hai?\nMe: 'mujhenahipata'\nBoss: wo to mujhe bhi nahi pata 🤣",
    "Papa: beta padhai kaisi chal rahi hai?\nMe: perfect papa, 90% website open ho jati hai 💀",
    "Wifi: kya baat hai? 😏\nMobile data: kuch nahi yaar, teri hi yaad aa rahi thi ❤️",
]
SHAYARI = [
    "Dil ki baat hoton par laani nahi aati,\nkuch khwahishein bayaan nahi hoti,\njalne walon ko aag ka gyaan dena kya,\njo khud jal rahe hain unhe dua chahiye 🌙",
    "Waqt se pehle aur naseeb se zyada,\nkisi ko kuch nahi miltabhai,\nhaan wo sahi hai — bas dua karte raho 🌸",
    "Raat ke andhere me tara hi kaam aata hai,\nrishton me yahi hota hai — sach bolne wala akela reh jata hai ⭐",
    "Tumhari muskurahat ek shayari hai,\njo bina lafz likhi jaati hai 💜",
]
PICKUP = [
    "Tumhara naam kya hai? Kyunki main ise apni dua me rakhna chahta hoon 🌙",
    "Kya tum Google ho? Kyunki jo main dhoondh raha tha wo tum ho ✨",
    "Tumhari aankhon me kuch aisa hai jo battery se bhi zyada charge deta hai 🔋",
    "Mera wifi weak hai, par tumse connection full hai 📶",
]
COMPLIMENTS = [
    "tumhari energy poore group ko light kar deti hai ⚡",
    "tumhari hansi sabse best notification hai 🔔",
    "tum genuinely bahut pyare ho, bas bolna tha 💜",
    "tumhari soch level hai — log follow karte hain 🧠",
    "tum me ek calm si vibe hai jo sabko accha lagta hai 🌊",
]
ROASTS = [
    "tumhara confidence 4G hai, network 2G ka 🥲",
    "tum padhai me topper ho, baaton me chai wala ☕",
    "tumhari typing speed itni slow hai ki keyboard so jata hai 😴",
    "tum jaha jate ho, wahan wifi ki speed half ho jati hai 📉",
    "tum " '"legend"' " ho — mitti ke 🏺",
]
TRUTHS = [
    "last time tumne jhooth kab bola tha? 🤥",
    "tumhare phone me sabse pehle kaun open hota hai? 📱",
    "sabse embarrassing moment kya tha? 😳",
    "kisi ne ghost kiya hai tumhe? 👻",
    "tumhari sabse badi guilty pleasure kya hai? 🍫",
]
DARES = [
    "next 3 messages sirf emoji me bhejo 😶",
    "group ke kisi ek member ko genuine compliment do 💜",
    "apne favourite song ke 2 lines gaake voice note bhejo 🎤",
    "10 pushups karo aur bolo 'ho gaya' 🔥",
    "profile pic ka story batao 🖼",
]
WYR = [
    "paisa lekin no internet 💰  ya  internet lekin no paisa 📶?",
    "hamesha late uthna 😴  ya  hamesha late sona 🌙?",
    "chai hamesha ☕  ya  coffee hamesha ☕?",
    "ghost ban jao 👻  ya  invisible ho jao 🫥?",
    "1 crore abhi 💸  ya  10 crore 10 saal baad 🕰?",
]
FACTS = [
    "🦋 Butterfly apne taste buds pairon par rakhti hai.",
    "🧠 Human brain 20% energy sirf sochne me kharch karta hai.",
    "🐙 Octopus ke 3 dil hote hain.",
    "🌌 Universe me stars ki sankhya zameen par ret ke kanon se bhi zyada hai.",
    "🍯 Honey kabhi kharab nahi hota — 3000 saal purana bhi khaya ja sakta hai.",
]


def _who(update: Update) -> str:
    u = update.effective_user
    return '<a href="tg://user?id=%d">%s</a>' % (u.id, esc(u.first_name or "user"))


@cmd("8ball", aliases=("ask8", "ball"), cat="fun", desc="magic 8 ball", usage="8ball <question>", sudo=False)
async def c_8ball(update, ctx, args):
    q = args.strip() or "kuch bhi"
    await say(update, "🎱 <b>%s</b>\n\n➜ %s" % (esc(q[:120]), random.choice(EIGHT_BALL)))


@cmd("dice", aliases=("d", "dice2"), cat="fun", desc="dice roll", usage="dice", sudo=False)
async def c_dice(update, ctx, args):
    await update.effective_message.reply_dice(emoji="🎲")


@cmd("dart", cat="fun", desc="dart throw", usage="dart", sudo=False)
async def c_dart(update, ctx, args):
    await update.effective_message.reply_dice(emoji="🎯")


@cmd("bowl", cat="fun", desc="bowling", usage="bowl", sudo=False)
async def c_bowl(update, ctx, args):
    await update.effective_message.reply_dice(emoji="🎳")


@cmd("coin", aliases=("flip", "toss"), cat="fun", desc="coin toss", usage="coin", sudo=False)
async def c_coin(update, ctx, args):
    await say(update, "🪙 <b>%s</b>" % random.choice(["HEADS", "TAILS"]))


@cmd("rps", cat="fun", desc="rock paper scissors", usage="rps rock|paper|scissor", sudo=False)
async def c_rps(update, ctx, args):
    me = random.choice(["rock", "paper", "scissor"])
    you = (args.strip().lower() or random.choice(["rock", "paper", "scissor"]))[:9]
    you = "scissor" if you.startswith("s") else ("paper" if you.startswith("p") else "rock")
    beat = {"rock": "scissor", "paper": "rock", "scissor": "paper"}
    res = "🤝 TIE" if you == me else ("🏆 YOU WIN" if beat[you] == me else "💀 I WIN")
    await say(update, "✊✋✌️\n\n%s → <b>%s</b>\nme → <b>%s</b>\n\n<b>%s</b>" % (
        smallcaps("you"), you, me, res))


@cmd("truth", aliases=("t2",), cat="fun", desc="truth question", usage="truth", sudo=False)
async def c_truth(update, ctx, args):
    await say(update, "🫣 <b>ᴛʀᴜᴛʜ</b>\n\n%s %s" % (_who(update), random.choice(TRUTHS)))


@cmd("dare", cat="fun", desc="dare task", usage="dare", sudo=False)
async def c_dare(update, ctx, args):
    await say(update, "😈 <b>ᴅᴀʀᴇ</b>\n\n%s %s" % (_who(update), random.choice(DARES)))


@cmd("joke", aliases=("hasao",), cat="fun", desc="joke", usage="joke", sudo=False)
async def c_joke(update, ctx, args):
    await say(update, "😂 " + esc(random.choice(JOKES)))


@cmd("shayari", aliases=("shayri", "sher"), cat="fun", desc="shayari", usage="shayari", sudo=False)
async def c_shayari(update, ctx, args):
    await say(update, "🌙 " + esc(random.choice(SHAYARI)))


@cmd("pickup", aliases=("line", "flirt"), cat="fun", desc="pickup line", usage="pickup", sudo=False)
async def c_pickup(update, ctx, args):
    await say(update, "💘 " + esc(random.choice(PICKUP)))


@cmd("compliment", aliases=("tareef",), cat="fun", desc="tareef", usage="compliment [reply]", sudo=False)
async def c_compliment(update, ctx, args):
    r = update.effective_message.reply_to_message
    who = ('<a href="tg://user?id=%d">%s</a>' % (r.from_user.id, esc(r.from_user.first_name))
           if r and r.from_user else _who(update))
    await say(update, "💜 %s %s" % (who, esc(random.choice(COMPLIMENTS))))


@cmd("roast", cat="fun", desc="halki roast", usage="roast [reply]", sudo=False)
async def c_roast(update, ctx, args):
    r = update.effective_message.reply_to_message
    who = ('<a href="tg://user?id=%d">%s</a>' % (r.from_user.id, esc(r.from_user.first_name))
           if r and r.from_user else _who(update))
    await say(update, "🔥 %s %s" % (who, esc(random.choice(ROASTS))))


@cmd("would", aliases=("wyr",), cat="fun", desc="would you rather", usage="would", sudo=False)
async def c_would(update, ctx, args):
    await say(update, "🤔 <b>ᴡᴏᴜʟᴅ ʏᴏᴜ ʀᴀᴛʜᴇʀ</b>\n\n%s" % esc(random.choice(WYR)))


@cmd("fact", cat="fun", desc="random fact", usage="fact", sudo=False)
async def c_fact(update, ctx, args):
    await say(update, esc(random.choice(FACTS)))


@cmd("guess", aliases=("num",), cat="fun", desc="1-100 guess game", usage="guess <n>", sudo=False)
async def c_guess(update, ctx, args):
    key = "guess_%s" % update.effective_chat.id
    n = DB.data.get(key)
    if not args.strip().isdigit():
        DB.data[key] = random.randint(1, 100)
        DB.save_now()
        return await say(update, "🎯 1–100 ke beech socha. <code>%sguess 42</code>" % prefixes()[0])
    g = int(args.strip())
    if g == n:
        DB.data.pop(key, None)
        DB.save_now()
        return await say(update, "🏆 <b>SAHI!</b> number tha <b>%d</b>" % n)
    DB.data[key] = n
    DB.save_now()
    await say(update, ("📈 bada" if g < n else "📉 chhota"))


@cmd("slots", aliases=("spin", "casino"), cat="fun", desc="slot machine", usage="slots", sudo=False, cool=3)
async def c_slots(update, ctx, args):
    syms = ["🍒", "🍋", "🍇", "💎", "7️⃣", "⭐"]
    m = await say(update, load_card("pulse", "spinning", 1, 20))
    for i in range(5):
        try:
            await m.edit_text("🎰 " + "  ".join(random.choice(syms) for _ in range(3)) +
                              "\n" + bar(20 + i * 16))
        except TelegramError:
            pass
        await asyncio.sleep(0.45)
    row = [random.choice(syms) for _ in range(3)]
    win = len(set(row)) == 1
    await m.edit_text("🎰 <b>%s</b>\n\n%s" % ("  ".join(row),
                                              "🏆 JACKPOT!" if win else "🥲 phir se try kar"))


@cmd("ship", aliases=("love", "luv"), cat="fun", desc="love calculator", usage="ship [reply]", sudo=False)
async def c_ship(update, ctx, args):
    a = update.effective_user.first_name or "you"
    r = update.effective_message.reply_to_message
    b = r.from_user.first_name if r and r.from_user else (args.strip() or "crush")
    h = int(hashlib.md5((a + b).encode()).hexdigest()[:6], 16) % 101
    await say(update, hbox("ʟᴏᴠᴇ ᴍᴇᴛᴇʀ", [
        "💜 <b>%s</b>  +  <b>%s</b>" % (esc(a), esc(b)),
        bar(h) + "  <b>%d%%</b>" % h,
        random.choice(["perfect match 💞", "thoda kaam baaki hai 🙂",
                       "friendzone alert ⚠️", "shaadi pakki 💍"])],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["love"]))


@cmd("rate", cat="fun", desc="kuch bhi rate karo", usage="rate <cheez>", sudo=False)
async def c_rate(update, ctx, args):
    t = args.strip() or "tum"
    v = random.randint(1, 100)
    await say(update, "⭐ <b>%s</b> → <b>%d/100</b>\n%s" % (esc(t[:40]), v, bar(v)))


@cmd("aura", cat="fun", desc="aura points", usage="aura [reply]", sudo=False)
async def c_aura(update, ctx, args):
    v = random.randint(-999, 9999)
    await say(update, "🔮 %s · aura <b>%+d</b> %s" % (
        _who(update), v, "🔥" if v > 5000 else ("💀" if v < 0 else "✨")))


@cmd("vibe", cat="fun", desc="aaj ki vibe", usage="vibe", sudo=False)
async def c_vibe(update, ctx, args):
    await say(update, "🌊 aaj ki vibe · <b>%s</b>" % random.choice(
        ["main character energy ✨", "sigma mode 🗿", "soft hours 🌙",
         "chaos loading 💀", "focus mode 🎯", "chill vibes 🍃"]))


@cmd("brain", cat="fun", desc="iq check", usage="brain [reply]", sudo=False)
async def c_brain(update, ctx, args):
    await say(update, "🧠 %s · IQ <b>%d</b>" % (_who(update), random.randint(20, 180)))


@cmd("age", cat="fun", desc="age guess", usage="age [reply]", sudo=False)
async def c_age(update, ctx, args):
    await say(update, "🎂 %s · <b>%d</b> saal ka lagta hai" % (_who(update), random.randint(15, 40)))


@cmd("pick", aliases=("choose", "chun"), cat="fun", desc="option chuno", usage="pick a, b, c", sudo=False)
async def c_pick(update, ctx, args):
    opts = [o.strip() for o in re.split(r"[,/|]", args) if o.strip()]
    if len(opts) < 2:
        return await say(update, "❌ <code>%spick chai, coffee</code>" % prefixes()[0])
    await say(update, "🎯 <b>%s</b>" % esc(random.choice(opts)))


@cmd("roll", cat="fun", desc="random number", usage="roll [max]", sudo=False)
async def c_roll(update, ctx, args):
    mx = int(args.strip()) if args.strip().isdigit() else 100
    await say(update, "🎲 <b>%d</b> / %d" % (random.randint(1, max(1, mx)), mx))


@cmd("mock", aliases=("spongebob",), cat="fun", desc="moCkInG tExT", usage="mock <text>", sudo=False)
async def c_mock(update, ctx, args):
    out = "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(args or "nik"))
    await say(update, esc(out))


@cmd("party", aliases=("celebrate",), cat="fun", desc="party animation", usage="party", sudo=False, cool=3)
async def c_party(update, ctx, args):
    m = await say(update, "🎉")
    for fr in ["🎉", "🎉 🎊", "🎉 🎊 ✨", "🎊 🎉 🎈 ✨", "🥳 ᴘᴀʀᴛʏ ᴛɪᴍᴇ 🥳"]:
        try:
            await m.edit_text(fr)
        except TelegramError:
            pass
        await asyncio.sleep(0.4)



@cmd("say", aliases=("echo", "b", "bol"), cat="fun", desc="bot bolega",
     usage="say <text>", sudo=False)
async def c_say(update, ctx, args):
    body = _arg(update, args) if "_arg" in globals() else args
    if not body.strip():
        return await say(update, "❌ text do")
    await say(update, esc(body[:3500]))



# ══════════════════════════════════════════════════════════════════
# 18b · GAMES  —  inline button wale (poora group khel sakta hai)
# ══════════════════════════════════════════════════════════════════

TTT_WIN = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
           (2, 5, 8), (0, 4, 8), (2, 4, 6)]
TTT_EMO = {"X": "❌", "O": "⭕", " ": "▫"}

QUIZ_BANK = [
    ("Bharat ka pehla rocket kaunsa tha?", ["Aryabhata", "Chandrayaan", "PSLV", "Rohini"], 3),
    ("HTML ka full form?", ["Hyper Text Markup Language", "High Text Machine Lang",
                            "Hyper Tabular Markup", "Home Tool Markup"], 0),
    ("Sabse bada mahasagar?", ["Atlantic", "Indian", "Pacific", "Arctic"], 2),
    ("Python ka creator?", ["Guido van Rossum", "Linus Torvalds", "Dennis Ritchie",
                            "James Gosling"], 0),
    ("Ek saal me kitne seconds?", ["31,536,000", "31,000,000", "30,000,000", "32,400,000"], 0),
    ("Duniya ka sabse chhota desh?", ["Monaco", "Vatican City", "Nauru", "Malta"], 1),
    ("TCP/IP me IP ka matlab?", ["Internet Protocol", "Internal Process", "Input Port",
                                 "Interface Point"], 0),
    ("Bijli ka unit (kWh) kiski unit hai?", ["Power", "Energy", "Current", "Voltage"], 1),
    ("Telegram kis saal launch hua?", ["2011", "2013", "2010", "2014"], 1),
    ("1 GB me kitne MB?", ["1000", "1024", "512", "2048"], 1),
]
QUIZ_LIVE: Dict[str, Dict[str, Any]] = {}
QUIZ_SEQ = 0


def _ttt_render(chat_id: int, st: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
    b = st["b"]
    turn = st["turn"]
    who = st["x"] if turn == "X" else st.get("o")
    head = "❌ <b>vs</b> ⭕  ·  turn: <b>%s</b>" % (
        ("<a href='tg://user?id=%s'>@%s</a>" % (who, "player")) if who else smallcaps(turn))
    rows = []
    for r in range(3):
        rows.append([("%s" % TTT_EMO[b[r * 3 + c]], "ttt:%d:%d" % (chat_id, r * 3 + c))
                     for c in range(3)])
    rows.append([("reset", "ttt:%d:r" % chat_id), ("close", "close")])
    return head, kb(rows)


def _ttt_win(b: List[str]) -> Optional[str]:
    for a, m, z in TTT_WIN:
        if b[a] == b[m] == b[z] != " ":
            return b[a]
    return "draw" if " " not in b else None


@cmd("ttt", aliases=("tictactoe", "xo"), cat="fun", desc="tic tac toe (2 players)",
     usage="ttt", sudo=False, cool=2)
async def c_ttt(update: Update, ctx, args):
    chat_id = update.effective_chat.id
    u = update.effective_user
    st = {"b": [" "] * 9, "x": u.id, "o": None, "turn": "X"}
    DB.data.setdefault("ttt", {})[str(chat_id)] = st
    await DB.save()
    head, board = _ttt_render(chat_id, st)
    await update.effective_message.reply_text(
        "🎮 <b>ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ</b>\n%s\n<i>%s</i>" % (
            head, esc("dusra player koi bhi button dabaye — wo ⭕ ban jayega")),
        parse_mode=ParseMode.HTML, reply_markup=board)


async def _ttt_click(q, chat_id: int, pos: str) -> None:
    st = DB.data.get("ttt", {}).get(str(chat_id))
    if not st:
        return await q.answer("game khatam — .ttt se naya", show_alert=True)
    uid = q.from_user.id
    if pos == "r":
        st.update({"b": [" "] * 9, "x": uid, "o": None, "turn": "X"})
        await DB.save()
        head, board = _ttt_render(chat_id, st)
        return await q.edit_message_text("🎮 <b>ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ</b>\n%s" % head,
                                         parse_mode=ParseMode.HTML, reply_markup=board)
    idx = int(pos)
    sym = "X" if uid == st["x"] else "O"
    if sym == "O" and not st.get("o"):
        st["o"] = uid
    elif sym == "O" and st.get("o") != uid:
        return await q.answer("ye game do logon ka hai 🙂", show_alert=True)
    if st["turn"] != sym:
        return await q.answer("abhi %s ki baari" % st["turn"], show_alert=True)
    if st["b"][idx] != " ":
        return await q.answer("wo jagah bhari hai", show_alert=True)
    st["b"][idx] = sym
    win = _ttt_win(st["b"])
    st["turn"] = "O" if sym == "X" else "X"
    await DB.save()
    head, board = _ttt_render(chat_id, st)
    if win:
        DB.data["ttt"].pop(str(chat_id), None)
        await DB.save()
        txt = ("🏆 <b>%s wins!</b>" % ("❌" if win == "X" else "⭕")) if win != "draw" \
            else "🤝 <b>draw</b>"
        return await q.edit_message_text("🎮 <b>ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ</b>\n%s\n\n%s" % (head, txt),
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=kb([[("naya game", "ttt:%d:r" % chat_id),
                                                           ("close", "close")]]))
    await q.edit_message_text("🎮 <b>ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ</b>\n%s" % head,
                              parse_mode=ParseMode.HTML, reply_markup=board)


@cmd("quiz", aliases=("trivia", "gk"), cat="fun", desc="gk quiz · 4 options",
     usage="quiz", sudo=False, cool=3)
async def c_quiz(update: Update, ctx, args):
    global QUIZ_SEQ
    QUIZ_SEQ += 1
    qid = "%d_%d" % (update.effective_chat.id, QUIZ_SEQ)
    q, opts, ans = random.choice(QUIZ_BANK)
    QUIZ_LIVE[qid] = {"q": q, "opts": opts, "ans": ans}
    rows = [[("%s %s" % (chr(65 + i), o[:26]), "qz:%s:%d" % (qid, i))] for i, o in enumerate(opts)]
    await update.effective_message.reply_text(
        "🧠 <b>Qᴜɪᴢ</b>\n\n%s\n\n<i>%s</i>" % (esc(q), smallcaps("option dabao")),
        parse_mode=ParseMode.HTML, reply_markup=kb(rows))


async def _quiz_click(q, qid: str, idx: str) -> None:
    data = QUIZ_LIVE.pop(qid, None)
    if not data:
        return await q.answer("quiz purana ho gaya — .quiz se naya", show_alert=True)
    good = int(idx) == data["ans"]
    marks = ["🇦", "🇧", "🇨", "🇩"]
    body = "\n".join("%s %s %s" % (marks[i], esc(o),
                                   "✅" if i == data["ans"] else
                                   ("❌" if i == int(idx) else ""))
                     for i, o in enumerate(data["opts"]))
    await q.edit_message_text(
        "🧠 <b>%s</b>\n\n%s\n\n%s %s" % (
            esc(data["q"]), body,
            "🏆 <b>%s</b> sahi!" % esc(q.from_user.first_name or "you") if good
            else "💀 galat — sahi jawab <b>%s</b>" % esc(data["opts"][data["ans"]])),
        parse_mode=ParseMode.HTML)


HANG_WORDS = ["telegram", "python", "himalaya", "cricket", "chocolate", "planetary",
              "keyboard", "monsoon", "victory", "thunder"]
HANG_ART = ["  ┌─┐\n  │\n  │\n  │\n__┴__", "  ┌─┐\n  │ O\n  │\n  │\n__┴__",
            "  ┌─┐\n  │ O\n  │ │\n  │\n__┴__", "  ┌─┐\n  │ O\n  │/│\n  │\n__┴__",
            "  ┌─┐\n  │ O\n  │/│\\\n  │\n__┴__", "  ┌─┐\n  │ O\n  │/│\\\n  │/\n__┴__",
            "  ┌─┐\n  │ O\n  │/│\\\n  │/ \\\n__┴__"]


@cmd("hangman", aliases=("hang",), cat="fun", desc="hangman · letter guess",
     usage="hangman | hang <letter>", sudo=False, cool=2)
async def c_hangman(update: Update, ctx, args):
    chat_id = str(update.effective_chat.id)
    g = DB.data.get("hang_" + chat_id)
    word = args.strip().lower()[:1]
    if not g or not word.isalpha():
        g = {"w": random.choice(HANG_WORDS), "got": [], "life": 0}
        DB.data["hang_" + chat_id] = g
        await DB.save()
        return await say(update, "<pre>%s</pre>\n🔤 <b>%s</b>\n💚 lives · <b>%d</b>\n"
                                 "<i>%s</i>" % (HANG_ART[0],
                                                " ".join("_" for _ in g["w"]),
                                                7 - g["life"], smallcaps("hang a")))
    if word in g["got"]:
        return await say(update, "🔁 <b>%s</b> pehle bola tha" % word)
    g["got"].append(word)
    if word not in g["w"]:
        g["life"] += 1
    await DB.save()
    shown = " ".join(c if c in g["got"] else "_" for c in g["w"])
    if all(c in g["got"] for c in g["w"]):
        DB.data.pop("hang_" + chat_id, None)
        await DB.save()
        return await say(update, "🏆 <b>%s</b> · jeet gaya! word tha <b>%s</b>" % (
            esc(update.effective_user.first_name or "you"), g["w"]))
    if g["life"] >= 7:
        DB.data.pop("hang_" + chat_id, None)
        await DB.save()
        return await say(update, "<pre>%s</pre>\n💀 game over · word tha <b>%s</b>" % (
            HANG_ART[6], g["w"]))
    await say(update, "<pre>%s</pre>\n🔤 <b>%s</b>\n💚 lives · <b>%d</b>" % (
        HANG_ART[min(g["life"], 6)], shown, 7 - g["life"]))


@cmd("emojirain", aliases=("erain",), cat="anim", desc="emoji barish animation",
     usage="emojirain [emoji]", sudo=False, cool=4)
async def c_emojirain(update: Update, ctx, args):
    e = (args.strip()[:2] or random.choice(["✨", "💜", "🔥", "⭐"]))
    cols = 7
    m = await say(update, e)
    for step in range(6):
        grid = []
        for r in range(4):
            row = "".join(e if (r + step) % 4 == (c + step) % 4 else "ㅤ" for c in range(cols))
            grid.append(row)
        try:
            await m.edit_text("\n".join(grid))
        except TelegramError:
            pass
        await asyncio.sleep(0.35)
    try:
        await m.edit_text("✨ %s <b>%s</b>" % (e, smallcaps("barish khatam")),
                          parse_mode=ParseMode.HTML)
    except TelegramError:
        pass


# ── system / misc jo repo files se unique the ─────────────────────

@cmd("threads", cat="util", desc="threads + python info", usage="threads", sudo=False)
async def c_threads(update: Update, ctx, args):
    import threading
    rows = ["🧵 threads · <b>%d</b>" % threading.active_count(),
            "🐍 python · <b>%s</b>" % sys.version.split()[0],
            "🖥 pid · <b>%d</b>" % os.getpid(),
            "⏱ uptime · <b>%s</b>" % hms(time.time() - START_TS),
            "📦 tasks · <b>%d</b>" % len(asyncio.all_tasks())]
    await edit_say(update, card("runtime", [("info", rows)], icon=E["brain"]))


@cmd("sysinfo", aliases=("server",), cat="util", desc="server cpu / ram / disk",
     usage="sysinfo", sudo=False)
async def c_sysinfo(update: Update, ctx, args):
    def mem() -> Tuple[float, float]:
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k] = float(v.strip().split()[0])
            total = info.get("MemTotal", 0) / 1024
            avail = info.get("MemAvailable", 0) / 1024
            return total, total - avail
        except Exception:
            return 0.0, 0.0
    total, used = mem()
    du = shutil.disk_usage(str(BASE_DIR))
    rows = ["⚙️ load · <b>%.2f</b>" % (os.getloadavg()[0] if hasattr(os, "getloadavg") else 0),
            "🧠 ram · <b>%s / %s</b>" % (human_size(used * 1024 * 1024),
                                        human_size(total * 1024 * 1024)),
            "💾 disk · <b>%s / %s</b>" % (human_size(du.used), human_size(du.total)),
            "🐍 %s" % sys.version.split()[0],
            "⏱ %s" % hms(time.time() - START_TS)]
    await edit_say(update, card("server", [("stats", rows)], icon=E["tool"]))


@cmd("refresh", aliases=("reload",), cat="core", desc="slash-menu dobara set",
     usage="refresh", owner=True)
async def c_refresh(update: Update, ctx, args):
    cmds = [BotCommand("start", "bot on"), BotCommand("menu", "full panel"),
            BotCommand("help", "help"), BotCommand("ping", "speed"),
            BotCommand("setname", "bot ka naam"), BotCommand("setdesc", "description"),
            BotCommand("setpfp", "profile photo"), BotCommand("prefix", "prefix on/off")]
    for scope in (BotCommandScopeDefault(), BotCommandScopeAllPrivateChats(),
                  BotCommandScopeAllGroupChats()):
        try:
            await BOT.set_my_commands(cmds, scope=scope)
        except TelegramError:
            pass
    await say(update, "♻️ ᴍᴇɴᴜ ʀᴇꜰʀᴇꜱʜᴇᴅ · <b>%d</b> cmds" % len(COMMANDS))


@cmd("currency", aliases=("fx", "rate"), cat="util", desc="currency convert",
     usage="currency 100 usd inr", sudo=False)
async def c_currency(update: Update, ctx, args):
    p = args.upper().replace("IN", " IN ").split()
    amt = 1.0
    if p and re.fullmatch(r"[\d.]+", p[0]):
        amt = float(p.pop(0))
    src, dst = ("USD", "INR")
    if len(p) >= 2:
        src, dst = p[0][:3], p[1][:3]
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://api.frankfurter.app/latest",
                              params={"from": src, "to": dst})
        rate = r.json()["rates"][dst]
        await say(update, hbox("%s → %s" % (src, dst), [
            "💱 rate · <b>%.4f</b>" % rate,
            "💰 <b>%s %s</b> = <b>%s %s</b>" % (
                ("%g" % amt), src, ("%.2f" % (amt * rate)), dst)],
            footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["coin"]))
    except Exception as exc:
        await say(update, "❌ rate fail · <code>%s</code>" % esc(str(exc)[:60]))


@cmd("shorten", aliases=("shorturl",), cat="util", desc="link chhota karo",
     usage="shorten <url>", sudo=False)
async def c_shorten(update: Update, ctx, args):
    u = (args.strip() or "").split()[0] if args.strip() else ""
    if not u.startswith("http"):
        return await say(update, "❌ link do")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as cli:
            r = await cli.get("https://is.gd/create.php",
                              params={"format": "simple", "url": u})
        out = r.text.strip()
        if not out.startswith("http"):
            raise ValueError(out[:60])
        await say(update, "🔗 <code>%s</code>\n<i>%s</i>" % (esc(out), esc(u[:70])))
    except Exception:
        await say(update, "❌ shorten fail")


@cmd("ascii", aliases=("bigtext",), cat="util", desc="bada ascii text",
     usage="ascii <text>", sudo=False)
async def c_ascii(update: Update, ctx, args):
    t = (args.strip() or "NIK")[:10].upper()
    font = {
        "A": ["█▀█", "█▀█", "▀ ▀"], "B": ["█▀▄", "█▀▄", "▀▀ "],
        "C": ["█▀▀", "█  ", "▀▀▀"], "D": ["█▀▄", "█ █", "▀▀ "],
        "E": ["█▀▀", "█▀▀", "▀▀▀"], "F": ["█▀▀", "█▀▀", "▀  "],
        "G": ["█▀▀", "█ █", "▀▀▀"], "H": ["█ █", "█▀█", "▀ ▀"],
        "I": ["█", "█", "▀"], "J": ["  █", "  █", "▀▀ "],
        "K": ["█ █", "█▀▄", "▀ ▀"], "L": ["█  ", "█  ", "▀▀▀"],
        "M": ["█▄█", "█ █", "▀ ▀"], "N": ["█▄ █", "█ ▀█", "▀  ▀"],
        "O": ["█▀█", "█ █", "▀▀▀"], "P": ["█▀█", "█▀▀", "▀  "],
        "Q": ["█▀█", "█ █", "▀▀█"], "R": ["█▀█", "█▀▄", "▀ ▀"],
        "S": ["█▀▀", "▀▀█", "▀▀▀"], "T": ["▀█▀", " █ ", " ▀ "],
        "U": ["█ █", "█ █", "▀▀▀"], "V": ["█ █", "█ █", " ▀ "],
        "W": ["█ █", "█▄█", "▀ ▀"], "X": ["█ █", " ▄ ", "▀ ▀"],
        "Y": ["█ █", " █ ", " ▀ "], "Z": ["▀▀█", "▄▀ ", "▀▀▀"],
        " ": ["  ", "  ", "  "],
    }
    rows = [" ".join(font.get(c, font[" "])[i] for c in t) for i in range(3)]
    await say(update, "<pre>%s</pre>" % esc("\n".join(rows)))


@cmd("urban", cat="fun", desc="urban dictionary", usage="urban <word>", sudo=False)
async def c_urban(update: Update, ctx, args):
    w = args.strip()
    if not w:
        return await say(update, "❌ word do")
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://api.urbandictionary.com/v0/define",
                              params={"term": w})
        js = r.json()
        if not js.get("list"):
            raise ValueError("nahi mila")
        d = js["list"][0]
        mean = re.sub(r"[\[\]]", "", d["definition"])[:600]
        await say(update, "📖 <b>%s</b>\n\n%s" % (esc(d["word"]), esc(mean)))
    except Exception:
        await say(update, "❌ word nahi mila")

# ══════════════════════════════════════════════════════════════════
# 19 · UTILITY
# ══════════════════════════════════════════════════════════════════

def _arg(update: Update, args: str) -> str:
    if args.strip():
        return args.strip()
    r = update.effective_message.reply_to_message
    return (r.text or r.caption or "") if r else ""


@cmd("calc", aliases=("math", "c2"), cat="util", desc="calculator", usage="calc 2*(3+4)", sudo=False)
async def c_calc(update, ctx, args):
    expr = _arg(update, args)
    if not expr:
        return await say(update, "❌ <code>%scalc 2+2</code>" % prefixes()[0])
    if not re.fullmatch(r"[0-9+\-*/%(). ^,eEa-z_]*", expr):
        return await say(update, "❌ sirf numbers + - * / % ^ ( )")
    import builtins as _bi
    safe = {"__builtins__": {}}
    for fn in ("abs", "round", "min", "max", "sum", "pow"):
        safe[fn] = getattr(_bi, fn)
    try:
        expr2 = expr.replace("^", "**")
        expr2 = re.sub(r"\b(sqrt|sin|cos|tan|log)\(",
                       lambda m: "math.%s(" % m.group(1), expr2)
        val = eval(expr2, {"__builtins__": {}}, dict(safe, math=math))  # noqa: S307
    except Exception as exc:
        return await say(update, "❌ %s" % esc(str(exc)[:80]))
    await say(update, hbox("ᴄᴀʟᴄ", ["📥 <code>%s</code>" % esc(expr[:120]),
                                     "📤 <b>%s</b>" % esc(val)], icon=E["tool"]))


@cmd("encode", aliases=("b64", "enc"), cat="util", desc="base64 encode", usage="encode <text>", sudo=False)
async def c_encode(update, ctx, args):
    t = _arg(update, args)
    if not t:
        return await say(update, "❌ text do")
    await say(update, "<code>%s</code>" % esc(base64.b64encode(t.encode()).decode()))


@cmd("decode", aliases=("unb64", "dec"), cat="util", desc="base64 decode", usage="decode <b64>", sudo=False)
async def c_decode(update, ctx, args):
    t = _arg(update, args)
    try:
        out = base64.b64decode(t + "===").decode("utf-8", "ignore")
    except Exception:
        return await say(update, "❌ invalid base64")
    await say(update, "<code>%s</code>" % esc(out[:2000]))


@cmd("hash", aliases=("md5", "sha"), cat="util", desc="hash (md5/sha1/sha256/sha512)", usage="hash <text>", sudo=False)
async def c_hash(update, ctx, args):
    t = _arg(update, args)
    if not t:
        return await say(update, "❌ text do")
    b = t.encode()
    await say(update, hbox("ʜᴀꜱʜ", [
        "md5 · <code>%s</code>" % hashlib.md5(b).hexdigest(),
        "sha1 · <code>%s</code>" % hashlib.sha1(b).hexdigest(),
        "sha256 · <code>%s</code>" % hashlib.sha256(b).hexdigest()[:48] + "…"],
        icon=E["lock"]))


@cmd("qr", aliases=("qrcode",), cat="util", desc="qr banao", usage="qr <text|link>", sudo=False)
async def c_qr(update, ctx, args):
    t = _arg(update, args) or "https://t.me/%s" % OWNER_USERNAME
    url = "https://api.qrserver.com/v1/create-qr-code/?size=600x600&data=" + \
        urllib.parse.quote(t)
    try:
        await BOT.send_photo(update.effective_chat.id, url,
                             caption="🔳 <code>%s</code>" % esc(t[:80]),
                             parse_mode=ParseMode.HTML)
    except TelegramError as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))


@cmd("morse", cat="util", desc="morse code", usage="morse <text>", sudo=False)
async def c_morse(update, ctx, args):
    t = _arg(update, args).upper()
    table = {**{c: m for c, m in zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        [".-", "-...", "-.-.", "-..", ".", "..-.", "--.", "....", "..", ".---",
         "-.-", ".-..", "--", "-.", "---", ".--.", "--.-", ".-.", "...", "-",
         "..-", "...-", ".--", "-..-", "-.--", "--..", "-----", ".----", "..---",
         "...--", "....-", ".....", "-....", "--...", "---..", "----."])}}
    out = " ".join(table.get(c, c) if c != " " else "/" for c in t)
    await say(update, "<code>%s</code>" % esc(out[:3000]))


@cmd("binary", aliases=("bin",), cat="util", desc="text → binary", usage="binary <text>", sudo=False)
async def c_binary(update, ctx, args):
    t = _arg(update, args)
    if not t:
        return await say(update, "❌ text do")
    await say(update, "<code>%s</code>" % " ".join(format(ord(c), "08b") for c in t)[:3500])


@cmd("unbinary", aliases=("unbin",), cat="util", desc="binary → text", usage="unbinary <bits>", sudo=False)
async def c_unbinary(update, ctx, args):
    t = _arg(update, args)
    try:
        out = "".join(chr(int(b, 2)) for b in t.split())
    except Exception:
        return await say(update, "❌ invalid")
    await say(update, "<code>%s</code>" % esc(out[:2000]))


@cmd("rot13", cat="util", desc="rot13", usage="rot13 <text>", sudo=False)
async def c_rot13(update, ctx, args):
    import codecs
    t = _arg(update, args)
    await say(update, "<code>%s</code>" % esc(codecs.encode(t, "rot13")[:2000]))


@cmd("fancy", aliases=("font",), cat="util", desc="fancy fonts", usage="fancy <style> <text>", sudo=False)
async def c_fancy(update, ctx, args):
    parts = args.split(maxsplit=1)
    style = "bold"
    body = args
    if parts and parts[0].lower() in _FANCY:
        style = parts[0].lower()
        body = parts[1] if len(parts) > 1 else ""
    if not body.strip():
        styles = " · ".join(fancy(s, s) for s in _FANCY)
        return await say(update, styles + "\n\n<code>%sfancy mono Nik</code>" % prefixes()[0])
    await say(update, esc(fancy(body, style)))


@cmd("smallcaps", aliases=("sc",), cat="util", desc="small caps", usage="smallcaps <text>", sudo=False)
async def c_sc(update, ctx, args):
    await say(update, esc(smallcaps(_arg(update, args) or "nik bot")))


@cmd("reverse", aliases=("rev2",), cat="util", desc="reverse text", usage="reverse <text>", sudo=False)
async def c_reverse(update, ctx, args):
    t = _arg(update, args)
    await say(update, esc(t[::-1]))


@cmd("wc", aliases=("wordcount", "cc"), cat="util", desc="text stats", usage="wc <text>", sudo=False)
async def c_wc(update, ctx, args):
    t = _arg(update, args)
    await say(update, hbox("ᴄᴏᴜɴᴛ", [
        "🔤 chars · <b>%d</b>" % len(t),
        "📝 words · <b>%d</b>" % len(t.split()),
        "📄 lines · <b>%d</b>" % (t.count("\n") + 1)], icon=E["chart"]))


@cmd("upper", cat="util", desc="UPPERCASE", usage="upper <text>", sudo=False)
async def c_upper(update, ctx, args):
    await say(update, esc(_arg(update, args).upper()))


@cmd("lower", cat="util", desc="lowercase", usage="lower <text>", sudo=False)
async def c_lower(update, ctx, args):
    await say(update, esc(_arg(update, args).lower()))


@cmd("uuid", cat="util", desc="uuid4", usage="uuid", sudo=False)
async def c_uuid(update, ctx, args):
    await say(update, "<code>%s</code>" % uuid.uuid4())


@cmd("password", aliases=("pass", "pw"), cat="util", desc="strong password", usage="password [len]", sudo=False)
async def c_password(update, ctx, args):
    n = int(args.strip()) if args.strip().isdigit() else 16
    n = max(6, min(n, 64))
    pool = string.ascii_letters + string.digits + "!@#$%^&*"
    await say(update, "🔐 <code>%s</code>" % esc("".join(random.choice(pool) for _ in range(n))))


@cmd("time", cat="util", desc="time zones", usage="time", sudo=False)
async def c_time(update, ctx, args):
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for name, off in (("IST", 5.5), ("UTC", 0), ("DUBAI", 4), ("TOKYO", 9), ("NY", -4)):
        t = now + dt.timedelta(hours=off)
        rows.append("🕐 %s · <b>%s</b>" % (name, t.strftime("%H:%M")))
    await say(update, hbox("ᴛɪᴍᴇ", rows, footer=now.strftime("%d %b %Y"), icon=E["clock"]))


@cmd("weather", aliases=("wthr",), cat="util", desc="weather (city)", usage="weather <city>", sudo=False)
async def c_weather(update, ctx, args):
    city = args.strip() or "Kota"
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://wttr.in/%s?format=j1" % urllib.parse.quote(city))
        j = r.json()
        cur = j["current_condition"][0]
        await say(update, hbox("ᴡᴇᴀᴛʜᴇʀ · %s" % city.upper(), [
            "🌡 temp · <b>%s°C</b>" % cur["temp_C"],
            "🤔 feels · <b>%s°C</b>" % cur["FeelsLikeC"],
            "☁️ %s" % esc(cur["weatherDesc"][0]["value"]),
            "💧 humidity · <b>%s%%</b>" % cur["humidity"],
            "💨 wind · <b>%s km/h</b>" % cur["windspeedKmph"]], icon=E["cloud"]))
    except Exception as exc:
        await say(update, "❌ weather fail · <code>%s</code>" % esc(str(exc)[:60]))


@cmd("wiki", cat="util", desc="wikipedia summary", usage="wiki <topic>", sudo=False)
async def c_wiki(update, ctx, args):
    q = args.strip()
    if not q:
        return await say(update, "❌ topic do")
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                              urllib.parse.quote(q.replace(" ", "_")))
        j = r.json()
        if "extract" not in j:
            raise ValueError("no result")
        await say(update, "📖 <b>%s</b>\n\n%s" % (esc(j["title"]), esc(j["extract"][:900])))
    except Exception:
        await say(update, "❌ wikipedia me nahi mila")


@cmd("translate", aliases=("tr",), cat="util", desc="translate (auto → en/hi)", usage="translate <lang> <text>", sudo=False)
async def c_translate(update, ctx, args):
    parts = args.split(maxsplit=1)
    lang = "en"
    body = args
    if parts and re.fullmatch(r"[a-zA-Z-]{2,5}", parts[0]):
        lang = parts[0].lower()
        body = parts[1] if len(parts) > 1 else ""
    body = body.strip()
    if not body:
        return await say(update, "❌ <code>%stranslate hi hello world</code>" % prefixes()[0])
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": lang, "dt": "t", "q": body}
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get(url, params=params)
        data = r.json()
        out = "".join(seg[0] for seg in data[0])
        await say(update, "🌐 <b>%s</b>\n\n%s" % (lang, esc(out[:1500])))
    except Exception as exc:
        await say(update, "❌ translate fail · <code>%s</code>" % esc(str(exc)[:60]))


@cmd("tts", aliases=("voice", "speak"), cat="util", desc="text → voice", usage="tts <text>", sudo=False)
async def c_tts(update, ctx, args):
    text = _arg(update, args)
    if not text:
        return await say(update, "❌ text do")
    m = await say(update, load_card("pulse", "laguage loading", 1, 25))
    try:
        from gtts import gTTS
        fp = MEDIA_DIR / ("tts_%d.mp3" % int(time.time()))
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: gTTS(text=text[:400], lang="hi").save(str(fp)))
        await BOT.send_voice(update.effective_chat.id, InputFile(str(fp), "voice.mp3"),
                             caption="🔊 " + esc(text[:60]))
    except Exception as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))
    finally:
        try:
            await m.delete()
        except TelegramError:
            pass


@cmd("ip", aliases=("ipinfo", "myip"), cat="util", desc="ip info", usage="ip [ip]", sudo=False)
async def c_ip(update, ctx, args):
    q = args.strip()
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("http://ip-api.com/json/" + urllib.parse.quote(q))
        j = r.json()
        if j.get("status") != "success":
            raise ValueError("fail")
        await say(update, hbox("ɪᴘ ɪɴꜰᴏ", [
            "🌍 <b>%s</b>" % esc(j.get("query", "")),
            "🏳 %s, %s" % (esc(j.get("country", "")), esc(j.get("city", ""))),
            "📡 isp · %s" % esc(j.get("isp", "")),
            "🕐 tz · %s" % esc(j.get("timezone", ""))], icon=E["earth"]))
    except Exception:
        await say(update, "❌ ip info fail")


def _ytdlp_ok() -> bool:
    return shutil.which("yt-dlp") is not None or True


async def _yt_search(query: str, audio: bool = True) -> Optional[Path]:
    """yt-dlp se pehla result download. Returns path or None."""
    out_tpl = str(MEDIA_DIR / "%(title).60s.%(ext)s")
    cmd = YTDLP + [
        "--no-playlist", "--no-warnings", "--quiet", "--no-progress",
        "-f", "bestaudio/best" if audio else "bv*[height<=720]+ba/b[height<=720]",
        "-o", out_tpl,
        "--print", "after_move:filepath",
    ]
    if audio:
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    cmd += [query if query.startswith("http") else "ytsearch1:%s" % query]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
    lines = [l.strip() for l in out.decode(errors="ignore").splitlines() if l.strip()]
    for l in reversed(lines):
        p = Path(l)
        if p.exists() and p.is_file():
            return p
    return None


async def _music(update: Update, args: str, audio: bool) -> None:
    q = _arg(update, args)
    if not q:
        return await say(update, "❌ <code>%ssong kesariya</code>" % prefixes()[0])
    m = await say(update, load_card("search", "searching %s" % q[:28], 1, 12))
    try:
        path = await _yt_search(q, audio=audio)
        if not path:
            return await edit_say(update, "❌ kuch nahi mila")
        pct = 60
        for i in range(3):
            try:
                await m.edit_text(load_card("send" if audio else "down",
                                            "uploading", i + 2, pct + i * 15))
            except TelegramError:
                pass
            await asyncio.sleep(0.4)
        size = human_size(path.stat().st_size)
        if audio:
            await BOT.send_audio(update.effective_chat.id,
                                 InputFile(str(path), path.name),
                                 title=path.stem[:64], performer="Nik Bot",
                                 caption="🎼 <b>%s</b>\n💾 %s" % (esc(path.stem[:60]), size),
                                 parse_mode=ParseMode.HTML,
                                 reply_to_message_id=update.effective_message.message_id,
                                 allow_sending_without_reply=True)
        else:
            await BOT.send_video(update.effective_chat.id,
                                 InputFile(str(path), path.name),
                                 caption="🎬 <b>%s</b>\n💾 %s" % (esc(path.stem[:60]), size),
                                 parse_mode=ParseMode.HTML,
                                 reply_to_message_id=update.effective_message.message_id,
                                 allow_sending_without_reply=True)
    except asyncio.TimeoutError:
        await edit_say(update, "⌛ timeout — chhota query try kar")
    except Exception as exc:
        await edit_say(update, "❌ <code>%s</code>" % esc(str(exc)[:120]))
    finally:
        try:
            await m.delete()
        except TelegramError:
            pass
        for p in MEDIA_DIR.glob("*"):
            try:
                if time.time() - p.stat().st_mtime > 900:
                    p.unlink()
            except OSError:
                pass


@cmd("song", aliases=("music", "audio", "mp3"), cat="media",
     desc="gaana download (mp3)", usage="song <query|link>", sudo=False, cool=4)
async def c_song(update, ctx, args):
    await _music(update, args, audio=True)


@cmd("video", aliases=("vid", "mp4"), cat="media",
     desc="video download", usage="video <query|link>", sudo=False, cool=4)
async def c_video(update, ctx, args):
    await _music(update, args, audio=False)


@cmd("yt", aliases=("ytdl",), cat="media", desc="yt link → media",
     usage="yt <link>", sudo=False, cool=4)
async def c_yt(update, ctx, args):
    q = args.strip()
    await _music(update, q, audio=not q.startswith("http") or "music" in q or "song" in q)


@cmd("lyrics", aliases=("bol",), cat="media", desc="song lyrics",
     usage="lyrics <song>", sudo=False)
async def c_lyrics(update, ctx, args):
    q = args.strip()
    if not q:
        return await say(update, "❌ song naam do")
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            s = await cli.get("https://api.lyrics.ovh/suggest/" + urllib.parse.quote(q))
        data = s.json()["data"][0]
        title, artist = data["title"], data["artist"]["name"]
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://api.lyrics.ovh/v1/%s/%s" % (
                urllib.parse.quote(artist), urllib.parse.quote(title)))
        lyr = r.json().get("lyrics", "")
        if not lyr:
            raise ValueError
        await say(update, "🎤 <b>%s</b> — %s\n\n<pre>%s</pre>" % (
            esc(title), esc(artist), esc(lyr[:3000])))
    except Exception:
        await say(update, "❌ lyrics nahi mile")


@cmd("sticker", aliases=("s2", "st"), cat="media", desc="photo → sticker",
     usage="sticker (photo reply)", sudo=False)
async def c_sticker(update, ctx, args):
    img = await _media_bytes(update.effective_message.reply_to_message)
    if not img:
        return await say(update, "❌ photo reply karo")
    try:
        await BOT.send_sticker(update.effective_chat.id,
                               InputFile(io.BytesIO(img), "s.webp"))
    except TelegramError as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))


@cmd("toimg", aliases=("unsticker", "s2img"), cat="media", desc="sticker → photo",
     usage="toimg (sticker reply)", sudo=False)
async def c_toimg(update, ctx, args):
    r = update.effective_message.reply_to_message
    if not (r and r.sticker):
        return await say(update, "❌ sticker reply karo")
    try:
        f = await BOT.get_file(r.sticker.file_id)
        raw = bytes(await f.download_as_bytearray())
        await BOT.send_photo(update.effective_chat.id, InputFile(io.BytesIO(raw), "img.png"))
    except TelegramError as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))


@cmd("topdf", aliases=("pdf",), cat="media", desc="photos → pdf",
     usage="topdf (photo reply)", sudo=False)
async def c_topdf(update, ctx, args):
    r = update.effective_message.reply_to_message
    if not (r and r.photo):
        return await say(update, "❌ photo reply karo")
    try:
        from PIL import Image
        f = await BOT.get_file(r.photo[-1].file_id)
        raw = bytes(await f.download_as_bytearray())
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PDF")
        buf.seek(0)
        await BOT.send_document(update.effective_chat.id,
                                InputFile(buf, "nik.pdf"), caption="📄 pdf ready")
    except Exception as exc:
        await say(update, "❌ %s" % esc(str(exc)[:100]))


# ══════════════════════════════════════════════════════════════════
# 21 · ANIMATIONS  —  ek cmd, multi-frame edit, poori group dekhti hai
# ══════════════════════════════════════════════════════════════════

def _mood_frames(icon: str, word: str, line: str) -> List[str]:
    base = [icon, icon + " " + icon, "〔 %s 〕" % icon,
            "〔 %s 〕 %s" % (icon, smallcaps(word)),
            "〔 %s 〕  %s\n%s" % (icon, smallcaps(word), ANIM_WAVE[2]),
            "〔 %s 〕  %s\n%s %s" % (icon, smallcaps(word), bar(70), "✨"),
            "%s  <b>%s</b>\n%s" % (icon, smallcaps(word), esc(line))]
    return base


async def _mood(update: Update, icon: str, word: str, line: str) -> None:
    m = await say(update, icon)
    for fr in _mood_frames(icon, word, line):
        try:
            await m.edit_text(fr, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass
        await asyncio.sleep(0.32)


@cmd("hy", aliases=("hi", "hello", "hey", "hola"), cat="anim", desc="entry animation",
     usage="hy", sudo=False, cool=3)
async def c_hy(update, ctx, args):
    u = update.effective_user
    await _mood(update, "🫡", "hello %s" % (u.first_name or "dost"),
                "ᴋʏᴀ ʜᴀᴀʟ ʜᴀɪ · ɴɪᴋ ʙᴏᴛ ᴏɴʟɪɴᴇ ⚡")


@cmd("gm", aliases=("goodmorning",), cat="anim", desc="good morning", usage="gm", sudo=False, cool=3)
async def c_gm(update, ctx, args):
    await _mood(update, "🌅", "good morning", "ᴀᴀᴊ ᴋᴀ ᴅɪɴ ɢᴀᴀɴᴅ ʜᴀɪ 🔥")


@cmd("gn", aliases=("goodnight",), cat="anim", desc="good night", usage="gn", sudo=False, cool=3)
async def c_gn(update, ctx, args):
    await _mood(update, "🌙", "good night", "ꜱᴏ ᴊᴀᴏ ᴠᴀʀɴᴀ ᴍᴀɪ ɴᴇᴇɴᴅ ʜᴜ 🥱")


@cmd("bye", cat="anim", desc="bye animation", usage="bye", sudo=False, cool=3)
async def c_bye(update, ctx, args):
    await _mood(update, "👋", "bye bye", "ᴊᴀᴀ ʀᴀʜᴀ ʜᴜ · ᴍɪꜱꜱ ᴋᴀʀɴᴀ 💜")


@cmd("love", aliases=("ily",), cat="anim", desc="love animation", usage="love", sudo=False, cool=3)
async def c_love(update, ctx, args):
    await _mood(update, "💜", "love you", "ᴘʏᴀᴀʀ ʜᴀɪ · ᴛᴜ ᴍᴇʀᴀ ʟᴏɢᴏɴ ᴄʀᴇᴅɪᴛ ʜᴀɪ ❤️")


@cmd("hug", cat="anim", desc="hug", usage="hug [reply]", sudo=False, cool=3)
async def c_hug(update, ctx, args):
    r = update.effective_message.reply_to_message
    who = (r.from_user.first_name if r and r.from_user else "sabko")
    await _mood(update, "🫂", "hug", "ɢᴀʟᴇ ʟᴀɢ ᴊᴀᴏ %s 🤍" % esc(who))


@cmd("slap", cat="anim", desc="slap", usage="slap [reply]", sudo=False, cool=3)
async def c_slap(update, ctx, args):
    r = update.effective_message.reply_to_message
    who = (r.from_user.first_name if r and r.from_user else "tum")
    await _mood(update, "🖐", "slap", "%s ᴋᴏ ᴛʜᴀᴘᴘᴀᴅ ʟᴀɢᴀ 💥" % esc(who))


@cmd("dance", cat="anim", desc="dance", usage="dance", sudo=False, cool=3)
async def c_dance(update, ctx, args):
    await _mood(update, "🕺", "dance", "ᴄʜᴀʟ ᴛʜᴜᴍᴋᴀ 🎶")


@cmd("wave", cat="anim", desc="wave", usage="wave", sudo=False, cool=3)
async def c_wave(update, ctx, args):
    await _mood(update, "👋", "wave", "ʜᴀɴᴅ ᴡᴀᴠᴇ · ʜɪ ꜱᴜɴ ᴛᴜ 🫶")


@cmd("sad", aliases=("cry",), cat="anim", desc="sad animation", usage="sad", sudo=False, cool=3)
async def c_sad(update, ctx, args):
    await _mood(update, "🥀", "sad", "ᴅɪʟ ʙʜᴀʀɪ ʜᴀɪ · ᴄʜᴏᴋᴏʟᴇᴛ ʙʜᴇᴊ 💔")


@cmd("angry", cat="anim", desc="angry", usage="angry", sudo=False, cool=3)
async def c_angry(update, ctx, args):
    await _mood(update, "😡", "angry", "ɢᴜꜱꜱᴀ ᴍᴀᴛ ᴋᴀʀ · ᴘᴀɴɪ ᴘɪ 🥤")


@cmd("wow", cat="anim", desc="wow", usage="wow", sudo=False, cool=3)
async def c_wow(update, ctx, args):
    await _mood(update, "🤯", "wow", "ᴋʏᴀ ʙᴀᴀᴛ ʜᴀɪ ʙʜᴀɪ 🔥")


@cmd("respect", aliases=("salute",), cat="anim", desc="respect", usage="respect", sudo=False, cool=3)
async def c_respect(update, ctx, args):
    await _mood(update, "🫡", "respect", "ꜱᴀʟᴜᴛᴇ ʜᴀɪ ʙᴏꜱꜱ ⚡")


@cmd("thanks", aliases=("ty",), cat="anim", desc="thanks", usage="thanks", sudo=False, cool=3)
async def c_thanks(update, ctx, args):
    await _mood(update, "🙏", "thankyou", "ᴛʜᴀɴᴋꜱ ʙʜᴀɪ · ᴋᴀᴀᴍ ʜᴏ ɢᴀʏᴀ ✅")


@cmd("sorry", cat="anim", desc="sorry", usage="sorry", sudo=False, cool=3)
async def c_sorry(update, ctx, args):
    await _mood(update, "🥺", "sorry", "ɢᴀʟᴛɪ ʜᴏ ɢᴀʏɪ · ᴍᴀᴀꜰ ᴋᴀʀ ᴅᴇ 🙏")


@cmd("congrats", aliases=("congrats2",), cat="anim", desc="congrats", usage="congrats", sudo=False, cool=3)
async def c_congrats(update, ctx, args):
    await _mood(update, "🎉", "congratulations", "ʙᴀᴅʜᴀɪ ʜᴏ · ᴘᴀʀᴛʏ ᴋᴀʙ 🎊")


@cmd("sleepy", aliases=("sona",), cat="anim", desc="sleepy", usage="sleepy", sudo=False, cool=3)
async def c_sleepy(update, ctx, args):
    await _mood(update, "😴", "sleepy", "ɴᴇᴇɴᴅ ʜᴀɪ ʏᴀᴀʀ · ɢᴏᴏᴅ ɴɪɢʜᴛ 🌙")


@cmd("bored", cat="anim", desc="bored", usage="bored", sudo=False, cool=3)
async def c_bored(update, ctx, args):
    await _mood(update, "🥱", "bored", "ʙᴏʀᴇ ʜᴏ ɢᴀʏᴀ · ᴋᴜᴄʜ ᴋᴀʀᴏ ʏᴀᴀʀ 💤")


@cmd("anim", aliases=("anim1",), cat="anim", desc="custom animation",
     usage="anim <text>", sudo=False, cool=3)
async def c_anim(update, ctx, args):
    word = (args.strip() or "NIK BOT")[:24]
    m = await say(update, "▱▱▱▱▱▱▱▱▱▱")
    for i, fr in enumerate(ANIM_LOAD):
        try:
            await m.edit_text("%s\n<b>%s</b>" % (fr, esc(smallcaps(word))),
                              parse_mode=ParseMode.HTML)
        except TelegramError:
            pass
        await asyncio.sleep(0.28)
    try:
        await m.edit_text("⚡ <b>%s</b>\n%s" % (esc(smallcaps(word)), bar(100)),
                          parse_mode=ParseMode.HTML)
    except TelegramError:
        pass


# ══════════════════════════════════════════════════════════════════
# 22 · AI TOOLS  (free endpoints, koi key nahi)
# ══════════════════════════════════════════════════════════════════

@cmd("ai", aliases=("ask", "gpt", "bot"), cat="ai", desc="ai se poocho",
     usage="ai <question>", sudo=False)
async def c_ai(update, ctx, args):
    q = args.strip()
    if not q:
        return await say(update, "❌ <code>%sai batao python kya hai</code>" % prefixes()[0])
    m = await say(update, load_card("think", "soch raha hoon", 1, 30))
    try:
        async with httpx.AsyncClient(timeout=60) as cli:
            r = await cli.get("https://text.pollinations.ai/" + urllib.parse.quote(q[:1500]))
        out = r.text.strip()
        if not out:
            raise ValueError("empty")
        try:
            await m.edit_text("🧠 <b>%s</b>\n\n%s" % (esc(q[:80]), esc(out[:3000])),
                              parse_mode=ParseMode.HTML)
        except TelegramError:
            await say(update, esc(out[:3000]))
    except Exception as exc:
        await edit_say(update, "❌ ai fail · <code>%s</code>" % esc(str(exc)[:80]))


@cmd("imagine", aliases=("img", "draw", "pic2"), cat="ai", desc="ai image banao",
     usage="imagine <prompt>", sudo=False, cool=6)
async def c_imagine(update, ctx, args):
    p = args.strip()
    if not p:
        return await say(update, "❌ prompt do")
    m = await say(update, load_card("search", "image bana raha hoon", 1, 25))
    url = "https://image.pollinations.ai/prompt/%s?width=1024&height=1024&nologo=true" % \
        urllib.parse.quote(p[:400])
    try:
        await BOT.send_photo(update.effective_chat.id, url,
                             caption="🎨 <b>%s</b>" % esc(p[:150]),
                             parse_mode=ParseMode.HTML)
        await m.delete()
    except TelegramError as exc:
        await edit_say(update, "❌ %s" % esc(str(exc)[:100]))


@cmd("define", aliases=("dict", "meaning"), cat="ai", desc="dictionary meaning",
     usage="define <word>", sudo=False)
async def c_define(update, ctx, args):
    w = args.strip()
    if not w:
        return await say(update, "❌ word do")
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get("https://api.dictionaryapi.dev/api/v2/entries/en/" +
                              urllib.parse.quote(w))
        j = r.json()[0]
        mean = j["meanings"][0]["definitions"][0]["definition"]
        await say(update, "📚 <b>%s</b>\n\n%s" % (esc(j["word"]), esc(mean[:600])))
    except Exception:
        await say(update, "❌ word nahi mila")


@cmd("summarize", aliases=("sum",), cat="ai", desc="link ka summary",
     usage="summarize <url>", sudo=False)
async def c_summarize(update, ctx, args):
    u = args.strip()
    if not u.startswith("http"):
        return await say(update, "❌ link do")
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as cli:
            r = await cli.get(u)
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text,
                      flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        await say(update, "📄 <b>%s</b>\n\n%s…" % (esc(u[:60]), esc(text[:1200])))
    except Exception as exc:
        await say(update, "❌ %s" % esc(str(exc)[:90]))


# ══════════════════════════════════════════════════════════════════
# 23 · GLOBAL  —  gban / blacklist
# ══════════════════════════════════════════════════════════════════

@cmd("gban", cat="sudo", desc="global ban (har group me)", usage="gban <id> [reason]")
async def c_gban(update, ctx, args):
    u = await _target(update, args)
    if not u:
        return await say(update, "❌ id/@username/reply do")
    lst = DB.data.setdefault("gban", [])
    if u.id not in lst:
        lst.append(u.id)
        await DB.save()
    n = 0
    for cid in list(DB.data.get("chats", {})):
        if cid.startswith("-"):
            try:
                await BOT.ban_chat_member(int(cid), u.id)
                n += 1
            except TelegramError:
                pass
    await say(update, hbox("ɢʙᴀɴ", [
        "👤 <b>%s</b>" % esc(getattr(u, "first_name", str(u.id))),
        "🆔 <code>%s</code>" % u.id,
        "🔨 banned in · <b>%d</b> chats" % n],
        footer="ᴘᴏᴡᴇʀᴇᴅ ʙʏ @%s" % OWNER_USERNAME, icon=E["hammer"]))


@cmd("ungban", cat="sudo", desc="gban hatao", usage="ungban <id>")
async def c_ungban(update, ctx, args):
    u = await _target(update, args)
    if not u:
        return await say(update, "❌ id do")
    lst = DB.data.setdefault("gban", [])
    if u.id in lst:
        lst.remove(u.id)
        await DB.save()
    await say(update, "🕊 ᴜɴɢʙᴀɴ · <code>%s</code>" % u.id)


@cmd("gbanlist", aliases=("gl",), cat="sudo", desc="gban list", usage="gbanlist")
async def c_gbanlist(update, ctx, args):
    rows = ["🔨 <code>%s</code>" % u for u in DB.data.get("gban", [])[:30]]
    await edit_say(update, card("gban", [("banned", rows or ["<i>khaali</i>"])],
                                icon=E["hammer"]))


@cmd("blacklist", aliases=("bl2",), cat="sudo", desc="word blacklist add",
     usage="blacklist <word>", admin=True, only_group=True)
async def c_blacklist(update, ctx, args):
    w = args.strip().lower()
    if not w:
        return await say(update, "❌ word do")
    d = DB.data.setdefault("bl_words", {}).setdefault(str(update.effective_chat.id), [])
    if w not in d:
        d.append(w)
        await DB.save()
    await say(update, "🚫 ʙʟᴀᴄᴋʟɪꜱᴛᴇᴅ · <b>%s</b>" % esc(w))


@cmd("unblacklist", aliases=("unbl",), cat="sudo", desc="word hatao",
     usage="unblacklist <word|all>", admin=True, only_group=True)
async def c_unblacklist(update, ctx, args):
    d = DB.data.setdefault("bl_words", {}).setdefault(str(update.effective_chat.id), [])
    if args.strip() in ("all", "*"):
        d.clear()
    elif args.strip().lower() in d:
        d.remove(args.strip().lower())
    await DB.save()
    await say(update, "✅ ʀᴇᴍᴏᴠᴇᴅ")

# ══════════════════════════════════════════════════════════════════
# 24 · HANDLERS + RUNNER
# ══════════════════════════════════════════════════════════════════

async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    LOG.error("unhandled: %s", ctx.error, exc_info=ctx.error)


async def post_init(app: Application) -> None:
    global BOT
    BOT = app.bot
    me = await BOT.get_me()
    LOG.info("╔══════════════════════════════════════════╗")
    LOG.info("║  NIK BOT ONLINE · @%-22s ║", (me.username or me.id))
    LOG.info("║  commands: %-4d · categories: %-3d       ║", len(COMMANDS), len(CATEGORIES))
    LOG.info("╚══════════════════════════════════════════╝")
    # slash-menu (chhota, sirf main commands)
    cmds = [BotCommand("start", "bot on"), BotCommand("menu", "full panel"),
            BotCommand("help", "help"), BotCommand("ping", "speed"),
            BotCommand("setname", "bot ka naam"), BotCommand("setdesc", "description"),
            BotCommand("setpfp", "profile photo"), BotCommand("prefix", "prefix on/off")]
    for scope in (BotCommandScopeDefault(), BotCommandScopeAllPrivateChats(),
                  BotCommandScopeAllGroupChats()):
        try:
            await BOT.set_my_commands(cmds, scope=scope)
        except TelegramError:
            pass


async def health_server(port: int = 8080) -> None:
    """RDP/VPS keep-alive — http://ip:8080/ → uptime json."""
    from aiohttp import web

    async def _h(request: "web.Request") -> "web.Response":
        return web.json_response({
            "bot": BOT_NAME, "ok": True,
            "uptime": hms(time.time() - START_TS),
            "commands": len(COMMANDS),
        })

    app = web.Application()
    app.router.add_get("/", _h)
    app.router.add_get("/health", _h)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        LOG.info("health → http://0.0.0.0:%d/", port)
    except OSError as exc:
        LOG.warning("health server skip: %s", exc)


def build_app() -> Application:
    defaults = Defaults(parse_mode=None, disable_web_page_preview=True,
                        allow_sending_without_reply=True)
    app = (ApplicationBuilder()
           .token(TOKEN)
           .defaults(defaults)
           .rate_limiter(AIORateLimiter(max_retries=3))
           .concurrent_updates(True)
           .post_init(post_init)
           .build())

    # main router — saare commands ek hi jagah
    app.add_handler(MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL, router),
                    group=0)
    # guard (filters/antilink/antiflood) — commands ke baad
    app.add_handler(MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL, guard),
                    group=1)
    # welcome / goodbye
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS |
                                   filters.StatusUpdate.LEFT_CHAT_MEMBER, member_watcher),
                    group=2)
    # buttons
    app.add_handler(CallbackQueryHandler(cb_router))
    # member joins (captcha ke liye)
    app.add_handler(ChatMemberHandler(member_watcher,
                                      ChatMemberHandler.CHAT_MEMBER))
    app.add_error_handler(on_error)
    return app


async def run() -> None:
    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True,
                                    allowed_updates=Update.ALL_TYPES,
                                    timeout=30)
    try:
        await health_server(int(os.environ.get("NIK_PORT", "8080")))
    except Exception:
        pass
    LOG.info("polling started — Ctrl+C to stop")
    stop = asyncio.Event()
    try:
        await stop.wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def _selftest() -> None:
    print("commands:", len(COMMANDS), "| categories:", len(CATEGORIES))
    pages = _pages()
    print("menu pages:", len(pages), "| per page:", PAGE_SIZE)
    print("prefixes:", prefixes(), "| required:", prefix_required())
    missing = [c.name for c in COMMANDS.values() if not c.desc or not c.usage]
    print("incomplete meta:", missing or "none")
    unknown_cat = [c.name for c in COMMANDS.values() if c.cat not in CATEGORIES]
    print("unknown category:", unknown_cat or "none")
    print("emoji pack:", len(EMOJI_IDS), "ids")
    print(smallcaps("nik bot") + " · " + fancy("NIK", "script"))
    for name in ["ping", "menu", "song", "setname", "setpfp"]:
        c = COMMANDS.get(name)
        print(" ", name, "→", (c.desc if c else "MISSING"))
    print(build_menu_page(0)[:400])


if __name__ == "__main__":
    if "--check" in sys.argv:
        _selftest()
        raise SystemExit(0)
    if not TOKEN or "PASTE" in TOKEN or ":" not in TOKEN:
        print("❌ TOKEN set karo — file ke top pe TOKEN = \"123456:ABC…\"")
        raise SystemExit(1)
    if not OWNER_ID:
        print("⚠️  OWNER_ID 0 hai — .setname jaise owner commands kisi ke liye nahi chalenge")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nbye 👋")
