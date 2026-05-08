import sys

with open('aurora_desktop_agent.py', 'r') as f:
    content = f.read()

# Add logging to browser start
content = content.replace(
    '            self._page = self._browser.new_page()',
    '            self._page = self._browser.new_page()\\n            with open("aurora_debug.log", "a") as fl: fl.write(f"BROWSER STARTED (headed={headed})\\\\n")'
)

# Add logging to open_url
content = content.replace(
    '                self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)',
    '                with open("aurora_debug.log", "a") as fl: fl.write(f"NAVIGATING TO: {url}\\\\n")\\n                self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)'
)

with open('aurora_desktop_agent.py', 'w') as f:
    f.write(content)
