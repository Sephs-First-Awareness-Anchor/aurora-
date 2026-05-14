import os
import threading
import time
import math
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread
from kivy.utils import platform
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.properties import NumericProperty
from kivy.core.window import Window

try:
    from aurora import boot_aurora, process_external_user_turn, explore
except ImportError:
    boot_aurora = None
    process_external_user_turn = None
    explore = None

try:
    from plyer import tts
except ImportError:
    tts = None

# On non-Android, stub the decorator so the class body parses cleanly
if platform != 'android':
    def run_on_ui_thread(fn):
        return fn

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread

    Context        = autoclass('android.content.Context')
    Intent         = autoclass('android.content.Intent')
    RecognizerIntent = autoclass('android.speech.RecognizerIntent')
    SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class AndroidSpeechListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']

        def __init__(self, callback, rms_callback, status_callback):
            super().__init__()
            self.callback = callback
            self.rms_callback = rms_callback
            self.status_callback = status_callback

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, params):
            self.status_callback("Ready...")

        @java_method('()V')
        def onBeginningOfSpeech(self):
            self.status_callback("Listening...")

        @java_method('(F)V')
        def onRmsChanged(self, rmsdB):
            self.rms_callback(rmsdB)

        @java_method('([B)V')
        def onBufferReceived(self, buffer): pass

        @java_method('()V')
        def onEndOfSpeech(self):
            self.status_callback("Processing...")

        @java_method('(I)V')
        def onError(self, error):
            self.status_callback(f"Mic Error: {error}")
            self.callback(None, error=error)

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            texts = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if texts:
                self.callback(texts.get(0))

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, partialResults):
            texts = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if texts:
                self.status_callback(f"...{texts.get(0)}")

        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, eventType, params): pass

    class AuroraOverlayReceiver(PythonJavaClass):
        """Receives tap-broadcast from OverlayService so Kivy can respond."""
        __javainterfaces__ = ['android/content/BroadcastReceiver']

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, context, intent):
            Clock.schedule_once(lambda dt: self.callback(), 0)


# ---------------------------------------------------------------------------
# AuroraOrb — state-aware animated orb with face micro-elements
# ---------------------------------------------------------------------------
class AuroraOrb(FloatLayout):
    AXIS_COLORS = {
        'X': (0.8, 0.9, 1.0),
        'T': (0.6, 0.4, 1.0),
        'N': (0.2, 0.9, 0.4),
        'B': (1.0, 0.8, 0.2),
        'A': (1.0, 0.2, 0.6),
    }
    STATE_COLORS = {
        'DORMANT':   [(0.20, 0.20, 0.35)],
        'ONLINE':    [(0.55, 0.35, 0.95), (0.35, 0.15, 0.75)],
        'LISTENING': [(1.00, 0.15, 0.55), (0.85, 0.05, 0.40)],
        'THINKING':  [(0.05, 0.65, 1.00), (0.00, 0.45, 0.85)],
        'SPEAKING':  [(1.00, 0.85, 0.20), (0.95, 0.65, 0.05)],
    }

    audio_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (250, 250)
        self.pos_hint = {'center_x': 0.5, 'top': 0.95}
        self.colors = list(self.STATE_COLORS['DORMANT'])
        self.opacity_val = 0.8
        self.time = 0.0
        self._state = 'DORMANT'
        self._state_time = 0.0
        self._drag_touch = None
        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  audio_scale=self._update_canvas)
        Clock.schedule_interval(self._animate, 1 / 60.0)

    def set_state(self, state):
        if state == self._state:
            return
        self._state = state
        self._state_time = 0.0
        if state in self.STATE_COLORS:
            self.colors = list(self.STATE_COLORS[state])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._drag_touch = touch
            self.pos_hint = {}
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._drag_touch is touch:
            self.center = touch.pos
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._drag_touch is touch:
            self._drag_touch = None
            return True
        return super().on_touch_up(touch)

    def _update_canvas(self, *args):
        cx, cy = self.center
        base = min(self.width, self.height) * self.audio_scale
        t = self.time
        state = self._state

        if state == 'LISTENING':
            rings, speed, orb_r = 4, 2.8, 0.12
            cb, oa = 0.95, 0.55
        elif state == 'THINKING':
            rings, speed, orb_r = 6, 1.1, 0.20
            cb, oa = 0.80, 0.42
        elif state == 'SPEAKING':
            rings, speed, orb_r = 5, 3.2, 0.08
            cb, oa = 1.0,  0.65
        elif state == 'ONLINE':
            rings, speed, orb_r = 4, 1.6, 0.10
            cb, oa = 0.90, 0.48
        else:  # DORMANT
            rings, speed, orb_r = 2, 0.4, 0.04
            cb, oa = 0.25, 0.18

        cols = self.colors or [(0.5, 0.5, 0.8)]
        self.canvas.before.clear()
        with self.canvas.before:
            for i in range(rings):
                ph = t * speed + i * 1.35
                pulse = math.sin(ph) * 0.12 + 0.88
                sz = base * pulse * (1.0 - i * 0.14)

                if state == 'THINKING':
                    ang = t * 2.0 + i * (math.pi * 2.0 / rings)
                    ox = math.cos(ang) * (base * orb_r)
                    oy = math.sin(ang) * (base * orb_r)
                else:
                    ox = math.sin(t * 1.5 + i * 0.9) * (base * orb_r)
                    oy = math.cos(t * 1.2 + i * 0.7) * (base * orb_r)

                c = cols[i % len(cols)]
                alpha = self.opacity_val * max(0, oa - i * 0.08)
                Color(*c, alpha)
                Ellipse(size=(sz, sz), pos=(cx - sz/2 + ox, cy - sz/2 + oy))

            # Thin outer halo ring
            hr = base * 0.56
            ha = self.opacity_val * (0.55 + math.sin(t * speed) * 0.18)
            Color(*cols[0], ha)
            Ellipse(size=(hr*2, hr*2), pos=(cx - hr, cy - hr))
            ir = hr * 0.88
            Color(0.04, 0.04, 0.07, self.opacity_val)
            Ellipse(size=(ir*2, ir*2), pos=(cx - ir, cy - ir))

            # Core
            cs = base * (0.22 + math.sin(t * speed * 0.6) * 0.02)
            Color(cb, cb, 1.0, 0.95 * self.opacity_val)
            Ellipse(size=(cs, cs), pos=(cx - cs/2, cy - cs/2))

            # Face micro-elements (eyes + mouth nub)
            if state in ('ONLINE', 'LISTENING', 'SPEAKING', 'THINKING') and base > 90:
                dot = base * 0.046
                spread = base * 0.082
                rise = base * 0.052
                fa = 0.60 * self.opacity_val
                Color(0.05, 0.05, 0.15, fa)
                Ellipse(size=(dot, dot),
                        pos=(cx - spread - dot/2, cy + rise - dot/2))
                Ellipse(size=(dot, dot),
                        pos=(cx + spread - dot/2, cy + rise - dot/2))
                m = dot * 0.65
                Color(0.05, 0.05, 0.15, fa * 0.75)
                Ellipse(size=(m, m), pos=(cx - m/2, cy - rise * 1.6))

    def _animate(self, dt):
        self.time += dt
        self._state_time += dt
        self._update_canvas()

    def update_state(self, axes_activation):
        if not axes_activation:
            return
        sorted_axes = sorted(axes_activation.items(), key=lambda x: x[1], reverse=True)
        new_colors = [self.AXIS_COLORS[ax] for ax, _ in sorted_axes[:2]
                      if ax in self.AXIS_COLORS]
        if new_colors:
            self.colors = new_colors


# ---------------------------------------------------------------------------
# ChatBubble
# ---------------------------------------------------------------------------
class ChatBubble(BoxLayout):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = (10, 5)

        if sender == "user":
            self.add_widget(Label(size_hint_x=0.15))
            bg_color   = (0.18, 0.20, 0.28, 1)
            text_color = (0.95, 0.95, 1.00, 1)
            halign     = 'right'
        elif sender == "aurora":
            bg_color   = (0.07, 0.13, 0.24, 1)
            text_color = (0.72, 0.90, 1.00, 1)
            halign     = 'left'
        else:
            bg_color   = (0.08, 0.08, 0.10, 0.7)
            text_color = (0.52, 0.52, 0.62, 1)
            halign     = 'center'

        self.label = Label(
            text=text,
            color=text_color,
            halign=halign,
            valign='middle',
            size_hint_y=None,
            padding=(14, 12),
            font_size='15sp',
        )
        self.label.bind(
            width=lambda *x: self.label.setter('text_size')(
                self.label, (self.label.width, None)))
        self.label.bind(texture_size=self._update_height)

        with self.label.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(radius=[12])
        self.label.bind(pos=self._update_rect, size=self._update_rect)
        self.add_widget(self.label)

        if sender in ("aurora", "system"):
            self.add_widget(Label(size_hint_x=0.15))

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_height(self, instance, texture_size):
        instance.height = texture_size[1]
        self.height = instance.height + 10


# ---------------------------------------------------------------------------
# AuroraApp
# ---------------------------------------------------------------------------
class AuroraApp(App):
    def build(self):
        self.title = "Aurora"
        Window.clearcolor = (0.04, 0.04, 0.07, 1)
        self.root = FloatLayout()

        # Chat layer (hidden until SUMMONED)
        self.chat_layer = BoxLayout(
            orientation='vertical', padding=[10, 62, 10, 92], spacing=8)
        self.chat_layer.opacity = 0

        self.scroll = ScrollView(size_hint=(1, 1))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=12)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.chat_layer.add_widget(self.scroll)

        self.input_area = BoxLayout(
            orientation='horizontal', size_hint=(1, None),
            height=0, opacity=0, spacing=10)
        self.text_input = TextInput(
            multiline=False,
            hint_text="Talk to Aurora...",
            background_color=(0.12, 0.12, 0.16, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.40, 0.40, 0.50, 1),
            padding=(14, 12),
            cursor_color=(0.3, 0.85, 1.0, 1),
            font_size='15sp',
        )
        self.text_input.bind(on_text_validate=self.send_message)
        send_btn = Button(
            text="Send", size_hint=(None, 1), width=75,
            background_color=(0.18, 0.45, 0.75, 1), color=(1, 1, 1, 1))
        send_btn.bind(on_release=self.send_message)
        self.input_area.add_widget(self.text_input)
        self.input_area.add_widget(send_btn)
        self.chat_layer.add_widget(self.input_area)
        self.root.add_widget(self.chat_layer)

        # Top bar
        top = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=80,
            pos_hint={'top': 1}, padding=[15, 10])
        self.embody_toggle = ToggleButton(
            text="Embody: OFF", size_hint=(None, 1), width=185,
            font_size='17sp', background_color=(0.16, 0.16, 0.20, 1),
            color=(0.58, 0.58, 0.68, 1))
        self.embody_toggle.bind(on_release=self.toggle_embodiment)
        top.add_widget(self.embody_toggle)

        self.status_label = Label(
            text="Dormant", halign='center', font_size='15sp',
            color=(0.48, 0.48, 0.62, 1))
        top.add_widget(self.status_label)

        settings_btn = Button(
            text="⚙", size_hint=(None, 1), width=72,
            font_size='22sp', background_color=(0, 0, 0, 0),
            color=(0.55, 0.55, 0.65, 1))
        settings_btn.bind(on_release=self.show_settings)
        top.add_widget(settings_btn)
        self.root.add_widget(top)

        # Bottom toolbar (hidden until embodied)
        self.bottom_toolbar = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=95,
            pos_hint={'bottom': 1}, padding=[15, 12], spacing=14)
        self.bottom_toolbar.opacity = 0

        self.mic_btn = ToggleButton(
            text="🎤 Mute", state='normal', font_size='15sp',
            background_color=(0.72, 0.18, 0.18, 1))
        self.mic_btn.bind(on_release=self.toggle_mic)

        self.cam_btn = ToggleButton(
            text="📷 Live: OFF", state='normal', font_size='15sp',
            background_color=(0.16, 0.16, 0.20, 1))
        self.cam_btn.bind(on_release=self.on_live_toggle)

        self.voice_profile_btn = Button(
            text="🗣 Voice", font_size='15sp',
            background_color=(0.16, 0.16, 0.20, 1))

        self.kbd_btn = ToggleButton(
            text="⌨ Text", state='normal', font_size='15sp',
            background_color=(0.16, 0.16, 0.20, 1))
        self.kbd_btn.bind(on_release=self.toggle_keyboard)

        for w in (self.mic_btn, self.cam_btn, self.voice_profile_btn, self.kbd_btn):
            self.bottom_toolbar.add_widget(w)
        self.root.add_widget(self.bottom_toolbar)

        # Floating orb
        self.orb = AuroraOrb()
        self.orb.opacity_val = 0
        self.orb.size = (0, 0)
        self.orb.bind(on_touch_down=self.on_orb_touch)
        self.root.add_widget(self.orb)

        # App state
        self.systems          = None
        self._pending_messages = []   # queued while booting
        self._boot_done       = False
        self._thinking_bubble = None
        self.live_mode        = False
        self.voice_enabled    = True
        self.full_autonomy    = True
        self.last_percept_ts  = 0
        self.embodiment_state = "DORMANT"

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.ACCESS_FINE_LOCATION,
                Permission.SEND_SMS,
                Permission.CALL_PHONE,
                Permission.READ_CONTACTS,
            ], self.on_permissions_result)
            self._setup_overlay_receiver()
        else:
            self.start_boot_thread()

        return self.root

    # ------------------------------------------------------------------
    # Android overlay IPC
    # ------------------------------------------------------------------
    def _setup_overlay_receiver(self):
        try:
            IntentFilter   = autoclass('android.content.IntentFilter')
            activity       = PythonActivity.mActivity
            self._overlay_receiver = AuroraOverlayReceiver(self._on_overlay_tap)
            intent_filter  = IntentFilter('com.aurora.OVERLAY_TAP')
            # API 33+ wants explicit exported flag; fall back if unavailable
            try:
                RECEIVER_NOT_EXPORTED = 0x4
                activity.registerReceiver(
                    self._overlay_receiver, intent_filter, RECEIVER_NOT_EXPORTED)
            except Exception:
                activity.registerReceiver(self._overlay_receiver, intent_filter)
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
    # Orb touch / embodiment
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
            btn.text  = "Embody: ON"
            btn.color = (0.22, 0.82, 1.0, 1)
            self.set_embodiment_state("BACKGROUND")
        else:
            btn.text  = "Embody: OFF"
            btn.color = (0.58, 0.58, 0.68, 1)
            self.set_embodiment_state("DORMANT")

    def set_embodiment_state(self, state):
        self.embodiment_state = state
        if state == "DORMANT":
            self.orb.opacity_val = 0
            self.orb.size        = (0, 0)
            self.orb.set_state("DORMANT")
            self.chat_layer.opacity      = 0
            self.bottom_toolbar.opacity  = 0
            self.set_status("Dormant")
            self.stop_listening()
            if platform == 'android':
                self._stop_native_overlay()
                self._broadcast_state_to_overlay("DORMANT")

        elif state == "BACKGROUND":
            self.orb.opacity_val = 0.55
            self.orb.size        = (105, 105) if platform != 'android' else (0, 0)
            self.orb.pos_hint    = {'right': 0.95, 'top': 0.88}
            orb_st = "ONLINE" if self._boot_done else "DORMANT"
            self.orb.set_state(orb_st)
            self.chat_layer.opacity     = 0
            self.bottom_toolbar.opacity = 1
            self.set_status("Listening..." if self._boot_done else "Waking up...")
            if platform == 'android':
                self._start_native_overlay()
                self._broadcast_state_to_overlay(orb_st)
            if self.mic_btn.state == 'normal':
                self.mic_btn.state = 'down'
                self.toggle_mic(self.mic_btn)

        elif state == "SUMMONED":
            self.orb.opacity_val = 0.90
            self.orb.size        = (240, 240)
            self.orb.pos_hint    = {'center_x': 0.5, 'center_y': 0.62}
            self.orb.set_state("ONLINE" if self._boot_done else "DORMANT")
            self.chat_layer.opacity     = 1
            self.bottom_toolbar.opacity = 1
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
                self.check_overlay_permission()
                return
            intent = Intent()
            intent.setClassName(
                activity.getPackageName(), "org.aurora.aurora.OverlayService")
            activity.startService(intent)
        except Exception as e:
            self.set_status(f"Overlay Error: {e}")

    def _stop_native_overlay(self):
        try:
            activity = PythonActivity.mActivity
            intent   = Intent()
            intent.setClassName(
                activity.getPackageName(), "org.aurora.aurora.OverlayService")
            activity.stopService(intent)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Mic / STT
    # ------------------------------------------------------------------
    def toggle_mic(self, btn):
        if btn.state == 'down':
            btn.text             = "🎤 Active"
            btn.background_color = (0.12, 0.72, 0.12, 1)
            self.set_status("Mic Active — Listening...")
            self.orb.set_state("LISTENING")
            self._broadcast_state_to_overlay("LISTENING")
            self.start_listening()
        else:
            btn.text             = "🎤 Mute"
            btn.background_color = (0.72, 0.18, 0.18, 1)
            self.set_status("Mic Muted")
            st = "ONLINE" if self._boot_done else "DORMANT"
            self.orb.set_state(st)
            self._broadcast_state_to_overlay(st)
            self.stop_listening()

    def start_listening(self):
        if platform == 'android':
            try:
                self._native_stt_start()
            except Exception as e:
                self.add_bubble(f"Voice Error: {e}", "system")
        else:
            self.add_bubble("Voice recording not supported on desktop.", "system")
            self.mic_btn.state = 'normal'
            self.toggle_mic(self.mic_btn)

    @run_on_ui_thread
    def _native_stt_start(self):
        activity = PythonActivity.mActivity
        # Always destroy previous recognizer — prevents error 8 (already listening)
        if hasattr(self, 'recognizer') and self.recognizer is not None:
            try:
                self.recognizer.destroy()
            except Exception:
                pass
            self.recognizer = None
        self.recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
        self.stt_listener = AndroidSpeechListener(
            self.on_stt_results_native, self.on_rms_changed, self.set_status)
        self.recognizer.setRecognitionListener(self.stt_listener)
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
        self.recognizer.startListening(intent)

    def stop_listening(self):
        if platform == 'android':
            self._native_stt_stop()

    @run_on_ui_thread
    def _native_stt_stop(self):
        if hasattr(self, 'recognizer') and self.recognizer:
            self.recognizer.stopListening()

    def on_rms_changed(self, rmsdB):
        target = 1.0 + (max(0, rmsdB + 2) / 12.0) * 0.5
        self.orb.audio_scale = self.orb.audio_scale * 0.7 + target * 0.3

    @mainthread
    def on_stt_results_native(self, text, error=None):
        self.orb.audio_scale = 1.0
        if error:
            if self.mic_btn.state == 'down':
                Clock.schedule_once(lambda dt: self.start_listening(), 0.5)
            return
        if text:
            self.add_bubble(text, "user")
            if self.embodiment_state == "BACKGROUND" and "aurora" in text.lower():
                self.set_embodiment_state("SUMMONED")
            if self.systems:
                self._show_thinking()
                self.set_status("Thinking...")
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
        if platform == 'android':
            self.check_overlay_permission()
        self.start_boot_thread()

    def check_overlay_permission(self):
        try:
            from android import api_version
            Settings = autoclass('android.provider.Settings')
            activity = PythonActivity.mActivity
            if not Settings.canDrawOverlays(activity):
                self.add_bubble(
                    "Aurora needs 'Draw over other apps' permission. "
                    "Opening settings in 3 s…", "system")
                def open_settings(dt):
                    Uri    = autoclass('android.net.Uri')
                    _Intent = autoclass('android.content.Intent')
                    i = _Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:" + activity.getPackageName()))
                    activity.startActivity(i)
                Clock.schedule_once(open_settings, 3.0)
        except Exception:
            pass

    def start_boot_thread(self):
        threading.Thread(target=self.boot_aurora_thread, daemon=True).start()

    def boot_aurora_thread(self):
        if not boot_aurora:
            Clock.schedule_once(lambda dt: self.set_status("Aurora Core Not Found"), 0)
            return
        try:
            Clock.schedule_once(lambda dt: self.set_status("Waking Aurora…"), 0)
            self.systems     = boot_aurora(state_dir="aurora_state", verbose=False)
            self._boot_done  = True
            Clock.schedule_once(lambda dt: self.set_status("Aurora is Online"), 0)
            # Drain messages that arrived before boot completed
            pending = list(self._pending_messages)
            self._pending_messages.clear()
            for msg in pending:
                threading.Thread(
                    target=self.process_turn_thread, args=(msg,), daemon=True).start()
            threading.Thread(target=self.autonomy_loop, daemon=True).start()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._boot_done = False
            err = str(e)[:65]
            Clock.schedule_once(lambda dt: self.set_status(f"Boot Failed: {err}"), 0)

    @mainthread
    def set_status(self, text):
        self.status_label.text = text

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------
    def send_message(self, *args):
        user_text = self.text_input.text.strip()
        if not user_text:
            return
        self.add_bubble(user_text, "user")
        self.text_input.text = ""
        if self.systems:
            self._show_thinking()
            self.set_status("Thinking...")
            threading.Thread(
                target=self.process_turn_thread, args=(user_text,), daemon=True).start()
        else:
            self._pending_messages.append(user_text)
            self.add_bubble("I'm still waking up — your message is queued.", "aurora")

    def process_turn_thread(self, user_text):
        # Local voice command fast-path
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
            content    = getattr(resp_A, 'content', '…') if resp_A else '…'
            activation = result.get('noncomp_output', {}).get('axis_activation', {})
            Clock.schedule_once(
                lambda dt: self.on_aurora_response(
                    content, update_orb=True, activation=activation), 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            err = str(e)
            Clock.schedule_once(
                lambda dt: self.on_aurora_response(f"Error: {err}"), 0)

    def on_aurora_response(self, content, update_orb=False, activation=None):
        self._hide_thinking()
        self.add_bubble(content, "aurora")
        self.set_status("Aurora is Online")
        self.orb.set_state("ONLINE")
        if update_orb and activation:
            self.orb.update_state(activation)
        if self.voice_enabled:
            self.orb.set_state("SPEAKING")
            self._broadcast_state_to_overlay("SPEAKING")
            threading.Thread(target=self.speak_thread, args=(content,), daemon=True).start()

    def speak_thread(self, text):
        was_listening = (self.mic_btn.state == 'down')
        if was_listening:
            self.stop_listening()
            self.set_status("Speaking…")
        if tts:
            try:
                tts.speak(text)
                if was_listening:
                    time.sleep(max(1.5, len(text.split()) * 0.5))
            except Exception:
                pass
        resume = "LISTENING" if was_listening else "ONLINE"
        Clock.schedule_once(
            lambda dt: (self.orb.set_state(resume),
                        self._broadcast_state_to_overlay(resume)), 0)
        if was_listening:
            Clock.schedule_once(lambda dt: self.start_listening(), 0.8)

    @mainthread
    def _show_thinking(self):
        if self._thinking_bubble is None:
            self._thinking_bubble = ChatBubble(text="…", sender="aurora")
            self.chat_log.add_widget(self._thinking_bubble)
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
        self.orb.set_state("THINKING")
        self._broadcast_state_to_overlay("THINKING")

    @mainthread
    def _hide_thinking(self):
        if self._thinking_bubble is not None:
            try:
                self.chat_log.remove_widget(self._thinking_bubble)
            except Exception:
                pass
            self._thinking_bubble = None

    @mainthread
    def add_bubble(self, text, sender):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_log.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    # ------------------------------------------------------------------
    # Settings / misc
    # ------------------------------------------------------------------
    def show_settings(self, *args):
        content = BoxLayout(orientation='vertical', padding=12, spacing=10)

        for label_text, attr in [("Voice Synthesis", 'voice_enabled'),
                                  ("Full Autonomy",    'full_autonomy')]:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=42)
            row.add_widget(Label(text=label_text, font_size='15sp'))
            val = getattr(self, attr)
            btn = ToggleButton(
                text="ON" if val else "OFF",
                state='down' if val else 'normal', font_size='15sp')
            btn.bind(on_release=lambda x, a=attr: (
                setattr(self, a, x.state == 'down'),
                setattr(x, 'text', "ON" if x.state == 'down' else "OFF")))
            row.add_widget(btn)
            content.add_widget(row)

        close_btn = Button(text="Close", size_hint_y=None, height=42, font_size='15sp')
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
            self.input_area.height  = 52
            self.input_area.opacity = 1
        else:
            self.input_area.height  = 0
            self.input_area.opacity = 0

    def autonomy_loop(self):
        while True:
            time.sleep(10)
            if not self.systems or not self.full_autonomy:
                continue
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
                                    lambda dt, x=c: self.on_aurora_response(
                                        x, update_orb=True), 0)
            except Exception:
                pass
            if self.live_mode and time.time() - getattr(self, '_last_live_ts', 0) > 45:
                self._perform_live_percept()
                self._last_live_ts = time.time()

    def _perform_live_percept(self):
        try:
            ctx = ("I am observing my environment. [SENSORY_DATA] "
                   "source: mobile_camera observation: steady presence.")
            result = process_external_user_turn(
                self.systems, ctx, source_label="live_mode_sensory")
            resp_A  = result.get('resp_A')
            content = getattr(resp_A, 'content', None) if resp_A else None
            if content and resp_A.confidence > 0.8:
                act = result.get('noncomp_output', {}).get('axis_activation')
                Clock.schedule_once(
                    lambda dt: self.on_aurora_response(
                        content, update_orb=True, activation=act), 0)
        except Exception:
            pass


if __name__ == '__main__':
    AuroraApp().run()
