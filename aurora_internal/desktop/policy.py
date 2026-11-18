"""Action-time boundary around existing desktop tools; no conversational rules."""
from __future__ import annotations

import contextlib
import contextvars
from urllib.parse import urlsplit

_OWNER_ACTION = contextvars.ContextVar("aurora_owner_action", default=False)


@contextlib.contextmanager
def owner_action():
    """Only the authenticated owner console enters this scope, never model kwargs."""
    token = _OWNER_ACTION.set(True)
    try:
        yield
    finally:
        _OWNER_ACTION.reset(token)


class HostPolicy:
    def __init__(self, systems):
        self.systems = systems

    def check(self, name, params):
        # These tools can contact people or execute arbitrary communication.
        # Explicit console actions are user instructions, not autonomous outreach.
        if _OWNER_ACTION.get():
            return ""
        if name in {"mobile_send_sms", "mobile_make_call", "desktop_shell_command", "desktop_macro"}:
            return "explicit_owner_action_required"
        if name == "desktop_browser_action" and params.get("action") not in {"read", "url", "screenshot"}:
            return "explicit_owner_action_required_for_browser_interaction"
        if name in {"desktop_open_url", "mobile_open_url"}:
            url = urlsplit(str(params.get("url") or ""))
            if url.scheme not in {"http", "https"} or url.username or url.password:
                return "passive_http_research_only"
        autonomy = self.systems.get("autonomy")
        if autonomy is not None and (not getattr(autonomy, "running", True) or
                                     getattr(getattr(autonomy, "level", None), "name", "") == "DORMANT"):
            return "autonomy_paused"
        boundaries = getattr(autonomy, "boundaries", None)
        if name == "desktop_file_manager":
            if boundaries is not None and not boundaries.is_path_allowed(str(params.get("path") or "")):
                return "autonomy_path_boundary"
            if params.get("op") not in {"list", "read", "info", "exists"}:
                if not getattr(boundaries, "can_write_files", False):
                    return "autonomous_file_write_disabled"
        if name in {"desktop_system_action", "desktop_process_control", "desktop_launch_app"}:
            if not getattr(boundaries, "can_execute_commands", False):
                return "autonomous_execution_disabled"
        return ""
