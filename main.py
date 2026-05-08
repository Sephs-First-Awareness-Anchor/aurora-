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

class AuroraOrb(FloatLayout):
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
        self.size_hint = (None, None)
        self.size = (150, 150)
        self.pos_hint = {'center_x': 0.5, 'top': 0.95} # Default to top center
        
        self.colors = [self.AXIS_COLORS['A'], self.AXIS_COLORS['N']]
        self.opacity_val = 0.8
        self.time = 0
        
        self.bind(pos=self._update_canvas, size=self._update_canvas)
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
        base_size = min(self.width, self.height)
        
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
        
        # Set a dark modern background
        Window.clearcolor = (0.05, 0.05, 0.08, 1)
        
        # Root is a FloatLayout for overlays
        self.root = FloatLayout()
        
        # Main background container (Chat + Input)
        main_layout = BoxLayout(orientation='vertical', padding=[10, 60, 10, 10], spacing=10)
        
        # Chat log
        self.scroll = ScrollView(size_hint=(1, 1))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        main_layout.add_widget(self.scroll)
        
        # Input area styling
        input_area = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, spacing=10)
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
        
        send_btn = Button(
            text="Send", 
            size_hint=(None, 1), 
            width=80,
            background_color=(0.2, 0.5, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        send_btn.bind(on_release=self.send_message)
        
        input_area.add_widget(self.text_input)
        input_area.add_widget(send_btn)
        main_layout.add_widget(input_area)
        
        # Add main layout to root (bottom layer)
        self.root.add_widget(main_layout)
        
        # Floating Status / Settings controls
        controls_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, pos_hint={'top': 1})
        
        settings_btn = Button(
            text="⚙ Settings", 
            size_hint=(None, 1), 
            width=100,
            background_color=(0, 0, 0, 0), # Transparent
            color=(0.7, 0.7, 0.7, 1)
        )
        settings_btn.bind(on_release=self.show_settings)
        controls_layout.add_widget(settings_btn)
        
        self.status_label = Label(text="Booting...", halign='center', color=(0.6, 0.6, 0.6, 1))
        controls_layout.add_widget(self.status_label)
        
        self.live_toggle = ToggleButton(
            text="Live: OFF", 
            size_hint=(None, 1), 
            width=100,
            background_color=(0, 0, 0, 0),
            color=(0.7, 0.7, 0.7, 1)
        )
        self.live_toggle.bind(on_release=self.on_live_toggle)
        controls_layout.add_widget(self.live_toggle)
        
        self.root.add_widget(controls_layout) # Add controls above chat
        
        # Floating Aurora Orb (Top layer)
        self.orb = AuroraOrb()
        self.root.add_widget(self.orb)
        
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
