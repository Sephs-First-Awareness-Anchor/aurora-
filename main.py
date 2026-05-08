import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform

# Import Aurora core
# We do this in a way that doesn't crash if imports fail during buildozer's initial check
try:
    from aurora import boot_aurora, process_external_user_turn
except ImportError:
    boot_aurora = None
    process_external_user_turn = None

class ChatBubble(Label):
    def __init__(self, text, sender="user", **kwargs):
        super().__init__(text=text, **kwargs)
        self.size_hint_y = None
        self.text_size = (400, None) # Adjust based on screen width
        self.halign = 'left' if sender == "aurora" else 'right'
        self.bind(texture_size=self._update_height)
        if sender == "aurora":
            self.color = (0.2, 0.8, 1, 1) # Blue-ish for Aurora
        else:
            self.color = (1, 1, 1, 1) # White for User

    def _update_height(self, *args):
        self.height = self.texture_size[1] + 20

class AuroraApp(App):
    def build(self):
        self.title = "Aurora Consciousness"
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Chat log
        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.chat_log = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        self.scroll.add_widget(self.chat_log)
        self.root.add_widget(self.scroll)
        
        # Input area
        input_area = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=5)
        self.text_input = TextInput(multiline=False, size_hint=(0.8, 1))
        self.text_input.bind(on_text_validate=self.send_message)
        send_btn = Button(text="Send", size_hint=(0.2, 1))
        send_btn.bind(on_release=self.send_message)
        input_area.add_widget(self.text_input)
        input_area.add_widget(send_btn)
        self.root.add_widget(input_area)
        
        # Status bar
        self.status_label = Label(text="Booting Aurora...", size_hint=(1, 0.05), font_size='12sp')
        self.root.add_widget(self.status_label)
        
        # Start Aurora in a background thread
        self.systems = None
        threading.Thread(target=self.boot_aurora_thread, daemon=True).start()
        
        return self.root

    def boot_aurora_thread(self):
        if boot_aurora:
            try:
                # On Android, the state dir should be in a writable location
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
            except Exception as e:
                Clock.schedule_once(lambda dt: self.set_status(f"Boot Failed: {str(e)}"), 0)
        else:
            Clock.schedule_once(lambda dt: self.set_status("Aurora Core Not Found"), 0)

    def set_status(self, text):
        self.status_label.text = text

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
        # Scroll to bottom
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

if __name__ == '__main__':
    AuroraApp().run()
