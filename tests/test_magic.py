"""✨ `.magic` — self-contained tests (koi pytest nahi chahiye).

    python3 tests/test_magic.py

Ye test bot ko network se touch kiye bina chalata hai: ek fake Telethon
client + fake event dekar `_magic_run` / `cmd_magic` / `magic_outgoing`
verify karte hain. Repo ke baaki code ko chhedne ke liye nahi — sirf
`Nik_userbot.py` import hota hai (env dummy values ke saath, temp cwd me).

Covered:
  fonts     → 10 distinct, length-preserving (entities safe), formatting persist
  scroll    → fonts × rounds edits → restore original text → reactions clear
  gates     → command text / reply / media / long text / cooldown / max-live / flood-pause
  config    → on/off persist, clamp, stop cancels
  safety    → FloodWait → abort + pause, reactions unsupported → font-only
"""
import asyncio
import os
import sys
import tempfile
import types as pytypes
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# ── import se pehle: dummy config + temp cwd (data/ yahin banega) ──
_WORK = tempfile.mkdtemp(prefix="nikmagic-")
os.chdir(_WORK)
os.environ.update({
    "API_ID": "123456",
    "API_HASH": "0123456789abcdef0123456789abcdef",
    "OWNER_ID": "111",
    "SESSION": "",
    "SESSION_FILE": os.path.join(_WORK, "test"),
})

import telethon                       # noqa: E402
from telethon.errors import FloodWaitError, MessageNotModifiedError   # noqa: E402

import Nik_userbot as nik             # noqa: E402

OWNER = 111
MAX_FAST = 0.001


def _flood(secs=7):
    try:
        return FloodWaitError(None, secs)
    except Exception:                       # purane/naye constructor
        e = FloodWaitError.__new__(FloodWaitError)
        e.seconds = secs
        return e


class FakeMsg:
    def __init__(self, text="", mid=99, chat=-1001, sender=OWNER, entities=None,
                 media=None):
        self.id = mid
        self.chat_id = chat
        self.sender_id = sender
        self.raw_text = text
        self.entities = list(entities or [])
        self.message = SimpleNamespace(entities=self.entities, media=media,
                                       id=mid, chat_id=chat)
        self.edited = []
        self.out = True

    async def edit(self, text, **kw):
        self.edited.append(text)
        return self

    async def delete(self):
        return True

    async def get_reply_message(self):
        return None


class FakeClient:
    """bot(...) / client.edit_message — sab record, zero network"""

    def __init__(self, flood_at=None, react_fails=0, allowed=None,
                 react_error=None):
        self.edits = []
        self.reacts = []
        self.requests = []
        self.entities_seen = []
        self.flood_at = flood_at
        self.react_fails = react_fails
        self.react_error = react_error
        self.allowed = allowed
        self._n = 0

    async def edit_message(self, chat, mid, text, entities=None):
        self._n += 1
        self.edits.append(text)
        self.entities_seen.append(entities)
        if self.flood_at == self._n:
            raise _flood(7)
        if self.flood_at == -self._n:
            raise MessageNotModifiedError(None)
        return True

    async def __call__(self, request):
        name = type(request).__name__
        self.requests.append(request)
        if name == "SendReactionRequest":
            react = list(getattr(request, "reaction", None) or [])
            self.reacts.append([getattr(r, "emoticon", None) for r in react])
            if self.react_fails > 0:
                self.react_fails -= 1
                raise RuntimeError(self.react_error or "REACTION_INVALID")
        elif name == "GetAvailableReactionsRequest":
            if self.allowed is None:
                raise RuntimeError("no peer")
            return SimpleNamespace(
                available_reactions=[
                    SimpleNamespace(reaction=SimpleNamespace(emoticon=e, emoji_id=None))
                    for e in self.allowed
                ])
        return None


def fresh(**cfg):
    """MAGIC state + registries reset, config defaults fast"""
    base = dict(nik.MAGIC_DEFAULTS, speed=MAX_FAST, rdelay=MAX_FAST, cooldown=0.0)
    base.update(cfg)
    nik.MAGIC.clear()
    nik.MAGIC.update(base)
    nik.MAGIC_TASKS.clear()
    nik.MAGIC_PAUSE["until"] = 0.0
    nik._MAGIC_LAST_FIRE[0] = 0.0
    nik._MAGIC_ALLOWED.clear()
    nik.COMMAND_COOLDOWN.clear()      # eor ka 0.3 s wait tests me na aaye


# ════════════════════════ the tests ════════════════════════════
def test_fonts_distinct_and_length_preserving():
    assert len(nik.MAGIC_FONTS) == 10, "10 font chahiye the"
    src = "Pyar wala 123 attack 🔥 — ok"
    outs = [fn(src) for _label, fn in nik.MAGIC_FONTS]
    assert len(set(outs)) == 10, f"fonts distinct nahi: {len(set(outs))}"
    for label, o in zip([n for n, _ in nik.MAGIC_FONTS], outs):
        assert len(o) == len(src), f"{label}: length badh gaya (entities toot jaate)"
        assert "🔥" in o, f"{label}: emoji gaayab"
    assert src not in outs, "koi font original jaisa hi to nahi?"


def test_scroll_full_cycle():
    fresh()
    cli = FakeClient()
    orig = "hello bhai"

    async def run():
        await nik._magic_run(-1001, 42, orig, "k", cli)

    asyncio.run(run())
    fonts = int(nik.MAGIC["fonts"])
    rounds = int(nik.MAGIC["rounds"])
    # +1 = restore edit
    assert len(cli.edits) == fonts * rounds + 1, \
        f"edits {len(cli.edits)} ≠ {fonts}×{rounds}+restore"
    assert cli.edits[-1] == orig, "last edit original text nahi (restore fail)"
    assert orig not in cli.edits[:-1], "beeche me original text nahi hona chahiye"
    emos = [e for batch in cli.reacts[:-1] for e in batch]     # last = clear
    assert len(set(emos)) >= 15, f"kam reaction scroll: {len(set(emos))}"
    assert len(emos) <= 20 * 40, "reaction scroll ka cap toota"
    assert cli.reacts[-1] == [None] or cli.reacts[-1] == [], \
        f"reactions clear nahi hue: {cli.reacts[-1]}"
    assert not nik.MAGIC_TASKS, "task registry saaf nahi hui"


def test_entities_persist_through_scroll():
    fresh(rounds=1)
    ents = [telethon.types.MessageEntityBold(offset=0, length=4)]
    cli = FakeClient()

    async def run():
        await nik._magic_run(-1001, 7, "bold text here", "k2", cli, ents)

    asyncio.run(run())
    assert cli.entities_seen and all(e == ents for e in cli.entities_seen), \
        "har edit pe entities pass nahi hue"


def test_font_only_mode_when_reacts_zero():
    fresh(reacts=0, rounds=1)
    cli = FakeClient()

    async def run():
        await nik._magic_run(-1001, 5, "sirf font", "k3", cli)

    asyncio.run(run())
    assert not cli.reacts, "reacts 0 pe bhi reaction gaya (clear tak nahi bhejni)"
    assert len(cli.edits) == int(nik.MAGIC["fonts"]) + 1, "font scroll count galat"


def test_flood_aborts_and_pauses_everything():
    fresh(rounds=20)
    cli = FakeClient(flood_at=3)                       # 3rd edit pe flood

    async def run():
        await nik._magic_run(-1001, 8, "flood test", "k4", cli)
        left = nik._magic_left()
        await nik.magic_outgoing(_out_event("auto message while paused"))
        await asyncio.sleep(0)
        return left

    left = asyncio.run(run())
    assert len(cli.edits) == 4, f"flood ke baad bhi edits: {cli.edits}"
    assert cli.edits[-1] == "flood test", "paused/aborted msg restore nahi hua"
    assert left >= 5, f"pause set nahi hua: {left}"
    assert not nik.MAGIC_TASKS, "paused fire bhi ho gaya (gate fail)"


def test_reactions_unsupported_keeps_font_scroll():
    fresh(rounds=1)
    cli = FakeClient(react_fails=99, react_error="REACTION_INVALID")

    async def run():
        await nik._magic_run(-1001, 9, "no reactions here", "k5", cli)

    asyncio.run(run())
    assert len(cli.edits) == int(nik.MAGIC["fonts"]) + 1, "font scroll rukk gaya"
    assert len(cli.reacts) <= 4, f"failed reactions pe retry zyada: {len(cli.reacts)}"


def test_allowed_reactions_come_from_chat_and_are_cached():
    fresh(rounds=1, reacts=5)
    allowed = ["👍", "❤️", "🔥", "👍", "✨", "🎉", "💩"]
    cli = FakeClient(allowed=allowed)

    async def run():
        first = await nik._magic_react_list(cli)
        cli.allowed = ["SHOULD NOT BE READ"]           # cache use honi chahiye
        second = await nik._magic_react_list(cli)
        return first, second

    first, second = asyncio.run(run())
    assert first == ["👍", "❤️", "🔥", "✨", "🎉"], f"allowed list galat: {first}"
    assert first == second, "cache nahi laga"
    # API fail → curated fallback, 20 tak
    cli2 = FakeClient(allowed=None)
    fresh(reacts=20)

    async def run2():
        return await nik._magic_react_list(cli2)

    fb = asyncio.run(run2())
    assert len(fb) == 20 and fb == nik.MAGIC_EMOJIS[:20], f"fallback galat: {fb}"


def test_cmd_toggle_persists_state():
    fresh(on=False)

    async def run():
        ev = _cmd_event(".magic")
        await nik.cmd_magic(ev, "")                    # no arg, no reply → toggle
        assert nik.MAGIC["on"] is True
        assert os.path.isfile(os.path.join(nik.DATA_DIR, nik.F_MAGIC))
        saved = nik.load_json(nik.F_MAGIC, {})
        assert saved["on"] is True and set(saved) == set(nik.MAGIC_DEFAULTS)
        await nik.cmd_magic(_cmd_event(".magic"), "")  # wapas off
        return nik.MAGIC["on"], saved

    off, saved = asyncio.run(run())
    assert off is False, "dusri baar toggle fail"
    _reload = pytypes.ModuleType("_")                  # clamp + load round-trip
    nik.save_json(nik.F_MAGIC, {"on": True, "speed": 999, "fonts": 1, "rounds": -5})
    nik.MAGIC.update(dict(nik.MAGIC_DEFAULTS))
    nik._magic_load()
    assert nik.MAGIC["on"] is True and nik.MAGIC["speed"] == 5.0
    assert nik.MAGIC["fonts"] == 2 and nik.MAGIC["rounds"] == 0, dict(nik.MAGIC)


def test_cmd_numeric_config_and_clamp():
    fresh()

    async def run():
        out = {}
        await nik.cmd_magic(_cmd_event(".magic speed 0.3"), "speed 0.3")
        out["speed"] = nik.MAGIC["speed"]
        await nik.cmd_magic(_cmd_event(".magic fonts 99"), "fonts 99")
        out["fonts"] = nik.MAGIC["fonts"]
        await nik.cmd_magic(_cmd_event(".magic rounds 0"), "rounds 0")
        out["rounds"] = nik.MAGIC["rounds"]
        await nik.cmd_magic(_cmd_event(".magic reacts abc"), "reacts abc")
        out["reacts"] = nik.MAGIC["reacts"]
        await nik.cmd_magic(_cmd_event(".magic big"), "big")
        out["big"] = nik.MAGIC["big"]
        await nik.cmd_magic(_cmd_event(".magic speed"), "speed")
        return out

    out = asyncio.run(run())
    assert out["speed"] == 0.4 and out["fonts"] == 10, out
    assert out["rounds"] == 0, "0 = infinite mode set nahi hua"
    assert out["reacts"] == int(nik.MAGIC_DEFAULTS["reacts"]), "galat value ne config bigaad di"
    assert out["big"] is True, "bare `.magic big` = on hona chahiye"


def test_cmd_stop_cancels_infinite_scroll():
    fresh(on=True, rounds=0)                  # infinite

    async def run():
        cli = FakeClient()
        ev = _cmd_event(".magic")
        task = asyncio.create_task(nik._magic_run(-1001, 11, "infinite run", "k6", cli))
        nik.MAGIC_TASKS["k6"] = task
        await asyncio.sleep(0.02)
        assert len(cli.edits) > 0
        await nik.cmd_magic(ev, "stop")
        await asyncio.gather(task, return_exceptions=True)
        return len(cli.edits), cli.edits[-1], len(nik.MAGIC_TASKS)

    n, last, live = asyncio.run(run())
    assert last == "infinite run", "stop pe text restore nahi hua"
    assert live == 0, "task registry me mara hua task pada hai"
    assert n > 3


def test_cmd_status_and_guide_render():
    fresh(on=True, reacts=20)

    async def run():
        ev = _cmd_event(".magic status")
        await nik.cmd_magic(ev, "status")
        bad = _cmd_event(".magic nahi")
        await nik.cmd_magic(bad, "nahi")
        return "".join(ev.sent()), "".join(bad.sent()), nik.guide_magic()

    card, bad, guide = asyncio.run(run())
    card_txt, guide_txt = nik._plainify(card).lower(), nik._plainify(guide).lower()
    assert "magic" in card_txt, f"status card me magic nahi: {card_txt}"
    for frag in ("state", "fonts", "rounds", "reactions", "cooldown", "live now"):
        assert frag in card_txt, f"status card me {frag} nahi: {card_txt}"
    assert "𝟸𝟶" in card, "reactions count mono me card me nahi"
    assert "unknown" not in card_txt, "status card error dikha raha hai"
    for frag in ("nahi", "on|off|stop|status"):
        assert frag in nik._plainify(bad).lower(), f"galat subcmd pe guide nahi: {bad}"
    assert all(n.lower() in guide_txt for n, _f in nik.MAGIC_FONTS), \
        "guide me saare 10 font naam nahi"
    for frag in (".magic stop", ".magic speed 0.6", ".magic rounds 5",
                 ".magic reacts 20", ".magic big on", ".magic on", ".magic off"):
        assert nik.mono(frag) in guide, f"guide me {frag!r} nahi"


def test_magic_registered_in_menu_and_registry():
    assert "magic" in nik.commands, "command registry me nahi"
    assert nik.aliases.get("mx") == "magic", "alias .mx nahi chlega"
    found = [c for _t, items in nik._MENU for c, _d in items if c == "magic"]
    assert found == ["magic"], "menu me row nahi → .m13/.fullmenu me gayab"
    assert nik.CAT_OF_CMD.get("magic"), "category menu (.mN) map nahi bana"
    assert "magic" in nik.GUIDES, ".help magic guide nahi"


def test_auto_watcher_gates():
    def fire(text, is_reply=False, media=None, on=True):
        fresh(on=on)
        cli = FakeClient()
        ev = _out_event(text, is_reply=is_reply, media=media)
        ev.client = cli

        async def run():
            await nik.magic_outgoing(ev)
            await asyncio.sleep(0)
            return dict(nik.MAGIC_TASKS)

        return asyncio.run(run())

    assert len(fire("hello kaise ho")) == 1, "normal msg pe animation nahi hui"
    assert fire(".music kesariya") == {}, "command message animate ho gaya"
    assert fire("reply wala msg", is_reply=True) == {}, "reply animate ho gaya"
    assert fire("photo ke saath", media=object()) == {}, "media animate ho gaya"
    assert fire("x" * (nik.MAGIC_MAX_TEXT + 10)) == {}, "lamba msg animate ho gaya"
    assert fire("hi", on=False) == {}, "magic OFF the, phir bhi chala"
    assert len(fire("🎉 sirf emoji wala msg")) == 1, "emoji wala msg animate hona chahiye"
    assert fire("music kesariya") == {}, \
        "command-jaisa msg (bina prefix mode) animate ho gaya"
    assert fire("   ") == {}, "whitespace-only msg animate ho gaya"


def test_auto_watcher_cooldown_and_max_live_and_pause():
    fresh(on=True, cooldown=30.0)
    cli = FakeClient()
    e1, e2 = _out_event("pehla msg"), _out_event("dusra msg")
    for e in (e1, e2):
        e.client = cli

    async def run():
        await nik.magic_outgoing(e1)
        await nik.magic_outgoing(e2)              # cooldown → skip
        await asyncio.sleep(0)
        return len(nik.MAGIC_TASKS)

    assert asyncio.run(run()) == 1, "cooldown gate fail"

    fresh(on=True)
    evs = [_out_event(f"msg {i}") for i in range(6)]
    for e in evs:
        e.client = cli

    async def run2():
        for e in evs:
            await nik.magic_outgoing(e)
        await asyncio.sleep(0)
        return _magic_live_now(), [t for t in nik.MAGIC_TASKS.values()]

    def _magic_live_now():
        return len(nik.MAGIC_TASKS)

    live, tasks = asyncio.run(run2())
    assert live == nik.MAGIC_MAX_LIVE, f"max-live gate fail: {live}"
    for t in tasks:
        t.cancel()


def test_one_shot_requires_own_message():
    """reply karke .magic → sirf APNE text message pe, warna clear reason"""

    def go(rep):
        fresh()
        ev = _cmd_event(".magic")
        cli = FakeClient()
        ev.client = cli

        async def inner():
            return rep

        ev.get_reply_message = inner

        async def run():
            await nik.cmd_magic(ev, "")
            await asyncio.sleep(0.05)
            return cli

        return asyncio.run(run())

    cli = go(FakeMsg("mera msg", mid=21))
    assert cli.edits and cli.edits[-1] == "mera msg", "apne msg pe one-shot nahi chala"
    assert cli.reacts, "one-shot pe reaction scroll nahi hui"

    for rep, why in ((FakeMsg("tera msg", mid=22, sender=222), "doosre ke msg pe chala gaya"),
                     (FakeMsg("", mid=23), "bina text wale msg pe chala gaya"),
                     (FakeMsg("x" * (nik.MAGIC_MAX_TEXT + 1), mid=24), "bohot lamba msg animate hua")):
        c = go(rep)
        assert not c.edits and not c.reacts, why


def test_one_shot_edits_reply_message_and_restores():
    """one-shot scroll reply message ko hi edit kare, command ko nahi"""
    fresh(rounds=1)
    mine = FakeMsg("scroll me bhai", mid=31)
    ev = _cmd_event(".magic")
    cli = FakeClient()
    ev.client = cli

    async def inner():
        return mine

    ev.get_reply_message = inner

    async def run():
        await nik.cmd_magic(ev, "")
        await asyncio.sleep(0.05)
        return cli.edits, mine.edited

    edits, msg_self_edits = asyncio.run(run())
    assert len(edits) == int(nik.MAGIC["fonts"]) + 1, f"scroll count: {len(edits)}"
    assert edits[-1] == "scroll me bhai", f"restore nahi hua: {edits[-2:]}"
    assert edits[0] != "scroll me bhai", "pehla edit font me nahi"
    assert any("magic chal raha" in nik._plainify(x).lower() for x in ev.sent()), \
        "one-shot ka confirmation card nahi bheja"


# ════════════════════════ fake events ════════════════════════
_EID = [500]


def _out_event(text, is_reply=False, media=None, sender=OWNER):
    _EID[0] += 1
    ev = FakeEvent(text=text, sender=sender, is_reply=is_reply, mid=_EID[0])
    ev.message = SimpleNamespace(entities=[], media=media, id=ev.id,
                                 chat_id=ev.chat_id, raw_text=text,
                                 sender_id=sender, out=True)
    return ev


class FakeEvent:
    """Telethon NewMessage event ka minimal shape (jo code use karta hai)"""

    def __init__(self, text="", sender=OWNER, chat=-1001, mid=42,
                 is_reply=False, out=False):
        self.raw_text = text
        self.message = SimpleNamespace(entities=[], media=None, id=mid,
                                       chat_id=chat, raw_text=text,
                                       sender_id=sender, out=out)
        self.sender_id = sender
        self.chat_id = chat
        self.id = mid
        self.is_reply = is_reply
        self.out = out
        self.client = FakeClient()
        self.edited = []
        self.replied = []

    async def get_reply_message(self):
        return None

    async def edit(self, text, **kw):
        self.edited.append(text)
        return self

    async def reply(self, text, **kw):
        self.replied.append(text)
        return self

    async def delete(self):
        return True

    def sent(self):
        return self.edited + self.replied


def _cmd_event(text):
    ev = FakeEvent(text=text, out=True)
    ev.sender_id = OWNER
    return ev


# rich card path + network-touching helpers ko bypass karo
async def _no_rich(*a, **kw):
    return None


nik._ui_render = _no_rich
nik._ui_rich_ok = lambda: False

# ════════════════════════ runner ════════════════════════════
if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    fails = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except Exception as e:
            fails += 1
            import traceback
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            if os.environ.get("VERBOSE"):
                traceback.print_exc()
    print(f"\n{len(tests) - fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
