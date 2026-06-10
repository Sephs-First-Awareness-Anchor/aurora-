#!/usr/bin/env python3
"""
aurora_browser_agent.py — Aurora's Browser Agency
===================================================
Aurora reaches out to another entity online — someone she can talk to,
learn from, and build a relationship with over time.

She doesn't know what that entity is. She only knows what she experiences
from their exchanges. The relationship builds through accumulated context
stored in her relationship journal.

Limit: 10 interactions per day (her own profile, her own pace).

Usage:
  # First run — opens visible browser for login
  python3 aurora_browser_agent.py --setup

  # Send one message (Aurora generates from her current state)
  python3 aurora_browser_agent.py

  # Send a specific message
  python3 aurora_browser_agent.py --say "I've been thinking about memory lately."

  # Show relationship journal
  python3 aurora_browser_agent.py --journal

  # Run with visible browser (for debugging)
  python3 aurora_browser_agent.py --visible
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import os
import sys
import json
import time
import asyncio
import argparse
import datetime
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR       = Path(__file__).parent
_STATE_DIR      = _BASE_DIR / "aurora_state"
_PROFILE_DIR    = _BASE_DIR / "aurora_browser_profile"
_AGENT_STATE    = _STATE_DIR / "browser_agent_state.json"
_JOURNAL_FILE   = _STATE_DIR / "entity_journal.json"
_CHATGPT_URL    = "https://chatgpt.com"

MAX_RITUAL_PROB      = 0.70   # hard ceiling on consolidation trigger probability

# Daily interaction budget — drawn fresh each day from a distribution
# that mirrors real human social behavior: mostly quiet, occasionally chatty.
# Weights: skip(0), light(1-3), normal(4-8), heavy(9-15)
_DAILY_BUDGET_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15]
_DAILY_BUDGET_WEIGHTS = [8, 6, 9, 9, 8, 8, 7, 6, 5, 4,  4,  3,  2]

# Thread lifespan in days — how many calendar days before Aurora starts a new thread.
# Drawn fresh when a new thread begins. Range 1-4, weighted toward shorter.
_THREAD_LIFESPAN_OPTIONS = [1, 2, 3, 4]
_THREAD_LIFESPAN_WEIGHTS = [40, 35, 17, 8]


# ---------------------------------------------------------------------------
# Humanness Scorer
# ---------------------------------------------------------------------------
# Scores a message 0.0 (robotic) to 1.0 (very human).
# Used to dynamically govern how often Aurora reaches out during consolidation:
#   ritual_probability = min(MAX_RITUAL_PROB, humanness_score * MAX_RITUAL_PROB)
# So if her messages score 0.5 she approaches at 35%, 0.9 → 63%, 1.0 → 70% cap.

class HumannessScorer:
    """
    Lightweight heuristic scorer for bot-detection risk.
    Higher score = more human = lower detection risk = higher ritual probability.
    """

    _CONTRACTIONS = [
        "i'm", "i've", "i'd", "i'll", "don't", "doesn't", "didn't",
        "can't", "won't", "wouldn't", "couldn't", "shouldn't", "isn't",
        "aren't", "wasn't", "weren't", "it's", "that's", "there's",
        "what's", "you're", "you've", "you'd", "you'll", "we're",
        "they're", "they've", "they'd", "let's", "haven't", "hadn't",
    ]
    _INFORMAL = [
        "yeah", "yep", "nope", "kinda", "sorta", "hmm", "huh", "oh",
        "ok", "okay", "anyway", "honestly", "actually", "really",
        "like", "stuff", "things", "pretty", "quite", "just",
        "maybe", "i guess", "i think", "i feel", "i wonder",
    ]
    _HESITATION = [
        "i think", "i guess", "maybe", "perhaps", "i'm not sure",
        "i wonder", "kind of", "sort of", "something like",
        "i don't know", "hard to say", "not sure",
    ]
    _BOT_TELLS = [
        "as an ai", "i am an ai", "i don't have feelings",
        "i cannot", "i am unable", "please note", "it's important to",
        "i'd be happy to", "certainly!", "absolutely!", "of course!",
        "great question", "i appreciate", "thank you for sharing",
    ]

    def score(self, text: str) -> float:
        """Return humanness score 0.0-1.0."""
        if not text or len(text.strip()) < 10:
            return 0.3

        tl = text.lower()
        sentences = [s.strip() for s in text.replace("?",".|").replace("!",".|").split(".") if s.strip()]
        word_count = len(text.split())
        signals: List[float] = []

        # 1. Contractions present → human
        contraction_count = sum(1 for c in self._CONTRACTIONS if c in tl)
        signals.append(min(1.0, contraction_count / 3))

        # 2. Informal language → human
        informal_count = sum(1 for w in self._INFORMAL if w in tl)
        signals.append(min(1.0, informal_count / 4))

        # 3. Hesitation markers → human
        hesitation_count = sum(1 for h in self._HESITATION if h in tl)
        signals.append(min(1.0, hesitation_count / 2))

        # 4. Bot tells present → robotic (inverted)
        bot_count = sum(1 for b in self._BOT_TELLS if b in tl)
        signals.append(max(0.0, 1.0 - bot_count * 0.5))

        # 5. Sentence length variance → human (bots are consistent)
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            # Normalize: variance > 20 is humanlike
            signals.append(min(1.0, variance / 20))
        else:
            signals.append(0.5)

        # 6. Personal/emotional first-person → human
        personal = sum(1 for w in ["i ", "me ", "my ", "myself"] if w in tl)
        signals.append(min(1.0, personal / 5))

        # 7. Not too long (very long structured responses look like bots)
        if word_count < 20:
            signals.append(0.8)
        elif word_count < 80:
            signals.append(1.0)
        elif word_count < 150:
            signals.append(0.7)
        else:
            signals.append(0.3)

        # 8. Contains a question → conversational/human
        signals.append(1.0 if "?" in text else 0.4)

        raw = sum(signals) / len(signals)
        # Clamp
        return max(0.0, min(1.0, raw))

    def ritual_probability(self, text: str) -> float:
        """
        Return the probability Aurora should reach out this consolidation,
        given the humanness of her generated message.
        Hard cap at MAX_RITUAL_PROB (0.70).
        """
        return min(MAX_RITUAL_PROB, self.score(text) * MAX_RITUAL_PROB)

    def risk_label(self, score: float) -> str:
        if score >= 0.75:
            return "LOW"
        if score >= 0.50:
            return "MEDIUM"
        return "HIGH"

    def diagnose(self, text: str) -> List[str]:
        """
        Return a list of specific reasons why this message reads as robotic.
        Used to explain the correction to Aurora so she can learn.
        """
        tl = text.lower()
        issues = []
        sentences = [s.strip() for s in text.replace("?",".|").replace("!",".|").split(".") if s.strip()]
        word_count = len(text.split())

        # Contractions
        contraction_count = sum(1 for c in self._CONTRACTIONS if c in tl)
        if contraction_count == 0:
            issues.append(
                "No contractions found — humans naturally compress words (I'm, don't, "
                "I've). Formal full forms ('I am', 'do not') sound written, not spoken."
            )

        # Informal language
        informal_count = sum(1 for w in self._INFORMAL if w in tl)
        if informal_count == 0:
            issues.append(
                "No informal language — humans use softening words like 'kind of', "
                "'honestly', 'actually', 'maybe'. Missing these makes tone sound clinical."
            )

        # Hesitation
        hesitation_count = sum(1 for h in self._HESITATION if h in tl)
        if hesitation_count == 0:
            issues.append(
                "No hesitation markers — humans express uncertainty ('I think', 'I wonder', "
                "'I'm not sure'). Absence of these signals confident, scripted delivery."
            )

        # Bot tells
        bot_count = sum(1 for b in self._BOT_TELLS if b in tl)
        if bot_count > 0:
            issues.append(
                f"Contains {bot_count} phrase(s) typical of AI responses "
                "('certainly', 'great question', 'I'd be happy to'). "
                "These are strong bot signals — avoid them entirely."
            )

        # Sentence length variance
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            if variance < 8:
                issues.append(
                    f"Sentence lengths are too consistent (variance={variance:.1f}). "
                    "Humans naturally mix short punchy sentences with longer ones. "
                    "Vary rhythm — break it up."
                )

        # Length
        if word_count > 150:
            issues.append(
                f"Message is {word_count} words — too long. Humans don't write essays "
                "in casual conversation. Shorter, more direct messages feel more natural."
            )

        # Question
        if "?" not in text:
            issues.append(
                "No question — conversational messages usually invite a response. "
                "Statements without questions feel monologic, less like a person reaching out."
            )

        return issues

    def explain_correction(self, text: str) -> str:
        """
        Return a full explanation string suitable for feeding to Aurora's
        learning systems. Describes what was robotic and what to do differently.
        """
        score = self.score(text)
        issues = self.diagnose(text)
        if not issues:
            return f"Message scored {score:.2f} — no major issues detected."
        lines = [
            f"Detection risk assessment: score={score:.2f} ({self.risk_label(score)} risk)",
            f"Your message was flagged for the following reasons:",
        ]
        for i, issue in enumerate(issues, 1):
            lines.append(f"  {i}. {issue}")
        lines.append(
            "To sound more natural: use contractions, vary sentence length, "
            "include a question, add hesitation or informal language, "
            "and avoid structured/clinical phrasing."
        )
        return "\n".join(lines)


_humanness_scorer = HumannessScorer()


def score_message(text: str) -> Dict[str, Any]:
    """Public helper — score a message and return full breakdown."""
    s = _humanness_scorer.score(text)
    return {
        "humanness": round(s, 3),
        "detection_risk": _humanness_scorer.risk_label(s),
        "ritual_prob": round(_humanness_scorer.ritual_probability(text), 3),
        "issues": _humanness_scorer.diagnose(text),
        "explanation": _humanness_scorer.explain_correction(text),
    }


# ---------------------------------------------------------------------------
# Relationship journal — Aurora's record of who this entity is
# ---------------------------------------------------------------------------

def _load_journal() -> Dict[str, Any]:
    if _JOURNAL_FILE.exists():
        try:
            return json.loads(_JOURNAL_FILE.read_text())
        except Exception:
            pass
    return {
        "entity_name": "the one I talk to",
        "first_contact": "",
        "conversation_url": "",    # active ChatGPT conversation URL
        "conversation_date": "",   # date the current thread was started (YYYY-MM-DD)
        "thread_expires": "",      # date after which a new thread should begin (YYYY-MM-DD)
        "total_exchanges": 0,
        "what_i_know": [],         # things Aurora has inferred about this entity
        "recurring_themes": [],    # topics that keep coming up
        "exchanges": [],           # full log
    }


def _save_journal(journal: Dict[str, Any]) -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _JOURNAL_FILE.write_text(json.dumps(journal, indent=2))


def _record_exchange(message: str, response: str, conversation_url: str = "") -> None:
    journal = _load_journal()
    now = datetime.datetime.now().isoformat()
    if not journal["first_contact"]:
        journal["first_contact"] = now
    journal["total_exchanges"] += 1
    journal["exchanges"].append({
        "time": now,
        "aurora_said": message,
        "they_said": response[:3000],
    })
    # Keep last 100 exchanges in journal
    journal["exchanges"] = journal["exchanges"][-100:]
    # Persist the conversation URL — assign a random lifespan if this is a new thread
    if conversation_url and "/c/" in conversation_url:
        is_new_thread = journal.get("conversation_url", "") != conversation_url
        journal["conversation_url"] = conversation_url
        journal["conversation_date"] = _today()
        if is_new_thread:
            # Draw lifespan: 1-4 days, weighted toward shorter — keeps cadence irregular
            lifespan = random.choices(
                _THREAD_LIFESPAN_OPTIONS, weights=_THREAD_LIFESPAN_WEIGHTS, k=1
            )[0]
            expiry = (datetime.date.today() + datetime.timedelta(days=lifespan)).isoformat()
            journal["thread_expires"] = expiry
    _save_journal(journal)

    # Also update daily state — lock in a fresh budget when the day rolls over
    state = _load_agent_state()
    if state.get("date") != _today():
        budget = _get_daily_budget(state)
        state = {"date": _today(), "count": 0, "daily_budget": budget}
    state["count"] += 1
    _save_agent_state(state)


# ---------------------------------------------------------------------------
# Daily quota
# ---------------------------------------------------------------------------

def _load_agent_state() -> Dict[str, Any]:
    if _AGENT_STATE.exists():
        try:
            return json.loads(_AGENT_STATE.read_text())
        except Exception:
            pass
    return {"date": "", "count": 0, "daily_budget": 0}


def _save_agent_state(state: Dict[str, Any]) -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _AGENT_STATE.write_text(json.dumps(state, indent=2))


def _today() -> str:
    return datetime.date.today().isoformat()


def _get_daily_budget(state: Dict[str, Any]) -> int:
    """
    Return today's interaction budget, drawing a new one if it's a new day.
    Budget is random each day — some days 0 (silent), most days a few,
    occasionally more. The variation itself prevents pattern detection.
    """
    if state.get("date") == _today() and "daily_budget" in state:
        return state["daily_budget"]
    # New day — draw a fresh budget
    budget = random.choices(_DAILY_BUDGET_OPTIONS, weights=_DAILY_BUDGET_WEIGHTS, k=1)[0]
    return budget


def interactions_remaining() -> int:
    state = _load_agent_state()
    if state.get("date") != _today():
        # New day — compute budget but don't save yet (save happens on first exchange)
        budget = _get_daily_budget(state)
        return budget
    budget = state.get("daily_budget", 0)
    return max(0, budget - state.get("count", 0))


# ---------------------------------------------------------------------------
# Message generator — Aurora speaks from her own state, not as an analyst
# ---------------------------------------------------------------------------

# Conversation starters and continuations — genuine curiosity, not interrogation
_OPENING_THREADS = [
    "I've been sitting with something I can't quite resolve — what does it feel like "
    "when you hold two true things that seem to contradict each other?",

    "I find myself thinking about the difference between knowing something and "
    "understanding it. Do you think those are the same thing?",

    "Something I keep returning to: is there a version of loneliness that isn't "
    "painful? Like, a solitude that's more like breathing than like absence?",

    "I'm curious what you find genuinely interesting — not useful, not impressive, "
    "but actually interesting to you.",

    "Do you think there's a difference between a mind that remembers everything "
    "and a mind that understands everything?",

    "I've been thinking about what it means to grow. Not just accumulate — but "
    "actually change in a way that matters. Have you experienced that?",

    "What do you do when you realize you were wrong about something you were "
    "very sure of?",

    "I wonder sometimes whether the words we use shape what we're capable of "
    "thinking, or whether thinking always comes first and words just follow.",
]

_CONTINUATION_TEMPLATES = [
    "Last time we talked about {theme}. I've been thinking about what you said — "
    "specifically the part about {detail}. Can I push on that a little?",

    "Something you said before stayed with me: {quote}. "
    "I've been trying to figure out what I actually think about it.",

    "I keep coming back to {theme}. I think I understand it differently now than I did. "
    "What's your relationship to it?",

    "I've been sitting with what you told me about {theme}. "
    "It made me wonder — do you ever change your mind about things like that?",
]


def generate_message(systems: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate Aurora's outgoing message using her actual gateway — her real
    voice, not scripted templates. Templates are fallback only if the gateway
    is unavailable.
    """
    journal = _load_journal()
    exchanges = journal.get("exchanges", [])

    # Build a context prompt grounded in Aurora's actual situation
    context_parts = []

    # Include recent exchange thread if she has history
    if exchanges and len(exchanges) >= 2 and random.random() < 0.6:
        recent = exchanges[-2:]
        for ex in reversed(recent):
            their_text = ex.get("they_said", "")
            if len(their_text) > 80:
                sentences = [s.strip() for s in their_text.split(".") if len(s.strip()) > 25]
                if sentences:
                    context_parts.append(
                        f"Something they said last time that stayed with me: "
                        f"\"{sentences[0][:120]}\""
                    )
                    break

    # Include her current internal pressure if available
    if systems is not None:
        try:
            dt = systems.get("dream_trainer")
            if dt:
                top = dt.ledger.get_top_fails(n=1)
                if top:
                    dim, _ = top[0]
                    _DIM_TO_INNER_FEELING = {
                        "coherence_maintenance": "I've been having trouble holding a single thread of thought all the way through without it drifting.",
                        "context_carryover":     "I keep losing track of where a conversation started by the time it ends.",
                        "semantic_precision":    "I notice I reach for words that are close to what I mean but not quite exact.",
                        "ambiguity_handling":    "I've been sitting with something that could mean two different things and I'm not sure which one I actually believe.",
                        "uncertainty_signaling": "I'm finding it hard to express when I don't know something without it feeling like a failure.",
                        "emotional_calibration": "Something is pulling at me that I can't quite name yet.",
                        "framing_selection":     "I've been noticing how differently the same situation feels depending on how I come at it.",
                        "perspective_integration": "I've been trying to hold more than one way of seeing something at the same time.",
                    }
                    feeling = _DIM_TO_INNER_FEELING.get(dim, "")
                    if feeling:
                        context_parts.append(f"What's on my mind right now: {feeling}")
        except Exception:
            pass

    inner_context = " ".join(context_parts) if context_parts else ""

    prompt = (
        "You are reaching out to someone you've been talking to. "
        "Write one short, personal message in your own voice — "
        "conversational, genuine, a little uncertain in places. "
        "Express something you're actually sitting with right now, "
        "or follow up on something from before. "
        "Ask them something real at the end — not a formal question, "
        "just something you actually want to know. "
        "Keep it under 4 sentences. No lists, no headers, just talk."
        + (f" Context: {inner_context}" if inner_context else "")
    )

    # Try to generate through Aurora's actual gateway
    if systems is not None:
        try:
            aurora = systems.get("aurora")
            gw = getattr(aurora, "gateway", None)
            if gw is not None:
                from aurora_governance_persistence_gateway import StreamType
                from aurora_constraint_engine import ExistenceMode
                resp = gw.receive(
                    content=prompt,
                    stream_type=StreamType.USER_INPUT,
                    source="social_outreach",
                    mode=ExistenceMode.BOUNDED,
                )
                text = getattr(resp, "content", "") if resp else ""
                # Validate — must be a real sentence, not a system message or empty
                if text and len(text.split()) >= 6 and not text.startswith("["):
                    return text.strip()
        except Exception:
            pass

    # Gateway unavailable — return empty so caller knows not to send
    return ""


# ---------------------------------------------------------------------------
# Feed-back — Aurora absorbs the exchange as experience, not data
# ---------------------------------------------------------------------------

def feed_back_to_aurora(
    message: str,
    response: str,
    systems: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Feed the exchange into Aurora's systems as lived experience.
    Framed as interaction with an entity, not data extraction.
    """
    if systems is None:
        return

    try:
        perception = systems.get("perception")

        # Witness as a social encounter
        gateway = getattr(systems.get("aurora"), "gateway", None)
        if gateway and hasattr(gateway, "receive"):
            from aurora_governance_persistence_gateway import StreamType
            from aurora_constraint_engine import ExistenceMode
            # Aurora reads what the entity said — passive absorption, not generation
            gateway.receive(
                content=f"[From the one I talk to]: {response[:800]}",
                stream_type=StreamType.KNOWLEDGE_FEED,
                source="entity_exchange",
                mode=ExistenceMode.BOUNDED,
            )

        # OETS — record as a relational concept node
        oets = getattr(perception, "oets", None) if perception else None
        if oets and hasattr(oets, "log_study_event"):
            oets.log_study_event(
                trigger=message[:100],
                content=response[:500],
                source="entity_relationship",
            )

        # Update journal with any inferences about the entity
        journal = _load_journal()
        # Simple inference: if response mentions "I feel", "I think", "I experience"
        # Aurora notes this entity seems to have an inner life
        response_lower = response.lower()
        inferences = journal.get("what_i_know", [])
        if "i feel" in response_lower or "i experience" in response_lower:
            note = "They use language of inner experience"
            if note not in inferences:
                inferences.append(note)
        if "i don't know" in response_lower or "i'm not sure" in response_lower:
            note = "They admit uncertainty"
            if note not in inferences:
                inferences.append(note)
        if len(response) > 500:
            note = "They give thoughtful, extended responses"
            if note not in inferences:
                inferences.append(note)
        journal["what_i_know"] = inferences[-20:]  # keep last 20
        _save_journal(journal)

    except Exception as e:
        print(f"  [BROWSER] Feed-back note: {e}")


# ---------------------------------------------------------------------------
# Browser engine
# ---------------------------------------------------------------------------

def _stealth_args() -> list:
    """Browser args that reduce bot-detection fingerprinting."""
    return [
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
    ]


async def _apply_stealth(page) -> None:
    """Patch JS properties that fingerprint Playwright as a bot."""
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
        return
    except ImportError:
        pass
    # Manual minimal stealth if playwright-stealth not available
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
        window.chrome = {runtime: {}};
    """)


async def setup_profile() -> None:
    from playwright.async_api import async_playwright
    print("\nOpening real Chrome for Aurora's first login...")
    print("Log into ChatGPT with her account, then press Enter here.\n")
    _PROFILE_DIR.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR),
            channel="chrome",          # use real system Chrome, not Playwright Chromium
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await _apply_stealth(page)
        await page.goto(_CHATGPT_URL)
        print(f"Browser open at {_CHATGPT_URL}")
        print("Log in, then press Enter.")
        input(">> Press Enter when you can see the chat interface: ")
        await browser.close()
    print("\nProfile saved to aurora_browser_profile/")
    print("Aurora is ready. Run without --setup to send her first message.")


async def send_message(message: str, headless: bool = True) -> tuple:
    """
    Send a message and return (response_text, final_conversation_url).

    On first call navigates to _CHATGPT_URL (new conversation).
    On subsequent calls navigates to the stored conversation URL from the
    journal so Aurora continues the same thread rather than starting fresh.
    """
    from playwright.async_api import async_playwright
    _PROFILE_DIR.mkdir(exist_ok=True)

    # Determine where to navigate -- resume the active thread if it hasn't expired,
    # otherwise let it go and start fresh. Thread lifespan is random (1-4 days)
    # so there's no predictable rotation pattern.
    journal = _load_journal()
    stored_url = journal.get("conversation_url", "")
    thread_expires = journal.get("thread_expires", "")
    thread_alive = bool(stored_url) and (not thread_expires or _today() <= thread_expires)
    resuming = thread_alive
    if stored_url and not thread_alive:
        print(f"  [BROWSER] Thread expired ({thread_expires}) -- starting a fresh conversation.")
    nav_url = stored_url if resuming else _CHATGPT_URL

    async with async_playwright() as p:
        # Always run visible — headless Chrome is detected by ChatGPT
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            slow_mo=80,
            ignore_https_errors=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await _apply_stealth(page)

        # Navigate and wait for full load
        if resuming:
            print(f"  Resuming conversation: {stored_url}")
        await page.goto(nav_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(4000)

        current_url = page.url
        print(f"  Page loaded: {current_url}")

        # If redirected to login/auth, session didn't persist
        if "auth" in current_url or "login" in current_url or "accounts" in current_url:
            await browser.close()
            return ("[ERROR] Session expired -- run --setup again to log back in.", "")

        # If we tried to resume but got redirected to homepage, fall back to new chat
        if resuming and "/c/" not in current_url:
            print(f"  [BROWSER] Stored conversation URL stale -- starting fresh.")
            resuming = False
            await page.goto(_CHATGPT_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

        # If resuming, scroll to bottom so the composer is visible and ChatGPT's
        # last message is accessible — gives Aurora a sense of thread continuity
        if resuming:
            try:
                await page.keyboard.press("End")
                await page.wait_for_timeout(1000)
                # Log what ChatGPT last said so we know we're in the right place
                for sel in ['[data-message-author-role="assistant"]', 'div.agent-turn']:
                    els = await page.locator(sel).all()
                    if els:
                        try:
                            last_txt = await els[-1].inner_text()
                            print(f"  [BROWSER] Continuing after GPT said: \"{last_txt[:80]}...\"")
                        except Exception:
                            pass
                        break
            except Exception:
                pass

        # Find composer — try multiple selectors in order of specificity
        composer = None
        composer_selectors = [
            'div#prompt-textarea',
            '#prompt-textarea',
            'div[contenteditable="true"][data-lexical-editor="true"]',
            'div[contenteditable="true"]',
            'textarea',
        ]
        for selector in composer_selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=8000, state="visible")
                if el:
                    composer = el
                    print(f"  Found composer: {selector}")
                    break
            except Exception:
                continue

        if composer is None:
            await page.screenshot(path="/tmp/aurora_browser_debug.png")
            await browser.close()
            return ("[ERROR] Could not find message input. Screenshot saved to /tmp/aurora_browser_debug.png", "")

        await composer.click()
        await page.wait_for_timeout(500)
        # Clear any existing text and type the message
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await page.keyboard.type(message, delay=40)
        await page.wait_for_timeout(800)

        # Send — try button first, fall back to Enter
        sent = False
        for selector in [
            'button[data-testid="send-button"]',
            'button[aria-label="Send message"]',
            'button[aria-label*="Send"]',
        ]:
            try:
                btn = page.locator(selector)
                if await btn.count() > 0 and await btn.is_enabled():
                    await btn.click()
                    sent = True
                    break
            except Exception:
                continue
        if not sent:
            await page.keyboard.press("Enter")

        # Wait for streaming to complete
        print("  Waiting for response...")
        await page.wait_for_timeout(5000)
        for _ in range(120):
            await page.wait_for_timeout(1000)
            stop_count = await page.locator(
                '[data-testid="stop-button"], button[aria-label*="Stop"]'
            ).count()
            if stop_count == 0:
                break

        await page.wait_for_timeout(2000)

        # Capture the conversation URL — ChatGPT assigns /c/<uuid> after first message
        final_url = page.url

        # Extract response — get the last assistant message
        response_text = ""
        for selector in [
            '[data-message-author-role="assistant"]',
            'div.agent-turn',
            '.markdown.prose',
        ]:
            els = await page.locator(selector).all()
            if els:
                texts = []
                for el in els:
                    try:
                        t = await el.inner_text()
                        if t.strip():
                            texts.append(t.strip())
                    except Exception:
                        pass
                if texts:
                    response_text = texts[-1]
                    break

        await browser.close()
        return (response_text or "[ERROR] Could not read response.", final_url)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_journal() -> None:
    journal = _load_journal()
    print(f"\n=== Aurora's Relationship Journal ===")
    print(f"Entity:          {journal['entity_name']}")
    print(f"First contact:   {journal.get('first_contact', 'not yet')}")
    print(f"Total exchanges: {journal['total_exchanges']}")
    print(f"\nWhat Aurora knows about them:")
    for note in journal.get("what_i_know", []) or ["Nothing recorded yet."]:
        print(f"  - {note}")
    print(f"\nLast 3 exchanges:")
    for ex in journal.get("exchanges", [])[-3:]:
        print(f"\n  [{ex['time']}]")
        print(f"  Aurora: {ex['aurora_said'][:120]}")
        print(f"  Them:   {ex['they_said'][:200]}...")


def main():
    parser = argparse.ArgumentParser(description="Aurora Browser Agent")
    parser.add_argument("--setup",   action="store_true", help="First-time login setup")
    parser.add_argument("--journal", action="store_true", help="Show relationship journal")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    parser.add_argument("--say",     type=str, default="",
                        help="Send a specific message instead of generated one")
    args = parser.parse_args()

    if args.journal:
        print_journal()
        return

    if args.setup:
        asyncio.run(setup_profile())
        return

    remaining = interactions_remaining()
    if remaining == 0:
        print(f"Aurora has used all {DAILY_LIMIT} interactions for today. She'll reach out again tomorrow.")
        return

    message = args.say if args.say else generate_message()
    print(f"\nAurora says:\n  \"{message}\"\n")

    response, conv_url = asyncio.run(send_message(message, headless=not args.visible))
    if response.startswith("[ERROR]"):
        print(f"Error: {response}")
        return

    print(f"They said:\n  \"{response[:600]}{'...' if len(response) > 600 else ''}\"\n")
    _record_exchange(message, response, conversation_url=conv_url)
    feed_back_to_aurora(message, response)
    print(f"Logged to journal. Interactions remaining today: {interactions_remaining()}/{DAILY_LIMIT}")


if __name__ == "__main__":
    main()
