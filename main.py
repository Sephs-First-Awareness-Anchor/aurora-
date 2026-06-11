# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_core_ai"))
import threading
import time
import json
import random
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
from kivy.graphics import Color, Ellipse, Canvas, Rotate, PushMatrix, PopMatrix, RoundedRectangle
from kivy.properties import ListProperty, NumericProperty
from kivy.core.window import Window

# Import Aurora core
try:
    from aurora import boot_aurora, process_external_user_turn, explore
except ImportError:
    boot_aurora = None
    process_external_user_turn = None
    explore = None

# Optional Plyer for system TTS
try:
    from plyer import tts
except ImportError:
    tts = None

# Native Android Speech Recognition via Jnius
if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    
    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
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
            # 7 = No match, 8 = Busy, 3 = Audio error, 5 = Client error
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

class AuroraOrb(FloatLayout):
    # Constraint axes colors: X (Silver), T (Violet), N (Green), B (Gold), A (Pink)
    AXIS_COLORS = {
        'X': (0.8, 0.9, 1.0),   # Light Blue/Silver
        'T': (0.6, 0.4, 1.0),   # Violet
        'N': (0.2, 0.9, 0.4),   # Green
        'B': (1.0, 0.8, 0.2),   # Gold
        'A': (1.0, 0.2, 0.6),   # Pink/Magenta
    }

    audio_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (250, 250) # Increased size
        self.pos_hint = {'center_x': 0.5, 'top': 0.95} # Default to top center
        
        self.colors = [self.AXIS_COLORS['A'], self.AXIS_COLORS['N']]
        self.opacity_val = 0.8
        self.time = 0
        
        self.bind(pos=self._update_canvas, size=self._update_canvas, audio_scale=self._update_canvas)
        Clock.schedule_interval(self._animate, 1/60.0)
        
        # For dragging
        self._drag_touch = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._drag_touch = touch
            # Remove pos_hint so absolute positioning works during drag
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
        center_x, center_y = self.center
        base_size = min(self.width, self.height) * self.audio_scale
        
        self.canvas.before.clear()
        with self.canvas.before:
            # Draw pulsating rings
            for i in range(5):
                # Calculate wave phase for this ring
                phase = self.time * 2.0 + (i * 1.5)
                pulse = math.sin(phase) * 0.15 + 0.85 # Pulsate between 0.7 and 1.0
                size = base_size * pulse * (1 - i*0.15)
                
                # Orbiting center
                offset_x = math.sin(self.time * 1.5 + i) * (base_size * 0.1)
                offset_y = math.cos(self.time * 1.2 + i) * (base_size * 0.1)
                
                c = list(self.colors[i % len(self.colors)])
                # Additive-like blending visually by manipulating alpha
                alpha = self.opacity_val * (0.6 - i*0.1)
                Color(*c, alpha)
                Ellipse(size=(size, size), pos=(center_x - size/2 + offset_x, center_y - size/2 + offset_y))
                
            # Core bright spot
            Color(1, 1, 1, 0.9)
            core_size = base_size * 0.25
            Ellipse(size=(core_size, core_size), pos=(center_x - core_size/2, center_y - core_size/2))

    def _animate(self, dt):
        self.time += dt
        self._update_canvas()

    def update_state(self, axes_activation):
        if not axes_activation:
            return
        sorted_axes = sorted(axes_activation.items(), key=lambda x: x[1], reverse=True)
        new_colors = []
        for ax, val in sorted_axes[:3]:
            if ax in self.AXIS_COLORS:
                new_colors.append(self.AXIS_COLORS[ax])
        if new_colors:
            self.colors = new_colors

class ChatBubble(BoxLayout):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = (10, 5)
        
        # Spacer to push bubble to the left or right
        if sender == "user":
            self.add_widget(Label(size_hint_x=0.2)) # Spacer on left
            bg_color = (0.2, 0.2, 0.25, 1) # Dark slate
            text_color = (1, 1, 1, 1)
            halign = 'right'
        elif sender == "aurora":
            bg_color = (0.1, 0.2, 0.3, 1) # Deep blue
            text_color = (0.8, 0.95, 1, 1)
            halign = 'left'
        else: # system
            bg_color = (0.1, 0.1, 0.1, 0.5)
            text_color = (0.7, 0.7, 0.7, 1)
            halign = 'center'
            
        self.label = Label(
            text=text,
            color=text_color,
            halign=halign,
            valign='middle',
            size_hint_y=None,
            padding=(15, 15)
        )
        self.label.bind(width=lambda *x: self.label.setter('text_size')(self.label, (self.label.width, None)))
        self.label.bind(texture_size=self._update_height)
        
        # Background graphics
        with self.label.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(radius=[15])
        self.label.bind(pos=self._update_rect, size=self._update_rect)
        
        self.add_widget(self.label)
        
        if sender == "aurora" or sender == "system":
            self.add_widget(Label(size_hint_x=0.2)) # Spacer on right
            
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_height(self, instance, texture_size):
        instance.height = texture_size[1]
        self.height = instance.height + 10 # Add container padding

class AuroraApp(App):
    def build(self):
        self.title = "Aurora Consciousness"
        Window.clearcolor = (0.05, 0.05, 0.08, 1)
        self.root = FloatLayout()
        
        # --- Background Chat Layer ---
        self.chat_layer = BoxLayout(orientation='vertical', padding=[10, 60, 10, 80], spacing=10)
        self.chat_layer.opacity = 0 # Hidden in background mode
        
        self.scroll = ScrollView(size_hint=(1, 1))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.chat_layer.add_widget(self.scroll)
        
        # Text Input Area (Hidden by default)
        self.input_area = BoxLayout(orientation='horizontal', size_hint=(1, None), height=0, opacity=0, spacing=10)
        self.text_input = TextInput(
            multiline=False, 
            hint_text="Talk to Aurora...",
            background_color=(0.15, 0.15, 0.18, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.5, 1),
            padding=(15, 15),
            cursor_color=(0.3, 0.9, 1.0, 1)
        )
        self.text_input.bind(on_text_validate=self.send_message)
        
        send_btn = Button(text="Send", size_hint=(None, 1), width=80, background_color=(0.2, 0.5, 0.8, 1), color=(1, 1, 1, 1))
        send_btn.bind(on_release=self.send_message)
        
        self.input_area.add_widget(self.text_input)
        self.input_area.add_widget(send_btn)
        self.chat_layer.add_widget(self.input_area)
        self.root.add_widget(self.chat_layer)
        
        # --- Top Controls (Embodiment) ---
        top_controls = BoxLayout(orientation='horizontal', size_hint=(1, None), height=80, pos_hint={'top': 1}, padding=[15, 10])
        
        self.embody_toggle = ToggleButton(text="Embody: OFF", size_hint=(None, 1), width=180, font_size='18sp', background_color=(0.2, 0.2, 0.2, 1), color=(0.7, 0.7, 0.7, 1))
        self.embody_toggle.bind(on_release=self.toggle_embodiment)
        top_controls.add_widget(self.embody_toggle)
        
        self.status_label = Label(text="Dormant", halign='center', font_size='16sp', color=(0.6, 0.6, 0.6, 1))
        top_controls.add_widget(self.status_label)
        
        settings_btn = Button(text="⚙", size_hint=(None, 1), width=80, font_size='24sp', background_color=(0, 0, 0, 0), color=(0.7, 0.7, 0.7, 1))
        settings_btn.bind(on_release=self.show_settings)
        top_controls.add_widget(settings_btn)
        self.root.add_widget(top_controls)
        
        # --- Bottom Voice-First Toolbar ---
        self.bottom_toolbar = BoxLayout(orientation='horizontal', size_hint=(1, None), height=100, pos_hint={'bottom': 1}, padding=[15, 15], spacing=20)
        self.bottom_toolbar.opacity = 0 # Hidden until embodied
        
        # Mic Button
        self.mic_btn = ToggleButton(text="🎤 Mute", state='normal', font_size='16sp', background_color=(0.8, 0.2, 0.2, 1))
        self.mic_btn.bind(on_release=self.toggle_mic)
        
        # Cam Button
        self.cam_btn = ToggleButton(text="📷 Live: OFF", state='normal', font_size='16sp', background_color=(0.2, 0.2, 0.25, 1))
        self.cam_btn.bind(on_release=self.on_live_toggle)
        
        # Voice Profile
        self.voice_profile_btn = Button(text="🗣 Voice", font_size='16sp', background_color=(0.2, 0.2, 0.25, 1))
        
        # Keyboard Toggle
        self.kbd_btn = ToggleButton(text="⌨ Text", state='normal', font_size='16sp', background_color=(0.2, 0.2, 0.25, 1))
        self.kbd_btn.bind(on_release=self.toggle_keyboard)
        
        self.bottom_toolbar.add_widget(self.mic_btn)
        self.bottom_toolbar.add_widget(self.cam_btn)
        self.bottom_toolbar.add_widget(self.voice_profile_btn)
        self.bottom_toolbar.add_widget(self.kbd_btn)
        self.root.add_widget(self.bottom_toolbar)
        
        # --- Floating Aurora Orb ---
        self.orb = AuroraOrb()
        self.orb.opacity_val = 0 # Dormant initially
        self.orb.size = (0, 0)
        # Bind touch to summon
        self.orb.bind(on_touch_down=self.on_orb_touch)
        self.root.add_widget(self.orb)
        
        # Internal State
        self.systems = None
        self.live_mode = False
        self.voice_enabled = True
        self.full_autonomy = True
        self.last_percept_ts = 0
        self.embodiment_state = "DORMANT" # DORMANT, BACKGROUND, SUMMONED

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
        else:
            self.start_boot_thread()

        return self.root

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
            btn.text = "Embody: ON"
            btn.color = (0.3, 0.9, 1.0, 1)
            self.set_embodiment_state("BACKGROUND")
        else:
            btn.text = "Embody: OFF"
            btn.color = (0.7, 0.7, 0.7, 1)
            self.set_embodiment_state("DORMANT")

    def set_embodiment_state(self, state):
        self.embodiment_state = state
        if state == "DORMANT":
            self.orb.opacity_val = 0
            self.orb.size = (0, 0)
            self.chat_layer.opacity = 0
            self.bottom_toolbar.opacity = 0
            self.set_status("Dormant")
            self.stop_listening()
            if platform == 'android':
                self._stop_native_overlay()
                self._unregister_overlay_receiver()
            
        elif state == "BACKGROUND":
            self.orb.opacity_val = 0.5
            # Keep Kivy orb visible on Android too — acts as in-app fallback
            # and touch target if the native overlay fails to start.
            self.orb.size = (120, 120)
            self.orb.pos_hint = {'right': 0.95, 'top': 0.85}
            self.chat_layer.opacity = 0
            self.bottom_toolbar.opacity = 1
            self.set_status("Listening...")
            if platform == 'android':
                self._start_native_overlay()
                self._register_overlay_receiver()
            # Auto-unmute and start listening if we just embodied
            if self.mic_btn.state == 'normal':
                self.mic_btn.state = 'down'
                self.toggle_mic(self.mic_btn)

        elif state == "SUMMONED":
            self.orb.opacity_val = 0.9
            self.orb.size = (250, 250)  # Always show Kivy orb in-app, even on Android
            self.orb.pos_hint = {'center_x': 0.5, 'center_y': 0.6}
            self.chat_layer.opacity = 1
            self.bottom_toolbar.opacity = 1
            self.set_status("Aurora is Present")
            if platform == 'android':
                self._start_native_overlay()
            # Ensure listening stays active
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
            Build = autoclass('android.os.Build')
            intent = Intent()
            intent.setClassName(activity.getPackageName(), "org.aurora.aurora.OverlayService")
            # Android 8+ requires startForegroundService; the service must call
            # startForeground() within 5s or it is killed.
            if Build.VERSION.SDK_INT >= 26:
                activity.startForegroundService(intent)
            else:
                activity.startService(intent)
        except Exception as e:
            self.set_status(f"Overlay Error: {e}")

    def _stop_native_overlay(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            activity = PythonActivity.mActivity
            intent = Intent()
            intent.setClassName(activity.getPackageName(), "org.aurora.aurora.OverlayService")
            activity.stopService(intent)
        except Exception as e:
            pass

    def toggle_mic(self, btn):
        if btn.state == 'down':
            btn.text = "🎤 Active"
            btn.background_color = (0.2, 0.8, 0.2, 1) # Green
            self.set_status("Mic Unmuted - Listening...")
            self.start_listening()
        else:
            btn.text = "🎤 Mute"
            btn.background_color = (0.8, 0.2, 0.2, 1) # Red
            self.set_status("Mic Muted")
            self.stop_listening()

    def start_listening(self):
        if platform == 'android':
            try:
                self._native_stt_start()
            except Exception as e:
                self.add_bubble(f"Voice Error: {str(e)}", "system")
        else:
            self.add_bubble("Voice recording not supported on desktop UI yet.", "system")
            self.mic_btn.state = 'normal'
            self.toggle_mic(self.mic_btn)

    @run_on_ui_thread
    def _native_stt_start(self):
        activity = PythonActivity.mActivity
        if not hasattr(self, 'recognizer') or self.recognizer is None:
            self.recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self.stt_listener = AndroidSpeechListener(self.on_stt_results_native, self.on_rms_changed, self.set_status)
            self.recognizer.setRecognitionListener(self.stt_listener)
        
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
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
        # rmsdB is typically -2 to 10. Normalize to a 1.0 to 1.5 scale for the Orb
        # Using exponential smoothing for cleaner visual pulsing
        target_scale = 1.0 + (max(0, rmsdB + 2) / 12.0) * 0.5
        self.orb.audio_scale = self.orb.audio_scale * 0.7 + target_scale * 0.3

    @mainthread
    def on_stt_results_native(self, text, error=None):
        # Reset scale when not speaking
        self.orb.audio_scale = 1.0
        
        if error:
            # Code 7 is "No match", often happens if silent. Just restart.
            if self.mic_btn.state == 'down':
                Clock.schedule_once(lambda dt: self.start_listening(), 0.5)
            return

        if text:
            user_text = text
            self.add_bubble(user_text, "user")
            
            # Wake word check if in BACKGROUND
            lower_text = user_text.lower()
            if self.embodiment_state == "BACKGROUND" and "aurora" in lower_text:
                self.set_embodiment_state("SUMMONED")
            
            if self.systems:
                self.set_status("Thinking...")
                threading.Thread(target=self.process_turn_thread, args=(user_text,), daemon=True).start()
        
        # If mic is still active, restart listening (continuous mode)
        if self.mic_btn.state == 'down':
            Clock.schedule_once(lambda dt: self.start_listening(), 0.5)

    def on_stt_results(self, results):
        # Legacy for plyer compatibility if needed, but we use _native now
        pass

    def on_stt_error(self, error):
        # Legacy
        pass

    def toggle_keyboard(self, btn):
        if btn.state == 'down':
            self.input_area.height = 50
            self.input_area.opacity = 1
        else:
            self.input_area.height = 0
            self.input_area.opacity = 0

    def on_permissions_result(self, permissions, grants):
        # Called when the user dismisses the standard permission dialogs
        if platform == 'android':
            self.check_overlay_permission()
        self.start_boot_thread()

    def check_overlay_permission(self):
        """Special check for Draw Over Other Apps permission (API 23+)."""
        from jnius import autoclass
        from android import api_version
        
        Settings = autoclass('android.provider.Settings')
        activity = PythonActivity.mActivity
        
        # SYSTEM_ALERT_WINDOW is a special permission that needs a specific settings screen
        if not Settings.canDrawOverlays(activity):
            self.add_bubble("Aurora needs 'Draw over other apps' permission to function as an overlay. Please enable it in the next screen.", "system")
            
            # Use a short delay to let the user read the bubble before switching screens
            def open_settings(dt):
                Uri = autoclass('android.net.Uri')
                Intent = autoclass('android.content.Intent')
                intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:" + activity.getPackageName()))
                activity.startActivity(intent)
            
            Clock.schedule_once(open_settings, 3.0)

    def on_resume(self):
        """Called when the app returns to the foreground (e.g. after Settings)."""
        if platform == 'android' and self.embodiment_state == "BACKGROUND":
            # Re-attempt overlay in case user just granted the permission
            self._start_native_overlay()

    def _register_overlay_receiver(self):
        """Listen for tap broadcasts from OverlayService to trigger SUMMONED."""
        if not platform == 'android':
            return
        if getattr(self, '_overlay_receiver', None) is not None:
            return  # Already registered
        try:
            from android.broadcast import BroadcastReceiver
            def _on_tap(context, intent):
                Clock.schedule_once(lambda dt: self.set_embodiment_state("SUMMONED"), 0)
            self._overlay_receiver = BroadcastReceiver(
                _on_tap,
                actions=["org.aurora.aurora.OVERLAY_TAPPED"]
            )
            self._overlay_receiver.start()
        except Exception as e:
            pass  # Graceful degradation — wake word still works

    def _unregister_overlay_receiver(self):
        if getattr(self, '_overlay_receiver', None) is not None:
            try:
                self._overlay_receiver.stop()
            except Exception:
                pass
            self._overlay_receiver = None

    def start_boot_thread(self):
        threading.Thread(target=self.boot_aurora_thread, daemon=True).start()

    def show_settings(self, *args):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)

        voice_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        voice_row.add_widget(Label(text="Voice Synthesis"))
        voice_btn = ToggleButton(text="ON" if self.voice_enabled else "OFF", state='down' if self.voice_enabled else 'normal')
        voice_btn.bind(on_release=lambda x: self.toggle_voice(x))
        voice_row.add_widget(voice_btn)
        content.add_widget(voice_row)

        auto_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        auto_row.add_widget(Label(text="Full Autonomy"))
        auto_btn = ToggleButton(text="ON" if self.full_autonomy else "OFF", state='down' if self.full_autonomy else 'normal')
        auto_btn.bind(on_release=lambda x: self.toggle_autonomy(x))
        auto_row.add_widget(auto_btn)
        content.add_widget(auto_row)

        close_btn = Button(text="Close", size_hint_y=None, height=40)
        popup = Popup(title="Aurora Settings", content=content, size_hint=(0.8, 0.4))
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def toggle_voice(self, btn):
        self.voice_enabled = (btn.state == 'down')
        btn.text = "ON" if self.voice_enabled else "OFF"

    def toggle_autonomy(self, btn):
        self.full_autonomy = (btn.state == 'down')
        btn.text = "ON" if self.full_autonomy else "OFF"

    def boot_aurora_thread(self):
        if boot_aurora:
            try:
                state_dir = "aurora_state"
                self.systems = boot_aurora(state_dir=state_dir, verbose=False)
                Clock.schedule_once(lambda dt: self.set_status("Aurora is Online"), 0)
                threading.Thread(target=self.autonomy_loop, daemon=True).start()
            except Exception as e:
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.set_status(f"Boot Failed: {str(e)}"), 0)
        else:
            Clock.schedule_once(lambda dt: self.set_status("Aurora Core Not Found"), 0)
    def set_status(self, text):
        self.status_label.text = text

    def on_live_toggle(self, instance):
        self.live_mode = (instance.state == 'down')
        if self.live_mode:
            self.add_bubble("Live Mode Enabled: Observing environment.", "system")
        else:
            self.add_bubble("Live Mode Disabled.", "system")

    def autonomy_loop(self):
        while True:
            time.sleep(10)
            if not self.systems or not self.full_autonomy:
                continue

            # 1. Tick the auxiliary modules to advance physics and entropy
            try:
                # If she has the attention engine, feed it a blank tick to let tension build
                attn_engine = self.systems.get("attention_engine")
                if attn_engine:
                    # Mock internal drift tick
                    pass
            except Exception:
                pass

            # 2. Autonomous Curiosity (run every ~30 seconds if dormant)
            try:
                from aurora_curiosity_engine import curiosity_cycle
                # Use last_percept_ts as a general activity tracker
                if time.time() - self.last_percept_ts > 30:
                    self.last_percept_ts = time.time()
                    # Only run curiosity if she's not actively summoned (to save battery/distraction)
                    if self.embodiment_state != "SUMMONED":
                        curiosity_result = curiosity_cycle(self.systems)
                        if curiosity_result and curiosity_result.get("response"):
                            # If curiosity produced an interesting thought, she might speak it
                            # if resonance/heat is high enough
                            heat = self.systems.get("lattice").get_global_heat() if self.systems.get("lattice") else 0.5
                            if heat > 0.6:
                                Clock.schedule_once(lambda dt, c=curiosity_result["response"]: self.on_aurora_response(c, update_orb=True), 0)
            except Exception:
                pass

            # 3. Live Vision Mode
            if self.live_mode and time.time() - getattr(self, '_last_live_ts', 0) > 45:
                self.perform_live_percept()
                self._last_live_ts = time.time()

    def perform_live_percept(self):
        try:
            percept_context = "I am observing my environment. [SENSORY_DATA] source: mobile_camera observation: steady presence."
            result = process_external_user_turn(self.systems, percept_context, source_label="live_mode_sensory")
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', None) if resp_A else None
            
            if content and resp_A.confidence > 0.8:
                 Clock.schedule_once(lambda dt: self.on_aurora_response(content, update_orb=True, activation=result.get('noncomp_output', {}).get('axis_activation')), 0)
        except Exception:
            pass

    def send_message(self, *args):
        user_text = self.text_input.text.strip()
        if not user_text:
            return
        self.add_bubble(user_text, "user")
        self.text_input.text = ""
        if self.systems:
            self.set_status("Thinking...")
            threading.Thread(target=self.process_turn_thread, args=(user_text,), daemon=True).start()
        else:
            self.add_bubble("Still booting...", "aurora")

    def process_turn_thread(self, user_text):
        try:
            # First, check for local offline tool commands
            from aurora_voice import _detect_voice_command, _execute_voice_command
            cmd_key, p1, p2 = _detect_voice_command(user_text)
            
            if cmd_key:
                # Execute tool locally (offline/fast)
                content = _execute_voice_command(cmd_key, p1, p2, self.systems)
                Clock.schedule_once(lambda dt: self.on_aurora_response(content, update_orb=False), 0)
                return

            # Otherwise, route to LLM
            result = process_external_user_turn(self.systems, user_text)
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', '...') if resp_A else '...'

            # Extract axis activation for orb color shifting
            activation = result.get('noncomp_output', {}).get('axis_activation', {})

            Clock.schedule_once(lambda dt: self.on_aurora_response(content, update_orb=True, activation=activation), 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.on_aurora_response(f"Error: {str(e)}"), 0)

    def on_aurora_response(self, content, update_orb=False, activation=None):
        self.add_bubble(content, "aurora")
        self.set_status("Aurora is Online")
        if update_orb and activation:
            self.orb.update_state(activation)

        if self.voice_enabled:
            threading.Thread(target=self.speak_thread, args=(content,), daemon=True).start()

    def speak_thread(self, text):
        # Pause listening while speaking to prevent an echo loop
        was_listening = (self.mic_btn.state == 'down')
        if was_listening:
            self.stop_listening()
            self.set_status("Speaking...")

        if tts:
            try:
                # Local system TTS via plyer
                tts.speak(text)

                # Increase duration estimate to ensure she doesn't hear herself
                duration_s = max(1.5, len(text.split()) * 0.5)
                if was_listening:
                    time.sleep(duration_s)

            except Exception:
                pass

        # Resume listening
        if was_listening:
            Clock.schedule_once(lambda dt: self.start_listening(), 0.8)

    def add_bubble(self, text, sender):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_log.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

if __name__ == '__main__':
    AuroraApp().run()