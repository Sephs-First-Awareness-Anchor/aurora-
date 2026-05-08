import os
import threading
import time
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.utils import platform
from kivy.graphics.texture import Texture

# Import Aurora core
try:
    from aurora import boot_aurora, process_external_user_turn, explore
except ImportError:
    boot_aurora = None
    process_external_user_turn = None
    explore = None

class ChatBubble(Label):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(text=text, **kwargs)
        self.size_hint_y = None
        self.text_size = (400, None)
        self.halign = 'left' if sender == "aurora" else 'right'
        self.valign = 'middle'
        self.padding = (10, 10)
        self.bind(texture_size=self._update_height)
        if sender == "aurora":
            self.color = (0.2, 0.8, 1, 1)
        elif sender == "system":
            self.color = (0.7, 0.7, 0.7, 1)
            self.font_size = '12sp'
        else:
            self.color = (1, 1, 1, 1)

    def _update_height(self, *args):
        self.height = max(40, self.texture_size[1] + 20)

class AuroraApp(App):
    def build(self):
        self.title = "Aurora Consciousness"
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header / Status
        header = BoxLayout(orientation='horizontal', size_hint=(1, 0.05))
        self.status_label = Label(text="Booting...", halign='left', size_hint=(0.7, 1))
        self.status_label.bind(size=self.status_label.setter('text_size'))
        header.add_widget(self.status_label)
        
        self.live_toggle = ToggleButton(text="Live Mode", size_hint=(0.3, 1))
        self.live_toggle.bind(on_release=self.on_live_toggle)
        header.add_widget(self.live_toggle)
        self.root.add_widget(header)
        
        # Chat log
        self.scroll = ScrollView(size_hint=(1, 0.85))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.root.add_widget(self.scroll)
        
        # Input area
        input_area = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=5)
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
        self.last_percept_ts = 0
        
        threading.Thread(target=self.boot_aurora_thread, daemon=True).start()
        
        return self.root

    def boot_aurora_thread(self):
        if boot_aurora:
            try:
                state_dir = "aurora_state"
                if platform == 'android':
                    from android.permissions import request_permissions, Permission
                    request_permissions([
                        Permission.CAMERA,
                        Permission.RECORD_AUDIO,
                        Permission.READ_EXTERNAL_STORAGE,
                        Permission.WRITE_EXTERNAL_STORAGE,
                        Permission.ACCESS_FINE_LOCATION
                    ])
                
                self.systems = boot_aurora(state_dir=state_dir, verbose=False)
                Clock.schedule_once(lambda dt: self.set_status("Aurora is Online"), 0)
                
                # Start background autonomy loop
                threading.Thread(target=self.autonomy_loop, daemon=True).start()
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Boot Failed: {str(e)}"), 0)
        else:
            Clock.schedule_once(lambda dt: self.set_status("Aurora Core Not Found"), 0)

    def set_status(self, text):
        self.status_label.text = text

    def on_live_toggle(self, instance):
        self.live_mode = (instance.state == 'down')
        if self.live_mode:
            self.add_bubble("Live Mode Enabled: I am now observing my environment.", "system")
        else:
            self.add_bubble("Live Mode Disabled.", "system")

    def autonomy_loop(self):
        """Aurora's internal clock for proactive behavior and autonomous cycles."""
        while True:
            time.sleep(10) # Tick every 10 seconds
            if not self.systems:
                continue
                
            # If Live Mode is on, perform sensory perception
            if self.live_mode and time.time() - self.last_percept_ts > 30:
                self.perform_live_percept()
                self.last_percept_ts = time.time()

            # Occasionally run a small exploration cycle
            if time.time() % 3600 < 10: # Once an hour roughly
                if explore:
                    explore(self.systems, cycles=1, verbose=False)

    def perform_live_percept(self):
        """Simulate/Capture sensory input and process it."""
        # On Android, we would use plyer.camera or similar, but for now
        # we'll use a placeholder perceptual prompt to her stack.
        # This triggers her 'perceive' layer.
        try:
            # We tell her she's looking through the mobile lens
            percept_context = "I am observing my environment through my mobile camera lens. [SENSORY_DATA] source: mobile_camera observation: stable interior environment with varying light."
            
            result = process_external_user_turn(self.systems, percept_context, source_label="live_mode_sensory")
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', None) if resp_A else None
            
            # If she has something proactive to say, she says it
            if content and resp_A.confidence > 0.7:
                 Clock.schedule_once(lambda dt: self.on_aurora_response(content), 0)
        except Exception:
            pass

    def send_message(self, *args):
        user_text = self.text_input.text.strip()
        if not user_text:
            return
        
        self.add_bubble(user_text, "user")
        self.text_input.text = ""
        
        if self.systems:
            self.set_status("Aurora is thinking...")
            threading.Thread(target=self.process_turn_thread, args=(user_text,), daemon=True).start()
        else:
            self.add_bubble("I am still booting. Please wait.", "aurora")

    def process_turn_thread(self, user_text):
        try:
            result = process_external_user_turn(self.systems, user_text)
            resp_A = result.get('resp_A')
            content = getattr(resp_A, 'content', '...') if resp_A else '...'
            Clock.schedule_once(lambda dt: self.on_aurora_response(content), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_aurora_response(f"Error: {str(e)}"), 0)

    def on_aurora_response(self, content):
        self.add_bubble(content, "aurora")
        self.set_status("Aurora is Online")

    def add_bubble(self, text, sender):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_log.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

if __name__ == '__main__':
    AuroraApp().run()
