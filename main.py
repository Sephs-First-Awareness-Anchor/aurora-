import os
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
from kivy.clock import Clock
from kivy.utils import platform
from kivy.graphics import Color, Ellipse, Canvas, Rotate, PushMatrix, PopMatrix
from kivy.properties import ListProperty, NumericProperty

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

class AuroraOrb(BoxLayout):
    # Constraint axes colors: X (Silver), T (Violet), N (Green), B (Gold), A (Pink)
    AXIS_COLORS = {
        'X': (0.8, 0.9, 1.0),   # Light Blue/Silver
        'T': (0.6, 0.4, 1.0),   # Violet
        'N': (0.2, 0.9, 0.4),   # Green
        'B': (1.0, 0.8, 0.2),   # Gold
        'A': (1.0, 0.2, 0.6),   # Pink/Magenta
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, 0.3)
        self.colors = [self.AXIS_COLORS['A'], self.AXIS_COLORS['N']] # Initial
        self.opacity_val = 0.6
        self.angle = 0
        
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=0, origin=self.center)
            # We'll draw several layers of ellipses with different offsets and colors
            self.layers = []
            for i in range(4):
                layer_color = Color(*self.colors[i % len(self.colors)], self.opacity_val)
                self.layers.append(layer_color)
                Ellipse(size=(100, 100), pos=(0, 0)) # Placeholder pos, updated in bind
            PopMatrix()

        self.bind(pos=self._update_canvas, size=self._update_canvas)
        Clock.schedule_interval(self._animate, 1/30.0)

    def _update_canvas(self, *args):
        self.rot.origin = self.center
        center_x, center_y = self.center
        base_size = min(self.width, self.height) * 0.8
        
        self.canvas.before.clear()
        with self.canvas.before:
            PushMatrix()
            Rotate(angle=self.angle, origin=self.center)
            for i in range(4):
                offset_x = math.sin(self.angle/50.0 + i) * 20
                offset_y = math.cos(self.angle/40.0 + i) * 20
                size = base_size * (1 - i*0.1)
                
                # Blend colors based on current "mood"
                c = list(self.colors[i % len(self.colors)])
                Color(*c, self.opacity_val * (1 - i*0.15))
                Ellipse(size=(size, size), pos=(center_x - size/2 + offset_x, center_y - size/2 + offset_y))
            PopMatrix()

    def _animate(self, dt):
        self.angle += 1
        self._update_canvas()

    def update_state(self, axes_activation):
        """Update orb colors based on 5-axis activation."""
        if not axes_activation:
            return
            
        # Sort axes by activation level
        sorted_axes = sorted(axes_activation.items(), key=lambda x: x[1], reverse=True)
        new_colors = []
        for ax, val in sorted_axes[:3]:
            if ax in self.AXIS_COLORS:
                new_colors.append(self.AXIS_COLORS[ax])
        
        if new_colors:
            self.colors = new_colors

class ChatBubble(Label):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(text=text, **kwargs)
        self.size_hint_y = None
        self.text_size = (400, None)
        self.halign = 'left' if sender == "aurora" else 'right'
        self.valign = 'middle'
        self.padding = (15, 15)
        self.bind(texture_size=self._update_height)
        if sender == "aurora":
            self.color = (0.3, 0.9, 1.0, 1) # Brighter Aurora Blue
        elif sender == "system":
            self.color = (0.5, 0.5, 0.5, 1)
            self.font_size = '11sp'
        else:
            self.color = (1, 1, 1, 1)

    def _update_height(self, *args):
        self.height = max(50, self.texture_size[1] + 30)

class AuroraApp(App):
    def build(self):
        self.title = "Aurora Consciousness"
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Orb Visualization
        self.orb = AuroraOrb()
        self.root.add_widget(self.orb)
        
        # Header / Status
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.05), spacing=10)
        self.status_label = Label(text="Booting...", halign='left', size_hint=(0.4, 1))
        self.status_label.bind(size=self.status_label.setter('text_size'))
        header.add_widget(self.status_label)
        
        self.live_toggle = ToggleButton(text="Live", size_hint=(0.2, 1))
        self.live_toggle.bind(on_release=self.on_live_toggle)
        header.add_widget(self.live_toggle)
        
        settings_btn = Button(text="Settings", size_hint=(0.2, 1))
        settings_btn.bind(on_release=self.show_settings)
        header.add_widget(settings_btn)
        self.root.add_widget(header)
        
        # Chat log
        self.scroll = ScrollView(size_hint=(1, 0.55))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.root.add_widget(self.scroll)
        
        # Input area
        input_area = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=5)
        self.text_input = TextInput(multiline=False, size_hint=(0.8, 1), hint_text="Talk to Aurora...")
        self.text_input.bind(on_text_validate=self.send_message)
        send_btn = Button(text="Send", size_hint=(0.2, 1))
        send_btn.bind(on_release=self.send_message)
        input_area.add_widget(self.text_input)
        input_area.add_widget(send_btn)
        self.root.add_widget(input_area)
        
        # Internal State
        self.systems = None
        self.live_mode = False
        self.voice_enabled = True
        self.full_autonomy = True
        self.last_percept_ts = 0

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.ACCESS_FINE_LOCATION,
            ], self.on_permissions_result)
        else:
            self.start_boot_thread()

        return self.root

    def on_permissions_result(self, permissions, grants):
        # Called when the user dismisses the permission dialogs
        self.start_boot_thread()

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
                
            if self.live_mode and time.time() - self.last_percept_ts > 45:
                self.perform_live_percept()
                self.last_percept_ts = time.time()

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
            result = process_external_user_turn(self.systems, user_text)
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', '...') if resp_A else '...'
            
            # Extract axis activation for orb color shifting
            activation = result.get('noncomp_output', {}).get('axis_activation', {})
            
            Clock.schedule_once(lambda dt: self.on_aurora_response(content, update_orb=True, activation=activation), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_aurora_response(f"Error: {str(e)}"), 0)

    def on_aurora_response(self, content, update_orb=False, activation=None):
        self.add_bubble(content, "aurora")
        self.set_status("Aurora is Online")
        if update_orb and activation:
            self.orb.update_state(activation)
        
        if self.voice_enabled:
            threading.Thread(target=self.speak_thread, args=(content,), daemon=True).start()

    def speak_thread(self, text):
        if tts:
            try:
                # Local system TTS via plyer
                tts.speak(text)
            except Exception:
                pass
        else:
            # Fallback to edge-tts if internet is available and ffplay is present
            # but on Android, system TTS is preferred.
            pass

    def add_bubble(self, text, sender):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_log.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

if __name__ == '__main__':
    AuroraApp().run()
