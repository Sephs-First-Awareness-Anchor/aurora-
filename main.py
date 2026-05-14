import os
import sys
import threading
import time
import math
import re

# ---------------------------------------------------------------------------
# Path + env — configured BEFORE any aurora import
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE_AI = os.path.join(_HERE, 'aurora_core_ai')

# aurora_core_ai/ is the authoritative cognitive stack.
# Root is support-only fallback for modules not yet in core_ai.
for _p in (_HERE, _CORE_AI):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# After the loop sys.path order is: [aurora_core_ai, _HERE, ...]
# so all imports prefer aurora_core_ai/ over root-level duplicates.

os.environ['AURORA_SKIP_DEP_INSTALL'] = '1'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.clock import Clock, mainthread
from kivy.utils import platform
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.properties import NumericProperty, StringProperty
from kivy.core.window import Window

# Lazy aurora imports — populated in boot_aurora_thread after path setup
boot_aurora                = None
process_external_user_turn = None
explore                    = None

try:
    from plyer import tts as _plyer_tts
except ImportError:
    _plyer_tts = None

# Non-Android stub so the class body compiles cleanly on desktop
if platform != 'android':
    def run_on_ui_thread(fn):
        return fn

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread

    Context           = autoclass('android.content.Context')
    Intent            = autoclass('android.content.Intent')
    RecognizerIntent  = autoclass('android.speech.RecognizerIntent')
    SpeechRecognizer  = autoclass('android.speech.SpeechRecognizer')
    PythonActivity    = autoclass('org.kivy.android.PythonActivity')
    _JavaTTS          = autoclass('android.speech.tts.TextToSpeech')

    class _TTSInitListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
        def __init__(self, cb):
            super().__init__(); self._cb = cb
        @java_method('(I)V')
        def onInit(self, status):
            Clock.schedule_once(lambda dt: self._cb(status == 0), 0)

    class AndroidSpeechListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']
        def __init__(self, cb, rms_cb, status_cb):
            super().__init__()
            self.callback = cb; self.rms_callback = rms_cb; self.status_callback = status_cb
        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, p): self.status_callback("Ready…")
        @java_method('()V')
        def onBeginningOfSpeech(self): self.status_callback("Listening…")
        @java_method('(F)V')
        def onRmsChanged(self, rms): self.rms_callback(rms)
        @java_method('([B)V')
        def onBufferReceived(self, b): pass
        @java_method('()V')
        def onEndOfSpeech(self): self.status_callback("Processing…")
        @java_method('(I)V')
        def onError(self, e):
            self.status_callback(f"Mic Error: {e}"); self.callback(None, error=e)
        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            texts = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if texts: self.callback(texts.get(0))
        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, p):
            texts = p.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if texts: self.status_callback(f"…{texts.get(0)}")
        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, t, p): pass

    class AuroraOverlayReceiver(PythonJavaClass):
        __javainterfaces__ = ['android/content/BroadcastReceiver']
        def __init__(self, cb): super().__init__(); self.callback = cb
        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, ctx, intent):
            Clock.schedule_once(lambda dt: self.callback(), 0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clean_response(text: str) -> str:
    """Strip internal template artifacts that make Aurora sound scripted."""
    if not text:
        return text
    t = re.sub(r'\[[A-Z_]{3,}\]', '', text).strip()
    # Discard raw constraint token dumps only: 5+ bare single-word tokens (no spaces
    # within each token) separated by semicolons — e.g. "action; listen; awareness; emerge; self"
    # This avoids discarding valid phrases like "Yes; I understand; that's present."
    if re.match(r'^\w+(?:;\s*\w+){4,}\.?$', t):
        return ""
    return re.sub(r'\s{2,}', ' ', t).strip()


# ---------------------------------------------------------------------------
# AuroraFace — animated face avatar embedded in the chat panel
# ---------------------------------------------------------------------------
class AuroraFace(Widget):
    """
    Face avatar drawn entirely with Kivy canvas.
    Sits as a BoxLayout header item — no FloatLayout floating needed.
    """
    STATE_SPEC = {
        'DORMANT':   {'eye': (0.25, 0.25, 0.40), 'glow': (0.10, 0.08, 0.25), 'mouth': 'neutral'},
        'ONLINE':    {'eye': (0.50, 0.80, 1.00),  'glow': (0.30, 0.15, 0.70), 'mouth': 'slight_smile'},
        'LISTENING': {'eye': (1.00, 0.25, 0.65),  'glow': (0.70, 0.05, 0.35), 'mouth': 'neutral'},
        'THINKING':  {'eye': (0.20, 0.70, 1.00),  'glow': (0.05, 0.35, 0.70), 'mouth': 'slight_frown'},
        'SPEAKING':  {'eye': (1.00, 0.85, 0.20),  'glow': (0.70, 0.50, 0.00), 'mouth': 'open'},
    }

    audio_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint    = (1, None)
        self.height       = 200

        self.time         = 0.0
        self._state       = 'DORMANT'
        self._state_time  = 0.0
        self._blink       = 0.0   # 0=open 1=closed
        self._blink_next  = 3.5
        self._blinking    = False
        self._blink_t     = 0.0

        self.bind(pos=self._redraw, size=self._redraw, audio_scale=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 60.0)

    def set_state(self, state):
        if state == self._state:
            return
        self._state = state; self._state_time = 0.0

    def _tick(self, dt):
        if self.height < 4 or self.opacity < 0.01:
            return  # skip all work when invisible — prevents ANR on Android

        self.time        += dt
        self._state_time += dt

        # Blink
        self._blink_next -= dt
        if self._blink_next <= 0 and not self._blinking:
            self._blinking = True; self._blink_t = 0.0
            self._blink_next = 2.8 + (self.time % 2.0)
        if self._blinking:
            self._blink_t += dt
            half = 0.07
            if self._blink_t < half:
                self._blink = self._blink_t / half
            elif self._blink_t < half * 2:
                self._blink = 1.0 - (self._blink_t - half) / half
            else:
                self._blink = 0.0; self._blinking = False
        else:
            self._blink = 0.0

        self._redraw()

    def _redraw(self, *args):
        cx, cy = self.center
        w, h   = self.width, self.height
        t      = self.time
        spec   = self.STATE_SPEC.get(self._state, self.STATE_SPEC['ONLINE'])
        eye_c  = spec['eye']
        glow_c = spec['glow']
        mouth  = spec['mouth']
        blink  = self._blink

        # Face oval proportions
        fw = w * 0.46
        fh = h * 0.88
        breath = 1.0 + math.sin(t * 0.75) * 0.006

        fw *= breath; fh *= breath

        # Eye geometry
        er      = fw * 0.150
        ey      = cy + fh * 0.10
        espread = fw * 0.260
        pr      = er * 0.40

        # Brow height
        brow_y  = ey + er * 1.55

        self.canvas.before.clear()
        with self.canvas.before:
            # Outer glow rings
            for ri in range(3):
                gr   = max(fw, fh) * (0.55 + ri * 0.06)
                spd  = 2.2 if self._state == 'LISTENING' else 0.8
                galp = max(0, (0.14 - ri * 0.04) + math.sin(t * spd + ri) * 0.03)
                Color(*glow_c, galp)
                Ellipse(size=(gr*2, gr*2), pos=(cx - gr, cy - gr))

            # Face oval (dark, slightly tinted)
            Color(0.09, 0.08, 0.16, 1.0)
            Ellipse(size=(fw, fh), pos=(cx - fw/2, cy - fh/2))

            # Face rim
            Color(*glow_c, 0.30)
            Line(ellipse=(cx - fw/2, cy - fh/2, fw, fh), width=1.3)

            # Eyebrows
            bw = er * 1.55; bh = er * 0.20
            lby = brow_y + (er * 0.10 if self._state == 'THINKING' else 0)
            rby = brow_y + (er * 0.32 if self._state == 'THINKING' else 0)
            Color(*eye_c, 0.60)
            Line(ellipse=(cx - espread - bw/2, lby, bw, bh, 0, 180), width=1.7)
            Line(ellipse=(cx + espread - bw/2, rby, bw, bh, 0, 180), width=1.7)

            # Eyes
            for side in (-1, 1):
                ex = cx + side * espread

                # Open height (squeezed during blink)
                eh = er * 2.0 * (1.0 - blink * 0.93)
                ey_off = er * blink * 0.46

                # Eye socket
                Color(0.05, 0.04, 0.10, 0.92)
                Ellipse(size=(er*2, max(2, eh)), pos=(ex - er, ey - eh/2 + ey_off))

                # Iris
                ir = er * 0.72; ih = ir * (1.0 - blink * 0.93)
                Color(*eye_c, 0.88 * (1 - blink * 0.9))
                Ellipse(size=(ir*2, max(1, ih)), pos=(ex - ir, ey - ih/2 + ey_off * 0.8))

                # Pupil shift for THINKING
                px = -er * 0.18 if self._state == 'THINKING' else 0
                py =  er * 0.12 if self._state == 'THINKING' else 0

                # Pupil
                Color(0.03, 0.03, 0.07, 1.0 - blink)
                p2 = pr * (1.0 - blink * 0.96)
                Ellipse(size=(p2*2, p2*2), pos=(ex - p2 + px, ey - p2 + py))

                # Specular
                Color(1.0, 1.0, 1.0, 0.55 * (1 - blink))
                hr = p2 * 0.34
                Ellipse(size=(hr*2, hr*2),
                        pos=(ex + er*0.26 - hr + px, ey + er*0.24 - hr + py))

            # Mouth
            my   = cy - fh * 0.22
            mew  = fw * 0.38
            meh  = fw * 0.18

            if mouth == 'open':
                oh = meh * (0.42 + self.audio_scale * 0.58)
                Color(*eye_c, 0.72)
                Ellipse(size=(mew * 0.52, max(4, oh * 0.68)),
                        pos=(cx - mew*0.26, my - oh*0.34))
                Color(0.04, 0.03, 0.08, 0.88)
                iw = mew * 0.32; ih2 = max(2, oh * 0.38)
                Ellipse(size=(iw, ih2), pos=(cx - iw/2, my - ih2/2 + oh*0.04))
            elif mouth == 'slight_smile':
                Color(*eye_c, 0.58)
                Line(ellipse=(cx - mew/2, my - meh/2, mew, meh, 207, 333), width=1.9)
            elif mouth == 'slight_frown':
                Color(*eye_c, 0.48)
                Line(ellipse=(cx - mew/2, my + meh*0.18, mew, meh*0.7, 22, 158), width=1.6)
            else:
                Color(*eye_c, 0.44)
                Line(ellipse=(cx - mew*0.38, my - meh*0.10, mew*0.76, meh*0.52, 197, 343),
                     width=1.3)

    def update_state(self, axes_activation):
        """Accept axis-activation dict from the pipeline (no-op — face state drives visuals)."""
        pass

    def on_touch_down(self, touch):
        return False  # let taps pass through to underlying handlers


# ---------------------------------------------------------------------------
# AuroraOrb — small indicator for BACKGROUND mode + overlay fallback
# ---------------------------------------------------------------------------
class AuroraOrb(FloatLayout):
    STATE_COLORS = {
        'DORMANT':   [(0.20, 0.20, 0.35)],
        'ONLINE':    [(0.55, 0.35, 0.95), (0.35, 0.15, 0.75)],
        'LISTENING': [(1.00, 0.15, 0.55), (0.85, 0.05, 0.40)],
        'THINKING':  [(0.05, 0.65, 1.00), (0.00, 0.45, 0.85)],
        'SPEAKING':  [(1.00, 0.85, 0.20), (0.95, 0.65, 0.05)],
    }
    AXIS_COLORS = {
        'X': (0.8, 0.9, 1.0), 'T': (0.6, 0.4, 1.0),
        'N': (0.2, 0.9, 0.4), 'B': (1.0, 0.8, 0.2), 'A': (1.0, 0.2, 0.6),
    }
    audio_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint   = (None, None)
        self.size        = (100, 100)
        self.pos_hint    = {'right': 0.95, 'top': 0.88}
        self.colors      = list(self.STATE_COLORS['DORMANT'])
        self.opacity_val = 0.0
        self.time        = 0.0
        self._state      = 'DORMANT'
        self._drag_touch = None
        self.bind(pos=self._redraw, size=self._redraw, audio_scale=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 60.0)

    def set_state(self, state):
        if state == self._state: return
        self._state = state
        if state in self.STATE_COLORS:
            self.colors = list(self.STATE_COLORS[state])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._drag_touch = touch; self.pos_hint = {}; return True
        return super().on_touch_down(touch)
    def on_touch_move(self, touch):
        if self._drag_touch is touch:
            self.center = touch.pos; return True
        return super().on_touch_move(touch)
    def on_touch_up(self, touch):
        if self._drag_touch is touch:
            self._drag_touch = None; return True
        return super().on_touch_up(touch)

    def _redraw(self, *args):
        cx, cy = self.center
        base   = min(self.width, self.height) * self.audio_scale
        t, st  = self.time, self._state
        if st == 'LISTENING':  rings, spd, orb_r = 3, 2.8, 0.12
        elif st == 'THINKING': rings, spd, orb_r = 5, 1.1, 0.20
        elif st == 'SPEAKING': rings, spd, orb_r = 4, 3.2, 0.08
        elif st == 'ONLINE':   rings, spd, orb_r = 3, 1.6, 0.10
        else:                  rings, spd, orb_r = 2, 0.4, 0.04
        cols = self.colors or [(0.5, 0.5, 0.8)]
        self.canvas.before.clear()
        with self.canvas.before:
            for i in range(rings):
                sz  = base * (math.sin(t * spd + i * 1.35) * 0.12 + 0.88) * (1 - i * 0.15)
                ox  = math.sin(t * 1.5 + i * 0.9) * (base * orb_r)
                oy  = math.cos(t * 1.2 + i * 0.7) * (base * orb_r)
                c   = cols[i % len(cols)]
                Color(*c, self.opacity_val * max(0, 0.50 - i * 0.10))
                Ellipse(size=(sz, sz), pos=(cx - sz/2 + ox, cy - sz/2 + oy))
            cs = base * 0.24
            Color(0.9, 0.9, 1.0, 0.90 * self.opacity_val)
            Ellipse(size=(cs, cs), pos=(cx - cs/2, cy - cs/2))

    def _tick(self, dt):
        if self.opacity_val < 0.01 or self.width < 4:
            return  # skip when invisible — prevents ANR on Android
        self.time += dt; self._redraw()

    def update_state(self, axes_activation):
        if not axes_activation: return
        sa = sorted(axes_activation.items(), key=lambda x: x[1], reverse=True)
        nc = [self.AXIS_COLORS[a] for a, _ in sa[:2] if a in self.AXIS_COLORS]
        if nc: self.colors = nc


# ---------------------------------------------------------------------------
# ChatBubble
# ---------------------------------------------------------------------------
class ChatBubble(BoxLayout):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'; self.size_hint_y = None; self.padding = (10, 4)
        if sender == "user":
            self.add_widget(Label(size_hint_x=0.12))
            bg = (0.17, 0.19, 0.27, 1); fg = (0.95, 0.95, 1.0, 1); hal = 'right'
        elif sender == "aurora":
            bg = (0.07, 0.12, 0.23, 1); fg = (0.72, 0.90, 1.0, 1); hal = 'left'
        else:
            bg = (0.08, 0.08, 0.10, 0.7); fg = (0.52, 0.52, 0.62, 1); hal = 'center'
        self.label = Label(text=text, color=fg, halign=hal, valign='middle',
                           size_hint_y=None, padding=(14, 11), font_size='15sp')
        self.label.bind(width=lambda *x: self.label.setter('text_size')(
            self.label, (self.label.width, None)))
        self.label.bind(texture_size=lambda i, ts: (
            setattr(i, 'height', ts[1]), setattr(self, 'height', ts[1] + 10)))
        with self.label.canvas.before:
            Color(*bg); self.rect = RoundedRectangle(radius=[12])
        self.label.bind(pos=lambda i, _: setattr(self.rect, 'pos', i.pos),
                        size=lambda i, _: setattr(self.rect, 'size', i.size))
        self.add_widget(self.label)
        if sender in ('aurora', 'system'):
            self.add_widget(Label(size_hint_x=0.12))


# ---------------------------------------------------------------------------
# AuroraApp
# ---------------------------------------------------------------------------
class AuroraApp(App):
    def build(self):
        self.title = "Aurora"
        Window.clearcolor = (0.03, 0.03, 0.06, 1)
        self.root = FloatLayout()

        # ── Main chat column — fills screen ──
        self.chat_layer = BoxLayout(
            orientation='vertical', spacing=0)
        self.chat_layer.opacity = 0

        # Face avatar header (zero-height when hidden, full height when SUMMONED)
        self.face = AuroraFace()
        self.face.size_hint = (1, None)
        self.face.height = 0       # hidden by default
        self.face.opacity = 0
        self.chat_layer.add_widget(self.face)

        # Chat scroll (expands to fill remaining space)
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None,
                                  spacing=10, padding=[10, 10])
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.chat_layer.add_widget(self.scroll)

        # Text input row (collapsed until keyboard toggled on)
        self.input_area = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=0, opacity=0, spacing=10,
            padding=[10, 5])
        self.text_input = TextInput(
            multiline=False, hint_text="Talk to Aurora…",
            background_color=(0.11, 0.11, 0.15, 1), foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.38, 0.38, 0.48, 1), padding=(14, 12),
            cursor_color=(0.3, 0.85, 1.0, 1), font_size='15sp')
        self.text_input.bind(on_text_validate=self.send_message)
        send_btn = Button(text="Send", size_hint=(None, 1), width=72,
                          background_color=(0.16, 0.42, 0.72, 1), color=(1, 1, 1, 1))
        send_btn.bind(on_release=self.send_message)
        self.input_area.add_widget(self.text_input)
        self.input_area.add_widget(send_btn)
        self.chat_layer.add_widget(self.input_area)

        # Give chat_layer top/bottom margins for the top bar and toolbar
        self.chat_layer_wrapper = BoxLayout(
            orientation='vertical',
            padding=[0, 78, 0, 90],  # top = top-bar height, bottom = toolbar height
            size_hint=(1, 1))
        self.chat_layer_wrapper.add_widget(self.chat_layer)
        self.root.add_widget(self.chat_layer_wrapper)

        # ── Top bar ──
        top = BoxLayout(orientation='horizontal', size_hint=(1, None), height=78,
                        pos_hint={'top': 1}, padding=[14, 10])
        self.embody_toggle = ToggleButton(
            text="Embody: OFF", size_hint=(None, 1), width=185,
            font_size='16sp', background_color=(0.14, 0.14, 0.19, 1),
            color=(0.55, 0.55, 0.65, 1))
        self.embody_toggle.bind(on_release=self.toggle_embodiment)
        top.add_widget(self.embody_toggle)
        self.status_label = Label(text="Dormant", halign='center', font_size='14sp',
                                  color=(0.44, 0.44, 0.56, 1))
        top.add_widget(self.status_label)
        settings_btn = Button(text="⚙", size_hint=(None, 1), width=65,
                              font_size='20sp', background_color=(0, 0, 0, 0),
                              color=(0.50, 0.50, 0.60, 1))
        settings_btn.bind(on_release=self.show_settings)
        top.add_widget(settings_btn)
        self.root.add_widget(top)

        # ── Bottom toolbar ──
        self.bottom_toolbar = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=88,
            pos_hint={'bottom': 1}, padding=[14, 10], spacing=12)
        self.bottom_toolbar.opacity = 0

        self.mic_btn = ToggleButton(text="🎤 Mute", state='normal', font_size='14sp',
                                    background_color=(0.68, 0.15, 0.15, 1))
        self.mic_btn.bind(on_release=self.toggle_mic)
        self.cam_btn = ToggleButton(text="📷 Live: OFF", state='normal', font_size='14sp',
                                    background_color=(0.14, 0.14, 0.19, 1))
        self.cam_btn.bind(on_release=self.on_live_toggle)
        self.voice_btn = Button(text="🗣 Voice", font_size='14sp',
                                background_color=(0.14, 0.14, 0.19, 1))
        self.voice_btn.bind(on_release=self.cycle_voice)
        self.kbd_btn = ToggleButton(text="⌨ Text", state='normal', font_size='14sp',
                                    background_color=(0.14, 0.14, 0.19, 1))
        self.kbd_btn.bind(on_release=self.toggle_keyboard)
        for w in (self.mic_btn, self.cam_btn, self.voice_btn, self.kbd_btn):
            self.bottom_toolbar.add_widget(w)
        self.root.add_widget(self.bottom_toolbar)

        # ── Floating background orb (BACKGROUND mode) ──
        self.orb = AuroraOrb()
        self.orb.bind(on_touch_down=self.on_orb_touch)
        self.root.add_widget(self.orb)

        # ── State ──
        self.systems           = None
        self._pending_messages = []
        self._boot_done        = False
        self._thinking_bubble  = None
        self.live_mode         = False
        self.voice_enabled     = True
        self.full_autonomy     = True
        self.last_percept_ts   = 0
        self.embodiment_state  = "DORMANT"
        self._tts_engine       = None
        self._tts_ready        = False

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA, Permission.RECORD_AUDIO,
                Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE,
                Permission.ACCESS_FINE_LOCATION, Permission.SEND_SMS,
                Permission.CALL_PHONE, Permission.READ_CONTACTS,
            ], self.on_permissions_result)
            self._setup_overlay_receiver()
            self._init_android_tts()
        else:
            self.start_boot_thread()

        return self.root

    # ------------------------------------------------------------------
    # Android TTS
    # ------------------------------------------------------------------
    def _init_android_tts(self):
        try:
            activity = PythonActivity.mActivity
            self._tts_engine = _JavaTTS(activity, _TTSInitListener(self._on_tts_init))
        except Exception:
            pass

    def _on_tts_init(self, success):
        self._tts_ready = success
        if success and self._tts_engine:
            try:
                self._tts_engine.setSpeechRate(0.93)
                self._tts_engine.setPitch(1.04)
            except Exception:
                pass

    def _android_speak(self, text):
        if self._tts_engine and self._tts_ready:
            try:
                self._tts_engine.speak(text, 0, None, "aurora")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Overlay IPC
    # ------------------------------------------------------------------
    def _setup_overlay_receiver(self):
        try:
            IntentFilter = autoclass('android.content.IntentFilter')
            activity = PythonActivity.mActivity
            self._overlay_receiver = AuroraOverlayReceiver(self._on_overlay_tap)
            ifilter = IntentFilter('com.aurora.OVERLAY_TAP')
            try:
                activity.registerReceiver(self._overlay_receiver, ifilter, 0x4)
            except Exception:
                activity.registerReceiver(self._overlay_receiver, ifilter)
        except Exception:
            pass

    def _on_overlay_tap(self):
        if self.embodiment_state == "BACKGROUND":
            self.set_embodiment_state("SUMMONED")
        elif self.embodiment_state == "SUMMONED":
            self.set_embodiment_state("BACKGROUND")

    def _broadcast_state_to_overlay(self, state):
        if platform != 'android':
            return
        try:
            intent = Intent('com.aurora.SET_STATE')
            intent.setPackage(PythonActivity.mActivity.getPackageName())
            intent.putExtra('state', state)
            PythonActivity.mActivity.sendBroadcast(intent)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Orb touch + embodiment
    # ------------------------------------------------------------------
    def on_orb_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if self.embodiment_state == "BACKGROUND":
                self.set_embodiment_state("SUMMONED")
            elif self.embodiment_state == "SUMMONED":
                self.set_embodiment_state("BACKGROUND")
            return True
        return False

    def toggle_embodiment(self, btn):
        if btn.state == 'down':
            btn.text = "Embody: ON"; btn.color = (0.20, 0.80, 1.0, 1)
            self.set_embodiment_state("SUMMONED")
        else:
            btn.text = "Embody: OFF"; btn.color = (0.55, 0.55, 0.65, 1)
            self.set_embodiment_state("DORMANT")

    def set_embodiment_state(self, state):
        self.embodiment_state = state

        if state == "DORMANT":
            self.chat_layer.opacity     = 0
            self.bottom_toolbar.opacity = 0
            self.face.height            = 0
            self.face.opacity           = 0
            self.face.canvas.before.clear()
            self.orb.canvas.before.clear()
            self.orb.opacity_val        = 0.0
            self.orb.size               = (0, 0)
            self.face.set_state("DORMANT")
            self.orb.set_state("DORMANT")
            self.set_status("Dormant")
            self.stop_listening()
            if platform == 'android':
                self._stop_native_overlay()
                self._broadcast_state_to_overlay("DORMANT")

        elif state == "BACKGROUND":
            self.chat_layer.opacity     = 0
            self.bottom_toolbar.opacity = 1
            self.face.height            = 0
            self.face.opacity           = 0
            # Show small orb
            orb_st = "ONLINE" if self._boot_done else "DORMANT"
            self.orb.opacity_val = 0.65
            self.orb.size        = (95, 95)
            self.orb.set_state(orb_st)
            self.set_status("Listening…" if self._boot_done else "Waking up…")
            if platform == 'android':
                self._start_native_overlay()
                self._broadcast_state_to_overlay(orb_st)
            if self.mic_btn.state == 'normal':
                self.mic_btn.state = 'down'; self.toggle_mic(self.mic_btn)

        elif state == "SUMMONED":
            self.chat_layer.opacity     = 1
            self.bottom_toolbar.opacity = 1
            # Hide orb, show face
            self.orb.opacity_val = 0.0
            self.orb.size        = (0, 0)
            self.face.height     = 200
            self.face.opacity    = 1
            face_st = "ONLINE" if self._boot_done else "DORMANT"
            self.face.set_state(face_st)
            self.set_status("Aurora is Present")
            if platform == 'android':
                self._start_native_overlay()
            if self.mic_btn.state == 'down':
                self.start_listening()

    def _start_native_overlay(self):
        try:
            Settings = autoclass('android.provider.Settings')
            activity = PythonActivity.mActivity
            if not Settings.canDrawOverlays(activity):
                self.set_status("Need 'Draw over other apps' permission")
                self.check_overlay_permission(); return
            intent = Intent()
            intent.setClassName(activity.getPackageName(), "org.aurora.aurora.OverlayService")
            activity.startService(intent)
        except Exception as e:
            self.set_status(f"Overlay Error: {e}")

    def _stop_native_overlay(self):
        try:
            activity = PythonActivity.mActivity
            intent   = Intent()
            intent.setClassName(activity.getPackageName(), "org.aurora.aurora.OverlayService")
            activity.stopService(intent)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Mic / STT
    # ------------------------------------------------------------------
    def _set_state(self, state):
        if self.embodiment_state == "SUMMONED":
            self.face.set_state(state)
        else:
            self.orb.set_state(state)
        self._broadcast_state_to_overlay(state)

    def toggle_mic(self, btn):
        if btn.state == 'down':
            btn.text = "🎤 Active"; btn.background_color = (0.10, 0.68, 0.10, 1)
            self.set_status("Mic Active — Listening…")
            self._set_state("LISTENING"); self.start_listening()
        else:
            btn.text = "🎤 Mute"; btn.background_color = (0.68, 0.15, 0.15, 1)
            self.set_status("Mic Muted")
            self._set_state("ONLINE" if self._boot_done else "DORMANT")
            self.stop_listening()

    def start_listening(self):
        if platform == 'android':
            try: self._native_stt_start()
            except Exception as e: self.add_bubble(f"Voice Error: {e}", "system")
        else:
            self.add_bubble("Voice recording not supported on desktop.", "system")
            self.mic_btn.state = 'normal'; self.toggle_mic(self.mic_btn)

    @run_on_ui_thread
    def _native_stt_start(self):
        activity = PythonActivity.mActivity
        if hasattr(self, 'recognizer') and self.recognizer is not None:
            try: self.recognizer.destroy()
            except Exception: pass
            self.recognizer = None
        self.recognizer   = SpeechRecognizer.createSpeechRecognizer(activity)
        self.stt_listener = AndroidSpeechListener(
            self.on_stt_results_native, self.on_rms_changed, self.set_status)
        self.recognizer.setRecognitionListener(self.stt_listener)
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
        self.recognizer.startListening(intent)

    def stop_listening(self):
        if platform == 'android': self._native_stt_stop()

    @run_on_ui_thread
    def _native_stt_stop(self):
        if hasattr(self, 'recognizer') and self.recognizer:
            self.recognizer.stopListening()

    def on_rms_changed(self, rmsdB):
        target = 1.0 + (max(0, rmsdB + 2) / 12.0) * 0.5
        if self.embodiment_state == "SUMMONED":
            self.face.audio_scale = self.face.audio_scale * 0.7 + target * 0.3
        else:
            self.orb.audio_scale = self.orb.audio_scale * 0.7 + target * 0.3

    @mainthread
    def on_stt_results_native(self, text, error=None):
        if self.embodiment_state == "SUMMONED": self.face.audio_scale = 1.0
        else: self.orb.audio_scale = 1.0
        if error:
            if self.mic_btn.state == 'down':
                Clock.schedule_once(lambda dt: self.start_listening(), 0.5)
            return
        if text:
            self.add_bubble(text, "user")
            if self.embodiment_state == "BACKGROUND" and "aurora" in text.lower():
                self.set_embodiment_state("SUMMONED")
            if self.systems:
                self._show_thinking(); self.set_status("Thinking…")
                threading.Thread(
                    target=self.process_turn_thread, args=(text,), daemon=True).start()
            else:
                self._pending_messages.append(text)
        if self.mic_btn.state == 'down':
            Clock.schedule_once(lambda dt: self.start_listening(), 0.5)

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------
    def on_permissions_result(self, permissions, grants):
        if platform == 'android': self.check_overlay_permission()
        self.start_boot_thread()

    def check_overlay_permission(self):
        try:
            Settings = autoclass('android.provider.Settings')
            activity = PythonActivity.mActivity
            if not Settings.canDrawOverlays(activity):
                self.add_bubble(
                    "Aurora needs 'Draw over other apps' permission. Opening settings…", "system")
                def go(dt):
                    Uri     = autoclass('android.net.Uri')
                    _Intent = autoclass('android.content.Intent')
                    i = _Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:" + activity.getPackageName()))
                    activity.startActivity(i)
                Clock.schedule_once(go, 3.0)
        except Exception:
            pass

    def start_boot_thread(self):
        threading.Thread(target=self.boot_aurora_thread, daemon=True).start()

    def boot_aurora_thread(self):
        global boot_aurora, process_external_user_turn, explore
        try:
            from aurora import boot_aurora as _ba, process_external_user_turn as _pt
            boot_aurora                = _ba
            process_external_user_turn = _pt
            try:
                from aurora import explore as _ex; explore = _ex
            except Exception:
                pass
        except ImportError as e:
            Clock.schedule_once(
                lambda dt: self.set_status(f"Aurora Core Not Found: {str(e)[:50]}"), 0)
            return

        try:
            Clock.schedule_once(lambda dt: self.set_status("Waking Aurora…"), 0)

            if platform == 'android':
                try:
                    activity  = PythonActivity.mActivity
                    state_dir = os.path.join(
                        str(activity.getFilesDir().getAbsolutePath()), 'aurora_state')
                except Exception:
                    state_dir = os.path.join(_HERE, 'aurora_state')
            else:
                state_dir = os.path.join(_HERE, 'aurora_state')

            os.makedirs(state_dir, exist_ok=True)
            self.systems    = boot_aurora(state_dir=state_dir, verbose=False)
            self._boot_done = True
            Clock.schedule_once(lambda dt: self.set_status("Aurora is Online"), 0)

            pending = list(self._pending_messages)
            self._pending_messages.clear()
            for msg in pending:
                threading.Thread(
                    target=self.process_turn_thread, args=(msg,), daemon=True).start()
            threading.Thread(target=self.autonomy_loop, daemon=True).start()
        except Exception as e:
            import traceback; traceback.print_exc()
            err = str(e)[:65]
            Clock.schedule_once(
                lambda dt: self.set_status(f"Boot Failed: {err}"), 0)

    @mainthread
    def set_status(self, text):
        self.status_label.text = text

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------
    def send_message(self, *args):
        user_text = self.text_input.text.strip()
        if not user_text: return
        self.add_bubble(user_text, "user"); self.text_input.text = ""
        if self.systems:
            self._show_thinking(); self.set_status("Thinking…")
            threading.Thread(
                target=self.process_turn_thread, args=(user_text,), daemon=True).start()
        else:
            self._pending_messages.append(user_text)
            self.add_bubble("I'm still waking up — your message is queued.", "aurora")

    def process_turn_thread(self, user_text):
        # Voice command fast-path (tools: battery, weather, sms, call, …)
        try:
            from aurora_voice import _detect_voice_command, _execute_voice_command
            cmd_key, p1, p2 = _detect_voice_command(user_text)
            if cmd_key:
                content = _execute_voice_command(cmd_key, p1, p2, self.systems)
                Clock.schedule_once(
                    lambda dt: self.on_aurora_response(content, update_orb=False), 0)
                return
        except Exception:
            pass

        try:
            result     = process_external_user_turn(self.systems, user_text)
            resp_A     = result.get('resp_A')
            raw        = getattr(resp_A, 'content', '') if resp_A else ''
            content    = _clean_response(raw) or '…'
            activation = result.get('noncomp_output', {}).get('axis_activation', {})
            Clock.schedule_once(
                lambda dt: self.on_aurora_response(
                    content, update_orb=True, activation=activation), 0)
        except Exception as e:
            import traceback; traceback.print_exc()
            Clock.schedule_once(
                lambda dt: self.on_aurora_response(f"Error: {e}"), 0)

    def on_aurora_response(self, content, update_orb=False, activation=None):
        self._hide_thinking()
        self.add_bubble(content, "aurora")
        self.set_status("Aurora is Online")
        self._set_state("ONLINE")
        if update_orb and activation:
            if self.embodiment_state == "SUMMONED": self.face.update_state(activation)
            else: self.orb.update_state(activation)
        if self.voice_enabled:
            self._set_state("SPEAKING")
            threading.Thread(target=self.speak_thread, args=(content,), daemon=True).start()

    def speak_thread(self, text):
        was_listening = (self.mic_btn.state == 'down')
        if was_listening:
            self.stop_listening(); self.set_status("Speaking…")
        if platform == 'android':
            self._android_speak(text)
            time.sleep(max(1.5, len(text.split()) * 0.55))
        else:
            spoke = False
            try:
                from aurora_voice import speak as _av_speak; _av_speak(text); spoke = True
            except Exception:
                pass
            if not spoke and _plyer_tts:
                try:
                    _plyer_tts.speak(text)
                    time.sleep(max(1.5, len(text.split()) * 0.5))
                except Exception:
                    pass
        resume = "LISTENING" if was_listening else "ONLINE"
        Clock.schedule_once(
            lambda dt: (self._set_state(resume), self._broadcast_state_to_overlay(resume)), 0)
        if was_listening:
            Clock.schedule_once(lambda dt: self.start_listening(), 0.8)

    def cycle_voice(self, *args):
        try:
            from aurora_voice import _execute_voice_command
            msg = _execute_voice_command("switchvoice", None, None, self.systems)
            self.add_bubble(msg or "Voice changed.", "system")
        except Exception:
            self.add_bubble("Voice cycling not available.", "system")

    @mainthread
    def _show_thinking(self):
        if self._thinking_bubble is None:
            self._thinking_bubble = ChatBubble(text="…", sender="aurora")
            self.chat_log.add_widget(self._thinking_bubble)
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
        self._set_state("THINKING")

    @mainthread
    def _hide_thinking(self):
        if self._thinking_bubble is not None:
            try: self.chat_log.remove_widget(self._thinking_bubble)
            except Exception: pass
            self._thinking_bubble = None

    @mainthread
    def add_bubble(self, text, sender):
        b = ChatBubble(text=text, sender=sender)
        self.chat_log.add_widget(b)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    # ------------------------------------------------------------------
    # Settings / misc
    # ------------------------------------------------------------------
    def show_settings(self, *args):
        content = BoxLayout(orientation='vertical', padding=12, spacing=10)
        for lbl, attr in [("Voice Synthesis", 'voice_enabled'),
                           ("Full Autonomy",    'full_autonomy')]:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=42)
            row.add_widget(Label(text=lbl, font_size='14sp'))
            val = getattr(self, attr)
            btn = ToggleButton(text="ON" if val else "OFF",
                               state='down' if val else 'normal', font_size='14sp')
            btn.bind(on_release=lambda x, a=attr: (
                setattr(self, a, x.state == 'down'),
                setattr(x, 'text', "ON" if x.state == 'down' else "OFF")))
            row.add_widget(btn)
            content.add_widget(row)
        close_btn = Button(text="Close", size_hint_y=None, height=42, font_size='14sp')
        popup = Popup(title="Aurora Settings", content=content, size_hint=(0.82, 0.42))
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def on_live_toggle(self, instance):
        self.live_mode = (instance.state == 'down')
        self.add_bubble(
            "Live Mode Enabled." if self.live_mode else "Live Mode Disabled.", "system")

    def toggle_keyboard(self, btn):
        if btn.state == 'down':
            self.input_area.height = 52; self.input_area.opacity = 1
        else:
            self.input_area.height = 0; self.input_area.opacity = 0

    def autonomy_loop(self):
        while True:
            time.sleep(10)
            if not self.systems or not self.full_autonomy: continue
            try:
                from aurora_curiosity_engine import curiosity_cycle
                if time.time() - self.last_percept_ts > 30:
                    self.last_percept_ts = time.time()
                    if self.embodiment_state != "SUMMONED":
                        result = curiosity_cycle(self.systems)
                        if result and result.get("response"):
                            heat = (self.systems.get("lattice").get_global_heat()
                                    if self.systems.get("lattice") else 0.5)
                            if heat > 0.6:
                                c = result["response"]
                                Clock.schedule_once(
                                    lambda dt, x=c: self.on_aurora_response(x, update_orb=True), 0)
            except Exception:
                pass
            if self.live_mode and time.time() - getattr(self, '_last_live_ts', 0) > 45:
                self._perform_live_percept(); self._last_live_ts = time.time()

    def _perform_live_percept(self):
        try:
            ctx    = "I am observing my environment. [SENSORY_DATA] source: mobile_camera"
            result = process_external_user_turn(
                self.systems, ctx, source_label="live_mode_sensory")
            resp_A = result.get('resp_A')
            raw    = getattr(resp_A, 'content', None) if resp_A else None
            if raw and getattr(resp_A, 'confidence', 0) > 0.8:
                content = _clean_response(raw)
                act     = result.get('noncomp_output', {}).get('axis_activation')
                if content:
                    Clock.schedule_once(
                        lambda dt: self.on_aurora_response(
                            content, update_orb=True, activation=act), 0)
        except Exception:
            pass

    def on_stop(self):
        if platform == 'android' and self._tts_engine:
            try: self._tts_engine.shutdown()
            except Exception: pass


if __name__ == '__main__':
    AuroraApp().run()
