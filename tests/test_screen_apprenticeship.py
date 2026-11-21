#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_screen_apprenticeship.py -- learning a phone task by being shown it.

A stand-in phone plays a music app with three screens: home (a Your Library
tab), the library (a Liked Songs row) and the playlist (a Play button).  None
of those words appear anywhere in aurora_screen_apprenticeship.py; she finds
them by reading the screen.

These pin:
  * a request whose app she can open but whose rest she has never done stays
    open, with nothing pressed;
  * when Sir shows her, each thing he names is found on the screen she sees,
    pressed by her, and watched until the screen changes, in the order he said;
  * a word he says beside a word that found its place comes to mean that
    place ("liked playlist" means the Liked Songs row);
  * the next time he asks, she does it herself, step by step;
  * when a step is no longer where it was, she stops there and the part she
    could not do is open again;
  * Sir's own presses while he shows her are kept as his steps;
  * on a whole-mind phone the skill is kept in screen_skills.json; on a
    paired phone it is not written there, it goes home as a request, and
    what home hands down is what she uses;
  * home keeps it and sends it down only when it changed;
  * a password box is never typed into, and an act on a screen that changed
    under her is not sent to a different place.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal import aurora_screen_apprenticeship as asa
from aurora_internal import aurora_store_ownership as gate
from aurora_internal.dual_strata import strata_link as sl

MUSIC = "com.example.music"


class FakePhone:
    """A small phone: screens of nodes, and presses that move between them."""

    def __init__(self, library_has_liked: bool = True) -> None:
        self.screen = "own"
        self.frame = 1
        self.library_has_liked = library_has_liked
        self.acts = []
        self.typed = {}

    # what is on each screen ---------------------------------------------
    def nodes(self):
        tabs = [
            {"text": "Home", "view_id": f"{MUSIC}:id/home_tab", "cls": "android.widget.TextView", "clickable": True},
            {"text": "Search", "view_id": f"{MUSIC}:id/search_tab", "cls": "android.widget.TextView", "clickable": True},
            {"text": "Your Library", "view_id": f"{MUSIC}:id/library_tab", "cls": "android.widget.TextView", "clickable": True},
        ]
        if self.screen == "own":
            return [{"text": "Aurora", "cls": "android.widget.TextView"},
                    {"text": "", "desc": "Message", "editable": True, "cls": "android.widget.EditText"}]
        if self.screen == "home":
            return [{"text": "Good evening", "cls": "android.widget.TextView"},
                    {"text": "Show all", "clickable": True, "cls": "android.widget.Button"},
                    {"text": "Show all", "clickable": True, "cls": "android.widget.Button"},
                    {"text": "Show all", "clickable": True, "cls": "android.widget.Button"},
                    {"text": "Show all", "clickable": True, "cls": "android.widget.Button"},
                    {"text": "Daily Mix 1", "clickable": True, "cls": "android.widget.TextView"}] + tabs
        if self.screen == "library":
            rows = [{"text": "Playlists", "clickable": True, "cls": "android.widget.Button"},
                    {"text": "Road Trip", "desc": "Playlist", "clickable": True, "cls": "android.view.ViewGroup"}]
            if self.library_has_liked:
                rows.insert(1, {"text": "Liked Songs", "desc": "250 songs", "clickable": True,
                                "cls": "android.view.ViewGroup"})
            return rows + tabs
        if self.screen == "liked":
            return [{"text": "Liked Songs", "cls": "android.widget.TextView"},
                    {"text": "", "desc": "Shuffle", "view_id": f"{MUSIC}:id/shuffle", "clickable": True,
                     "cls": "android.widget.ImageButton"},
                    {"text": "", "desc": "Play", "view_id": f"{MUSIC}:id/play_button", "clickable": True,
                     "cls": "android.widget.ImageButton"}] + tabs
        if self.screen == "playing":
            return [{"text": "Liked Songs", "cls": "android.widget.TextView"},
                    {"text": "", "desc": "Pause", "view_id": f"{MUSIC}:id/play_button", "clickable": True,
                     "cls": "android.widget.ImageButton"}] + tabs
        if self.screen == "login":
            return [{"text": "", "desc": "Password", "editable": True, "password": True,
                     "cls": "android.widget.EditText"},
                    {"text": "Log in", "clickable": True, "cls": "android.widget.Button"}]
        return []

    def package(self):
        return "org.aurora.app" if self.screen == "own" else MUSIC

    # hands ----------------------------------------------------------------
    def available(self):
        return True

    def read(self):
        nodes = [dict(n, i=i) for i, n in enumerate(self.nodes())]
        return asa.ScreenFrame.from_json({"ok": True, "frame": self.frame, "package": self.package(),
                                          "nodes": nodes, "screen": [1080, 2400]})

    def _go(self, screen):
        self.screen = screen
        self.frame += 1

    def act(self, frame, index, action, text=""):
        if frame.frame_id != self.frame:
            return {"ok": False, "error": "stale"}
        nodes = self.nodes()
        if index >= len(nodes):
            return {"ok": False, "error": "no such node"}
        node = nodes[index]
        self.acts.append((self.screen, node.get("text") or node.get("desc"), action))
        if action == "type":
            if node.get("password"):
                return {"ok": False, "error": "password"}
            self.typed[index] = text
            self.frame += 1
            return {"ok": True}
        vid = node.get("view_id", "")
        label = node.get("text") or node.get("desc")
        if vid.endswith("library_tab"):
            self._go("library")
        elif vid.endswith("home_tab"):
            self._go("home")
        elif label == "Liked Songs" and self.screen == "library":
            self._go("liked")
        elif vid.endswith("play_button") and self.screen == "liked":
            self._go("playing")
        return {"ok": True}

    def global_action(self, name):
        if name == "home":
            self._go("own")
        return {"ok": True}

    def bring_to_front(self, package):
        if package == MUSIC:
            self._go("home")
            return True
        return False

    def wait(self, seconds):
        return None


@pytest.fixture(autouse=True)
def _whole_mind():
    gate.disable_surface_only()
    yield
    gate.disable_surface_only()
    sl._CLIENT = None


def _shown(tmp_path, phone=None):
    phone = phone or FakePhone()
    app = asa.ScreenApprenticeship(tmp_path, phone, {})
    return app, phone


def _teach(app, phone):
    phone.screen = "home"
    out = app.take_request("Open Spotify and play my liked playlist",
                           launched_package=MUSIC, consumed_words=["open", "spotify"])
    assert out["state"] == "open"
    assert phone.acts == []                               # nothing pressed on a guess
    assert app.wants_to_hear()
    first = app.hear("let me show you")
    assert first["steps"] == 0 and first["watching"]      # "show all" is everywhere: it means no one place
    out = app.hear("once the app is open you select library then liked playlist. "
                   "Once that's open you hit the play button to play my liked playlist")
    return out


def test_an_unknown_request_stays_open_and_nothing_is_pressed(tmp_path):
    app, phone = _shown(tmp_path)
    phone.screen = "home"
    out = app.take_request("Open Spotify and play my liked playlist",
                           launched_package=MUSIC, consumed_words=["open", "spotify"])
    assert out["state"] == "open"
    assert set(out["unknown"]) >= {"play", "liked", "playlist"}
    assert phone.acts == []
    assert app.status()["watching"] is True


def test_being_shown_she_does_each_step_herself_in_order(tmp_path):
    app, phone = _shown(tmp_path)
    out = _teach(app, phone)
    assert out["finished"] is True
    assert [a[1] for a in phone.acts] == ["Your Library", "Liked Songs", "Play"]
    assert phone.screen == "playing"
    assert not app.wants_to_hear() or app.episode is None
    skill = app.skills[out["skill_id"]]
    assert skill.package == MUSIC
    assert [s.istate["DID"] for s in skill.steps] == ["DID", "DID", "DID"]
    assert all(s.istate["SAW"] == "SAW" for s in skill.steps)
    assert all(set(s.axes) == {"X", "T", "N", "B", "A"} for s in skill.steps)
    assert len(skill.instructions) == 2


def test_a_word_beside_the_found_word_comes_to_mean_that_place(tmp_path):
    app, phone = _shown(tmp_path)
    _teach(app, phone)
    # "playlist" was said beside "liked", which found the Liked Songs row.
    assert app.meaning.match("playlist", "songs") >= 0.5
    # What led into a press teaches what kind of act it was.
    assert app.meaning.act_lean(["select"]).get("tap", 0) > 0


def test_next_time_she_does_it_herself(tmp_path):
    app, phone = _shown(tmp_path)
    _teach(app, phone)
    phone.acts.clear()
    phone.screen = "own"
    out = app.take_request("Open Spotify and play my liked playlist",
                           launched_package=MUSIC, consumed_words=["open", "spotify"])
    assert out["state"] == "done", out
    assert [a[1] for a in phone.acts] == ["Your Library", "Liked Songs", "Play"]
    assert phone.screen == "playing"
    skill = app.skills[out["skill_id"]]
    assert skill.uses == 1 and skill.successes == 1


def test_she_remembers_across_a_restart_on_a_whole_mind_phone(tmp_path):
    app, phone = _shown(tmp_path)
    _teach(app, phone)
    saved = json.loads((tmp_path / asa.SKILLS_FILENAME).read_text())
    assert len(saved["skills"]) == 1
    again = asa.ScreenApprenticeship(tmp_path, FakePhone(), {})
    assert len(again.skills) == 1
    sk, cov = again.recall(["play", "liked", "playlist"], MUSIC)
    assert sk is not None and cov == pytest.approx(1.0)


def test_a_step_no_longer_where_it_was_stops_her_there_and_opens_again(tmp_path):
    app, phone = _shown(tmp_path)
    _teach(app, phone)
    moved = FakePhone(library_has_liked=False)
    app.hands = moved
    moved.screen = "own"
    out = app.take_request("play my liked playlist", launched_package=MUSIC)
    assert out["state"] == "stopped"
    assert out["reached"] == 1 and out["of"] == 3
    assert app.episode is not None and len(app.episode.steps) == 1     # the part that still held
    assert [a[1] for a in moved.acts] == ["Your Library"]


def test_his_own_presses_while_showing_are_kept_as_his_steps(tmp_path):
    app, phone = _shown(tmp_path)
    phone.screen = "home"
    app.take_request("Open Spotify and play my liked playlist",
                     launched_package=MUSIC, consumed_words=["open", "spotify"])
    app.observe_event({"event_type": "view_clicked", "package": MUSIC, "agent": "user",
                       "source_node": {"text": "Your Library", "view_id": f"{MUSIC}:id/library_tab",
                                       "cls": "android.widget.TextView"}})
    # Her own presses (agent "self") are not his.
    app.observe_event({"event_type": "view_clicked", "package": MUSIC, "agent": "self",
                       "source_node": {"text": "Home"}})
    phone._go("library")
    out = app.hear("see, I went to your library")
    assert out["steps"] >= 1
    sirs = [s for s in app.episode.steps if s.agent == "sir"]
    assert len(sirs) == 1 and sirs[0].target["text"] == "Your Library"


def test_the_same_turn_is_not_taken_twice(tmp_path):
    app, phone = _shown(tmp_path)
    phone.screen = "home"
    app.take_request("Open Spotify and play my liked playlist", launched_package=MUSIC,
                     consumed_words=["open", "spotify"])
    text = "select library"
    app.hear(text)
    assert app.take_request(text)["state"] == "heard_as_shown"


def test_password_boxes_are_never_typed_into(tmp_path):
    app, phone = _shown(tmp_path)
    phone.screen = "login"
    frame = phone.read()
    assert not any(g.node.password for g in asa.ground([(0, "password")], frame, app.meaning))
    assert app.act_on("type", "password", "hunter2")["ok"] is False
    assert phone.typed == {}


def test_a_stale_frame_is_not_acted_on_elsewhere(tmp_path):
    app, phone = _shown(tmp_path)
    phone.screen = "home"
    old = phone.read()
    phone._go("library")
    out = phone.act(old, 0, "tap")
    assert out == {"ok": False, "error": "stale"}


def test_on_a_paired_phone_skills_go_home_and_come_back_from_home(tmp_path, monkeypatch):
    surface = tmp_path / "phone"
    home = tmp_path / "home"
    surface.mkdir()
    home.mkdir()
    gate.enable_surface_only(surface)
    sent = []

    def fake_request_home(state_dir, kind, payload=None):
        assert kind in sl.HOME_REQUEST_KINDS
        sent.append({"kind": kind, "payload": dict(payload or {})})
        return {"ok": True, "queued": True}

    monkeypatch.setattr(sl, "request_home", fake_request_home)
    app = asa.ScreenApprenticeship(surface, FakePhone(), {})
    assert app.is_surface()
    out = _teach(app, app.hands)
    assert out["finished"]
    # Not written as her own store on the phone; held as present until home has it.
    assert not (surface / asa.SKILLS_FILENAME).exists()
    assert (surface / "strata_link" / asa.PENDING_FILENAME).exists()
    assert [s["kind"] for s in sent] == ["screen_skill"]

    # Home keeps it.
    gate.disable_surface_only()
    desk = asa.HomeScreenSkills(home)
    assert desk.take(sent[0]) == "learned"
    assert (home / asa.SKILLS_FILENAME).exists()

    # Home sends what she knows down once, and again only when it changed.
    class Box:
        def __init__(self):
            self.items = []

        def append(self, channel, kind, payload):
            self.items.append((channel, kind, payload))

    box, memo = Box(), {}
    assert asa.relay_down(home, box, memo) == 1
    assert asa.relay_down(home, box, memo) == 0
    channel, _, payload = box.items[0]
    assert channel == asa.DOWN_CHANNEL

    # The phone takes it; what home has is no longer pending.
    gate.enable_surface_only(surface)
    assert app.receive_from_home(payload) == "applied"
    pending = json.loads((surface / "strata_link" / asa.PENDING_FILENAME).read_text())
    assert pending["skills"] == {}
    assert len(app.skills) == 1

    # Using it on the phone is counted and sent home.
    app.hands.screen = "own"
    app.hands.acts.clear()
    used = app.take_request("play my liked playlist", launched_package=MUSIC)
    assert used["state"] == "done"
    assert sent[-1]["kind"] == "screen_skill_use"
    gate.disable_surface_only()
    assert desk.take(sent[-1]) == "counted"
    assert desk.take(sent[-1]) == "counted"        # once, however often it arrives
    sid = used["skill_id"]
    assert desk.skills[sid]["uses"] == 1


def test_the_downlink_channel_reaches_her(tmp_path):
    gate.enable_surface_only(tmp_path)
    app = asa.ScreenApprenticeship(tmp_path, FakePhone(), {})
    asa.install(app)
    try:
        assert sl.apply_downlink_record(tmp_path, {"channel": asa.DOWN_CHANNEL,
                                                   "payload": {"skills": {}, "meaning": {}}}) == "applied"
        assert (tmp_path / "strata_link" / asa.HOME_COPY_FILENAME).exists()
    finally:
        asa.install(None)


def test_no_app_or_button_names_in_the_module():
    src = Path(asa.__file__).read_text(encoding="utf-8").lower()
    code = "\n".join(line for line in src.splitlines()
                     if not line.strip().startswith("#"))
    body = code.split('"""', 2)[2]                    # past the module docstring
    for word in ("spotify", "liked songs", "your library", "play button"):
        assert word not in body


def test_her_directive_dispatch_holds_the_unknown_part_open_then_does_it(tmp_path, monkeypatch):
    import aurora
    from aurora_internal import tool_registry as tr

    phone = FakePhone()
    app = asa.ScreenApprenticeship(tmp_path, phone, {})
    systems = {"state_dir": str(tmp_path)}
    asa.install(app, systems)

    def fake_launch(name, package="", systems=None, **_):
        phone._go("home")
        return tr.ToolResult("mobile_launch_app", f"Launched {package}", True)

    monkeypatch.setattr(tr, "call", fake_launch)
    monkeypatch.setattr(tr, "_resolve_app_package", lambda e: MUSIC if str(e).lower() == "spotify" else None)
    try:
        text = "Open Spotify and play my liked playlist"
        parsed = {"entities": ["Open", "Spotify"]}
        # She opens it; the rest she does not know, so no reply is made here:
        # it is held open for her own reasoning.
        assert aurora._dispatch_user_directive(text, parsed, systems) is None
        assert systems["_phone_goal_open"]["package"] == MUSIC
        assert phone.acts == []
        app.hear("once the app is open you select library then liked playlist, "
                 "then you hit the play button")
        assert phone.screen == "playing"
        systems.pop("_phone_goal_open", None)
        phone.acts.clear()
        reply = aurora._dispatch_user_directive(text, parsed, systems)
        assert reply is not None and "Your Library" in reply and "Play" in reply
        assert [a[1] for a in phone.acts] == ["Your Library", "Liked Songs", "Play"]
        assert "_phone_goal_open" not in systems
    finally:
        asa.install(None, systems)
