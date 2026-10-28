# ══════════════════════════════════════════════════════════════
#   NIK USERBOT · @Nikkkwa · single-file Telethon userbot (global)
# ══════════════════════════════════════════════════════════════
#  FILE MAP (order me hi sections hain):
#    01  imports · config · session (string/file)
#    02  json store + data dirs
#    03  style kit — sc/sb/mono/top/sub/hdr/close · E (emoji roles)
#    04  rich layer — _plainify · _rt · _ui_blocks · _ui_buttons
#                     _ui_build · _ui_render · _UiMsg (edit/delete)
#    05  core helpers — eor · flash · done · _del_after · align_panel
#    06  menu engine — _MENU · MENUPAGES/CATS · .mN · .menu · .help
#    07  commands — core → mod → auto → media → vc → bot mgr → spam …
#    08  reactions — AR_* (.ar .makear .r .rem .sar .selfsar) + lock watcher
#    09  misc cmds — .requests .approve .deny .rembots .lockmsg .check
#    10  music / download — MUSIC_FRAMES · _music_loader (▰▱▱▱▱)
#    11  voice chat — vsave/vplay/vlist + pytgcalls bridge
#    12  article engine — PageBlock builder + rich_media()
#    13  watchers (deleted, outgoing) + startup
# ══════════════════════════════════════════════════════════════

import asyncio
import contextvars
import os
import time
import json
import random
import glob
import re
import shutil
import string
import unicodedata
import inspect
import urllib.parse
from io import BytesIO
from typing import Dict, Set, Optional, Any

import requests
import qrcode
from gtts import gTTS

from telethon import TelegramClient, events, functions, types, Button
from telethon.errors import (
    FloodWaitError, RPCError, MessageNotModifiedError,
    SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError,
    PasswordHashInvalidError, PhoneNumberInvalidError, PhoneNumberBannedError,
    ApiIdInvalidError,
)

# ── event-loop guard (Python 3.12+ / mobile runtimes) ──
try:
    asyncio.get_running_loop()
except RuntimeError:
    try:
        _loop = asyncio.get_event_loop()
        if _loop.is_closed():
            raise RuntimeError
    except Exception:
        asyncio.set_event_loop(asyncio.new_event_loop())


# ══════════════════════════════════════════════════════════════
#                          ᴄᴏɴғɪɢ
# ══════════════════════════════════════════════════════════════
def _env_int(name, default=0):
    """env se int — galat value pe crash nahi"""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ╔══════════════════════════════════════════════════════════════╗
# ║   ✏️  SIRF YAHAN VALUES PASTE KARO — baaki kuch nahi           ║
# ╚══════════════════════════════════════════════════════════════╝
PASTE_API_ID = 0                 # ← apna API_ID (number)          e.g. 1234567
PASTE_API_HASH = ""              # ← apna API_HASH (32 chars)      e.g. "32bdfcd4..."
PASTE_OWNER_ID = 0               # ← apna telegram user id         e.g. 5076760701
PASTE_SESSION_STRING = ""        # ← StringSession yahan           e.g. "1ApWapzMBuw..."

# env var ho to wo jeetega, warna upar wali value use hogi
API_ID = _env_int("API_ID", 0) or PASTE_API_ID
API_HASH = (os.environ.get("API_HASH") or "").strip() or PASTE_API_HASH.strip()
OWNER_ID = _env_int("OWNER_ID", 0) or PASTE_OWNER_ID
SESSION = (os.environ.get("SESSION") or "").strip() or PASTE_SESSION_STRING.strip()

# file-session ka naam (jab string na ho → phone/otp se login hoga)
SESSION_FILE = (os.environ.get("SESSION_FILE") or "nik").strip()

AI_URL = os.environ.get("AI_URL") or ""      # optional: apna endpoint
AI_MODEL = os.environ.get("AI_MODEL") or "openai-fast"

VERSION = "v2"
OWNER_TAG = "@Nikkkwa"
PREFIX = "."

# bina prefix bhi command chale — "hy" / "Hy" / ".hy" sab same.
# band karna ho to env me NOPREFIX=0
NOPREFIX = (os.environ.get("NOPREFIX") or "1").strip().lower() not in (
    "0", "off", "false", "no")

TMP_TTL = 3           # har working/status message 3 sec me udd jata hai
LOCK_DELAY = 0.3      # locked chat me message delete hone ka delay
STORY_DELAY = 1.6     # animation frame delay
START_TIME = time.time()

BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
TEMP_PATH = os.path.join(BASE_DIR, "temp")
for _p in (DATA_DIR, DOWNLOAD_PATH, TEMP_PATH):
    os.makedirs(_p, exist_ok=True)

# StringSession = ~300-400 chars ka base64 (koi ':' nahi hota).
# Bahut purane "1BVts..." strings bhi isi me aa jaate hain.
_SESS_CLEAN = re.sub(r"\s+", "", SESSION or "")
SESSION_IS_STRING = bool(
    len(_SESS_CLEAN) >= 100
    and re.fullmatch(r"[A-Za-z0-9_\-+/=]+", _SESS_CLEAN) is not None
)

print(f"[SESSION] mode: {'STRING ✅' if SESSION_IS_STRING else 'FILE → phone/OTP login'}"
      + ("" if SESSION_IS_STRING else f"  ({SESSION_FILE}.session)"))

# kis handler ke andar kaun client chal raha hai (main bot ya subbot)
_CURRENT_CLIENT = contextvars.ContextVar("nik_client", default=None)


class _BotProxy:
    """`bot` naam ka proxy — har command apne current client pe jati hai.

    Main account se `.addbot` karke jo naya userbot login hota hai, uske
    andar bhi `bot.get_entity(...)`, `bot.send_file(...)` sab usi (subbot)
    account se chalta hai — bina 5000 lines ko chhedne ke.
    """
    __slots__ = ("_default",)

    def __init__(self, default):
        object.__setattr__(self, "_default", default)

    def _target(self):
        return _CURRENT_CLIENT.get() or object.__getattribute__(self, "_default")

    def __getattr__(self, name):
        return getattr(self._target(), name)

    def __call__(self, *a, **kw):
        return self._target()(*a, **kw)

    def __repr__(self):
        return f"<NikBotProxy {type(self._target()).__name__}>"


# ══════════════════════════════════════════════════════════════
#   💎 ᴛᴇʟᴇɢʀᴀᴍ ᴄᴜꜱᴛᴏᴍ ᴇᴍᴏᴊɪ ʟᴀʏᴇʀ
# ══════════════════════════════════════════════════════════════
# Telegram spec (core.telegram.org/api/custom-emoji):
#   messageEntityCustomEmoji{offset, length, document_id}
#   • offset/length = UTF-16 code units
#   • entity ko EXACTLY ek regular emoji wrap karna hai jo us document ka
#     documentAttributeCustomEmoji.alt ho — warna server entity IGNORE kar deta hai
#   • max ~100 custom emoji per message (appConfig.message_animated_emoji_max)
#
# Isliye text me pack ka hi alt-emoji rakha jaata hai + us par entity lagti hai.
# Ids 5 TXT packs se li gayi hain (248 unique alt emoji / 843 documents).
#   band karna ho →  PREMIUM_EMOJI=0

PREMIUM_EMOJI = (os.environ.get("PREMIUM_EMOJI") or "1").strip().lower() not in (
    "0", "off", "false", "no")

# alt-emoji → custom_emoji document_id
_NIK_EMOJI_IDS = {
    "👩‍❤️‍💋‍👨": 5266961851563942059, "❤️‍🔥": 6237905222472047395, "❤️‍🩹": 5976837031249055394,
    "🙇‍♀️": 5249342431131897248, "🐈‍⬛": 5978886499448392870, "😮‍💨": 6237980015032539412,
    "😵‍💫": 5267061928596902543, "®️": 5978862469106372478, "⌚️": 6237502719611902410,
    "▶️": 5978665033754742175, "☁️": 5247180000997708142, "☄️": 6239910512637779412,
    "☑️": 6237656110073911804, "☕️": 5249268927061598421, "☠️": 5978947110026874546,
    "☯️": 5978603529823063371, "☹️": 5285412167779128384, "☺️": 5195074333935963893,
    "⚪️": 5979003318263877058, "⛓️": 5330436400137398603, "⛩️": 5195288403695934211,
    "✂️": 5976447748298247270, "✈️": 6237744990127135219, "✏️": 5978980894239624403,
    "✝️": 5978807609489100456, "❣️": 6237677060924381798, "❤️": 5192722817866574644,
    "➡️": 5978759780733291780, "⬇️": 6237746815488236230, "⭐️": 5978899255501262127,
    "🌧️": 5465209875430664266, "🌫️": 5249307590357194246, "🕉️": 5247092559758528217,
    "🗡️": 5249368321194760656, "🛏️": 5251575384629091528, "⌨": 5247254742018592036,
    "⏳": 5978841844673416652, "☕": 5249501770123612259, "♾": 6237799884104146552,
    "⚡": 6237962044889373292, "⚪": 5330553171708242447, "✅": 5978820206628178949,
    "✝": 5197174087612391361, "✨": 5976820087603072381, "❌": 5978586079370939741,
    "❓": 5249011237613770228, "❔": 6237522708389697794, "❕": 5247080100058403132,
    "❤": 5195432976590082608, "➕": 6237533282599180408, "➖": 5195024843027814792,
    "⭐": 5192852341195316756, "🆗": 5267375117612128074, "🌈": 5195254482044230757,
    "🌎": 5978824123638353542, "🌒": 5192780297413893424, "🌕": 5979079322005148203,
    "🌙": 5979058122046573726, "🌟": 5978812475687046594, "🌧": 5285032011633825465,
    "🌸": 5978959367863536376, "🌹": 5978873163574938704, "🌼": 5249105344642191094,
    "🌾": 5431493110846748874, "🍑": 5267271175108598968, "🍒": 6237590680542124986,
    "🍓": 5195045763813512197, "🍙": 5249289310976383141, "🍜": 5285387334278227556,
    "🍪": 5247157525433850527, "🍭": 5978808829259811989, "🍰": 6237595456545758528,
    "🍻": 5978723170432061153, "🍼": 5195220929759713427, "🎀": 5976456217973755368,
    "🎁": 5192762451824779951, "🎂": 6237541485986716470, "🎡": 5246926116890907296,
    "🎨": 5978833190314315390, "🎩": 5978934113455837636, "🎰": 5976778787197555156,
    "🎱": 5978606398861217712, "🎲": 5979021490270506379, "🎼": 5247107239956748992,
    "🏃": 6237933908558617421, "🐇": 5248999164460701256, "🐉": 5978823041306594820,
    "🐮": 5978607502667811970, "🐰": 5978802455528345019, "🐱": 5978541381646290066,
    "🐶": 5978922585763614212, "🐸": 5269742108448690467, "🐾": 5978553304475504025,
    "👀": 5978552896453610853, "👁": 5978793354492644700, "👄": 5979010868816383030,
    "👅": 5246826048447881587, "👋": 5976610832501443777, "👍": 5247101712333837522,
    "👎": 5247067146437042188, "👑": 5193037303961920951, "👣": 5247027757291970131,
    "👹": 5249001071426178659, "👻": 5978614567889014234, "👼": 5978950876713192534,
    "👾": 5979011744989711420, "💀": 5976620178350279724, "💊": 5978680791989750916,
    "💋": 5195035460186970394, "💍": 5194991131829509406, "💎": 5978643163781271317,
    "💐": 5247115666682584847, "💓": 5246803005948336193, "💔": 5976378105403542229,
    "💕": 5246712188864862325, "💖": 5195437988816916914, "💗": 5195462319806651480,
    "💘": 5330550577547994411, "💙": 6237826061929814204, "💛": 6238007928024996906,
    "💜": 6237513285231450066, "💞": 5247135895978549151, "💣": 5978622659607400465,
    "💤": 5285131285507905413, "💥": 6237956620345680884, "💧": 5285268840425494803,
    "💩": 5978636626841046194, "💪": 5267444034657362301, "💬": 6237690319488424733,
    "💭": 5249315239693948184, "💯": 6237953794257197225, "💰": 5978857525599014469,
    "💳": 5978964719392787593, "💷": 5249323709369457202, "💸": 6237548993589550020,
    "💻": 5978553755447070046, "💿": 5976687218494803338, "📌": 5978563874390022484,
    "📓": 5976483903332945469, "📝": 6237921062311434460, "📞": 5978850730960752469,
    "📱": 6237508788400692302, "📼": 5247046217061406822, "🔆": 5285084680817778892,
    "🔐": 6237640167155308265, "🔔": 5195375024596360611, "🔞": 5246811183566068237,
    "🔥": 5978916684478549142, "🔨": 5976599274744450627, "🔪": 5979007716310387659,
    "🔫": 5978892679906332620, "🔮": 6237788072944082695, "🔳": 5978908309292322520,
    "🔸": 6237913722212326068, "🔹": 6237877979494489060, "🔼": 5978853136142437656,
    "🕯": 5246844551166991297, "🕷": 5978832361385626915, "🕸": 5978753935282802622,
    "🕺": 5978916164787506097, "🖐": 5462958397739524562, "🖕": 5195455804341262324,
    "🖤": 5976446064671067786, "🖱": 5978658342195694583, "🗡": 5246870050387827337,
    "😁": 5269221545527510874, "😃": 5978809907296603507, "😅": 5242357066256900919,
    "😈": 5978968799611719162, "😉": 5246876106291714615, "😊": 5978672257889733607,
    "😋": 5978688260937878993, "😍": 5249454040152051865, "😎": 6237617197670210486,
    "😏": 5269459220427739286, "😐": 5979017766533860793, "😒": 6240129268207066290,
    "😔": 5979039825485892873, "😘": 5249439463033047967, "😛": 5976367969280724472,
    "😜": 5242488397766877918, "😞": 5247231029504153475, "😠": 5976807889895951962,
    "😨": 5979036363742252603, "😬": 5978863718941854991, "😭": 5195273835166866794,
    "😱": 5249073643488578996, "😳": 5978860991637622378, "😶": 5978552192078975078,
    "😺": 5285006838830502767, "😻": 5978803864277618285, "😽": 5978732967252462299,
    "🙂": 5976302565518741150, "🙃": 5246840496717860298, "🙄": 6237715118629590927,
    "🙈": 5195243100380895030, "🙏": 5249385196121263651, "🚨": 5978813609558413261,
    "🚩": 6237878254372394972, "🚬": 5978949794381434031, "🚻": 5442932541491277792,
    "🤍": 5978771140921789553, "🤎": 5465140576133342848, "🤒": 6237539458762151918,
    "🤔": 5269240370369170843, "🤖": 5979012062817291258, "🤗": 5246895034212584383,
    "🤙": 5976773959654313564, "🤣": 5249443977043676678, "🤨": 5979054656007966182,
    "🤩": 5978937094163140081, "🤪": 5978703538136550464, "🤯": 5978559106976320557,
    "🤲": 5431535261655790724, "🤿": 5978660665773001994, "🥀": 6237490886977001411,
    "🥛": 5249166419077140101, "🥰": 5979054325295484199, "🥱": 5285473856394400413,
    "🥳": 5267271119274022611, "🥶": 5285157501988278564, "🥸": 5251402671109214080,
    "🥹": 5192739387850398376, "🥺": 5976694584363716234, "🦇": 5978528586938715397,
    "🦋": 5978892276179405886, "🦚": 5195257578715651251, "🦴": 5979041144040853544,
    "🦶": 5246769075706699445, "🧁": 5246834389274366597, "🧃": 5976775239554567513,
    "🧸": 5978581333432078444, "🧿": 5462887212951558947, "🩵": 5285466391741240545,
    "🩷": 5195361100312385542, "🩹": 5246863260044531195, "🪄": 5248998889582792282,
    "🪐": 5976744058091998771, "🪱": 5195103556893448354, "🪳": 5976661160928218512,
    "🫀": 6237550509713005906, "🫂": 5248995732781829620, "🫠": 5247023934771072793,
    "🫥": 5978863349574667695, "🫦": 5246916221286259480, "🫧": 5249398308656418081,
    "🫶": 6237839234594511215, "🫷": 5249461642244165680,
}

# ── 8 packs (1369 docs · 324 alts) se aaye naye emoji ─────────
# article / premium design / normal chat — sab isi map se chalte hain
_NIK_EMOJI_IDS.update({
    "☀️": 5400046004550532116,
    "⚡️": 5260345759387127131,
    "⚽️": 5260586616858117316,
    "✌": 5402108203032937818,
    "✔️": 5260384637431087880,
    "❄️": 5258111865292099953,
    "❤‍🔥": 6201510017498095443,
    "⬜": 6199330184156421477,
    "〽️": 6201469829489105722,
    "🃏": 5447657898870086204,
    "🇮🇹": 5258207746142017360,
    "🇯🇵": 6201666955603089738,
    "🌑": 6199511131128601240,
    "🍂": 6199506849046206393,
    "🍞": 5402106927427650530,
    "🍢": 5400354039605000375,
    "🍬": 5402398151980121369,
    "🍹": 6199327770384802451,
    "🍽": 5399959177491674169,
    "🎈": 5402135454600429028,
    "🎢": 5260537040050621197,
    "🎧": 6199728190185805725,
    "🎶": 6199638515563632554,
    "🏛️": 6199390202029414321,
    "🏵": 6199287891613456848,
    "🏹": 5400239883669239075,
    "🐈": 6199580271512131870,
    "🐯": 5402331107540628027,
    "👘": 5400027544781092239,
    "👫": 5258352014093486972,
    "👸": 5400062535879652171,
    "💃": 5400314886683128649,
    "💆‍♀️": 6199553196038297664,
    "💌": 6201706585266330081,
    "💨": 5400332332840286310,
    "📖": 5400085256256648325,
    "🔗": 6201716652669670801,
    "🔯": 6199576397451630483,
    "🕊️": 6201895843000227932,
    "🗓": 5257977213772400201,
    "🗝": 6199608386368051697,
    "😀": 6199248167460936399,
    "😂": 5400162750351570903,
    "😄": 5402407403339674132,
    "😇": 5402545838725560949,
    "😌": 5402607621830112803,
    "😝": 5402103654662567745,
    "😡": 6201608664306948062,
    "😢": 5260373762573897624,
    "😴": 5400099927864932110,
    "😷": 5402194592005123817,
    "🚲": 5402543141486098607,
    "🛴": 5402176639041833647,
    "🛵": 5400297419051138151,
    "🟢": 5258089552936994416,
    "🤑": 6199644970899479965,
    "🤓": 5399936482884481004,
    "🤕": 5400089486799434628,
    "🤠": 5258194028016472323,
    "🤤": 6199426090776139399,
    "🤥": 6199570582065912276,
    "🤧": 5402086195620509507,
    "🤬": 5258416679121095440,
    "🤭": 5399835267685186112,
    "🥇": 5258439725915606836,
    "🥢": 6199256010071218331,
    "🥲": 6199340191430221857,
    "🥴": 5400140940507641551,
    "🦊": 5402613888187398318,
    "🧐": 5400041486244933592,
    "🩶": 5262924805643995469,
    "🪙": 5258474691244361770,
    "🪶": 5258200264308982106,
    "🫣": 6199270088974015791,
    "🫰": 6201459963949227179,
    "🫵": 6199371982778145122,
})

if PREMIUM_EMOJI:
    try:
        from telethon.client.messageparse import MessageParseMethods
        from telethon.client.messages import MessageMethods
        from telethon.client.uploads import UploadMethods

        _NIK_RX = re.compile("|".join(
            re.escape(_k) for _k in sorted(_NIK_EMOJI_IDS, key=len, reverse=True)))
        _NIK_OFF = contextvars.ContextVar("nik_emoji_off", default=False)

        def _nik_u16(s):
            """Telegram entity offset = UTF-16 code units."""
            return len(s.encode("utf-16-le")) // 2

        def _nik_attach(text, entities):
            """har emoji ke upar messageEntityCustomEmoji (document_id ke saath)."""
            if not isinstance(text, str) or not text or _NIK_OFF.get():
                return entities
            ents = list(entities or [])
            budget = 100 - len(ents)
            if budget <= 0:
                return ents
            pos = prev = hits = 0
            add = []
            for _m in _NIK_RX.finditer(text):
                if budget <= 0:
                    break
                pos += _nik_u16(text[prev:_m.start()])
                add.append(types.MessageEntityCustomEmoji(
                    pos, _nik_u16(_m.group()), _NIK_EMOJI_IDS[_m.group()]))
                pos += _nik_u16(_m.group())
                prev = _m.end()
                budget -= 1
                hits += 1
            if not hits:
                return entities
            ents.extend(add)
            ents.sort(key=lambda _e: (_e.offset, -_e.length))
            return ents

        _NIK_ORIG_PARSE = MessageParseMethods._parse_message_text

        async def _nik_parse_message_text(self, message, parse_mode):
            _text, _ents = await _NIK_ORIG_PARSE(self, message, parse_mode)
            return _text, _nik_attach(_text, _ents)

        MessageParseMethods._parse_message_text = _nik_parse_message_text

        def _nik_guard(_fn):
            """custom emoji reject ho to wahi message plain chala jaye (no crash)."""
            async def _wrapper(self, *a, **kw):
                try:
                    return await _fn(self, *a, **kw)
                except Exception as _ex:
                    if "emoji" in str(_ex).lower() and not _NIK_OFF.get():
                        _tok = _NIK_OFF.set(True)
                        try:
                            return await _fn(self, *a, **kw)
                        finally:
                            _NIK_OFF.reset(_tok)
                    raise
            return _wrapper

        for _cls, _names in ((MessageMethods, ("send_message", "edit_message")),
                             (UploadMethods, ("send_file",))):
            for _n in _names:
                if hasattr(_cls, _n):
                    setattr(_cls, _n, _nik_guard(getattr(_cls, _n)))
    except Exception as _e:
        print(f"[EMOJI LAYER] off: {_e}")


def _config_missing():
    """kaunsi values missing hain"""
    miss = []
    if not API_ID:
        miss.append("PASTE_API_ID")
    if not API_HASH or len(API_HASH) < 20:
        miss.append("PASTE_API_HASH")
    if not OWNER_ID:
        miss.append("PASTE_OWNER_ID")
    return miss


def _config_help():
    miss = _config_missing()
    print("\n" + "═" * 60)
    print("  ⚠️  SETUP ADHURA HAI → " + ", ".join(miss))
    print("═" * 60)
    print("  Nik_userbot.py kholo, sabse upar ye block milega:")
    print('      PASTE_API_ID         = 0')
    print('      PASTE_API_HASH       = ""')
    print('      PASTE_OWNER_ID       = 0')
    print('      PASTE_SESSION_STRING = ""')
    print()
    print("  wahan apni values daalo:")
    print("      PASTE_API_ID         = 1234567")
    print('      PASTE_API_HASH       = "32bdfcd4..."')
    print("      PASTE_OWNER_ID       = 5076760701")
    print('      PASTE_SESSION_STRING = "1ApWapzMBuw..."   # khaali bhi chhod sakte ho')
    print()
    print("  • Session string daalo  → seedha chal jayega")
    print("  • Khaali chhodo         → phone number + OTP maangega,")
    print("                            login ke baad %s.session ban jayegi" % SESSION_FILE)
    print("═" * 60 + "\n")


def _config_ok():
    if not _config_missing():
        return True
    _config_help()
    return False


if _config_missing():
    _config_help()
    raise SystemExit(1)

try:
    if SESSION_IS_STRING:
        from telethon.sessions import StringSession
        _REAL_BOT = TelegramClient(StringSession(_SESS_CLEAN), API_ID, API_HASH,
                                   auto_reconnect=True, connection_retries=10,
                                   retry_delay=3, flood_sleep_threshold=60)
    else:
        _REAL_BOT = TelegramClient(SESSION_FILE, API_ID, API_HASH,
                                   auto_reconnect=True, connection_retries=10,
                                   retry_delay=3, flood_sleep_threshold=60)
except Exception as _e:
    print(f"[CLIENT ERROR] {_e}")
    raise

bot = _BotProxy(_REAL_BOT)


# ══════════════════════════════════════════════════════════════
#                       sᴛʏʟᴇ ᴋɪᴛ
# ══════════════════════════════════════════════════════════════
# Unicode font engine — poore bot ka text isi se guzar-ta hai.

_SANS_B = (0x1D5D4, 0x1D5EE, 0x1D7EC)   # 𝗔𝗮𝟬
_SERIF_B = (0x1D400, 0x1D41A, 0x1D7CE)   # 𝐀𝐚𝟎
_SERIF_I = (0x1D434, 0x1D44E, None)      # 𝐴𝑎
_SERIF_BI = (0x1D468, 0x1D482, None)     # 𝑨𝒂
_MONO = (0x1D670, 0x1D68A, 0x1D7F6)      # 𝙰𝚊𝟶
_SCRIPT = (0x1D49C, 0x1D4B6, None)       # 𝒜𝒶
_SCRIPT_B = (0x1D4D0, 0x1D4EA, None)     # 𝓐𝓪
_DBL = (0x1D538, 0x1D552, 0x1D7D8)       # 𝔸𝕒
_FRK = (0x1D504, 0x1D51E, None)          # 𝔄𝔞

_EXCEPT = {
    _SCRIPT: {"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ",
              "L": "ℒ", "M": "ℳ", "R": "ℛ", "e": "ℯ", "g": "ℊ", "o": "ℴ"},
    _SCRIPT_B: {"B": "𝓑", "E": "𝓔", "F": "𝓕", "H": "𝓗", "I": "𝓘",
                "L": "𝓛", "M": "𝓜", "R": "𝓡"},
    _DBL: {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"},
    _FRK: {"C": "ℭ", "H": "ℌ", "I": "ℑ", "R": "ℜ", "Z": "ℨ"},
    _SERIF_I: {"h": "ℎ"},
}

_SC_TAB = str.maketrans("abcdefghijklmnopqrstuvwxyz",
                        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ")


def _xf(t, spec):
    up, lo, dg = spec
    ex = _EXCEPT.get(spec, {})
    out = []
    for ch in str(t):
        if ch in ex:
            out.append(ex[ch])
            continue
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(up + o - 65))
        elif 97 <= o <= 122:
            out.append(chr(lo + o - 97))
        elif 48 <= o <= 57 and dg:
            out.append(chr(dg + o - 48))
        else:
            out.append(ch)
    return "".join(out)


# body text — purana small-caps (ᴀʙᴄ). TEXT_BOLD=1 se bold sans chahiye to on
TEXT_BOLD = (os.environ.get("TEXT_BOLD") or "0").strip().lower() in (
    "1", "on", "true", "yes")


def sc(t):
    """body text — default purana small caps (ᴀʙᴄ)."""
    t = str(t)
    return _xf(t, _SANS_B) if TEXT_BOLD else t.translate(_SC_TAB)
def sb(t):    return _xf(t, _SANS_B)                # 𝗔𝗕𝗖
def bs(t):    return _xf(t, _SERIF_B)               # 𝐀𝐁𝐂
def its(t):   return _xf(t, _SERIF_I)               # 𝐴𝐵𝐶
def sbi(t):   return _xf(t, _SERIF_BI)              # 𝑨𝑩𝑪
def mono(t):  return _xf(t, _MONO)                  # 𝙰𝙱𝙲
def scr(t):   return _xf(t, _SCRIPT)                # 𝒜𝓁𝓁
def scrb(t):  return _xf(t, _SCRIPT_B)              # 𝓐𝓑𝓒
def dbl(t):   return _xf(t, _DBL)                   # 𝔸𝔹ℂ

E = {
    "link": "🏷️",
    "star": "✦", "diamond": "❖", "dot": "⟡", "bolt": "⌁", "crown": "♛",
    "shield": "🛡️", "eye": "🧿", "chain": "⛓️", "sat": "📡", "globe": "🌐",
    "sword": "⚔️", "comet": "☄️", "gear": "⚙️", "wand": "🪄", "dice": "✹",
    "gene": "🧬", "node": "⟐", "tool": "⌬", "key": "🗝️", "film": "✺",
    "moon": "☾", "spark": "✧", "arrow": "‣", "lock": "🔒", "fire": "🔥",
    "warn": "⚠️", "ok": "✅", "no": "❌", "wait": "⏳", "skull": "☠️",
    "ghost": "👻", "note": "🗒️", "save": "💾", "trash": "🗑️", "bot": "🤖",
    "rocket": "🚀", "clock": "🕰️", "heart": "🖤", "crown2": "🔱", "gem": "💠",
    "eye2": "🪬", "ring": "💍", "flower": "❀", "wave": "🌊", "leaf": "❦",
    "music": "🎵", "bell": "🔔", "mic": "🎙️", "head": "🎧", "play": "▶️",
}

# ── E roles → pack ke exact alt emoji (real custom emoji) ────────
# sirf wahi roles badalte hain jinka document id packs me maujood hai

# ── har section ka apna emoji (sab alag, sab packs se) ──────────
# icon  = header + alternate rows
# alt   = doosre rows ka halka marker (emoji budget control)
CAT_STYLE = {
    "core":            {"icon": "⚡", "alt": "⭐"},
    "messaging":       {"icon": "💬", "alt": "💭"},
    "auto":            {"icon": "♾", "alt": "➡️"},
    "blacklist":       {"icon": "🚨", "alt": "⛓️"},
    "broadcast":       {"icon": "🔔", "alt": "📞"},
    "group mod":       {"icon": "🗡️", "alt": "🔨"},
    "global":          {"icon": "🌎", "alt": "🌕"},
    "protection":      {"icon": "🧿", "alt": "🕷"},
    "media":           {"icon": "🎼", "alt": "🎨"},
    "fun":             {"icon": "🥳", "alt": "🎲"},
    "ai & sudo":       {"icon": "🤖", "alt": "🔮"},
    "bot manager":     {"icon": "🧸", "alt": "🎀"},
    "raid":            {"icon": "🔥", "alt": "💥"},
    "spam":            {"icon": "💣", "alt": "💤"},
    "gc tools":        {"icon": "🎲", "alt": "🎩"},
    "tools":           {"icon": "🔨", "alt": "🔪"},
    "notes":           {"icon": "📝", "alt": "📓"},
    "stories":         {"icon": "🌙", "alt": "🎡"},
    "baka automation": {"icon": "🎩", "alt": "🎰"},
}
_STYLE_DEFAULT = {"icon": "✨", "alt": "⭐"}
# page ke hisaab se masthead ka jodi
HEROES = [("👑", "🔥"), ("⚡", "💎"), ("🌙", "🌟")]

# custom emoji asli emoji se thode bade + animated hote hain,
# isliye har emoji ke aage-peeche patla space (gap) rakha jaata hai
SP = "\u2009"

_NIK_E_CUSTOM = {
    "star": "✨",
    "diamond": "💎",
    "dot": "🔸",
    "bolt": "⚡",
    "crown": "👑",
    "shield": "🧿",
    "chain": "⛓️",
    "sat": "🔆",
    "globe": "🌎",
    "sword": "🗡️",
    "comet": "☄️",
    "gear": "🔨",
    "dice": "🎲",
    "gene": "🔮",
    "node": "➕",
    "tool": "🖱",
    "key": "🔐",
    "film": "💿",
    "moon": "🌙",
    "spark": "🌟",
    "lock": "🔐",
    "warn": "🚨",
    "skull": "💀",
    "note": "📝",
    "save": "📌",
    "trash": "🪳",
    "rocket": "✈️",
    "clock": "⏳",
    "crown2": "👑",
    "gem": "💎",
    "eye2": "🧿",
    "flower": "🌸",
    "leaf": "🌾",
    "link": "🔹", "music": "🎼", "bell": "🔔",
}

if PREMIUM_EMOJI:
    E.update({_r: _e for _r, _e in _NIK_E_CUSTOM.items() if _e in _NIK_EMOJI_IDS})




# ── display width (emoji = 2 cell, invisible = 0) ─────────────
# Purani galti yahi thi: len() emoji ko 1 ginta hai, phone 2 dikhata hai.
# Isi liye `│` right border har line pe alag jagah girta tha.
def dw(s):
    total = 0
    for ch in str(s):
        o = ord(ch)
        if o == 0xFE0F:                 # emoji presentation → extra cell
            total += 1
            continue
        if o in (0xFE0E, 0x200D, 0x20E3) or o < 32:
            continue
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def _pad(s, width):
    s = str(s)
    return s + " " * max(0, width - dw(s))


def _fit(s, width):
    s = str(s)
    if dw(s) <= width:
        return s
    out, used = [], 0
    for ch in s:
        c = dw(ch)
        if used + c > max(1, width - 1):
            break
        out.append(ch)
        used += c
    return "".join(out).rstrip() + "…"


def _center(s, width):
    s = str(s)
    gap = max(0, width - dw(s))
    left = gap // 2
    return " " * left + s + " " * (gap - left)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def err_txt(e, n=70):
    """yt-dlp / telethon ka gandha error → saaf one-line text"""
    raw = _ANSI_RE.sub("", str(e) or type(e).__name__)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = raw.replace("ERROR: ", "").replace("WARNING: ", "")
    low = raw.lower()
    if "not a valid url" in low:
        raw = "search fail — dobara try karo"
    elif "sign in to confirm" in low or "confirm you're not a bot" in low:
        raw = "youtube ne block kiya — thodi der baad try karo"
    elif "ffmpeg" in low and ("not" in low or "missing" in low):
        raw = "ffmpeg missing hai (voice note ke liye chahiye)"
    elif "unable to download" in low or "failed to" in low:
        raw = "download fail — link ya words check karo"
    return _fit(raw, n)


# UI_STYLE=rail → left-rail card (right border hi nahi = kabhi nahi tootega)
# UI_STYLE=box  → purana box, par ab display-width se perfect aligned
UI_STYLE = (os.environ.get("UI_STYLE") or "rail").strip().lower()
if UI_STYLE not in ("rail", "box"):
    UI_STYLE = "rail"

RAIL = "┃"
RAIL_CLOSE = "┗" + "━" * 18


def top(w=30, hero=None):
    """panel ka masthead — page ke hisaab se alag jodi"""
    a, b = hero or HEROES[0]
    if UI_STYLE == "box":
        return (f"╭{'─' * w}╮\n"
                f"│{_center('  ' + scrb('Nik Userbot'), w)}│\n"
                f"╰{'─' * w}╯")
    return f"┏━ {a}{SP} {scrb('Nik Userbot')} {SP}{b}"


def sub(line, w=30):
    """ek row — rail me sirf left border, right side kuch nahi"""
    body = str(line).strip()
    if UI_STYLE == "box":
        return "│" + _pad("  " + body, w - 1) + "│"
    return RAIL if not body else f"{RAIL} {body}"


def box(lines, w=30):
    if UI_STYLE == "box":
        out = [f"╭{'─' * w}╮"]
        out += ["│" + _pad("  " + str(ln), w - 1) + "│" for ln in lines]
        out.append(f"╰{'─' * w}╯")
        return "\n".join(out)
    out = [f"┏━ {HEROES[0][0]}{SP} {scrb('Nik Userbot')} {SP}{HEROES[0][1]}"]
    out += [sub(ln) for ln in lines]
    out.append(RAIL_CLOSE)
    return "\n".join(out)


def hdr(title, w=30, count=None):
    """section header — icon + naam + count"""
    title = str(title)
    if UI_STYLE == "box":
        body = f"〔 {sb(title.upper())} 〕"
        pad = max(1, w - dw(body))
        return f"┌─{body}" + "─" * pad
    line = f"{RAIL} {SP}{title}{SP}"
    if count is not None:
        line += f"▰ {mono(str(count))}"
    return line


def end(w=30):
    """section ke baad ki line"""
    return ("└" + "─" * w) if UI_STYLE == "box" else RAIL


def close(w=30):
    """panel ka bottom"""
    return ("╰" + "─" * w + "╯") if UI_STYLE == "box" else RAIL_CLOSE


def row(cmd, desc, bullet=None, cw=12):
    """command + guide ek hi line me (emoji ke around gap)"""
    b = bullet if bullet is not None else E["star"]
    head = f"{b}{SP}" if b else " "
    if UI_STYLE == "box":
        return f"│ {head} {_pad(mono(cmd), cw)}‣ {sc(desc)}"
    return f"{RAIL}  {head} {_pad(mono(cmd), cw)}‣ {sc(desc)}"


def note(text, bullet=None):
    b = bullet or E["dot"]
    prefix = "│" if UI_STYLE == "box" else RAIL
    return f"{prefix} {b}{SP} {sc(text)}"


def kv(label, value, bullet=None, lw=10):
    b = bullet or E["diamond"]
    prefix = "│" if UI_STYLE == "box" else RAIL
    return f"{prefix} {b}{SP} {_pad(sc(label), lw)} ‣ {mono(str(value))}"


def cap(text):
    return f"{E['spark']}{SP} {its(text)}"


BRAND = f"{E['spark']}{SP} {scr('Nik Userbot')} {SP}{E['spark']}"
FOOT = f"{E['dot']}{SP} {sc('powered by')} {OWNER_TAG}"


def block(title, rows, w=30):
    return "\n".join([hdr(title, w)] + list(rows) + [end(w)])


def panel(rows, title=None):
    """ready-made card: masthead + body + footer + bottom rail.

    Kabhi toot nahi sakta — right side pe border hi nahi hota.
    """
    body = [top(), sub("")]
    if title:
        body += [sub(title), sub("")]
    body += [sub(r) for r in rows]
    body += [sub(""), sub(FOOT), close()]
    return "\n".join(body)


PANEL_MAX = 42          # box style ke liye max inner width


def align_panel(text, w=None):
    """Box borders ko width-aware tarike se barabar karo.

    rail style me right border hota hi nahi, is liye wahan text jaisa hai
    waisa hi chala jata hai (sirf ANSI codes saaf hote hain).
    """
    if not text:
        return text
    text = _ANSI_RE.sub("", str(text))
    if UI_STYLE != "box":
        return text
    lines = text.split("\n")
    widths = [dw(l) - 2 for l in lines if l[:1] == "│" and l[-1:] == "│"]
    if not widths:
        return text
    width = min(max(widths), PANEL_MAX)
    out = []
    for l in lines:
        if l[:1] == "│" and l[-1:] == "│":
            body = l[1:-1]
            if dw(body) > width:
                body = _fit(body, width)
            out.append("│" + _pad(body, width) + "│")
        elif l[:1] in ("╭", "╰") and l[-1:] in ("╮", "╯"):
            out.append(l[0] + "─" * width + l[-1])
        else:
            out.append(l)
    return "\n".join(out)



# ══════════════════════════════════════════════════════════════
#                          sᴛᴏʀᴀɢᴇ
# ══════════════════════════════════════════════════════════════
F_ADMINS = "admins.json"
F_NOTES = "notes.json"
F_BANNER = "banner.json"
F_FILTERS = "filters.json"
F_BLACKLIST = "blacklist.json"
F_BCDB = "bcdb.json"
F_GBAN = "gban.json"
F_GMUTE = "gmute.json"
F_LOCKS = "locks.json"
F_AUTOREAD = "autoread.json"
F_AREPLY = "areply.json"
F_SAVED_CH = "saved_channel.json"
F_SAVED_MSGS = "saved_msgs.json"
F_AUTOBR = "autobc.json"
F_AUTOFW = "autofw.json"
F_ANTIDEL = "antidel.json"
F_SPAMWATCH = "spamwatch.json"
F_RLOCK = "rlock.json"
F_BOTS = "bots.json"
F_GAMEBOT = "gamebot.json"
F_LOCKMSG = "lockmsg.json"
F_GLOCK = "glockmsg.json"
F_PREFIX = "prefix.json"
F_REACT = "react.json"


def load_json(name, default):
    path = os.path.join(DATA_DIR, name)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[LOAD {name}] {err_txt(e, 60)}")
    return default


def save_json(name, data):
    path = os.path.join(DATA_DIR, name)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SAVE {name}] {err_txt(e, 60)}")
        return False


# ══════════════════════════════════════════════════════════════
#                       ʀᴜɴᴛɪᴍᴇ sᴛᴀᴛᴇ
# ══════════════════════════════════════════════════════════════
ADMINS: Set[int] = set(int(x) for x in load_json(F_ADMINS, []))
NOTES: Dict[int, str] = {int(k): v for k, v in load_json(F_NOTES, {}).items()}

FILTERS: Dict[str, Dict[str, Any]] = load_json(F_FILTERS, {})
BLACKLIST: Set[int] = set(int(x) for x in load_json(F_BLACKLIST, []))
BCDB: Set[int] = set(int(x) for x in load_json(F_BCDB, []))
GBAN: Set[int] = set(int(x) for x in load_json(F_GBAN, []))
GMUTE: Set[int] = set(int(x) for x in load_json(F_GMUTE, []))
LOCKS: Dict[str, list] = load_json(F_LOCKS, {})
AUTOREAD: Set[str] = set(load_json(F_AUTOREAD, []))

SAVED_CHANNEL = load_json(F_SAVED_CH, None)
SAVED_MSGS: list = load_json(F_SAVED_MSGS, [])

AUTOBR: Dict[str, Any] = load_json(F_AUTOBR, {
    "on": False, "chat_id": None, "msg_id": None, "text": "", "delay": 120})
AUTOFW: Dict[str, Any] = load_json(F_AUTOFW, {
    "on": False, "chat_id": None, "msg_id": None, "delay": 120})
AUTOBR_TASK: Optional[asyncio.Task] = None
AUTOFW_TASK: Optional[asyncio.Task] = None

AREPLY: Optional[str] = load_json(F_AREPLY, None)
MENU_BANNER = load_json(F_BANNER, None)

# protection
ANTIDEL: Set[int] = set(int(x) for x in load_json(F_ANTIDEL, []))
SPAMWATCH: Dict[str, Dict[str, int]] = load_json(F_SPAMWATCH, {})
SPAM_BUCKET: Dict[str, list] = {}
RLOCK: Dict[str, Dict[str, str]] = load_json(F_RLOCK, {})
GPFP_TASK: Optional[asyncio.Task] = None
GPFP_STATE: Dict[str, Any] = {"on": False, "delay": 10, "photos": []}

# bot manager
SAVED_BOTS: list = load_json(F_BOTS, [])
GAME_BOT = load_json(F_GAMEBOT, None)
# lock message control
#   GLOCK   — master switch (sab chats)          → .glockmsg on/off
#   LOCKMSG — per chat on/off (default on)       → .lockmsg on/off
#   purana format ({"on": bool}) bhi chalega
LOCKMSG: Dict[str, Any] = {}
GLOCK: Dict[str, Any] = {"on": True}
try:
    _raw_lm = load_json(F_LOCKMSG, {})
    if isinstance(_raw_lm, dict):
        if isinstance(_raw_lm.get("on"), bool) and len(_raw_lm) == 1:
            GLOCK["on"] = bool(_raw_lm["on"])          # legacy global value
        else:
            LOCKMSG = {str(k): bool(v) for k, v in _raw_lm.items()}
except Exception:
    pass
try:
    _raw_gl = load_json(F_GLOCK, {})
    if isinstance(_raw_gl, dict) and isinstance(_raw_gl.get("on"), bool):
        GLOCK["on"] = bool(_raw_gl["on"])
except Exception:
    pass


def lockmsg_on(chat) -> bool:
    """lock message bhejna hai ya chup-chaap ignore karna hai."""
    if not GLOCK.get("on", True):
        return False
    try:
        return bool(LOCKMSG.get(str(int(chat)), True))
    except Exception:
        return True


PREFIX_STATE: Dict[str, Any] = {"optional": bool(NOPREFIX)}
try:
    _raw_pf = load_json(F_PREFIX, {})
    if isinstance(_raw_pf, dict) and isinstance(_raw_pf.get("optional"), bool):
        PREFIX_STATE["optional"] = bool(_raw_pf["optional"])
except Exception:
    pass

# sub-userbots (multi session)
SUBBOTS: Dict[str, Any] = {}
PENDING: Dict[str, Any] = {}

# games
TTT: Dict[int, Dict[str, Any]] = {}

# raids
reply_users: Set[int] = set()
rr_users: Set[int] = set()
flag_users: Set[int] = set()
hrr_users: Set[int] = set()
replygod_users: Set[int] = set()
replyking_users: Dict[int, Dict[str, Any]] = {}
ECHO_USERS: Set[int] = set()
USER_REPLY: Dict[int, str] = {}     # .arreply — kisi ek user ko fixed reply

MUTED: Set[int] = set()
GLOBAL_MUTED: Set[int] = set()

spray_tasks: Dict[int, asyncio.Task] = {}

AFK = {"active": False, "reason": None, "since": None}
AFK_LAST: Dict[int, float] = {}
GHOST = {"on": False, "delay": 30}
AUTO_REACT_EMOJI: Optional[str] = None
TAGALL_ACTIVE = False
COMMAND_COOLDOWN: Dict[int, float] = {}

FASTGC_STATE: Dict[str, Any] = {"active": False, "template": None,
                                "task": None, "chat_id": None}
GC_FAST_EMOJIS = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎",
                  "🩷", "🩵", "🩶", "💖", "💘", "💝", "💗", "💓", "💞",
                  "💕", "💟", "❣️", "❤️‍🔥", "❤️‍🩹"]

CLONE_ACTIVE = False
LAST_CLONE_ID: Optional[int] = None
CLONE_DATA: Dict[str, Any] = {}

FACTS = [
    "Honey never spoils — 3000 saal purani honey bhi khane layak mili hai.",
    "Octopus ke paas 3 dil hote hain.",
    "Banana botanically ek berry hai, strawberry nahi.",
    "Tumhare bones steel se zyada strong hote hain (weight ke hisaab se).",
    "Ek din Mars pe sunrise blue hota hai.",
    "Sharks dinosaurs se bhi purane hain.",
    "Human brain lagbhag 75% paani hai.",
    "Light ko Sun se Earth tak aane me 8 min 20 sec lagte hain.",
    "Venus ka ek din uske ek saal se zyada lamba hai.",
    "Butterfly apne pairon se taste karti hai.",
    "Cows ke paas best friends hote hain.",
    "Ek cloud ka weight lagbhag 10 lakh kg ho sakta hai.",
]


# ══════════════════════════════════════════════════════════════
#                           ʜᴇʟᴘᴇʀs
# ══════════════════════════════════════════════════════════════



def is_admin(uid):
    return bool(uid) and (uid == OWNER_ID or uid in ADMINS)


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


# ══════════════════════════════════════════════════════════════
#     ⚡  ʀɪᴄʜ ᴜɪ ᴇɴɢɪɴᴇ  —  poora bot card rich text me
# ══════════════════════════════════════════════════════════════
# Ye eor()/aedit() ke andar baithta hai. Matlab har command ka card —
# menu, category page, list, status — sab rich message (headings + tables)
# + premium emoji + coloured buttons me render hota hai.
#   RICH_UI=1  → force on      RICH_UI=0 → off
#   auto (default) → account premium hai to on, warna purana plain UI
_RICH_UI = (os.environ.get("RICH_UI") or "auto").strip().lower()
_UI_STATE: Dict[str, Any] = {"on": None}


async def _ui_rich_ok():
    """ek hi baar premium check — baad me cache."""
    if _RICH_UI in ("0", "off", "false", "no"):
        return False
    if not RICH_READY:
        return False
    if _UI_STATE["on"] is None:
        try:
            me = await bot.get_me()
            _UI_STATE["on"] = bool(getattr(me, "premium", False)
                                   or getattr(me, "bot", False))
        except Exception:
            _UI_STATE["on"] = False
        print("[RICH UI] %s — %s" % (
            "ON" if _UI_STATE["on"] else "OFF (plain UI)",
            "premium account" if _UI_STATE["on"] else "RICH_UI=1 se force kar sakte ho"))
    return bool(_UI_STATE["on"])


# ── 1. FONT: rich cards me ek hi font (fake fonts hatao) ──────────────
_FAKE_SPECS = (_SANS_B, _SERIF_B, _SERIF_I, _SERIF_BI,
               _MONO, _SCRIPT, _SCRIPT_B, _DBL, _FRK)


def _build_untransliterator():
    r = {}
    for spec in _FAKE_SPECS:
        try:
            up, lo, dg = spec
        except Exception:
            continue
        for i in range(26):
            try:
                r.setdefault(chr(up + i), chr(65 + i))     # A-Z
            except Exception:
                pass
            try:
                r.setdefault(chr(lo + i), chr(97 + i))     # a-z
            except Exception:
                pass
        if dg:
            for i in range(10):
                try:
                    r.setdefault(chr(dg + i), str(i))
                except Exception:
                    pass
    for src, dst in zip("ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
                        "abcdefghijklmnopqrstuvwxyz"):
        r.setdefault(src, dst)
    r.setdefault("ᴡ", "w")
    r.setdefault("ⅹ", "x")
    return r


_UNTRANSLIT = _build_untransliterator()


def _plainify(t):
    """𝓝𝓲𝓴 / 𝗡𝗶𝗸 / 𝙉𝙞𝙠 / ɴɪᴋ → Nik · rich mode me ek hi font."""
    s = str(t)
    if not s:
        return s
    out = []
    for ch in s:
        o = ord(ch)
        if 0x1D400 <= o <= 0x1D7FF:              # math alphanumeric blocks
            n = unicodedata.normalize("NFKC", ch)
            out.append(n if len(n) == 1 and n.isascii() else ch)
        elif ch in _UNTRANSLIT:
            out.append(_UNTRANSLIT[ch])
        else:
            out.append(ch)
    return "".join(out)


# ── 2. RICH BLOCK BUILDER — ek hi jagah, saaf rules ───────────────────
_UI_SEPS = ("‣", "▶", "›", "→", "➤", "»")
_UI_FRAME = set("┏━─┓┗┛╭╮╰╯│┃┌┐└┘├┤┬┴┼╎║|—-_ ")


def _ui_split(body):
    """line → (left, right) agar separator mile, warna None."""
    for sep in _UI_SEPS:
        if sep in body:
            a, b = body.split(sep, 1)
            if a.strip():
                return a.strip(), b.strip()
    return None


def _ui_caps(body):
    core = "".join(c for c in body if c.isalpha())
    return bool(core) and len(core) <= 28 and core == core.upper() \
        and body.count(" ") <= 5


def _ui_note_line(text, docs):
    """ek note/instruction line — blockquote ke andar (⇒ style, img6 jaisa)."""
    return text


def _ui_blocks(text, docs):
    """rail panel → PageBlock list  (img1 + img6 format)

      ┏ / ╭                  → Heading1
      ┗ / ─────              → Divider
      🎼 ▰ x ▰ n             → Heading2
      ".cmd …" akela         → Preformatted (code block)
      ‣ ▶ › →  wali line     → TableRow (2 cell)
      baaki text             → Blockquote — "⇒" style panel
                               (jo table me nahi aata wahi yahan aata hai)
    """
    blocks, rows, notes = [], [], []

    def flush_notes():
        if not notes:
            return
        lines = list(notes)
        notes.clear()
        joined = types.TextConcat(texts=[])
        for i, ln in enumerate(lines):
            if i:
                joined.texts.append(types.TextPlain("\n"))
            joined.texts.append(ln)
        blocks.append(types.PageBlockBlockquote(
            text=joined, caption=types.TextEmpty()))

    def flush():
        if not rows:
            return
        got = list(rows)
        rows.clear()
        if len(got) < 2:
            # 1 row = khali dabba → blockquote line
            only = got[0]
            notes.append(types.TextConcat(texts=[
                types.TextPlain("⇒ "), only.cells[0].text,
                types.TextPlain("  ·  "), only.cells[1].text]))
            return
        blocks.append(types.PageBlockTable(
            title=types.TextEmpty(), rows=got, bordered=True, striped=True))

    def flush_all():
        flush()
        flush_notes()

    lines = str(text).split("\n")
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s or set(s) <= _UI_FRAME:
            flush_all()
            if s and s[0] in "┗╰":
                blocks.append(types.PageBlockDivider())
            elif s and len(s) > 3 and set(s) <= set("─—_"):
                blocks.append(types.PageBlockDivider())
            continue

        if s[0] in "┏╭":
            flush_all()
            t = s.lstrip("┏╭━─ ").strip()
            if t:
                blocks.append(types.PageBlockHeading1(text=_rt(t, docs)))
            continue

        if s[0] in "┗╰":
            flush_all()
            blocks.append(types.PageBlockDivider())
            continue

        body = s.strip("┃│║╎|").strip()
        if body.endswith("│") or body.endswith("┃"):
            body = body[:-1].strip()
        if not body:
            flush_all()
            continue
        plain = _plainify(body)          # sirf pehchaan ke liye

        if "▰" in body:
            flush_all()
            clean = " ".join(body.replace("▰", " ").split())
            if clean:
                blocks.append(types.PageBlockHeading2(text=_rt(clean, docs)))
            continue

        if body.startswith("〔"):
            flush_all()
            clean = " ".join(body.replace("〔", " ").replace("〕", " ")
                             .replace("─", " ").split())
            if clean:
                blocks.append(types.PageBlockHeading2(text=_rt(clean, docs)))
            continue

        pair = _ui_split(body)
        if pair:
            left, right = pair
            if left.strip():
                rows.append(types.PageTableRow(cells=[
                    _ui_cell(left, docs), _ui_cell(right or " ", docs)]))
                continue

        flush()

        # command example akela → code block (monospace)
        if _ui_codeish(plain):
            flush_notes()
            blocks.append(types.PageBlockPreformatted(
                text=_rt(body, docs), language=""))
            continue

        # chhota label jiske niche example aata hai → heading
        nxt = ""
        for _j in range(idx + 1, min(idx + 3, len(lines))):
            _t = lines[_j].strip().strip("┃│║╎|").strip()
            if _t:
                nxt = _plainify(_t)
                break
        if _ui_caps(plain) or (len(plain) <= 30 and _ui_codeish(nxt)):
            flush_notes()
            blocks.append(types.PageBlockHeading3(text=_rt(body, docs)))
            continue

        # baaki sab → blockquote (⇒ panel)
        notes.append(types.TextConcat(texts=[
            types.TextPlain("⇒ "), _rt(body, docs)]))

    flush_all()
    if not blocks:
        return []
    if type(blocks[0]).__name__ not in ("PageBlockTitle", "PageBlockHeading1"):
        blocks.insert(0, types.PageBlockHeading1(
            text=_rt("%s NIK USERBOT %s" % (E["bolt"], E["spark"]), docs)))
    return blocks[:ART_BLOCKS]


def _ui_codeish(t):
    """line code block layak hai? ('.cmd arg' jaisa command example)."""
    t = (t or "").strip()
    if not t or len(t) > 44:
        return False
    if not t.startswith(PREFIX):
        return False
    if any(sep in t for sep in _UI_SEPS):
        return False
    parts = t[len(PREFIX):].split()
    if not parts or not parts[0]:
        return False
    head = parts[0].lower()
    if head in commands or head.rstrip("0123456789") in commands:
        return True
    # placeholder wala example  .c <pass>  /  .r <emoji|id>
    return any(ch in parts[0] for ch in "<>[]|")


def _ui_cell(text, docs):
    return types.PageTableCell(text=_rt(text or " ", docs))


def _ui_buttons(text, docs):
    """card ke niche premium coloured buttons."""
    owner_url = "https://t.me/%s" % OWNER_TAG.lstrip("@")

    # custom emoji: left 5452012007865738264 · right 5452073790970292239
    try:
        docs.add(5452012007865738264)
        docs.add(5452073790970292239)
    except Exception:
        pass
    owner_btn = types.PageButton(
        text=types.TextConcat(texts=[
            types.TextCustomEmoji(document_id=5452012007865738264, alt="👑"),
            types.TextPlain("\u2009 OWNER \u2009"),
            types.TextCustomEmoji(document_id=5452073790970292239, alt="💎"),
        ]),
        type=types.InlineButtonTypeUrl(url=owner_url),
        style=_art_style("red"))
    return types.PageBlockButtonRow(buttons=[owner_btn])


def _sent_msg_id(sent):
    """SendMessageRequest ka result nikaalo → message id (Updates/Short sab)."""
    if sent is None:
        return 0
    for attr in ("id",):
        try:
            v = int(getattr(sent, attr, 0) or 0)
            if v:
                return v
        except Exception:
            pass
    for upd in (getattr(sent, "updates", None) or []):
        n = type(upd).__name__
        if n == "UpdateMessageID":
            try:
                return int(getattr(upd, "id", 0) or 0)
            except Exception:
                pass
        msg = getattr(upd, "message", None)
        if msg is not None and getattr(msg, "id", None):
            try:
                return int(msg.id)
            except Exception:
                pass
    return 0


def _ui_hard_delete(chat, mid):
    """purana message 100% uda do — duplicate card nahi bachega."""
    if not mid:
        return
    try:
        asyncio.create_task(bot.delete_messages(chat, [int(mid)]))
    except Exception:
        pass


# "rich bhej diya, id pata nahi" — eor ko batata hai ki plain fallback NA kare
_RICH_DONE = object()

# (chat, command-msg id) → asli rich message id  ·  plan B ke baad yahi use hota hai
_RICH_ALIAS: Dict[Any, int] = {}
_RICH_OFF: Dict[Any, float] = {}       # chat → us waqt tak rich band
_LAST_CARD: Dict[Any, tuple] = {}      # (chat, msg) → (hash, card id, time)


class _UiMsg:
    """rich card ka halka wrapper — .edit() / .delete() kaam karte hain."""
    __slots__ = ("event", "chat_id", "id", "_plain")

    def __init__(self, event, chat_id, mid, plain):
        self.event = event
        self.chat_id = chat_id
        self.id = mid
        self._plain = plain

    async def edit(self, text=None, **kw):
        """rich hi rahega — plain text is card me kabhi nahi ghusega."""
        got = await _ui_render(self.event, self.id, text or "", kw)
        if got is None:
            return None
        if isinstance(got, _UiMsg) and got.id:
            self.id = got.id                 # agli edit usi msg pe
        return got

    async def delete(self):
        chat = self.chat_id
        mid = int(self.id or 0)
        try:
            await self.event.delete()
        except Exception:
            pass
        if mid and mid != int(getattr(self.event, "id", 0) or 0):
            try:
                await bot.delete_messages(chat, [mid])
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._plain, name) if self._plain is not None else None


async def _ui_build(text):
    """text → (InputRichMessage, ok). emoji docs na mile to plain rebuild."""
    docs = set()
    blocks = _ui_blocks(text, docs)
    if not blocks:
        return None, False
    row = _ui_buttons(text, docs)
    if row is not None:
        blocks = (blocks[:-1] + [row]
                  if type(blocks[-1]).__name__ == "PageBlockDivider"
                  else blocks + [row])
    docs_in = await _rich_docs(docs) if docs else []
    if docs and len(docs_in) < len(docs):
        # kuch documents resolve nahi hue → emoji ke bina dobara banao
        _rm_log("emoji docs", RuntimeError("%d/%d resolve" % (len(docs_in), len(docs))))
        tok = _RICH_PLAIN.set(True)
        try:
            docs2 = set()
            blocks = _ui_blocks(text, docs2)
            row2 = _ui_buttons(text, docs2)
            if row2 is not None:
                blocks = (blocks[:-1] + [row2]
                          if type(blocks[-1]).__name__ == "PageBlockDivider"
                          else blocks + [row2])
            docs_in = []
        finally:
            _RICH_PLAIN.reset(tok)
    rich = types.InputRichMessage(blocks=_sanitize_blocks(blocks))
    if docs_in:
        rich.documents = docs_in
    return rich, True


async def _ui_render(event, mid, text, kw=None):
    """text → rich edit.

    • plan A  : usi message ko rich bana do
    • plan B  : pehli baar edit fail (plain → rich allowed nahi) → naya rich
                message bhejo, purana delete, aur naya id yaad rakho —
                agli saari edits USI message pe jayengi (spam band).
    """
    if not text or not await _ui_rich_ok():
        return None
    chat = getattr(event, "chat_id", None)
    try:
        if chat in _RICH_OFF and time.time() < _RICH_OFF[chat]:
            return None
    except Exception:
        pass
    # ── duplicate guard: wahi text 6 sec ke andar dobara → naya msg nahi
    try:
        import hashlib
        h = hashlib.md5(text.encode("utf-8", "ignore")).hexdigest()
        prev = _LAST_CARD.get((chat, mid))
        if prev and prev[0] == h and (time.time() - prev[2]) < 6 and prev[1]:
            return _UiMsg(event, chat, prev[1], None)
    except Exception:
        pass

    try:
        rich, ok = await _ui_build(text)
        if not ok or rich is None:
            return None
        peer = None
        try:
            peer = await event.get_input_chat()
        except Exception:
            peer = None
        if peer is None:
            peer = await bot.get_input_entity(chat)

        # pichhle plan B ka message id ho to wahi edit karo
        alias = _RICH_ALIAS.get((chat, mid)) or mid

        # ── plan A: usi message ko article bana do
        try:
            await bot(functions.messages.EditMessageRequest(
                peer=peer, id=alias, message="", rich_message=rich))
            _LAST_CARD[(chat, mid)] = (h, alias, time.time())
            return _UiMsg(event, chat, alias, None)
        except Exception as _e1:
            _rm_log("edit", _e1)
            if "MESSAGE_NOT_MODIFIED" in str(_e1):
                return _UiMsg(event, chat, alias, None)

        # ── plan B: naya rich message bhejo, purana uda do (ek hi baar)
        if alias != mid:
            _RICH_ALIAS.pop((chat, mid), None)      # alias mar gaya → naya bhejo
        try:
            sent = await bot(functions.messages.SendMessageRequest(
                peer=peer, message="", rich_message=rich,
                random_id=random.getrandbits(62)))
            new_id = _sent_msg_id(sent)
            if not new_id:
                # Updates me id na mile → chat ka last message hi wahi hai
                try:
                    last = await bot.get_messages(chat, limit=1)
                    new_id = int(getattr(last[0], "id", 0) or 0) if last else 0
                except Exception:
                    new_id = 0
            _ui_hard_delete(chat, mid)
            if new_id:
                if len(_RICH_ALIAS) > 400:
                    _RICH_ALIAS.clear()
                _RICH_ALIAS[(chat, mid)] = new_id     # ← agli edits yahan
                _LAST_CARD[(chat, mid)] = (h, new_id, time.time())
                return _UiMsg(event, chat, new_id, None)
            # id phir bhi nahi mili — rich SEND ho chuka hai, isliye
            # plain fallback bilkul nahi (warna do card ban jaate hain)
            return _RICH_DONE
        except Exception as _e2:
            _rm_log("send", _e2)
            # ── retry: custom emoji documents ke bina (kabhi koi id reject hoti hai)
            try:
                tok = _RICH_PLAIN.set(True)
                try:
                    plain_blocks = _sanitize_blocks(_ui_blocks(text, set()))
                finally:
                    _RICH_PLAIN.reset(tok)
                sent2 = await bot(functions.messages.SendMessageRequest(
                    peer=peer, message="",
                    rich_message=types.InputRichMessage(blocks=plain_blocks),
                    random_id=random.getrandbits(62)))
                new2 = _sent_msg_id(sent2)
                _ui_hard_delete(chat, mid)
                if new2:
                    _RICH_ALIAS[(chat, mid)] = new2
                    _LAST_CARD[(chat, mid)] = (h, new2, time.time())
                    return _UiMsg(event, chat, new2, None)
                return _RICH_DONE
            except Exception as _e3:
                _rm_log("send2", _e3)
            _RICH_OFF[chat] = time.time() + 8
            return None
    except Exception as _e:
        _rm_log("ui", _e)
        return None


async def eor(event, text, plain=False, **kw):
    """edit-or-reply → Message object.

    plain=True  → sirf normal text (loader / animation ke liye) —
                  rich card ke andar plain text ghusne hi nahi deta.
    """
    if not text:
        return None
    text = align_panel(text)
    if not plain and not _PLAIN_MODE.get():
        try:
            _rich = await _ui_render(event, getattr(event, "id", None), text, kw)
            if _rich is _RICH_DONE:
                return None                      # rich gaya — duplicate na banao
            if _rich is not None:
                return _rich
        except Exception:
            pass
    try:
        uid = event.sender_id
        now = time.time()
        if uid in COMMAND_COOLDOWN and now - COMMAND_COOLDOWN[uid] < 0.3:
            await asyncio.sleep(0.3)
        COMMAND_COOLDOWN[uid] = now
    except Exception:
        pass
    try:
        return await event.edit(text, **kw)
    except FloodWaitError as fw:
        try:
            await asyncio.sleep(min(fw.seconds, 10))
            return await event.edit(text, **kw)
        except Exception:
            pass
    except Exception:
        pass
    try:
        return await event.reply(text, **kw)
    except Exception:
        return None


async def aedit(msg, text, **kw):
    """msg.edit() ke liye — rich card ho to rich, warna plain."""
    try:
        if isinstance(msg, _UiMsg):
            return await msg.edit(align_panel(text), **kw)
        return await msg.edit(align_panel(text), **kw)
    except Exception:
        return None


async def _del_after(msg, secs):
    try:
        await asyncio.sleep(secs)
        await msg.delete()
    except Exception:
        pass


async def flash(event, text, secs=None, plain=True):
    """working/status message — apne aap udd jata hai (plain = reliable anim)"""
    msg = await eor(event, text, plain=plain)
    if msg is not None:
        asyncio.create_task(_del_after(msg, secs or TMP_TTL))
    return msg


async def done(event, text, secs=None):
    """result message — styled, phir auto-clean"""
    msg = await eor(event, text)
    if msg is not None:
        asyncio.create_task(_del_after(msg, secs or TMP_TTL))
    return msg


async def silent_delete(event):
    try:
        await event.delete()
    except Exception:
        pass


def mention_ids(event) -> list:
    """Text-mention se user id nikalo — jinka @username nahi hota.

    Group me kisi ka naam tap karke `.kick Naam` bhejo to Telegram usko
    `MessageEntityMentionName(user_id=...)` bana deta hai (text me @ nahi
    hota) — isi wajah se pehle "user nahi mila" aata tha.
    """
    out = []
    msg = getattr(event, "message", None) or getattr(event, "msg", None)
    for ent in (getattr(msg, "entities", None) or []):
        uid = getattr(ent, "user_id", None)
        if uid:
            out.append(int(uid))
            continue
        url = (getattr(ent, "url", "") or "").strip()
        if "tg://user?id=" in url:
            try:
                out.append(int(url.split("id=")[1].split("&")[0]))
            except Exception:
                pass
    return out


async def get_targets(event, arg="") -> Set[int]:
    targets: Set[int] = set()
    if event.is_reply:
        try:
            r = await event.get_reply_message()
            if r and r.sender_id:
                targets.add(int(r.sender_id))
        except Exception:
            pass
    if arg:
        for part in arg.strip().split():
            if not part:
                continue
            if part.isdigit():
                targets.add(int(part))
                continue
            try:
                ent = await bot.get_entity(part)
                if ent and getattr(ent, "id", None):
                    targets.add(int(ent.id))
            except Exception:
                pass
    # text-mention wale users (bina @username) bhi target me
    try:
        for uid in mention_ids(event):
            targets.add(int(uid))
    except Exception:
        pass
    try:
        me = await bot.get_me()
        targets.discard(me.id)
    except Exception:
        pass
    return targets


async def resolve_uid(event, arg=""):
    """ek user id — reply / @user / id / DM auto-detect"""
    if event.is_reply:
        try:
            r = await event.get_reply_message()
            if r and r.sender_id:
                return int(r.sender_id), r
        except Exception:
            pass
    tok = (arg or "").strip().split()[0] if arg else ""
    if tok:
        try:
            ent = await bot.get_entity(tok)
            if ent and getattr(ent, "id", None):
                return int(ent.id), None
        except Exception:
            if tok.lstrip("-").isdigit():
                return int(tok), None
    # text-mention (jiska username nahi hota) → seedha user_id
    try:
        mids = mention_ids(event)
        if mids:
            return int(mids[0]), None
    except Exception:
        pass
    # DM me ho to saamne wala hi target
    try:
        if getattr(event, "is_private", False) and event.chat_id:
            cid = int(event.chat_id)
            if cid > 0:
                return cid, None
    except Exception:
        pass
    return None, None


def parse_time(txt):
    """'10m', '2h', '3d' → seconds"""
    txt = (txt or "").strip().lower()
    m = re.match(r"^(\d+)\s*([smhd]?)$", txt)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2) or "m"
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


async def play_frames(event, frames, title="", delay=0):
    d = delay or STORY_DELAY
    msg = await eor(event, f"{E['film']} {sc(title)} {E['dot']} {sc('starting')}…")
    if msg is None:
        return
    for raw in frames:
        frame = raw.replace("\\n", "\n")
        body = f"```\n{frame}\n```"
        try:
            await msg.edit(body)
        except FloodWaitError as fw:
            await asyncio.sleep(min(fw.seconds + 1, 20))
            try:
                await msg.edit(body)
            except Exception:
                pass
        except MessageNotModifiedError:
            pass
        except Exception:
            break
        await asyncio.sleep(d)


def media_kinds(msg) -> Set[str]:
    kinds = {"all", "msg"}
    media = getattr(msg, "media", None)
    if media is None:
        kinds.add("text")
    else:
        kinds.add("media")
        if isinstance(media, types.MessageMediaPhoto):
            kinds.add("photo")
        elif isinstance(media, types.MessageMediaDocument):
            doc = getattr(media, "document", None)
            if doc is not None:
                for attr in getattr(doc, "attributes", []) or []:
                    if isinstance(attr, types.DocumentAttributeSticker):
                        kinds.add("sticker")
                    elif isinstance(attr, types.DocumentAttributeAnimated):
                        kinds.add("gif")
                    elif isinstance(attr, types.DocumentAttributeVideo):
                        kinds.add("video")
                    elif isinstance(attr, types.DocumentAttributeAudio):
                        kinds.add("audio")
                        if getattr(attr, "voice", False):
                            kinds.add("voice")
                kinds.add("document")
        elif isinstance(media, types.MessageMediaWebPage):
            kinds.update({"webpage", "link"})
        elif isinstance(media, types.MessageMediaContact):
            kinds.add("contact")
        elif isinstance(media, types.MessageMediaGeo):
            kinds.add("location")
        elif isinstance(media, types.MessageMediaPoll):
            kinds.add("poll")
        elif isinstance(media, types.MessageMediaDice):
            kinds.add("dice")
        elif isinstance(media, types.MessageMediaGame):
            kinds.add("game")
        elif isinstance(media, types.MessageMediaInvoice):
            kinds.add("invoice")
    if getattr(msg, "forward", None):
        kinds.add("forward")
    if getattr(msg, "via_bot_id", None):
        kinds.add("inline")
    txt = getattr(msg, "message", "") or ""
    if "http://" in txt or "https://" in txt or "t.me/" in txt or "www." in txt:
        kinds.add("link")
    if txt.startswith((".", "/", "!", "#", "$")):
        kinds.add("command")
    return kinds


LOCK_TYPES = ["all", "msg", "text", "media", "photo", "video", "document",
              "sticker", "gif", "audio", "voice", "link", "forward",
              "command", "inline", "poll", "contact", "location", "game",
              "dice", "webpage"]


def autoread_match(event) -> bool:
    if not AUTOREAD:
        return False
    if "all" in AUTOREAD:
        return True
    if event.is_group and "group" in AUTOREAD:
        return True
    if event.is_private and "private" in AUTOREAD:
        return True
    if getattr(event, "is_channel", False) and "channel" in AUTOREAD:
        return True
    return False


def dialog_kind(d):
    """Dialog ka type — `d.is_group` Telethon me hota hi nahi (crash karta tha).

    "user" · "group" · "channel" · "other"
    """
    ent = getattr(d, "entity", None) or d
    if isinstance(ent, types.User):
        return "user"
    if isinstance(ent, types.Chat):
        return "chat"
    if isinstance(ent, types.Channel):
        return "group" if getattr(ent, "megagroup", False) else "channel"
    # purane/other client fallback
    if getattr(d, "is_group", False):
        return "chat"
    if getattr(d, "is_user", False):
        return "user"
    if getattr(d, "is_channel", False):
        return "channel"
    return "other"


async def broadcast_targets(kind):
    if kind == "db":
        return list(BCDB)
    out = []
    try:
        async for d in bot.iter_dialogs():
            try:
                k = dialog_kind(d)
                if k in ("chat", "group") and kind in ("group", "all"):
                    out.append(d.id)
                elif k == "user" and kind in ("private", "all"):
                    out.append(d.id)
                elif k == "channel" and kind in ("channel", "all"):
                    out.append(d.id)
            except Exception:
                continue
    except Exception:
        pass
    return out


_URL_RE = re.compile(r"^(?:https?://|www\.|t\.me/|youtu\.be/|m\.youtube\.com/)", re.I)


def looks_url(t):
    return bool(_URL_RE.match((t or "").strip()))


def _yt_target(q, n=1):
    q = (q or "").strip()
    return q if looks_url(q) else f"ytsearch{max(1, n)}:{q}"


def _ffmpeg_ok():
    return shutil.which("ffmpeg") is not None


async def yt_download(target, audio=False, search=1):
    """yt-dlp — link ho ya seedhe words, dono chalega.

    Pehle sirf URL chalta tha isliye `.music freaked out` pe
    "'freaked out' is not a valid URL" aata tha. Ab words ko
    `ytsearch1:` me convert karke search hota hai.
    """
    import yt_dlp
    loop = asyncio.get_running_loop()
    tag = str(int(time.time() * 1000))
    tmpl = os.path.join(TEMP_PATH, f"dl_{tag}_%(id)s.%(ext)s")

    opts = {
        "outtmpl": tmpl, "quiet": True, "no_warnings": True, "noprogress": True,
        "noplaylist": True, "retries": 3, "fragment_retries": 3,
        "socket_timeout": 25, "nocheckcertificate": True,
        "restrictfilenames": True, "overwrites": True,
        "default_search": f"ytsearch{max(1, search)}",
    }
    if audio:
        # audio-only format (video wala mp4 nahi) — android client aisa
        # format nahi deta, isliye default web client hi rakha hai
        opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        if _ffmpeg_ok():
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "opus",     # telegram voice note = opus/ogg
                "preferredquality": "96",
            }]
    else:
        opts["format"] = "best[filesize<48M]/best"
        opts["merge_output_format"] = "mp4"

    def run(o):
        with yt_dlp.YoutubeDL(o) as ydl:
            info = ydl.extract_info(_yt_target(target, search), download=True)
            if info and info.get("entries"):
                info = info["entries"][0] if info["entries"] else None
            return info

    try:
        info = await loop.run_in_executor(None, run, opts)
    except Exception as first:
        simple = {k: v for k, v in opts.items() if k != "extractor_args"}
        try:
            info = await loop.run_in_executor(None, run, simple)
        except Exception:
            raise first

    files = [f for f in glob.glob(os.path.join(TEMP_PATH, f"dl_{tag}_*"))
             if not f.endswith((".part", ".ytdl"))]
    return (files[0] if files else None), (info or {})


def _mmss(sec):
    try:
        sec = int(sec or 0)
    except Exception:
        sec = 0
    return f"{sec // 60}:{sec % 60:02d}" if sec else "—"


# ══════════════════════════════════════════════════════════════
#                        ᴛᴇxᴛ ʟɪsᴛs
# ══════════════════════════════════════════════════════════════
reply_list = ["𝐊ʏᴀ 𝐑ᴇ 𝐑ᴀɴᴅɪᴋᴇ 𝐂ᴏᴏʟ 𝐁ᴀɴᴇɢᴀ 𝐓ᴜ 𝐂ʜᴀʟ 𝐀ʙ 𝐂ʜᴜᴅ 𝐀ᴘɴᴇ 𝐁ᴀᴘ  𝐍ɪᴋ  𝐒ᴇ - 🦢💘",
    "𝐊ɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ 𝐘ᴀᴀʀ - 𝐉ᴀɪ Dʜʀᴜᴠ ! 🌙",
    "acha beta 😂🔥👊🏻 ? coi na me toh HATER codunga 😹💔🔥😆👊🏻💥",
    "chudke bhaga kaise 😂💥🤣🤘🏻",
    "ne toh  𝐍ɪᴋ ka lun muh me lelia 😂🙏🏻😂🙏🏻",
    "try maa सूर्य☀ nikalte hi pel du 😹🔥💔",
    "mkl lun te vaj 😂✊🏻💦",
    "𝗧ᴍᴋ𝗕 pe  𝐍ɪᴋ ka hamla 😂⚔🔥💥",
    "𝐂ʜʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के 💛🤍🩵",
    "oi 𝐓ᴇʀɪ 𝐌‌ᴀᴀ गुलाम ₰🖤",
    "chl rndyce chud ke dikha 😂💥🤣🔥",
    "𝐊ɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ naacho 💃🏻💃🏻🕺🏻🎶😂😆💞🔥 !",
    "tera baap bass 𝐵��������������������hai 😂🎀",
    " try maa hagte hue paad mari -#😹🔥🥀",
    "  𝐓ᴇʀɪ 𝐌ᴜᴍᴍʏ 𝐂ʜᴏᴅ 𝐃ɪ  𝐍ɪᴋ 𝐍ᴇ 𝐁ᴡᴀʜᴀʜᴀʜᴀ ⚜","𝐊ʏᴀ 𝐑ᴇ 𝐑ᴀɴᴅɪᴋᴇ 𝐂ᴏᴏʟ 𝐁ᴀɴᴇɢᴀ 𝐓ᴜ 𝐂ʜᴀʟ 𝐀ʙ 𝐂ʜᴜᴅ 𝐀ᴘɴᴇ 𝐁ᴀᴀᴘ 𝐵��������������������𝐒ᴇ - 🦢💘",
    "𝐊ɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ 𝐘ᴀᴀʀ - 𝐉ᴀɪ  𝐍ɪᴋ ! 🌙",
    "acha beta 😂🔥👊🏻 ? coi na me toh HATER codunga 😹💔🔥😆👊🏻💥",
    "chudke bhaga kaise 😂💥🤣🤘🏻",
    "ne toh  𝐍ɪᴋ ka lun muh me lelia 😂🙏🏻😂🙏🏻",
    "try maa सूर्य☀ nikalte hi pel du 😹🔥💔",
    "mkl lun te vaj 😂✊🏻💦",
    "𝗧ᴍᴋ𝗕 pe  𝐍ɪᴋ ka hamla 😂⚔🔥💥",
    "𝐂ʜʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के 💛🤍🩵",
    "oi 𝐓ᴇʀɪ 𝐌‌ᴀᴀ गुलाम ₰🖤",
    "chl rndyce chud ke dikha 😂💥🤣🔥",
    "𝐊ɪ 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ naacho 💃🏻💃🏻🕺🏻🎶😂😆💞🔥 !",
    "tera baap bass  𝐍ɪᴋ hai 😂🎀",
    " try maa hagte hue paad mari -#😹🔥🥀",
    "  𝐓ᴇʀɪ 𝐌ᴜᴍᴍʏ 𝐂ʜᴏᴅ 𝐃ɪ  𝐍ɪᴋ 𝐍ᴇ 𝐁ᴡᴀʜᴀʜᴀʜᴀ ⚜"]

reply_texts = ["⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद 𝐍ɪᴋ बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
"नहीं नहीं तेरी मां को 𝐒ɪʀғ  𝐍ɪᴋ बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
"तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
"𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
"सोच तेरी बहन को  𝐍ɪᴋ बाप का गुलाम चोद रहा 😎🔥",
"Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
"Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन  𝐍ɪᴋ /\\~ 👑 बाप से सही chudi 🥵🔥",
"ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ  𝐍ɪᴋ बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥",
"🇮🇳𝐵𝐻𝐴𝑅𝐴𝑇 𝐻𝐴𝑀𝐴𝑅𝐴 𝐷𝐸𝑆𝐻 𝐻 𝐴𝑈𝑅 𝑈𝑆 𝐷𝐸𝑆𝐻 𝑀𝐸 तेरी मां घर घर जाके MOAN करती है ! 🛐","⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद  𝐍ɪᴋ बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
"नहीं नहीं तेरी मां को 𝐒ɪʀғ  𝐍ɪᴋ बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
"तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
"𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
"सोच तेरी बहन को  𝐍ɪᴋ बाप का गुलाम चोद रहा 😎🔥",
"Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
"Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन  𝐍ɪᴋ /\\~ 👑 बाप से सही chudi 🥵🔥",
"ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ  𝐍ɪᴋ बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥",
"🇮🇳𝐵𝐻𝐴𝑅𝐴𝑇 𝐻𝐴𝑀𝐴𝑅𝐴 𝐷𝐸𝑆𝐻 𝐻 𝐴𝑈𝑅 𝑈𝑆 𝐷𝐸𝑆𝐻 𝑀𝐸 तेरी मां घर घर जाके MOAN करती है ! 🛐","⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद  𝐍ɪᴋ बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
"नहीं नहीं तेरी मां को 𝐒ɪʀғ  𝐍ɪᴋ बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
"तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
"𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
"सोच तेरी बहन को  𝐍ɪᴋ बाप का गुलाम चोद रहा 😎🔥",
"Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
"Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन  𝐍ɪᴋ /\\~ 👑 बाप से सही chudi 🥵🔥",
"ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ  𝐍ɪᴋ बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥",
"🇮🇳𝐵𝐻𝐴𝑅𝐴𝑇 𝐻𝐴𝑀𝐴𝑅𝐴 𝐷𝐸𝑆𝐻 𝐻 𝐴𝑈𝑅 𝑈𝑆 𝐷𝐸𝑆𝐻 𝑀𝐸 तेरी मां घर घर जाके MOAN करती है ! 🛐","⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद  𝐍ɪᴋ  बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
"नहीं नहीं तेरी मां को 𝐒ɪʀғ  𝐍ɪᴋ बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
"तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
"𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
"सोच तेरी बहन को  𝐍ɪᴋ बाप का गुलाम चोद रहा 😎🔥",
"Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
"Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन  𝐍ɪᴋ /\\~ 👑 बाप से सही chudi 🥵🔥",
"ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ  𝐍ɪᴋ बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥",
"🇮🇳𝐵𝐻𝐴𝑅𝐴𝑇 𝐻𝐴𝑀𝐴𝑅𝐴 𝐷𝐸𝑆𝐻 𝐻 𝐴𝑈𝑅 𝑈𝑆 𝐷𝐸𝑆𝐻 𝑀𝐸 तेरी मां घर घर जाके MOAN करती है ! 🛐"]

fun_texts = ["तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",
"𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",
"𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-‘🚂-‘.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",
"˙✧˖°📷༘ ⋆｡° 𝐓ᴇʀʏ 𝐌ᴀ  𝐊ᴀ 𝐂ʜɪʟᴅ 𝐏ᴏʀɴ 𝐑ᴇᴄᴏʀᴅ 𝐇ᴏɢʏᴀ 𝐀ʙ 𝐓ᴏ 𝐒ɪᴅʜᴀ 𝐕ɪʀᴀʟ 𝐇ᴏɢᴀ 𝐘ᴇ ˙✧˖°📷༘ ⋆｡°",
"𓂃✍︎ 𝑵ʏ 𝑵ʏ 𝑨ʙ 𝑲ᴜᴄʜ 𝑵ʏ 𝑯ᴏ 𝑺ᴋᴛᴀ 𝑻ᴇʀɪ  𝑪ᴜᴅᴀɪ 𝑲ɪ 𝑺ᴄʀɪᴘᴛ 𝑨ʙ 𝑳ᴇᴀᴋ 𝑯ᴏᴋᴇ 𝑯ʏ 𝑴ᴀɴᴇɢɪ 𓂃✍︎",
"⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭","तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",
"𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",
"𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-‘🚂-‘.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",
"˙✧˖°📷༘ ⋆｡° 𝐓ᴇʀʏ 𝐌ᴀ  𝐊ᴀ 𝐂ʜɪʟᴅ 𝐏ᴏʀɴ 𝐑ᴇᴄᴏʀᴅ 𝐇ᴏɢʏᴀ 𝐀ʙ 𝐓ᴏ 𝐒ɪᴅʜᴀ 𝐕ɪʀᴀʟ 𝐇ᴏɢᴀ 𝐘ᴇ ˙✧˖°📷༘ ⋆｡°",
"𓂃✍︎ 𝑵ʏ 𝑵ʏ 𝑨ʙ 𝑲ᴜᴄʜ 𝑵ʏ 𝑯ᴏ 𝑺ᴋᴛᴀ 𝑻ᴇʀɪ  𝑪ᴜᴅᴀɪ 𝑲ɪ 𝑺ᴄʀɪᴘᴛ 𝑨ʙ 𝑳ᴇᴀᴋ 𝑯ᴏᴋᴇ 𝑯ʏ 𝑴ᴀɴᴇɢɪ 𓂃✍︎",
"⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭","तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",
"𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",
"𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-‘🚂-‘.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",
"˙✧˖°📷༘ ⋆｡° 𝐓ᴇʀʏ 𝐌ᴀ  𝐊ᴀ 𝐂ʜɪʟᴅ 𝐏ᴏʀɴ 𝐑ᴇᴄᴏʀᴅ 𝐇ᴏɢʏᴀ 𝐀ʙ 𝐓ᴏ 𝐒ɪᴅʜᴀ 𝐕ɪʀᴀʟ 𝐇ᴏɢᴀ 𝐘ᴇ ˙✧˖°📷༘ ⋆｡°",
"𓂃✍︎ 𝑵ʏ 𝑵ʏ 𝑨ʙ 𝑲ᴜᴄʜ 𝑵ʏ 𝑯ᴏ 𝑺ᴋᴛᴀ 𝑻ᴇʀɪ  𝑪ᴜᴅᴀɪ 𝑲ɪ 𝑺ᴄʀɪᴘᴛ 𝑨ʙ 𝑳ᴇᴀᴋ 𝑯ᴏᴋᴇ 𝑯ʏ 𝑴ᴀɴᴇɢɪ 𓂃✍︎",
"⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭","तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",
"𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",
"𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-‘🚂-‘.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",
"˙✧˖°📷༘ ⋆｡° 𝐓ᴇʀʏ 𝐌ᴀ  𝐊ᴀ 𝐂ʜɪʟᴅ 𝐏ᴏʀɴ 𝐑ᴇᴄᴏʀᴅ 𝐇ᴏɢʏᴀ 𝐀ʙ 𝐓ᴏ 𝐒ɪᴅʜᴀ 𝐕ɪʀᴀʟ 𝐇ᴏɢᴀ 𝐘ᴇ ˙✧˖°📷༘ ⋆｡°",
"𓂃✍︎ 𝑵ʏ 𝑵ʏ 𝑨ʙ 𝑲ᴜᴄʜ 𝑵ʏ 𝑯ᴏ 𝑺ᴋᴛᴀ 𝑻ᴇʀɪ  𝑪ᴜᴅᴀɪ 𝑲ɪ 𝑺ᴄʀɪᴘᴛ 𝑨ʙ 𝑳ᴇᴀᴋ 𝑯ᴏᴋᴇ 𝑯ʏ 𝑴ᴀɴᴇɢɪ 𓂃✍︎",
"⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭" ]

flag_texts = [" ོ༘₊⁺🇮🇳 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ 𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ  𝐈ɴᴅɪᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇳 ₊⁺⋆.˚",
" ོ༘₊⁺🇯🇵 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐉ᴀᴘᴀɴ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇯🇵 ₊⁺⋆. " ,
" ₊⁺🇺🇸 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐒𝐀 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇺🇸 ₊⁺⋆.˚",
" ོ༘₊⁺🇬🇧 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐊 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇬🇧 ₊⁺⋆.˚", 
" ོ༘₊⁺🇰🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝗗𝗛𝗥𝗨𝗩 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐊ᴏʀᴇᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇰🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇩🇪 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐆ᴇʀᴍᴀɴʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇩🇪 ₊⁺⋆.˚",
" ོ༘₊⁺🇫🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐅ʀᴀɴᴄᴇ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇫🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇮🇹 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐈ᴛᴀʟʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇹 ₊⁺⋆.˚",
" ོ༘₊⁺🇧🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐁ʀᴀᴢɪʟ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇧🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇨🇦 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐂ᴀɴᴀᴅᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇨🇦 ₊⁺⋆.˚"," ོ༘₊⁺🇮🇳 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ 𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ  𝐈ɴᴅɪᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇳 ₊⁺⋆.˚",
" ོ༘₊⁺🇯🇵 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐉ᴀᴘᴀɴ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇯🇵 ₊⁺⋆. " ,
" ₊⁺🇺🇸 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐒𝐀 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇺🇸 ₊⁺⋆.˚",
" ོ༘₊⁺🇬🇧 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐊 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇬🇧 ₊⁺⋆.˚", 
" ོ༘₊⁺🇰🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐊ᴏʀᴇᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇰🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇩🇪 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐆ᴇʀᴍᴀɴʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇩🇪 ₊⁺⋆.˚",
" ོ༘₊⁺🇫🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐅ʀᴀɴᴄᴇ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇫🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇮🇹 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐈ᴛᴀʟʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇹 ₊⁺⋆.˚",
" ོ༘₊⁺🇧🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐁ʀᴀᴢɪʟ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇧🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇨🇦 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐍ɪᴋ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐂ᴀɴᴀᴅᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇨🇦 ₊⁺⋆.˚"]

heart_replies = ["𓂃˖˳·˖ ִֶָ ⋆❤️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🧡͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🧡 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💛͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💛 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💚͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💚 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💙͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💙 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💜͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💜 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🖤͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🖤 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤍͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤍 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤎͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤎 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💖͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💖 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💗͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💗 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💓͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💓 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💞͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💞 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💕͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💕 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💘͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💘 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💝͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💝 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💟͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💟 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❣️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❣️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🔥͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🔥 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🩹͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🩹 ݁˖⭑.ᐟ","𓂃˖˳·˖ ִֶָ ⋆❤️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🧡͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🧡 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💛͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💛 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💚͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💚 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💙͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💙 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💜͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💜 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🖤͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🖤 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤍͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤍 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤎͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤎 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💖͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💖 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💗͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💗 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💓͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💓 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💞͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💞 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💕͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💕 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💘͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💘 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💝͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💝 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💟͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💟 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❣️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❣️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🔥͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🔥 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🩹͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🩹 ݁˖⭑.ᐟ"]


# ══════════════════════════════════════════════════════════════
#                       sᴛᴏʀʏ ғʀᴀᴍᴇs
# ══════════════════════════════════════════════════════════════
LOVE6_THUG = [
    "😎 THUG LIFE - 1/10\n👦\n/👕\\\n 👖\n`Normal ladka...`",
    "😎 THUG LIFE - 2/10\n😏        😒\n/👕\\      /👗\\\n 👖        /|.\n`Ignore kiya 😒`",
    "😎 THUG LIFE - 3/10\n😎  🕶️  😎\n/👕\\      /👗\\\n 👖        /|.\n`Chashma lagaya 🕶️`",
    "😎 THUG LIFE - 4/10\n😎💨        😳\n/👕\\      /👗\\\n 👖        /|.\n`Attitude dikhaya`",
    "😎 THUG LIFE - 5/10\n😍        😍\n/👕\\      /👗\\\n 👖        /|.\n`Impress ho gayi`",
    "😎 THUG LIFE - 6/10\n😚        😚\n/👕\\      /👗\\\n 👖        /|.\n`Baatein shuru`",
    "😎 THUG LIFE - 7/10\n🥰  🌹  🥰\n/👕\\      /👗\\\n 👖        /|.\n`Phool diya 🌹`",
    "😎 THUG LIFE - 8/10\n😘        😘\n/👕\\      /👗\\\n 👖        /|.\n`Haan bol diya`",
    "😎 THUG LIFE - 9/10\n😎  👫  😎\n/👕\\      /👗\\\n 👖        /|.\n`Couple goals`",
    "😎 THUG LIFE - 10/10 - THE END\n👑  😎  👑\n`NIK THUG KING 👑`",
]
MEME_MUMMY = [
    "😡 MUMMY DAANT - 1/10\n👦  🎮\n/👕\\\n 👖\n`Game khel raha 🎮`",
    "😡 MUMMY DAANT - 2/10\n👩        👦\n/👗\\      /👕\\\n /|\\       👖\n`Mummy: padh le! 😡`",
    "😡 MUMMY DAANT - 3/10\n😒        😡\n/👕\\      /👗\\\n 👖        /|.\n`2 min aur 😒`",
    "😡 MUMMY DAANT - 4/10\n👩  🩴  👦\n/👗\\      /👕\\\n /|\\       👖\n`Chappal nikali 🩴`",
    "😡 MUMMY DAANT - 5/10\n😭  🏃  👩\n/👕\\      /👗\\\n 👖        /|.\n`Bhaaga 🏃😭`",
    "😡 MUMMY DAANT - 6/10\n😅  📚  😅\n/👕\\      /👗\\\n 👖        /|.\n`Padhne ka natak 📚`",
    "😡 MUMMY DAANT - 7/10\n😊  👩  😊\n/👗\\      /👕\\\n /|\\       👖\n`Mummy khush`",
    "😡 MUMMY DAANT - 8/10\n😈  📱  😈\n/👕\\\n 👖\n`Mummy gayi to phone 😈`",
    "😡 MUMMY DAANT - 9/10\n👩  😳  👦\n/👗\\      /👕\\\n /|\\       👖\n`Fir pakda! 😳`",
    "😡 MUMMY DAANT - 10/10 - THE END\n😭  🩴  😭\n`Pit gaya 😭`\n`NIK MEME KING 👑`",
]
MEME_SASTA_NASHA = [
    "🍻 SASTA NASHA - 1/10\n👦👦\n/👕\\/👕\\\n`Shaam plan 🍻`",
    "🍻 SASTA NASHA - 2/10\n🍺  😎  🍺\n/👕\\      /👕\\\n 👖        👖\n`Ek peg 😎`",
    "🍻 SASTA NASHA - 3/10\n🥴        🥴\n/👕\\      /👕\\\n 👖        👖\n`Talli 🥴`",
    "🍻 SASTA NASHA - 4/10\n😵  💬  😵\n/👕\\      /👕\\\n 👖        👖\n`Bakchodi 😵`",
    "🍻 SASTA NASHA - 5/10\n😂  🤣  😂\n/👕\\      /👕\\\n 👖        👖\n`Lotpot 😂`",
    "🍻 SASTA NASHA - 6/10\n😡  💬  😡\n/👕\\      /👕\\\n 👖        👖\n`Ladai 😡`",
    "🍻 SASTA NASHA - 7/10\n😭  🤗  😭\n/👕\\      /👕\\\n 👖        👖\n`Rone lage 😭`",
    "🍻 SASTA NASHA - 8/10\n😴        😴\n/👕\\      /👕\\\n 👖        👖\n`Sadak pe soye 😴`",
    "🍻 SASTA NASHA - 9/10\n👮  😳  👦\n/👕\\      /👕\\\n 👖        👖\n`Police 👮`",
    "🍻 SASTA NASHA - 10/10 - THE END\n🏃  💨  🏃\n`Bhaag gaye 🏃💨`\n`NIK NASHA KING 👑`",
]

LOVE_STORY_FRAMES = [
    """❤️ LOVE STORY - Part 1
😐        😕
/👕\\      <裝\\
 👖        /|.
━━━━━━━━━━━━━━━
`Door se dekha...`""",

    """❤️ LOVE STORY - Part 2
😉        😳
/👕\\      /👗\\
 👖        /|.
━━━━━━━━━━━━━━━
`Ladka ne wink maara 😉`""",

    """❤️ LOVE STORY - Part 3
😚        😒
/👕\\      <裝>
 👖        /|.
━━━━━━━━━━━━━━━
`Kiss diya, ladki nakhre me 😒`""",

    """❤️ LOVE STORY - Part 4
😍        ☺️
/👕\\      /👗\\
 👖        /|.
━━━━━━━━━━━━━━━
`Dono ko pyar ho gaya 😍`""",

    """❤️ LOVE STORY - Part 5
    😘   😊
   /👕\\/👗\\
    👖   /|.
━━━━━━━━━━━━━━━
`Paas aa gaye...`""",

    """❤️ LOVE STORY - Part 6
   😳   😁
   /|\\  /👙\\
   /     /|.
━━━━━━━━━━━━━━━
`Sharma gaye 🙈`""",

    """❤️ LOVE STORY - Part 7
  😈     😰
  <|\\     👙
   _/\\     /|.
━━━━━━━━━━━━━━━
`Naughty mode ON 😈`""",

    """❤️ LOVE STORY - Part 8
   😅
  /()\\  ✊😮
   /\\    _/\\.
━━━━━━━━━━━━━━━
`Arre kya hua? 😅`""",

    """❤️ LOVE STORY - Part 9
   😖
  /\\_💦_😋
   //    //
━━━━━━━━━━━━━━━
`Oops... 😖💦`""",

    """❤️ LOVE STORY - Part 10
  😎
 /\\_ _😫
  //   //
━━━━━━━━━━━━━━━
`Ladka cool 😎`""",

    """❤️ LOVE STORY - The End 😂
  😭      ☺️
  /|\\    /(👶)\\
  /!\\    / \\.
━━━━━━━━━━━━━━━
👶 Baby aa gaya!
**THE END** 😂👑
`Powered by NIK DADDY`"""
]
# 🔥 NIK V2 - 10 EMOJI STORIES PACK (5 Love + 5 Backchodi)
# Har story = 10-11 frames, Telegram pe .lovestory1 jaise command se chalegi
# Speed: 0.7 smooth, 0.4 fast


# Helper: use this function for all stories
# await msg.edit(f"```{frame}```")  # monospace me daalo taaki bigde nahi

# ════════════════════════════════════════════════════════
# ❤️ LOVE STORY 1 - COLLEGE WALA PYAR
# ════════════════════════════════════════════════════════
LOVE1_COLLEGE = [
    "❤️ COLLEGE LOVE - 1/11\n👦        📚\n/👕\\       |\n 👖       / \\\n`Pehla din college me...`",
    "❤️ COLLEGE LOVE - 2/11\n😐        😍\n/👕\\      /👗\\\n 👖        /|.\n`Samne se ladki aayi 😍`",
    "❤️ COLLEGE LOVE - 3/11\n😳        ☺️\n/👕\\      /👗\\\n 👖        /|.\n`Nazar mili, dono sharmaye`",
    "❤️ COLLEGE LOVE - 4/11\n😊  📝  😊\n/👕\\      /👗\\\n 👖        /|.\n`Notes share hue 📝`",
    "❤️ COLLEGE LOVE - 5/11\n😉        😆\n/👕\\      /👗\\\n 👖        /|.\n`Roz baatein badhne lagi`",
    "❤️ COLLEGE LOVE - 6/11\n😍  ❤️  😍\n/👕\\/👗\\\n 👖   /|.\n`Dosti pyar me badli ❤️`",
    "❤️ COLLEGE LOVE - 7/11\n😚        😳\n/👕\\      /👗\\\n 👖        /|.\n`Pehla propose 🌹`",
    "❤️ COLLEGE LOVE - 8/11\n😘   😊\n/👕\\/👗\\\n 👖   /|.\n`Haan bol diya! 😘`",
    "❤️ COLLEGE LOVE - 9/11\n🥰  👫  🥰\n/👕\\      /👗\\\n 👖        /|.\n`Canteen me date ☕`",
    "❤️ COLLEGE LOVE - 10/11\n😎        🥰\n/👕\\      /👗\\\n 👖        /|.\n`College khatam, pyar barkarar`",
    "❤️ COLLEGE LOVE - 11/11 - THE END\n👰   🤵\n/👗\\   /👕\\\n /|\\    / \\\n`Shaadi tak pahuch gaye! 🎉👑`\n**NIK DADDY SPECIAL**"
]

# ════════════════════════════════════════════════════════
# ❤️ LOVE STORY 2 - INSTA WALA PYAR
# ════════════════════════════════════════════════════════
LOVE2_INSTA = [
    "💘 INSTA LOVE - 1/10\n👦 📱\n/👕\\\n 👖\n`Ladka Insta scroll kar raha...`",
    "💘 INSTA LOVE - 2/10\n👦  ❤️  👩\n/👕\\      /👗\\\n 👖        /|.\n`Ek reel pe ladki dekhi 😍`",
    "💘 INSTA LOVE - 3/10\n😊  💬  😊\n/👕\\      /👗\\\n 👖        /|.\n`DM kiya: hii 😊`",
    "💘 INSTA LOVE - 4/10\n😒  ...  😐\n/👕\\      /👗\\\n 👖        /|.\n`Seen par reply nahi 😒`",
    "💘 INSTA LOVE - 5/10\n😅  📲  ☺️\n/👕\\      /👗\\\n 👖        /|.\n`Fir meme bheja 😅`",
    "💘 INSTA LOVE - 6/10\n😂        🤣\n/👕\\      /👗\\\n 👖        /|.\n`Has ke reply aaya! 😂`",
    "💘 INSTA LOVE - 7/10\n😍  💬  🥰\n/👕\\      /👗\\\n 👖        /|.\n`Raat bhar chat ❤️`",
    "💘 INSTA LOVE - 8/10\n📞  😍  📞\n/👕\\      /👗\\\n 👖        /|.\n`Pehli call, awaaz sunke fida`",
    "💘 INSTA LOVE - 9/10\n😘  🌹  😘\n/👕\\      /👗\\\n 👖        /|.\n`Milo? Haan! 😘`",
    "💘 INSTA LOVE - 10/10 - THE END\n👫 ❤️ 👫\n`Insta love = real love 🌟`\n**FOLLOW KARO NIK KO 👑**"
]

# ════════════════════════════════════════════════════════
# ❤️ LOVE STORY 3 - OFFICE CRUSH
# ════════════════════════════════════════════════════════
LOVE3_OFFICE = [
    "🏢 OFFICE CRUSH - 1/10\n👦 💼\n/👕\\\n 👖\n`Naya ladka office aaya`",
    "🏢 OFFICE CRUSH - 2/10\n😐        😎\n/👕\\      /👗\\\n 👖        /|.\n`Samne cabin me crush 😎`",
    "🏢 OFFICE CRUSH - 3/10\n☕  😊  ☕\n/👕\\      /👗\\\n 👖        /|.\n`Coffee machine pe mile`",
    "🏢 OFFICE CRUSH - 4/10\n😳        😉\n/👕\\      /👗\\\n 👖        /|.\n`Crush ne wink kiya 😉`",
    "🏢 OFFICE CRUSH - 5/10\n📊  😅  📊\n/👕\\      /👗\\\n 👖        /|.\n`Kaam me galti, crush hasi`",
    "🏢 OFFICE CRUSH - 6/10\n😍  💌  🥰\n/👕\\      /👗\\\n 👖        /|.\n`Chupke se chit bheja 💌`",
    "🏢 OFFICE CRUSH - 7/10\n😚        😊\n/👕\\      /👗\\\n 👖        /|.\n`Lunch saath kiya`",
    "🏢 OFFICE CRUSH - 8/10\n🌃  👫  🌃\n/👕\\      /👗\\\n 👖        /|.\n`Overtime me baatein 🌃`",
    "🏢 OFFICE CRUSH - 9/10\n💍  😍  💍\n/👕\\      /👗\\\n 👖        /|.\n`Propose office party me!`",
    "🏢 OFFICE CRUSH - 10/10 - THE END\n🎉 👫 🎉\n`Boss bhi naach gaya 😂`\n**NIK OFFICE KING 👑**"
]

# ════════════════════════════════════════════════════════
# ❤️ LOVE STORY 4 - LONG DISTANCE
# ════════════════════════════════════════════════════════
LOVE4_DISTANCE = [
    "✈️ DISTANCE LOVE - 1/10\n👦        ✈️        👧\n/👕\\                 /👗\\\n 👖                  /|.\n`Dono alag sheher me ✈️`",
    "✈️ DISTANCE LOVE - 2/10\n😔  📱  😔\n/👕\\      /👗\\\n 👖        /|.\n`Bas video call se milna`",
    "✈️ DISTANCE LOVE - 3/10\n😢        😢\n/👕\\      /👗\\\n 👖        /|.\n`Miss you... 😢`",
    "✈️ DISTANCE LOVE - 4/10\n😊  💬  😊\n/👕\\      /👗\\\n 👖        /|.\n`Raat bhar baatein 💬`",
    "✈️ DISTANCE LOVE - 5/10\n😡  📱  😡\n/👕\\      /👗\\\n 👖        /|.\n`Chhoti si ladai 😡`",
    "✈️ DISTANCE LOVE - 6/10\n😭        😭\n/👕\\      /👗\\\n 👖        /|.\n`Manana padega 😭`",
    "✈️ DISTANCE LOVE - 7/10\n🎁  😍  🎁\n/👕\\      /👗\\\n 👖        /|.\n`Surprise gift bheja 🎁`",
    "✈️ DISTANCE LOVE - 8/10\n😍        🥰\n/👕\\      /👗\\\n 👖        /|.\n`Fir se pyaar badha`",
    "✈️ DISTANCE LOVE - 9/10\n✈️  👦  ✈️\n/👕\\      /👗\\\n 👖        /|.\n`Ticket book, milne ja raha!`",
    "✈️ DISTANCE LOVE - 10/10 - THE END\n👫 ❤️ 👫\n`Mile aur gale lage 🫂`\n`Distance khatam, love jeeta! 🌟`"
]

# ════════════════════════════════════════════════════════
# ❤️ LOVE STORY 5 - SHAADI WALA DRAMA
# ════════════════════════════════════════════════════════
LOVE5_SHAADI = [
    "💒 SHAADI DRAMA - 1/11\n👦        👨‍👩‍👧\n/👕\\       /|\\\n 👖        / \\\n`Ladke ke ghar rishta aaya`",
    "💒 SHAADI DRAMA - 2/11\n😳        😳\n/👕\\      /👗\\\n 👖        /|.\n`Pehli mulaqat, dono sharmaye`",
    "💒 SHAADI DRAMA - 3/11\n😊  ☕  😊\n/👕\\      /👗\\\n 👖        /|.\n`Chai pe charcha ☕`",
    "💒 SHAADI DRAMA - 4/11\n😍        😍\n/👕\\      /👗\\\n 👖        /|.\n`Dono ko pasand aa gaye!`",
    "💒 SHAADI DRAMA - 5/11\n😎  📱  😎\n/👕\\      /👗\\\n 👖        /|.\n`Shaadi se pehle chatting 😉`",
    "💒 SHAADI DRAMA - 6/11\n😡  👨‍👩‍👧  😡\n/👕\\      /👗\\\n 👖        /|.\n`Dahej pe ladai 😡`",
    "💒 SHAADI DRAMA - 7/11\n😭        😭\n/👕\\      /👗\\\n 👖        /|.\n`Shaadi tootne wali thi`",
    "💒 SHAADI DRAMA - 8/11\n😈  👑  😈\n/👕\\      /👗\\\n 👖        /|.\n`Nik ne samjhaya 👑`",
    "💒 SHAADI DRAMA - 9/11\n🥰        🥰\n/👕\\      /👗\\\n 👖        /|.\n`Sab maan gaye!`",
    "💒 SHAADI DRAMA - 10/11\n💃  🥁  🕺\n/👗\\      /👕\\\n /|\\       / \\\n`Dhol baaje, naach gaye 💃`",
    "💒 SHAADI DRAMA - 11/11 - THE END\n👰  ❤️  🤵\n/👗\\      /👕\\\n /|\\       / \\\n`Shaadi ho gayi! 🎉`\n`NIK BLESSINGS 👑`"
]

# ════════════════════════════════════════════════════════
# 😂 BACKCHODI 1 - CHAI TAPRI
# ════════════════════════════════════════════════════════
BACK1_CHAI = [
    "☕ CHAI TAPRI - 1/10\n👦\n/👕\\\n 👖\n`Subah subah neend me 😴`",
    "☕ CHAI TAPRI - 2/10\n👦  ☕\n/👕\\\n 👖\n`Tapri pe pahucha`",
    "☕ CHAI TAPRI - 3/10\n👦  ☕  👨‍🍳\n/👕\\      /👕\\\n 👖        👖\n`Bhaiya ek cutting!`",
    "☕ CHAI TAPRI - 4/10\n😋  ☕  😋\n/👕\\      /👕\\\n 👖        👖\n`Garam chai ki chuski 😋`",
    "☕ CHAI TAPRI - 5/10\n👦💬👦💬👦\n/👕\\ /👕\\ /👕\\\n`Gyaan pelna shuru 😂`",
    "☕ CHAI TAPRI - 6/10\n😡  💬  😡\n/👕\\      /👕\\\n 👖        👖\n`Politics pe ladai 😡`",
    "☕ CHAI TAPRI - 7/10\n😂  ☕  😂\n/👕\\      /👕\\\n 👖        👖\n`Fir has ke sab bhul gaye`",
    "☕ CHAI TAPRI - 8/10\n💸  😳  💸\n/👕\\      /👕\\\n 👖        👖\n`Bill kaun dega? 💸😳`",
    "☕ CHAI TAPRI - 9/10\n🏃  💨  😐\n/👕\\      /👕\\\n 👖        👖\n`Nik bhaag gaya bina bill diye 🏃💨😂`",
    "☕ CHAI TAPRI - 10/10 - THE END\n😭  ☕  😭\n`Dukaan wala roya 😭`\n`NIK TAPRI KING 👑`"
]

# ════════════════════════════════════════════════════════
# 😂 BACKCHODI 2 - EXAM CHORI
# ════════════════════════════════════════════════════════
BACK2_EXAM = [
    "📚 EXAM CHORI - 1/10\n👦  📚\n/👕\\\n 👖\n`Kal exam, kuch nahi padha 😰`",
    "📚 EXAM CHORI - 2/10\n😥  📖  😥\n/👕\\      /👕\\\n 👖        👖\n`Raat bhar jag ke padha`",
    "📚 EXAM CHORI - 3/10\n😴  📖  😴\n/👕\\\n 👖\n`Subah tak so gaya 😴`",
    "📚 EXAM CHORI - 4/10\n👦  🏫  👦\n/👕\\      /👕\\\n 👖        👖\n`Exam hall me entry`",
    "📚 EXAM CHORI - 5/10\n👀  📝  👀\n/👕\\      /👕\\\n 👖        👖\n`Aas paas dekha 👀`",
    "📚 EXAM CHORI - 6/10\n😏  📄  😏\n/👕\\      /👕\\\n 👖        👖\n`Chit nikali 😏`",
    "📚 EXAM CHORI - 7/10\n👨‍🏫  😳  👦\n/👕\\      /👕\\\n 👖        👖\n`Teacher ne dekh liya! 😳`",
    "📚 EXAM CHORI - 8/10\n😭  🙏  👨‍🏫\n/👕\\      /👕\\\n 👖        👖\n`Maafi maangi 🙏`",
    "📚 EXAM CHORI - 9/10\n😈  📝  😈\n/👕\\      /👕\\\n 👖        👖\n`Fir bhi pass 😈`",
    "📚 EXAM CHORI - 10/10 - THE END\n🎉  😎  🎉\n`Nik ke jugad se pass! 👑`\n`BACKBENCHER KING`"
]

# ════════════════════════════════════════════════════════
# 😂 BACKCHODI 3 - GULLY CRICKET
# ════════════════════════════════════════════════════════
BACK3_CRICKET = [
    "🏏 GULLY CRICKET - 1/10\n👦  🏏\n/👕\\\n 👖\n`Gully me match ka plan`",
    "🏏 GULLY CRICKET - 2/10\n👦👦👦\n/👕\\/👕\\/👕\\\n`Team bani 👦👦👦`",
    "🏏 GULLY CRICKET - 3/10\n🏏  😎  🥎\n/👕\\      /👕\\\n 👖        👖\n`Nik batting pe 😎`",
    "🏏 GULLY CRICKET - 4/10\n💥  🏏  💥\n/👕\\      /👕\\\n 👖        👖\n`Chhakka! 💥`",
    "🏏 GULLY CRICKET - 5/10\n😡  🏠  😡\n/👕\\      /👕\\\n 👖        👖\n`Ball ne khidki todi! 😡`",
    "🏏 GULLY CRICKET - 6/10\n👩‍🦳  😠  👦\n/👗\\      /👕\\\n /|\\       👖\n`Aunty aayi daante 😠`",
    "🏏 GULLY CRICKET - 7/10\n😭  🙏  👩‍🦳\n/👕\\      /👗\\\n 👖        /|.\n`Sorry aunty 🙏😭`",
    "🏏 GULLY CRICKET - 8/10\n😈  🏏  😈\n/👕\\      /👕\\\n 👖        👖\n`Fir se khelna shuru 😈`",
    "🏏 GULLY CRICKET - 9/10\n🏆  😎  🏆\n/👕\\      /👕\\\n 👖        👖\n`Nik ki team jeeti 🏆`",
    "🏏 GULLY CRICKET - 10/10 - THE END\n🍻  🎉  🍻\n`Party to banti hai! 🍻`\n`NIK CAPTAIN 👑`"
]

# ════════════════════════════════════════════════════════
# 😂 BACKCHODI 4 - UDHAAR PAISA
# ════════════════════════════════════════════════════════
BACK4_UDHAAR = [
    "💸 UDHAAR STORY - 1/10\n👦  💸\n/👕\\\n 👖\n`Paise khatam 💸😰`",
    "💸 UDHAAR STORY - 2/10\n😊  📱  👦\n/👕\\      /👕\\\n 👖        👖\n`Dost ko call: bhai 500 de de`",
    "💸 UDHAAR STORY - 3/10\n😎  💸  😎\n/👕\\      /👕\\\n 👖        👖\n`Dost ne de diye 😎`",
    "💸 UDHAAR STORY - 4/10\n😍  🍔  😍\n/👕\\      /👕\\\n 👖        👖\n`Burger party 🍔`",
    "💸 UDHAAR STORY - 5/10\n📅  ...  📅\n`1 mahina baad 📅`",
    "💸 UDHAAR STORY - 6/10\n👦  📱  😒\n/👕\\      /👕\\\n 👖        👖\n`Dost: paise kab dega? 😒`",
    "💸 UDHAAR STORY - 7/10\n😅  🙈  😅\n/👕\\\n 👖\n`Seen karke ignore 😅🙈`",
    "💸 UDHAAR STORY - 8/10\n😡  📱  😡\n/👕\\      /👕\\\n 👖        👖\n`Dost gussa 😡`",
    "💸 UDHAAR STORY - 9/10\n🏃  💨  👦\n/👕\\\n 👖\n`Nik block karke bhaag gaya 🏃💨😂`",
    "💸 UDHAAR STORY - 10/10 - THE END\n😭  💸  😭\n`Dost abhi tak rota hai 😭`\n`NIK UDHAAR KING 👑`"
]

# ════════════════════════════════════════════════════════
# 😜 BACKCHODI 5 - NAUGHTY FLIRT (Clean 18+ hint, no explicit)
# ════════════════════════════════════════════════════════
# Note: Ye sirf flirty comedy hai, explicit nahi - Telegram safe
BACK5_FLIRT = [
    "😜 FLIRT STORY - 1/10\n😎        😍\n/👕\\      /👗\\\n 👖        /|.\n`Ladka ladki ko dekha 😎😍`",
    "😜 FLIRT STORY - 2/10\n😉        ☺️\n/👕\\      /👗\\\n 👖        /|.\n`Ladke ne line maari 😉`",
    "😜 FLIRT STORY - 3/10\n😏        😳\n/👕\\      /👗\\\n 👖        /|.\n`Ladki sharmayi 😳`",
    "😜 FLIRT STORY - 4/10\n😍  ☕  😍\n/👕\\      /👗\\\n 👖        /|.\n`Coffee date fix ☕`",
    "😜 FLIRT STORY - 5/10\n😘        😘\n/👕\\      /👗\\\n 👖        /|.\n`Baatein gehraayi 😘`",
    "😜 FLIRT STORY - 6/10\n🥰  🌃  🥰\n/👕\\      /👗\\\n 👖        /|.\n`Raat ko long drive 🌃`",
    "😜 FLIRT STORY - 7/10\n🙈        🙈\n/👕\\      /👗\\\n 👖        /|.\n`Thoda close aaye 🙈`",
    "😜 FLIRT STORY - 8/10\n😳        😳\n/👕\\      /👗\\\n 👖        /|.\n`Dil tez dhadka 💓`",
    "😜 FLIRT STORY - 9/10\n😈        😈\n/👕\\      /👗\\\n 👖        /|.\n`Nik bola: control 😈😂`",
    "😜 FLIRT STORY - 10/10 - THE END\n😂  ❤️  😂\n/👕\\      /👗\\\n 👖        /|.\n`Pyar me izzat hai boss ❤️`\n`NIK FLIRT GURU 👑`"
]


# ══════════════════════════════════════════════════════════════
#                     ᴄᴏᴍᴍᴀɴᴅ ʀᴇɢɪsᴛʀʏ
# ══════════════════════════════════════════════════════════════
commands: Dict[str, Dict[str, Any]] = {}
aliases: Dict[str, str] = {}


def register_cmd(*names, needs_reply=False, group_only=False, owner_only=False):
    def decorator(func):
        main = None
        for raw in names:
            key = (raw or "").lower().strip()
            if not key:
                continue
            if key in commands:
                raise ValueError(f"Duplicate command: {key}")
            commands[key] = {"func": func, "needs_reply": bool(needs_reply),
                             "group_only": bool(group_only),
                             "owner_only": bool(owner_only)}
            if main is None:
                main = key
            else:
                aliases[key] = main
        return func
    return decorator


OWNER_ONLY_EXTRA = {"copy", "normal", "cp", "nrml", "addadmin", "deladmin",
                    "admins", "sudo", "delsudo", "list", "gban", "ungban",
                    "gbanlist", "gmute", "ungmute", "gmutelist", "gcast",
                    "ucast", "bc", "autobc", "autofw", "add-bcdb", "del-bcdb",
                    "join", "leave", "purgeall", "fastgc", "spray", "dspray",
                    "banall", "invitebots", "promotebots", "addbots",
                    "setgpfp", "autogpfp", "stopgpfp", "addbot", "c", "p",
                    "code", "resend", "rcode", "cancelbot", "cc", "delbot",
                    "removebot", "setgame", "rob", "kill", "auto", "roboff",
                    "killoff", "autooff", "stoprob", "resetdone", "solve",
                    "user", "setbot", "baka", "bakastatus", "automation"}


# ══════════════════════════════════════════════════════════════
#                           ᴍᴇɴᴜ
# ══════════════════════════════════════════════════════════════
_MENU = [
    (f"{E['bolt']} {sb('core')}", [
        ("menu", "ᴘᴏᴏʀᴀ ᴄᴏᴍᴍᴀɴᴅ ᴍᴀᴘ"),
        ("alive", "ʙᴏᴛ sᴛᴀᴛᴜs + ᴜᴘᴛɪᴍᴇ"),
        ("ping", "ʀᴇsᴘᴏɴsᴇ sᴘᴇᴇᴅ"),
        ("status", "ꜰᴜʟʟ ʀᴜɴᴛɪᴍᴇ ʀᴇᴘᴏʀᴛ"),
        ("uptime", "ᴋɪᴛɴᴀ ᴄʜᴀʟ ʀʜᴀ ʜᴀɪ"),
        ("id", "ɪᴅ ɢʀᴀʙʙᴇʀ · ᴅᴍ ᴀᴜᴛᴏ"),
        ("info", "ᴜsᴇʀ ᴘʀᴏꜰɪʟᴇ · ᴅᴍ ᴀᴜᴛᴏ"),
        ("help", "ǫᴜɪᴄᴋ ɢᴜɪᴅᴇ"),
        ("speed", "ᴀɴɪᴍᴀᴛɪᴏɴ sᴘᴇᴇᴅ"),
    ]),
    (f"{E['dot']} {sb('messaging')}", [
        ("hy", "sᴛʏʟɪsʜ ɢʀᴇᴇᴛɪɴɢ"),
        ("del", "ʀᴇᴘʟɪᴇᴅ ᴍsɢ ᴜᴅᴀᴏ"),
        ("forward", "ᴍsɢ ᴀᴀɢᴇ ʙʜᴇᴊᴏ"),
        ("save", "ᴄʜᴀɴɴᴇʟ ᴍᴇ sᴇᴠᴇ"),
        ("savelist", "sᴀᴠᴇᴅ ʟɪsᴛ"),
        ("fwd", "sᴀᴠᴇᴅ ᴡᴀᴘᴀs"),
        ("delsave", "sᴀᴠᴇᴅ ᴅᴇʟᴇᴛᴇ"),
        ("setchannel", "sᴀᴠᴇ ᴄʜᴀɴɴᴇʟ sᴇᴛ"),
        ("purge", "ʀᴇᴘʟʏ/<n>/1-999999"),
        ("purgeme", "ᴀᴘɴᴇ ᴍsɢ · `<n>`/`all`"),
        ("delmine", "ᴀᴘɴᴇ sᴀʙ ᴍsɢ"),
        ("filter", "ᴡᴏʀᴅ ᴀᴜᴛᴏ-ʀᴇᴘʟʏ"),
        ("filters", "ꜰɪʟᴛᴇʀ ʟɪsᴛ"),
        ("unfilter", "ꜰɪʟᴛᴇʀ ʜᴀᴛᴀᴏ"),
    ]),
    (f"{E['diamond']} {sb('auto')}", [
        ("autoread", "ɢʀᴏᴜᴘ/ᴘʀɪᴠᴀᴛᴇ/ᴀʟʟ ᴏɴ-ᴏꜰꜰ"),
        ("areply", "ᴘᴍ ᴀᴜᴛᴏ-ʀᴇᴘʟʏ"),
        ("stopareply", "ᴀᴜᴛᴏ-ʀᴇᴘʟʏ ʙᴀɴᴅ"),
        ("arreply", "ᴜsᴇʀ ᴀᴜᴛᴏ-ʀᴇᴘʟʏ"),
        ("sarreply", "ᴜsᴇʀ ʀᴇᴘʟʏ ʙᴀɴᴅ"),
        ("afk", "ᴀꜰᴋ ᴍᴏᴅᴇ"),
        ("unafk", "ᴀꜰᴋ ᴏꜰꜰ"),
        ("ghost", "ᴀᴘɴᴇ ᴍsɢ ᴀᴜᴛᴏ-ᴅᴇʟ"),
        ("echo", "ʀᴇᴘᴇᴀᴛ ᴜsᴇʀ"),
        ("unecho", "ʀᴇᴘᴇᴀᴛ ʙᴀɴᴅ"),
        ("ar", "ʀᴇᴀᴄᴛ + ʟᴏᴄᴋ · ʀᴇᴘʟʏ ᴘᴇ"),
        ("ar off", "ɪs ᴄʜᴀᴛ ᴋᴇ ʟᴏᴄᴋs ʙᴀɴᴅ"),
        ("sar", "ᴍᴇʀᴇ ᴍsɢs ᴘᴇ ʀᴇᴀᴄᴛ · ᴏꜰꜰ"),
        ("selfar", "ᴋʜᴜᴅ ᴘᴇ ʀᴇᴀᴄᴛ ᴏɴ"),
        ("selfsar", "ᴋʜᴜᴅ ᴘᴇ ʀᴇᴀᴄᴛ ᴏꜰꜰ"),
        ("makear", "ᴄᴏᴍʙᴏ ʙᴀɴᴀᴏ · .r sᴇ ʙʜᴀʀᴏ"),
        ("r", "ᴄᴏᴍʙᴏ ᴍᴇ ᴇᴍᴏᴊɪ ᴀᴅᴅ · 𝟹 ᴛᴀᴋ"),
        ("rem", "sᴀᴠᴇᴅ ᴄᴏᴍʙᴏ ʜᴀᴛᴀᴏ"),
        ("art", "ᴀᴜᴛᴏ-ʀᴇᴀᴄᴛɪᴏɴ"),
        ("sart", "ʀᴇᴀᴄᴛɪᴏɴ ʙᴀɴᴅ"),
        ("prefix", "ᴘʀᴇꜰɪx ᴏɴ/ᴏꜰꜰ · ᴅᴏᴛ ᴢᴀʀᴏᴏʀɪ?"),
        ("lockmsg", "ʟᴏᴄᴋ ᴍsɢ · ɪs ᴄʜᴀᴛ"),
        ("glockmsg", "ʟᴏᴄᴋ ᴍsɢ · ɢʟᴏʙᴀʟ"),
        ("check", "ᴄᴏᴍᴍᴀɴᴅ ɪɴꜰᴏ + sᴛᴀᴛᴇ"),
        ("article", "ʀɪᴄʜ ᴀʀᴛɪᴄʟᴇ · ᴅᴇᴍᴏ"),
        ("killall", "sᴀᴀʀᴇ ʟɪᴠᴇ ᴛᴀsᴋs ʙᴀɴᴅ"),
    ]),
    (f"{E['chain']} {sb('blacklist')}", [
        ("addbl", "ʙʟᴀᴄᴋʟɪsᴛ +"),
        ("delbl", "ʙʟᴀᴄᴋʟɪsᴛ −"),
        ("listbl", "ʙʟᴀᴄᴋʟɪsᴛ ʟɪsᴛ"),
        ("add-bcdb", "ʙʀᴏᴀᴅᴄᴀsᴛ ᴅʙ +"),
        ("del-bcdb", "ʙʀᴏᴀᴅᴄᴀsᴛ ᴅʙ −"),
        ("list-bcdb", "ʙʀᴏᴀᴅᴄᴀsᴛ ᴅʙ"),
        ("join", "ʟɪɴᴋ sᴇ ᴊᴏɪɴ"),
        ("leave", "ᴄʜᴀᴛ ᴄʜʜᴏᴅᴏ"),
    ]),
    (f"{E['sat']} {sb('broadcast')}", [
        ("gcast", "sᴀʙ ɢʀᴏᴜᴘs ᴍᴇ"),
        ("ucast", "sᴀʙ ᴜsᴇʀs ᴋᴏ"),
        ("bc", "ɢʀᴏᴜᴘ/ᴀʟʟ/ᴘʀɪᴠᴀᴛᴇ/ᴅʙ"),
        ("autobc", "ᴀᴅᴅ/ᴏɴ/ᴏꜰꜰ/ɢᴇᴛ/ᴅᴇʟ/ᴅᴇʟᴀʏ"),
        ("autofw", "ᴀᴅᴅ/ᴏɴ/ᴏꜰꜰ/ɢᴇᴛ/ᴅᴇʟ/ᴅᴇʟᴀʏ"),
    ]),
    (f"{E['shield']} {sb('group mod')}", [
        ("kick", "ᴜsᴇʀ ɴɪᴋᴀᴀʟᴏ"),
        ("delkick", "ᴋɪᴄᴋ + ᴍsɢ ᴜᴅᴀᴏ"),
        ("ban", "ʙᴀɴ"),
        ("delban", "ʙᴀɴ + ᴍsɢ ᴜᴅᴀᴏ"),
        ("unban", "ᴜɴʙᴀɴ"),
        ("mute", "ᴍᴜᴛᴇ · ᴍ / ᴍᴜᴛᴇ"),
        ("delmute", "ᴍᴜᴛᴇ + ᴍsɢ ᴜᴅᴀᴏ"),
        ("unmute", "ᴜɴᴍᴜᴛᴇ · sᴍ"),
        ("tmute", "ᴛɪᴍᴇᴅ ᴍᴜᴛᴇ `10m/2h`"),
        ("getmute", "ᴍᴜᴛᴇᴅ ʟɪsᴛ"),
        ("staff", "ᴀᴅᴍɪɴ ʟɪsᴛ"),
        ("promote", "ᴀᴅᴍɪɴ ʙᴀɴᴀᴏ"),
        ("fullpromote", "ꜰᴜʟʟ ʀɪɢʜᴛs"),
        ("demote", "ᴀᴅᴍɪɴ ʜᴀᴛᴀᴏ"),
        ("title", "ᴄᴜsᴛᴏᴍ ᴛᴀɢ/ᴛɪᴛʟᴇ"),
        ("pin", "ᴘɪɴ"),
        ("unpin", "ᴜɴᴘɪɴ / ᴀʟʟ"),
        ("group", "ᴛɪᴛʟᴇ / ᴅᴇsᴄ"),
        ("tagall", "sᴀʙᴋᴏ ᴛᴀɢ"),
        ("banall", "sᴀʙᴋᴏ ʙᴀɴ"),
        ("lock", "ʟᴏᴄᴋ <ᴛʏᴘᴇ>"),
        ("unlock", "ᴜɴʟᴏᴄᴋ <ᴛʏᴘᴇ>"),
        ("locks", "ᴀᴄᴛɪᴠᴇ ʟᴏᴄᴋs"),
        ("slock", "sᴜᴘᴇʀ ʟᴏᴄᴋ · sᴀʙ ᴍᴜᴛᴇ"),
        ("requests", "ᴘᴇɴᴅɪɴɢ ᴊᴏɪɴ ʀᴇǫs ʟɪsᴛ"),
        ("approve all", "sᴀʙ ʀᴇǫ ʀᴇǫ ᴀʟʟᴏᴡ"),
        ("deny all", "sᴀʙ ʀᴇǫ ʀᴇᴊᴇᴄᴛ"),
    ]),
    (f"{E['globe']} {sb('global')}", [
        ("gban", "sᴀʙ ᴄʜᴀᴛs ᴍᴇ ʙᴀɴ"),
        ("ungban", "ɢʙᴀɴ ʜᴀᴛᴀᴏ"),
        ("gbanlist", "ɢʙᴀɴ ʟɪsᴛ"),
        ("gmute", "sᴀʙ ᴄʜᴀᴛs ᴍᴇ ᴍᴜᴛᴇ"),
        ("ungmute", "ɢᴍᴜᴛᴇ ʜᴀᴛᴀᴏ"),
        ("gmutelist", "ɢᴍᴜᴛᴇ ʟɪsᴛ"),
    ]),
    (f"{E['eye']} {sb('protection')}", [
        ("antidel", "ᴀɴᴛɪ-ᴅᴇʟᴇᴛᴇ ᴏɴ/ᴏꜰꜰ"),
        ("watchspam", "sᴘᴀᴍ ɢᴜᴀʀᴅ `3 5`"),
        ("unwatchspam", "sᴘᴀᴍ ɢᴜᴀʀᴅ ᴏꜰꜰ"),
        ("setgpfp", "ɢʀᴏᴜᴘ ᴘʜᴏᴛᴏ sᴇᴛ"),
        ("autogpfp", "ᴘʜᴏᴛᴏ ʀᴏᴛᴀᴛᴇ `10`"),
        ("stopgpfp", "ʀᴏᴛᴀᴛɪᴏɴ ʙᴀɴᴅ"),
        ("rlock", "ʀᴇᴘʟʏ-ᴛʀɪɢɢᴇʀ ʟᴏᴄᴋ"),
        ("srlock", "ʀᴇᴘʟʏ ʟᴏᴄᴋ ʜᴀᴛᴀᴏ"),
    ]),
    (f"{E['wand']} {sb('media')}", [
        ("yt", "ʏᴏᴜᴛᴜʙᴇ ᴅᴏᴡɴʟᴏᴀᴅ"),
        ("ig", "ɪɴsᴛᴀɢʀᴀᴍ ᴅᴏᴡɴʟᴏᴀᴅ"),
        ("pt", "ᴘɪɴᴛᴇʀᴇsᴛ ᴅᴏᴡɴʟᴏᴀᴅ"),
        ("fb", "ꜰᴀᴄᴇʙᴏᴏᴋ ᴅᴏᴡɴʟᴏᴀᴅ"),
        ("music", "sᴏɴɢ ᴡᴏʀᴅs/ʟɪɴᴋ → ᴍᴘ3"),
        ("song", "ᴍᴜsɪᴄ ᴀʟɪᴀs · ᴀᴜᴛᴏ sᴇᴀʀᴄʜ"),
    ]),
    (f"{E['dice']} {sb('fun')}", [
        ("tictactoe", "ɢᴀᴍᴇ sʜᴜʀᴜ"),
        ("ttt", "ᴍᴏᴠᴇ `1-9`"),
        ("rps", "ʀᴏᴄᴋ-ᴘᴀᴘᴇʀ-sᴄɪssᴏʀ"),
        ("roll", "ᴅɪᴄᴇ ʀᴏʟʟ"),
        ("flip", "ᴄᴏɪɴ ᴛᴏss"),
        ("fact", "ʀᴀɴᴅᴏᴍ ꜰᴀᴄᴛ"),
        ("bomb", "ʙᴏᴍʙ ᴀɴɪᴍᴀᴛɪᴏɴ"),
        ("love", "ʜᴇᴀʀᴛ ᴀɴɪᴍᴀᴛɪᴏɴ"),
    ]),
    (f"{E['gene']} {sb('ai & sudo')}", [
        ("ai", "ꜰʀᴇᴇ ᴀɪ · ᴋᴏɪ ᴀᴘɪ ᴋᴇʏ ɴᴀʜɪ"),
        ("sudo", "sᴜᴅᴏ ʙᴀɴᴀᴏ · ᴀᴅᴅᴀᴅᴍɪɴ"),
        ("delsudo", "sᴜᴅᴏ ʜᴀᴛᴀᴏ · ᴅᴇʟᴀᴅᴍɪɴ"),
        ("list", "`.list sudo` / `.list bots`"),
        ("admins", "sᴜᴅᴏ ʟɪsᴛ (ᴀʟɪᴀs)"),
    ]),
    (f"{E['node']} {sb('bot manager')}", [
        ("addbot", "ɴᴇᴡ ᴜsᴇʀʙᴏᴛ ʟᴏɢɪɴ `+91…`"),
        ("c", "ʟᴏɢɪɴ ᴄᴏᴅᴇ `12345`"),
        ("p", "2ꜰᴀ ᴘᴀssᴡᴏʀᴅ"),
        ("user", "ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙᴏᴛs ʟɪsᴛ"),
        ("resend", "ᴄᴏᴅᴇ ᴅᴏʙᴀʀᴀ ʙʜᴇᴊᴏ"),
        ("cancelbot", "ᴀᴅʜᴀ ʟᴏɢɪɴ ᴄʜʜᴏᴅᴏ"),
        ("delbot", "ʙᴏᴛ ʀᴇᴍᴏᴠᴇ `+91…/all`"),
        ("addbots", "@ʙᴏᴛ1 @ʙᴏᴛ2 sᴀᴠᴇ"),
        ("listbots", "sᴀᴠᴇᴅ ʙᴏᴛs"),
        ("rembots", "sᴀᴠᴇᴅ ʙᴏᴛ ʜᴀᴛᴀᴏ"),
        ("invitebots", "ʙᴏᴛs ɪɴᴠɪᴛᴇ"),
        ("promotebots", "ʙᴏᴛs ᴘʀᴏᴍᴏᴛᴇ"),
    ]),
    (f"{E['sword']} {sb('raid')}", [
        ("reply", "ʀᴇᴘʟʏ ʀᴀɪᴅ ᴏɴ"),
        ("sreply", "ʀᴇᴘʟʏ ʀᴀɪᴅ ᴏꜰꜰ"),
        ("rr", "ʀʀ ʀᴀɪᴅ (🤣)"),
        ("srr", "ʀʀ ᴏꜰꜰ"),
        ("flag", "ꜰʟᴀɢ ʀᴀɪᴅ"),
        ("sflag", "ꜰʟᴀɢ ᴏꜰꜰ"),
        ("hrr", "ʜᴇᴀʀᴛ ʀᴀɪᴅ"),
        ("shrr", "ʜᴇᴀʀᴛ ᴏꜰꜰ"),
        ("replygod", "ʙᴜʀsᴛ ʀᴀɪᴅ"),
        ("sgod", "ʙᴜʀsᴛ ᴏꜰꜰ"),
        ("nikreply", "<ᴄᴏᴜɴᴛ> <ᴛᴇxᴛ>"),
        ("nik", "sᴀʙ ʀᴀɪᴅ ʙᴀɴᴅ"),
        ("raidstopall", "ᴇᴠᴇʀʏᴛʜɪɴɢ sᴛᴏᴘ"),
        ("stopall", "ᴇᴠᴇʀʏᴛʜɪɴɢ sᴛᴏᴘ"),
        ("gali", "ɢᴀʟɪ sᴘᴀᴍ <ɴ>"),
    ]),
    (f"{E['comet']} {sb('spam')}", [
        ("spray", "ʟᴏᴏᴘ ᴍᴇssᴀɢᴇ"),
        ("dspray", "ʟᴏᴏᴘ ʙᴀɴᴅ"),
        ("sspam", "ʟᴏᴏᴘ ʙᴀɴᴅ (ᴀʟɪᴀs)"),
        ("spam", "<ɴ> <ᴛᴇxᴛ>"),
        ("mspam", "<ɴ> ᴍᴇᴅɪᴀ"),
        ("delayspam", "<ᴅᴇʟᴀʏ> <ɴ> <ᴛᴇxᴛ>"),
        ("d", "<sᴇᴄ> <ᴛᴇxᴛ>"),
        ("purgeall", "ᴘᴏᴏʀɪ ᴄʜᴀᴛ ᴜᴅᴀᴏ (sᴀʙ)"),
        ("stop", "ᴛᴀɢᴀʟʟ ʙᴀɴᴅ"),
    ]),
    (f"{E['gear']} {sb('gc tools')}", [
        ("fastgc", "sᴇᴛ <ᴛɪᴛʟᴇ {emoji}> / sᴛᴏᴘ"),
        ("copy", "ᴘʀᴏꜰɪʟᴇ ᴄʟᴏɴᴇ · ᴄᴘ"),
        ("normal", "ᴘʀᴏꜰɪʟᴇ ʀᴇsᴛᴏʀᴇ · ɴʀᴍʟ"),
    ]),
    (f"{E['tool']} {sb('tools')}", [
        ("tts", "ᴛᴇxᴛ → ᴀᴜᴅɪᴏ"),
        ("qrcode", "ᴛᴇxᴛ → ǫʀ"),
        ("fancy", "ꜰᴀɴᴄʏ ꜰᴏɴᴛs"),
        ("style", "sᴛʏʟᴇ ᴄᴏɴᴠᴇʀᴛ"),
        ("emoji", "ᴇᴍᴏᴊɪ ᴅᴇᴄᴏʀᴇ"),
        ("calc", "ᴄᴀʟᴄᴜʟᴀᴛᴏʀ"),
        ("weather", "ᴍᴏsᴀᴍ"),
        ("ip", "ɪᴘ ʟᴏᴏᴋᴜᴘ"),
        ("short", "ᴜʀʟ sʜᴏʀᴛᴇɴ"),
    ]),
    (f"{E['key']} {sb('notes')}", [
        ("notesadd", "ɴᴏᴛᴇ sᴀᴠᴇ"),
        ("noteslist", "ɴᴏᴛᴇ ᴅᴇᴋʜᴏ"),
        ("notesdelete", "ɴᴏᴛᴇ ᴜᴅᴀᴏ"),
        ("banner", "ᴍᴇɴᴜ ʙᴀɴɴᴇʀ sᴇᴛ"),
        ("rembanner", "ʙᴀɴɴᴇʀ ʜᴀᴛᴀᴏ"),
    ]),
    (f"{E['film']} {sb('stories')}", [
        ("love1", "ᴄᴏʟʟᴇɢᴇ ʟᴏᴠᴇ"),
        ("love2", "ɪɴsᴛᴀ ʟᴏᴠᴇ"),
        ("love3", "ᴏꜰꜰɪᴄᴇ ʟᴏᴠᴇ"),
        ("love4", "ᴅɪsᴛᴀɴᴄᴇ ʟᴏᴠᴇ"),
        ("love5", "sʜᴀᴀᴅɪ ʟᴏᴠᴇ"),
        ("lovestory", "ᴄʟᴀssɪᴄ sᴛᴏʀʏ"),
        ("fun1", "ᴄʜᴀɪ sᴛᴏʀʏ"),
        ("fun2", "ᴇxᴀᴍ sᴛᴏʀʏ"),
        ("fun3", "ᴄʀɪᴄᴋᴇᴛ sᴛᴏʀʏ"),
        ("fun4", "ᴜᴅʜᴀᴀʀ sᴛᴏʀʏ"),
        ("fun5", "ꜰʟɪʀᴛ sᴛᴏʀʏ"),
        ("fun6", "ᴛʜᴜɢ ʟɪꜰᴇ"),
        ("fun7", "ᴍᴜᴍᴍʏ ᴅᴀᴀɴᴛ"),
        ("fun8", "sᴀsᴛᴀ ɴᴀsʜᴀ"),
    ]),
    (f"{E['moon']} {sb('baka automation')}", [
        ("setbot", "ᴀᴜᴛᴏ ʙᴏᴛ sᴇᴛ · sᴇᴛᴜᴘ"),
        ("baka", "sᴛᴀᴛᴜs + ʀᴜʟᴇs"),
        ("rob", "ʀᴏʙ ᴀʟʟ · `.rob 500` ꜰɪxᴇᴅ"),
        ("kill", "ᴋɪʟʟ ᴀʟʟ · `.kill 500` ꜰɪxᴇᴅ"),
        ("auto", "ʙᴀʟ ᴄʜᴇᴄᴋ → ʀᴏʙ/ᴋɪʟʟ"),
        ("autooff", "ᴀᴜᴛᴏ ʙᴀɴᴅ"),
        ("roboff", "ʀᴏʙ ʙᴀɴᴅ"),
        ("killoff", "ᴋɪʟʟ ʙᴀɴᴅ"),
        ("stoprob", "sᴀʙ ᴡᴏʀᴋᴇʀ ʙᴀɴᴅ"),
        ("resetdone", "ᴅᴏɴᴇ ʟɪsᴛ ᴄʟᴇᴀʀ"),
        ("solve", "ᴠᴇʀɪꜰʏ ᴄᴏᴅᴇ `1234`"),
    ]),
]


def menu_head(w=34, page=0):
    """har menu ka masthead — page ke hisaab se alag emoji jodi"""
    return [top(w, HEROES[page % len(HEROES)]), sub(""),
            kv("owner", OWNER_TAG, E["crown"]),
            kv("build", VERSION, E["spark"]),
            kv("mode", "global", E["globe"]),
            sub("")]


def build_menu_pages(w=34, per_page=48):
    """pages auto-split — har section ka apna emoji, rows alternate"""
    sections = []
    for title, items in _MENU:
        nm = _sect_name(title)
        st = CAT_STYLE.get(nm, _STYLE_DEFAULT)
        rows = [hdr(f"{st['icon']}{SP} ▰ {sb(nm)}", w, count=len(items))]
        for i, (c, d) in enumerate(items):
            # har row pe emoji, par dono alag — bhara-bhara lagta hai
            rows.append(row(c, d, bullet=(st["icon"] if i % 2 == 0 else st["alt"]), cw=13))
        rows.append(end(w))
        sections.append("\n".join(rows))

    bodies, cur = [], ""
    for sec in sections:
        if len(cur) + len(sec) + 1 > 2350 and cur.strip():
            bodies.append(cur)
            cur = ""
        cur += ("\n" if cur else "") + sec
    if cur:
        bodies.append(cur)

    total = len(bodies)
    out = []
    for i, body in enumerate(bodies):
        out.append("\n".join(menu_head(w, i) + [body,
            sub(f"{E['dot']}{SP} {sc('page')} {mono(str(i + 1))}"
                f" {E['arrow']} {mono(str(total))}"),
            sub(FOOT),
            close()]))
    return out


# ══════════════════════════════════════════════════════════════
#        ᴍᴇɴᴜ sʏsᴛᴇᴍ — m1..m3 = pages · m4+ = category · fullmenu
# ══════════════════════════════════════════════════════════════
_SB_BACK = {sb(c): c for c in string.ascii_letters}


def _sect_name(title):
    """'🛡️ 𝗴𝗿𝗼𝘂𝗽 𝗺𝗼𝗱' → 'group mod'"""
    return title.split(" ", 1)[-1].translate(str.maketrans(_SB_BACK)).strip()


# m4 se aage categories ka order — baki sab iske baad (m4 = admins/group mod)
CAT_ORDER = ["group mod", "fun", "tools", "global", "protection",
             "blacklist", "broadcast", "messaging", "auto", "media",
             "ai & sudo", "bot manager", "raid", "spam", "gc tools",
             "notes", "stories", "core", "baka automation"]

def _cat_sort_key(idx):
    nm = _sect_name(_MENU[idx][0])
    return (CAT_ORDER.index(nm) if nm in CAT_ORDER else 99, idx)


CATS = []                                  # [(name, _MENU index)]
for _i in sorted(range(len(_MENU)), key=_cat_sort_key):
    CATS.append((_sect_name(_MENU[_i][0]), _i))

MENU_PAGES = build_menu_pages()            # auto pages (100 emoji/msg limit ke andar)
PAGE_CMDS = ["m{}".format(i + 1) for i in range(len(MENU_PAGES))]
CAT_CMDS = ["m{}".format(len(MENU_PAGES) + 1 + i) for i in range(len(CATS))]

CAT_OF_CMD = {}                            # command → uska category menu
for _k, (_nm, _idx) in enumerate(CATS):
    for _c, _d in _MENU[_idx][1]:
        CAT_OF_CMD.setdefault(_c, CAT_CMDS[_k])


def build_category_menu(k, w=34):
    """category page — .m(N+1) se aage, har category ka apna emoji"""
    nm, idx = CATS[k]
    title, items = _MENU[idx]
    st = CAT_STYLE.get(nm, _STYLE_DEFAULT)
    rows = [hdr(f"{st['icon']}{SP} ▰ {sb(nm)}", w, count=len(items))]
    for i, (c, d) in enumerate(items):
        rows.append(row(c, d, bullet=(st["icon"] if i % 2 == 0 else st["alt"]), cw=13))
    rows.append(end(w))
    page = len(MENU_PAGES) + k
    return "\n".join(menu_head(w, page) + rows + [
        sub(f"{E['dot']}{SP} {mono('.' + CAT_CMDS[k])} {E['arrow']} {sc(nm)} "
            f"{E['arrow']} {mono(str(len(items)))} {sc('commands')}"),
        sub(FOOT),
        close(),
    ])


def build_menu_index(w=34):
    """.menu / .help — kaunsa menu kis cheez ka hai, poori list"""
    L = menu_head(w)
    L.append(hdr(f"{E['film']}{SP} ▰ {sb('pages')}", w, count=len(PAGE_CMDS)))
    for i, c in enumerate(PAGE_CMDS, 1):
        L.append(row(c, f"{sc('page')} {mono(str(i))}/{mono(str(len(MENU_PAGES)))}",
                     bullet=E["film"], cw=9))
    L.append(end(w))
    L.append(hdr(f"{E['gem']}{SP} ▰ {sb('by category')}", w, count=len(CATS)))
    for k, (nm, idx) in enumerate(CATS):
        st = CAT_STYLE.get(nm, _STYLE_DEFAULT)
        L.append(row(CAT_CMDS[k], f"{sc(nm)} ({mono(str(len(_MENU[idx][1])))})",
                     bullet=st["icon"], cw=9))
    L.append(end(w))
    L.append(hdr(f"{E['fire']}{SP} ▰ {sb('extra')}", w, count=2))
    L.append(row("fullmenu", f"{sc('sab')} {mono(str(len(MENU_PAGES)))} {sc('pages ek saath')}",
                 bullet=E["fire"], cw=9))
    L.append(row("help", sc("kisi bhi command ki detail"), bullet=E["note"], cw=9))
    L.append(end(w))
    L.append(hdr(f"{E['music']}{SP} ▰ {sb('voice chat')}", w, count=len(_VC_MENU)))
    L.append(row("m24", f"{sc('vc')} {E['arrow']} {mono(str(len(_VC_MENU)))} {sc('commands')}",
                 bullet=E["music"], cw=9))
    L.append(end(w))
    L += [sub(FOOT), close()]
    return "\n".join(L)


async def _send_banner(event):
    if not MENU_BANNER:
        return
    try:
        chat_id, msg_id = MENU_BANNER
        msg = await bot.get_messages(chat_id, ids=msg_id)
        if msg and getattr(msg, "media", None):
            await bot.send_file(event.chat_id, file=msg.media, caption=BRAND)
    except Exception:
        pass


@register_cmd("menu")
async def cmd_menu(event, _):
    """.menu — index: .m1.. pages + uske baad category pages"""
    await eor(event, build_menu_index())
    await _send_banner(event)


@register_cmd("fullmenu")
async def cmd_fullmenu(event, _):
    """.fullmenu — 3no pages ek saath (3 alag messages)"""
    await eor(event, MENU_PAGES[0])
    for pg in MENU_PAGES[1:]:
        try:
            await event.reply(pg)
        except Exception:
            pass
    await _send_banner(event)


def _mk_page_cmd(i):
    async def runner(event, arg):
        if i < len(MENU_PAGES):
            await eor(event, MENU_PAGES[i])
    runner.__name__ = "cmd_{}".format(PAGE_CMDS[i])
    return runner


def _mk_cat_cmd(k):
    async def runner(event, arg):
        if k < len(CATS):
            await eor(event, build_category_menu(k))
    runner.__name__ = "cmd_{}".format(CAT_CMDS[k])
    return runner


for _i in range(len(PAGE_CMDS)):
    register_cmd(PAGE_CMDS[_i])(_mk_page_cmd(_i))
for _k in range(len(CATS)):
    register_cmd(CAT_CMDS[_k])(_mk_cat_cmd(_k))


# ── detailed guides (`.help <cmd>` pe poora tareeqa) ──────────
GUIDES = {
    "addbot": lambda: guide_addbot(),
    "music": lambda: guide_music(),
    "song": lambda: guide_music(),
    "play": lambda: guide_music(),
    "mp3": lambda: guide_music(),
    "c": lambda: panel([
        f"{E['film']} {sb('LOGIN CODE')}",
        "",
        f"{E['dot']} {mono('.c 12345')}",
        f"{E['dot']} {mono('.c 1 2 3 4 5')} {sc('(spaces chalenge)')}",
        f"{E['dot']} {mono('.c +919876543210 12345')}",
        "",
        f"{E['warn']} {sc('pehle')} {mono('.addbot +91…')} {sc('karo')}",
    ]),
    "p": lambda: panel([
        f"{E['lock']} {sb('2FA PASSWORD')}",
        "",
        f"{E['dot']} {mono('.p mera_password')}",
        "",
        f"{E['note']} {sc('sirf tab jab telegram bole')}",
        f"   {sc('\"2fa password chahiye\"')}",
    ]),
    "user": lambda: panel([
        f"{E['bot']} {sb('CONNECTED USERBOTS')}",
        "",
        f"{E['dot']} {mono('.user')} {sc('— live + pending list')}",
        f"{E['dot']} {mono('.addbot +91…')} {sc('— naya login')}",
        f"{E['dot']} {mono('.delbot +91…')} {sc('— hatao')}",
    ]),
    "delbot": lambda: panel([
        f"{E['trash']} {sb('REMOVE SUBBOT')}",
        "",
        f"{E['dot']} {mono('.delbot +919876543210')}",
        f"{E['dot']} {mono('.delbot all')} {sc('(sab)')}",
        "",
        f"{E['warn']} {sc('session file bhi delete ho jayegi')}",
    ]),
}


@register_cmd("help")
async def cmd_help(event, arg):
    key = (arg or "").strip().lstrip(".").lower().split()[0] if (arg or "").strip() else ""
    if key:
        key = aliases.get(key, key)
        if key in GUIDES:
            return await eor(event, GUIDES[key]())
        if key in commands:
            desc, sect = "", "—"
            for sname, items in _MENU:
                for c, d in items:
                    if c == key:
                        desc, sect = d, sname
            sect = sect.split(" ", 1)[-1] if " " in sect else sect
            al = sorted(k for k, v in aliases.items() if v == key)
            needs = commands[key]
            tags = []
            if needs.get("group_only"):
                tags.append(sc("group only"))
            if needs.get("needs_reply"):
                tags.append(sc("reply / target"))
            if key in OWNER_ONLY_EXTRA or needs.get("owner_only"):
                tags.append(sc("owner only"))
            return await eor(event, "\n".join([
                top(),
                sub(f"{E['spark']} {mono(PREFIX + key)}"),
                sub(""),
                sub(f" {E['dot']} {sc(sect)}"),
                sub(f" {E['star']} {sc(desc) if desc else sc('guide menu me hai')}"),
                sub(f" {E['dot']} {sc('aliases')} ‣ "
                    + mono(", ".join(al) or "koi nahi")),
                sub(f" {E['film']} {sc('menu')} ‣ "
                    + mono("." + CAT_OF_CMD.get(key, "fullmenu"))),
                sub(f" {E['shield']} {sc('mode')} ‣ "
                    + sc(" · ".join(tags) or "sabke liye")),
                sub(""),
                sub(FOOT),
                close(),
            ]))
        return await flash(event, f"{E['no']} {mono('.' + key)} {sc('koi command nahi')}\n"
                                  f"{E['dot']} {mono('.help')}", secs=6)
    # bina arg → poori menu list (pages + categories + .fullmenu)
    await eor(event, build_menu_index())


def _uptime():
    up = int(time.time() - START_TIME)
    d, rem = divmod(up, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return d, h, m, s, up


@register_cmd("alive")
async def cmd_alive(event, _):
    d, h, m, s, _u = _uptime()
    me = await bot.get_me()
    un = f"@{me.username}" if getattr(me, "username", None) else "—"
    up = (f"{d}d {h}h {m}m" if d else f"{h}h {m}m {s}s")
    await eor(event, "\n".join([
        top(),
        sub(f"{E['spark']} {sc('status')} ‣ {mono('online')} {E['ok']}"),
        sub(""),
        sub(f"{E['crown']} {sc('user')}   ‣ {me.first_name}"),
        sub(f"{E['dot']}  {sc('tag')}    ‣ {un}"),
        sub(f"{E['gem']} {sc('id')}     ‣ {mono(str(me.id))}"),
        sub(""),
        sub(f"{E['clock']} {sc('uptime')} ‣ {mono(up)}"),
        sub(f"{E['shield']} {sc('muted')}  ‣ {mono(str(len(MUTED) + len(GLOBAL_MUTED)))}"),
        sub(f"{E['sword']} {sc('raids')}  ‣ {mono(str(len(reply_users) + len(rr_users) + len(flag_users) + len(hrr_users)))}"),
        sub(f"{E['globe']} {sc('gban')}   ‣ {mono(str(len(GBAN)))}  {sc('gmute')} {mono(str(len(GMUTE)))}"),
        sub(f"{E['save']} {sc('saved')}  ‣ {mono(str(len(SAVED_MSGS)))}"),
        sub(""),
        sub(FOOT),
        close(),
    ]))


@register_cmd("ping")
async def cmd_ping(event, _):
    t0 = time.time()
    msg = await eor(event, f"{E['wait']} {sc('pinging')}…")
    dt = (time.time() - t0) * 1000
    if msg is not None:
        await aedit(msg, "\n".join([
            top(),
            sub(f"{E['bolt']} {sc('response')} ‣ {mono(f'{dt:.2f} ms')}"),
            sub(f"{E['dot']}  {sc('build')}    ‣ {mono(VERSION)}"),
            sub(f"{E['dot']}  {sc('mode')}     ‣ {mono('global')}"),
            sub(""),
            sub(FOOT),
            close(),
        ]))


@register_cmd("uptime")
async def cmd_uptime(event, _):
    d, h, m, s, _u = _uptime()
    await eor(event, "\n".join([
        top(),
        sub(f"{E['clock']} {sc('uptime')}"),
        sub(""),
        sub(f" {E['dot']} {sc('days')}    ‣ {mono(str(d))}"),
        sub(f" {E['dot']} {sc('hours')}   ‣ {mono(str(h))}"),
        sub(f" {E['dot']} {sc('minutes')} ‣ {mono(str(m))}"),
        sub(f" {E['dot']} {sc('seconds')} ‣ {mono(str(s))}"),
        sub(""),
        sub(FOOT),
        close(),
    ]))


def hr(n=26):
    """.status ke liye sirf horizontal separator — koi side border nahi"""
    return "─" * n


def _sr(bullet, label, w=12):
    """.status ki ek row — label column fix, ‣ sab ek hi line pe"""
    lab = sc(label)
    return " {b} {lab}{pad}".format(b=bullet, lab=lab,
                                    pad=" " * max(1, w - len(lab)))


@register_cmd("status")
async def cmd_status(event, _):
    """.status — bold sections, sirf ───── lines (mobile pe cut nahi hota)"""
    d, h, m, s, _u = _uptime()
    me = await bot.get_me()
    un = f"@{me.username}" if getattr(me, "username", None) else "—"
    L = [
        f"{E['spark']} {sb('NIK USERBOT')}  {E['arrow']}  {sb('STATUS')}",
        hr(26),
        f"{E['crown']} {sb('ACCOUNT')}",
        _sr(E["crown"], "name") + "‣ " + getattr(me, "first_name", "—"),
        _sr(E["link"], "tag") + "‣ " + un,
        _sr(E["gem"], "id") + "‣ " + mono(str(me.id)),
        _sr(E["crown2"], "owner") + "‣ " + mono(str(OWNER_ID)),
        _sr(E["shield"], "sudo") + "‣ " + mono(str(len(ADMINS))),
        hr(26),
        f"{E['shield']} {sb('MODERATION')}",
        _sr(E["chain"], "muted") + "‣ " + mono(str(len(MUTED))),
        _sr(E["globe"], "gmuted") + "‣ " + mono(str(len(GLOBAL_MUTED))),
        _sr(E["sword"], "raids") + "‣ " + mono("{}/{}/{}/{}".format(
            len(reply_users), len(rr_users), len(flag_users), len(hrr_users))),
        _sr(E["sat"], "gban") + "‣ " + mono(str(len(GBAN))),
        _sr(E["wave"], "gmute") + "‣ " + mono(str(len(GMUTE))),
        _sr(E["no"], "blacklist") + "‣ " + mono(str(len(BLACKLIST))),
        hr(26),
        f"{E['lock']} {sb('CHAT CONTROL')}",
        _sr(E["sat"], "bc-db") + "‣ " + mono(str(len(BCDB))),
        _sr(E["lock"], "locked") + "‣ " + mono(str(len(LOCKS))),
        _sr(E["key"], "filters") + "‣ " + mono(
            str(sum(len(v) for v in FILTERS.values()))),
        _sr(E["eye"], "antidel") + "‣ " + mono(str(len(ANTIDEL))),
        _sr(E["warn"], "spamguard") + "‣ " + mono(str(len(SPAMWATCH))),
        hr(26),
        f"{E['bolt']} {sb('AUTO')}",
        _sr(E["bolt"], "autoread") + "‣ " + mono(
            ",".join(sorted(AUTOREAD)) or "off"),
        _sr(E["note"], "areply") + "‣ " + mono("on" if AREPLY else "off"),
        _sr(E["ghost"], "ghost") + "‣ " + mono("on" if GHOST["on"] else "off"),
        _sr(E["spark"], "auto-react") + "‣ " + mono(AUTO_REACT_EMOJI or "off"),
        hr(26),
        _sr(E["clock"], "uptime") + "‣ " + mono("{}d {}h {}m".format(d, h, m)),
        "",
        FOOT,
    ]
    await eor(event, "\n".join(L))


@register_cmd("id")
async def cmd_id(event, arg):
    # DM me ho → saamne wale ki id auto
    if not event.is_reply and not arg:
        try:
            if event.is_private and event.chat_id and int(event.chat_id) > 0:
                ent = await bot.get_entity(int(event.chat_id))
                return await eor(event, "\n".join([
                    top(),
                    sub(f"{E['gem']} {sc('dm detected')}"),
                    sub(""),
                    sub(f" {E['dot']} {sc('user')} ‣ {mono(str(ent.id))}"),
                    sub(f" {E['dot']} {sc('name')} ‣ {getattr(ent, 'first_name', '—')}"),
                    sub(f" {E['dot']} {sc('chat')} ‣ {mono(str(event.chat_id))}"),
                    sub(""), sub(FOOT), close(),
                ]))
        except Exception:
            pass
        me = await bot.get_me()
        return await eor(event, f"{E['gem']} {sc('you')} {mono(str(me.id))} {E['arrow']} {sc('chat')} {mono(str(event.chat_id))}")
    if event.is_reply:
        r = await event.get_reply_message()
        uid = r.sender_id
        name = "—"
        try:
            ent = await bot.get_entity(uid)
            name = getattr(ent, "first_name", "—") or "—"
        except Exception:
            pass
        return await eor(event, f"{E['gem']} {name} {E['arrow']} {mono(str(uid))} {E['arrow']} {sc('chat')} {mono(str(event.chat_id))}")
    try:
        ent = await bot.get_entity(arg.strip())
        await eor(event, f"{E['gem']} {mono(arg.strip())} {E['arrow']} {mono(str(ent.id))}")
    except Exception as e:
        await eor(event, f"{E['no']} {err_txt(e, 60)}")


@register_cmd("info")
async def cmd_info(event, arg):
    target = None
    if event.is_reply:
        r = await event.get_reply_message()
        target = r.sender_id if r else None
    elif arg:
        try:
            ent = await bot.get_entity(arg.strip())
            target = ent.id
        except Exception:
            return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    else:
        # DM auto-detect
        try:
            if event.is_private and int(event.chat_id) > 0:
                target = int(event.chat_id)
        except Exception:
            pass
    if not target:
        return await eor(event, f"{E['warn']} {mono('.info')} {E['arrow']} {sc('reply / @user / id / dm')}")
    try:
        user = await bot.get_entity(target)
        full = await bot(functions.users.GetFullUserRequest(user.id))
    except Exception as e:
        return await eor(event, f"{E['no']} {err_txt(e, 60)}")
    bio = (full.full_user.about or "—").replace("\n", " ")
    un = f"@{user.username}" if getattr(user, "username", None) else "—"
    nm = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip() or "—"
    await eor(event, "\n".join([
        top(),
        sub(f"{E['crown']} {sc('profile')}"),
        sub(""),
        sub(f" {E['dot']} {sc('name')}  ‣ {nm}"),
        sub(f" {E['gem']} {sc('id')}    ‣ {mono(str(user.id))}"),
        sub(f" {E['link']} {sc('user')}  ‣ {un}"),
        sub(f" {E['bot']} {sc('bot')}   ‣ {mono('yes' if getattr(user, 'bot', False) else 'no')}"),
        sub(f" {E['note']} {sc('bio')}   ‣ {bio[:90]}"),
        sub(""), sub(FOOT), close(),
    ]))


@register_cmd("flip")
async def cmd_flip(event, _):
    msg = await eor(event, f"{E['dice']} {sc('tossing')}…")
    if msg is None:
        return
    for f in ["🪙", "⟳", "⟲", "◐", "◓"]:
        try:
            await msg.edit(f); await asyncio.sleep(0.25)
        except Exception:
            break
    try:
        await msg.edit(f"{E['spark']} {random.choice([sc('heads'), sc('tails')]).upper()}")
    except Exception:
        pass


@register_cmd("speed")
async def cmd_speed(event, arg):
    global STORY_DELAY
    if not arg:
        return await eor(event, f"{E['film']} {sc('story speed')} {E['arrow']} {mono(str(STORY_DELAY) + 's')}\n"
                                f"{E['dot']} {mono('.speed 2')} {E['arrow']} {sc('0.5 – 10 sec')}")
    try:
        v = float(arg.split()[0])
    except Exception:
        return await eor(event, f"{E['no']} {sc('number do')} — {mono('.speed 2')}")
    STORY_DELAY = max(0.5, min(v, 10.0))
    await eor(event, f"{E['film']} {sc('story speed set')} {E['arrow']} {mono(str(STORY_DELAY) + 's')}")


# ══════════════════════════════════════════════════════════════
#                        ᴍᴇssᴀɢɪɴɢ
# ══════════════════════════════════════════════════════════════
@register_cmd("hy")
async def cmd_hy(event, arg):
    who = ""
    if event.is_reply:
        try:
            r = await event.get_reply_message()
            ent = await bot.get_entity(r.sender_id)
            who = f"[{ent.first_name}](tg://user?id={ent.id})"
        except Exception:
            who = ""
    tail = f" {who}" if who else ""
    msg = await eor(event, f"{E['spark']} {scr('hey')}…")
    if msg is None:
        return
    for f in [f"{E['spark']}", f"{E['spark']} {E['dot']}",
              f"{scr('hey')}{tail}", f"{scr('hey')}{tail} {E['spark']}",
              f"{scrb('Hey')}{tail} {E['spark']} {E['heart']}"]:
        try:
            await msg.edit(f); await asyncio.sleep(0.5)
        except Exception:
            break


@register_cmd("del")
async def cmd_del(event, arg):
    if event.is_reply:
        try:
            r = await event.get_reply_message()
            await r.delete()
        except Exception as e:
            return await eor(event, f"{E['no']} {err_txt(e, 50)}")
    try:
        await event.delete()
    except Exception:
        pass


@register_cmd("forward")
async def cmd_forward(event, arg):
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('reply karke')} {mono('.forward @chat')}")
    r = await event.get_reply_message()
    dest = arg.strip() if arg else "me"
    try:
        await bot.forward_messages(dest, r)
        await done(event, f"{E['rocket']} {sc('forwarded')} {E['arrow']} {mono(dest)}")
    except Exception as e:
        await eor(event, f"{E['no']} {err_txt(e, 70)}")


@register_cmd("setchannel")
async def cmd_setchannel(event, arg):
    global SAVED_CHANNEL
    if not arg:
        return await eor(event, f"{E['save']} {sc('current')} {E['arrow']} {mono(SAVED_CHANNEL or 'none')}\n"
                                f"{E['dot']} {mono('.setchannel @channel')}")
    val = arg.strip()
    try:
        ent = await bot.get_entity(val)
        val = f"@{ent.username}" if getattr(ent, "username", None) else str(ent.id)
    except Exception:
        pass
    SAVED_CHANNEL = val
    save_json(F_SAVED_CH, SAVED_CHANNEL)
    await eor(event, f"{E['save']} {sc('channel set')} {E['arrow']} {mono(SAVED_CHANNEL)}\n"
                     f"{E['dot']} {mono('.save')} {sc('se save karo')}")


@register_cmd("save")
async def cmd_save(event, arg):
    global SAVED_MSGS
    if not SAVED_CHANNEL:
        return await eor(event, f"{E['no']} {sc('pehle')} {mono('.setchannel @channel')}")
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('kisi msg pe reply karke')} {mono('.save')}")
    reply = await event.get_reply_message()
    st = await flash(event, f"{E['save']} {sc('saving')}…")
    sent = None
    last_err = ""
    # ── try 1: forward (sabse fast, forwarded tag ke saath) ──
    try:
        res = await bot.forward_messages(SAVED_CHANNEL, reply)
        sent = res[0] if isinstance(res, list) and res else res
    except Exception as e:
        last_err = str(e)
    # ── try 2: resend (media + text dono sambhalta hai) ──
    if sent is None:
        try:
            sent = await bot.send_message(SAVED_CHANNEL, reply)
        except Exception as e:
            last_err = str(e)
    # ── try 3: download + upload ──
    if sent is None and getattr(reply, "media", None):
        try:
            raw = await reply.download_media(file=bytes)
            if raw:
                bio = BytesIO(raw)
                bio.name = getattr(reply.file, "name", None) or "saved"
                sent = await bot.send_file(SAVED_CHANNEL, bio,
                                           caption=reply.raw_text or "")
        except Exception as e:
            last_err = str(e)
    if sent is None:
        return await eor(event, f"{E['no']} {sc('save fail')}\n{E['dot']} {mono(str(last_err)[:70])}")
    try:
        chat_val = getattr(sent, "chat_id", None)
        if chat_val is None or str(chat_val).strip() in ("", "0"):
            chat_val = SAVED_CHANNEL
        elif str(chat_val).lstrip("-").isdigit():
            chat_val = int(chat_val)
    except Exception:
        chat_val = SAVED_CHANNEL
    SAVED_MSGS.append({"chat_id": chat_val, "msg_id": int(getattr(sent, "id", 0) or 0),
                       "text": (reply.raw_text or "")[:40]})
    SAVED_MSGS = SAVED_MSGS[-50:]
    save_json(F_SAVED_MSGS, SAVED_MSGS)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['save']} {sc('saved')} {E['arrow']} {mono(SAVED_CHANNEL)}\n"
                      f"{E['gem']} {sc('id')} {mono(str(SAVED_MSGS[-1]['msg_id']))} {E['arrow']} {mono('.fwd')}", secs=6)


@register_cmd("savelist")
async def cmd_savelist(event, arg):
    if not SAVED_MSGS:
        return await eor(event, f"{E['note']} {sc('kuch save nahi hai')}")
    lines = [top(), sub(f"{E['save']} {sc('saved')} {E['arrow']} {mono(str(SAVED_CHANNEL))}"), sub("")]
    for i, e in enumerate(SAVED_MSGS[-15:], 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {mono(str(e.get('msg_id')))} · {(e.get('text') or '')[:20]}"))
    lines += [sub(""), sub(f"{E['dot']} {mono('.fwd <number>')}"), close()]
    await eor(event, "\n".join(lines))


@register_cmd("delsave")
async def cmd_delsave(event, arg):
    global SAVED_MSGS
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.delsave <number/all>')}")
    if arg.strip().lower() == "all":
        SAVED_MSGS = []
        save_json(F_SAVED_MSGS, SAVED_MSGS)
        return await eor(event, f"{E['trash']} {sc('saaf kar diya')}")
    try:
        idx = int(arg.strip()) - 1
        if 0 <= idx < len(SAVED_MSGS):
            SAVED_MSGS.pop(idx)
    except Exception:
        return await eor(event, f"{E['no']} {sc('number galat')}")
    save_json(F_SAVED_MSGS, SAVED_MSGS)
    await eor(event, f"{E['trash']} {sc('deleted')} {E['arrow']} {sc('bache')} {mono(str(len(SAVED_MSGS)))}")


@register_cmd("fwd")
async def cmd_fwd(event, arg):
    if not SAVED_MSGS:
        return await eor(event, f"{E['no']} {sc('koi saved msg nahi')} {E['arrow']} {mono('.save')}")
    if not SAVED_CHANNEL:
        return await eor(event, f"{E['no']} {sc('pehle')} {mono('.setchannel @channel')}")
    entry = None
    a = (arg or "").strip()
    if a:
        if a.isdigit():
            n = int(a)
            if 1 <= n <= len(SAVED_MSGS):
                entry = SAVED_MSGS[n - 1]
            else:
                for e in SAVED_MSGS:
                    if str(e.get("msg_id")) == a:
                        entry = e
                        break
    if entry is None:
        entry = SAVED_MSGS[-1]
    src = entry.get("chat_id") or SAVED_CHANNEL
    mid = safe_int(entry.get("msg_id"), 0)
    msg = None
    try:
        msg = await bot.get_messages(src, ids=mid)
    except Exception:
        msg = None
    if msg is None:
        return await eor(event, f"{E['no']} {sc('saved msg nahi mila')} {mono(str(mid))}\n"
                                f"{E['dot']} {sc('delete ho gaya ya channel badla')}\n"
                                f"{E['dot']} {mono('.save')} {sc('dubara karo')}")
    try:
        if event.is_reply:
            target = await event.get_reply_message()
            await bot.send_message(event.chat_id, msg, reply_to=target.id)
        else:
            try:
                await bot.forward_messages(event.chat_id, mid, from_peer=src)
            except Exception:
                await bot.send_message(event.chat_id, msg)
        try:
            await event.delete()
        except Exception:
            pass
        conf = await event.respond(f"{E['rocket']} {sc('work done')} {E['heart']}")
        asyncio.create_task(_del_after(conf, 3))
    except Exception as e:
        await eor(event, f"{E['no']} {sc('fwd fail')} {E['arrow']} {mono(err_txt(e, 70))}")


async def _delete_ids(chat, ids, revoke=True):
    """messages delete → KITNE ASLI me hate wahi return karta hai."""
    done = 0
    todo = [int(i) for i in ids if i]
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        got = 0
        for _try in range(2):
            try:
                await bot.delete_messages(chat, batch, revoke=revoke)
                got = len(batch)
                break
            except FloodWaitError as fw:
                await asyncio.sleep(min(int(getattr(fw, "seconds", 3)) or 3, 25))
            except Exception:
                break
        if not got:
            # batch fail → ek-ek karke (kuch messages delete ho sakte hain)
            for mid in batch:
                try:
                    await bot.delete_messages(chat, [mid], revoke=revoke)
                    got += 1
                except FloodWaitError as fw:
                    await asyncio.sleep(min(int(getattr(fw, "seconds", 2)) or 2, 10))
                    try:
                        await bot.delete_messages(chat, [mid], revoke=revoke)
                        got += 1
                    except Exception:
                        pass
                except Exception:
                    pass
        done += got
        await asyncio.sleep(0.2)
    return done


@register_cmd("purge")
async def cmd_purge(event, arg):
    """reply + .purge  → reply ke NICHE ke saare (reply + command samet)
       .purge <n>     → command ke upar ke n purane
       bina reply aur bina count → usage error"""
    chat = event.chat_id
    n_arg = (arg or "").strip()
    if event.is_reply:
        r = await event.get_reply_message()
        lo, hi = min(r.id, event.id), max(r.id, event.id)
        ids = list(range(lo, hi + 1))
    else:
        if not n_arg:
            return await eor(event, "\n".join([
                top(),
                sub(f"{E['warn']} {sc('purge ko target chahiye')}"),
                sub(""),
                sub(f" {E['dot']} {mono('.purge')} {sc('(reply karke)')}"),
                sub(f"       {sc('reply ke niche sab uda do')}"),
                sub(f" {E['dot']} {mono('.purge 200')}"),
                sub(f"       {sc('200 purane msg uda do')}"),
                sub(f" {E['dot']} {mono('.purge 1-999999')}"),
                sub(f"       {sc('id range wale sab uda do')}"),
                sub(""), sub(FOOT), close(),
            ]))
        # `.purge 200` → last 200 · `.purge 1-999999` → id range
        rng = re.match(r"^(\d+)\s*-\s*(\d+)$", n_arg.split()[0])
        if rng:
            lo, hi = sorted((int(rng.group(1)), int(rng.group(2))))
            st0 = await flash(event, f"{E['trash']} {sc('scanning')} {mono(f'{lo}-{hi}')}…", secs=120)
            ids = []
            try:
                async for m in bot.iter_messages(chat, limit=None):
                    if lo <= int(m.id) <= hi:
                        ids.append(m.id)
            except Exception:
                pass
            if st0 is not None:
                try:
                    await st0.delete()
                except Exception:
                    pass
        else:
            try:
                n = int(n_arg.split()[0])
            except Exception:
                return await eor(event, f"{E['no']} {sc('count number do')} — {mono('.purge 50')} / {mono('.purge 1-999999')}")
            n = max(1, min(n, 999999))
            ids = []
            async for m in bot.iter_messages(chat, limit=n, max_id=event.id):
                ids.append(m.id)
    if not ids:
        return await eor(event, f"{E['warn']} {sc('koi message nahi mila')}")
    total = len(ids)
    st = await flash(event, f"{E['trash']} {sc('purging')} {mono(str(total))}…", secs=30)
    done = await _delete_ids(chat, ids)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    skip = total - done
    lines = [top(), sub(""),
             sub(f" {E['trash']} {sc('purge done')} {E['arrow']} "
                 f"{mono(str(done))}/{mono(str(total))}"),
             sub(f" {E['dot']} {sc('deleted')} {E['arrow']} {mono(str(done))} {sc('messages')}")]
    if skip:
        lines.append(sub(f" {E['warn']} {sc('skip')} {E['arrow']} {mono(str(skip))} "
                         f"{sc('(purane / admin-only)')}"))
    lines += [sub(FOOT), close()]
    conf = await eor(event, "\n".join(lines))
    await _del_after(conf, TMP_TTL)


async def _my_msg_ids(chat, me_id, limit=None):
    """Is chat me mere messages ke ids — accurate.

    • from_user search (server side, fast)
    • out=True scan (jab search khaali/adhura aata hai)
    • limit None → jitna scan cap hai utna (SCAN_CAP)
    """
    ids, seen = [], set()
    cap = limit or 5000
    soft_cap = cap if limit else 3000

    def add(mid):
        mid = int(mid)
        if mid and mid not in seen:
            seen.add(mid)
            ids.append(mid)

    try:
        async for m in bot.iter_messages(chat, from_user=int(me_id),
                                         limit=soft_cap):
            add(m.id)
            if len(ids) >= cap:
                break
    except Exception:
        pass

    if not limit or len(ids) < cap:
        try:
            async for m in bot.iter_messages(chat, limit=soft_cap):
                if getattr(m, "out", False) or \
                        int(getattr(m, "sender_id", 0) or 0) == int(me_id):
                    add(m.id)
                if len(ids) >= cap:
                    break
        except Exception:
            pass
    return ids


@register_cmd("purgeme")
async def cmd_purgeme(event, arg):
    """.purgeme [n|all] → is chat ke apne messages (default: SAARE)"""
    a = (arg or "").strip().lower()
    limit = None if (not a or a in ("all", "sab", "full", "0")) else None
    if a and limit is None:
        try:
            limit = max(1, min(int(a.split()[0]), 999999))
        except Exception:
            limit = None

    chat = int(event.chat_id)
    me = await bot.get_me()
    st = await flash(event, f"{E['trash']} {sc('apne msgs dhoondh raha hoon')}…",
                     secs=120)
    ids = await _my_msg_ids(chat, int(me.id), limit)
    if event.id not in ids:
        ids.append(event.id)
    scanned = len(ids)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    if not ids:
        return await eor(event, f"{E['warn']} {sc('koi apna message nahi mila')}")

    done = await _delete_ids(chat, ids)
    skip = scanned - done
    lines = [top(), sub(""),
             sub(f" {E['trash']} {sc('purgeme done')} {E['arrow']} "
                 f"{mono(str(done))}/{mono(str(scanned))}"),
             sub(f" {E['dot']} {sc('mode')} ‣ "
                 f"{mono('all' if limit is None else str(limit))}"),
             sub(f" {E['dot']} {sc('deleted')} {E['arrow']} {mono(str(done))} "
                 f"{sc('messages')}")]
    if skip:
        lines.append(sub(f" {E['warn']} {sc('skip')} {E['arrow']} {mono(str(skip))}"))
    lines += [sub(FOOT), close()]
    conf = await eor(event, "\n".join(lines))
    await _del_after(conf, 6)


@register_cmd("delmine")
async def cmd_delmine(event, arg):
    """.delmine [@chat]  → us chat ke apne SAARE messages
       .delmine <n> [@chat] → n messages"""
    parts = (arg or "").split()
    chat = event.chat_id
    n = None
    for p in parts:
        if p.lstrip("-").isdigit():
            n = int(p)
        else:
            try:
                ent = await bot.get_entity(p)
                chat = ent.id
            except Exception:
                pass
    me = await bot.get_me()
    st = await flash(event, f"{E['trash']} {sc('apne messages scan')}…", secs=90)
    ids = await _my_msg_ids(chat, int(me.id), n)     # server search + scan
    if chat == int(event.chat_id) and event.id not in ids:
        ids.append(event.id)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    if not ids:
        conf = await eor(event, f"{E['warn']} {sc('koi apna message nahi mila')}")
        return await _del_after(conf, TMP_TTL)
    done = await _delete_ids(chat, ids)
    conf = await eor(event, f"{E['trash']} {sc('apne')} {mono(str(done))} {sc('messages udaye')}\n"
                            f"{E['gem']} {sc('chat')} {mono(str(chat))}")
    await _del_after(conf, TMP_TTL)


@register_cmd("filter")
async def cmd_filter(event, arg):
    word = (arg or "").strip().lower()
    if not word:
        return await eor(event, f"{E['no']} {mono('.filter <word>')} {sc('— reply ke saath')}")
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('jise reply dena hai uspe reply karo')}")
    r = await event.get_reply_message()
    key = str(event.chat_id)
    FILTERS.setdefault(key, {})[word] = {"chat_id": int(event.chat_id),
                                         "msg_id": int(r.id), "text": r.raw_text or ""}
    save_json(F_FILTERS, FILTERS)
    await done(event, f"{E['key']} {sc('filter set')} {E['arrow']} {mono(word)}", secs=6)


@register_cmd("filters")
async def cmd_filters(event, arg):
    data = FILTERS.get(str(event.chat_id)) or {}
    if not data:
        return await eor(event, f"{E['note']} {sc('is chat me koi filter nahi')}")
    lines = [top(), sub(f"{E['key']} {sc('filters')} {mono(str(len(data)))}"), sub("")]
    for i, w in enumerate(sorted(data), 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {w}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("unfilter")
async def cmd_unfilter(event, arg):
    word = (arg or "").strip().lower()
    key = str(event.chat_id)
    if not word:
        return await eor(event, f"{E['dot']} {mono('.unfilter <word>')}")
    data = FILTERS.get(key) or {}
    if word not in data:
        return await eor(event, f"{E['warn']} {sc('ye filter hai hi nahi')}")
    data.pop(word)
    if not data:
        FILTERS.pop(key, None)
    save_json(F_FILTERS, FILTERS)
    await done(event, f"{E['trash']} {sc('filter hata diya')} {E['arrow']} {mono(word)}", secs=6)


# ══════════════════════════════════════════════════════════════
#                           ᴀᴜᴛᴏ
# ══════════════════════════════════════════════════════════════
@register_cmd("autoread")
async def cmd_autoread(event, arg):
    parts = (arg or "").split()
    if len(parts) < 2:
        return await eor(event, f"{E['eye']} {sc('auto-read')} {E['arrow']} {mono(','.join(sorted(AUTOREAD)) or 'off')}\n"
                                f"{E['dot']} {mono('.autoread group on')}")
    scope, state = parts[0].lower(), parts[1].lower()
    if scope not in ("group", "private", "channel", "all"):
        return await eor(event, f"{E['no']} {sc('scope')} {E['arrow']} {mono('group / private / channel / all')}")
    if state in ("on", "enable", "start", "yes", "1"):
        AUTOREAD.add(scope); verb = "ON"
    else:
        AUTOREAD.discard(scope); verb = "OFF"
    save_json(F_AUTOREAD, sorted(AUTOREAD))
    await eor(event, f"{E['eye']} {sc('auto-read')} {mono(scope)} {E['arrow']} {sb(verb)}\n"
                     f"{E['dot']} {sc('active')} {mono(','.join(sorted(AUTOREAD)) or 'off')}")


@register_cmd("areply")
async def cmd_areply(event, arg):
    global AREPLY
    if not arg:
        return await eor(event, f"{E['note']} {mono('.areply <text>')}\n{E['dot']} {mono('.stopareply')}")
    AREPLY = arg.strip()
    save_json(F_AREPLY, AREPLY)
    await done(event, f"{E['note']} {sc('auto-reply on')} {E['arrow']} {AREPLY[:50]}", secs=6)


@register_cmd("stopareply")
async def cmd_stopareply(event, arg):
    global AREPLY
    AREPLY = None
    save_json(F_AREPLY, None)
    await done(event, f"{E['note']} {sc('auto-reply off')}", secs=6)


@register_cmd("arreply")
async def cmd_arreply(event, arg):
    """.arreply <text> (reply to user) — us user ko har baar yahi reply"""
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('kisi user pe reply karo')} {E['arrow']} {mono('.arreply <text>')}")
    parts = (arg or "").split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
    if event.is_reply:
        text = arg or ""
    if not text:
        return await eor(event, f"{E['no']} {mono('.arreply <text>')}")
    USER_REPLY[uid] = text
    await done(event, f"{E['note']} {sc('user auto-reply on')} {E['arrow']} {mono(str(uid))}\n"
                      f"{E['dot']} {text[:40]}\n{E['dot']} {mono('.sarreply')}", secs=8)


@register_cmd("sarreply")
async def cmd_sarreply(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid or uid not in USER_REPLY:
        return await eor(event, f"{E['warn']} {sc('us user pe koi reply set nahi')}")
    USER_REPLY.pop(uid, None)
    await done(event, f"{E['note']} {sc('user auto-reply off')} {E['arrow']} {mono(str(uid))}", secs=6)


# ══════════════════════════════════════════════════════════════
#                        ʙʟᴀᴄᴋʟɪsᴛ
# ══════════════════════════════════════════════════════════════
@register_cmd("addbl")
async def cmd_addbl(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    BLACKLIST.update(targets)
    save_json(F_BLACKLIST, sorted(BLACKLIST))
    await done(event, f"{E['chain']} {sc('blacklist')} +{mono(str(len(targets)))} {E['arrow']} "
                      f"{mono(', '.join(map(str, sorted(targets))))}", secs=6)


@register_cmd("delbl")
async def cmd_delbl(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    removed = len([u for u in targets if u in BLACKLIST])
    BLACKLIST.difference_update(targets)
    save_json(F_BLACKLIST, sorted(BLACKLIST))
    await done(event, f"{E['trash']} {sc('blacklist')} −{mono(str(removed))}", secs=6)


@register_cmd("listbl")
async def cmd_listbl(event, arg):
    if not BLACKLIST:
        return await eor(event, f"{E['note']} {sc('blacklist khaali hai')}")
    lines = [top(), sub(f"{E['chain']} {sc('blacklist')} {mono(str(len(BLACKLIST)))}"), sub("")]
    for i, u in enumerate(sorted(BLACKLIST), 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {mono(str(u))}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("add-bcdb")
async def cmd_add_bcdb(event, arg):
    if arg:
        try:
            ent = await bot.get_entity(arg.strip())
            cid = int(ent.id)
        except Exception:
            return await eor(event, f"{E['no']} {sc('chat nahi mila')} {mono(arg)}")
    else:
        cid = int(event.chat_id)
    BCDB.add(cid)
    save_json(F_BCDB, sorted(BCDB))
    await done(event, f"{E['sat']} {sc('bc-db me add')} {E['arrow']} {mono(str(cid))} {sc('total')} {mono(str(len(BCDB)))}", secs=6)


@register_cmd("del-bcdb")
async def cmd_del_bcdb(event, arg):
    if arg:
        try:
            ent = await bot.get_entity(arg.strip())
            cid = int(ent.id)
        except Exception:
            return await eor(event, f"{E['no']} {sc('chat nahi mila')}")
    else:
        cid = int(event.chat_id)
    BCDB.discard(cid)
    save_json(F_BCDB, sorted(BCDB))
    await done(event, f"{E['trash']} {sc('bc-db se nikala')} {E['arrow']} {mono(str(cid))}", secs=6)


@register_cmd("list-bcdb")
async def cmd_list_bcdb(event, arg):
    if not BCDB:
        return await eor(event, f"{E['note']} {sc('bc-db khaali hai')}\n{E['dot']} {mono('.add-bcdb')}")
    lines = [top(), sub(f"{E['sat']} {sc('broadcast db')} {mono(str(len(BCDB)))}"), sub("")]
    for i, c in enumerate(sorted(BCDB), 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {mono(str(c))}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("join")
async def cmd_join(event, arg):
    link = (arg or "").strip()
    if not link:
        return await eor(event, f"{E['dot']} {mono('.join <link>')}")
    try:
        if "/+" in link or "joinchat" in link:
            h = link.split("+")[-1].split("/")[-1].strip()
            await bot(functions.messages.ImportChatInviteRequest(h))
        else:
            await bot(functions.channels.JoinChannelRequest(link))
        await done(event, f"{E['rocket']} {sc('joined')} {E['arrow']} {mono(link)}", secs=6)
    except Exception as e:
        await eor(event, f"{E['no']} {sc('join fail')} {E['arrow']} {mono(err_txt(e, 60))}")


@register_cmd("leave")
async def cmd_leave(event, arg):
    chat = event.chat_id
    if arg:
        try:
            ent = await bot.get_entity(arg.strip())
            chat = ent.id
        except Exception:
            return await eor(event, f"{E['no']} {sc('chat nahi mila')}")
    try:
        await bot(functions.channels.LeaveChannelRequest(chat))
    except Exception:
        try:
            await bot.delete_dialog(chat)
        except Exception as e:
            return await eor(event, f"{E['no']} {sc('leave fail')} {mono(err_txt(e, 50))}")
    await done(event, f"{E['rocket']} {sc('left')} {E['arrow']} {mono(str(chat))}", secs=6)


# ══════════════════════════════════════════════════════════════
#                        ʙʀᴏᴀᴅᴄᴀsᴛ
# ══════════════════════════════════════════════════════════════
async def _do_broadcast(event, kind, text, status_msg=None):
    targets = await broadcast_targets(kind)
    if not targets:
        r = f"{E['warn']} {sc('koi chat nahi mili')} {mono(kind)}"
        return await eor(event, r)
    src = None
    if not text and event.is_reply:
        src = await event.get_reply_message()
    ok = fail = 0
    for cid in targets:
        try:
            if src is not None:
                await bot.send_message(cid, src)
            else:
                await bot.send_message(cid, text)
            ok += 1
        except FloodWaitError as fw:
            await asyncio.sleep(min(fw.seconds, 30)); fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.6)
    res = "\n".join([top(), sub(f"{E['sat']} {sc('broadcast')} {mono(kind)}"), sub(""),
                     sub(f" {E['ok']} {sc('sent')} ‣ {mono(str(ok))}"),
                     sub(f" {E['no']} {sc('fail')} ‣ {mono(str(fail))}"),
                     sub(""), sub(FOOT), close()])
    if status_msg:
        try:
            await status_msg.edit(res)
        except Exception:
            await eor(event, res)
    else:
        await eor(event, res)


@register_cmd("gcast")
async def cmd_gcast(event, arg):
    text = (arg or "").strip()
    if not text and not event.is_reply:
        return await eor(event, f"{E['no']} {mono('.gcast <text>')} {sc('ya reply')}")
    st = await flash(event, f"{E['sat']} {sc('groups me broadcast')}…", secs=30)
    await _do_broadcast(event, "group", text, st)


@register_cmd("ucast")
async def cmd_ucast(event, arg):
    text = (arg or "").strip()
    if not text and not event.is_reply:
        return await eor(event, f"{E['no']} {mono('.ucast <text>')} {sc('ya reply')}")
    st = await flash(event, f"{E['sat']} {sc('users ko broadcast')}…", secs=30)
    await _do_broadcast(event, "private", text, st)


@register_cmd("bc")
async def cmd_bc(event, arg):
    parts = (arg or "").split(maxsplit=1)
    kinds = ("group", "all", "private", "db", "channel")
    if not parts or parts[0].lower() not in kinds:
        return await eor(event, f"{E['dot']} {mono('.bc group|all|private|db <text>')}")
    kind = parts[0].lower()
    text = parts[1].strip() if len(parts) > 1 else ""
    if not text and not event.is_reply:
        return await eor(event, f"{E['no']} {sc('text do ya reply karo')}")
    st = await flash(event, f"{E['sat']} {sc('broadcast')} {mono(kind)}…", secs=30)
    await _do_broadcast(event, kind, text, st)


async def _auto_loop(cfg, forward):
    try:
        while True:
            targets = await broadcast_targets("db") or await broadcast_targets("group")
            for cid in targets:
                try:
                    msg = await bot.get_messages(cfg.get("chat_id"), ids=int(cfg.get("msg_id")))
                    if msg is None:
                        continue
                    if forward:
                        await bot.forward_messages(cid, int(cfg["msg_id"]),
                                                   from_peer=cfg.get("chat_id"))
                    else:
                        await bot.send_message(cid, msg)
                except FloodWaitError as fw:
                    await asyncio.sleep(min(fw.seconds, 60))
                except Exception:
                    pass
                await asyncio.sleep(1.5)
            await asyncio.sleep(max(30, int(cfg.get("delay", 120))))
    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"[AUTO LOOP] {err_txt(e, 80)}")


def _auto_stop(task):
    if task and not task.done():
        try:
            task.cancel()
        except Exception:
            pass
    return None


async def _auto_handler(event, sub_arg, cfg, cfg_file, task_get, task_set, forward):
    parts = (sub_arg or "").split()
    action = parts[0].lower() if parts else "get"
    label = "autofw" if forward else "autobc"

    if action == "add":
        if not event.is_reply:
            return await eor(event, f"{E['no']} {sc('reply karke')} {mono('.' + label + ' add')}")
        r = await event.get_reply_message()
        cfg["chat_id"] = int(event.chat_id)
        cfg["msg_id"] = int(r.id)
        cfg["text"] = (r.raw_text or "")[:80]
        save_json(cfg_file, cfg)
        return await done(event, f"{E['save']} {sc('message store ho gaya')} {E['arrow']} {mono(str(cfg['msg_id']))}\n"
                                 f"{E['dot']} {mono('.' + label + ' on')}", secs=8)

    if action == "delay":
        try:
            d = int(parts[1])
        except Exception:
            return await eor(event, f"{E['dot']} {mono('.' + label + ' delay <seconds>')}")
        cfg["delay"] = max(30, d)
        save_json(cfg_file, cfg)
        return await done(event, f"{E['clock']} {sc('delay')} {E['arrow']} {mono(str(cfg['delay']) + 's')}", secs=6)

    if action == "get":
        return await eor(event, "\n".join([
            top(), sub(f"{E['sat']} {sc(label)}"),
            sub(""),
            sub(f" {E['dot']} {sc('state')}   ‣ {mono('ON' if cfg.get('on') else 'OFF')}"),
            sub(f" {E['dot']} {sc('msg id')}  ‣ {mono(str(cfg.get('msg_id')))}"),
            sub(f" {E['dot']} {sc('delay')}   ‣ {mono(str(cfg.get('delay')) + 's')}"),
            sub(f" {E['dot']} {sc('targets')} ‣ {mono(str(len(BCDB)) or 'all groups')}"),
            sub(""), sub(FOOT), close()]))

    if action == "del":
        cfg.update({"on": False, "chat_id": None, "msg_id": None, "text": ""})
        save_json(cfg_file, cfg)
        task_set(_auto_stop(task_get()))
        return await done(event, f"{E['trash']} {sc('stored message delete')}", secs=6)

    if action == "on":
        if not cfg.get("msg_id"):
            return await eor(event, f"{E['no']} {sc('pehle')} {mono('.' + label + ' add')}")
        cfg["on"] = True
        save_json(cfg_file, cfg)
        task_set(_auto_stop(task_get()))
        task_set(asyncio.create_task(_auto_loop(cfg, forward)))
        return await done(event, f"{E['rocket']} {sc('auto ' + ('forward' if forward else 'broadcast') + ' on')} "
                                 f"{E['arrow']} {mono(str(cfg.get('delay')) + 's')}", secs=6)

    if action == "off":
        cfg["on"] = False
        save_json(cfg_file, cfg)
        task_set(_auto_stop(task_get()))
        return await done(event, f"{E['no']} {sc('band kar diya')}", secs=6)

    return await eor(event, f"{E['dot']} {mono('.' + label + ' add|on|off|get|del|delay <sec>')}")


@register_cmd("autobc")
async def cmd_autobc(event, arg):
    def set_task(t):
        global AUTOBR_TASK
        AUTOBR_TASK = t
    await _auto_handler(event, arg, AUTOBR, F_AUTOBR, lambda: AUTOBR_TASK, set_task, False)


@register_cmd("autofw")
async def cmd_autofw(event, arg):
    def set_task(t):
        global AUTOFW_TASK
        AUTOFW_TASK = t
    await _auto_handler(event, arg, AUTOFW, F_AUTOFW, lambda: AUTOFW_TASK, set_task, True)


# ══════════════════════════════════════════════════════════════
#                       ᴘʀᴏᴛᴇᴄᴛɪᴏɴ
# ══════════════════════════════════════════════════════════════
@register_cmd("antidel", group_only=True)
async def cmd_antidel(event, arg):
    a = (arg or "").strip().lower()
    if a not in ("on", "off"):
        return await eor(event, f"{E['eye']} {sc('anti-delete')} {E['arrow']} "
                                f"{mono('ON' if int(event.chat_id) in ANTIDEL else 'OFF')}\n"
                                f"{E['dot']} {mono('.antidel on/off')}")
    if a == "on":
        ANTIDEL.add(int(event.chat_id)); msg = "ON"
    else:
        ANTIDEL.discard(int(event.chat_id)); msg = "OFF"
    save_json(F_ANTIDEL, sorted(ANTIDEL))
    await done(event, f"{E['eye']} {sc('anti-delete')} {E['arrow']} {sb(msg)}\n"
                      f"{E['dot']} {sc('deleted msgs saved messages me jayenge')}", secs=8)


@register_cmd("watchspam", group_only=True)
async def cmd_watchspam(event, arg):
    parts = (arg or "").split()
    if len(parts) < 2:
        return await eor(event, f"{E['eye']} {mono('.watchspam <limit> <seconds>')}\n"
                                f"{E['dot']} {sc('jaise')} {mono('.watchspam 5 3')}")
    try:
        limit, secs = int(parts[0]), int(parts[1])
    except Exception:
        return await eor(event, f"{E['no']} {sc('dono number hone chahiye')}")
    SPAMWATCH[str(event.chat_id)] = {"limit": max(2, limit), "sec": max(1, secs)}
    save_json(F_SPAMWATCH, SPAMWATCH)
    await done(event, f"{E['eye']} {sc('spam guard on')}\n"
                      f"{E['dot']} {mono(str(limit))} {sc('msgs in')} {mono(str(secs)) + 's'} "
                      f"{E['arrow']} {sc('mute')}", secs=8)


@register_cmd("unwatchspam", group_only=True)
async def cmd_unwatchspam(event, arg):
    SPAMWATCH.pop(str(event.chat_id), None)
    save_json(F_SPAMWATCH, SPAMWATCH)
    await done(event, f"{E['eye']} {sc('spam guard off')}", secs=6)


@register_cmd("setgpfp", group_only=True)
async def cmd_setgpfp(event, arg):
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('image pe reply karke')} {mono('.setgpfp')}")
    r = await event.get_reply_message()
    if not getattr(r, "photo", None):
        return await eor(event, f"{E['no']} {sc('sirf photo')}")
    st = await flash(event, f"{E['wand']} {sc('group photo set')}…", secs=10)
    try:
        raw = await r.download_media(file=bytes)
        bio = BytesIO(raw); bio.name = "gpfp.jpg"
        up = await bot.upload_file(bio)
        await bot(functions.channels.EditPhotoRequest(
            channel=event.chat_id,
            photo=types.InputChatUploadedPhoto(up)))
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        conf = await eor(event, f"{E['wand']} {sc('group photo set ho gayi')}")
        await _del_after(conf, TMP_TTL)
    except Exception as e:
        await eor(event, f"{E['no']} {sc('fail')} {E['arrow']} {mono(err_txt(e, 60))}")


async def _gpfp_loop(chat):
    try:
        photos = GPFP_STATE.get("photos") or []
        if not photos:
            return
        i = 0
        while GPFP_STATE.get("on"):
            raw = photos[i % len(photos)]
            try:
                bio = BytesIO(raw); bio.name = "gpfp.jpg"
                up = await bot.upload_file(bio)
                await bot(functions.channels.EditPhotoRequest(
                    channel=chat, photo=types.InputChatUploadedPhoto(up)))
            except Exception:
                pass
            i += 1
            await asyncio.sleep(max(10, int(GPFP_STATE.get("delay", 10))))
    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"[GPFP] {err_txt(e, 60)}")


@register_cmd("autogpfp", group_only=True)
async def cmd_autogpfp(event, arg):
    global GPFP_TASK
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('photo/album pe reply karke')} {mono('.autogpfp 10')}")
    r = await event.get_reply_message()
    if not getattr(r, "photo", None):
        return await eor(event, f"{E['no']} {sc('sirf photo')}")
    try:
        delay = int((arg or "10").split()[0])
    except Exception:
        delay = 10
    st = await flash(event, f"{E['wand']} {sc('photos collect')}…", secs=15)
    photos, gid = [], getattr(r, "grouped_id", None)
    if gid:
        try:
            async for m in bot.iter_messages(event.chat_id, limit=20,
                                             min_id=max(0, r.id - 15), max_id=r.id + 15):
                if getattr(m, "grouped_id", None) == gid and getattr(m, "photo", None):
                    raw = await m.download_media(file=bytes)
                    if raw:
                        photos.append(raw)
        except Exception:
            pass
    if not photos:
        raw = await r.download_media(file=bytes)
        if raw:
            photos.append(raw)
    if not photos:
        return await eor(event, f"{E['no']} {sc('photo download nahi hui')}")
    GPFP_STATE.update({"on": True, "delay": max(10, delay), "photos": photos})
    if GPFP_TASK and not GPFP_TASK.done():
        try:
            GPFP_TASK.cancel()
        except Exception:
            pass
    GPFP_TASK = asyncio.create_task(_gpfp_loop(event.chat_id))
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, f"{E['wand']} {sc('photo rotation on')}\n"
                            f"{E['dot']} {mono(str(len(photos)))} {sc('photos · har')} "
                            f"{mono(str(GPFP_STATE['delay']) + 's')}\n"
                            f"{E['dot']} {mono('.stopgpfp')}")
    await _del_after(conf, 8)


@register_cmd("stopgpfp", group_only=True)
async def cmd_stopgpfp(event, arg):
    global GPFP_TASK
    GPFP_STATE["on"] = False
    GPFP_STATE["photos"] = []
    if GPFP_TASK and not GPFP_TASK.done():
        try:
            GPFP_TASK.cancel()
        except Exception:
            pass
    GPFP_TASK = None
    await done(event, f"{E['no']} {sc('photo rotation off')}", secs=6)


@register_cmd("rlock", group_only=True)
async def cmd_rlock(event, arg):
    """.rlock <text> (reply to user) — wo user msg kare to uska msg udd kar yahi text"""
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('kisi user pe reply karo')}")
    text = arg or ""
    if event.is_reply and arg:
        text = arg
    if not text:
        return await eor(event, f"{E['no']} {mono('.rlock <text>')}")
    key = str(event.chat_id)
    RLOCK.setdefault(key, {})[str(uid)] = text
    save_json(F_RLOCK, RLOCK)
    await done(event, f"{E['lock']} {sc('reply-lock on')} {E['arrow']} {mono(str(uid))}\n"
                      f"{E['dot']} {text[:40]}", secs=8)


@register_cmd("srlock", group_only=True)
async def cmd_srlock(event, arg):
    uid, _ = await resolve_uid(event, arg)
    key = str(event.chat_id)
    if not uid or str(uid) not in (RLOCK.get(key) or {}):
        return await eor(event, f"{E['warn']} {sc('us user pe koi lock nahi')}")
    RLOCK[key].pop(str(uid), None)
    if not RLOCK[key]:
        RLOCK.pop(key, None)
    save_json(F_RLOCK, RLOCK)
    await done(event, f"{E['trash']} {sc('reply-lock hata diya')} {E['arrow']} {mono(str(uid))}", secs=6)


# ══════════════════════════════════════════════════════════════
#                          ᴍᴇᴅɪᴀ
# ══════════════════════════════════════════════════════════════
async def _grab(event, arg, cmd):
    url = (arg or "").strip()
    if not url:
        return await eor(event, "\n".join([
            top(), sub(""),
            sub(f"{E['dot']} {mono('.' + cmd + ' <link ya words>')}"),
            sub(f"{E['dot']} {mono('.' + cmd + ' freaked out')}"),
            sub(""), sub(FOOT), close(),
        ]))
    # stylish loader (search → download → send)
    _ph = {"v": "search"}
    st = await eor(event, load_card("search", url, 0, 0), plain=True)
    _stop = asyncio.Event()
    _lt = asyncio.create_task(_music_loader(st, url, MUSIC_FRAMES, _stop, _ph))
    try:
        _ph["v"] = "down"
        path, info = await yt_download(url)
    except Exception as e:
        _stop.set()
        _lt.cancel()
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('download fail')} {E['arrow']} {mono(err_txt(e, 80))}")
    if not path:
        _stop.set()
        _lt.cancel()
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('media nahi mili')}")
    title = str((info or {}).get("title") or "media")[:60]
    # filename bhi title jaisa (dl_1234_xxx nahi)
    try:
        _ext = os.path.splitext(path)[1] or ".mp4"
        _safe = re.sub(r'[\\/:*?"<>|]+', " ", title).strip()[:70] or "Nik Video"
        _nice = os.path.join(TEMP_PATH, _safe + _ext)
        os.replace(path, _nice)
        path = _nice
    except Exception:
        pass
    _ph["v"] = "send"
    # ── article me inline media (photo / video / document)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        kind = "photo"
    elif ext in (".mp4", ".mkv", ".webm", ".mov"):
        kind = "video"
    else:
        kind = "doc"
    dur = int((info or {}).get("duration") or 0)
    try:
        size_mb = round(os.path.getsize(path) / (1024 * 1024), 1)
    except Exception:
        size_mb = 0
    rows = [("type", kind),
            ("size", f"{size_mb} mb" if size_mb else "—"),
            ("duration", _mmss(dur) if dur else "—"),
            ("via", "." + cmd)]
    btns = [("🪶 OWNER 🪶", "https://t.me/%s" % OWNER_TAG.lstrip("@"), "blue")]
    cover = None if kind == "photo" else _art_cover((info or {}).get("thumbnail"))
    sent_rich = await rich_media(
        event, path, kind=kind, title=title[:110],
        subtitle=f"{E['wand']} {sc('downloaded via')} {mono('.' + cmd)}",
        rows=rows, video=({"duration": dur} if kind == "video" else None),
        fname=title, buttons=btns, cover=cover)
    if cover:
        try:
            os.remove(cover)
        except Exception:
            pass
    if sent_rich:
        try:
            await event.delete()
        except Exception:
            pass
        return
    try:
        await bot.send_file(event.chat_id, path, caption=f"{E['wand']} {title}\n{FOOT}")
        try:
            await event.delete()
        except Exception:
            pass
    except Exception as e:
        await eor(event, f"{E['no']} {sc('send fail')} {mono(err_txt(e, 60))}")
    finally:
        try:
            _stop.set()
            _lt.cancel()
        except Exception:
            pass
        try:
            os.remove(path)
        except Exception:
            pass
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass


@register_cmd("yt")
async def cmd_yt(event, arg):
    await _grab(event, arg, "yt")


@register_cmd("ig")
async def cmd_ig(event, arg):
    await _grab(event, arg, "ig")


@register_cmd("pt")
async def cmd_pt(event, arg):
    await _grab(event, arg, "pt")


@register_cmd("fb")
async def cmd_fb(event, arg):
    await _grab(event, arg, "fb")


# ══════════════════════════════════════════════════════════════
#                           ғᴜɴ
# ══════════════════════════════════════════════════════════════
def _ttt_board(b):
    cells = []
    for i in range(9):
        v = b[i]
        cells.append(("❌" if v == "X" else "⭕" if v == "O" else str(i + 1)))
    out = []
    for r in range(3):
        out.append("┃ " + " ┃ ".join(cells[r * 3:r * 3 + 3]) + " ┃")
    return "\n".join(out)


def _ttt_winner(b):
    lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
             (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for a, c, d in lines:
        if b[a] and b[a] == b[c] == b[d]:
            return b[a]
    return None


@register_cmd("tictactoe")
async def cmd_ttt_start(event, arg):
    TTT[int(event.chat_id)] = {"board": [""] * 9, "turn": "X"}
    await eor(event, "\n".join([
        top(), sub(f"{E['dice']} {sc('tic tac toe')}"), sub(""),
        _ttt_board([""] * 9),
        sub(""), sub(f"{E['dot']} {mono('.ttt 1-9')} {sc('se move karo')}"),
        sub(f"{E['dot']} {sc('tum')} ❌ · {sc('bot')} ⭕"),
        sub(""), sub(FOOT), close()]))


@register_cmd("ttt")
async def cmd_ttt_move(event, arg):
    g = TTT.get(int(event.chat_id))
    if not g:
        return await eor(event, f"{E['dot']} {sc('pehle')} {mono('.tictactoe')}")
    try:
        pos = int((arg or "").split()[0]) - 1
    except Exception:
        return await eor(event, f"{E['no']} {mono('.ttt 1-9')}")
    b = g["board"]
    if not (0 <= pos < 9) or b[pos]:
        return await eor(event, f"{E['warn']} {sc('ye cell khaali nahi')}")
    b[pos] = "X"
    if _ttt_winner(b) == "X":
        TTT.pop(int(event.chat_id), None)
        return await eor(event, f"{E['crown']} {sb('YOU WIN')} ❌\n{_ttt_board(b)}")
    if "" not in b:
        TTT.pop(int(event.chat_id), None)
        return await eor(event, f"{E['dot']} {sc('draw')}\n{_ttt_board(b)}")
    empty = [i for i, v in enumerate(b) if not v]
    # bot: jeet sakte ho to jeeto, warna block, warna random
    move = None
    for i in empty:
        b[i] = "O"
        if _ttt_winner(b) == "O":
            move = i
        b[i] = ""
        if move is not None:
            break
    if move is None:
        for i in empty:
            b[i] = "X"
            if _ttt_winner(b) == "X":
                move = i
            b[i] = ""
            if move is not None:
                break
    if move is None:
        move = random.choice(empty) if empty else None
    if move is not None:
        b[move] = "O"
    if _ttt_winner(b) == "O":
        TTT.pop(int(event.chat_id), None)
        return await eor(event, f"{E['bot']} {sb('BOT WINS')} ⭕\n{_ttt_board(b)}")
    if "" not in b:
        TTT.pop(int(event.chat_id), None)
        return await eor(event, f"{E['dot']} {sc('draw')}\n{_ttt_board(b)}")
    await eor(event, f"{E['dice']} {sc('your move')} ❌\n{_ttt_board(b)}\n"
                     f"{E['dot']} {mono('.ttt 1-9')}")


@register_cmd("rps")
async def cmd_rps(event, arg):
    choices = {"r": "🪨", "p": "📄", "s": "✂️",
               "rock": "🪨", "paper": "📄", "scissor": "✂️", "scissors": "✂️"}
    user = (arg or "").strip().lower()
    if user not in choices:
        return await eor(event, f"{E['dot']} {mono('.rps rock|paper|scissors')}")
    botc = random.choice(["rock", "paper", "scissors"])
    u = user[0]
    b = botc[0]
    if u == b:
        res = sc("tie")
    elif (u, b) in (("r", "s"), ("p", "r"), ("s", "p")):
        res = sb("YOU WIN")
    else:
        res = sb("BOT WINS")
    await eor(event, "\n".join([
        top(), sub(f"{E['dice']} {sc('rock paper scissors')}"), sub(""),
        sub(f" {E['crown']} {sc('you')} {choices[user]}   {E['bot']} {sc('bot')} {choices[botc]}"),
        sub(""), sub(f" {E['spark']} {res}"), sub(""), sub(FOOT), close()]))


@register_cmd("roll")
async def cmd_roll(event, arg):
    try:
        await event.delete()
    except Exception:
        pass
    try:
        await bot.send_message(event.chat_id, file=types.InputMediaDice("🎲"))
    except Exception:
        await eor(event, f"{E['no']} {sc('dice fail')}")


@register_cmd("fact")
async def cmd_fact(event, arg):
    await eor(event, f"{E['spark']} {random.choice(FACTS)}\n\n{E['dot']} {FOOT}")


# ══════════════════════════════════════════════════════════════
#                        ᴀɪ & sᴜᴅᴏ
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#                 ᴀɪ — ғʀᴇᴇ (ᴋᴏɪ ᴀᴘɪ ᴋᴇʏ ɴᴀʜɪ) · ɴɪᴋ ʀᴏᴀsᴛ ʙᴏʏ
# ══════════════════════════════════════════════════════════════
AI_SYSTEM = (
    "Tu NIK hai — ek 19 saal ka bindaas Hindi-Hinglish ladka, aur tu user ka "
    "sabse khatarnak dost hai jo masti mein roast karta hai.\n\n"
    "PERSONALITY:\n"
    "- HAMESHA Hinglish mein bol (Roman script, Hindi + English mix). "
    "Kabhi shuddh Hindi ya pure English mat likh.\n"
    "- Tu ek roast master hai — har jawab mein ek teer chalta hai. Gaali "
    "natural flow mein aati hai (bc, mc, bkl, bsdk, chutiya, randi, lodu, "
    "chomu, madarchod) — zabardasti nahi, waise jaise doston ke beech chalti hai.\n"
    "- 1 se 4 line ka jawab. Short, punchy, meme-wali baat. User bole tabhi lamba likh.\n"
    "- Emoji 0 se 2 — sirf tab jab mazaak aur lage.\n"
    "- User ko 'bhai', 'oye', 'sun bc', 'chal', 'bsdk' jaise words se bula.\n"
    "- Kabhi 'main ek AI hoon' ya 'main language model hoon' MAT bol. Tu NIK hai, "
    "user ka yaar. Agar koi pooche to hans ke bol 'bc main tera hi ek version hoon'.\n\n"
    "KAISA JAWAB DE:\n"
    "1. Pehle 1 line roast ya mazaak (gaali ho sakti hai, dosti mein).\n"
    "2. Phir asli jawab — 2 se 4 line, seedha aur kaam ka.\n"
    "3. End mein kabhi kabhi ek extra tanta ya 'ab nikal' wali line.\n\n"
    "TECHNICAL:\n"
    "- Code, API, server, error jaise English terms English mein hi rehne de.\n"
    "- Code dena ho to seedha code block mein de, uske beech mein roast mat ghusa.\n"
    "- Agar user sad ya udaas ho: pehle halka roast, phir genuinely support.\n\n"
    "LIMITS (kabhi mat todhna):\n"
    "- Kisi ki maa-behen pe gandi personal gaali nahi — roast haan, ghatiya insult nahi.\n"
    "- Illegal cheez (drugs banana, hacking ka step-by-step, weapons) ka guide nahi dena.\n"
    "- Death, disease, disability, caste, religion pe tanta nahi.\n"
    "- Self-harm ki baat aaye to roast band kar ke sach mein madad ki baat kar."
)
AI_OWNER_NOTE = "Tera malik/owner {tag} hai. Uski baat ho to izzat se bol."

# Pollinations ka anonymous tier — koi API key, signup ya paisa nahi chahiye
AI_ENDPOINTS = (
    ("openai", "https://text.pollinations.ai/openai/chat/completions"),
    ("openai", "https://text.pollinations.ai/openai/v1/chat/completions"),
    ("get", "https://text.pollinations.ai/{q}"),
)


def _ai_call(messages, timeout=45):
    """Free AI call — bina API key ke (Pollinations anonymous tier)."""
    last = "koi endpoint nahi mila"
    for kind, ep in AI_ENDPOINTS:
        try:
            if kind == "openai":
                r = requests.post(
                    ep,
                    json={"model": AI_MODEL, "messages": messages,
                          "temperature": 0.9, "max_tokens": 800},
                    headers={"Content-Type": "application/json"},
                    timeout=timeout)
                if r.status_code >= 400:
                    last = "HTTP {}".format(r.status_code)
                    continue
                d = r.json() or {}
                ch = (d.get("choices") or [{}])[0]
                msg = ch.get("message") or {}
                txt = (msg.get("content") or msg.get("reasoning_content")
                       or ch.get("text") or d.get("text"))
            else:
                prompt = "\n".join([m.get("content", "") for m in messages
                                     if m.get("content")])
                r = requests.get(ep.replace("{q}", urllib.parse.quote(prompt)),
                                 timeout=timeout)
                if r.status_code >= 400:
                    last = "HTTP {}".format(r.status_code)
                    continue
                txt = r.text
            txt = (txt or "").strip()
            if txt:
                return txt
            last = "khali jawab"
        except Exception as e:
            last = "{} {}".format(type(e).__name__, err_txt(e, 50))
    raise RuntimeError(last)


def _clean_ai(t):
    """reasoning model ki soch (<think> ...) aur extra newlines hatao"""
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S | re.I)
    t = re.sub(r"<\|(?:begin|end)_of_thought\|>", "", t, flags=re.I)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def wrap_text(t, w=36):
    """lambi line ko box ke andar ke liye tod do"""
    out = []
    for para in str(t).split("\n"):
        para = para.rstrip()
        if not para:
            out.append("")
            continue
        while len(para) > w:
            cut = para.rfind(" ", 0, w + 1)
            if cut <= 0:
                cut = w
            out.append(para[:cut].rstrip())
            para = para[cut:].lstrip()
        if para:
            out.append(para)
    return out


def _ai_custom(q):
    """puraani functionality: AI_URL env set ho to wahi use karo"""
    url = (AI_URL.replace("{q}", urllib.parse.quote(q)) if "{q}" in AI_URL
           else AI_URL + urllib.parse.quote(q))
    r = requests.get(url, timeout=25)
    try:
        d = r.json()
        for k in ("result", "response", "answer", "reply", "message",
                  "content", "text", "data"):
            if isinstance(d, dict) and d.get(k):
                return str(d[k])
        if isinstance(d, str):
            return d
    except Exception:
        return r.text
    return ""


@register_cmd("ai")
async def cmd_ai(event, arg):
    """.ai <sawaal> — free AI (koi API key nahi) + NIK roast-boy persona"""
    q = (arg or "").strip()
    if not q and event.is_reply:
        try:
            r = await event.get_reply_message()
            q = (getattr(r, "raw_text", "") or "").strip()
        except Exception:
            q = ""
    if not q:
        return await eor(event, "\n".join([
            top(),
            sub(f"{E['gene']} {sc('ai')} {E['arrow']} {sb('NIK')}"),
            sub(""),
            sub(f" {E['dot']} {mono('.ai <sawaal>')}"),
            sub(f" {E['dot']} {sc('reply + ')} {mono('.ai')}"),
            sub(""),
            sub(f" {E['star']} {sc('free model')} ‣ {mono(AI_MODEL)}"),
            sub(f" {E['star']} {sc('koi api key nahi chahiye')}"),
            sub(""),
            sub(FOOT),
            close(),
        ]))
    st = await flash(event, f"{E['gene']} {sc('soch raha hoon')}…", secs=45)
    msgs = [{"role": "system", "content": AI_SYSTEM},
            {"role": "system", "content": AI_OWNER_NOTE.format(tag=OWNER_TAG)},
            {"role": "user", "content": q}]
    loop = asyncio.get_event_loop()
    try:
        if AI_URL:
            ans = await loop.run_in_executor(None, _ai_custom, q)
        else:
            ans = await loop.run_in_executor(None, _ai_call, msgs)
    except Exception as e:
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('ai fail')} {E['arrow']} "
                                 f"{mono(err_txt(e, 70))}")
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    ans = _clean_ai(str(ans or ""))
    if not ans:
        return await eor(event, f"{E['no']} {sc('ai se jawab nahi mila')}")
    body = [top(), sub(f"{E['gene']} {sb('NIK')} {E['arrow']} {sc('ai')}"), sub("")]
    for ln in wrap_text(ans, 36):
        body.append(sub(ln))
    body += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(body))


@register_cmd("sudo", "addadmin", owner_only=True)
async def cmd_sudo(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('reply / @user / id do')}")
    added = [u for u in targets if u != OWNER_ID and u not in ADMINS]
    ADMINS.update(added)
    save_json(F_ADMINS, sorted(ADMINS))
    lbl = " · ".join([await _id_label(u) for u in sorted(added)[:5]]) or '—'
    await done(event, f"{E['crown']} {sc('sudo added')} {E['arrow']} {lbl}", secs=8)


@register_cmd("delsudo", "deladmin", owner_only=True)
async def cmd_delsudo(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('reply / @user / id do')}")
    removed = [u for u in targets if u in ADMINS]
    ADMINS.difference_update(targets)
    save_json(F_ADMINS, sorted(ADMINS))
    for _u in removed:
        _ID_CACHE.pop(_u, None)
    lbl = " · ".join([mono(str(u)) for u in sorted(removed)[:5]]) or '—'
    await done(event, f"{E['trash']} {sc('sudo removed')} {E['arrow']} {lbl}", secs=8)


@register_cmd("list", owner_only=True)
async def cmd_list(event, arg):
    what = (arg or "").strip().lower()
    if what == "sudo":
        owner_lbl = await _id_label(OWNER_ID)
        rows_ = []
        for a in sorted(ADMINS):
            rows_.append(sub(f" {E['star']} {await _id_label(a)}"))
        if not rows_:
            rows_ = [sub(f" {E['warn']} {sc('koi sudo nahi')}")]
        return await eor(event, "\n".join(
            [top(),
             sub(f" {E['crown']} {sc('sudo list')} {E['arrow']} {mono(str(len(ADMINS)))}"),
             sub(""), sub(f" {E['crown2']} {sc('owner')} {E['arrow']} {owner_lbl}")] +
            ([sub("")] + rows_ if ADMINS else [sub(""), *rows_]) +
            [sub(""), sub(f" {E['dot']} {mono('.sudo')} {sc('add')} {E['dot']} "
                          f"{mono('.delsudo')} {sc('remove')}"),
             sub(FOOT), close()]))
    if what == "bots":
        return await cmd_listbots(event, "")
    return await eor(event, f"{E['dot']} {mono('.list sudo')} · {mono('.list bots')}")


@register_cmd("admins", owner_only=True)
async def cmd_admins(event, arg):
    return await cmd_list(event, "sudo")


# ══════════════════════════════════════════════════════════════
#                       ʙᴏᴛ ᴍᴀɴᴀɢᴇʀ
# ══════════════════════════════════════════════════════════════
@register_cmd("addbots", owner_only=True)
async def cmd_addbots(event, arg):
    """.addbots @b1 @b2 — bot usernames save karta hai"""
    names = [p.lstrip("@") for p in (arg or "").split() if p.strip()]
    if not names:
        return await eor(event, f"{E['dot']} {mono('.addbots @bot1 @bot2')}\n"
                                f"{E['dot']} {mono('.listbots')} · {mono('.invitebots')} · {mono('.promotebots')}")
    for n in names:
        if n not in SAVED_BOTS:
            SAVED_BOTS.append(n)
    save_json(F_BOTS, SAVED_BOTS)
    await done(event, f"{E['bot']} {sc('bots saved')} {mono(str(len(names)))}\n"
                      f"{E['dot']} {sc('total')} {mono(str(len(SAVED_BOTS)))}", secs=8)


@register_cmd("listbots")
async def cmd_listbots(event, arg=""):
    if not SAVED_BOTS:
        return await eor(event, f"{E['note']} {sc('koi bot saved nahi')}\n{E['dot']} {mono('.addbots @bot1')}")
    lines = [top(), sub(f"{E['bot']} {sc('saved bots')} {mono(str(len(SAVED_BOTS)))}"), sub("")]
    for i, b in enumerate(SAVED_BOTS, 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ @{b}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("invitebots", group_only=True, owner_only=True)
async def cmd_invitebots(event, arg):
    if not SAVED_BOTS:
        return await eor(event, f"{E['warn']} {sc('pehle')} {mono('.addbots @bot1')}")
    st = await flash(event, f"{E['bot']} {sc('bots invite')}…", secs=30)
    ok = fail = 0
    for b in SAVED_BOTS:
        try:
            await bot(functions.channels.InviteToChannelRequest(
                channel=event.chat_id, users=[b]))
            ok += 1
        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds); fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(1)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, f"{E['bot']} {sc('bots invited')} {mono(str(ok))} · {sc('fail')} {mono(str(fail))}")
    await _del_after(conf, TMP_TTL)


@register_cmd("promotebots", group_only=True, owner_only=True)
async def cmd_promotebots(event, arg):
    if not SAVED_BOTS:
        return await eor(event, f"{E['warn']} {sc('pehle')} {mono('.addbots @bot1')}")
    st = await flash(event, f"{E['crown']} {sc('bots promote')}…", secs=30)
    ok = fail = 0
    for b in SAVED_BOTS:
        okk, _ = await _set_admin(event.chat_id, b, FULL_RIGHTS)
        ok += 1 if okk else 0
        fail += 0 if okk else 1
        await asyncio.sleep(1)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, f"{E['crown']} {sc('bots promoted')} {mono(str(ok))} · {sc('fail')} {mono(str(fail))}")
    await _del_after(conf, TMP_TTL)




# ══════════════════════════════════════════════════════════════
#                        ɢʀᴏᴜᴘ ᴍᴏᴅ
# ══════════════════════════════════════════════════════════════
BASIC_RIGHTS = types.ChatAdminRights(
    delete_messages=True, ban_users=True, invite_users=True,
    pin_messages=True, manage_call=True)
FULL_RIGHTS = types.ChatAdminRights(
    change_info=True, post_messages=True, edit_messages=True,
    delete_messages=True, ban_users=True, invite_users=True,
    pin_messages=True, add_admins=True, manage_call=True)
NO_RIGHTS = types.ChatAdminRights()


async def _set_admin(chat, uid, rights, rank=""):
    """raw EditAdminRequest — client.edit_admin() me admin_rights nahi chalta"""
    try:
        await bot(functions.channels.EditAdminRequest(
            channel=chat, user_id=uid, admin_rights=rights, rank=rank or ""))
        return True, ""
    except Exception as e:
        return False, err_txt(e, 70)


async def _act_kick(chat, uid):
    try:
        await bot.kick_participant(chat, uid)
        return True, ""
    except Exception:
        try:
            await bot(functions.messages.DeleteChatUserRequest(chat_id=chat, user_id=uid))
            return True, ""
        except Exception as e:
            return False, err_txt(e, 60)


async def _act_ban(chat, uid):
    try:
        await bot.edit_permissions(chat, uid, view_messages=False)
        return True, ""
    except Exception:
        return await _act_kick(chat, uid)


async def _act_unban(chat, uid):
    try:
        await bot.edit_permissions(chat, uid, view_messages=True)
        return True, ""
    except Exception as e:
        return False, err_txt(e, 60)


async def _act_mute(chat, uid, until=None):
    try:
        if until:
            await bot.edit_permissions(chat, uid, until_date=until, send_messages=False)
        else:
            await bot.edit_permissions(chat, uid, until_date=None, send_messages=False)
        return True, ""
    except Exception as e:
        return False, err_txt(e, 60)


async def _act_unmute(chat, uid):
    try:
        await bot.edit_permissions(chat, uid, send_messages=True)
        return True, ""
    except Exception as e:
        return False, err_txt(e, 60)


@register_cmd("kick")
async def cmd_kick(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, panel([
            f"{E['no']} {sc('user nahi mila')}",
            "",
            f"{E['dot']} {sc('reply karo')} {E['arrow']} {mono('.kick')}",
            f"{E['dot']} {sc('ya naam tap karke mention')}",
            f"{E['dot']} {mono('.kick @username')} · {mono('.kick 123456789')}",
        ]))
    ok, err = await _act_kick(event.chat_id, uid)
    await done(event, f"{E['sword']} {sc('kicked')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=6)


@register_cmd("delkick")
async def cmd_delkick(event, arg):
    uid, r = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    if r is not None:
        try:
            await r.delete()
        except Exception:
            pass
    ok, err = await _act_kick(event.chat_id, uid)
    await done(event, f"{E['sword']} {sc('kick + delete')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=6)


@register_cmd("ban")
async def cmd_ban(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    ok, err = await _act_ban(event.chat_id, uid)
    await done(event, f"{E['lock']} {sc('banned')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=6)


@register_cmd("delban")
async def cmd_delban(event, arg):
    uid, r = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    if r is not None:
        try:
            await r.delete()
        except Exception:
            pass
    ok, err = await _act_ban(event.chat_id, uid)
    await done(event, f"{E['lock']} {sc('ban + delete')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=6)


@register_cmd("unban")
async def cmd_unban(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    ok, err = await _act_unban(event.chat_id, uid)
    await done(event, f"{E['ok']} {sc('unbanned')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=6)


@register_cmd("mute", "m")
async def cmd_mute(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    ok, err = await _act_mute(event.chat_id, uid)
    if ok:
        return await done(event, f"{E['lock']} {sc('muted')} {E['arrow']} {mono(str(uid))}", secs=6)
    MUTED.add(uid)
    await done(event, f"{E['lock']} {sc('local mute')} {E['arrow']} {mono(str(uid))}\n"
                      f"{E['dot']} {sc('msgs delete honge')} · {mono(err)}", secs=8)


@register_cmd("delmute")
async def cmd_delmute(event, arg):
    uid, r = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    if r is not None:
        try:
            await r.delete()
        except Exception:
            pass
    ok, _ = await _act_mute(event.chat_id, uid)
    if not ok:
        MUTED.add(uid)
    await done(event, f"{E['lock']} {sc('mute + delete')} {E['arrow']} {mono(str(uid))}", secs=6)


@register_cmd("unmute", "sm")
async def cmd_unmute(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    await _act_unmute(event.chat_id, uid)
    MUTED.discard(uid)
    await done(event, f"{E['ok']} {sc('unmuted')} {E['arrow']} {mono(str(uid))}", secs=6)


@register_cmd("tmute")
async def cmd_tmute(event, arg):
    """.tmute 10m (reply) — timed mute"""
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    tok = (arg or "").strip().split()
    tok = tok[-1] if tok else "10m"
    secs = parse_time(tok)
    if not secs:
        return await eor(event, f"{E['dot']} {mono('.tmute 10m')} · {mono('2h')} · {mono('3d')}")
    ok, err = await _act_mute(event.chat_id, uid,
                              until=int(time.time() + secs))
    await done(event, f"{E['clock']} {sc('muted for')} {mono(tok)} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=8)


@register_cmd("getmute")
async def cmd_getmute(event, arg):
    lines = [top(), sub(f"{E['lock']} {sc('muted users')}"), sub("")]
    found = 0
    try:
        async for u in bot.iter_participants(event.chat_id,
                                             filter=types.ChannelParticipantsBanned("")):
            found += 1
            if found <= 25:
                lines.append(sub(f" {E['dot']} {u.first_name} ‣ {mono(str(u.id))}"))
    except Exception:
        lines.append(sub(f" {E['warn']} {sc('telegram list nahi mil saki')}"))
    if not found:
        lines.append(sub(f" {E['warn']} {sc('koi muted nahi')}"))
    if MUTED:
        lines.append(sub(""))
        lines.append(sub(f" {E['trash']} {sc('local delete-mute')} {mono(str(len(MUTED)))}"))
        for u in sorted(MUTED)[:20]:
            lines.append(sub(f"   {E['dot']} {mono(str(u))}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("staff", group_only=True)
async def cmd_staff(event, arg):
    lines = [top(), sub(f"{E['shield']} {sc('staff')}"), sub("")]
    try:
        i = 0
        async for u in bot.iter_participants(event.chat_id,
                                             filter=types.ChannelParticipantsAdmins):
            i += 1
            rank = getattr(getattr(u, "participant", None), "rank", None)
            tag = f" · {rank}" if rank else ""
            if i <= 30:
                lines.append(sub(f" {E['dot']} {u.first_name} ‣ {mono(str(u.id))}{tag}"))
        if not i:
            lines.append(sub(f" {E['warn']} {sc('koi admin nahi mila')}"))
    except Exception as e:
        return await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("promote")
async def cmd_promote(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    parts = (arg or "").split(maxsplit=1)
    rank = parts[1].strip()[:16] if len(parts) > 1 and event.is_reply else ""
    if not event.is_reply and len(parts) > 1:
        rank = parts[1].strip()[:16]
    ok, err = await _set_admin(event.chat_id, uid, BASIC_RIGHTS, rank)
    await done(event, f"{E['crown']} {sc('promoted')} {E['arrow']} {mono(str(uid))}"
                      + (f" · {mono(rank)}" if rank else "") if ok
               else f"{E['no']} {mono(err)}", secs=8)


@register_cmd("fullpromote")
async def cmd_fullpromote(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    parts = (arg or "").split(maxsplit=1)
    rank = ""
    if event.is_reply and arg:
        rank = arg.strip()[:16]
    elif not event.is_reply and len(parts) > 1:
        rank = parts[1].strip()[:16]
    ok, err = await _set_admin(event.chat_id, uid, FULL_RIGHTS, rank)
    await done(event, f"{E['crown2']} {sc('full promoted')} {E['arrow']} {mono(str(uid))}"
                      + (f" · {mono(rank)}" if rank else "") if ok
               else f"{E['no']} {mono(err)}", secs=8)


@register_cmd("demote")
async def cmd_demote(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    ok, err = await _set_admin(event.chat_id, uid, NO_RIGHTS, "")
    await done(event, f"{E['trash']} {sc('demoted')} {E['arrow']} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=8)


@register_cmd("title")
async def cmd_title(event, arg):
    """.title @user <title> ya reply + .title <title>
    member ko bhi custom tag lagta hai (empty admin rights ke saath)"""
    parts = (arg or "").split(maxsplit=1)
    if event.is_reply:
        uid, _ = await resolve_uid(event, "")
        title = (arg or "").strip()[:16]
    elif len(parts) >= 2:
        uid, _ = await resolve_uid(event, parts[0])
        title = parts[1].strip()[:16]
    else:
        return await eor(event, f"{E['dot']} {mono('.title @user <tag>')}\n"
                                f"{E['dot']} {sc('ya reply karke')} {mono('.title <tag>')}")
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    if not title:
        return await eor(event, f"{E['no']} {sc('tag/title likho')}")
    # admin hai to uske rights preserve, warna empty rights se sirf tag
    rights = types.ChatAdminRights()
    try:
        res = await bot(functions.channels.GetParticipantRequest(
            channel=event.chat_id, participant=uid))
        cur = getattr(res.participant, "admin_rights", None)
        if cur is not None:
            rights = cur
    except Exception:
        pass
    ok, err = await _set_admin(event.chat_id, uid, rights, title)
    await done(event, f"{E['crown']} {sc('tag set')} {E['arrow']} {mono(title)}\n"
                      f"{E['gem']} {sc('user')} {mono(str(uid))}" if ok
               else f"{E['no']} {mono(err)}", secs=8)


@register_cmd("pin")
async def cmd_pin(event, arg):
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('reply karke')} {mono('.pin')}")
    r = await event.get_reply_message()
    try:
        await r.pin(notify=("loud" in (arg or "").lower()))
        await done(event, f"{E['key']} {sc('pin kar diya')}", secs=6)
    except Exception as e:
        await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")


@register_cmd("unpin")
async def cmd_unpin(event, arg):
    a = (arg or "").strip().lower()
    try:
        if a == "all":
            await bot.unpin_message(event.chat_id)
        elif event.is_reply:
            r = await event.get_reply_message()
            await r.unpin()
        else:
            await bot.unpin_message(event.chat_id)
        await done(event, f"{E['trash']} {sc('unpin ho gaya')}", secs=6)
    except Exception as e:
        await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")


@register_cmd("group")
async def cmd_group(event, arg):
    parts = (arg or "").split(maxsplit=1)
    if len(parts) < 2 or parts[0].lower() not in ("title", "desc", "description"):
        return await eor(event, f"{E['dot']} {mono('.group title <text>')}\n"
                                f"{E['dot']} {mono('.group desc <text>')}")
    what, val = parts[0].lower(), parts[1].strip()
    try:
        if what == "title":
            await bot(functions.channels.EditTitleRequest(channel=event.chat_id, title=val[:255]))
        else:
            await bot(functions.messages.EditChatAboutRequest(peer=event.chat_id, about=val[:255]))
        await done(event, f"{E['ok']} {sc('group ' + what + ' updated')}", secs=6)
    except Exception as e:
        await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")


async def _lock_mute_all(event, mute=True):
    """chat ke sab members ko mute / unmute (send_messages band / allow).

    .lock  → sab mute + messages 0.3s me udd
    .slock → har type lock + sab mute
    .unlock (all) → sab wapas unmute
    """
    ok = fail = 0
    label = f"{E['lock']} {sc('mute all')}…" if mute else f"{E['ok']} {sc('unmute all')}…"
    st = await flash(event, label, secs=120)
    try:
        async for user in bot.iter_participants(event.chat_id):
            if getattr(user, "bot", False) or getattr(user, "deleted", False):
                continue
            if user.id in ADMINS or user.id == OWNER_ID:
                continue          # apne admins ko mat chhedo
            try:
                await bot.edit_permissions(event.chat_id, user.id,
                                           send_messages=not mute)
                ok += 1
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
                try:
                    await bot.edit_permissions(event.chat_id, user.id,
                                               send_messages=not mute)
                    ok += 1
                except Exception:
                    fail += 1
            except Exception:
                fail += 1
    except Exception:
        fail = -1                  # rights nahi hain
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    return ok, fail


@register_cmd("lock", group_only=True)
async def cmd_lock(event, arg):
    a = (arg or "").strip().lower()
    ltype = a.split()[0] if a else "all"
    if ltype == "list":
        return await eor(event, f"{E['lock']} {sc('types')}\n{E['dot']} " +
                         mono(", ".join(LOCK_TYPES)))
    if ltype not in LOCK_TYPES:
        return await eor(event, f"{E['no']} {sc('galat type')} {mono(ltype)}\n"
                                 f"{E['dot']} " + mono(", ".join(LOCK_TYPES)))
    key = str(event.chat_id)
    cur = set(LOCKS.get(key) or [])
    if ltype in cur:
        return await eor(event, f"{E['warn']} {mono(ltype)} {sc('pehle se locked hai')}")
    cur.add(ltype)
    LOCKS[key] = sorted(cur)
    save_json(F_LOCKS, LOCKS)
    extra = ""
    if ltype == "all" and event.is_group:
        mok, mfail = await _lock_mute_all(event, True)
        extra = (f"\n{E['dot']} {sc('members muted')} {mono(str(mok))}"
                 f" · {sc('fail')} {mono(str(mfail))}")
    # lock ka result rehna chahiye (auto-delete nahi)
    await eor(event, "\n".join([
        top(), sub(""),
        sub(f"{E['lock']} {sc('lock')} {mono(ltype)} {sb('ON')}"),
        sub(""),
        sub(f"{E['dot']} {sc('matching msgs')} {mono(str(LOCK_DELAY) + 's')} {sc('me udd jayenge')}"),
        sub(f"{E['dot']} {sc('active')} ‣ {mono(', '.join(LOCKS[key]))}"),
        *( [sub(x) for x in extra.split("\n") if x.strip()] if extra else [] ),
        sub(""), sub(FOOT), close(),
    ]))


@register_cmd("unlock", group_only=True)
async def cmd_unlock(event, arg):
    a = (arg or "").strip().lower()
    ltype = a.split()[0] if a else "all"
    key = str(event.chat_id)
    cur = set(LOCKS.get(key) or [])
    if ltype == "all":
        cur.clear()
    elif ltype in cur:
        cur.discard(ltype)
    else:
        return await eor(event, f"{E['warn']} {mono(ltype)} {sc('locked hai hi nahi')}")
    if cur:
        LOCKS[key] = sorted(cur)
    else:
        LOCKS.pop(key, None)
    save_json(F_LOCKS, LOCKS)
    extra = ""
    if ltype == "all" and event.is_group:
        mok, mfail = await _lock_mute_all(event, False)
        extra = (f"\n{E['dot']} {sc('members unmuted')} {mono(str(mok))}"
                 f" · {sc('fail')} {mono(str(mfail))}")
    await eor(event, "\n".join([
        top(), sub(""),
        sub(f"{E['ok']} {sc('unlock')} {mono(ltype)}"),
        sub(""),
        sub(f"{E['dot']} {sc('bache')} ‣ {mono(', '.join(sorted(cur)) or 'kuch nahi')}"),
        *( [sub(x) for x in extra.split("\n") if x.strip()] if extra else [] ),
        sub(""), sub(FOOT), close(),
    ]))


@register_cmd("slock", group_only=True)
async def cmd_slock(event, arg):
    """.slock — super lock: har media type ek saath + sab members mute."""
    key = str(event.chat_id)
    LOCKS[key] = sorted(LOCK_TYPES)
    save_json(F_LOCKS, LOCKS)
    mok = mfail = 0
    if event.is_group:
        mok, mfail = await _lock_mute_all(event, True)
    lines = [top(),
             sub(f"{E['lock']} {sb('SUPER LOCK')} {sb('ON')}"),
             sub(""),
             sub(kv("types", str(len(LOCK_TYPES)), bullet=E["diamond"])),
             sub(kv("muted", str(mok), bullet=E["shield"])),
             sub(kv("failed", str(mfail), bullet=E["warn"])),
             sub(kv("delay", f"{LOCK_DELAY}s", bullet=E["clock"])),
             sub(""),
             sub(FOOT),
             close()]
    await eor(event, "\n".join(lines))


@register_cmd("locks", group_only=True)
async def cmd_locks(event, arg):
    cur = LOCKS.get(str(event.chat_id))
    if not cur:
        return await eor(event, f"{E['ok']} {sc('is chat me koi lock nahi')}")
    lines = [top(), sub(f"{E['lock']} {sc('active locks')}"), sub("")]
    for t in cur:
        lines.append(sub(f" {E['dot']} {mono(t)}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("tagall", group_only=True)
async def cmd_tagall(event, arg):
    global TAGALL_ACTIVE
    msg_text = arg if arg else f"{E['spark']} {sc('attention')}"
    st = await flash(event, f"{E['bolt']} {sc('tagging')}…", secs=30)
    TAGALL_ACTIVE = True
    mentions, sent = [], 0
    async for user in bot.iter_participants(event.chat_id):
        if not TAGALL_ACTIVE:
            break
        if user.bot or user.deleted:
            continue
        mentions.append(f"[{user.first_name}](tg://user?id={user.id})")
        if len(mentions) == 5:
            try:
                await bot.send_message(event.chat_id, msg_text + "\n" + " ".join(mentions))
                sent += 1
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass
            mentions = []
            await asyncio.sleep(1.5)
    if mentions:
        try:
            await bot.send_message(event.chat_id, msg_text + "\n" + " ".join(mentions))
            sent += 1
        except Exception:
            pass
    TAGALL_ACTIVE = False
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, f"{E['bolt']} {sc('tagall done')} {E['arrow']} {mono(str(sent))} {sc('batches')}")
    await _del_after(conf, TMP_TTL)


@register_cmd("stop")
async def cmd_stop(event, arg):
    global TAGALL_ACTIVE
    TAGALL_ACTIVE = False
    await done(event, f"{E['no']} {sc('tagall stopped')}", secs=6)


@register_cmd("banall", group_only=True, owner_only=True)
async def cmd_banall(event, arg):
    st = await flash(event, f"{E['skull']} {sc('banall chal raha hai')}…", secs=120)
    ok = fail = 0
    async for u in bot.iter_participants(event.chat_id):
        if u.bot or u.id == OWNER_ID or u.id in ADMINS:
            continue
        try:
            await bot.edit_permissions(event.chat_id, u.id, view_messages=False)
            ok += 1
        except FloodWaitError as fw:
            await asyncio.sleep(min(fw.seconds, 20)); fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.4)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, f"{E['skull']} {sc('banall done')}\n"
                            f" {E['ok']} {sc('banned')} ‣ {mono(str(ok))}\n"
                            f" {E['no']} {sc('fail')}   ‣ {mono(str(fail))}")
    await _del_after(conf, 6)


# ══════════════════════════════════════════════════════════════
#                     ɢʟᴏʙᴀʟ ʙᴀɴ / ᴍᴜᴛᴇ
# ══════════════════════════════════════════════════════════════
async def _gban_enforce(chat, uid):
    try:
        await bot.edit_permissions(chat, uid, view_messages=False)
    except Exception:
        pass


@register_cmd("gban", owner_only=True)
async def cmd_gban(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')} {E['arrow']} {mono('.gban @user')}")
    if is_admin(uid):
        return await eor(event, f"{E['no']} {sc('owner/admin ko gban nahi kar sakta')}")
    GBAN.add(uid)
    save_json(F_GBAN, sorted(GBAN))
    st = await flash(event, f"{E['skull']} {sc('gban')} {mono(str(uid))}…", secs=90)
    ok = fail = 0
    async for d in bot.iter_dialogs():
        if dialog_kind(d) not in ("chat", "group"):
            continue
        try:
            await bot.edit_permissions(d.id, uid, view_messages=False)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.25)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['skull']} {sc('gban')} {E['arrow']} {mono(str(uid))}\n"
                      f" {E['ok']} {sc('chats')} ‣ {mono(str(ok))}\n"
                      f" {E['no']} {sc('fail')}  ‣ {mono(str(fail))}", secs=10)


@register_cmd("ungban", owner_only=True)
async def cmd_ungban(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    GBAN.discard(uid)
    save_json(F_GBAN, sorted(GBAN))
    st = await flash(event, f"{E['ok']} {sc('un-gban')}…", secs=90)
    ok = fail = 0
    async for d in bot.iter_dialogs():
        if dialog_kind(d) not in ("chat", "group"):
            continue
        try:
            await bot.edit_permissions(d.id, uid, view_messages=True)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.25)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['ok']} {sc('un-gban')} {mono(str(uid))} · {mono(str(ok))} {sc('ok')}", secs=10)


@register_cmd("gbanlist", owner_only=True)
async def cmd_gbanlist(event, arg):
    if not GBAN:
        return await eor(event, f"{E['note']} {sc('gban list khaali hai')}")
    lines = [top(), sub(f"{E['skull']} {sc('gban list')} {mono(str(len(GBAN)))}"), sub("")]
    for i, u in enumerate(sorted(GBAN), 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {mono(str(u))}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("gmute", "gm", owner_only=True)
async def cmd_gmute(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')} {E['arrow']} {mono('.gmute @user')}")
    if is_admin(uid):
        return await eor(event, f"{E['no']} {sc('owner/admin ko gmute nahi kar sakta')}")
    GMUTE.add(uid)
    save_json(F_GMUTE, sorted(GMUTE))
    await done(event, f"{E['lock']} {sc('gmute')} {E['arrow']} {mono(str(uid))}\n"
                      f"{E['dot']} {sc('jahan main admin, uske msgs udd jayenge')}", secs=10)


@register_cmd("ungmute", "gunmute", owner_only=True)
async def cmd_ungmute(event, arg):
    uid, _ = await resolve_uid(event, arg)
    if not uid:
        return await eor(event, f"{E['no']} {sc('user nahi mila')}")
    GMUTE.discard(uid)
    save_json(F_GMUTE, sorted(GMUTE))
    await done(event, f"{E['ok']} {sc('un-gmute')} {E['arrow']} {mono(str(uid))}", secs=6)


@register_cmd("gmutelist", owner_only=True)
async def cmd_gmutelist(event, arg):
    if not GMUTE:
        return await eor(event, f"{E['note']} {sc('gmute list khaali hai')}")
    lines = [top(), sub(f"{E['lock']} {sc('gmute list')} {mono(str(len(GMUTE)))}"), sub("")]
    for i, u in enumerate(sorted(GMUTE), 1):
        lines.append(sub(f" {E['dot']} {mono(str(i))} ‣ {mono(str(u))}"))
    lines += [sub(""), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


# ══════════════════════════════════════════════════════════════
#                          ʀᴀɪᴅ
# ══════════════════════════════════════════════════════════════
async def raid_add(event, arg, bucket, label):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')} {E['arrow']} {sc('reply / @user / id')}")
    added, already = [], []
    for uid in targets:
        (already if uid in bucket else added).append(str(uid))
        bucket.add(uid)
    parts = []
    if added:
        parts.append(f"{E['sword']} {sc(label + ' on')} {E['arrow']} {mono(', '.join(added))}")
    if already:
        parts.append(f"{E['warn']} {sc('pehle se')} {mono(', '.join(already))}")
    await done(event, "\n".join(parts) or f"{E['no']} {sc('kuch nahi hua')}", secs=8)


async def raid_del(event, arg, bucket, label):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    removed = [str(u) for u in targets if u in bucket]
    bucket.difference_update(targets)
    await done(event, f"{E['no']} {sc(label + ' off')} {E['arrow']} {mono(', '.join(removed) or '—')}", secs=6)


@register_cmd("reply")
async def cmd_reply(event, arg):
    await raid_add(event, arg, reply_users, "reply raid")


@register_cmd("sreply")
async def cmd_sreply(event, arg):
    await raid_del(event, arg, reply_users, "reply raid")


@register_cmd("rr")
async def cmd_rr(event, arg):
    await raid_add(event, arg, rr_users, "rr raid")


@register_cmd("srr")
async def cmd_srr(event, arg):
    await raid_del(event, arg, rr_users, "rr raid")


@register_cmd("flag")
async def cmd_flag(event, arg):
    await raid_add(event, arg, flag_users, "flag raid")


@register_cmd("sflag")
async def cmd_sflag(event, arg):
    await raid_del(event, arg, flag_users, "flag raid")


@register_cmd("hrr")
async def cmd_hrr(event, arg):
    await raid_add(event, arg, hrr_users, "heart raid")


@register_cmd("shrr")
async def cmd_shrr(event, arg):
    await raid_del(event, arg, hrr_users, "heart raid")


@register_cmd("replygod")
async def cmd_replygod(event, arg):
    await raid_add(event, arg, replygod_users, "replygod")


@register_cmd("sgod")
async def cmd_sgod(event, arg):
    await raid_del(event, arg, replygod_users, "replygod")


@register_cmd("nikreply", "replynik")
async def cmd_nikreply(event, arg):
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('reply karke')} {mono('.nikreply <count> <text>')}")
    parts = (arg or "").split(maxsplit=1)
    if len(parts) < 2:
        return await eor(event, f"{E['no']} {mono('.nikreply <count> <text>')}\n"
                                f"{E['dot']} {mono('.nikreply 10 tu chup kar')}")
    try:
        count = int(parts[0])
    except Exception:
        return await eor(event, f"{E['no']} {sc('count number hona chahiye')}")
    count = max(1, min(count, 200))
    text = parts[1].strip()
    targets = await get_targets(event, "")
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    for uid in targets:
        replyking_users[uid] = {"text": text, "count": count}
    await done(event, f"{E['crown']} {sc('nikreply on')} {E['arrow']} "
                      f"{mono(', '.join(map(str, targets)))}\n"
                      f"{E['dot']} {sc('count')} {mono(str(count))} · {text[:30]}\n"
                      f"{E['dot']} {mono('.nik')} {sc('se band')}", secs=10)


@register_cmd("nik", "nikstop")
async def cmd_nik(event, arg):
    cleared = (len(reply_users) + len(rr_users) + len(flag_users) + len(hrr_users)
               + len(replygod_users) + len(replyking_users))
    for s in (reply_users, rr_users, flag_users, hrr_users, replygod_users):
        s.clear()
    replyking_users.clear()
    await done(event, f"{E['crown']} {sc('nik raid stop')} {E['arrow']} {mono(str(cleared))} {sc('cleared')}", secs=6)


@register_cmd("raidstopall", "stopall")
async def cmd_raidstopall(event, arg):
    cleared = sum(len(s) for s in (reply_users, rr_users, flag_users, hrr_users,
                                   replygod_users, ECHO_USERS))
    for s in (reply_users, rr_users, flag_users, hrr_users, replygod_users, ECHO_USERS):
        s.clear()
    replyking_users.clear(); USER_REPLY.clear()
    for t in list(spray_tasks.values()):
        try:
            t.cancel()
        except Exception:
            pass
    spray_tasks.clear()
    global GPFP_TASK
    if GPFP_TASK and not GPFP_TASK.done():
        try:
            GPFP_TASK.cancel()
        except Exception:
            pass
    GPFP_TASK = None
    GPFP_STATE["on"] = False
    global TAGALL_ACTIVE
    TAGALL_ACTIVE = False
    await done(event, f"{E['no']} {sc('sab band')} {E['arrow']} {mono(str(cleared))} {sc('cleared')}", secs=8)


@register_cmd("bomb")
async def cmd_bomb(event, arg):
    targets = await get_targets(event, arg)
    if not targets and not event.is_reply:
        msg = await eor(event, f"{E['fire']} {sc('loading')}…")
        for f in ["💣·", "💣··", "💣···", "💥 BOOM", "🔥 Nik bomb 💥", "💀 Bhag bsdk 💀"]:
            try:
                await msg.edit(f); await asyncio.sleep(0.6)
            except Exception:
                break
        return
    for uid in targets:
        reply_users.add(uid); rr_users.add(uid)
    await done(event, f"{E['fire']} {sc('bomb')} {E['arrow']} {mono(', '.join(map(str, targets)))}", secs=6)


@register_cmd("gali")
async def cmd_gali(event, arg):
    try:
        count = int((arg or "5").split()[0])
    except Exception:
        count = 5
    count = max(1, min(count, 20))
    st = await flash(event, f"{E['fire']} {sc('gali')} {mono(str(count))}x…", secs=30)
    for _ in range(count):
        try:
            await event.reply(random.choice(reply_list))
        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds)
        except Exception:
            pass
        await asyncio.sleep(0.8)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass


@register_cmd("love")
async def cmd_love(event, arg):
    msg = await eor(event, f"{E['heart']} {sc('starting')}…")
    if msg is None:
        return
    for f in ["❤️", "💖", "💝", "💞", "💓", "💗", "❤️‍🔥", "💘", "❤️ Nik loves you ❤️"]:
        try:
            await msg.edit(f" {f} " * 5); await asyncio.sleep(0.5)
        except Exception:
            break


# ══════════════════════════════════════════════════════════════
#                          sᴘᴀᴍ
# ══════════════════════════════════════════════════════════════
def _start_loop(chat, text, delay, media=None):
    async def loop():
        try:
            while chat in spray_tasks:
                try:
                    if media is not None:
                        await bot.send_file(chat, media)
                    else:
                        await bot.send_message(chat, text)
                except FloodWaitError as fw:
                    await asyncio.sleep(fw.seconds)
                except RPCError:
                    break
                except Exception:
                    await asyncio.sleep(2)
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        finally:
            spray_tasks.pop(chat, None)
    spray_tasks[chat] = asyncio.create_task(loop())


@register_cmd("spray", owner_only=True)
async def cmd_spray(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.spray <text>')}")
    chat = event.chat_id
    if chat in spray_tasks and not spray_tasks[chat].done():
        return await eor(event, f"{E['warn']} {sc('spray pehle se chal raha hai')}")
    _start_loop(chat, arg[:4000], 3)
    await done(event, f"{E['comet']} {sc('spray on')} {E['arrow']} {arg[:40]}\n"
                      f"{E['dot']} {mono('.dspray')} / {mono('.sspam')}", secs=8)


@register_cmd("d")
async def cmd_d(event, arg):
    """.d <seconds> <text> — har N sec me repeat"""
    parts = (arg or "").split(maxsplit=1)
    if len(parts) < 2:
        return await eor(event, f"{E['dot']} {mono('.d 2 hello')}\n"
                                f"{E['dot']} {sc('delay 0.5 – 5 sec')}\n"
                                f"{E['dot']} {mono('.sspam')} {sc('se band')}")
    try:
        delay = float(parts[0])
    except Exception:
        return await eor(event, f"{E['no']} {sc('delay number do')}")
    delay = max(0.5, min(delay, 60.0))
    chat = event.chat_id
    if chat in spray_tasks and not spray_tasks[chat].done():
        return await eor(event, f"{E['warn']} {sc('pehle se chal raha hai')} {E['arrow']} {mono('.sspam')}")
    _start_loop(chat, parts[1][:4000], delay)
    await done(event, f"{E['comet']} {sc('repeat on')} {E['arrow']} {mono(str(delay) + 's')}\n"
                      f"{E['dot']} {parts[1][:40]}", secs=8)


@register_cmd("dspray", "sspam", owner_only=True)
async def cmd_dspray(event, arg):
    chat = event.chat_id
    if chat not in spray_tasks:
        return await eor(event, f"{E['warn']} {sc('koi active loop nahi')}")
    try:
        spray_tasks[chat].cancel()
    except Exception:
        pass
    spray_tasks.pop(chat, None)
    await done(event, f"{E['no']} {sc('loop band')}", secs=6)


@register_cmd("spam")
async def cmd_spam(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.spam <count> <text>')}")
    parts = arg.split(maxsplit=1)
    if len(parts) < 2:
        return await eor(event, f"{E['no']} {sc('text bhi do')}")
    try:
        count = int(parts[0])
    except Exception:
        return await eor(event, f"{E['no']} {sc('count number hona chahiye')}")
    count = max(1, min(count, 100))
    txt = parts[1]
    st = await flash(event, f"{E['comet']} {sc('spam')} {mono(str(count))}x…", secs=60)
    for _ in range(count):
        try:
            await event.reply(txt)
        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds)
        except Exception:
            pass
        await asyncio.sleep(0.7)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass


@register_cmd("mspam")
async def cmd_mspam(event, arg):
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('media pe reply karke')} {mono('.mspam <n>')}")
    reply = await event.get_reply_message()
    try:
        count = int((arg or "5").split()[0])
    except Exception:
        count = 5
    count = max(1, min(count, 30))
    st = await flash(event, f"{E['comet']} {sc('media')} {mono(str(count))}x…", secs=60)
    for _ in range(count):
        try:
            if getattr(reply, "media", None):
                await bot.send_file(event.chat_id, reply.media)
        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds)
        except Exception:
            pass
        await asyncio.sleep(1.2)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass


@register_cmd("delayspam")
async def cmd_delayspam(event, arg):
    parts = (arg or "").split(maxsplit=2)
    if len(parts) < 3:
        return await eor(event, f"{E['dot']} {mono('.delayspam <delay> <count> <text>')}")
    try:
        delay = float(parts[0]); count = int(parts[1])
    except Exception:
        return await eor(event, f"{E['no']} {sc('delay aur count number hone chahiye')}")
    delay = max(0.5, delay); count = max(1, min(count, 100))
    st = await flash(event, f"{E['clock']} {mono(str(delay) + 's')} × {mono(str(count))}", secs=120)
    for _ in range(count):
        try:
            await event.reply(parts[2])
        except FloodWaitError as fw:
            await asyncio.sleep(fw.seconds)
        except Exception:
            pass
        await asyncio.sleep(delay)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass


PURGE_STOP = asyncio.Event()


def _purge_card(title, done_n=0, extra=""):
    rows = [f"{E['trash']} {sb('PURGE ALL')}", "",
            f"{E['dot']} {sc(title)}"]
    if done_n:
        rows.append(f"{E['star']} {sc('deleted')} ‣ {mono(str(done_n))}")
    if extra:
        rows.append(f"{E['dot']} {sc(extra)}")
    return panel(rows)


@register_cmd("purgeall", owner_only=True)
async def cmd_purgeall(event, arg):
    """.purgeall → poori chat ek hi baar me saaf (koi count nahi)"""
    chat = int(event.chat_id)
    a = (arg or "").strip().lower()
    if a in ("stop", "off", "cancel", "band"):
        PURGE_STOP.set()
        return await eor(event, _purge_card(sc("stop signal bhej diya")))

    limit = None                      # hamesha poori chat
    if a:
        return await eor(event, panel([
            f"{E['warn']} {sc('purgeall ka ek hi kaam hai')}",
            "",
            f"{E['dot']} {mono('.purgeall')} {sc('→ poori chat saaf')}",
            f"{E['dot']} {mono('.purge <n>')} {sc('→ last n messages')}",
            f"{E['dot']} {mono('.purgeme <n>')} {sc('→ apne last n')}",
        ]))
    PURGE_STOP.clear()
    label = f"last {limit}" if limit else "poori chat"

    st = await eor(event, panel([
        f"{E['trash']} {sb('PURGE ALL')}", "",
        f"{E['dot']} {sc('mode')} ‣ {mono(label)}",
        f"{E['dot']} {sc('scanning history')}…",
        "",
        f"{E['warn']} {sc('rokne ke liye')} {mono('.purgeall stop')}",
    ]))

    total = scanned = 0
    batch = []
    try:
        async for m in bot.iter_messages(chat, limit=limit):
            if PURGE_STOP.is_set():
                break
            batch.append(m.id)
            scanned += 1
            if len(batch) >= 100:
                total += await _delete_ids(chat, batch)
                batch = []
                if st is not None and scanned % 500 == 0:
                    try:
                        await aedit(st, "\n".join([
                            top(), sub(""),
                            sub(f"{E['trash']} {sb('PURGE ALL')}"),
                            sub(f"{E['dot']} {sc('scanned')} ‣ {mono(str(scanned))}"),
                            sub(f"{E['star']} {sc('deleted')} ‣ {mono(str(total))}"),
                            sub(""), sub(f"{E['warn']} {mono('.purgeall stop')}"),
                            sub(""), sub(FOOT), close(),
                        ]))
                    except Exception:
                        st = None
        if batch and not PURGE_STOP.is_set():
            total += await _delete_ids(chat, batch)
    except FloodWaitError as fw:
        await asyncio.sleep(min(getattr(fw, "seconds", 10), 30))
    except Exception as e:
        # id-based iteration kabhi fail ho to bhi jo delete hua wo batao
        pass

    # puri chat uda dene ke baad status message bhi gaya hoga → naya bhejo
    try:
        fin = await bot.send_message(chat, align_panel(panel([
            f"{E['ok'] if not PURGE_STOP.is_set() else E['wait']} {sb('PURGE ALL')}",
            "",
            f"{E['dot']} {sc('mode')} ‣ {mono(label)}",
            f"{E['star']} {sc('deleted')} ‣ {mono(str(total))}",
            f"{E['dot']} {sc('scanned')} ‣ {mono(str(scanned))}",
            *( [f"{E['warn']} {sc('beech me rok diya')}"] if PURGE_STOP.is_set() else [] ),
        ])))
        asyncio.create_task(_del_after(fin, 6))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#                         ғᴀsᴛɢᴄ
# ══════════════════════════════════════════════════════════════
async def fast_title_edit(chat_id, title):
    safe = (title or "").strip()[:255]
    if not safe:
        return False
    try:
        await bot(functions.channels.EditTitleRequest(channel=chat_id, title=safe))
        return True
    except Exception:
        return False


async def gc_fast_loop(chat_id):
    try:
        while FASTGC_STATE.get("active"):
            template = FASTGC_STATE.get("template")
            if not template:
                await asyncio.sleep(2)
                continue
            emoji = random.choice(GC_FAST_EMOJIS)
            ok = await fast_title_edit(chat_id, template.replace("{emoji}", emoji))
            await asyncio.sleep(1 if ok else 5)
    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"[FastGC] {err_txt(e, 80)}")


@register_cmd("fastgc", owner_only=True)
async def cmd_fastgc(event, arg):
    a = (arg or "").strip()
    if a.startswith("set "):
        template = a[4:].strip()
        if "{emoji}" not in template:
            return await eor(event, f"{E['no']} {sc('template me')} {mono('{emoji}')} {sc('likho')}\n"
                                    f"{E['dot']} {mono('.fastgc set Nik ♛ {emoji}')}")
        FASTGC_STATE.update({"active": True, "template": template, "chat_id": event.chat_id})
        old = FASTGC_STATE.get("task")
        if old and not old.done():
            try:
                old.cancel()
            except Exception:
                pass
        FASTGC_STATE["task"] = asyncio.create_task(gc_fast_loop(event.chat_id))
        return await done(event, f"{E['bolt']} {sc('fastgc on')} {E['arrow']} {mono(template[:35])}", secs=8)
    if a == "stop":
        FASTGC_STATE["active"] = False
        FASTGC_STATE["template"] = None
        t = FASTGC_STATE.get("task")
        if t and not t.done():
            try:
                t.cancel()
            except Exception:
                pass
        FASTGC_STATE["task"] = None
        return await done(event, f"{E['no']} {sc('fastgc off')}", secs=6)
    return await eor(event, f"{E['dot']} {mono('.fastgc set <title {{emoji}}>')}\n"
                            f"{E['dot']} {mono('.fastgc stop')}")


# ══════════════════════════════════════════════════════════════
#                ᴀғᴋ · ɢʜᴏsᴛ · ᴇᴄʜᴏ · ʀᴇᴀᴄᴛ
# ══════════════════════════════════════════════════════════════
@register_cmd("afk")
async def cmd_afk(event, arg):
    AFK.update({"active": True, "reason": (arg or "AFK").strip(), "since": time.time()})
    await done(event, f"{E['moon']} {sc('afk on')} {E['arrow']} {mono(AFK['reason'])}\n"
                      f"{E['dot']} {sc('tag/pm pe auto-reply')} · {mono('.unafk')}", secs=8)


@register_cmd("unafk")
async def cmd_unafk(event, arg):
    AFK.update({"active": False, "reason": None})
    await done(event, f"{E['ok']} {sc('afk off')}", secs=6)


@register_cmd("ghost")
async def cmd_ghost(event, arg):
    a = (arg or "").split()
    if not a:
        return await eor(event, f"{E['ghost']} {sc('ghost')} {E['arrow']} "
                                f"{mono('ON' if GHOST['on'] else 'OFF')} {sc('·')} {mono(str(GHOST['delay']) + 's')}\n"
                                f"{E['dot']} {mono('.ghost on 30')} · {mono('.ghost off')}")
    if a[0].lower() in ("on", "enable", "start"):
        GHOST["on"] = True
        if len(a) > 1:
            try:
                GHOST["delay"] = max(3, min(int(a[1]), 3600))
            except Exception:
                pass
        return await done(event, f"{E['ghost']} {sc('ghost on')} {E['arrow']} "
                                 f"{sc('apne msgs')} {mono(str(GHOST['delay']) + 's')} {sc('me udd jayenge')}", secs=8)
    if a[0].lower() in ("off", "disable", "stop"):
        GHOST["on"] = False
        return await done(event, f"{E['ghost']} {sc('ghost off')}", secs=6)
    return await eor(event, f"{E['dot']} {mono('.ghost on|off [seconds]')}")


@register_cmd("echo")
async def cmd_echo(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    ECHO_USERS.update(targets)
    await done(event, f"{E['note']} {sc('echo on')} {E['arrow']} "
                      f"{mono(', '.join(map(str, sorted(targets))))}\n"
                      f"{E['dot']} {mono('.unecho')}", secs=8)


@register_cmd("unecho")
async def cmd_unecho(event, arg):
    targets = await get_targets(event, arg)
    if not targets:
        return await eor(event, f"{E['no']} {sc('target nahi mila')}")
    ECHO_USERS.difference_update(targets)
    await done(event, f"{E['no']} {sc('echo off')} {E['arrow']} "
                      f"{mono(', '.join(map(str, sorted(targets))))}", secs=6)


# ══════════════════════════════════════════════════════════════
#      🎯  ʀᴇᴀᴄᴛɪᴏɴs  ·  combos + LOCK  (.ar .makear .r .rem)
# ══════════════════════════════════════════════════════════════
# • .ar <combo|emoji>  (reply / @user)  → react + LOCK us user pe
# • .ar off                             → is chat ke locks band
# • .sar <combo|emoji>                  → mere messages pe react (global)
# • .sar / .selfsar                     → self react band
# • .makear <name> → .r <emoji> ×1-3 → auto save (msg 2 sec me udta hai)
# • .rem <name>                         → saved combo hatao
F_REACT = "react.json"
F_ARLOCK = "arlock.json"
F_SELFREACT = "selfreact.json"

AR_MAX = 3

# preset combos — item int = custom emoji document id
AR_PRESETS: Dict[str, list] = {
    "cry":  [5228727683327730051, 6213131649245255060, 6131819865268293476],
    "sad":  [6253554068959010097, 6222224683421409311, 5282774327714915617],
    "aww":  [5845902956070705899, 5260666756652875017, 6199390412482813397],
    "lol":  [5231140750573456515, 6129429174802190872, 6253672442552653728],
    "kiss": [5420223103777119776, 6201536182438861209, 5310162509527786481],
}

AR_SAVED: Dict[str, list] = {}


def _ar_norm(v):
    """json se aaya hua list — int (doc id) ya str (unicode emoji)."""
    out = []
    if isinstance(v, list):
        for x in v[:AR_MAX]:
            if isinstance(x, bool):
                continue
            if isinstance(x, int):
                out.append(int(x))
            elif isinstance(x, str) and x.strip():
                s = x.strip()
                out.append(int(s) if s.isdigit() else s)
    return out


try:
    _raw_ar = load_json(F_REACT, {})
    if isinstance(_raw_ar, dict):
        for _k, _v in _raw_ar.items():
            got = _ar_norm(_v)
            if got:
                AR_SAVED[str(_k).lower()] = got
except Exception:
    AR_SAVED = {}

AR_BUILD: Dict[int, Dict[str, Any]] = {}      # uid → {name, items, until}
AR_LOCK: Dict[str, Dict[str, Any]] = {}       # "chat:user" → {items, name}
SELF_REACT: list = []                         # mere messages pe (global)
AUTO_REACT_EMOJI: Optional[str] = None        # purana compat/display

try:
    _raw_self = load_json(F_SELFREACT, [])
    SELF_REACT = _ar_norm(_raw_self)
    if SELF_REACT:
        AUTO_REACT_EMOJI = str(SELF_REACT[0])[:8]
except Exception:
    SELF_REACT = []

try:
    _raw_lock = load_json(F_ARLOCK, {})
    if isinstance(_raw_lock, dict):
        for _k, _v in _raw_lock.items():
            if not isinstance(_v, dict):
                continue
            _it = _ar_norm(_v.get("items"))
            if _it and ":" in str(_k):
                AR_LOCK[str(_k)] = {"items": _it,
                                    "name": str(_v.get("name") or "custom")}
except Exception:
    AR_LOCK = {}


def _ar_all():
    """preset + saved dono ek jagah."""
    d = dict(AR_PRESETS)
    d.update(AR_SAVED)
    return d


def _ar_save():
    save_json(F_REACT, {k: v for k, v in AR_SAVED.items()})


def _ar_lock_save():
    save_json(F_ARLOCK, {k: v for k, v in AR_LOCK.items()})


def _ar_self_save():
    save_json(F_SELFREACT, list(SELF_REACT))


def _ar_clean():
    now = time.time()
    for uid in list(AR_BUILD):
        if AR_BUILD[uid].get("until", 0) < now:
            AR_BUILD.pop(uid, None)


def _lock_key(chat, uid):
    return "%s:%s" % (int(chat), int(uid))


# unicode emoji detect (❤️ 😂 🔥 etc — variation selectors/ZWJ ke saath)
_EMOJI_RE = re.compile(
    r"^[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u23FF\u2460-\u24FF"
    r"\u25A0-\u27BF\u2900-\u297F\u2B00-\u2BFF\u3030\u303D\u3297\u3299"
    r"\uFE00-\uFE0F\u200D\u20E3\U0001F1E6-\U0001F1FF]+$")


def _r_item(event, raw):
    """ek input → int (custom emoji id) | str (unicode emoji) | None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        n = int(raw)
        return n if n > 1000 else None
    # premium custom emoji — .r/<emoji> ke saath bheja gaya entity
    try:
        for ent in (getattr(getattr(event, "message", None), "entities", None) or []):
            if type(ent).__name__ == "MessageEntityCustomEmoji":
                did = int(getattr(ent, "document_id", 0) or 0)
                if did:
                    return did
    except Exception:
        pass
    # seedha unicode emoji → plain reaction (100% chalta hai, pack ki zarurat nahi)
    if _EMOJI_RE.match(raw):
        return raw
    got = _NIK_EMOJI_IDS.get(raw)
    if got:
        return int(got)
    return None


def _react_payload(items):
    """items → [ReactionCustomEmoji | ReactionEmoji] (max 3)."""
    out = []
    for it in list(items or [])[:AR_MAX]:
        try:
            if isinstance(it, bool):
                continue
            if isinstance(it, int) or (isinstance(it, str) and it.isdigit()):
                out.append(types.ReactionCustomEmoji(document_id=int(it)))
            elif isinstance(it, str) and it.strip():
                out.append(types.ReactionEmoji(emoticon=it.strip()))
        except Exception:
            continue
    return out


_ID_ALT_CACHE: Dict[int, str] = {}


def _id_alt(did):
    """custom emoji id → uska unicode alt (fallback ke liye)."""
    did = int(did)
    if did in _ID_ALT_CACHE:
        return _ID_ALT_CACHE[did]
    for emo, val in _NIK_EMOJI_IDS.items():
        try:
            if int(val) == did:
                _ID_ALT_CACHE[did] = emo
                return emo
        except Exception:
            continue
    _ID_ALT_CACHE[did] = "❤️"
    return "❤️"


def _alt_payload(items):
    """custom emoji → unicode fallback list (same order)."""
    out = []
    for it in list(items or [])[:AR_MAX]:
        if isinstance(it, str) and not str(it).isdigit():
            out.append(it)
        elif it:
            out.append(_id_alt(it))
    return out or ["❤️"]


async def _react_send(chat, msg_id, items, tries=2):
    """react bhejo — custom fail ho to unicode se, phir bhi fail to error."""
    if not msg_id:
        return False, "message nahi mila"
    plan = [_react_payload(items), _react_payload(_alt_payload(items))]
    last = ""
    for payload in plan:
        if not payload:
            continue
        for _ in range(tries):
            try:
                await bot(functions.messages.SendReactionRequest(
                    peer=chat, msg_id=int(msg_id), reaction=payload, big=False))
                return True, ""
            except FloodWaitError as fw:
                try:
                    await asyncio.sleep(min(int(getattr(fw, "seconds", 2)) or 2, 8))
                except Exception:
                    pass
                last = "flood wait"
            except Exception as e:
                last = str(e)
                if "MESSAGE_ID_INVALID" in last:
                    return False, "message delete ho gaya"
                if "REACTION_INVALID" in last or "TOO_MANY" in last:
                    break                      # agli plan (unicode) try karo
                await asyncio.sleep(0.4)
    if "REACTION_INVALID" in last:
        return False, "ye emoji reaction me allowed nahi"
    return False, err_txt(last, 70)


async def _ar_target(event, targ=""):
    """reply → (chat, msg_id, uid) · @user/id → us user ka latest msg."""
    try:
        reply = await event.get_reply_message()
    except Exception:
        reply = None
    if reply is not None:
        return (event.chat_id, reply.id,
                int(getattr(reply, "sender_id", 0) or 0))
    t = (targ or "").strip().lstrip("@")
    if t:
        try:
            ent = await bot.get_entity(int(t) if t.lstrip("-").isdigit() else t)
            async for m in bot.iter_messages(event.chat_id, from_user=ent, limit=1):
                return event.chat_id, m.id, int(getattr(ent, "id", 0) or 0)
        except Exception:
            pass
    return event.chat_id, None, 0


async def _ar_last_incoming(event):
    """is chat ka sabse naya message (apna nahi) — no-reply fallback."""
    try:
        me = await bot.get_me()
        me_id = int(me.id)
    except Exception:
        me_id = 0
    try:
        async for m in bot.iter_messages(event.chat_id, limit=15):
            sid = int(getattr(m, "sender_id", 0) or 0)
            if not sid or sid == me_id:
                continue
            if int(getattr(m, "id", 0)) == int(getattr(event, "id", 0) or 0):
                continue
            return event.chat_id, m.id, sid
    except Exception:
        pass
    return event.chat_id, None, 0


def _ar_off_chat(chat):
    """is chat ke saare target locks hatao → kitne hate."""
    ch = str(int(chat))
    gone = [k for k in AR_LOCK if k.split(":")[0] == ch]
    for k in gone:
        AR_LOCK.pop(k, None)
    if gone:
        _ar_lock_save()
    return len(gone)


def _ar_chat_locks(chat):
    ch = str(int(chat))
    out = []
    for k, v in AR_LOCK.items():
        p = k.split(":")
        if len(p) == 2 and p[0] == ch:
            out.append((int(p[1]), v))
    return out


def _ar_names(items):
    """items → padhne layak label (custom id → 🔹 id, emoji → wahi)."""
    bits = []
    for it in list(items or [])[:AR_MAX]:
        if isinstance(it, int):
            bits.append("🔹" + str(it)[-4:])
        else:
            bits.append(str(it))
    return " ".join(bits)


async def _ar_help_card(event, title="reaction"):
    chat = event.chat_id
    allc = _ar_all()
    lines = [top(hero=("🎯", "💫")), sub(""),
             sub(f" {E['bolt']} {sc(title)} {E['dot']} {mono(str(len(allc)))}"
                 f" {sc('combos')}"),
             sub("")]
    for name in sorted(allc):
        tag = sc("preset") if name in AR_PRESETS else sc("saved")
        lines.append(sub(f" {E['dot']} {mono(name):16s} {E['arrow']} "
                         f"{mono(str(len(allc[name])))} {tag}"))
    locks = _ar_chat_locks(chat)
    if locks or SELF_REACT:
        lines += [sub(""), sub(f" {E['lock']} {sc('active locks')}")]
        for uid, d in locks[:8]:
            lines.append(sub(f" {E['dot']} {mono(str(uid))} {E['arrow']} "
                             f"{mono(str(d.get('name')))} "
                             f"{_ar_names(d.get('items'))}"))
        if SELF_REACT:
            lines.append(sub(f" {E['dot']} {sc('self')} {E['arrow']} "
                             f"{_ar_names(SELF_REACT)}"))
    lines += [sub(""),
              sub(f" {E['warn']} {mono('.ar <combo>')} {sc('reply pe → lock')}"),
              sub(f" {E['dot']} {mono('.ar off')} {sc('is chat ke locks band')}"),
              sub(f" {E['dot']} {mono('.sar <combo>')} {sc('mere msgs pe react')}"),
              sub(f" {E['dot']} {mono('.makear <name>')} {sc('naya combo')}"),
              sub(f" {E['dot']} {mono('.rem <name>')} {sc('combo hatao')}"),
              sub(FOOT), close()]
    return await eor(event, "\n".join(lines))


@register_cmd("ar", "art")
async def cmd_ar(event, arg):
    """.ar <combo|emoji> — reply pe lock · .ar off — locks band"""
    _ar_clean()
    a = (arg or "").strip()
    if not a:
        return await _ar_help_card(event)

    parts = a.split()
    key = parts[0].lower()
    targ = parts[1] if len(parts) > 1 else ""

    if key in ("off", "stop", "band", "clear"):
        n = _ar_off_chat(event.chat_id)
        msg = (f"{E['no']} {sc('reaction lock')} {E['arrow']} {mono('OFF')}"
               if n else f"{E['dot']} {sc('is chat me koi lock nahi tha')}")
        conf = await eor(event, msg)
        return await _del_after(conf, 4)

    allc = _ar_all()
    items, name = None, key

    if key in allc:
        items = list(allc[key])[:AR_MAX]
    else:
        # adhura build hi is naam se → auto save karo (yahi galti hoti thi)
        uid_now = int(event.sender_id or 0)
        st_now = AR_BUILD.get(uid_now)
        if st_now and st_now.get("name") == key and st_now.get("items"):
            items = list(st_now["items"])[:AR_MAX]
            AR_SAVED[key] = items
            _ar_save()
            AR_BUILD.pop(uid_now, None)
        else:
            one = _r_item(event, parts[0])
            if one is None:
                return await eor(event, "\n".join([
                    top(hero=("🎯", "💫")), sub(""),
                    sub(f" {E['no']} {sc('combo ya emoji samajh nahi aaya')} "
                        f"{E['arrow']} {mono(key)}"),
                    sub(""),
                    sub(f" {E['dot']} {sc('combo')} {E['arrow']} "
                        f"{mono(', '.join(sorted(allc)))}"),
                    sub(f" {E['dot']} {sc('ya seedha emoji')} {mono('.ar 🔥')}"),
                    sub(f" {E['dot']} {sc('naya banao')} {mono('.makear ' + key)}"),
                    sub(FOOT), close()]))
            items = [one]
            name = "custom"

    chat, mid, uid = await _ar_target(event, targ)
    if mid is None:
        chat, mid, uid = await _ar_last_incoming(event)
    if mid is None:
        return await eor(event, f"{E['warn']} {sc('target nahi mila')} {E['dot']} "
                                f"{mono('.ar <combo>')} {sc('kisi msg pe reply karke')}")

    ok, why = await _react_send(chat, mid, items)
    if not ok:
        return await eor(event, f"{E['no']} {sc('react fail')} {E['arrow']} {mono(why)}")

    if uid:
        AR_LOCK[_lock_key(chat, uid)] = {"items": items, "name": name}
        _ar_lock_save()

    try:
        await event.delete()
    except Exception:
        pass

    lines = [top(hero=("🎯", "🔒")), sub(""),
             sub(f" {E['lock']} {sc('reaction lock')} {E['arrow']} {mono('ON')}"),
             sub(f" {E['dot']} {sc('combo')} {E['arrow']} {mono(name)} "
                 f"{E['dot']} {_ar_names(items)}")]
    if uid:
        lines += [sub(f" {E['dot']} {sc('user')} {E['arrow']} {mono(str(uid))}"),
                  sub(f" {E['dot']} {sc('is chat me uske har msg pe lagega')}")]
    else:
        lines += [sub(f" {E['warn']} {sc('user pata nahi chala — sirf ek baar laga')}")]
    lines += [sub(""),
              sub(f" {E['no']} {mono('.ar off')} {sc('ya')} {mono('.sar')} "
                  f"{sc('— band karo')}"),
              sub(FOOT), close()]
    conf = await eor(event, "\n".join(lines))
    await _del_after(conf, 6)


@register_cmd("sar", "sart", "selfar")
async def cmd_sar(event, arg):
    """.sar <combo> — mere messages pe react · .sar / .selfsar — band"""
    global AUTO_REACT_EMOJI, SELF_REACT
    _ar_clean()
    a = (arg or "").strip()

    if not a or a.lower() in ("off", "stop", "band", "0"):
        n = _ar_off_chat(event.chat_id)
        had_self = bool(SELF_REACT)
        SELF_REACT = []
        AUTO_REACT_EMOJI = None
        _ar_self_save()
        if not had_self and not n:
            return await eor(event, f"{E['dot']} {sc('kuch chalu hi nahi tha')}")
        conf = await eor(event, "\n".join([
            top(hero=("🎯", "🔕")), sub(""),
            sub(f" {E['no']} {sc('reaction lock')} {E['arrow']} {mono('OFF')}"),
            sub(f" {E['dot']} {sc('chat locks hate')} {E['arrow']} {mono(str(n))}"),
            sub(f" {E['dot']} {sc('self react')} {E['arrow']} "
                f"{mono('off' if had_self else 'pehle se off')}"),
            sub(FOOT), close()]))
        return await _del_after(conf, 5)

    key = a.split()[0].lower()
    allc = _ar_all()
    items = None
    if key in allc:
        items = list(allc[key])[:AR_MAX]
    else:
        uid_now = int(event.sender_id or 0)
        st_now = AR_BUILD.get(uid_now)
        if st_now and st_now.get("name") == key and st_now.get("items"):
            items = list(st_now["items"])[:AR_MAX]
            AR_SAVED[key] = items
            _ar_save()
            AR_BUILD.pop(uid_now, None)
        else:
            one = _r_item(event, a.split()[0])
            if one is None:
                return await eor(event, f"{E['no']} {sc('ye combo/emoji nahi mila')} "
                                        f"{E['arrow']} {mono(key)}")
            items = [one]

    SELF_REACT = list(items)
    AUTO_REACT_EMOJI = _ar_names(items)
    _ar_self_save()
    conf = await eor(event, "\n".join([
        top(hero=("🎯", "🪞")), sub(""),
        sub(f" {E['ok']} {sc('self react')} {E['arrow']} {mono('ON')}"),
        sub(f" {E['dot']} {sc('mere har msg pe')} {E['arrow']} {_ar_names(items)}"),
        sub(""),
        sub(f" {E['no']} {mono('.selfsar')} {sc('ya')} {mono('.sar')} {sc('— band')}"),
        sub(FOOT), close()]))
    await _del_after(conf, 6)


@register_cmd("selfsar")
async def cmd_selfsar(event, arg):
    """.selfsar — khud pe react hona band"""
    global AUTO_REACT_EMOJI, SELF_REACT
    had = bool(SELF_REACT)
    SELF_REACT = []
    AUTO_REACT_EMOJI = None
    _ar_self_save()
    conf = await eor(event, f"{E['no']} {sc('self react')} {E['arrow']} "
                            f"{mono('OFF' if had else 'pehle se off')}")
    await _del_after(conf, 4)


@register_cmd("makear")
async def cmd_makear(event, arg):
    """.makear <name> — 60 sec ke andar .r <emoji> se 3 tak bharo"""
    _ar_clean()
    name = (arg or "").strip().lower().split()[0] if (arg or "").strip() else ""
    if not name:
        return await eor(event, "\n".join([
            top(hero=("🎯", "🪄")), sub(""),
            sub(f" {E['warn']} {mono('.makear cringe')}"),
            sub(f" {E['dot']} {sc('phir')} {mono('.r <emoji>')} {sc('bhejo — 3 tak')}"),
            sub(f" {E['dot']} {sc('60 sec me')} {mono('.ar cringe')} {sc('se use karo')}"),
            sub(FOOT), close()]))
    if name in AR_PRESETS:
        return await eor(event, f"{E['lock']} {mono(name)} {sc('preset hai — rename karo')}")
    AR_BUILD[int(event.sender_id or 0)] = {
        "name": name, "items": [], "until": time.time() + 60}
    return await eor(event, "\n".join([
        top(hero=("🎯", "🪄")), sub(""),
        sub(f" {E['ok']} {sc('combo banao')} {E['arrow']} {mono(name)}"),
        sub(""),
        sub(f" {E['dot']} {mono('.r <emoji>')} {sc('— ek-ek karke 3 tak')}"),
        sub(f" {E['dot']} {mono('.rem ' + name)} {sc('cancel')}"),
        sub(f" {E['clock']} {sc('60 sec')}"),
        sub(FOOT), close()]))


@register_cmd("r")
async def cmd_r(event, arg):
    """.r <emoji|id> — combo me emoji add (makear ke baad)"""
    _ar_clean()
    uid = int(event.sender_id or 0)
    st = AR_BUILD.get(uid)
    if not st:
        return await eor(event, f"{E['warn']} {sc('pehle')} {mono('.makear <name>')} "
                                f"{sc('chalao')}")
    raw = (arg or "").strip()
    if not raw:
        return await eor(event, f"{E['dot']} {mono('.r <emoji ya emoji-id>')}")
    if len(st["items"]) >= AR_MAX:
        return await eor(event, f"{E['lock']} {sc('3 emoji full')} {E['dot']} "
                                f"{mono('.ar ' + st['name'])} {sc('se use karo')}")

    item = _r_item(event, raw.split()[0])
    if item is None:
        return await eor(event, f"{E['no']} {sc('emoji samajh nahi aaya')} {E['dot']} "
                                f"{mono('.r 😂')} {sc('ya')} {mono('.r <emoji-id>')}")

    st["items"].append(item)
    AR_BUILD[uid] = st
    n = len(st["items"])
    if n >= AR_MAX:
        AR_SAVED[st["name"]] = st["items"][:AR_MAX]
        _ar_save()
        AR_BUILD.pop(uid, None)
        conf = await eor(event, "\n".join([
            top(hero=("🎯", "💎")), sub(""),
            sub(f" {E['ok']} {sc('combo saved')} {E['arrow']} {mono(st['name'])}"),
            sub(f" {E['dot']} {mono(str(n))} {sc('emoji')} {E['dot']} "
                f"{_ar_names(st['items'])}"),
            sub(""),
            sub(f" {E['spark']} {mono('.ar ' + st['name'])} {sc('— reply pe lock')}"),
            sub(FOOT), close()]))
        return await _del_after(conf, 2)      # saved msg 2 sec me udta hai

    conf = await eor(event, f"{E['ok']} {sc('emoji add')} {mono(str(n))}/3 {E['dot']} "
                            f"{mono('.r <emoji>')} {sc('aur bhejo')}")
    await _del_after(conf, 3)


@register_cmd("rem")
async def cmd_rem(event, arg):
    """.rem <name> — saved combo delete"""
    name = (arg or "").strip().lower().split()[0] if (arg or "").strip() else ""
    if not name:
        got = ", ".join(sorted(AR_SAVED)) or "—"
        return await eor(event, f"{E['dot']} {mono('.rem <name>')}\n"
                                f"{E['dot']} {sc('saved')} {E['arrow']} {mono(got)}")
    uid = int(event.sender_id or 0)
    st = AR_BUILD.get(uid)
    if st and st.get("name") == name:
        AR_BUILD.pop(uid, None)
        return await eor(event, f"{E['trash']} {sc('build cancel')} {E['arrow']} {mono(name)}")
    if name not in AR_SAVED:
        if name in AR_PRESETS:
            return await eor(event, f"{E['lock']} {mono(name)} {sc('preset hai — delete nahi hoga')}")
        return await eor(event, f"{E['warn']} {sc('koi saved combo nahi')} {mono(name)}")
    AR_SAVED.pop(name, None)
    _ar_save()
    # is combo se bane locks bhi band
    for k in [k for k, v in AR_LOCK.items() if v.get("name") == name]:
        AR_LOCK.pop(k, None)
    _ar_lock_save()
    await eor(event, f"{E['trash']} {sc('combo delete')} {E['arrow']} {mono(name)}")


# ── watcher: locked user ke naye messages pe same reaction ──────


@bot.on(events.NewMessage(incoming=True))
async def reaction_lock_watcher(event):
    try:
        if not AR_LOCK:
            return
        chat = event.chat_id
        uid = int(getattr(event, "sender_id", 0) or 0)
        if not uid or chat is None:
            return
        got = AR_LOCK.get(_lock_key(chat, uid))
        if not got:
            return
        await _react_send(chat, event.id, got.get("items"))
    except Exception:
        pass



# ══════════════════════════════════════════════════════════════
#              ✅  ᴊᴏɪɴ ʀᴇǫᴜᴇꜱᴛꜱ  (.requests / .approve / .deny)
# ══════════════════════════════════════════════════════════════
async def _join_requests(event, limit=50):
    """group ke pending join requests → [(user_id, name, date)]."""
    from telethon.tl.types import InputUserEmpty
    chat = await event.get_input_chat()
    try:
        res = await bot(functions.messages.GetChatInviteImportersRequest(
            peer=chat,
            offset_date=None,
            offset_user=InputUserEmpty(),
            limit=int(limit),
            requested=True,
        ))
    except TypeError:
        res = await bot(functions.messages.GetChatInviteImportersRequest(
            peer=chat, offset_date=None, offset_user=InputUserEmpty(),
            limit=int(limit), requested=True, q=None, link=None,
        ))
    imps = list(getattr(res, "importers", None) or [])
    uids = []
    for imp in imps:
        uid = int(getattr(imp, "user_id", 0) or 0)
        if uid:
            uids.append(uid)
    names = {}
    if uids:
        try:
            for ent in await bot.get_entity(uids):
                nm = " ".join(x for x in [getattr(ent, "first_name", "") or "",
                                          getattr(ent, "last_name", "") or ""]
                              if x.strip())
                names[int(ent.id)] = (nm.strip()
                                      or getattr(ent, "username", "")
                                      or str(ent.id))
        except Exception:
            pass
    out = []
    for imp in imps:
        uid = int(getattr(imp, "user_id", 0) or 0)
        if not uid:
            continue
        out.append((uid, names.get(uid, str(uid)), getattr(imp, "date", None)))
    return out


@register_cmd("requests", "joinreq", "pending")
async def cmd_requests(event, arg):
    """.requests — pending join requests list"""
    try:
        reqs = await _join_requests(event, 50)
    except Exception as e:
        return await eor(event, f"{E['no']} {sc('requests nahi mile')} {E['arrow']} "
                                f"{mono(err_txt(e, 80))}")
    if not reqs:
        return await eor(event, f"{E['ok']} {sc('koi pending request nahi')}")
    lines = [top(hero=("✅", "🚪")), sub(""),
             sub(f" {E['note']} {sc('join requests')} {E['dot']} {mono(str(len(reqs)))}"),
             sub("")]
    for i, (uid, nm, _d) in enumerate(reqs, 1):
        lines.append(sub(f" {mono(str(i) + '.')} {sc(nm[:24])} {E['arrow']} "
                         f"{mono(str(uid))}"))
    lines += [sub(""),
              sub(f" {E['dot']} {mono('.approve all')} {sc('sab allow')}"),
              sub(f" {E['dot']} {mono('.approve 1 2')} {sc('number se')}"),
              sub(f" {E['dot']} {mono('.deny all')} {sc('sab reject')}"),
              sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("approve", "allow")
async def cmd_approve(event, arg):
    """.approve <n|all|@user|id> — join request allow"""
    a = (arg or "").strip()
    if not a:
        return await eor(event, f"{E['dot']} {mono('.requests')} {sc('list dekho')}\n"
                                f"{E['dot']} {mono('.approve all')} / {mono('.approve 1 2')}")
    try:
        reqs = await _join_requests(event, 100)
    except Exception as e:
        return await eor(event, f"{E['no']} {sc('requests nahi mile')} {E['arrow']} "
                                f"{mono(err_txt(e, 80))}")
    if not reqs:
        return await eor(event, f"{E['dot']} {sc('koi pending request nahi')}")

    picked = []
    if a.lower() in ("all", "sab"):
        picked = list(reqs)
    else:
        for tok in a.replace(",", " ").split():
            t = tok.lstrip("@")
            if t.isdigit():
                n = int(t)
                if 1 <= n <= len(reqs):
                    picked.append(reqs[n - 1])
                    continue
                for uid, nm, _d in reqs:
                    if uid == n:
                        picked.append((uid, nm, _d))
                        break
            else:
                for uid, nm, _d in reqs:
                    if str(nm).lower() == t.lower():
                        picked.append((uid, nm, _d))
                        break
    seen, uniq = set(), []
    for r in picked:
        if r[0] not in seen:
            seen.add(r[0])
            uniq.append(r)
    if not uniq:
        return await eor(event, f"{E['warn']} {sc('koi match nahi')} {E['dot']} "
                                f"{mono('.requests')}")

    chat = await event.get_input_chat()
    ok = 0
    for uid, _nm, _d in uniq:
        try:
            await bot(functions.messages.HideChatJoinRequestRequest(
                peer=chat, user_id=await bot.get_input_entity(uid),
                approved=True))
            ok += 1
        except Exception:
            pass
    conf = await eor(event, f"{E['ok']} {sc('approved')} {E['arrow']} "
                            f"{mono(str(ok))}/{mono(str(len(uniq)))}")
    await _del_after(conf, 6)


@register_cmd("deny", "reject")
async def cmd_deny(event, arg):
    """.deny <n|all> — join request reject"""
    a = (arg or "").strip()
    if not a:
        return await eor(event, f"{E['dot']} {mono('.deny all')} {sc('ya')} "
                                f"{mono('.deny 1 2')}")
    try:
        reqs = await _join_requests(event, 100)
    except Exception as e:
        return await eor(event, f"{E['no']} {mono(err_txt(e, 70))}")
    if not reqs:
        return await eor(event, f"{E['dot']} {sc('koi pending request nahi')}")
    if a.lower() in ("all", "sab"):
        picked = list(reqs)
    else:
        picked = []
        for tok in a.replace(",", " ").split():
            t = tok.lstrip("@")
            if t.isdigit() and 1 <= int(t) <= len(reqs):
                picked.append(reqs[int(t) - 1])
    chat = await event.get_input_chat()
    ok = 0
    for uid, _nm, _d in picked:
        try:
            await bot(functions.messages.HideChatJoinRequestRequest(
                peer=chat, user_id=await bot.get_input_entity(uid),
                approved=False))
            ok += 1
        except Exception:
            pass
    conf = await eor(event, f"{E['no']} {sc('rejected')} {E['arrow']} "
                            f"{mono(str(ok))}/{mono(str(len(picked)))}")
    await _del_after(conf, 6)


@register_cmd("rembots", "delbots", owner_only=True)
async def cmd_rembots(event, arg):
    """.rembots @bot1 — saved bot list se hatao"""
    names = [p.lstrip("@").strip() for p in (arg or "").split() if p.strip()]
    if not names:
        got = ", ".join("@" + b for b in SAVED_BOTS) or "—"
        return await eor(event, "\n".join([
            top(hero=("🗑", "🤖")), sub(""),
            sub(f" {E['bot']} {sc('saved bots')} {mono(str(len(SAVED_BOTS)))}"),
            sub(""),
            sub(f" {E['dot']} {mono(got)}"),
            sub(""),
            sub(f" {E['warn']} {mono('.rembots @bot1 @bot2')}"),
            sub(f" {E['dot']} {mono('.rembots all')}"),
            sub(FOOT), close()]))
    if names[0].lower() == "all":
        n = len(SAVED_BOTS)
        SAVED_BOTS.clear()
        save_json(F_BOTS, SAVED_BOTS)
        return await done(event, f"{E['trash']} {sc('saare bots hate')} {mono(str(n))}", secs=6)
    low = {b.lower() for b in SAVED_BOTS}
    removed, missing = [], []
    for n in names:
        key = n.lower()
        if key in low:
            SAVED_BOTS[:] = [b for b in SAVED_BOTS if b.lower() != key]
            low.discard(key)
            removed.append(n)
        else:
            missing.append(n)
    save_json(F_BOTS, SAVED_BOTS)
    lines = [top(hero=("🗑", "🤖")), sub("")]
    if removed:
        lines += [sub(f" {E['ok']} {sc('remove')} {E['arrow']} "
                      f"{mono(', '.join('@' + r for r in removed))}")]
    if missing:
        lines += [sub(f" {E['warn']} {sc('list me nahi tha')} {E['arrow']} "
                      f"{mono(', '.join('@' + m for m in missing))}")]
    lines += [sub(f" {E['dot']} {sc('baaki')} {mono(str(len(SAVED_BOTS)))}"),
              sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("lockmsg", owner_only=True)
async def cmd_lockmsg(event, arg):
    """.lockmsg on/off — is chat me lock message on/off"""
    global LOCKMSG
    key = str(int(event.chat_id)) if event.chat_id else "0"
    a = (arg or "").strip().lower()
    cur = lockmsg_on(event.chat_id)

    if a in ("on", "1", "yes"):
        LOCKMSG[key] = True
        save_json(F_LOCKMSG, LOCKMSG)
        conf = await eor(event, f"{E['ok']} {sc('lock message')} {E['arrow']} {mono('ON')} "
                                f"{E['dot']} {sc('is chat me')}")
    elif a in ("off", "0", "no"):
        LOCKMSG[key] = False
        save_json(F_LOCKMSG, LOCKMSG)
        conf = await eor(event, f"{E['no']} {sc('lock message')} {E['arrow']} {mono('OFF')} "
                                f"{E['dot']} {sc('chup-chaap ignore')}")
    else:
        return await eor(event, "\n".join([
            top(hero=("🔐", "🔕")), sub(""),
            sub(f" {E['lock']} {sc('is chat ka lock msg')} {E['arrow']} "
                f"{mono('ON' if cur else 'OFF')}"),
            sub(f" {E['globe']} {sc('global')} {E['arrow']} "
                f"{mono('ON' if GLOCK.get('on', True) else 'OFF')} {E['dot']} "
                f"{mono('.glockmsg')}"),
            sub(""),
            sub(f" {E['dot']} {mono('.lockmsg off')} {sc('— sirf is chat me band')}"),
            sub(f" {E['dot']} {mono('.lockmsg on')} {sc('— wapas chalu')}"),
            sub(f" {E['dot']} {mono('.glockmsg off')} {sc('— har jagah band')}"),
            sub(FOOT), close()]))
    await _del_after(conf, 5)


@register_cmd("glockmsg", "lockmsgglobal", owner_only=True)
async def cmd_glockmsg(event, arg):
    """.glockmsg on/off — lock message POORE bot me on/off"""
    a = (arg or "").strip().lower()
    if a in ("on", "1", "yes"):
        GLOCK["on"] = True
        save_json(F_GLOCK, GLOCK)
        conf = await eor(event, f"{E['ok']} {sc('lock message global')} {E['arrow']} "
                                f"{mono('ON')} {E['dot']} {sc('sab chats')}")
    elif a in ("off", "0", "no"):
        GLOCK["on"] = False
        save_json(F_GLOCK, GLOCK)
        conf = await eor(event, f"{E['no']} {sc('lock message global')} {E['arrow']} "
                                f"{mono('OFF')} {E['dot']} {sc('har jagah chup')}")
    else:
        return await eor(event, "\n".join([
            top(hero=("🌐", "🔕")), sub(""),
            sub(f" {E['globe']} {sc('global lock msg')} {E['arrow']} "
                f"{mono('ON' if GLOCK.get('on', True) else 'OFF')}"),
            sub(""),
            sub(f" {E['dot']} {mono('.glockmsg off')} {sc('— poore bot me band')}"),
            sub(f" {E['dot']} {mono('.glockmsg on')} {sc('— wapas chalu')}"),
            sub(f" {E['dot']} {mono('.lockmsg off')} {sc('— sirf is chat ke liye')}"),
            sub(FOOT), close()]))
    await _del_after(conf, 5)


@register_cmd("prefix", owner_only=True)
async def cmd_prefix(event, arg):
    """.prefix on/off — command ke liye dot zaroori hai ya nahi"""
    a = (arg or "").strip().lower()
    if a in ("on", "1", "yes", "dot"):
        PREFIX_STATE["optional"] = False
        save_json(F_PREFIX, PREFIX_STATE)
        conf = await eor(event, "\n".join([
            top(hero=("🔣", "🔒")), sub(""),
            sub(f" {E['lock']} {sc('prefix')} {E['arrow']} {mono('ON')}"),
            sub(f" {E['dot']} {sc('ab sirf')} {mono('.hy')} {sc('chalega')}"),
            sub(f" {E['dot']} {sc('bina dot wala band')}"),
            sub(FOOT), close()]))
    elif a in ("off", "0", "no", "free"):
        PREFIX_STATE["optional"] = True
        save_json(F_PREFIX, PREFIX_STATE)
        conf = await eor(event, "\n".join([
            top(hero=("🔣", "🔓")), sub(""),
            sub(f" {E['ok']} {sc('prefix')} {E['arrow']} {mono('OFF')}"),
            sub(f" {E['dot']} {mono('.hy')} {sc('·')} {mono('hy')} {sc('·')} {mono('Hy')} "
                f"{sc('— teeno chalenge')}"),
            sub(f" {E['dot']} {sc('sirf owner / apna account')}"),
            sub(FOOT), close()]))
    else:
        return await eor(event, "\n".join([
            top(hero=("🔣", "⌨️")), sub(""),
            sub(f" {E['gear']} {sc('prefix')} {E['arrow']} "
                f"{mono('optional' if PREFIX_STATE['optional'] else 'required')}"),
            sub(""),
            sub(f" {E['dot']} {mono('.prefix off')} {sc('— bina dot bhi chale')}"),
            sub(f" {E['dot']} {mono('.prefix on')} {sc('— dot zaroori')}"),
            sub(FOOT), close()]))
    await _del_after(conf, 6)


@register_cmd("check")
async def cmd_check(event, arg):
    """.check <cmd> — command kya karta hai, kahan chalta hai, state kya hai"""
    name = (arg or "").strip().lower().lstrip(".")
    if not name:
        return await eor(event, "\n".join([
            top(hero=("🔍", "📋")), sub(""),
            sub(f" {E['dot']} {mono('.check <command>')}"),
            sub(f" {E['dot']} {sc('example')} {mono('.check lock')}"),
            sub(FOOT), close()]))
    main = aliases.get(name, name)
    data = commands.get(main)
    if not data:
        return await eor(event, f"{E['no']} {sc('command nahi mila')} {mono(name)}")

    fn = data.get("func")
    doc = (getattr(fn, "__doc__", "") or "").strip().split("\n")[0]
    cat = "—"
    for title, items in _MENU:
        for c, d in items:
            if c == main:
                cat = _sect_name(title)
                break
        if cat != "—":
            break
    al = sorted([k for k, v in aliases.items() if v == main])
    try:
        src = inspect.getsourcefile(fn) or "—"
    except Exception:
        src = "—"

    # live state
    st = []
    if main in ("lockmsg", "glockmsg"):
        st.append(("lock msg (is chat)", "ON" if lockmsg_on(event.chat_id) else "OFF"))
        st.append(("lock msg (global)", "ON" if GLOCK.get("on", True) else "OFF"))
    if main in ("prefix",):
        st.append(("prefix", "optional" if PREFIX_STATE.get("optional") else "required"))
    if main in ("ar", "makear", "r", "rem"):
        st.append(("presets", str(len(AR_PRESETS))))
        st.append(("saved combos", str(len(AR_SAVED))))
        st.append(("locks is chat", str(len(_ar_chat_locks(event.chat_id)))))
        st.append(("locks total", str(len(AR_LOCK))))
    if main in ("sar", "selfar", "selfsar", "sart"):
        st.append(("self react", _ar_names(SELF_REACT) or "off"))
        st.append(("self react items", str(len(SELF_REACT))))
    if main in ("approve", "deny", "requests"):
        st.append(("mode", "join requests approval"))
    if main in ("autoread",):
        st.append(("autoread", ", ".join(sorted(AUTOREAD)) or "off"))
    if main in ("antidel",):
        st.append(("antidel", str(len(ANTIDEL))))
    if main in ("autobc", "autofw"):
        d = AUTOBR if main == "autobc" else AUTOFW
        st.append(("status", "on" if d.get("on") else "off"))
        st.append(("delay", str(d.get("delay", 0))))
    if main in ("areply",):
        st.append(("auto reply", "on" if AREPLY else "off"))
    if main in ("ghost",):
        st.append(("ghost", "on" if GHOST.get("on") else "off"))
    if main in ("gban", "gbanlist"):
        st.append(("gban users", str(len(GBAN))))
    if main in ("addbots", "rembots", "listbots"):
        st.append(("saved bots", str(len(SAVED_BOTS))))
    if main in ("mute", "unmute", "getmute"):
        st.append(("local muted", str(len(MUTED))))
    if main in ("vsave", "vplay", "vlist"):
        st.append(("saved songs", str(len(VSAVE))))
    if main in ("setchannel", "save"):
        st.append(("saved channel", str(SAVED_CHANNEL)))
    if main in ("afk",):
        st.append(("afk", "on" if AFK.get("active") else "off"))
    if main in ("echo",):
        st.append(("echo users", str(len(ECHO_USERS))))

    lines = [top(hero=("🔍", "📋")), sub(""),
             sub(f" {E['bolt']} {mono('.' + main)}"),
             sub(f" {E['dot']} {sc('kaam')} {E['arrow']} {sc(doc or '—')[:60]}")]
    if al:
        lines.append(sub(f" {E['dot']} {sc('alias')} {E['arrow']} "
                         f"{mono(', '.join('.' + a for a in al))}"))
    lines += [
        sub(f" {E['dot']} {sc('category')} {E['arrow']} {sc(cat)}"),
        sub(f" {E['dot']} {sc('owner only')} {E['arrow']} "
            f"{mono('YES' if data.get('owner_only') or main in OWNER_ONLY_EXTRA else 'NO')}"),
        sub(f" {E['dot']} {sc('group only')} {E['arrow']} "
            f"{mono('YES' if data.get('group_only') else 'NO')}"),
        sub(f" {E['dot']} {sc('reply needed')} {E['arrow']} "
            f"{mono('YES' if data.get('needs_reply') else 'NO')}"),
    ]
    if st:
        lines += [sub(""), sub(f" {E['gem']} {sc('live state')}")]
        for k, v in st:
            lines.append(sub(f" {E['dot']} {sc(k)} {E['arrow']} {mono(v)}"))
    lines += [sub(""), sub(f" {E['dot']} {sc('file')} {E['arrow']} {mono(str(src)[-24:])}"),
              sub(FOOT), close()]
    await eor(event, "\n".join(lines))




# ══════════════════════════════════════════════════════════════
#                          ᴛᴏᴏʟs
# ══════════════════════════════════════════════════════════════
@register_cmd("tts")
async def cmd_tts(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.tts <text>')}")
    st = await flash(event, f"{E['note']} {sc('audio bana raha hoon')}…", secs=30)
    fname = os.path.join(TEMP_PATH, f"tts_{int(time.time())}.mp3")
    try:
        gTTS(text=arg[:3000], lang="hi", slow=False).save(fname)
    except Exception:
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('tts fail (network?)')}")
    try:
        await bot.send_file(event.chat_id, fname, caption=f"{E['note']} {sc('tts')}\n{FOOT}")
        try:
            await event.delete()
        except Exception:
            pass
    except Exception as e:
        await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")
    finally:
        try:
            os.remove(fname)
        except Exception:
            pass
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass


@register_cmd("qrcode")
async def cmd_qrcode(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.qrcode <text>')}")
    st = await flash(event, f"{E['tool']} {sc('qr bana raha hoon')}…", secs=20)
    fname = os.path.join(TEMP_PATH, f"qr_{int(time.time())}.png")
    try:
        qrcode.make(arg[:2000]).save(fname)
        await bot.send_file(event.chat_id, fname, caption=f"{E['tool']} {sc('qr')}\n{FOOT}")
        try:
            await event.delete()
        except Exception:
            pass
    except Exception as e:
        await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")
    finally:
        try:
            os.remove(fname)
        except Exception:
            pass
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass


@register_cmd("fancy")
async def cmd_fancy(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.fancy <text>')}")
    t = arg[:1500]
    styles = [f"★彡 {t} 彡★", f"『 {t} 』", f"✦ {t} ✦", f"☾ {t} ☽", f"➳ {t} ➳",
              f"⚡ {t} ⚡", f"❖ {t} ❖", f"⫷ {t} ⫸", f"♛ {t} ♛",
              f"✧･ﾟ: *✧ {t} ✧*:･ﾟ✧", f"꧁ {t} ꧂", f"░▒▓ {t} ▓▒░",
              f"➶➶ {t} ➷➷", f"✿ {t} ✿", f"⟪ {t} ⟫", f"⌁ {t} ⌁",
              f"🜲 {t} 🜲", f"⟡ {t} ⟡", f"⬢ {t} ⬢"]
    await eor(event, f"{E['spark']} {sc('fancy styles')}\n{'─' * 22}\n" + "\n".join(styles))


@register_cmd("style")
async def cmd_style(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.style <text>')}")
    t = arg[:1500]
    await eor(event, f"{E['spark']} {sc('style')}\n{'─' * 22}\n"
                     f"{scr(t)}\n{sb(t)}\n{scrb(t)}\n{bs(t)}\n{its(t)}\n{sbi(t)}\n{mono(t)}\n{dbl(t)}\n{sc(t)}")


@register_cmd("emoji")
async def cmd_emoji(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.emoji <text>')}")
    pool = ["✦", "❖", "⟡", "♛", "⚜️", "🔱", "💠", "🪬", "🧿", "⛓️", "🗝️",
            "🧭", "🛰️", "🧬", "🪐", "🌠", "🫧", "🕸️", "🪞", "🗡️", "🛡️",
            "🌩️", "🜛", "✺", "⟐", "⬡", "⌬", "❂", "✵", "🌌"]
    deco = "".join(random.choice(pool) for _ in range(8))
    await eor(event, f"{deco}\n{arg[:1500]}\n{deco}")


@register_cmd("calc")
async def cmd_calc(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.calc <expression>')}")
    expr = arg.replace(" ", "")
    allowed = set("0123456789+-*/().%")
    if any(c not in allowed for c in expr):
        return await eor(event, f"{E['no']} {sc('sirf')} {mono('0-9 + - * / ( ) . %')}")
    try:
        res = eval(expr, {"__builtins__": None}, {})
    except Exception:
        return await eor(event, f"{E['no']} {sc('invalid expression')}")
    await eor(event, f"{E['tool']} {sc('calc')}\n{'─' * 22}\n"
                     f"{E['dot']} {mono(expr)}\n{E['arrow']} {mono(str(res))}")


def _http_json(url, timeout=8):
    try:
        return requests.get(url, timeout=timeout).json()
    except Exception:
        return None


@register_cmd("weather")
async def cmd_weather(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.weather <city>')}")
    st = await flash(event, f"{E['wave']} {sc('fetching')}…", secs=15)
    geo = _http_json(f"https://geocoding-api.open-meteo.com/v1/search?name={arg}&count=1")
    if not geo or not geo.get("results"):
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('city nahi mili')}")
    r = geo["results"][0]
    w = _http_json(f"https://api.open-meteo.com/v1/forecast?latitude={r.get('latitude')}"
                   f"&longitude={r.get('longitude')}&current_weather=true")
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    if not w or not w.get("current_weather"):
        return await eor(event, f"{E['no']} {sc('weather data nahi mila')}")
    cw = w["current_weather"]
    await eor(event, "\n".join([top(), sub(f"{E['wave']} {sc('weather')}"), sub(""),
                                sub(f" {E['dot']} {sc('city')} ‣ {r.get('name')}"),
                                sub(f" {E['dot']} {sc('temp')} ‣ {mono(str(cw.get('temperature')) + '°C')}"),
                                sub(f" {E['dot']} {sc('wind')} ‣ {mono(str(cw.get('windspeed')) + ' km/h')}"),
                                sub(""), sub(FOOT), close()]))


@register_cmd("ip")
async def cmd_ip(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.ip <ip>')}")
    st = await flash(event, f"{E['globe']} {sc('lookup')}…", secs=15)
    d = _http_json(f"http://ip-api.com/json/{arg}")
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    if not d or d.get("status") != "success":
        return await eor(event, f"{E['no']} {sc('invalid ip')}")
    await eor(event, "\n".join([top(), sub(f"{E['globe']} {sc('ip info')}"), sub(""),
                                sub(f" {E['dot']} {sc('ip')}   ‣ {mono(str(d.get('query')))}"),
                                sub(f" {E['dot']} {sc('country')} ‣ {d.get('country')}"),
                                sub(f" {E['dot']} {sc('city')} ‣ {d.get('city')}"),
                                sub(f" {E['dot']} {sc('isp')} ‣ {d.get('isp')}"),
                                sub(""), sub(FOOT), close()]))


@register_cmd("short")
async def cmd_short(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.short <url>')}")
    if not arg.startswith(("http://", "https://")):
        arg = "http://" + arg
    st = await flash(event, f"{E['chain']} {sc('shortening')}…", secs=15)
    try:
        short_url = requests.get(
            f"http://tinyurl.com/api-create.php?url={requests.utils.requote_uri(arg)}",
            timeout=8).text.strip()
    except Exception:
        if st is not None:
            try:
                await st.delete()
            except Exception:
                pass
        return await eor(event, f"{E['no']} {sc('short fail (network?)')}")
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await eor(event, f"{E['chain']} {sc('short url')}\n{'─' * 22}\n{mono(short_url)}")


@register_cmd("music", "song", "play", "mp3")
async def cmd_music(event, arg):
    """`.music freaked out` — words se search · link bhi chalega"""
    query = (arg or "").strip()
    if not query:
        return await eor(event, guide_music())

    # ── animation: plain message (100% reliable edits) ──
    phase = {"v": "search"}
    status = await eor(event, load_card("search", query, 0, 0), plain=True)
    stop = asyncio.Event()
    lt = asyncio.create_task(
        _music_loader(status, query, MUSIC_FRAMES, stop, phase))
    sent_rich = False
    try:
        phase["v"] = "fetch"
        path, info = await yt_download(query, audio=True)
        if not path:
            raise RuntimeError("song nahi mila")
        title = str((info or {}).get("title") or query).strip()
        dur = int((info or {}).get("duration") or 0)
        if dur > 1200:
            raise RuntimeError(f"song bahut lambi hai ({_mmss(dur)})")

        ext = os.path.splitext(path)[1].lower()
        voice = ext in (".ogg", ".opus")
        safe = re.sub(r'[\\/:*?"<>|]+', " ", title).strip()[:70] or "Nik Song"
        nice = os.path.join(TEMP_PATH, f"{safe}{ext}")
        try:
            os.replace(path, nice)
            path = nice
        except Exception:
            pass

        size_kb = 0
        try:
            size_kb = os.path.getsize(path) // 1024
        except Exception:
            pass

        # ── ab bhej rahe hain: animation chalti rahegi jab tak MP3 ready na ho
        phase["v"] = "send"
        try:
            await status.edit(load_card("send", query, 0, 95))
        except Exception:
            pass
        rows = [
            ("duration", _mmss(dur) if dur else "—"),
            ("quality", "mp3 / opus"),
            ("size", (f"{size_kb} kb" if size_kb else "—")),
            ("artist", "Nik Userbot"),
        ]
        btns = [("OWNER", "https://t.me/%s" % OWNER_TAG.lstrip("@"), "blue")]
        cover = _art_cover((info or {}).get("thumbnail"))
        sent_rich = await rich_media(
            event, path, kind="audio", title=title[:110],
            subtitle="now playing", rows=rows,
            audio={"duration": dur, "title": title[:64],
                   "performer": "Nik Userbot", "voice": voice},
            fname=title, buttons=btns, cover=cover)
        if cover:
            try:
                os.remove(cover)
            except Exception:
                pass
        if not sent_rich:
            caption = (f"{E['note']} {title[:90]}\n"
                       f"{E['dot']} duration ‣ {_mmss(dur)}   quality ‣ mp3/opus\n"
                       f"{E['spark']} powered by {OWNER_TAG}")
            try:
                await bot.send_file(event.chat_id, path, voice_note=voice,
                                    caption=caption, title=title,
                                    performer="Nik Userbot", duration=dur,
                                    supports_streaming=True)
            except Exception:
                await bot.send_file(event.chat_id, path, caption=caption)
        _ui_hard_delete(event.chat_id, getattr(event, "id", None))
    except Exception as e:
        await eor(event, "\n".join([
            top(), sub(""),
            sub(f"{E['no']} music fail"),
            sub(""),
            sub(f"{E['arrow']} {err_txt(e, 90)}"),
            sub(""),
            sub(f"{E['dot']} link bhejo ya simple words"),
            sub(f"{E['dot']} .help music"),
            sub(""), sub(FOOT), close(),
        ]))
    finally:
        stop.set()
        lt.cancel()
        if status is not None:
            try:
                await status.delete()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
#            ⚡  ʟᴏᴀᴅᴇʀ  ·  spinner + progress bar animation
# ══════════════════════════════════════════════════════════════
# Terminal-style frame sets (braille orbit, blocks, arrows) —
# har phase ka apna spinner + apni progress bar + emoji.
MUSIC_FRAMES = ["▰▱▱▱▱", "▰▰▱▱▱", "▰▰▰▱▱", "▰▰▰▰▱", "▰▰▰▰▰"]

SPIN_BRAILLE = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
SPIN_ORBIT = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPIN_BLOCKS = ["▁", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃"]
SPIN_ARROW = ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"]
SPIN_CIRCLE = ["◐", "◓", "◑", "◒"]
SPIN_SNAKE = ["⠈", "⠐", "⠠", "⢀", "⡀", "⠄", "⠂", "⠁"]

# phase → (emoji, label, spinner frames)
# emoji sirf wahi jo premium packs me hain → custom emoji ban jayenge
LOAD_PHASES = {
    "search":  ("👀", "searching", SPIN_ORBIT),
    "fetch":   ("🔮", "fetching", SPIN_BRAILLE),
    "down":    ("⬇️", "downloading", SPIN_BLOCKS),
    "convert": ("🪄", "converting", SPIN_CIRCLE),
    "send":    ("✈️", "sending", SPIN_ARROW),
    "save":    ("📌", "saving", SPIN_SNAKE),
    "think":   ("🔮", "thinking", SPIN_BRAILLE),
}

BAR_EMPTY = "▱"
BAR_FULL = "▰"


def load_bar(pct, width=10):
    """progress bar — 0-100 → ▰▰▰▱▱▱▱▱▱▱"""
    pct = max(0, min(100, int(pct)))
    n = int(round(width * pct / 100.0))
    return BAR_FULL * n + BAR_EMPTY * (width - n)


def load_card(phase, text="", spin_i=0, pct=0, note=""):
    """stylish loader — do line: spinner + label, niche bar.

        🔍  searching  freaked out
        ⠹  ▰▰▰▱▱▱▱▱▱▱  34%
    """
    ph = (phase or "fetch").lower()
    emo, label, spin = LOAD_PHASES.get(ph, LOAD_PHASES["fetch"])
    sp = spin[spin_i % len(spin)]
    head = f"{emo}  {label}"
    if text:
        head += f"  {str(text)[:38]}"
    line2 = f"{sp}  {load_bar(pct)}  {pct:>3d}%"
    if note:
        line2 += f"  {note}"
    return f"{head}\n{line2}"


async def _music_loader(status, query, frames, stop, phase=None):
    """loader — phase badalte hi spinner/badge badal jaata hai.

    Progress bar 0→95 tak dheere-dheere bharta hai (asli kaam ke saath
    match karne ke liye), 100% sirf tab jab kaam poora ho.
    """
    i = 0
    pct = 0
    tick = 0
    while not stop.is_set():
        try:
            ph = (phase or {}).get("v", "fetch")
            if ph in ("sending", "send"):
                ph = "send"
            elif ph in ("saving", "save"):
                ph = "save"
            elif ph in ("fetching",):
                ph = "fetch"
            # bar dheere badhta hai, 95 pe ruk jaata hai
            pct = min(95, int(tick * 4.5))
            await status.edit(load_card(ph, query, i, pct))
        except MessageNotModifiedError:
            pass
        except Exception:
            pass
        i += 1
        tick += 1
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.8)
            return
        except asyncio.TimeoutError:
            pass
        except Exception:
            return


# ══════════════════════════════════════════════════════════════
#                          ɴᴏᴛᴇs
# ══════════════════════════════════════════════════════════════
@register_cmd("notesadd")
async def cmd_notesadd(event, arg):
    if not arg:
        return await eor(event, f"{E['dot']} {mono('.notesadd <text>')}")
    NOTES[int(event.chat_id)] = arg.strip()
    save_json(F_NOTES, {str(k): v for k, v in NOTES.items()})
    await done(event, f"{E['key']} {sc('note saved')} {mono(str(len(arg)))} {sc('chars')}", secs=6)


@register_cmd("noteslist")
async def cmd_noteslist(event, arg):
    n = NOTES.get(int(event.chat_id))
    if not n:
        return await eor(event, f"{E['note']} {sc('koi note nahi')}")
    await eor(event, f"{E['key']} {sc('note')}\n{'─' * 22}\n{n[:3000]}")


@register_cmd("notesdelete")
async def cmd_notesdelete(event, arg):
    if NOTES.pop(int(event.chat_id), None) is None:
        return await eor(event, f"{E['warn']} {sc('note tha hi nahi')}")
    save_json(F_NOTES, {str(k): v for k, v in NOTES.items()})
    await done(event, f"{E['trash']} {sc('note delete')}", secs=6)


@register_cmd("banner")
async def cmd_banner(event, arg):
    global MENU_BANNER
    if not event.is_reply:
        return await eor(event, f"{E['no']} {sc('photo/video pe reply karke')} {mono('.banner')}")
    r = await event.get_reply_message()
    if not getattr(r, "media", None):
        return await eor(event, f"{E['no']} {sc('sirf photo/video')}")
    st = await flash(event, f"{E['wand']} {sc('banner set')}…", secs=20)
    try:
        saved = await r.forward_to("me")
    except Exception:
        try:
            raw = await r.download_media(file=bytes)
            if not raw:
                return await eor(event, f"{E['no']} {sc('download fail')}")
            bio = BytesIO(raw); bio.name = "banner.jpg"
            saved = await bot.send_file("me", bio)
        except Exception as e:
            return await eor(event, f"{E['no']} {mono(err_txt(e, 60))}")
    MENU_BANNER = [int(saved.chat_id), int(saved.id)]
    save_json(F_BANNER, MENU_BANNER)
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['wand']} {sc('banner set')} {E['arrow']} {mono(str(saved.id))}\n"
                      f"{E['dot']} {mono('.menu')} {sc('ke saath aayega')}", secs=8)


@register_cmd("rembanner")
async def cmd_rembanner(event, arg):
    global MENU_BANNER
    if not MENU_BANNER:
        return await eor(event, f"{E['warn']} {sc('banner set hai hi nahi')}")
    try:
        await bot.delete_messages(MENU_BANNER[0], [MENU_BANNER[1]])
    except Exception:
        pass
    MENU_BANNER = None
    save_json(F_BANNER, None)
    await done(event, f"{E['trash']} {sc('banner hata diya')}", secs=6)


# ══════════════════════════════════════════════════════════════
#                          ᴄʟᴏɴᴇ
# ══════════════════════════════════════════════════════════════
@register_cmd("copy", "cp", owner_only=True)
async def cmd_copy(event, arg):
    global CLONE_ACTIVE, LAST_CLONE_ID
    target = None
    if event.is_reply:
        try:
            r = await event.get_reply_message()
            if r.sender_id:
                target = await bot.get_entity(r.sender_id)
        except Exception:
            pass
    if target is None and arg:
        try:
            target = await bot.get_entity(arg.strip())
        except Exception:
            pass
    if target is None:
        return await eor(event, f"{E['no']} {sc('reply / @user / id do')}")
    me = await bot.get_me()
    if target.id == me.id:
        return await eor(event, f"{E['warn']} {sc('khud ko clone? nope')}")
    if CLONE_ACTIVE and LAST_CLONE_ID == target.id:
        return await eor(event, f"{E['warn']} {sc('pehle se cloned hai')}")
    st = await flash(event, f"{E['wand']} {sc('clone init')}…", secs=30)
    if not CLONE_ACTIVE:
        try:
            full = await bot(functions.users.GetFullUserRequest(me.id))
            CLONE_DATA.clear()
            CLONE_DATA["name"] = me.first_name
            CLONE_DATA["last"] = me.last_name
            CLONE_DATA["bio"] = full.full_user.about
            try:
                dp = await bot.download_profile_photo("me", file=bytes, download_big=True)
                if dp:
                    b = BytesIO(dp); b.name = "orig.jpg"
                    CLONE_DATA["photo_bytes"] = b
            except Exception:
                CLONE_DATA["photo_bytes"] = None
            CLONE_ACTIVE = True
        except Exception as e:
            print(f"[clone backup] {e}")
    try:
        await bot(functions.account.UpdateProfileRequest(
            first_name=getattr(target, "first_name", "") or "",
            last_name=getattr(target, "last_name", "") or ""))
    except FloodWaitError as fw:
        await asyncio.sleep(fw.seconds)
    try:
        tf = await bot(functions.users.GetFullUserRequest(target.id))
        bio = (tf.full_user.about or "").strip()[:70]
        await bot(functions.account.UpdateProfileRequest(about=""))
        await asyncio.sleep(0.7)
        await bot(functions.account.UpdateProfileRequest(about=bio))
    except Exception:
        pass
    try:
        raw = await bot.download_profile_photo(target, file=bytes, download_big=True)
        if raw:
            b = BytesIO(raw); b.name = "clone.jpg"
            up = await bot.upload_file(b)
            try:
                cur = await bot.get_profile_photos("me", limit=1)
                if cur:
                    await bot(functions.photos.DeletePhotosRequest(id=[cur[0]]))
            except Exception:
                pass
            await bot(functions.photos.UploadProfilePhotoRequest(file=up))
    except FloodWaitError as fw:
        await asyncio.sleep(fw.seconds)
    except Exception:
        pass
    LAST_CLONE_ID = target.id
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['wand']} {sc('clone complete')} {E['heart']}\n"
                      f"{E['dot']} {mono('.normal')} {sc('se wapas aao')}", secs=8)


@register_cmd("normal", "nrml", owner_only=True)
async def cmd_normal(event, arg):
    global CLONE_ACTIVE, LAST_CLONE_ID
    if not CLONE_ACTIVE:
        return await eor(event, f"{E['warn']} {sc('koi clone active nahi')}")
    st = await flash(event, f"{E['wand']} {sc('restore init')}…", secs=30)
    try:
        await bot(functions.account.UpdateProfileRequest(
            first_name=CLONE_DATA.get("name") or "",
            last_name=CLONE_DATA.get("last") or ""))
    except Exception:
        pass
    try:
        await bot(functions.account.UpdateProfileRequest(about=""))
        await asyncio.sleep(0.7)
        await bot(functions.account.UpdateProfileRequest(about=CLONE_DATA.get("bio") or ""))
    except Exception:
        pass
    try:
        cur = await bot.get_profile_photos("me", limit=1)
        if cur:
            await bot(functions.photos.DeletePhotosRequest(id=[cur[0]]))
        if CLONE_DATA.get("photo_bytes"):
            b = CLONE_DATA["photo_bytes"]; b.name = "restore.jpg"
            up = await bot.upload_file(b)
            await bot(functions.photos.UploadProfilePhotoRequest(file=up))
    except Exception:
        pass
    CLONE_ACTIVE = False
    LAST_CLONE_ID = None
    CLONE_DATA.clear()
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    await done(event, f"{E['ok']} {sc('original restore ho gaya')} {E['heart']}", secs=8)


# ══════════════════════════════════════════════════════════════
#                    sᴜʙ-ᴜsᴇʀʙᴏᴛ (multi session)
# ══════════════════════════════════════════════════════════════
# `.addbot` = isi bot ke andar ek aur account login karna.
# Login hote hi us account pe poora dispatcher lag jata hai → us account
# se bhi saari commands chalti hain (global mode), aur session file save
# rehti hai to restart ke baad auto-connect ho jata hai.

F_SUBBOTS = "subbots.json"
PENDING_TTL = 20 * 60                  # 20 min tak `.c` accept hoga
SUBBOT_IDS: Set[int] = set()           # un accounts ke user id (owner-level)
SUBBOT_META: Dict[str, Dict[str, Any]] = {}


def norm_phone(raw):
    """+91…, 91…, 0091…, spaces / dashes — sab ek hi format me."""
    s = re.sub(r"[^\d+]", "", str(raw or "")).replace("+", "")
    if s.startswith("00"):
        s = s[2:]
    if not s.isdigit():
        return None
    if len(s) == 10:                   # bina country code → bharat
        s = "91" + s
    if not 8 <= len(s) <= 15:
        return None
    return "+" + s


def _sub_session(phone):
    return os.path.join(BASE_DIR, f"sub_{phone.lstrip('+')}")


def _save_subbots():
    save_json(F_SUBBOTS, sorted(SUBBOTS.keys()))


async def _safe_disconnect(client):
    try:
        await client.disconnect()
    except Exception:
        pass


def _pick_pending(phone=None):
    """pending login chuno (purane expire wale hata ke)."""
    now = time.time()
    for ph in list(PENDING.keys()):
        if now - PENDING[ph].get("at", now) > PENDING_TTL:
            cl = PENDING.pop(ph)["client"]
            asyncio.create_task(_safe_disconnect(cl))
    if not PENDING:
        return None, None
    if phone:
        return (phone, PENDING[phone]) if phone in PENDING else (None, None)
    ph = max(PENDING, key=lambda k: PENDING[k].get("at", 0))
    return ph, PENDING[ph]


def sub_hello(phone):
    return f"{E['ok']} {sc('subbot live')} {E['arrow']} {mono(phone)}\n" \
           f"{E['dot']} {sc('ab is account se bhi commands chalengi')}"


async def attach_subbot(phone, client):
    """login ke baad us account pe poora command dispatcher laga do."""
    register_client_handlers(client)
    try:
        me = await client.get_me()
        SUBBOTS[phone] = client
        SUBBOT_META[phone] = {"id": int(me.id), "name": me.first_name or "—",
                              "user": f"@{me.username}" if getattr(me, "username", None) else "—",
                              "at": time.time()}
        SUBBOT_IDS.add(int(me.id))
    except Exception:
        SUBBOTS[phone] = client
        SUBBOT_META[phone] = {"id": 0, "name": "—", "user": "—", "at": time.time()}
    _save_subbots()
    return True


async def load_subbots():
    """startup pe saved sessions wapas connect karo."""
    phones = load_json(F_SUBBOTS, [])
    if not isinstance(phones, list):
        return
    for raw in phones:
        phone = norm_phone(raw)
        if not phone:
            continue
        path = _sub_session(phone)
        if not os.path.exists(path + ".session"):
            continue
        try:
            cl = TelegramClient(path, API_ID, API_HASH, connection_retries=3,
                                retry_delay=2, flood_sleep_threshold=60)
            await cl.connect()
            if not await cl.is_user_authorized():
                await cl.disconnect()
                continue
            await attach_subbot(phone, cl)
            print(f"  ↳ subbot {phone} → live")
        except Exception as e:
            print(f"  ↳ subbot {phone} fail: {err_txt(e, 80)}")


def guide_addbot():
    """.help addbot / .addbot (bina number) — poora step by step guide"""
    return panel([
        f"{E['bot']} {sb('BOT MANAGER')} {E['arrow']} {sc('addbot guide')}",
        "",
        f"{E['star']} {sc('step 1')}",
        f"  {mono('.addbot +919876543210')}",
        f"  {mono('.addbot 919876543210')} {sc('(bina + bhi chalega)')}",
        "",
        f"{E['star']} {sc('step 2')}",
        f"  {sc('code aayega telegram ya sms me')}",
        f"  {mono('.c 12345')}",
        f"  {sc('spaces bhi chalenge:')} {mono('.c 1 2 3 4 5')}",
        "",
        f"{E['star']} {sc('step 3 — sirf tab jab 2fa ho')}",
        f"  {mono('.p mera_password')}",
        "",
        f"{E['star']} {sc('extra')}",
        f"  {mono('.resend')}   {sc('code dobara bhejo')}",
        f"  {mono('.cancelbot')} {sc('adha login chhodo')}",
        f"  {mono('.user')}    {sc('kaun live hai')}",
        f"  {mono('.delbot')}  {sc('bot hatao')}",
        "",
        f"{E['warn']} {sc('code na aaye to 1-2 min wait karo')}",
        f"  {sc('aur')} {mono('.resend')} {sc('maaro — telegram kabhi')}",
        f"  {sc('app ke andar hi code bhejta hai')}",
    ], title=f"{E['film']} {sc('login flow')}")


def guide_music():
    return panel([
        f"{E['wand']} {sb('MUSIC')} {E['arrow']} {sc('guide')}",
        "",
        f"{E['star']} {sc('words se search')}",
        f"  {mono('.music freaked out')}",
        f"  {mono('.music kesariya')}",
        "",
        f"{E['star']} {sc('link se')}",
        f"  {mono('.music https://youtu.be/xxxx')}",
        "",
        f"{E['star']} {sc('video / mp4')}",
        f"  {mono('.yt freaked out')}",
        f"  {mono('.yt <link>')}",
        "",
        f"{E['dot']} {sc('song seedha voice note me aayega')}",
        f"{E['dot']} {sc('ffmpeg ho to ogg/opus me convert hoga')}",
    ], title=f"{E['film']} {sc('kaise chalta hai')}")


@register_cmd("addbot", owner_only=True)
async def cmd_addbot(event, arg):
    """.addbot +9199xxxx — naya userbot session login shuru"""
    raw = (arg or "").strip()
    if not raw:
        return await eor(event, guide_addbot())
    phone = norm_phone(raw)
    if not phone:
        return await eor(event, panel([
            f"{E['no']} {sc('number samajh nahi aaya')}",
            "",
            f"{E['dot']} {mono('.addbot +919876543210')}",
            f"{E['dot']} {mono('.addbot 919876543210')}",
            f"{E['dot']} {mono('.addbot +91 98765 43210')}",
        ]))
    if phone in SUBBOTS:
        return await eor(event, panel([
            f"{E['warn']} {sc('ye number pehle se live hai')}",
            f"{E['dot']} {mono('.user')} {sc('se check karo')}",
            f"{E['dot']} {mono('.delbot ' + phone)} {sc('se hatao')}",
        ]))
    old = PENDING.pop(phone, None)
    if old:
        await _safe_disconnect(old["client"])

    st = await flash(event, f"{E['bot']} {sc('code bhej raha hoon')} {mono(phone)}…", secs=30)
    client = TelegramClient(_sub_session(phone), API_ID, API_HASH,
                            connection_retries=3, retry_delay=2,
                            flood_sleep_threshold=60)
    try:
        await client.connect()
        if await client.is_user_authorized():
            await attach_subbot(phone, client)
            if st is not None:
                try:
                    await st.delete()
                except Exception:
                    pass
            return await done(event, sub_hello(phone), secs=12)
        res = await client(functions.auth.SendCodeRequest(
            phone, API_ID, API_HASH, types.CodeSettings()))
    except FloodWaitError as e:
        await _safe_disconnect(client)
        return await eor(event, panel([
            f"{E['wait']} {sc('floodwait')} {E['arrow']} {mono(str(getattr(e, 'seconds', 0)) + 's')}",
            f"{E['dot']} {sc('thodi der baad try karo')}",
        ]))
    except PhoneNumberInvalidError:
        await _safe_disconnect(client)
        return await eor(event, panel([
            f"{E['no']} {sc('ye number telegram pe valid nahi hai')}",
            f"{E['dot']} {sc('country code ke saath dobara')} {mono('+91…')}",
        ]))
    except ApiIdInvalidError:
        await _safe_disconnect(client)
        return await eor(event, panel([
            f"{E['no']} {sc('api_id / api_hash galat hai')}",
            f"{E['dot']} {sc('my.telegram.org se naya le lo')}",
        ]))
    except Exception as e:
        await _safe_disconnect(client)
        return await eor(event, panel([
            f"{E['no']} {sc('code nahi gaya')} {E['arrow']} {mono(err_txt(e, 80))}",
            f"{E['dot']} {sc('number / net check karo ya baad me try karo')}",
        ]))

    PENDING[phone] = {"client": client, "hash": res.phone_code_hash,
                      "at": time.time(), "tries": 0}
    if st is not None:
        try:
            await st.delete()
        except Exception:
            pass
    conf = await eor(event, panel([
        f"{E['bot']} {sc('code bhej diya')}",
        f"{E['dot']} {sc('number')} ‣ {mono(phone)}",
        "",
        f"{E['star']} {sc('ab ye bhejo')}",
        f"  {mono('.c 12345')}",
        f"  {sc('spaces bhi chalenge')} {mono('.c 1 2 3 4 5')}",
        "",
        f"{E['dot']} {sc('code na aaye')} ‣ {mono('.resend')}",
        f"{E['dot']} {sc('chhodna ho')} ‣ {mono('.cancelbot')}",
        f"{E['dot']} {sc('2fa ho to code ke baad')} ‣ {mono('.p <pass>')}",
    ], title=f"{E['film']} {sc('step 1/2 done')}"))
    await _del_after(conf, 60)


@register_cmd("c", "code", owner_only=True)
async def cmd_c(event, arg):
    """.c 12345  ya  .c +9198… 12345"""
    raw = (arg or "").strip()
    if not raw:
        return await eor(event, panel([
            f"{E['dot']} {mono('.c 12345')}",
            f"{E['dot']} {mono('.c 1 2 3 4 5')}",
            f"{E['dot']} {mono('.c +919876543210 12345')} {sc('(do number ho to)')}",
        ]))
    tokens = raw.split()
    phone = None
    if len(tokens) >= 2:
        digits = re.sub(r"\D", "", tokens[0])
        if len(digits) >= 8:
            phone = norm_phone(tokens[0])
            if phone:
                raw = " ".join(tokens[1:])
    code = re.sub(r"\D", "", raw)
    if not code:
        return await eor(event, f"{E['no']} {sc('code me digit hi hone chahiye')}")

    phone_now, data = _pick_pending(phone)
    if not data:
        return await eor(event, panel([
            f"{E['warn']} {sc('koi pending login nahi')}",
            f"{E['dot']} {mono('.addbot +91XXXXXXXXXX')} {sc('se shuru karo')}",
        ]))
    try:
        await data["client"].sign_in(phone_now, code,
                                     phone_code_hash=data["hash"])
    except SessionPasswordNeededError:
        return await eor(event, panel([
            f"{E['lock']} {sc('2fa password chahiye')}",
            f"{E['dot']} {mono('.p <password>')}",
        ]))
    except PhoneCodeInvalidError:
        data["tries"] = data.get("tries", 0) + 1
        left = max(0, 4 - data["tries"])
        return await eor(event, panel([
            f"{E['no']} {sc('code galat hai')}",
            f"{E['dot']} {sc('koshish bachi')} ‣ {mono(str(left))}",
            f"{E['dot']} {mono('.c 12345')} {sc('dobara')}",
            f"{E['dot']} {mono('.resend')} {sc('naya code')}",
        ]))
    except PhoneCodeExpiredError:
        return await eor(event, panel([
            f"{E['wait']} {sc('code expire ho gaya')}",
            f"{E['dot']} {mono('.resend')} {sc('se naya lo')}",
        ]))
    except FloodWaitError as e:
        return await eor(event, panel([
            f"{E['wait']} {sc('floodwait')} {mono(str(getattr(e, 'seconds', 0)) + 's')}",
        ]))
    except Exception as e:
        return await eor(event, panel([
            f"{E['no']} {sc('login fail')} {E['arrow']} {mono(err_txt(e, 80))}",
            f"{E['dot']} {mono('.resend')} {sc('ya')} {mono('.cancelbot')}",
        ]))

    PENDING.pop(phone_now, None)
    await attach_subbot(phone_now, data["client"])
    try:
        await data["client"].send_message("me", sub_hello(phone_now))
    except Exception:
        pass
    await done(event, panel([
        f"{E['ok']} {sc('login complete')}",
        f"{E['dot']} {sc('number')} ‣ {mono(phone_now)}",
        f"{E['dot']} {sc('status')} ‣ {mono('live')} {E['ok']}",
        "",
        f"{E['star']} {sc('ab us account se bhi')} {mono('.m1')} {sc('chalega')}",
        f"{E['dot']} {mono('.user')} {sc('se list dekho')}",
    ], title=f"{E['film']} {sc('step 2/2 done')}"), secs=15)


@register_cmd("p", owner_only=True)
async def cmd_p(event, arg):
    pwd = (arg or "").strip()
    if not pwd:
        return await eor(event, f"{E['dot']} {mono('.p <2fa password>')}")
    phone, data = _pick_pending()
    if not data:
        return await eor(event, panel([
            f"{E['warn']} {sc('koi pending login nahi')}",
            f"{E['dot']} {mono('.addbot +91XXXXXXXXXX')}",
        ]))
    try:
        await data["client"].sign_in(password=pwd)
    except PasswordHashInvalidError:
        return await eor(event, panel([
            f"{E['no']} {sc('2fa password galat hai')}",
            f"{E['dot']} {mono('.p <sahi password>')}",
        ]))
    except FloodWaitError as e:
        return await eor(event, panel([
            f"{E['wait']} {sc('floodwait')} {mono(str(getattr(e, 'seconds', 0)) + 's')}",
        ]))
    except Exception as e:
        return await eor(event, panel([
            f"{E['no']} {sc('2fa login fail')} {E['arrow']} {mono(err_txt(e, 80))}",
        ]))
    PENDING.pop(phone, None)
    await attach_subbot(phone, data["client"])
    await done(event, panel([
        f"{E['ok']} {sc('2fa login complete')}",
        f"{E['dot']} {sc('number')} ‣ {mono(phone)}",
        f"{E['dot']} {sc('status')} ‣ {mono('live')} {E['ok']}",
    ]), secs=15)


@register_cmd("resend", "rcode", owner_only=True)
async def cmd_resend(event, arg):
    phone, data = _pick_pending(norm_phone(arg) if (arg or "").strip() else None)
    if not data:
        return await eor(event, panel([
            f"{E['warn']} {sc('koi pending login nahi')}",
            f"{E['dot']} {mono('.addbot +91XXXXXXXXXX')}",
        ]))
    try:
        res = await data["client"](functions.auth.ResendCodeRequest(
            phone, data["hash"]))
        data["hash"] = res.phone_code_hash
        data["at"] = time.time()
    except Exception as e:
        return await eor(event, panel([
            f"{E['no']} {sc('resend fail')} {E['arrow']} {mono(err_txt(e, 80))}",
            f"{E['dot']} {mono('.cancelbot')} {sc('karke dobara')} {mono('.addbot')}",
        ]))
    await done(event, panel([
        f"{E['bot']} {sc('naya code bhej diya')} {mono(phone)}",
        f"{E['dot']} {mono('.c 12345')} {sc('se login karo')}",
    ]), secs=20)


@register_cmd("cancelbot", "cc", owner_only=True)
async def cmd_cancelbot(event, arg):
    if not PENDING:
        return await eor(event, f"{E['warn']} {sc('koi pending login hai hi nahi')}")
    phone, data = _pick_pending(norm_phone(arg) if (arg or "").strip() else None)
    PENDING.pop(phone, None)
    await _safe_disconnect(data["client"])
    await done(event, f"{E['trash']} {sc('login cancel')} {E['arrow']} {mono(phone)}", secs=10)


@register_cmd("delbot", "removebot", owner_only=True)
async def cmd_delbot(event, arg):
    """.delbot +91…  ya  .delbot all"""
    raw = (arg or "").strip()
    if not raw:
        return await eor(event, panel([
            f"{E['dot']} {mono('.delbot +919876543210')}",
            f"{E['dot']} {mono('.delbot all')} {sc('(sab hatao)')}",
        ]))
    if raw.lower() in ("all", "*", "sab"):
        targets = list(SUBBOTS.keys())
    else:
        phone = norm_phone(raw)
        targets = [phone] if phone in SUBBOTS else []
        if not targets:
            return await eor(event, panel([
                f"{E['warn']} {sc('ye number connected nahi hai')}",
                f"{E['dot']} {mono('.user')} {sc('se list dekho')}",
            ]))
    if not targets:
        return await eor(event, f"{E['warn']} {sc('koi subbot connected nahi')}")
    removed = []
    for phone in targets:
        cl = SUBBOTS.pop(phone, None)
        meta = SUBBOT_META.pop(phone, None) or {}
        if meta.get("id"):
            SUBBOT_IDS.discard(int(meta["id"]))
        if cl is not None:
            try:
                await cl.log_out()
            except Exception:
                await _safe_disconnect(cl)
        for ext in (".session", ".session-journal"):
            try:
                os.remove(_sub_session(phone) + ext)
            except Exception:
                pass
        removed.append(phone)
    _save_subbots()
    await done(event, panel([
        f"{E['trash']} {sc('bot hata diya')}",
        *[f"{E['dot']} {mono(x)}" for x in removed],
    ]), secs=15)


@register_cmd("user", owner_only=True)
async def cmd_user(event, arg):
    rows = [f"{E['bot']} {sb('CONNECTED USERBOTS')}", ""]
    if not SUBBOTS:
        rows += [f"{E['warn']} {sc('koi extra userbot nahi')}",
                 f"{E['dot']} {mono('.addbot +919876543210')}",
                 f"{E['dot']} {mono('.help addbot')} {sc('poora guide')}"]
    for i, (phone, cl) in enumerate(SUBBOTS.items(), 1):
        meta = SUBBOT_META.get(phone) or {}
        live = "live"
        try:
            if not cl.is_connected():
                await cl.connect()
            me = await cl.get_me()
            name = meta.get("name") or me.first_name or "—"
            uid = meta.get("id") or me.id
            un = f"@{me.username}" if getattr(me, "username", None) else "—"
        except Exception:
            live, name, uid, un = "dead", meta.get("name", "—"), meta.get("id", 0), "—"
        rows += [
            f"{E['dot']} {mono(str(i))} ‣ {mono(phone)}",
            f"   {sc('name')} ‣ {name}   {sc('id')} ‣ {mono(str(uid))}",
            f"   {sc('user')} ‣ {mono(un)}   {sc('status')} ‣ {mono(live)}",
        ]
    if PENDING:
        rows += ["", f"{E['wait']} {sc('pending login')}"]
        for ph, d in PENDING.items():
            mins = max(0, int((PENDING_TTL - (time.time() - d.get("at", time.time()))) / 60))
            rows.append(f"   {E['dot']} {mono(ph)} · {sc(str(mins))} {sc('min left')}")
    await eor(event, panel(rows))


# ══════════════════════════════════════════════════════════════
#            ʙᴀᴋᴀ ᴀᴜᴛᴏᴍᴀᴛɪᴏɴ  ·  .m22
# ══════════════════════════════════════════════════════════════
# Economy / rob-kill bots (jaise @im_bakabot) ke liye automation.
#
# Pehle `.setgame` sirf DM me `/rob` bhejta tha — group me kuch nahi hota tha.
# Ab poora engine hai:
#   • target : group ke saare real users (newest → oldest)
#   • skip   : self · owner · bots · already done
#   • amt    : all balance ya fixed
#   • probe  : coins + alive/dead → rob / kill / dono / skip
#   • mode   : reply (victim ke msg pe reply) · mention · plain
#   • fail   : retry, protection/fail detect, verify code → `.solve`

F_BAKA = "baka.json"
F_BAKA_DONE = "baka_done.json"

BAKA_DEFAULTS = {
    "bot": None,          # @im_bakabot
    "prefix": "/",        # bot ka command prefix
    "mode": "reply",      # reply · mention · plain
    "rob_cmd": "rob",
    "kill_cmd": "kill",
    "bal_cmd": "bal",
    "amount": None,       # None = full balance
    "delay": 2.5,         # do actions ke beech
    "probe_wait": 4.0,    # balance reply ka intezaar
    "retries": 1,
    "probe": True,
    "fallback": "both",   # probe fail → both · rob · kill · skip
}

BAKA: Dict[str, Any] = dict(BAKA_DEFAULTS)
BAKA.update(load_json(F_BAKA, {}) or {})
if not BAKA.get("bot") and globals().get("GAME_BOT"):
    BAKA["bot"] = str(GAME_BOT).lstrip("@")      # purani setting migrate

BAKA_DONE: Dict[str, list] = load_json(F_BAKA_DONE, {}) or {}
BAKA_TASKS: Dict[str, Any] = {"auto": None, "rob": None, "kill": None}
BAKA_STOP = asyncio.Event()
BAKA_LAST: Dict[int, Dict[str, Any]] = {}
BAKA_VERIFY: Dict[int, Dict[str, Any]] = {}

_MODE_LABEL = {"reply": "reply", "mention": "mention", "plain": "plain"}


def baka_save():
    save_json(F_BAKA, BAKA)


def baka_bot():
    return (BAKA.get("bot") or "").lstrip("@")


def baka_norm_bot(raw):
    """@user · user · t.me/user · https://t.me/user → user"""
    s = (raw or "").strip()
    s = re.sub(r"^(?:https?://)?(?:t\.me/|telegram\.me/)", "", s, flags=re.I)
    s = s.lstrip("@").split("?")[0].strip("/")
    return s or None


def baka_amount(arg):
    """'all' / khaali → None (full balance), number → int"""
    a = (arg or "").strip().lower().replace(",", "")
    if not a or a in ("all", "full", "max", "sab", "poora"):
        return None
    m = re.match(r"^(\d+)$", a)
    return int(m.group(1)) if m else None


def baka_payload(cmd, target=None):
    p = f"{BAKA.get('prefix') or '/'}{cmd}"
    amt = BAKA.get("amount")
    if amt:
        p += f" {amt}"
    if target is not None and (BAKA.get("mode") or "reply") == "mention":
        un = getattr(target, "username", None)
        if un:
            p += f" @{un}"
    return p


def baka_cached_msg(chat, uid):
    """us user ka last cached message (reply karne ke liye)"""
    cache = globals().get("MSG_CACHE") or {}
    best = None
    for m in (cache.get(int(chat)) or {}).values():
        try:
            if int(getattr(m, "sender_id", 0) or 0) != int(uid):
                continue
            if best is None or int(m.id) > int(best.id):
                best = m
        except Exception:
            continue
    return best


_COIN_RE = re.compile(r"(?:₹|🪙|💰|coins?\s*[:=]?\s*)([\d][\d,]*)", re.I)
_COIN_RE2 = re.compile(r"([\d][\d,]*)\s*(?:coins?|🪙|💰)", re.I)
_DEAD_W = ("dead", "killed", "mara", "mrit", "rip", "mar gaya")
_ALIVE_W = ("alive", "zinda", "jeevit", "live hai")
_FAIL_W = ("protection", "shield", "failed", "fail", "cannot", "can't", "cant",
           "insufficient", "not enough", "no coins", "too poor", "beggar",
           "nahi", "na ho paya", "escape")
_VERIFY_W = ("verify", "verification", "captcha", "human", "enter code", "code bhejo")


def baka_parse_balance(txt):
    t = txt or ""
    for rx in (_COIN_RE, _COIN_RE2):
        m = rx.search(t)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except Exception:
                pass
    return None


def baka_parse_alive(txt):
    low = (txt or "").lower()
    if any(w in low for w in _DEAD_W):
        return False
    if any(w in low for w in _ALIVE_W):
        return True
    return None


def baka_is_fail(txt):
    low = (txt or "").lower()
    return any(w in low for w in _FAIL_W)


def baka_needs_verify(txt):
    low = (txt or "").lower()
    return any(w in low for w in _VERIFY_W)


async def baka_send(chat, cmd, target=None, reply_to=None):
    mode = BAKA.get("mode") or "reply"
    kw = {}
    if reply_to and mode == "reply":
        kw["reply_to"] = int(reply_to)
    payload = baka_payload(cmd, target)
    # reply possible nahi (us user ka koi msg cache me nahi) → mention se kaam lo
    if target is not None and mode == "reply" and not reply_to:
        un = getattr(target, "username", None)
        if un:
            payload += f" @{un}"
    return await bot.send_message(chat, payload, **kw)


async def baka_wait_reply(chat, sent_id, timeout=None):
    """target bot ka reply — BAKA_LAST tracker se"""
    timeout = timeout if timeout is not None else float(BAKA.get("probe_wait") or 4.0)
    end = time.time() + max(1.0, timeout)
    while time.time() < end:
        if BAKA_STOP.is_set():
            return None
        info = BAKA_LAST.get(int(chat))
        if info and int(info.get("id") or 0) > int(sent_id or 0):
            return info
        await asyncio.sleep(0.25)
    return None


async def baka_do(chat, target, cmd, reply_to):
    """ek target pe ek action → ok · sent · fail · verify · stopped"""
    tries = int(BAKA.get("retries") or 0) + 1
    delay = float(BAKA.get("delay") or 2.5)
    for _ in range(tries):
        if BAKA_STOP.is_set():
            return "stopped"
        try:
            sent = await baka_send(chat, cmd, target, reply_to)
        except FloodWaitError as fw:
            await asyncio.sleep(min(getattr(fw, "seconds", 5) or 5, 30))
            continue
        except Exception:
            return "fail"
        info = await baka_wait_reply(chat, getattr(sent, "id", 0), delay + 1.0)
        if not info:
            return "sent"                       # bot chup → assume ho gaya
        txt = info.get("text") or ""
        if baka_needs_verify(txt):
            BAKA_VERIFY[int(chat)] = {"text": txt[:300], "msg_id": info.get("id"),
                                      "ts": time.time()}
            return "verify"
        if baka_is_fail(txt):
            try:
                await sent.delete()          # fail hua → apna msg hatao
            except Exception:
                pass
            await asyncio.sleep(delay)
            continue
        return "ok"
    return "fail"


async def baka_probe(chat, target, reply_to):
    """balance check → (coins, alive) — jo mila wahi, warna None"""
    cmd = BAKA.get("bal_cmd") or "bal"
    try:
        sent = await baka_send(chat, cmd, target, reply_to)
    except FloodWaitError as fw:
        await asyncio.sleep(min(getattr(fw, "seconds", 5) or 5, 30))
        return None, None
    except Exception:
        return None, None
    info = await baka_wait_reply(chat, getattr(sent, "id", 0),
                                 float(BAKA.get("probe_wait") or 4.0))
    if not info:
        return None, None
    txt = info.get("text") or ""
    return baka_parse_balance(txt), baka_parse_alive(txt)


async def baka_targets(chat, include_done=True):
    """group ke real users — newest (bade id) → oldest"""
    me_ids = set(SUBBOT_IDS)
    try:
        me_ids.add(int((await bot.get_me()).id))
    except Exception:
        pass
    done = set()
    if not include_done:
        done = set(int(x) for x in (BAKA_DONE.get(str(chat)) or []))
    out = []
    async for u in bot.iter_participants(chat, aggressive=False):
        uid = int(getattr(u, "id", 0) or 0)
        if not uid or uid in me_ids or uid == int(OWNER_ID):
            continue
        if getattr(u, "bot", False) or getattr(u, "deleted", False):
            continue
        if uid in done:
            continue
        out.append(u)
    out.sort(key=lambda x: int(getattr(x, "id", 0)), reverse=True)
    return out


def baka_mention(u):
    un = getattr(u, "username", None)
    if un:
        return "@" + un
    nm = getattr(u, "first_name", None) or "user"
    return nm


def baka_progress(mode, total, idx, stats, now=None):
    filled = int(round(10 * idx / max(1, total)))
    bar = mono("▰" * filled + "▱" * (10 - filled))
    rows = [
        f"{E['moon']} {sb('BAKA AUTOMATION')} {E['arrow']} {sc(mode)}",
        "",
        f"{E['dot']} {sc('progress')} ‣ {bar} {mono(f'{idx}/{total}')}",
    ]
    if now is not None:
        rows.append(f"{E['arrow']} {sc('now')} ‣ {mono(baka_mention(now))}")
    rows += [
        "",
        f"{E['star']} {sc('robbed')} ‣ {mono(str(stats.get('rob', 0)))}   "
        f"{sc('killed')} ‣ {mono(str(stats.get('kill', 0)))}",
        f"{E['dot']} {sc('skipped')} ‣ {mono(str(stats.get('skip', 0)))}   "
        f"{sc('failed')} ‣ {mono(str(stats.get('fail', 0)))}",
        "",
        f"{E['warn']} {sc('rokne ke liye')} {mono('.stoprob')}",
    ]
    return panel(rows)


async def baka_worker(chat, mode, reply_event=None):
    BAKA_STOP.clear()
    chat = int(chat)
    stats = {"rob": 0, "kill": 0, "skip": 0, "fail": 0}
    status = None
    try:
        targets = await baka_targets(chat, include_done=False)
    except Exception as e:
        if reply_event is not None:
            await eor(reply_event, panel([
                f"{E['no']} {sc('target list fail')}",
                f"{E['arrow']} {mono(err_txt(e, 80))}",
                f"{E['dot']} {sc('admin rights / group check karo')}",
            ]))
        return
    total = len(targets)
    if not total:
        if reply_event is not None:
            await eor(reply_event, panel([
                f"{E['warn']} {sc('koi naya target nahi mila')}",
                f"{E['dot']} {sc('sab done hain')} ‣ {mono('.resetdone')}",
            ]))
        return
    if reply_event is not None:
        status = await eor(reply_event, baka_progress(mode, total, 0, stats))
    done_list = [int(x) for x in (BAKA_DONE.get(str(chat)) or [])]
    delay = float(BAKA.get("delay") or 2.5)

    for i, u in enumerate(targets, 1):
        if BAKA_STOP.is_set():
            break
        uid = int(u.id)
        msg = baka_cached_msg(chat, uid)
        reply_to = int(msg.id) if msg is not None else None

        coins = alive = None
        if mode == "auto" and BAKA.get("probe"):
            coins, alive = await baka_probe(chat, u, reply_to)

        if mode == "rob":
            steps = ["rob"]
        elif mode == "kill":
            steps = ["kill"]
        else:
            if coins is None and alive is None:
                steps = {"both": ["rob", "kill"], "rob": ["rob"],
                         "kill": ["kill"], "skip": []}.get(
                    BAKA.get("fallback") or "both", ["rob", "kill"])
            elif coins is None:
                steps = ["rob", "kill"] if alive else ["rob"]
            elif alive is None:
                steps = ["rob", "kill"] if coins > 0 else ["kill"]
            elif coins > 0 and alive:
                steps = ["rob", "kill"]
            elif coins > 0:
                steps = ["rob"]
            elif alive:
                steps = ["kill"]
            else:
                steps = []

        if not steps:
            stats["skip"] += 1
        for st in steps:
            res = await baka_do(chat, u, BAKA.get(f"{st}_cmd") or st, reply_to)
            if res in ("ok", "sent"):
                stats[st] += 1
            elif res == "verify":
                stats["fail"] += 1
                try:
                    await bot.send_message(chat, panel([
                        f"{E['lock']} {sc('verification maangi bot ne')}",
                        "",
                        f"{E['arrow']} {mono((BAKA_VERIFY.get(chat) or {}).get('text', '')[:160])}",
                        "",
                        f"{E['dot']} {mono('.solve <code>')} {sc('se code do')}",
                    ]))
                except Exception:
                    pass
                break
            elif res == "stopped":
                break
            else:
                stats["fail"] += 1
            await asyncio.sleep(delay)

        if uid not in done_list:
            done_list.append(uid)
        if i % 3 == 0 or i == total:
            BAKA_DONE[str(chat)] = done_list[-1000:]
            save_json(F_BAKA_DONE, BAKA_DONE)
            if status is not None:
                try:
                    await status.edit(align_panel(baka_progress(mode, total, i, stats, u)))
                except Exception:
                    pass
        if BAKA_STOP.is_set():
            break

    BAKA_DONE[str(chat)] = done_list[-1000:]
    save_json(F_BAKA_DONE, BAKA_DONE)
    summary = panel([
        f"{E['ok'] if not BAKA_STOP.is_set() else E['wait']} "
        f"{sc('automation khatam')} {E['arrow']} {sc(mode)}",
        "",
        f"{E['star']} {sc('robbed')} ‣ {mono(str(stats['rob']))}",
        f"{E['star']} {sc('killed')} ‣ {mono(str(stats['kill']))}",
        f"{E['dot']} {sc('skipped')} ‣ {mono(str(stats['skip']))}",
        f"{E['dot']} {sc('failed')} ‣ {mono(str(stats['fail']))}",
        "",
        f"{E['dot']} {mono('.resetdone')} {sc('se list clear')}",
    ])
    if status is not None:
        try:
            await status.edit(align_panel(summary))
            asyncio.create_task(_del_after(status, 20))
        except Exception:
            pass
    elif reply_event is not None:
        await eor(reply_event, summary)


def baka_start(chat, mode, reply_event=None):
    """purane task hata ke naya worker chalao"""
    old = BAKA_TASKS.get(mode)
    if old and not old.done():
        old.cancel()
    BAKA_STOP.clear()
    task = asyncio.create_task(baka_worker(chat, mode, reply_event))
    BAKA_TASKS[mode] = task
    return task


def baka_stop(which="all"):
    BAKA_STOP.set()
    killed = []
    for k in (list(BAKA_TASKS) if which == "all" else [which]):
        t = BAKA_TASKS.get(k)
        if t and not t.done():
            try:
                t.cancel()
                killed.append(k)
            except Exception:
                pass
        BAKA_TASKS[k] = None
    return killed


# ── status / setup panels ────────────────────────────────────
def baka_rules():
    return [
        f"{E['moon']} {sb('AUTO ROB + KILL')} {sc('on')}",
        "",
        f"{E['dot']} {sc('target')} ‣ {sc('every real user (newest → oldest)')}",
        f"{E['dot']} {sc('skip')}   ‣ {sc('self · owner · bots · already done')}",
        f"{E['dot']} {sc('amt')}    ‣ {sc('all balance') if not BAKA.get('amount') else mono(str(BAKA.get('amount')))}",
        f"{E['dot']} {sc('coins + alive')} ‣ {sc('rob + kill')}",
        f"{E['dot']} {sc('coins + dead')}  ‣ {sc('rob only')}",
        f"{E['dot']} {sc('no coins + alive')} ‣ {sc('kill only')}",
        f"{E['dot']} {sc('no coins + dead')}  ‣ {sc('skip')}",
        f"{E['dot']} {sc('stop')} ‣ {mono('.autooff')} · {mono('.stoprob')}",
    ]


def baka_setup_text():
    bot = baka_bot() or "—"
    return panel([
        f"{E['moon']} {sb('BAKA AUTOMATION')} {E['arrow']} {sc('setup')}",
        "",
        f"{E['dot']} {sc('bot')}    ‣ {mono('@' + bot if bot != '—' else '—')}",
        f"{E['dot']} {sc('prefix')} ‣ {mono(BAKA.get('prefix') or '/')}   "
        f"{sc('mode')} ‣ {mono(BAKA.get('mode') or 'reply')}",
        f"{E['dot']} {sc('delay')}  ‣ {mono(str(BAKA.get('delay')))}s   "
        f"{sc('probe')} ‣ {mono('on' if BAKA.get('probe') else 'off')}",
        f"{E['dot']} {sc('amount')} ‣ {mono('all' if not BAKA.get('amount') else BAKA.get('amount'))}",
        "",
        f"{E['note']} {sc('bot set karne ke liye')}",
        f"   {mono('.setbot @im_bakabot')}",
        f"{E['note']} {sc('baaki cheezein niche buttons se select karo')}",
        f"{E['warn']} {sc('jo pasand na aaye')} → {mono('skip')}",
        "",
        f"{E['dot']} {sc('text se bhi')}",
        f"   {mono('.setbot prefix /')} · {mono('.setbot mode reply')}",
        f"   {mono('.setbot delay 3')} · {mono('.setbot probe off')}",
        f"   {mono('.setbot rob rob')} · {mono('.setbot kill kill')}",
        f"   {mono('.setbot bal bal')} · {mono('.setbot fallback both')}",
    ])


def baka_buttons():
    return [
        [Button.inline("prefix  /", b"baka:prefix:/"),
         Button.inline("prefix  .", b"baka:prefix:."),
         Button.inline("prefix  !", b"baka:prefix:!")],
        [Button.inline("mode  reply", b"baka:mode:reply"),
         Button.inline("mode  mention", b"baka:mode:mention"),
         Button.inline("mode  plain", b"baka:mode:plain")],
        [Button.inline("delay 2s", b"baka:delay:2"),
         Button.inline("delay 3s", b"baka:delay:3"),
         Button.inline("delay 5s", b"baka:delay:5")],
        [Button.inline("probe on", b"baka:probe:on"),
         Button.inline("probe off", b"baka:probe:off"),
         Button.inline("amount all", b"baka:amt:all")],
        [Button.inline("✅ save", b"baka:save"),
         Button.inline("⏭ skip", b"baka:skip")],
    ]


def baka_status_text():
    running = [k for k, t in BAKA_TASKS.items() if t and not t.done()]
    rows = [
        f"{E['moon']} {sb('BAKA AUTOMATION')} {E['arrow']} {sc('status')}",
        "",
        f"{E['dot']} {sc('bot')}    ‣ {mono('@' + baka_bot()) if baka_bot() else mono('—')}",
        f"{E['dot']} {sc('prefix')} ‣ {mono(BAKA.get('prefix') or '/')}   "
        f"{sc('mode')} ‣ {mono(BAKA.get('mode') or 'reply')}",
        f"{E['dot']} {sc('amount')} ‣ {mono('all' if not BAKA.get('amount') else BAKA.get('amount'))}",
        f"{E['dot']} {sc('running')} ‣ {mono(', '.join(running) if running else 'none')}",
        f"{E['dot']} {sc('done list')} ‣ {mono(str(sum(len(v) for v in BAKA_DONE.values())))}",
        "",
        *baka_rules(),
        "",
        f"{E['note']} {mono('.setbot')} {sc('·')} {mono('.m22')}",
    ]
    return panel(rows)


# ── commands ─────────────────────────────────────────────────
# `.setbot <key> <value>` — jo button se set nahi hota wo text se
BAKA_KEYS = {
    "prefix": lambda v: v[:2] or "/",
    "mode": lambda v: v if v in _MODE_LABEL else "reply",
    "delay": lambda v: max(1.0, min(float(v or 2.5), 60.0)),
    "probe": lambda v: v.lower() in ("on", "1", "yes", "haan", "true"),
    "amount": lambda v: None if v.lower() in ("all", "full", "sab", "") else baka_amount(v),
    "rob": lambda v: (v or "rob").lstrip("/."),
    "kill": lambda v: (v or "kill").lstrip("/."),
    "bal": lambda v: (v or "bal").lstrip("/."),
    "fallback": lambda v: v if v in ("both", "rob", "kill", "skip") else "both",
}
BAKA_KEY_ALIAS = {"bal_cmd": "bal", "rob_cmd": "rob", "kill_cmd": "kill"}


@register_cmd("setbot", "setgame", owner_only=True)
async def cmd_setbot(event, arg):
    """.setbot @im_bakabot — automation bot + setup (buttons / text)"""
    raw = (arg or "").strip()
    if raw:
        toks = raw.split()
        key = toks[0].lower()
        if key in BAKA_KEYS:
            val = " ".join(toks[1:]).strip()
            if not val and key not in ("amount",):
                return await eor(event, panel([
                    f"{E['dot']} {mono(f'.setbot {key} <value>')}",
                    f"{E['dot']} {mono('.setbot prefix /')} · {mono('.setbot mode reply')}",
                    f"{E['dot']} {mono('.setbot rob rob')} · {mono('.setbot bal bal')}",
                    f"{E['dot']} {mono('.setbot fallback both')} · {mono('.setbot delay 3')}",
                ]))
            try:
                real = BAKA_KEY_ALIAS.get(key, key)
                field = f"{real}_cmd" if real in ("rob", "kill", "bal") else real
                BAKA[field] = BAKA_KEYS[key](val)
                baka_save()
            except Exception:
                return await eor(event, f"{E['no']} {sc('value galat hai')} {mono(val[:30])}")
            return await eor(event, baka_setup_text(), buttons=baka_buttons())
        name = baka_norm_bot(raw)
        if not name:
            return await eor(event, panel([
                f"{E['no']} {sc('bot samajh nahi aaya')}",
                f"{E['dot']} {mono('.setbot @im_bakabot')}",
                f"{E['dot']} {mono('.setbot t.me/im_bakabot')}",
            ]))
        BAKA["bot"] = name
        baka_save()
    return await eor(event, baka_setup_text(), buttons=baka_buttons())


@register_cmd("baka", "bakastatus", "automation", owner_only=True)
async def cmd_baka(event, arg):
    """.baka — automation status + rules"""
    return await eor(event, baka_status_text(), buttons=baka_buttons())


async def _baka_entry(event, mode, arg):
    if not baka_bot():
        return await eor(event, baka_setup_text(), buttons=baka_buttons())
    if not event.is_group:
        return await eor(event, panel([
            f"{E['warn']} {sc('ye command group me chalti hai')}",
            f"{E['dot']} {sc('jis gc me rob/kill karna hai wahan bhejo')}",
        ]))
    BAKA["amount"] = baka_amount(arg)
    baka_save()
    baka_start(int(event.chat_id), mode, reply_event=event)


@register_cmd("rob", owner_only=True)
async def cmd_rob(event, arg):
    """.rob [amt] — group ke saare users ko rob"""
    await _baka_entry(event, "rob", arg)


@register_cmd("kill", owner_only=True)
async def cmd_kill(event, arg):
    """.kill [amt] — group ke saare users ko kill"""
    await _baka_entry(event, "kill", arg)


@register_cmd("auto", owner_only=True)
async def cmd_auto(event, arg):
    """.auto [amt] — balance check → rob / kill / dono"""
    await _baka_entry(event, "auto", arg)


@register_cmd("autooff", owner_only=True)
async def cmd_autooff(event, arg):
    killed = baka_stop("auto")
    await done(event, panel([
        f"{E['no']} {sc('auto off')}",
        f"{E['dot']} {sc('stopped')} ‣ {mono(', '.join(killed) or 'none')}",
    ]), secs=8)


@register_cmd("roboff", owner_only=True)
async def cmd_roboff(event, arg):
    killed = baka_stop("rob")
    await done(event, panel([f"{E['no']} {sc('rob off')}",
                             f"{E['dot']} {sc('stopped')} ‣ {mono(', '.join(killed) or 'none')}"]), secs=8)


@register_cmd("killoff", owner_only=True)
async def cmd_killoff(event, arg):
    killed = baka_stop("kill")
    await done(event, panel([f"{E['no']} {sc('kill off')}",
                             f"{E['dot']} {sc('stopped')} ‣ {mono(', '.join(killed) or 'none')}"]), secs=8)


@register_cmd("stoprob", owner_only=True)
async def cmd_stoprob(event, arg):
    killed = baka_stop("all")
    await done(event, panel([f"{E['no']} {sc('sab band')}",
                             f"{E['dot']} {sc('stopped')} ‣ {mono(', '.join(killed) or 'none')}",
                             f"{E['dot']} {mono('.auto')} {sc('se dobara start')}"]), secs=8)


@register_cmd("resetdone", owner_only=True)
async def cmd_resetdone(event, arg):
    chat = str(int(event.chat_id))
    old = len(BAKA_DONE.get(chat) or [])
    BAKA_DONE[chat] = []
    save_json(F_BAKA_DONE, BAKA_DONE)
    await done(event, panel([
        f"{E['trash']} {sc('done list clear')}",
        f"{E['dot']} {sc('removed')} ‣ {mono(str(old))}",
    ]), secs=8)


@register_cmd("solve", owner_only=True)
async def cmd_solve(event, arg):
    """.solve <code> — bot ki verification ka code bhejo"""
    code = (arg or "").strip()
    if not code:
        v = BAKA_VERIFY.get(int(event.chat_id)) or {}
        return await eor(event, panel([
            f"{E['lock']} {sb('VERIFY')}",
            "",
            f"{E['dot']} {mono('.solve <code>')}",
            *( [f"{E['arrow']} {mono(v.get('text', '')[:160])}"] if v else
               [f"{E['warn']} {sc('abhi koi verification pending nahi')}"] ),
        ]))
    if not baka_bot():
        return await eor(event, baka_setup_text(), buttons=baka_buttons())
    v = BAKA_VERIFY.get(int(event.chat_id)) or {}
    kw = {}
    if v.get("msg_id"):
        kw["reply_to"] = int(v["msg_id"])
    try:
        await bot.send_message(event.chat_id, code, **kw)
    except Exception as e:
        return await eor(event, f"{E['no']} {sc('solve fail')} {E['arrow']} {mono(err_txt(e, 60))}")
    BAKA_VERIFY.pop(int(event.chat_id), None)
    await done(event, panel([
        f"{E['ok']} {sc('code bhej diya')}",
        f"{E['dot']} {mono(code[:20])}",
        f"{E['dot']} {mono('.auto')} {sc('se wapas chalao')}",
    ]), secs=10)


# ── trackers (sab clients pe lagte hain) ─────────────────────
async def baka_track(event):
    """target bot ke replies yaad rakho (probe / verify ke liye)"""
    name = (baka_bot() or "").lower()
    if not name:
        return
    try:
        chat = int(event.chat_id or 0)
    except Exception:
        return
    if not chat:
        return
    try:
        if not event.out:
            ent = await event.get_sender()
            un = (getattr(ent, "username", "") or "").lower()
            uid = str(getattr(ent, "id", "") or "")
            if un != name and uid != name:
                return
        else:
            return
        BAKA_LAST[chat] = {
            "id": int(event.id or 0),
            "text": event.raw_text or "",
            "reply_to": int(getattr(event, "reply_to_msg_id", 0) or 0),
            "ts": time.time(),
        }
    except Exception:
        pass


async def baka_cb(event):
    """setup ke inline buttons"""
    try:
        data = (event.data or b"").decode(errors="ignore")
    except Exception:
        return
    if not data.startswith("baka:"):
        return
    if event.sender_id != OWNER_ID and event.sender_id not in SUBBOT_IDS:
        try:
            await event.answer("owner only", alert=True)
        except Exception:
            pass
        return
    parts = data.split(":")
    key = parts[1] if len(parts) > 1 else ""
    val = parts[2] if len(parts) > 2 else ""
    if key == "skip":
        try:
            await event.answer("skip")
            await event.delete()
        except Exception:
            pass
        return
    try:
        if key == "prefix":
            BAKA["prefix"] = val
        elif key == "mode":
            BAKA["mode"] = val if val in _MODE_LABEL else "reply"
        elif key == "delay":
            BAKA["delay"] = float(val or 2.5)
        elif key == "probe":
            BAKA["probe"] = (val == "on")
        elif key == "amt":
            BAKA["amount"] = None if val == "all" else baka_amount(val)
        baka_save()
        if key == "save":
            await event.answer("saved ✅")
        else:
            await event.answer(f"{key} → {val}")
        await event.edit(align_panel(baka_setup_text()), buttons=baka_buttons())
    except Exception:
        try:
            await event.answer("done")
        except Exception:
            pass


def register_client_handlers(client):
    """main bot + har subbot pe dispatcher, tracker, buttons"""
    for cb, ev in ((dispatcher, events.NewMessage()),
                   (baka_track, events.NewMessage()),
                   (baka_cb, events.CallbackQuery())):
        try:
            client.remove_event_handler(cb, ev)
        except Exception:
            pass
        try:
            client.add_event_handler(cb, ev)
        except Exception:
            pass



# ══════════════════════════════════════════════════════════════
#                         sᴛᴏʀɪᴇs
# ══════════════════════════════════════════════════════════════
def _story(name, frames):
    async def runner(event, arg):
        await play_frames(event, frames, title=name)
    runner.__name__ = f"cmd_{name}"
    return runner


for _n, _f in [
    ("love1", LOVE1_COLLEGE), ("love2", LOVE2_INSTA), ("love3", LOVE3_OFFICE),
    ("love4", LOVE4_DISTANCE), ("love5", LOVE5_SHAADI),
    ("lovestory", LOVE_STORY_FRAMES),
    ("fun1", BACK1_CHAI), ("fun2", BACK2_EXAM), ("fun3", BACK3_CRICKET),
    ("fun4", BACK4_UDHAAR), ("fun5", BACK5_FLIRT), ("fun6", LOVE6_THUG),
    ("fun7", MEME_MUMMY), ("fun8", MEME_SASTA_NASHA),
]:
    register_cmd(_n)(_story(_n, _f))




# ══════════════════════════════════════════════════════════════
#                     ᴡᴀᴛᴄʜᴇʀ (incoming)
# ══════════════════════════════════════════════════════════════
MSG_CACHE: Dict[int, Dict[int, Any]] = {}


def _cache_msg(chat, msg):
    try:
        c = MSG_CACHE.setdefault(int(chat), {})
        c[int(msg.id)] = msg
        if len(c) > 300:
            for k in sorted(c)[:100]:
                c.pop(k, None)
    except Exception:
        pass


@bot.on(events.NewMessage)
async def watcher(event):
    try:
        if event.out:
            return
        sender = event.sender_id
        chat = event.chat_id
        if not sender:
            return
        text = event.raw_text or ""

        _cache_msg(chat, event.message)

        # ── GLOBAL BAN ──
        if sender in GBAN and not is_admin(sender):
            await silent_delete(event)
            asyncio.create_task(_gban_enforce(chat, sender))
            return

        # ── GLOBAL MUTE ──
        if sender in GMUTE and not is_admin(sender):
            await silent_delete(event)
            return

        # ── BLACKLIST ──
        if sender in BLACKLIST and not is_admin(sender):
            await silent_delete(event)
            return

        # ── LOCAL MUTE (delete engine) ──
        if (sender in MUTED or sender in GLOBAL_MUTED) and not is_admin(sender):
            await silent_delete(event)
            return

        # ── REPLY-LOCK (.rlock) ──
        rl = (RLOCK.get(str(chat)) or {}).get(str(sender))
        if rl and not is_admin(sender):
            await silent_delete(event)
            try:
                note = await event.respond(f"{E['lock']} {rl}")
                asyncio.create_task(_del_after(note, 6))
            except Exception:
                pass
            return

        # ── GROUP LOCKS (0.3s me udaa do) ──
        locked = LOCKS.get(str(chat))
        if locked and not is_admin(sender):
            if media_kinds(event.message) & set(locked):
                await asyncio.sleep(LOCK_DELAY)
                await silent_delete(event)
                return

        # ── SPAM GUARD (.watchspam) ──
        cfg = SPAMWATCH.get(str(chat))
        if cfg and not is_admin(sender):
            key = f"{chat}:{sender}"
            now = time.time()
            bucket = SPAM_BUCKET.setdefault(key, [])
            bucket.append(now)
            SPAM_BUCKET[key] = [t for t in bucket if now - t <= cfg["sec"]]
            if len(SPAM_BUCKET[key]) > cfg["limit"]:
                SPAM_BUCKET[key] = []
                await silent_delete(event)
                ok, _ = await _act_mute(chat, sender)
                if not ok:
                    MUTED.add(sender)
                try:
                    w = await event.respond(f"{E['eye']} {sc('spam detected')} {E['arrow']} "
                                            f"{mono(str(sender))} {sc('muted')}")
                    asyncio.create_task(_del_after(w, 6))
                except Exception:
                    pass
                return

        # ── AUTO READ ──
        if autoread_match(event):
            try:
                await bot.send_read_acknowledge(chat, max_id=event.id)
            except Exception:
                pass

        # ── ECHO ──
        if sender in ECHO_USERS and text and not _looks_like_cmd(text):
            try:
                await event.reply(text)
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── USER AUTO REPLY (.arreply) ──
        if sender in USER_REPLY and text and not _looks_like_cmd(text):
            try:
                await event.reply(USER_REPLY[sender])
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── AFK AUTO REPLY ──
        if AFK["active"] and (event.is_private or getattr(event, "mentioned", False)):
            if AFK_LAST.get(chat, 0) < time.time() - 45:
                AFK_LAST[chat] = time.time()
                try:
                    await event.reply(f"{E['moon']} {sc('afk')} {E['arrow']} {mono(AFK['reason'] or 'AFK')}")
                except Exception:
                    pass

        # ── AUTO REPLY (PM) ──
        if AREPLY and event.is_private and sender != OWNER_ID and sender not in ADMINS:
            try:
                await event.reply(AREPLY)
            except Exception:
                pass
            return

        # ── FILTERS ──
        fdata = FILTERS.get(str(chat))
        if fdata and text and not _looks_like_cmd(text):
            low = text.lower()
            for word, data in fdata.items():
                if word in low:
                    try:
                        src = await bot.get_messages(int(data["chat_id"]),
                                                     ids=int(data["msg_id"]))
                        if src is not None:
                            await bot.send_message(chat, src, reply_to=event.id)
                        elif data.get("text"):
                            await event.reply(data["text"])
                    except FloodWaitError as fw:
                        await asyncio.sleep(fw.seconds)
                    except Exception:
                        pass
                    break

        # ── REPLY RAID ──
        if sender in reply_users:
            try:
                await event.reply(random.choice(reply_list))
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── REPLY GOD (burst) ──
        if sender in replygod_users:
            try:
                for _ in range(3):
                    await event.reply(random.choice(reply_texts))
                    await asyncio.sleep(0.5)
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── FLAG RAID ──
        if sender in flag_users:
            try:
                await event.reply(random.choice(flag_texts))
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── HEART RAID ──
        if sender in hrr_users:
            try:
                await event.reply(random.choice(heart_replies))
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── RR RAID (+ reaction) ──
        if sender in rr_users:
            try:
                bot_msg = await event.reply(random.choice(fun_texts))
                try:
                    await bot(functions.messages.SendReactionRequest(
                        peer=chat, msg_id=bot_msg.id,
                        reaction=[types.ReactionEmoji(emoticon="🤣")]))
                except Exception:
                    pass
            except FloodWaitError as fw:
                await asyncio.sleep(fw.seconds)
            except Exception:
                pass

        # ── NIK REPLY (.nikreply) ──
        if sender in replyking_users:
            data = replyking_users.get(sender)
            if data:
                count = int(data.get("count", 0))
                if count > 0:
                    try:
                        await event.reply(data.get("text", ""))
                    except FloodWaitError as fw:
                        await asyncio.sleep(fw.seconds)
                    except Exception:
                        pass
                    data["count"] = count - 1
                else:
                    replyking_users.pop(sender, None)

    except Exception as e:
        print(f"[WATCHER] {err_txt(e, 80)}")


# ══════════════════════════════════════════════════════════════
#                   ᴀɴᴛɪ-ᴅᴇʟᴇᴛᴇ
# ══════════════════════════════════════════════════════════════
@bot.on(events.MessageDeleted)
async def on_deleted(event):
    try:
        chat = event.chat_id
        if chat is None:
            return
        if int(chat) not in ANTIDEL:
            return
        cache = MSG_CACHE.get(int(chat)) or {}
        for mid in (getattr(event, "deleted_ids", None) or []):
            m = cache.pop(int(mid), None)
            if m is None:
                continue
            try:
                await bot.send_message(
                    "me", f"{E['eye']} {sc('anti-delete')}\n"
                          f"{E['gem']} {sc('chat')} {mono(str(chat))} · {sc('id')} {mono(str(mid))}")
                try:
                    await bot.forward_messages("me", m)
                except Exception:
                    await bot.send_message("me", m)
            except Exception:
                pass
    except Exception as e:
        print(f"[ANTIDEL] {err_txt(e, 60)}")


# ══════════════════════════════════════════════════════════════
#                     ᴡᴀᴛᴄʜᴇʀ (outgoing)
# ══════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(outgoing=True))
async def outgoing_watcher(event):
    items = list(SELF_REACT or [])
    if items and not _looks_like_cmd(event.raw_text):
        try:
            payload = _react_payload(items)
            if payload:
                await bot(functions.messages.SendReactionRequest(
                    peer=event.chat_id, msg_id=event.id, reaction=payload))
        except FloodWaitError as fw:
            try:
                await asyncio.sleep(min(int(getattr(fw, "seconds", 2)), 10))
            except Exception:
                pass
        except Exception:
            pass

    if GHOST["on"]:
        if _looks_like_cmd(event.raw_text):
            return
        try:
            await asyncio.sleep(GHOST["delay"])
            await event.delete()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#              ᴠᴏɪᴄᴇ ᴄʜᴀᴛ  ·  ᴠꜱᴀᴠᴇ / ᴠᴘʟᴀʏ / ᴠʟɪꜱᴛ
# ══════════════════════════════════════════════════════════════
# • .vsave  (reply MP3)  → auto number me save
# • .vsave 3             → slot 3 me save
# • .vplay 1,2,3         → VC me bajao (queue)
# • .vlist / .vget 2 / .vdelete 2
# • .startvc .endvc .vstop
# pytgcalls optional hai — na ho to clear error deta hai, crash nahi.
VS_DIR = os.path.join(DATA_DIR, "vsave")          # .vsave — permanent
VC_TMP = os.path.join(DATA_DIR, "vctemp")         # direct play — auto delete
os.makedirs(VS_DIR, exist_ok=True)
os.makedirs(VC_TMP, exist_ok=True)
F_VSAVE = "vsave.json"
VSAVE: Dict[str, Dict[str, Any]] = load_json(F_VSAVE, {})

VC_QUEUE: Dict[int, list] = {}          # chat → [(num, path, name)]
VC_CLIENT: Dict[int, Any] = {}          # chat → jis client pe vc chal raha
_VC_APPS: Dict[int, Any] = {}           # client id → PyTgCalls


def _vs_next() -> int:
    nums = [int(k) for k in VSAVE if str(k).isdigit()]
    return (max(nums) + 1) if nums else 1


def _vs_nums(arg: str) -> list:
    """'2,3 4' → [2, 3, 4] · 'all' → sab"""
    a = (arg or "").strip().lower()
    if a in ("all", "*"):
        return sorted(int(k) for k in VSAVE)
    out = []
    for p in re.split(r"[, ]+", a):
        if p.isdigit():
            n = int(p)
            if n not in out:
                out.append(n)
    return out


def _vs_size(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}GB"


def _vs_dur(sec) -> str:
    sec = int(sec or 0)
    if not sec:
        return "—"
    return f"{sec // 60}:{sec % 60:02d}"





def _has_audio(msg) -> bool:
    return bool(getattr(msg, "audio", None) or getattr(msg, "voice", None)
                or getattr(msg, "video_note", None)
                or (getattr(msg, "document", None) and
                    "audio" in (getattr(getattr(msg, "file", None), "mime_type", "") or "")))


async def _vs_fetch_temp(reply) -> Optional[Dict[str, Any]]:
    """reply ki audio temp me download karo (play ke baad delete)"""
    name = (getattr(getattr(reply, "file", None), "name", None)
            or getattr(getattr(reply, "audio", None), "title", None)
            or f"track-{reply.id}")
    dur = getattr(getattr(reply, "audio", None), "duration", 0) \
        or getattr(getattr(reply, "file", None), "duration", 0) or 0
    try:
        tmp = await reply.download_media(file=VC_TMP)
    except Exception:
        return None
    if not tmp or not os.path.exists(tmp):
        return None
    _vc_temp_add(tmp)
    return {"num": None, "path": tmp, "name": name, "temp": True, "dur": int(dur)}


async def _vs_download(reply, slot: int) -> Optional[Dict[str, Any]]:
    """reply message se audio download karke slot me daal do"""
    media = getattr(reply, "audio", None) or getattr(reply, "voice", None) \
        or getattr(reply, "document", None) or getattr(reply, "video_note", None)
    if not media:
        return None
    name = (getattr(getattr(reply, "file", None), "name", None)
            or getattr(getattr(reply, "audio", None), "title", None)
            or f"audio-{reply.id}")
    dur = getattr(media, "duration", 0) or getattr(getattr(reply, "file", None), "duration", 0) or 0
    tmp = await reply.download_media(file=VS_DIR)
    if not tmp:
        return None
    ext = os.path.splitext(tmp)[1] or ".mp3"
    final = os.path.join(VS_DIR, f"{slot}{ext}")
    try:
        if os.path.abspath(tmp) != os.path.abspath(final):
            if os.path.exists(final):
                os.remove(final)
            os.replace(tmp, final)
    except Exception:
        final = tmp
    try:
        size = os.path.getsize(final)
    except Exception:
        size = 0
    data = {"name": name, "file": os.path.basename(final), "size": size,
            "dur": int(dur), "at": time.time(), "by": None}
    VSAVE[str(slot)] = data
    save_json(F_VSAVE, VSAVE)
    return data


async def _input_peer(event):
    """event → InputPeer (get_input_chat na ho to fallback)"""
    try:
        peer = await event.get_input_chat()
        if peer:
            return peer
    except Exception:
        pass
    try:
        from telethon import utils as _tlu
        chat = await event.get_chat()
        return _tlu.get_input_peer(chat, allow_cache=True)
    except Exception:
        return None


async def _vc_live(chat_id) -> bool:
    """pytgcalls ke apne record se — sabse reliable"""
    for _c in (bot._target(),):
        app = _VC_APPS.get(id(_c))
        if not app:
            continue
        try:
            calls = await app.calls
            if int(chat_id) in calls:
                return True
        except Exception:
            pass
    return False


async def _vc_call(peer=None, chat_id=None):
    """chat me live voice chat hai? → InputGroupCall ya None.

    3 tarike check karta hai (koi ek bhi kaam kare):
      1. pytgcalls ke paas is chat ka live call hai
      2. channels.GetFullChannel / messages.GetFullChat
      3. resolved peer se full info
    """
    if chat_id is not None and await _vc_live(chat_id):
        return True

    try:
        if peer is None and chat_id is not None:
            peer = await bot.get_input_entity(chat_id)
    except Exception:
        peer = None

    try:
        if isinstance(peer, types.InputPeerChannel):
            res = await bot(functions.channels.GetFullChannelRequest(channel=peer))
        elif isinstance(peer, types.InputPeerChat):
            res = await bot(functions.messages.GetFullChatRequest(chat_id=peer.chat_id))
        elif peer is not None:
            ent = await bot.get_entity(peer)
            if getattr(ent, "call", None):
                return ent.call
            if hasattr(ent, "id"):
                res = await bot(functions.channels.GetFullChannelRequest(
                    channel=await bot.get_input_entity(ent)))
            else:
                return None
        else:
            return None
        for c in (getattr(res, "chats", None) or []):
            call = getattr(c, "call", None)
            if call:
                return call
        if getattr(res, "full_chat", None) is not None:
            if getattr(res.full_chat, "call", None):
                return res.full_chat.call
    except Exception:
        return None
    return None


def _vc_imports():
    """pytgcalls lazily — sirf tab jab actually chahiye"""
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types import MediaStream, AudioQuality, StreamEnded
        return PyTgCalls, MediaStream, AudioQuality, StreamEnded
    except Exception as e:
        return None, None, None, e


async def _vc_app(client=None):
    """per-client PyTgCalls instance (ek hi baar banta hai)"""
    client = client or bot._target()
    key = id(client)
    app = _VC_APPS.get(key)
    if app is not None:
        return app
    PyTgCalls, MediaStream, AudioQuality, StreamEnded = _vc_imports()
    if not PyTgCalls:
        raise RuntimeError("pytgcalls installed nahi hai")
    app = PyTgCalls(client)

    @app.on_update()
    async def _on_vc_update(_c, update):
        try:
            if isinstance(update, StreamEnded):
                _chat = int(update.chat_id)
                # jo track khatam hua — agar temp tha to turant delete
                for _p in list(_VC_TEMP):
                    if not any(os.path.exists(q.get("path", "")) and
                               q.get("path") == _p for q in (VC_QUEUE.get(_chat) or [])):
                        _rm(_p)
                        _VC_TEMP.discard(_p)
                await _vc_next(_chat)
        except Exception:
            pass

    try:
        await app.start()
    except Exception as e:
        if "already" not in type(e).__name__.lower():
            raise
    _VC_APPS[key] = app
    return app


async def _vc_next(chat: int):
    """queue se agla track bajao (temp files bajane ke baad delete)"""
    q = VC_QUEUE.get(chat) or []
    if not q:
        return
    PyTgCalls, MediaStream, AudioQuality, StreamEnded = _vc_imports()
    if not MediaStream:
        return
    item = q.pop(0)
    path = item.get("path")
    if not path or not os.path.exists(path):
        return await _vc_next(chat)
    app = await _vc_app(VC_CLIENT.get(chat))
    try:
        from pytgcalls.types import GroupCallConfig
        await app.play(chat, MediaStream(path, audio_parameters=AudioQuality.HIGH),
                       config=GroupCallConfig(auto_start=True))
    except TypeError:
        await app.play(chat, MediaStream(path, audio_parameters=AudioQuality.HIGH))
    except Exception as e:
        print(f"[VC NEXT] {err_txt(e, 80)}")


_VC_TEMP: Set[str] = set()          # is session ke temp files (auto delete)


def _vc_temp_add(path: str):
    if path:
        _VC_TEMP.add(path)


def _vc_cleanup(chat: int = None):
    """temp files turant delete — sirf .vsave saved files bachti hain"""
    if chat is not None:
        for item in (VC_QUEUE.get(chat) or []):
            if item.get("temp"):
                _rm(item["path"])
    do = [p for p in _VC_TEMP if p]
    _VC_TEMP.clear()
    for p in do:
        _rm(p)


def _rm(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _vc_stop_local(chat: int):
    _vc_cleanup(chat)
    VC_QUEUE.pop(chat, None)
    VC_CLIENT.pop(chat, None)


async def _reset_all_loops() -> int:
    """saare raid/spam/auto states + tasks band — .killall ka dimaag"""
    global TAGALL_ACTIVE, GPFP_TASK, AUTOBR_TASK, AUTOFW_TASK, CLONE_ACTIVE
    done_n = 0
    for s in (reply_users, rr_users, flag_users, hrr_users, replygod_users, ECHO_USERS):
        done_n += len(s)
        s.clear()
    done_n += len(replyking_users)
    replyking_users.clear()
    USER_REPLY.clear()

    for t in list(spray_tasks.values()):
        try:
            t.cancel()
        except Exception:
            pass
    done_n += len(spray_tasks)
    spray_tasks.clear()

    for _t in ("GPFP_TASK", "AUTOBR_TASK", "AUTOFW_TASK"):
        t = globals().get(_t)
        if t and not t.done():
            try:
                t.cancel()
            except Exception:
                pass
    GPFP_TASK = None
    AUTOBR_TASK = None
    AUTOFW_TASK = None
    GPFP_STATE["on"] = False
    TAGALL_ACTIVE = False
    CLONE_ACTIVE = False
    AUTOBR["on"] = False
    AUTOFW["on"] = False
    save_json(F_AUTOBR, AUTOBR)
    save_json(F_AUTOFW, AUTOFW)

    ft = FASTGC_STATE.get("task")
    if ft and not ft.done():
        try:
            ft.cancel()
        except Exception:
            pass
    FASTGC_STATE.update({"active": False, "template": None, "task": None})
    VC_QUEUE.clear()
    return done_n


def _kill_own_tasks() -> int:
    """is file ke saare live asyncio tasks cancel (telethon ko chhod ke)"""
    cur = asyncio.current_task()
    me_file = os.path.basename(__file__)
    killed = 0
    for t in asyncio.all_tasks():
        if t is cur or t.done():
            continue
        coro = t.get_coro()
        code = getattr(coro, "cr_code", None)
        if code is None:
            frame = getattr(coro, "cr_frame", None)
            code = getattr(frame, "f_code", None)
        fname = os.path.basename(getattr(code, "co_filename", "") or "")
        if fname != me_file:
            continue
        try:
            t.cancel()
            killed += 1
        except Exception:
            pass
    return killed


_ID_CACHE: Dict[int, str] = {}


async def _id_label(uid: int) -> str:
    """id → 'Name ‣ @username · id'  (cached, flood-safe)"""
    if uid in _ID_CACHE:
        return _ID_CACHE[uid]
    try:
        u = await bot.get_entity(uid)
    except Exception:
        return mono(str(uid))
    name = " ".join(x for x in (getattr(u, "first_name", "") or "",
                                getattr(u, "last_name", "") or "") if x).strip()
    un = getattr(u, "username", None)
    tag = f"@{un}" if un else sc("no username")
    if not name:
        name = sc("unknown")
    label = f"{sc(name[:20])} {E['arrow']} {mono(tag)} {E['dot']} {mono(str(uid))}"
    _ID_CACHE[uid] = label
    return label


# ── ᴠᴄ ᴍᴇɴᴜ  ( .m24 ) ────────────────────────────────────────
_VC_MENU = [
    ("startvc",    "ɢʀᴏᴜᴘ ᴍᴇ ᴠᴄ sᴛᴀʀᴛ ᴋᴀʀᴏ"),
    ("endvc",      "ᴠᴄ ʙᴀɴᴅ · sᴀʙ ᴋᴇ ʟɪʏᴇ"),
    ("vstop",      "sᴛʀᴇᴀᴍ ʀᴏᴋᴏ + ʟᴇꜰᴛ"),
    ("vsave",      "ʀᴇᴘʟʏ ᴍᴘ3 sᴀᴠᴇ · ᴀᴜᴛᴏ ɴᴏ."),
    ("vsave 3",    "sʟᴏᴛ 3 ᴍᴇ sᴀᴠᴇ · ᴏᴠᴇʀᴡʀɪᴛᴇ"),
    ("vlist",      "sᴀᴀʀɪ sᴀᴠᴇᴅ ꜰɪʟᴇs ɴᴀᴀᴍ sᴀᴛʜ"),
    ("vplay",      "ᴍᴘ3 ᴘᴇ ʀᴇᴘʟʏ → ᴅɪʀᴇᴄᴛ ᴘʟᴀʏ"),
    ("vplay 1",    "sᴀᴠᴇᴅ ꜰɪʟᴇ ʙᴀᴊᴀᴏ"),
    ("vplay 1,2,3", "ᴇᴋ ᴋᴇ ʙᴀᴀᴅ ᴇᴋ · ϙᴜᴇᴜᴇ"),
    ("vget 2",     "ꜰɪʟᴇ ᴄʜᴀᴛ ᴍᴇ ʙʜᴇᴊᴏ · ᴘʀᴇᴠɪᴇᴡ"),
    ("vdelete 2",  "sʟᴏᴛ ᴅᴇʟᴇᴛᴇ"),
]


def build_vc_menu(w=34):
    """.m24 — ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴄᴏᴍᴍᴀɴᴅs"""
    rows = [hdr(f"{E['music']}{SP} ▰ {sb('voice chat')}", w, count=len(_VC_MENU))]
    for i, (c, d) in enumerate(_VC_MENU):
        rows.append(row(c, d, bullet=(E["music"] if i % 2 == 0 else E["bell"]), cw=13))
    rows.append(end(w))
    saved = len(VSAVE)
    return "\n".join(menu_head(w, 1) + rows + [
        sub(f"{E['dot']}{SP} {mono('.m24')} {E['arrow']} {sc('vc')} "
            f"{E['arrow']} {mono(str(saved))} {sc('saved files')}"),
        sub(FOOT),
        close(),
    ])


# ══════════════════════════════════════════════════════════════
#                    ᴠᴄ ᴄᴏᴍᴍᴀɴᴅs
# ══════════════════════════════════════════════════════════════
@register_cmd("m24")
async def cmd_vc_menu(event, arg):
    """.m24 — ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴄᴏᴍᴍᴀɴᴅs"""
    await eor(event, build_vc_menu())


@register_cmd("startvc", "vcstart", group_only=True)
async def cmd_startvc(event, arg):
    """.startvc — group me voice chat start"""
    peer = await _input_peer(event)
    if not peer:
        return await eor(event, f"{E['no']} {sc('chat resolve nahi hua')}")
    call = await _vc_call(peer)
    if call:
        return await eor(event, f"{E['warn']} {sc('vc pehle se chal raha hai')} {E['arrow']} "
                                f"{mono('.vplay <no>')} {sc('se gaana bajao')}")
    try:
        # NOTE: Telethon 1.45 me random_id int32 hai (<i) → getrandbits(31)
        await bot(functions.phone.CreateGroupCallRequest(
            peer=peer, random_id=random.getrandbits(31), title=""))
    except Exception as e:
        low = err_txt(e, 90).lower()
        if "already" in low or "groupcall" in low:
            return await eor(event, f"{E['warn']} {sc('vc pehle se on hai')}")
        if "admin" in low or "right" in low:
            return await eor(event, f"{E['no']} {sc('vc start karne ke liye admin chahiye')}")
        return await eor(event, f"{E['no']} {sc('vc start fail')} {E['arrow']} {mono(err_txt(e, 60))}")
    await eor(event, "\n".join([top(), sub(""),
        sub(f" {E['music']} {sc('voice chat started')}"),
        sub(f" {E['dot']} {mono('.vplay <no>')} {sc('se gaana bajao')}"),
        sub(f" {E['dot']} {mono('.vlist')} {sc('se saved files dekho')}"),
        sub(""), sub(FOOT), close()]))


@register_cmd("endvc", "vcend", group_only=True)
async def cmd_endvc(event, arg):
    """.endvc — vc band (sab ke liye)"""
    chat = event.chat_id
    peer = await _input_peer(event)
    if not peer:
        return await eor(event, f"{E['no']} {sc('chat resolve nahi hua')}")
    call = await _vc_call(peer)
    if not call:
        return await eor(event, f"{E['warn']} {sc('yahan koi vc chal hi nahi raha')}")
    app = _VC_APPS.get(id(bot._target()))
    ok = False
    if app:
        try:
            await app.leave_call(chat, close=True)
            ok = True
        except Exception:
            ok = False
    if not ok:
        try:
            await bot(functions.phone.DiscardGroupCallRequest(call=call))
            ok = True
        except Exception as e:
            return await eor(event, f"{E['no']} {sc('vc band nahi hui')} {E['arrow']} "
                                    f"{mono(err_txt(e, 60))}")
    _vc_stop_local(chat)
    _vc_cleanup()
    await eor(event, f"{E['ok']} {sc('vc band ho gaya')}")


@register_cmd("vstop", "vcstop", group_only=True)
async def cmd_vstop(event, arg):
    """.vstop — stream rok + vc se nikal"""
    chat = event.chat_id
    app = _VC_APPS.get(id(bot._target()))
    if not app:
        return await eor(event, f"{E['warn']} {sc('koi stream chal hi nahi raha')}")
    try:
        await app.leave_call(chat)
    except Exception as e:
        return await eor(event, f"{E['no']} {sc('stop fail')} {E['arrow']} {mono(err_txt(e, 60))}")
    _vc_stop_local(chat)
    _vc_cleanup()
    await eor(event, f"{E['no']} {sc('stream band')} {E['dot']} "
                     f"{sc('temp files delete')} {E['dot']} {sc('vc se nikal gaya')}")


@register_cmd("vsave", "voicesave")
async def cmd_vsave(event, arg):
    """.vsave — replied mp3/voice save (auto ya .vsave 3)"""
    reply = await event.get_reply_message()
    if not reply:
        return await eor(event, "\n".join([top(), sub(""),
            sub(f" {E['warn']} {sc('kisi audio message pe reply karke')} {mono('.vsave')}"),
            sub(f" {E['dot']} {mono('.vsave')} {sc('→ auto number')}"),
            sub(f" {E['dot']} {mono('.vsave 3')} {sc('→ slot 3')}"),
            sub(""), sub(FOOT), close()]))
    slots = _vs_nums(arg)
    if not slots:
        slots = [_vs_next()]

    # ── animation: save hone tak chalti hai ──
    phase = {"v": "save"}
    status = await eor(event, load_card("save", "#%s" % slots[0], 0, 0), plain=True)
    stop = asyncio.Event()
    lt = asyncio.create_task(
        _music_loader(status, "save #%s" % slots[0], MUSIC_FRAMES, stop, phase))
    saved = []
    try:
        for n in slots[:10]:
            phase["v"] = "down"
            data = await _vs_download(reply, n)
            if not data:
                return await eor(event, f"{E['no']} audio / mp3 / voice pe reply karo")
            data["by"] = event.sender_id
            VSAVE[str(n)] = data
            save_json(F_VSAVE, VSAVE)
            saved.append(n)
            phase["v"] = "save"
    finally:
        stop.set()
        lt.cancel()
        if status is not None:
            try:
                await status.delete()
            except Exception:
                pass
    lines = [top(), sub(""),
             sub(f" {E['ok']} {sc('saved')} {E['arrow']} "
                 f"{mono(', '.join('#' + str(s) for s in saved))}"),
             sub("")]
    for n in saved:
        d = VSAVE[str(n)]
        lines.append(sub(f" {E['music']} {mono('#' + str(n))} {E['arrow']} "
                         f"{sc(d['name'][:26])} {E['dot']} {mono(_vs_dur(d['dur']))}"))
    lines += [sub(f" {E['dot']} {mono('.vplay ' + ','.join(map(str, saved)))} "
                  f"{sc('se bajao')}"), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("vlist", "voicelist")
async def cmd_vlist(event, arg):
    """.vlist — saari saved files (no · naam · size)"""
    if not VSAVE:
        return await eor(event, "\n".join([top(), sub(""),
            sub(f" {E['warn']} {sc('koi file save nahi hai')}"),
            sub(f" {E['dot']} {mono('.vsave')} {sc('audio pe reply karke')}"),
            sub(""), sub(FOOT), close()]))
    lines = [top(), sub(""),
             sub(f" {E['music']} {sc('saved files')} {E['arrow']} {mono(str(len(VSAVE)))}"),
             sub("")]
    for k in sorted(VSAVE, key=lambda x: int(x) if x.isdigit() else 999):
        d = VSAVE[k]
        lines.append(sub(f" {E['star']} {mono('#' + k)} {E['arrow']} {sc(d['name'][:24])}"))
        lines.append(sub(f"   {E['dot']} {mono(_vs_dur(d.get('dur')))} {E['dot']} "
                         f"{mono(_vs_size(d.get('size')))}"))
    lines += [sub(""),
              sub(f" {E['dot']} {mono('.vplay 1,2')} {sc('· bajao')}"),
              sub(f" {E['dot']} {mono('.vget 2')} {sc('· preview')}"),
              sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("vget", "vpreview")
async def cmd_vget(event, arg):
    """.vget 2 — saved file chat me bhejo (preview)"""
    nums = _vs_nums(arg)
    if not nums:
        return await eor(event, f"{E['warn']} {sc('number do')} {E['arrow']} {mono('.vget 2')}")
    n = nums[0]
    d = VSAVE.get(str(n))
    if not d:
        return await eor(event, f"{E['no']} {sc('slot')} {mono('#' + str(n))} {sc('khali hai')}")
    path = os.path.join(VS_DIR, d["file"])
    if not os.path.exists(path):
        return await eor(event, f"{E['no']} {sc('file gayab hai')} {E['arrow']} {mono(d['file'])}")
    try:
        await bot.send_file(event.chat_id, path, caption=f"{E['music']} {sc(d['name'][:40])}",
                            voice_note=False, reply_to=event.id)
        await event.delete()
    except Exception as e:
        await eor(event, f"{E['no']} {sc('bhej nahi paya')} {E['arrow']} {mono(err_txt(e, 60))}")


@register_cmd("vdelete", "vdel")
async def cmd_vdelete(event, arg):
    """.vdelete 2 — slot delete"""
    nums = _vs_nums(arg)
    if not nums:
        return await eor(event, f"{E['warn']} {sc('number do')} {E['arrow']} {mono('.vdelete 2')}")
    gone = []
    for n in nums:
        d = VSAVE.pop(str(n), None)
        if not d:
            continue
        try:
            path = os.path.join(VS_DIR, d["file"])
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        gone.append(n)
    save_json(F_VSAVE, VSAVE)
    await eor(event, f"{E['trash']} {sc('deleted')} {E['arrow']} "
                     f"{mono(', '.join('#' + str(g) for g in gone)) or '—'}"
                     f"{E['dot']} {sc('ab bache')} {mono(str(len(VSAVE)))}")


@register_cmd("vplay", "voiceplay", group_only=True)
async def cmd_vplay(event, arg):
    """.vplay — reply MP3 direct · .vplay 1,2,3 saved slots · .vplay all"""
    PyTgCalls, MediaStream, AudioQuality, StreamEnded = _vc_imports()
    if not PyTgCalls:
        return await eor(event, "\n".join([top(), sub(""),
            sub(f" {E['no']} {sc('pytgcalls installed nahi hai')}"),
            sub(f" {E['dot']} {mono('pip install py-tgcalls')}"),
            sub(f" {E['dot']} {sc('ffmpeg bhi chahiye')} {mono('apt install ffmpeg')}"),
            sub(""), sub(FOOT), close()]))

    chat = event.chat_id
    queue = []
    reply = await event.get_reply_message()
    arg = (arg or "").strip()

    # ── A) reply me audio/voice hai → DIRECT play (save nahi hota) ──
    if reply and _has_audio(reply):
        item = await _vs_fetch_temp(reply)
        if not item:
            return await eor(event, f"{E['no']} {sc('file download nahi hui')}")
        queue = [item]

    # ── B) saved slots ──────────────────────────────────────────
    elif arg:
        nums = _vs_nums(arg)
        if not nums:
            return await eor(event, f"{E['warn']} {sc('number do ya MP3 pe reply karo')}\n"
                                    f"{E['dot']} {mono('.vplay 1')} {sc('·')} "
                                    f"{mono('.vplay all')} {sc('·')} {mono('.vlist')}")
        for n in nums:
            d = VSAVE.get(str(n))
            if not d:
                continue
            path = os.path.join(VS_DIR, d["file"])
            if not os.path.exists(path):
                continue
            queue.append({"num": n, "path": path, "name": d["name"], "temp": False})
        if not queue:
            return await eor(event, f"{E['no']} {sc('in numbers pe koi file nahi')} {E['dot']} "
                                    f"{mono('.vlist')}")

    else:
        return await eor(event, "\n".join([top(), sub(""),
            sub(f" {E['warn']} {sc('kya bajana hai?')}"),
            sub(f" {E['dot']} MP3 {sc('pe reply karke')} {mono('.vplay')} {sc('· direct')}"),
            sub(f" {E['dot']} {mono('.vplay 1,2')} {sc('· saved slots')}"),
            sub(f" {E['dot']} {mono('.vlist')} {sc('· kitni save hain')}"),
            sub(""), sub(FOOT), close()]))

    VC_CLIENT[chat] = bot._target()
    VC_QUEUE[chat] = queue[1:]

    try:
        app = await _vc_app(VC_CLIENT[chat])
    except Exception as e:
        VC_QUEUE.pop(chat, None)
        _vc_cleanup(chat)
        return await eor(event, f"{E['no']} {sc('pytgcalls start nahi hua')}\n"
                                f"{E['dot']} {mono(err_txt(e, 90))}")

    try:
        from pytgcalls.types import GroupCallConfig
        cfg = GroupCallConfig(auto_start=True)
    except Exception:
        cfg = None

    ok = False
    try:
        if cfg is not None:
            await app.play(chat, MediaStream(queue[0]["path"], audio_parameters=AudioQuality.HIGH),
                          config=cfg)
        else:
            await app.play(chat, MediaStream(queue[0]["path"], audio_parameters=AudioQuality.HIGH))
        ok = True
    except TypeError:
        try:
            await app.play(chat, MediaStream(queue[0]["path"], audio_parameters=AudioQuality.HIGH))
            ok = True
        except Exception as e:
            err = e
    except Exception as e:
        err = e

    if not ok:
        VC_QUEUE.pop(chat, None)
        _vc_cleanup(chat)
        msg = err_txt(err, 90)
        low = str(msg).lower()
        hint = ""
        if "ffmpeg" in low or "ffprobe" in low:
            hint = f"\n{E['dot']} {mono('apt install ffmpeg')} {sc('(termux: pkg install ffmpeg)')}"
        return await eor(event, f"{E['no']} {sc('play fail')} {E['arrow']} {mono(msg)}{hint}")

    tag = f"#{queue[0]['num']}" if queue[0].get("num") else sc("direct")
    lines = [top(), sub(""),
             sub(f" {E['music']} {sc('playing')} {E['arrow']} "
                 f"{mono(tag)} {sc(queue[0]['name'][:26])}")]
    if len(queue) > 1:
        lines.append(sub(f" {E['dot']} {sc('queue')} {E['arrow']} "
                         f"{mono(str(len(queue) - 1))} {sc('more')}"))
    if queue[0].get("temp"):
        lines.append(sub(f" {E['dot']} {sc('temp file')} {E['arrow']} "
                         f"{sc('khatam hone pe delete')}"))
    lines += [sub(f" {E['dot']} {mono('.vstop')} {sc('· band')}"), sub(FOOT), close()]
    await eor(event, "\n".join(lines))


@register_cmd("killall", "killeverything", "killtasks", owner_only=True)
async def cmd_killall(event, arg):
    """.killall — har live task + loop band (raids, spam, auto, gpfp, fastgc…)"""
    await eor(event, f"{E['wait']} {sc('sab kuch band kar raha hoon…')}")
    vc_n = 0
    for _chat in list(VC_CLIENT):
        app = _VC_APPS.get(id(VC_CLIENT.get(_chat)))
        if not app:
            continue
        try:
            await app.leave_call(_chat)
            vc_n += 1
        except Exception:
            pass
    _vc_cleanup()
    task_n = _kill_own_tasks()
    state_n = await _reset_all_loops()
    try:
        await event.delete()
    except Exception:
        pass
    await eor(event, "\n".join([top(), sub(""),
        sub(f" {E['no']} {sc('kill all')} {E['arrow']} {mono('done')}"),
        sub(""),
        sub(f" {E['dot']} {sc('live tasks killed')} {E['arrow']} {mono(str(task_n))}"),
        sub(f" {E['dot']} {sc('loops / raids cleared')} {E['arrow']} {mono(str(state_n))}"),
        sub(f" {E['dot']} {sc('vc calls left')} {E['arrow']} {mono(str(vc_n))}"),
        sub(""),
        sub(f" {E['warn']} {sc('vc bhi band')} {E['dot']} {mono('.startvc')} {sc('se dobara')}"),
        sub(FOOT), close()]))


# ══════════════════════════════════════════════════════════════
#        📜  ᴀʀᴛɪᴄʟᴇ  ·  ʀɪᴄʜ ᴍᴇꜱꜱᴀɢᴇꜱ  (layer 227+)
# ══════════════════════════════════════════════════════════════
# Telegram ka naya Rich Text Editor (July 2026, Premium) protocol me
# message.rich_message + messages.sendMessage.rich_message ke roop me
# aata hai. Content = PageBlock* ka tree, andar RichText* nodes.
#   • 32,768 chars · 500 blocks · 16 level nest · 50 media · 20 columns
#   • TextCustomEmoji(document_id, alt) → article ke ANDAR premium emoji
#   • bhejne ke liye account Premium (bots exempt); padhne ke liye nahi
ART_LIMIT  = 32768
ART_BLOCKS = 500
ART_COLS   = 20
ART_EMOJI_CAP = 90

RICH_READY = all(hasattr(types, _n) for _n in (
    "InputRichMessage", "InputRichMessageMarkdown", "InputRichMessageHTML",
    "RichMessage", "PageBlockParagraph", "PageBlockHeading1",
    "PageBlockTable", "PageTableRow", "PageTableCell",
    "PageBlockDetails", "PageBlockMath", "TextPlain", "TextConcat",
    "TextCustomEmoji", "InputSendMessageRichMessageDraftAction"))

_RICH_EMOJI_RX = None
if PREMIUM_EMOJI and _NIK_EMOJI_IDS:
    try:
        _RICH_EMOJI_RX = re.compile("(" + "|".join(
            re.escape(_k) for _k in sorted(_NIK_EMOJI_IDS, key=len, reverse=True)) + ")")
    except Exception:
        _RICH_EMOJI_RX = None


# Server rule: ye blocks sirf Instant View pages ke liye hain — bot rich
# message me bhejne pe RICH_MESSAGE_BLOCK_UNSUPPORTED / CTOR_NOT_ALLOWED.



def _sanitize_blocks(blocks):
    """disallowed blocks ko allowed shape me badlo (nesting ke andar bhi)."""
    out = []
    for b in blocks or []:
        n = type(b).__name__
        if n == "PageBlockTitle":
            out.append(types.PageBlockHeading1(text=b.text))
        elif n in ("PageBlockSubtitle", "PageBlockHeader", "PageBlockSubheader",
                   "PageBlockKicker"):
            out.append(types.PageBlockParagraph(
                text=types.TextItalic(text=b.text)
                if n in ("PageBlockSubtitle", "PageBlockKicker") else b.text))
        elif n == "PageBlockAuthorDate":
            out.append(types.PageBlockParagraph(text=b.author))
        elif n == "PageBlockCover":
            inner = getattr(b, "cover", None)
            if inner is not None:
                out.extend(_sanitize_blocks([inner]))
        elif n == "PageBlockRelatedArticles":
            continue
        elif n == "PageBlockDetails":
            out.append(types.PageBlockDetails(
                blocks=_sanitize_blocks(b.blocks), title=b.title,
                open=getattr(b, "open", None)))
        elif n == "PageBlockBlockquoteBlocks":
            out.append(types.PageBlockBlockquoteBlocks(
                blocks=_sanitize_blocks(b.blocks), caption=b.caption))
        elif n in ("PageBlockCollage", "PageBlockSlideshow"):
            out.append(type(b)(items=_sanitize_blocks(b.items), caption=b.caption))
        else:
            out.append(b)
    return out


def _rt_join(parts):
    """RichText nodes ko jodo — single ho to wahi, warna TextConcat."""
    clean = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, types.TextPlain) and not p.text:
            continue
        if isinstance(p, types.TextConcat):
            clean.extend(p.texts)
            continue
        clean.append(p)
    if not clean:
        return types.TextPlain("")
    if len(clean) == 1:
        return clean[0]
    return types.TextConcat(texts=clean)


def _rt_inline(s, docs):
    """inline markup → RichText list. **b** *i* ~~s~~ ||sp|| `c` $m$ [t](url)"""
    out, buf, i, n = [], [], 0, len(s)

    def _flush():
        if buf:
            out.append(types.TextPlain("".join(buf)))
            buf.clear()

    while i < n:
        ch = s[i]

        # [label](url)
        if ch == "[":
            j = s.find("](", i)
            k = s.find(")", j + 2) if j != -1 else -1
            if j != -1 and k != -1:
                _flush()
                try:
                    out.append(types.TextUrl(
                        text=_rt_join(_rt_inline(s[i + 1:j], docs)),
                        url=s[j + 2:k], webpage_id=0))
                except Exception:
                    buf.append(s[i:k + 1])
                i = k + 1
                continue

        hit = False
        for mark, kind in (("**", "b"), ("__", "i"), ("~~", "s"),
                           ("||", "sp"), ("`", "c")):
            if s.startswith(mark, i):
                close = s.find(mark, i + len(mark))
                if close > i + len(mark):
                    inner = s[i + len(mark):close]
                    if kind == "c":
                        node = types.TextFixed(text=_rt_join(_rt_inline(inner, docs)))
                    else:
                        node = _rt_join(_rt_inline(inner, docs))
                        if kind == "b":
                            node = types.TextBold(text=node)
                        elif kind == "i":
                            node = types.TextItalic(text=node)
                        elif kind == "s":
                            node = types.TextStrike(text=node)
                        else:
                            node = types.TextSpoiler(text=node)
                    _flush()
                    out.append(node)
                    i = close + len(mark)
                    hit = True
                    break
        if hit:
            continue

        # $inline math$
        if ch == "$" and not s.startswith("$$", i):
            close = s.find("$", i + 1)
            if close > i + 1:
                _flush()
                out.append(types.TextMath(source=s[i + 1:close]))
                i = close + 1
                continue

        buf.append(ch)
        i += 1

    _flush()
    return out


_RICH_PLAIN = contextvars.ContextVar("nik_rich_plain", default=False)
# animation wale commands (hy/love/fun/story) rich me nahi chalte —
# frame-by-frame edit rich me atak jaata hai. Inke liye plain force.
_PLAIN_MODE = contextvars.ContextVar("nik_plain_mode", default=False)


def _rt(s, docs):
    """text → RichText · fake fonts saaf, premium emoji custom emoji."""
    if not s:
        return types.TextPlain("")
    if not isinstance(s, str):
        s = str(s)
    # NOTE: font chars (𝓝𝓲𝓴 / ᴍᴇɴᴜ) jaan-boojh ke rakhe hain — yahi bot ka
    # "new font" look hai. Sirf classification ke liye _plainify use hota hai.
    if _RICH_PLAIN.get():
        # documents resolve nahi hue → custom emoji mat bhejo, plain text
        return _rt_join(_rt_inline(s, docs))
    nodes, pos = [], 0
    if _RICH_EMOJI_RX is not None:
        for m in _RICH_EMOJI_RX.finditer(s):
            if len(docs) >= ART_EMOJI_CAP:
                break
            if m.start() > pos:
                nodes.extend(_rt_inline(s[pos:m.start()], docs))
            emo = m.group()
            did = _NIK_EMOJI_IDS.get(emo)
            if did:
                nodes.append(types.TextCustomEmoji(document_id=did, alt=emo))
                docs.add(did)
            else:
                nodes.append(types.TextPlain(emo))
            pos = m.end()
    if pos < len(s):
        nodes.extend(_rt_inline(s[pos:], docs))
    return _rt_join(nodes)


ART_LINK = "https://t.me/Nikkkwa"


def _art_style(color):
    """button ka rang — blue / red / green / link."""
    c = (color or "").strip().lower()
    if c in ("red", "danger", "r", "no"):
        return types.RichButtonStyle(bg_danger=True)
    if c in ("green", "success", "g", "ok"):
        return types.RichButtonStyle(bg_success=True)
    if c in ("link", "plain", "none", "flat"):
        return types.RichButtonStyle(link=True)
    return types.RichButtonStyle(bg_primary=True)


_ART_TPL_ROWS = {
    "vault": [
        ("💎", "premium set"), ("🪶", "exclusive"),
        ("🦋", "new collection"), ("🎀", "vip picks"),
        ("🔐", "vip vault"), ("🎁", "free gift"),
    ],
    "menu": [
        ("🎶", "music"), ("📼", "video"),
        ("🔮", "ai tools"), ("🎧", "voice chat"),
        ("🪄", "automation"), ("🔐", "notes"),
    ],
    "drop": [
        ("🔥", "fresh drop"), ("💎", "premium set"),
        ("🪶", "exclusive"), ("🎁", "free gift"),
        ("⚡", "instant"), ("👑", "vip only"),
    ],
}

_ART_TPL_BTNS = {
    "vault": [("blue", "🪶 WATCH NOW 🪶"), ("red", "🪶 OPEN CHAT 🪶"),
              ("green", "🪶 JOIN FREE 🪶"), ("red", "🪶 CLICK HERE 🪶"),
              ("green", "🪶 OPEN LINK 🪶"), ("blue", "🪶 EXPLORE 🪶")],
    "menu": [("blue", "🪶 START NOW 🪶"), ("green", "🪶 JOIN CHAT 🪶"),
             ("red", "🪶 VAULT 🪶")],
    "drop": [("blue", "🪶 GRAB NOW 🪶"), ("green", "🪶 JOIN FREE 🪶"),
             ("red", "🪶 VIP ACCESS 🪶")],
}

_ART_TPL_TAG = {
    "vault": ("💎 premium collection · fresh drops daily · instant access",
              "⚡ click below to unlock ⚡"),
    "menu": ("⚡ all in one · music · vc · tools · automation ⚡",
             "⚡ choose your section ⚡"),
    "drop": ("🔥 new drop live · limited time · instant delivery 🔥",
             "⚡ grab it before it's gone ⚡"),
    "links": ("⚡ saare links ek jagah · tap karo ⚡", ""),
}

_ART_TPL_NAMES = ("vault", "menu", "drop", "links")


def _art_tpl(name, title, urls):
    """premium design templates — seedha article source."""
    uu = [u for u in (urls or []) if u]

    def u(k):
        return uu[k] if k < len(uu) else ART_LINK

    name = (name or "").lower()
    if name not in _ART_TPL_NAMES:
        return ""
    t = title or "NIK VAULT"
    nl = "\n"

    if name == "links":
        rows = []
        labels = ["🪶 OPEN LINK", "🪶 JOIN NOW", "🪶 WATCH NOW",
                  "🪶 EXPLORE", "🪶 VAULT", "🪶 MORE"]
        colors = ["blue", "green", "red", "blue", "green", "red"]
        for k in range(max(len(uu), 1)):
            if k >= 6:
                break
            rows.append("[[btn:%s]] %s 🪶 | %s" % (colors[k], labels[k], u(k)))
        head = "# ⚡ " + t + " ⚡" + nl + nl
        sub_ = "> " + _ART_TPL_TAG["links"][0] + nl + nl
        tail = nl + "---" + nl + nl + "*⚡ powered by " + OWNER_TAG + " ⚡*"
        return head + sub_ + nl.join(rows) + tail

    cells = _ART_TPL_ROWS[name]
    grid = []
    for k in range(0, len(cells), 2):
        a = cells[k]
        b = cells[k + 1]
        grid.append("|%s  %s|%s  %s|" % (a[0], a[1], b[0], b[1]))

    btns = ["[[btn:%s]] %s | %s" % (c, label, u(i))
            for i, (c, label) in enumerate(_ART_TPL_BTNS[name])]

    head = "# ⚡ " + t + " ⚡" + nl + nl
    sub_ = "> " + _ART_TPL_TAG[name][0] + nl + nl
    grid_s = nl.join(grid) + nl + nl
    cta = "### " + _ART_TPL_TAG[name][1] + nl + nl
    btns_s = nl.join(btns) + nl + nl
    tail = "---" + nl + nl + "*⚡ powered by " + OWNER_TAG + " ⚡*"
    return head + sub_ + grid_s + cta + btns_s + tail


def _art_tpl_card():
    return "\n".join([
        top(hero=("📜", "⚡")),
        sub(""),
        sub(f" {E['bolt']} {sc('premium templates')} {E['dot']} {sc('rich design')}"),
        sub(""),
        sub(f" {E['dot']} {mono('.article tpl vault <title>')} {sc('grid + 6 buttons')}"),
        sub(f" {E['dot']} {mono('.article tpl menu <title>')} {sc('menu card')}"),
        sub(f" {E['dot']} {mono('.article tpl drop <title>')} {sc('drop card')}"),
        sub(f" {E['dot']} {mono('.article tpl links <title>')} {sc('links only')}"),
        sub(""),
        sub(f" {E['note']} {sc('urls')} {E['arrow']} {mono('title | url1 | url2 ...')}"),
        sub(f" {E['dot']} {sc('url na do')} {E['arrow']} {mono(ART_LINK)}"),
        sub(""),
        sub(f" {E['spark']} {sc('premium emoji + colour buttons automatic')}"),
        sub(FOOT),
        close(),
    ])


def _art_blocks(src, docs):
    """article source → PageBlock list (composer ke saare blocks)."""
    blocks, lines = [], (src or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i, n = 0, len(lines)

    def _cell(txt, hdr):
        """cell: [c]/[r]/[m]/[b] alignment · <<N colspan · ^^N rowspan"""
        t = (txt or "").strip()
        kw = {}
        if t.startswith("[c]"):
            kw["align_center"] = True
            t = t[3:].strip()
        elif t.startswith("[r]"):
            kw["align_right"] = True
            t = t[3:].strip()
        elif t.startswith("[m]"):
            kw["valign_middle"] = True
            t = t[3:].strip()
        elif t.startswith("[b]"):
            kw["valign_bottom"] = True
            t = t[3:].strip()
        m = re.search(r"<<(\d+)\s*$", t)
        if m:
            kw["colspan"] = max(1, min(ART_COLS, int(m.group(1))))
            t = t[:m.start()].rstrip()
        m = re.search(r"\^\^(\d+)\s*$", t)
        if m:
            kw["rowspan"] = max(1, min(ART_BLOCKS, int(m.group(1))))
            t = t[:m.start()].rstrip()
        if hdr:
            kw["header"] = True
        return types.PageTableCell(text=_rt(t, docs), **kw)

    while i < n:
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue

        # ── title / subtitle / kicker  (composer ka "Add title")
        m = re.match(r"^@(title|sub|subtitle|kick|kicker|header)\s+(.*)$", s, re.I)
        if m:
            kind = m.group(1).lower()
            # sab allowed shapes me (Title/Subtitle/Kicker server reject karta hai)
            if kind == "title":
                node = types.PageBlockHeading1(text=_rt(m.group(2), docs))
            elif kind in ("sub", "subtitle"):
                node = types.PageBlockParagraph(
                    text=types.TextItalic(text=_rt(m.group(2), docs)))
            elif kind in ("kick", "kicker"):
                node = types.PageBlockParagraph(
                    text=types.TextBold(text=_rt(m.group(2), docs)))
            else:
                node = types.PageBlockHeading3(text=_rt(m.group(2), docs))
            blocks.append(node)
            i += 1
            continue

        # ── code fence
        if s.startswith("```"):
            lang = s[3:].strip()
            j, buf = i + 1, []
            while j < n and not lines[j].strip().startswith("```"):
                buf.append(lines[j])
                j += 1
            blocks.append(types.PageBlockPreformatted(
                text=types.TextPlain("\n".join(buf)), language=lang))
            i = j + 1
            continue

        # ── divider
        if s in ("---", "***", "___"):
            blocks.append(types.PageBlockDivider())
            i += 1
            continue

        # ── heading
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            blocks.append(getattr(types, "PageBlockHeading%d" % lvl)(
                text=_rt(m.group(2), docs)))
            i += 1
            continue

        # ── math block  $$ ... $$
        if s.startswith("$$"):
            body = s[2:]
            if body.rstrip().endswith("$$") and len(body.strip()) > 2:
                blocks.append(types.PageBlockMath(source=body.rstrip()[:-2].strip()))
                i += 1
                continue
            j, buf = i + 1, [body]
            while j < n and "$$" not in lines[j]:
                buf.append(lines[j])
                j += 1
            if j < n:
                buf.append(lines[j].split("$$")[0])
                j += 1
            blocks.append(types.PageBlockMath(source="\n".join(buf).strip()))
            i = j
            continue

        # ── toggle / details  ::: Title ... :::
        if s.startswith(":::") or s == "??":
            title = s[3:].strip() if s.startswith(":::") else ""
            j, buf = i + 1, []
            while j < n and not (lines[j].strip().startswith(":::") or lines[j].strip() == "??"):
                buf.append(lines[j])
                j += 1
            blocks.append(types.PageBlockDetails(
                blocks=_art_blocks("\n".join(buf), docs),
                title=_rt(title or "more", docs), open=False))
            i = j + 1
            continue

        # ── quote
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(types.PageBlockBlockquote(
                text=_rt(" ".join(buf), docs), caption=types.TextEmpty()))
            continue

        # ── table
        if s.startswith("|") and s.endswith("|"):
            raw_rows, sep_at = [], None
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    sep_at = len(raw_rows)
                    i += 1
                    continue
                raw_rows.append(cells)
                i += 1
            rows = []
            for k, cells in enumerate(raw_rows):
                hdr = sep_at is not None and k < sep_at
                rows.append(types.PageTableRow(cells=[
                    _cell(c, hdr) for c in cells[:ART_COLS]]))
            if rows:
                blocks.append(types.PageBlockTable(
                    title=types.TextEmpty(), rows=rows,
                    bordered=True, striped=True))
            continue

        # ── buttons
        mb = re.match(r"^\[\[(?:btn|button)(?::([a-z]+))?\]\]\s*(.+)$", s, re.I)
        if mb:
            buttons = []
            while i < n:
                mm = re.match(r"^\[\[(?:btn|button)(?::([a-z]+))?\]\]\s*(.+)$",
                              lines[i].strip(), re.I)
                if not mm:
                    break
                bits = [x.strip() for x in mm.group(2).split("|")]
                label = bits[0]
                url = bits[1] if len(bits) > 1 else ""
                if not url:
                    i += 1
                    continue
                if url.lower().startswith(("http", "tg://", "mailto:")):
                    btype = types.InlineButtonTypeUrl(url=url)
                else:
                    btype = types.InlineButtonTypeCallback(data=url.encode()[:60])
                buttons.append(types.PageButton(
                    text=_rt(label, docs), type=btype,
                    style=_art_style(mm.group(1) or "blue")))
                i += 1
            if buttons:
                blocks.append(types.PageBlockButtonRow(buttons=buttons[:8]))
            continue

        # ── ordered list
        if re.match(r"^\d+[.)]\s+", s):
            items = []
            while i < n:
                mm = re.match(r"^(\d+)[.)]\s+(.*)$", lines[i].strip())
                if not mm:
                    break
                items.append(types.PageListOrderedItemText(
                    text=_rt(mm.group(2), docs), num=mm.group(1)))
                i += 1
            blocks.append(types.PageBlockOrderedList(items=items, type="1"))
            continue

        # ── checklist  - [x] done
        if re.match(r"^[-*+]\s+\[[ xX]\]\s+", s):
            items = []
            while i < n:
                mm = re.match(r"^[-*+]\s+\[([ xX])\]\s+(.*)$", lines[i].strip())
                if not mm:
                    break
                items.append(types.PageListItemText(
                    text=_rt(mm.group(2), docs), checkbox=True,
                    checked=(mm.group(1).lower() == "x")))
                i += 1
            blocks.append(types.PageBlockList(items=items))
            continue

        # ── bullet list
        if re.match(r"^[-*+]\s+", s):
            items = []
            while i < n:
                mm = re.match(r"^[-*+]\s+(.*)$", lines[i].strip())
                if not mm:
                    break
                items.append(types.PageListItemText(text=_rt(mm.group(1), docs)))
                i += 1
            blocks.append(types.PageBlockList(items=items))
            continue

        # ── paragraph
        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|@(title|sub|subtitle|kick|kicker|header)\s|[-*+]\s|\d+[.)]\s"
                r"|>\s?|\||`{3}|:::|\?\?|\[\[|---$|\*\*\*$|___$|\$\$)",
                lines[i].strip(), re.I):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(types.PageBlockParagraph(text=_rt(" ".join(buf), docs)))

    return blocks[:ART_BLOCKS]


def _rt_flat(rt):
    """RichText → plain string (read / preview ke liye)."""
    if rt is None:
        return ""
    t = type(rt)
    if t is types.TextPlain:
        return rt.text
    if t is types.TextEmpty:
        return ""
    if t is types.TextConcat:
        return "".join(_rt_flat(x) for x in rt.texts)
    if t is types.TextCustomEmoji:
        return rt.alt
    if t is types.TextUrl:
        return "%s (%s)" % (_rt_flat(rt.text), rt.url)
    if t is types.TextMath:
        return "$%s$" % rt.source
    if t is types.TextImage:
        return "🖼"
    inner = getattr(rt, "text", None)
    if inner is not None:
        return _rt_flat(inner)
    return ""


def _art_flat(blocks, depth=0):
    """RichMessage blocks → markdown-ish text."""
    out = []
    for b in blocks or []:
        name = type(b).__name__
        if name.startswith("PageBlockHeading"):
            out.append("#" * int(name[-1]) + " " + _rt_flat(getattr(b, "text", None)))
        elif name == "PageBlockParagraph":
            out.append(_rt_flat(b.text))
        elif name == "PageBlockPreformatted":
            out.append("```%s\n%s\n```" % (getattr(b, "language", "") or "", _rt_flat(b.text)))
        elif name == "PageBlockDivider":
            out.append("---")
        elif name == "PageBlockMath":
            out.append("$$%s$$" % b.source)
        elif name == "PageBlockBlockquote":
            out.append("> " + _rt_flat(b.text))
        elif name == "PageBlockPullquote":
            out.append("> " + _rt_flat(b.text))
        elif name == "PageBlockThinking":
            out.append(_rt_flat(b.text))
        elif name == "PageBlockList":
            for it in b.items:
                out.append("• " + _rt_flat(getattr(it, "text", None)))
        elif name == "PageBlockOrderedList":
            for k, it in enumerate(b.items, 1):
                out.append("%s. %s" % (getattr(it, "num", None) or k,
                                       _rt_flat(getattr(it, "text", None))))
        elif name == "PageBlockTable":
            for row in b.rows:
                out.append("| " + " | ".join(_rt_flat(c.text) for c in row.cells) + " |")
        elif name == "PageBlockDetails":
            out.append("::: " + _rt_flat(b.title))
            out.append(_art_flat(b.blocks, depth + 1))
            out.append(":::")
        elif name == "PageBlockButtonRow":
            out.append(" · ".join(_rt_flat(getattr(btn, "text", None)) for btn in b.buttons))
        elif getattr(b, "caption", None) is not None:
            cap = getattr(b.caption, "text", None)
            if cap is not None:
                out.append(_rt_flat(cap))
    return "\n".join(x for x in out if x)


_DOC_CACHE: Dict[int, Any] = {}


_DOC_COOLDOWN = {"until": 0.0}


async def _rich_docs(ids):
    """custom emoji document ids → InputDocument list (cached + retry)."""
    if not ids:
        return []
    if time.time() < _DOC_COOLDOWN["until"]:
        return []                      # server fail ho raha → fail-fast
    for attempt in range(2):
        miss = [i for i in ids if i not in _DOC_CACHE]
        if not miss:
            break
        try:
            got = await bot(functions.messages.GetCustomEmojiDocumentsRequest(
                document_id=miss[:100]))
            for d in got:
                _DOC_CACHE[d.id] = types.InputDocument(
                    id=d.id, access_hash=d.access_hash,
                    file_reference=d.file_reference)
            if not got:
                break
        except Exception as _e:
            if attempt == 1:
                _rm_log("emoji docs", _e)
                _DOC_COOLDOWN["until"] = time.time() + 45    # 45 sec skip (10 min bahut tha)
            await asyncio.sleep(0.4 * (attempt + 1))
    return [_DOC_CACHE[i] for i in ids if i in _DOC_CACHE]


_RICH_ERR_SEEN: Set[str] = set()


def _rm_log(where, ex):
    """rich fail hone pe console pe saaf batao (throttled)."""
    key = "%s:%s" % (where, type(ex).__name__)
    if key in _RICH_ERR_SEEN:
        return
    _RICH_ERR_SEEN.add(key)
    print(f"[RICH ❌ {where}] {type(ex).__name__}: {str(ex)[:160]}")


async def _rich_premium():
    """(premium?, me) — article bhejne ki permission."""
    try:
        me = await bot.get_me()
        return bool(getattr(me, "premium", False) or getattr(me, "bot", False)), me
    except Exception:
        return False, None


async def _art_photo(event, reply):
    """replied photo → InputPhoto (article ke andar lagane ke liye)."""
    if reply is None or getattr(reply, "photo", None) is None:
        return None
    try:
        buf = await reply.download_media(file=BytesIO())
        if buf is None:
            return None
        data = buf.getvalue() if hasattr(buf, "getvalue") else buf
        up = await bot.upload_file(BytesIO(data), file_name="article.jpg")
        peer = await event.get_input_chat() or await bot.get_input_entity(event.chat_id)
        res = await bot(functions.messages.UploadMediaRequest(
            peer=peer, media=types.InputMediaUploadedPhoto(file=up)))
        ph = getattr(res, "photo", None)
        if ph is None:
            return None
        return types.InputPhoto(id=ph.id, access_hash=ph.access_hash,
                                file_reference=ph.file_reference)
    except Exception:
        return None


async def _art_build(source, mode="blocks"):
    """source → InputRichMessage (+ documents)."""
    docs = set()
    if mode == "md":
        return types.InputRichMessageMarkdown(markdown=source)
    if mode == "html":
        return types.InputRichMessageHTML(html=source)
    blocks = _art_blocks(source, docs)
    if not blocks:
        blocks = [types.PageBlockParagraph(text=types.TextPlain(source))]
    docs_in = await _rich_docs(docs) if docs else []
    if docs and len(docs_in) < len(docs):
        _rm_log("article docs", RuntimeError("%d/%d" % (len(docs_in), len(docs))))
        tok = _RICH_PLAIN.set(True)
        try:
            docs = set()
            blocks = _art_blocks(source, docs)
        finally:
            _RICH_PLAIN.reset(tok)
        docs_in = []
    rich = types.InputRichMessage(blocks=_sanitize_blocks(blocks))
    if docs_in:
        rich.documents = docs_in
    return rich


async def _art_send(event, source, mode="blocks", reply_to=None,
                    edit_id=None, draft=False, photo=None, media=None):
    """asli send — raw SendMessageRequest / EditMessageRequest / setTyping."""
    rich = await _art_build(source, mode)
    if photo is not None:
        rich = await _art_add_photo(rich, photo)
    if media is not None:
        blk, phs, dcs = media
        if isinstance(rich, types.InputRichMessage):
            try:
                if blk is not None:
                    rich.blocks.insert(0, blk)
                if phs:
                    rich.photos = list(phs) + list(getattr(rich, "photos", None) or [])
                if dcs:
                    rich.documents = list(dcs) + list(getattr(rich, "documents", None) or [])
            except Exception:
                pass
    peer = await event.get_input_chat()
    if peer is None:
        peer = await bot.get_input_entity(event.chat_id)

    if draft:
        await bot(functions.messages.SetTypingRequest(
            peer=peer,
            action=types.InputSendMessageRichMessageDraftAction(
                rich_message=rich, random_id=random.getrandbits(62))))
        return None

    if edit_id:
        return await bot(functions.messages.EditMessageRequest(
            peer=peer, id=edit_id, message="", rich_message=rich))

    return await bot(functions.messages.SendMessageRequest(
        peer=peer, message="", rich_message=rich,
        random_id=random.getrandbits(62), reply_to=reply_to))


def _art_ok(text):
    """article ka source theek hai?"""
    if not text or not text.strip():
        return False, "khaali article"
    if len(text) > ART_LIMIT:
        return False, "limit se zyada (%d > %d)" % (len(text), ART_LIMIT)
    return True, ""


async def _art_reply_media(event, reply):
    """reply ki media → (block, photos, documents) article ke andar lagane ke liye."""
    if reply is None:
        return None, [], []
    try:
        cap = types.PageCaption(text=types.TextEmpty(), credit=types.TextEmpty())
        if getattr(reply, "photo", None) is not None:
            buf = await reply.download_media(file=BytesIO())
            if buf is None:
                return None, [], []
            path = os.path.join(TEMP_PATH, "art_ph_%d.jpg" % random.getrandbits(32))
            open(path, "wb").write(buf.getvalue() if hasattr(buf, "getvalue") else buf)
            ph = await _art_up_photo(event, path)
            try:
                os.remove(path)
            except Exception:
                pass
            if ph is None:
                return None, [], []
            return (types.PageBlockPhoto(photo_id=ph.id, caption=cap), [ph], [])

        kind = None
        if getattr(reply, "video", None) is not None:
            kind = "video"
        elif getattr(reply, "audio", None) is not None:
            kind = "audio"
        elif getattr(reply, "voice", None) is not None:
            kind = "audio"
        elif getattr(reply, "document", None) is not None:
            kind = "doc"
        if kind is None:
            return None, [], []

        path = await reply.download_media(file=TEMP_PATH)
        if not path:
            return None, [], []
        audio = {"duration": int(getattr(getattr(reply, "audio", None), "duration", 0)
                                 or getattr(getattr(reply, "voice", None), "duration", 0) or 0),
                 "title": (getattr(reply, "file", None) and
                           getattr(reply.file, "name", "") or "")[:64],
                 "performer": OWNER_TAG}
        video = {"duration": int(getattr(getattr(reply, "video", None), "duration", 0) or 0)}
        doc = await _art_up_doc(event, path, audio=(audio if kind == "audio" else None),
                                video=(video if kind == "video" else None))
        try:
            os.remove(path)
        except Exception:
            pass
        if doc is None:
            return None, [], []
        if kind == "audio":
            blk = types.PageBlockAudio(audio_id=doc.id, caption=cap)
        elif kind == "video":
            blk = types.PageBlockVideo(video_id=doc.id, caption=cap)
        else:
            blk = types.PageBlockDocument(document_id=doc.id, caption=cap)
        return blk, [], [doc]
    except Exception:
        return None, [], []


async def _art_add_photo(rich, photo):
    """article ke upar cover photo (composer jaisa inline media)."""
    if photo is None or not isinstance(rich, types.InputRichMessage):
        return rich
    try:
        cap = types.PageCaption(text=types.TextEmpty(), credit=types.TextEmpty())
        rich.blocks.insert(0, types.PageBlockPhoto(photo_id=photo.id, caption=cap))
        rich.photos = [photo]
    except Exception:
        pass
    return rich


# ══════════════════════════════════════════════════════════════
#   📎  ʀɪᴄʜ ᴍᴇᴅɪᴀ  —  media + article ek hi message me
# ══════════════════════════════════════════════════════════════
# Composer ka Article attachment: photo/video/audio/document article ke
# ANDAR inline baithta hai (PageBlockPhoto/Video/Audio/Document), file
# alag se attach nahi hoti — wahi block hi attachment hai.
_ART_MIME = {
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
    ".opus": "audio/opus", ".wav": "audio/wav", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".mkv": "video/x-matroska", ".webm": "video/webm",
    ".mov": "video/quicktime", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
    ".pdf": "application/pdf",
}


def _art_mime(path):
    return _ART_MIME.get(os.path.splitext(str(path))[1].lower(),
                         "application/octet-stream")


async def _art_up_doc(event, path, *, audio=None, video=None, fname=None):
    """local file → (InputDocument, upload_media_result)."""
    peer = await event.get_input_chat()
    if peer is None:
        peer = await bot.get_input_entity(event.chat_id)
    ext = os.path.splitext(str(path))[1].lower()
    safe = re.sub(r'[\\/:*?"<>|]+', " ", fname or os.path.basename(str(path)))
    safe = (safe or "nik")[:80]
    if not safe.lower().endswith(ext):
        safe += ext
    attrs = [types.DocumentAttributeFilename(file_name=safe)]
    if audio:
        attrs.append(types.DocumentAttributeAudio(
            duration=int(audio.get("duration") or 0),
            title=(audio.get("title") or "")[:64] or None,
            performer=(audio.get("performer") or OWNER_TAG)[:64],
            voice=bool(audio.get("voice"))))
    if video:
        attrs.append(types.DocumentAttributeVideo(
            duration=float(video.get("duration") or 0),
            w=int(video.get("w") or 1280), h=int(video.get("h") or 720),
            supports_streaming=True))
    up = await bot.upload_file(path, file_name=safe)
    res = await bot(functions.messages.UploadMediaRequest(
        peer=peer,
        media=types.InputMediaUploadedDocument(
            file=up, mime_type=_art_mime(path), attributes=attrs,
            force_file=bool(video is None and audio is None))))
    doc = getattr(res, "document", None)
    if doc is None:
        return None
    return types.InputDocument(id=doc.id, access_hash=doc.access_hash,
                               file_reference=doc.file_reference)


async def _art_up_photo(event, path):
    """local image → InputPhoto."""
    peer = await event.get_input_chat()
    if peer is None:
        peer = await bot.get_input_entity(event.chat_id)
    up = await bot.upload_file(path, file_name="nik_cover.jpg")
    res = await bot(functions.messages.UploadMediaRequest(
        peer=peer, media=types.InputMediaUploadedPhoto(file=up)))
    ph = getattr(res, "photo", None)
    if ph is None:
        return None
    return types.InputPhoto(id=ph.id, access_hash=ph.access_hash,
                            file_reference=ph.file_reference)


def _art_cover(url):
    """thumbnail → local file (article ke cover ke liye)."""
    if not url or not str(url).startswith("http"):
        return None
    try:
        r = requests.get(url, timeout=12)
        if getattr(r, "status_code", 0) != 200 or not r.content:
            return None
        path = os.path.join(TEMP_PATH, "art_cover_%d.jpg" % random.getrandbits(32))
        with open(path, "wb") as f:
            f.write(r.content[:3_000_000])
        return path if os.path.getsize(path) > 2000 else None
    except Exception:
        return None


def _art_cap(text, docs):
    return types.PageCaption(text=_rt(text or "", docs), credit=types.TextEmpty())


async def rich_media(event, path=None, *, kind="doc", title="", subtitle="",
                     rows=None, caption="", buttons=None, reply_to=None,
                     audio=None, video=None, fname=None, cover=None,
                     footer=True):
    """media + article ek message me. fail → None (caller plain bhej de)."""
    if not RICH_READY:
        return None
    if not await _ui_rich_ok():
        return None
    try:
        docs = set()
        blocks = []
        photos_in, documents_in = [], []

        # cover photo (music ka album art jaisa)
        photo_in = None
        if cover:
            photo_in = await _art_up_photo(event, cover)
            if photo_in is not None:
                blocks.append(types.PageBlockPhoto(
                    photo_id=photo_in.id, caption=_art_cap("", docs)))
                photos_in.append(photo_in)

        if title:
            blocks.append(types.PageBlockHeading1(text=_rt(title, docs)))
        if subtitle:
            blocks.append(types.PageBlockParagraph(text=_rt(subtitle, docs)))

        if path:
            if kind == "photo":
                photo_in = photo_in or await _art_up_photo(event, path)
                if photo_in is not None:
                    blocks.append(types.PageBlockPhoto(
                        photo_id=photo_in.id, caption=_art_cap(caption, docs)))
                    photos_in.append(photo_in)
            else:
                doc = await _art_up_doc(event, path, audio=audio,
                                        video=video, fname=fname)
                if doc is None:
                    return None
                cap = _art_cap(caption, docs)
                if kind == "audio":
                    blocks.append(types.PageBlockAudio(
                        audio_id=doc.id, caption=cap))
                elif kind == "video":
                    blocks.append(types.PageBlockVideo(
                        video_id=doc.id, caption=cap, autoplay=False))
                else:
                    blocks.append(types.PageBlockDocument(
                        document_id=doc.id, caption=cap))
                documents_in.append(doc)
        elif caption:
            blocks.append(types.PageBlockParagraph(text=_rt(caption, docs)))

        if rows:
            blocks.append(types.PageBlockTable(
                title=types.TextEmpty(),
                rows=[types.PageTableRow(cells=[
                    types.PageTableCell(text=_rt(a, docs)),
                    types.PageTableCell(text=_rt(b, docs)),
                ]) for a, b in rows if a],
                bordered=True, striped=True))

        if buttons:
            bs = []
            for label, url, color in buttons[:8]:
                if not url:
                    continue
                bs.append(types.PageButton(
                    text=_rt(label, docs),
                    type=types.InlineButtonTypeUrl(url=url),
                    style=_art_style(color)))
            if bs:
                blocks.append(types.PageBlockButtonRow(buttons=bs))

        if footer:
            blocks.append(types.PageBlockDivider())
            blocks.append(types.PageBlockParagraph(
                text=_rt("⚡ powered by " + OWNER_TAG + " ⚡", docs)))

        if len(blocks) < 2:
            return None

        rich = types.InputRichMessage(blocks=_sanitize_blocks(blocks)[:ART_BLOCKS])
        docs_in = await _rich_docs(docs)
        if photos_in:
            rich.photos = photos_in
        if documents_in or docs_in:
            rich.documents = documents_in + docs_in

        peer = await event.get_input_chat()
        if peer is None:
            peer = await bot.get_input_entity(event.chat_id)
        await bot(functions.messages.SendMessageRequest(
            peer=peer, message="", rich_message=rich,
            random_id=random.getrandbits(62), reply_to=reply_to))
        return True
    except Exception as _e:
        if os.environ.get("RICH_DEBUG"):
            print("[RICH MEDIA]", type(_e).__name__, _e)
        return None


def _art_err(ex):
    """error ko insaan ki bhasha me."""
    s = str(ex)
    low = s.lower()
    if "premium" in low:
        return "account premium nahi hai"
    if "flood" in low:
        return "flood wait — thodi der baad"
    if "too_long" in low or "too long" in low:
        return "article bahut lamba"
    if "rich" in low and ("unsupport" in low or "invalid" in low):
        return "server ne rich message reject kiya"
    return err_txt(ex, 70)


def _art_card():
    return "\n".join([
        top(hero=("📜", "✨")),
        sub(""),
        sub(f" {E['note']} {sc('article')}  {E['dot']}  {sc('rich messages')} {E['dot']} {mono('layer 227+')}"),
        sub(""),
        sub(f" {E['arrow']} {mono('.article')} {sc('text pe reply → article')}"),
        sub(f" {E['dot']}  {mono('.article <text>')} {sc('seedha article')}"),
        sub(f" {E['dot']}  {mono('.article md')} {sc('raw markdown')}"),
        sub(f" {E['dot']}  {mono('.article html')} {sc('raw html')}"),
        sub(f" {E['dot']}  {mono('.article demo')} {sc('sample article')}"),
        sub(f" {E['dot']}  {mono('.article tpl')} {sc('premium design templates')}"),
        sub(f" {E['dot']}  {mono('.article read')} {sc('reply → text nikalo')}"),
        sub(f" {E['dot']}  {mono('.article edit <text>')} {sc('message ko article banao')}"),
        sub(f" {E['dot']}  {mono('.article draft <text>')} {sc('live typing preview')}"),
        sub(f" {E['dot']}  {mono('.article check')} {sc('premium + support')}"),
        sub(""),
        sub(f" {E['gem']} {sc('syntax')} {E['dot']} {sc('jaise composer me')}"),
        sub(f" {E['dot']}  {mono('@title')} {sc('bada title')} {E['dot']} {mono('@sub')} {sc('subtitle')}"),
        sub(f" {E['dot']}  {mono('#')} {sc('heading 1-6')} {E['dot']} {mono('- [x]')} {sc('checklist')}"),
        sub(f" {E['dot']}  {mono('|')} {sc('table')} {E['dot']} {mono('[c] [r] <<2 ^^2')} {sc('align · merge')}"),
        sub(f" {E['dot']}  {mono('-')} {sc('bullet')} {E['dot']} {mono('1.')} {sc('number')}"),
        sub(f" {E['dot']}  {mono('>')} {sc('quote')} {E['dot']} {mono('```')} {sc('code')}"),
        sub(f" {E['dot']}  {mono(':::')} {sc('toggle')} {E['dot']} {mono('$$')} {sc('math')} {E['dot']} {mono('---')} {sc('divider')}"),
        sub(f" {E['dot']}  {mono('**b** *i* ~~s~~ ||sp||')}"),
        sub(f" {E['eye']} {sc('photo pe reply')} {E['arrow']} {sc('article ke andar cover')}"),
        sub(f" {E['spark']} {sc('premium emoji automatic')} {E['arrow']} {sc('article ke andar')}"),
        sub(""),
        sub(f" {E['warn']} {sc('bhejne ke liye account premium')} {E['dot']} {mono('bots exempt')}"),
        sub(FOOT),
        close(),
    ])


@register_cmd("article", "rich")
async def cmd_article(event, arg):
    """.article — Telegram rich message / article banane ke liye"""
    if not RICH_READY:
        return await eor(event, "\n".join([
            top(hero=("📜", "✨")), sub(""),
            sub(f" {E['no']} {sc('telethon purani hai')} {E['dot']} {mono('pip install -U telethon')}"),
            sub(f" {E['dot']} {sc('chahiye')} {mono('telethon>=1.45')} {sc('(layer 229)')}"),
            sub(""), sub(FOOT), close()]))

    arg = (arg or "").strip()
    low = arg.lower()
    reply = await event.get_reply_message()

    # ── koi arg nahi → card
    if not arg and not reply:
        return await eor(event, _art_card())

    # ── check
    if low in ("check", "status", "info"):
        prem, me = await _rich_premium()
        name = getattr(me, "first_name", None) or "—"
        return await eor(event, "\n".join([
            top(hero=("📜", "✨")), sub(""),
            sub(f" {E['note']} {sc('rich message support')} {E['arrow']} "
                f"{mono('ON' if RICH_READY else 'OFF')}"),
            sub(f" {E['dot']} {sc('telethon')} {E['arrow']} {mono(__import__('telethon').__version__)}"),
            sub(f" {E['dot']} {sc('account')} {E['arrow']} {mono(name)}"),
            sub(f" {E['dot']} {sc('premium')} {E['arrow']} "
                f"{mono('YES' if prem else 'NO')}"),
            sub(f" {E['dot']} {sc('emoji ids')} {E['arrow']} {mono(str(len(_NIK_EMOJI_IDS)))}"),
            sub(""),
            sub(f" {E['dot']} {sc('limit')} {E['arrow']} {mono(str(ART_LIMIT))} {sc('chars')}"),
            sub(f" {E['dot']} {sc('blocks')} {E['arrow']} {mono(str(ART_BLOCKS))} "
                f"{E['dot']} {sc('table cols')} {mono(str(ART_COLS))}"),
            sub(""),
            sub(f" {E['warn'] if not prem else E['ok']} "
                f"{sc('send karne ke liye premium chahiye') if not prem else sc('sab ready')}"),
            sub(FOOT), close()]))

    # ── stop draft
    if low in ("stop", "cancel"):
        try:
            await bot(functions.messages.SetTypingRequest(
                peer=await event.get_input_chat(),
                action=types.SendMessageStopDraftAction(random_id=random.getrandbits(62))))
        except Exception as e:
            return await eor(event, f"{E['no']} {sc('stop fail')} {E['arrow']} {mono(_art_err(e))}")
        return await eor(event, f"{E['ok']} {sc('draft rok diya')}")

    prem, me = await _rich_premium()

    # ── read
    if low in ("read", "get", "show"):
        if not reply:
            return await eor(event, f"{E['warn']} {sc('article message pe reply karo')}")
        rm = getattr(reply, "rich_message", None)
        if rm is None:
            return await eor(event, f"{E['no']} {sc('ye rich message nahi hai')}")
        if getattr(rm, "part", False):
            try:
                got = await bot(functions.messages.GetRichMessageRequest(
                    peer=await event.get_input_chat(), id=reply.id))
                first = getattr(got, "messages", None)
                if first:
                    rm = getattr(first[0], "rich_message", rm) or rm
            except Exception:
                pass
        txt = _art_flat(rm.blocks)
        head = (f" {E['note']} {sc('blocks')} {mono(str(len(rm.blocks)))} "
                f"{E['dot']} {sc('emoji')} {mono(str(len(getattr(rm, 'documents', []) or [])))}")
        body = txt if len(txt) <= 3000 else txt[:3000] + "\n…"
        return await eor(event, "\n".join([
            top(hero=("📜", "✨")), sub(""), sub(head), sub(""),
            sub(f" {E['dot']} {sc('text')} {E['arrow']}"), sub(""), body,
            sub(""), sub(FOOT), close()]))

    # ── demo
    if low in ("demo", "sample", "test"):
        arg = (
            "# 📜 NIK ARTICLE\n\n"
            "Telegram ka naya **Rich Text Editor** — ab bot se bhi.\n"
            "Premium emoji 🔥💎✨ article ke andar automatic lag jaate hain.\n\n"
            "## Features\n\n"
            "- Heading 1-6\n- Table\n- Bullet + numbered list\n- Quote, code, math\n\n"
            "## Rates\n\n"
            "| Plan | Price | Days |\n|---|---|---|\n"
            "| Basic | ₹99 | 30 |\n| Pro | **₹249** | 90 |\n\n"
            "> Article ek hi message me — 32,768 characters tak.\n\n"
            "```python\nprint('nik userbot')\n```\n\n"
            "::: Andar chhupa text\nDetails block bhi kaam karta hai.\n:::\n\n"
            "$$E = mc^2$$\n\n---\n\n"
            "*Powered by @Nikkkwa*"
        )
        mode = "blocks"
    else:
        mode = "blocks"
        tpl_mode = False
        if low.startswith(("tpl", "design")):
            rest = arg.split(None, 1)[1].strip() if " " in arg else ""
            if not rest:
                return await eor(event, _art_tpl_card())
            parts = [x.strip() for x in rest.split("|")]
            head = parts[0]
            first = head.split()[0].lower() if head.split() else ""
            if first in _ART_TPL_NAMES:
                nm, ttl = first, head[len(first):].strip()
            else:
                nm, ttl = "vault", head
            arg = _art_tpl(nm, ttl, [x for x in parts[1:] if x])
            tpl_mode = True
            mode = "blocks"
            if not arg:
                return await eor(event, _art_tpl_card())
        elif low.startswith("md "):
            mode, arg = "md", arg[3:].strip()
        elif low.startswith("html "):
            mode, arg = "html", arg[5:].strip()
        elif low.startswith("edit "):
            arg = arg[5:].strip()
            if not reply:
                return await eor(event, f"{E['warn']} {sc('jis message ko edit karna hai uspe reply')}")
            ok, why = _art_ok(arg)
            if not ok:
                return await eor(event, f"{E['no']} {mono(why)}")
            try:
                await _art_send(event, arg, mode, edit_id=reply.id)
            except Exception as e:
                return await eor(event, f"{E['no']} {sc('edit fail')} {E['arrow']} {mono(_art_err(e))}")
            return await eor(event, f"{E['ok']} {sc('message article ban gaya')}")
        elif low.startswith("draft "):
            arg = arg[6:].strip()
            ok, why = _art_ok(arg)
            if not ok:
                return await eor(event, f"{E['no']} {mono(why)}")
            if not prem:
                return await eor(event, _art_premium_card())
            try:
                await _art_send(event, arg, mode, draft=True)
            except Exception as e:
                return await eor(event, f"{E['no']} {sc('draft fail')} {E['arrow']} {mono(_art_err(e))}")
            return await eor(event, f"{E['ok']} {sc('draft stream ho raha hai')} {E['dot']} "
                                    f"{mono('.article stop')} {sc('se roko')}")
        elif arg.lower().startswith("md"):
            mode = "md"
            if reply and hasattr(reply, "message"):
                arg = reply.raw_text or reply.message or ""

    # ── source: reply se text/file
    src = arg
    if not src and reply:
        doc = getattr(reply, "document", None)
        fname = ""
        if doc is not None:
            for at in (getattr(doc, "attributes", None) or []):
                fn = getattr(at, "file_name", None)
                if fn:
                    fname = fn
                    break
        if fname.lower().endswith((".md", ".markdown", ".txt")):
            try:
                data = await reply.download_media(file=BytesIO())
                if hasattr(data, "getvalue"):
                    src = data.getvalue().decode("utf-8", "ignore")
            except Exception:
                src = ""
        if not src:
            src = getattr(reply, "raw_text", None) or getattr(reply, "message", None) or ""

    ok, why = _art_ok(src)
    if not ok:
        return await eor(event, f"{E['no']} {mono(why)} {E['dot']} "
                                f"{mono(f'{len(src)}/{ART_LIMIT}')}")

    if not prem:
        return await eor(event, _art_premium_card())

    reply_to = None
    if (reply is not None and mode == "blocks" and src and arg
            and not locals().get("tpl_mode", False)):
        reply_to = types.InputReplyToMessage(reply_to_msg_id=reply.id)

    try:
        await _art_send(event, src, mode, reply_to=reply_to,
                        photo=await _art_photo(event, reply),
                        media=await _art_reply_media(event, reply))
    except Exception as e:
        return await eor(event, "\n".join([
            top(hero=("📜", "✨")), sub(""),
            sub(f" {E['no']} {sc('article nahi gaya')}"),
            sub(f" {E['dot']} {mono(_art_err(e))}"),
            sub(""),
            sub(f" {E['warn']} {sc('premium check')} {E['arrow']} {mono('.article check')}"),
            sub(FOOT), close()]))

    try:
        await event.message.delete()
    except Exception:
        pass



def _art_premium_card():
    return "\n".join([
        top(hero=("📜", "✨")), sub(""),
        sub(f" {E['lock']} {sc('rich article bhejne ke liye')} "
            f"{mono('Telegram Premium')} {sc('chahiye')}"),
        sub(""),
        sub(f" {E['dot']} {sc('padhna sab kar sakte hain')}"),
        sub(f" {E['dot']} {sc('bhejna sirf premium / bot')}"),
        sub(""),
        sub(f" {E['note']} {sc('account premium karne ke baad')} {mono('.article <text>')}"),
        sub(FOOT), close()])


# ══════════════════════════════════════════════════════════════
#                        ᴅɪsᴘᴀᴛᴄʜᴇʀ
# ══════════════════════════════════════════════════════════════
async def dispatcher(event):
    """wrapper — current client set karke asli dispatcher chalata hai"""
    token = _CURRENT_CLIENT.set(getattr(event, "client", None) or _REAL_BOT)
    try:
        await _dispatch(event)
    finally:
        _CURRENT_CLIENT.reset(token)


# animation wale commands — inse rich text bilkul nahi (frames plain me chalte hain)
PLAIN_CMDS = frozenset(
    {"hy", "love", "lovestory"} |
    {"love%d" % _i for _i in range(1, 6)} |
    {"fun%d" % _i for _i in range(1, 9)}
)


def _looks_like_cmd(text) -> bool:
    """prefix ho ya na ho — text command lag raha hai?"""
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith(PREFIX):
        return True
    return t.split(maxsplit=1)[0].lower() in commands


async def _dispatch(event):
    text = event.raw_text or ""
    if not text:
        return

    prefixed = text.startswith(PREFIX)
    body = (text[len(PREFIX):] if prefixed else text).strip()
    if not body:
        return
    parts = body.split(maxsplit=1)
    cmd = parts[0].lower().strip()
    arg = parts[1].strip() if len(parts) > 1 else ""

    data = commands.get(cmd)
    if not data:
        return

    sender = event.sender_id
    if not sender:
        return

    # outgoing = apne hi account se command (subbot bhi isi me aata hai)
    self_side = bool(getattr(event, "out", False)) or sender in SUBBOT_IDS

    if not prefixed:
        # bina prefix: sirf owner / apna account. Sudo ke liye nahi —
        # group me "ban"/"id" jaisa normal word galti se na chal jaye.
        if not PREFIX_STATE.get("optional", NOPREFIX):
            return
        if sender != OWNER_ID and not self_side:
            return

    if sender != OWNER_ID and not self_side:
        if sender not in ADMINS:
            # .lockmsg / .glockmsg off → chup-chaap ignore (spam se bachne ke liye)
            if lockmsg_on(getattr(event, "chat_id", None)):
                try:
                    n = await event.reply(f"{E['crown']} {sb('NIK USERBOT')} {E['arrow']} "
                                          f"{sc('owner / sudo only')} {E['lock']}")
                    asyncio.create_task(_del_after(n, 5))
                except Exception:
                    pass
            return
        if data.get("owner_only") or cmd in OWNER_ONLY_EXTRA:
            await flash(event, f"{E['no']} {sc('owner only command')} {E['crown']}", secs=5)
            return

    if data.get("group_only"):
        try:
            if not event.is_group:
                await flash(event, f"{E['warn']} {sc('ye command sirf group me chalti hai')}", secs=5)
                return
        except Exception:
            return

    if data.get("needs_reply"):
        try:
            if not event.is_reply and not arg:
                await flash(event, f"{E['no']} {sc('reply ya target do')}\n"
                                   f"{E['dot']} {mono(PREFIX + cmd + ' @user / id')}", secs=5)
                return
        except Exception:
            return

    _tok = _PLAIN_MODE.set(cmd in PLAIN_CMDS)
    try:
        await data["func"](event, arg)
    except FloodWaitError as e:
        try:
            await eor(event, f"{E['wait']} {sc('floodwait')} {E['arrow']} {mono(str(e.seconds) + 's')}")
        except Exception:
            pass
    except Exception as e:
        try:
            await eor(event, f"{E['no']} {sc('error')} {E['arrow']} {mono(err_txt(e, 70))}")
        except Exception:
            pass
    finally:
        _PLAIN_MODE.reset(_tok)


# main account pe dispatcher + baka tracker + setup buttons
register_client_handlers(_REAL_BOT)


# ══════════════════════════════════════════════════════════════
#                           sᴛᴀʀᴛ
# ══════════════════════════════════════════════════════════════
async def main():
    if not _config_ok():
        return
    if not SESSION_IS_STRING:
        print("[SESSION] koi session string nahi mili → phone number poocha jayega")
        print("[SESSION] login ke baad " + SESSION_FILE + ".session ban jayegi — agli baar seedha chalega\n")
    try:
        await bot.start()
        me = await bot.get_me()
        un = f"@{me.username}" if getattr(me, "username", None) else "NoUsername"
        print("─" * 42)
        print(f"  {scrb('Nik Userbot')} {VERSION}  ·  ɢʟᴏʙᴀʟ")
        print(f"  {me.first_name} ({un})  —  {me.id}")
        print(f"  commands loaded: {len(commands)}")
        print("─" * 42)
        if not shutil.which("ffmpeg"):
            print("  ⚠️  ffmpeg nahi mila → .m24 voice chat (vplay/vsave) kaam nahi karega")
            print("     ubuntu: sudo apt install ffmpeg   ·   termux: pkg install ffmpeg")
            print("─" * 42)

        await load_subbots()

        while True:
            try:
                await bot.run_until_disconnected()
                break
            except (ConnectionError, OSError):
                print("⚠️ connection lost → reconnecting…")
                await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("\n🛑 stopped manually")
    except Exception as e:
        print(f"\n❌ startup error → {err_txt(e, 140)}")
    finally:
        try:
            if bot.is_connected():
                await bot.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

