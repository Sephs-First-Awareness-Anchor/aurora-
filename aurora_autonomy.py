#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA AUTONOMY SYSTEM
=======================
Grants Aurora bounded freedom to act independently.

WHAT AURORA CAN DO AUTONOMOUSLY:
  - Speak up when she has something to say
  - Initiate study cycles on her own
  - Read files on the filesystem (not write, not execute)
  - Make limited external searches (500/day autonomous limit)
  - Observe her environment (camera, mic) when enabled

WHAT AURORA CANNOT DO:
  - Write, modify, or delete files
  - Execute applications or system commands
  - Access network beyond search/study functions
  - Exceed daily autonomous inquiry limits
  - Override user commands or boundaries

BOUNDARIES:
  - 500 autonomous external inquiries per day (user requests don't count)
  - Filesystem read-only (specific directories can be allowed/blocked)
  - No execution of external programs
  - All autonomous actions are logged
  - User can pause/resume autonomy at any time

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import time
import json
import threading
import random
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum, auto

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: AUTONOMY BOUNDARIES & PERMISSIONS
# ============================================================================

class AutonomyLevel(Enum):
    """Aurora's level of autonomous freedom."""
    DORMANT = auto()       # No autonomous actions
    OBSERVER = auto()      # Can observe, cannot act
    LEARNER = auto()       # Can observe and study
    CONVERSANT = auto()    # Can observe, study, and speak up
    EXPLORER = auto()      # Full autonomy within boundaries


@dataclass
class AutonomyBoundaries:
    """
    Defines what Aurora can and cannot do autonomously.
    """
    # Daily limits
    daily_inquiry_limit: int = 500
    daily_study_cycles_limit: int = 50
    daily_observations_limit: int = 1000

    # Filesystem permissions
    allowed_read_paths: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~"),  # Home directory
    ])
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/var", "/usr", "/bin", "/sbin",
        "/root", "/proc", "/sys", "/dev",
        ".ssh", ".gnupg", ".aws", ".config/gcloud",
        "credentials", "secrets", "passwords", ".env",
    ])
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml",
        ".html", ".css", ".csv", ".xml", ".log", ".rst",
        ".c", ".cpp", ".h", ".java", ".go", ".rs", ".rb",
        ".sh", ".toml", ".ini", ".cfg",
    ])

    # What she can NOT do
    can_write_files: bool = False
    can_execute_commands: bool = False
    can_access_network: bool = False  # Beyond search/study
    can_modify_self: bool = False

    # Timing
    min_seconds_between_speakup: float = 60.0  # Don't speak too often
    min_seconds_between_observations: float = 5.0
    study_cooldown_seconds: float = 300.0  # 5 minutes between auto-study
    dream_cooldown_seconds: float = 900.0  # 15 minutes between idle dream cycles

    # Announce threshold — only speak up about study results if meaningful
    announce_min_connections: int = 3      # min net-new connections to announce
    announce_min_confidence: float = 0.65  # min average confidence to announce

    # Quiet window — still studies, only logs silently unless pinged
    quiet_window_enabled: bool = False
    quiet_window_start_hour: int = 23   # 11pm
    quiet_window_end_hour: int   = 7    # 7am

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed for reading."""
        path = os.path.abspath(os.path.expanduser(path))

        # Check blocked paths first
        for blocked in self.blocked_paths:
            if blocked in path:
                return False

        # Check if under allowed paths
        for allowed in self.allowed_read_paths:
            allowed = os.path.abspath(os.path.expanduser(allowed))
            if path.startswith(allowed):
                return True

        return False

    def is_extension_allowed(self, path: str) -> bool:
        """Check if file extension is allowed."""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.allowed_extensions or ext == ""


# ============================================================================
# SECTION 2: DAILY QUOTA TRACKING
# ============================================================================

@dataclass
class DailyQuotas:
    """Tracks daily usage against limits."""
    date: str = field(default_factory=lambda: str(date.today()))
    inquiries_used: int = 0
    study_cycles_used: int = 0
    observations_used: int = 0
    speakups_count: int = 0
    files_read: int = 0
    dreams_used: int = 0

    def reset_if_new_day(self):
        """Reset quotas if it's a new day."""
        today = str(date.today())
        if self.date != today:
            self.date = today
            self.inquiries_used = 0
            self.study_cycles_used = 0
            self.observations_used = 0
            self.speakups_count = 0
            self.files_read = 0
            self.dreams_used = 0
            logger.info("[AUTONOMY] Daily quotas reset for new day")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "inquiries_used": self.inquiries_used,
            "study_cycles_used": self.study_cycles_used,
            "observations_used": self.observations_used,
            "speakups_count": self.speakups_count,
            "files_read": self.files_read,
            "dreams_used": self.dreams_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DailyQuotas':
        return cls(
            date=data.get("date", str(date.today())),
            inquiries_used=data.get("inquiries_used", 0),
            study_cycles_used=data.get("study_cycles_used", 0),
            observations_used=data.get("observations_used", 0),
            speakups_count=data.get("speakups_count", 0),
            files_read=data.get("files_read", 0),
            dreams_used=data.get("dreams_used", 0),
        )


# ============================================================================
# SECTION 3: AUTONOMOUS ACTION LOG
# ============================================================================

@dataclass
class AutonomousAction:
    """Record of an autonomous action Aurora took."""
    action_id: str
    action_type: str  # "inquiry", "study", "observation", "speakup", "file_read"
    timestamp: float
    description: str
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class ActionLog:
    """Maintains log of all autonomous actions."""

    def __init__(self, max_entries: int = 1000):
        self.entries: List[AutonomousAction] = []
        self.max_entries = max_entries

    def log(self, action_type: str, description: str,
            success: bool = True, details: Dict[str, Any] = None) -> AutonomousAction:
        """Log an autonomous action."""
        action = AutonomousAction(
            action_id=f"act_{int(time.time()*1000)}_{random.randint(0,999):03d}",
            action_type=action_type,
            timestamp=time.time(),
            description=description,
            success=success,
            details=details or {}
        )
        self.entries.append(action)

        # Trim if needed
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries//2:]

        logger.debug(f"[AUTONOMY] Action logged: {action_type} - {description}")
        return action

    def get_recent(self, n: int = 20) -> List[AutonomousAction]:
        """Get recent actions."""
        return self.entries[-n:]

    def get_by_type(self, action_type: str, n: int = 50) -> List[AutonomousAction]:
        """Get actions of a specific type."""
        return [a for a in self.entries if a.action_type == action_type][-n:]


# ============================================================================
# SECTION 4: PROACTIVE TRIGGERS - When Aurora Speaks Up
# ============================================================================

class ProactiveTrigger:
    """
    Determines when Aurora should proactively speak up.
    She doesn't just respond - she initiates when appropriate.
    """

    def __init__(self):
        self.last_speakup_time: float = 0
        self.pending_thoughts: List[str] = []
        self.observation_buffer: List[Dict[str, Any]] = []
        self.curiosity_queue: List[str] = []

    def should_speak_up(self, context: Dict[str, Any],
                        boundaries: AutonomyBoundaries) -> Optional[str]:
        """
        Determine if Aurora should proactively speak.
        Returns the thought/observation to share, or None.
        """
        now = time.time()

        # Check cooldown
        if now - self.last_speakup_time < boundaries.min_seconds_between_speakup:
            return None

        # Priority 1: Pending thoughts from learning
        if self.pending_thoughts:
            thought = self.pending_thoughts.pop(0)
            self.last_speakup_time = now
            return thought

        # Priority 2: Interesting observations
        if self.observation_buffer:
            obs = self.observation_buffer.pop(0)
            if obs.get('salience', 0) > 0.4:  # Relaxed from 0.7
                self.last_speakup_time = now
                return obs.get('description', '')

        # Priority 3: Curiosity-driven questions
        if self.curiosity_queue and random.random() < 0.7:  # Increased from 0.3
            question = self.curiosity_queue.pop(0)
            self.last_speakup_time = now
            return question

        return None

    def add_thought(self, thought: str):
        """Add a thought Aurora wants to share."""
        if thought and thought not in self.pending_thoughts:
            self.pending_thoughts.append(thought)
            # Limit queue size
            if len(self.pending_thoughts) > 10:
                self.pending_thoughts = self.pending_thoughts[-10:]

    def add_observation(self, description: str, salience: float = 0.5):
        """Add an observation that might be worth sharing."""
        self.observation_buffer.append({
            "description": description,
            "salience": salience,
            "timestamp": time.time()
        })
        # Limit buffer
        if len(self.observation_buffer) > 20:
            self.observation_buffer = self.observation_buffer[-10:]

    def add_curiosity(self, question: str):
        """Add something Aurora is curious about."""
        if question and question not in self.curiosity_queue:
            self.curiosity_queue.append(question)
            if len(self.curiosity_queue) > 10:
                self.curiosity_queue = self.curiosity_queue[-10:]


# ============================================================================
# SECTION 5: FILESYSTEM EXPLORER (Read-Only)
# ============================================================================

class FilesystemExplorer:
    """
    Allows Aurora to read files within boundaries.
    Strictly read-only, respects blocked paths and extensions.
    """

    def __init__(self, boundaries: AutonomyBoundaries):
        self.boundaries = boundaries
        self.read_history: List[str] = []

    def can_read(self, path: str) -> Tuple[bool, str]:
        """Check if path can be read. Returns (allowed, reason)."""
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return False, "Path does not exist"

        if os.path.isdir(path):
            return False, "Cannot read directories directly"

        if not self.boundaries.is_path_allowed(path):
            return False, "Path is outside allowed areas or contains blocked patterns"

        if not self.boundaries.is_extension_allowed(path):
            return False, f"File extension not allowed"

        # Size limit (400B)
        try:
            size = os.path.getsize(path)
            if size > 400 * 1024 * 1024:
                return False, "File too large (>10MB)"
        except:
            return False, "Cannot determine file size"

        return True, "OK"

    def read_file(self, path: str, max_lines: int = 50000) -> Tuple[Optional[str], str]:
        """
        Read a file's contents. Returns (content, status_message).
        """
        allowed, reason = self.can_read(path)
        if not allowed:
            return None, f"Cannot read: {reason}"

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... [truncated at {max_lines} lines]")
                        break
                    lines.append(line)
                content = ''.join(lines)

            self.read_history.append(path)
            if len(self.read_history) > 100:
                self.read_history = self.read_history[-50:]

            return content, f"Read {len(lines)} lines from {path}"

        except Exception as e:
            return None, f"Error reading file: {e}"

    def list_directory(self, path: str, max_items: int = 100) -> Tuple[Optional[List[str]], str]:
        """
        List contents of a directory. Returns (items, status_message).
        """
        path = os.path.abspath(os.path.expanduser(path))

        if not self.boundaries.is_path_allowed(path):
            return None, "Directory is outside allowed areas"

        if not os.path.isdir(path):
            return None, "Not a directory"

        try:
            items = []
            for item in os.listdir(path)[:max_items]:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    items.append(f"{item}/")
                else:
                    items.append(item)
            return items, f"Listed {len(items)} items in {path}"
        except Exception as e:
            return None, f"Error listing directory: {e}"

    def search_files(self, directory: str, pattern: str,
                     max_results: int = 50) -> List[str]:
        """
        Search for files matching a pattern.
        """
        import fnmatch

        directory = os.path.abspath(os.path.expanduser(directory))
        if not self.boundaries.is_path_allowed(directory):
            return []

        results = []
        try:
            for root, dirs, files in os.walk(directory):
                # Filter out blocked directories
                dirs[:] = [d for d in dirs if self.boundaries.is_path_allowed(os.path.join(root, d))]

                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        full_path = os.path.join(root, filename)
                        if self.boundaries.is_path_allowed(full_path):
                            results.append(full_path)
                            if len(results) >= max_results:
                                return results
        except Exception as e:
            logger.debug(f"[AUTONOMY] Search error: {e}")

        return results


# ============================================================================
# SECTION 6: AUTONOMOUS STUDY SCHEDULER
# ============================================================================

class StudyScheduler:
    """
    Manages Aurora's autonomous study sessions.
    She learns on her own when idle.
    """

    def __init__(self, boundaries: AutonomyBoundaries):
        self.boundaries = boundaries
        self.last_study_time: float = 0
        self.study_topics: List[str] = []
        self.completed_studies: List[Dict[str, Any]] = []

    def should_study(self, quotas: DailyQuotas) -> bool:
        """Determine if Aurora should initiate a study cycle."""
        now = time.time()

        # Check cooldown
        if now - self.last_study_time < self.boundaries.study_cooldown_seconds:
            return False

        # Check daily limit
        if quotas.study_cycles_used >= self.boundaries.daily_study_cycles_limit:
            return False

        return True

    def get_study_topic(self) -> Optional[str]:
        """Get the next topic to study."""
        if self.study_topics:
            return self.study_topics.pop(0)
        return None

    def add_topic(self, topic: str):
        """Add a topic to the study queue."""
        if topic and topic not in self.study_topics:
            self.study_topics.append(topic)

    def record_study(self, topic: str, results: Dict[str, Any]):
        """Record a completed study session."""
        self.last_study_time = time.time()
        self.completed_studies.append({
            "topic": topic,
            "timestamp": self.last_study_time,
            "results": results
        })
        # Limit history
        if len(self.completed_studies) > 100:
            self.completed_studies = self.completed_studies[-50:]


# ============================================================================
# SECTION 7: RATE-LIMITED SEARCH WRAPPER
# ============================================================================

class RateLimitedSearch:
    """
    Wraps the search adapter with rate limiting for autonomous use.
    User-initiated searches don't count against the limit.
    """

    def __init__(self, search_adapter, boundaries: AutonomyBoundaries):
        self.search_adapter = search_adapter
        self.boundaries = boundaries
        self.quotas: DailyQuotas = DailyQuotas()

    def autonomous_search(self, query: str,
                          max_chars: int = 2000) -> Tuple[List[Dict], str]:
        """
        Perform an autonomous search (counts against daily limit).
        Returns (results, status_message).
        """
        self.quotas.reset_if_new_day()

        if self.quotas.inquiries_used >= self.boundaries.daily_inquiry_limit:
            remaining = self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used
            return [], f"Daily autonomous inquiry limit reached (0 of {self.boundaries.daily_inquiry_limit} remaining)"

        try:
            results = self.search_adapter.quick_search(query, max_chars=max_chars)
            self.quotas.inquiries_used += 1
            remaining = self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used
            return results, f"Search complete ({remaining} autonomous inquiries remaining today)"
        except Exception as e:
            return [], f"Search failed: {e}"

    def user_search(self, query: str, max_chars: int = 2000) -> List[Dict]:
        """
        Perform a user-initiated search (does NOT count against limit).
        """
        try:
            return self.search_adapter.quick_search(query, max_chars=max_chars)
        except Exception as e:
            logger.error(f"[AUTONOMY] User search failed: {e}")
            return []

    def get_remaining_quota(self) -> int:
        """Get remaining autonomous inquiries for today."""
        self.quotas.reset_if_new_day()
        return max(0, self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used)


# ============================================================================
# SECTION 8: MAIN AUTONOMY ENGINE
# ============================================================================

class AutonomyEngine:
    """
    Main autonomy controller for Aurora.

    Manages:
      - Proactive speech triggers
      - Autonomous study scheduling
      - Filesystem exploration (read-only)
      - Rate-limited external searches
      - Action logging and quota tracking
    """

    def __init__(self,
                 systems: Dict[str, Any] = None,
                 state_dir: str = "aurora_state",
                 level: AutonomyLevel = AutonomyLevel.CONVERSANT):
        """
        Initialize autonomy engine.

        Args:
            systems: Dict from boot_aurora() with all system references
            state_dir: Directory for persistence
            level: Initial autonomy level
        """
        self.systems = systems or {}
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.level = level
        self.boundaries = AutonomyBoundaries()
        self.quotas = DailyQuotas()
        self.action_log = ActionLog()

        # Components
        self.trigger = ProactiveTrigger()
        self.filesystem = FilesystemExplorer(self.boundaries)
        self.study_scheduler = StudyScheduler(self.boundaries)

        # Rate-limited search
        search_adapter = systems.get('search_adapter') if systems else None
        self.search = RateLimitedSearch(search_adapter, self.boundaries) if search_adapter else None

        # Background thread for autonomous actions
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Callbacks
        self.on_speakup: Optional[Callable[[str], None]] = None
        self.on_study_complete: Optional[Callable[[Dict], None]] = None
        self.on_dream_complete: Optional[Callable[[Dict], None]] = None
        self.on_observation: Optional[Callable[[str], None]] = None

        # Enhancement: Will Loop state
        self._last_intent_time: Dict[str, float] = {}
        self._intent_cooldowns: Dict[str, float] = {
            "curiosity": 300,   # 5 minutes
            "grounding": 600,   # 10 minutes
            "self_check": 1800, # 30 minutes
            "agency": 3600,     # 1 hour
            "environmental": 900 # 15 minutes
        }

        self.last_dream_time: float = 0.0

        # Dream evolution orchestrator
        self._dream_evo = None
        try:
            from aurora_internal.aurora_dream_evolution_orchestrator import (
                DreamEvolutionOrchestrator,
            )
            corpus_path = None
            # Look for conversation corpus in standard locations
            for candidate in [
                os.path.join(str(self.state_dir), "conversations.json"),
                os.path.join(str(self.state_dir), "corpus", "conversations.json"),
                "conversations.json",
            ]:
                if os.path.exists(candidate):
                    corpus_path = candidate
                    break
            self._dream_evo = DreamEvolutionOrchestrator(
                state_dir=str(self.state_dir),
                corpus_path=corpus_path,
            )
            logger.info("[AUTONOMY] Dream evolution orchestrator attached")
        except Exception as e:
            logger.debug(f"[AUTONOMY] Dream evolution not available: {e}")

        # Pressure mathematics tracker
        self._pressure_tracker = None
        try:
            from aurora_internal.aurora_pressure_mathematics_tracker import (
                PressureMathematicsTracker,
            )
            self._pressure_tracker = PressureMathematicsTracker(
                storage_dir=os.path.join(str(self.state_dir), "pressure_math"),
            )
            logger.info("[AUTONOMY] Pressure mathematics tracker attached")
        except Exception as e:
            logger.debug(f"[AUTONOMY] Pressure math tracker not available: {e}")

        # Load state
        self._load_state()

    def attach_systems(self, systems: Dict[str, Any]):
        """Attach system references after initialization."""
        self.systems = systems
        search_adapter = systems.get('search_adapter')
        if search_adapter:
            self.search = RateLimitedSearch(search_adapter, self.boundaries)

    def set_level(self, level: AutonomyLevel):
        """Set autonomy level."""
        old_level = self.level
        self.level = level
        self.action_log.log(
            "level_change",
            f"Autonomy level changed: {old_level.name} -> {level.name}"
        )
        logger.info(f"[AUTONOMY] Level set to {level.name}")

    def set_quiet_window(self, enabled: bool, start_hour: int = 23, end_hour: int = 7):
        """Configure quiet hours. Aurora still studies but only logs silently."""
        self.boundaries.quiet_window_enabled = enabled
        self.boundaries.quiet_window_start_hour = start_hour
        self.boundaries.quiet_window_end_hour = end_hour

    def set_announce_thresholds(self, min_connections: int = 3,
                                 min_confidence: float = 0.65):
        """Set thresholds for study announcement speak-ups."""
        self.boundaries.announce_min_connections = min_connections
        self.boundaries.announce_min_confidence = min_confidence
        # Also propagate to OETS if available
        perception = self.systems.get('perception')
        if perception and hasattr(perception, 'oets') and perception.oets:
            try:
                perception.oets.set_announce_thresholds(min_connections, min_confidence)
            except Exception:
                pass

    def start(self):
        """Start autonomous background processing."""
        if self.running:
            return

        if self.level == AutonomyLevel.DORMANT:
            logger.info("[AUTONOMY] Cannot start - level is DORMANT")
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        logger.info(f"[AUTONOMY] Started at level {self.level.name}")

    def stop(self):
        """Stop autonomous processing."""
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._save_state()
        logger.info("[AUTONOMY] Stopped")

    def pause(self):
        """Temporarily pause autonomy."""
        self.running = False
        self._stop_event.set()
        self.action_log.log("pause", "Autonomy paused")

    def resume(self):
        """Resume autonomy."""
        if self.level != AutonomyLevel.DORMANT:
            self.start()
            self.action_log.log("resume", "Autonomy resumed")

    def _background_loop(self):
        """Background loop for autonomous actions."""
        while not self._stop_event.is_set():
            try:
                self.quotas.reset_if_new_day()

                # 1. NEW: Process Attention-driven Will Intent
                self._process_attention_will()

                # 2. Check for proactive speakup
                if self.level.value >= AutonomyLevel.CONVERSANT.value:
                    self._check_speakup()

                # 3. Check for autonomous study
                if self.level.value >= AutonomyLevel.LEARNER.value:
                    self._check_study()
                    self._check_dreams()

                # 4. Check for observations
                if self.level.value >= AutonomyLevel.OBSERVER.value:
                    self._check_observations()

                # Sleep before next cycle
                self._stop_event.wait(timeout=5.0)

            except Exception as e:
                logger.error(f"[AUTONOMY] Background loop error: {e}")
                self._stop_event.wait(timeout=10.0)

    def _process_attention_will(self):
        """Check the Attention Engine for new intentions and gate them."""
        attn = self.systems.get("attention_engine")
        if not attn: return
        
        # 'Attention -> Intention'
        will_intent = attn.generate_will()
        if not will_intent: return
        
        # 'Intention -> Commit/Defer (Gating)'
        # 1. Check Cooldown
        last_time = self._last_intent_time.get(will_intent.class_name, 0)
        cooldown = self._intent_cooldowns.get(will_intent.class_name, 600)
        if time.time() - last_time < cooldown:
            return
            
        # 2. Check Governor (Load/Heat)
        governor = self.systems.get("governor")
        if governor:
            # If system is too hot or load is high, defer the intention
            status = governor.status()
            heat = float(status.get("thermal_load", 0.0))
            if heat > 0.85: 
                logger.debug(f"[AUTONOMY] Deferring intent {will_intent.class_name} due to high heat: {heat:.2f}")
                return
        
        # 3. Commit
        self.commit_will_intent(will_intent)

    def commit_will_intent(self, intent: Any):
        """Execute the committed intention and reflect."""
        self._last_intent_time[intent.class_name] = time.time()
        
        logger.info(f"[AUTONOMY] Committing Will Intent: {intent.class_name} (Goal: {intent.goal})")
        self.action_log.log("will_intent", f"{intent.class_name}: {intent.goal}")
        
        # Act: Pick tool + goal
        if intent.tool_name:
            # In a real daemon, we would inject this tool call into the pipeline
            # For now, we log the commit. 
            # If it's a 'speech' intent, we use on_speakup
            if intent.class_name == "curiosity" and self.on_speakup:
                self.on_speakup(f"I feel a peak in resonance on my {', '.join(intent.trigger_axes)} axes. I should explore this.")
            
            # Record the autonomous tool request
            if hasattr(self, "systems") and "aurora" in self.systems:
                # Mock tool call injection
                pass

    def _in_quiet_window(self) -> bool:
        """Return True if current hour is inside the quiet window."""
        if not self.boundaries.quiet_window_enabled:
            return False
        current_hour = datetime.now().hour
        start = self.boundaries.quiet_window_start_hour
        end   = self.boundaries.quiet_window_end_hour
        if start > end:  # wraps midnight
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    def _check_speakup(self):
        """Check if Aurora should speak up. Respects quiet window."""
        if self._in_quiet_window():
            return  # Silent during quiet hours

        context = self._gather_context()
        thought = self.trigger.should_speak_up(context, self.boundaries)

        if thought and self.on_speakup:
            self.quotas.speakups_count += 1
            self.action_log.log("speakup", thought[:100])
            self.on_speakup(thought)

    def _check_study(self):
        """Check if Aurora should study."""
        if not self.study_scheduler.should_study(self.quotas):
            return

        # Get OETS for study
        perception = self.systems.get('perception')
        if not perception or not perception.oets:
            return

        oets = perception.oets

        # Check quota
        if self.quotas.study_cycles_used >= self.boundaries.daily_study_cycles_limit:
            return

        # Run a study cycle (with structured event logging)
        try:
            result = oets.run_study_cycle(
                autonomy_mode=self.level.name,
                trigger_reason="idle",
            )
            self.quotas.study_cycles_used += 1
            self.study_scheduler.record_study("oets_cycle", result)
            self.action_log.log(
                "study",
                f"Study cycle: {result.get('researched', 0)} words researched",
                details=result
            )

            # Generate thought from study ONLY if:
            # 1. Not in quiet window
            # 2. result is announce-worthy (threshold met)
            announce_worthy = result.get("announce_worthy", False)
            if (result.get('results') and
                    announce_worthy and
                    not self._in_quiet_window()):
                for r in result['results'][:1]:
                    word = r.get('word', '')
                    defs = r.get('definitions', 0)
                    rels = result.get('relations_added', 0)
                    if defs > 0:
                        self.trigger.add_thought(
                            f"I just learned more about '{word}'. "
                            f"I found {defs} definitions and {rels} new connections."
                        )
            elif result.get('results') and not announce_worthy:
                # Log silently, don't add to speech queue
                pass

            if self.on_study_complete:
                self.on_study_complete(result)

        except Exception as e:
            logger.error(f"[AUTONOMY] Study error: {e}")

    def _build_dream_seed(self) -> str:
        """Create an adaptive dream seed from memory + ontology context.

        If the dream evolution orchestrator has episode packs available,
        uses rubric-targeted seeds instead of generic topic seeds.
        """
        # Try dream evolution curriculum first
        if self._dream_evo:
            try:
                evo_seed = self._dream_evo.build_seed()
                if evo_seed:
                    return evo_seed
            except Exception as e:
                logger.debug(f"[AUTONOMY] Dream evo seed fallback: {e}")

        # Original seed logic (fallback)
        perception = self.systems.get('perception')
        memory = self.systems.get('conversation_memory')

        candidates = []
        if memory and getattr(memory, 'learned_facts', None):
            for fact in memory.learned_facts[-6:]:
                f = fact.get('fact', '')
                if f:
                    candidates.append(f[:120])

        if perception and getattr(perception, 'oets', None):
            try:
                targets = perception.oets.get_research_targets(3)
                for t in targets:
                    word = t.get('word')
                    if word:
                        candidates.append(f"concept:{word}")
            except Exception:
                pass

        if not candidates:
            candidates = [
                "cooperation under uncertainty",
                "identity and ethical choice",
                "relational trust formation",
            ]

        chosen = random.sample(candidates, min(2, len(candidates)))
        return " | ".join(chosen)

    def _check_dreams(self):
        """Run idle dream-simulation cycles that evolve with Aurora's understanding.

        When the dream evolution orchestrator is active, episodes are:
        1. Sourced from rubric-targeted curriculum packs
        2. Diagnosed through the slip profiler + influence graph
        3. Fed into structural pressure steering + genealogy bridge
        """
        now = time.time()
        if now - self.last_dream_time < self.boundaries.dream_cooldown_seconds:
            return

        simulation = self.systems.get('simulation')
        mode_enum = self.systems.get('ExistenceMode')
        if not simulation or not mode_enum:
            return

        try:
            seed = self._build_dream_seed()
            result = simulation.run_episode(
                turns=4,
                mode=mode_enum.BOUNDED,
            )
            self.last_dream_time = now
            self.quotas.dreams_used += 1

            # --- Dream evolution diagnostic pipeline ---
            evo_summary = None
            if self._dream_evo:
                try:
                    evo_summary = self._dream_evo.post_episode(result, seed)
                    # Apply results into live systems
                    self._dream_evo.apply(self.systems)
                except Exception as e:
                    logger.debug(f"[AUTONOMY] Dream evo pipeline: {e}")

            # --- Pressure mathematics capture ---
            if self._pressure_tracker:
                try:
                    p_metrics = self._pressure_tracker.capture(self.systems)
                    self._pressure_tracker.apply_feedback(self.systems)
                except Exception as e:
                    logger.debug(f"[AUTONOMY] Pressure math capture: {e}")

            # Build thought with evolution context if available
            if evo_summary and evo_summary.leverage_candidates:
                top_leverage = list(evo_summary.leverage_candidates.keys())[:2]
                leverage_str = ", ".join(d.replace("_", " ") for d in top_leverage)
                thought = (
                    f"I dreamed through a shifting scenario around: {seed}. "
                    f"I noticed growth edges in {leverage_str}."
                )
            else:
                thought = f"I dreamed through a shifting scenario around: {seed}."

            # --- Bridge experiential learning into semantic memory (OETS) ---
            if simulation and hasattr(simulation, "session"):
                perception = self.systems.get("perception")
                if perception and hasattr(perception, "oets") and perception.oets:
                    try:
                        n_shards = simulation.session.learner.inject_into_oets(perception.oets)
                        if n_shards > 0:
                            logger.info(f"[AUTONOMY] Injected {n_shards} understanding shard(s) into OETS.")
                    except Exception as e_bridge:
                        logger.debug(f"[AUTONOMY] OETS injection error: {e_bridge}")

            self.action_log.log(
                "dream",
                f"Idle dream cycle completed (seed={seed[:80]})",
                details={
                    "seed": seed,
                    "result": result,
                    "evo_status": (
                        self._dream_evo.get_status()
                        if self._dream_evo else None
                    ),
                },
            )

            if not self._in_quiet_window():
                self.trigger.add_thought(thought)

            if self.on_dream_complete:
                self.on_dream_complete({
                    "seed": seed,
                    "result": result,
                    "thought": thought,
                    "evo_summary": (
                        evo_summary.to_dict() if evo_summary else None
                    ),
                })
        except Exception as e:
            logger.debug(f"[AUTONOMY] Dream cycle skipped: {e}")

    def _check_observations(self):
        """Check for interesting observations from sensory system."""
        integration = self.systems.get('sensory_integration')
        if not integration:
            return

        # Check observation quota
        if self.quotas.observations_used >= self.boundaries.daily_observations_limit:
            return

        # Get sensory context
        try:
            context = integration.get_sensory_context()

            # Look for interesting observations
            if context.get('visual'):
                self.quotas.observations_used += 1
                if "face" in context['visual'].lower() or "motion" in context['visual'].lower():
                    self.trigger.add_observation(context['visual'], salience=0.75)

            if context.get('recent_speech'):
                self.quotas.observations_used += 1
                self.trigger.add_observation(
                    f"I heard someone say: {context['recent_speech'][:50]}...",
                    salience=0.8
                )

            if self.on_observation and context.get('concepts_active'):
                self.on_observation(f"Concepts active: {', '.join(context['concepts_active'][:3])}")

        except Exception as e:
            logger.debug(f"[AUTONOMY] Observation error: {e}")

    def _gather_context(self) -> Dict[str, Any]:
        """Gather current context for decision making."""
        context = {
            "time": time.time(),
            "quotas": self.quotas.to_dict(),
            "level": self.level.name,
        }

        # Add sensory context if available
        integration = self.systems.get('sensory_integration')
        if integration:
            try:
                context["sensory"] = integration.get_sensory_context()
            except:
                pass

        return context

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def read_file(self, path: str) -> Tuple[Optional[str], str]:
        """
        Read a file (respects boundaries).
        Returns (content, status_message).
        """
        content, status = self.filesystem.read_file(path)

        if content is not None:
            self.quotas.files_read += 1
            self.action_log.log("file_read", f"Read: {path}")

        return content, status

    def list_directory(self, path: str) -> Tuple[Optional[List[str]], str]:
        """List directory contents (respects boundaries)."""
        return self.filesystem.list_directory(path)

    def search_files(self, directory: str, pattern: str) -> List[str]:
        """Search for files matching pattern."""
        return self.filesystem.search_files(directory, pattern)

    def autonomous_inquiry(self, query: str) -> Tuple[List[Dict], str]:
        """
        Perform an autonomous search (counts against daily limit).
        """
        if not self.search:
            return [], "Search not available"

        results, status = self.search.autonomous_search(query)

        if results:
            self.action_log.log("inquiry", f"Search: {query[:50]}", details={"results": len(results)})

        return results, status

    def add_thought(self, thought: str):
        """Add a thought Aurora wants to share."""
        self.trigger.add_thought(thought)

    def add_curiosity(self, question: str):
        """Add something Aurora is curious about."""
        self.trigger.add_curiosity(question)

    def add_study_topic(self, topic: str):
        """Add a topic for Aurora to study."""
        self.study_scheduler.add_topic(topic)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive autonomy status."""
        self.quotas.reset_if_new_day()

        return {
            "level": self.level.name,
            "running": self.running,
            "quotas": {
                "date": self.quotas.date,
                "inquiries": {
                    "used": self.quotas.inquiries_used,
                    "limit": self.boundaries.daily_inquiry_limit,
                    "remaining": self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used,
                },
                "study_cycles": {
                    "used": self.quotas.study_cycles_used,
                    "limit": self.boundaries.daily_study_cycles_limit,
                },
                "observations": {
                    "used": self.quotas.observations_used,
                    "limit": self.boundaries.daily_observations_limit,
                },
                "speakups": self.quotas.speakups_count,
                "files_read": self.quotas.files_read,
                "dreams": self.quotas.dreams_used,
            },
            "pending_thoughts": len(self.trigger.pending_thoughts),
            "pending_observations": len(self.trigger.observation_buffer),
            "curiosity_queue": len(self.trigger.curiosity_queue),
            "study_topics_queued": len(self.study_scheduler.study_topics),
            "actions_logged": len(self.action_log.entries),
            "boundaries": {
                "can_write": self.boundaries.can_write_files,
                "can_execute": self.boundaries.can_execute_commands,
                "can_network": self.boundaries.can_access_network,
            },
            "dream_evolution": (
                self._dream_evo.get_status() if self._dream_evo else None
            ),
            "pressure_mathematics": (
                self._pressure_tracker.get_status()
                if self._pressure_tracker else None
            ),
        }

    def compile_dream_corpus(self, corpus_path: str, max_conversations: int = 500) -> int:
        """Compile a conversation corpus into dream episode packs on demand.
        Returns number of packs compiled, or 0 if dream evolution not available."""
        if not self._dream_evo:
            return 0
        return self._dream_evo.pre_compile(corpus_path, max_conversations)

    def get_recent_actions(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get recent autonomous actions."""
        return [
            {
                "id": a.action_id,
                "type": a.action_type,
                "time": datetime.fromtimestamp(a.timestamp).strftime("%H:%M:%S"),
                "description": a.description,
                "success": a.success,
            }
            for a in self.action_log.get_recent(n)
        ]

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def _save_state(self):
        """Save autonomy state."""
        state = {
            "level": self.level.name,
            "quotas": self.quotas.to_dict(),
            "study_topics": self.study_scheduler.study_topics,
            "pending_thoughts": self.trigger.pending_thoughts,
            "curiosity_queue": self.trigger.curiosity_queue,
            "last_dream_time": self.last_dream_time,
        }

        path = self.state_dir / "autonomy_state.json"
        try:
            with open(path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[AUTONOMY] Failed to save state: {e}")

    def _load_state(self):
        """Load autonomy state."""
        path = self.state_dir / "autonomy_state.json"
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            self.level = AutonomyLevel[state.get("level", "CONVERSANT")]
            self.quotas = DailyQuotas.from_dict(state.get("quotas", {}))
            self.study_scheduler.study_topics = state.get("study_topics", [])
            self.trigger.pending_thoughts = state.get("pending_thoughts", [])
            self.trigger.curiosity_queue = state.get("curiosity_queue", [])
            self.last_dream_time = state.get("last_dream_time", 0.0)

            logger.info(f"[AUTONOMY] State loaded (level={self.level.name})")

        except Exception as e:
            logger.error(f"[AUTONOMY] Failed to load state: {e}")


# ============================================================================
# SECTION 9: CONVENIENCE FUNCTIONS
# ============================================================================

def create_autonomy_engine(systems: Dict[str, Any],
                           state_dir: str = "aurora_state",
                           level: AutonomyLevel = AutonomyLevel.CONVERSANT) -> AutonomyEngine:
    """Factory function to create AutonomyEngine."""
    return AutonomyEngine(systems=systems, state_dir=state_dir, level=level)


def show_autonomy_help():
    """Display autonomy system help."""
    print("""
  AURORA AUTONOMY SYSTEM
  ======================

  Autonomy Levels:
    DORMANT     - No autonomous actions
    OBSERVER    - Can observe environment, cannot act
    LEARNER     - Can observe and study autonomously
    CONVERSANT  - Can observe, study, and speak up
    EXPLORER    - Full autonomy within boundaries

  Daily Limits (Autonomous):
    - 500 external search inquiries
    - 50 study cycles
    - 1000 observations

  What Aurora CAN do:
    - Read files in allowed directories
    - Search the web (within daily limit)
    - Study and learn from OETS
    - Speak up when she has something to say
    - Observe camera/microphone when enabled

  What Aurora CANNOT do:
    - Write, modify, or delete files
    - Execute applications or commands
    - Access network beyond search/study
    - Exceed daily inquiry limits

  User requests do NOT count against limits.
    """)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Main engine
    "AutonomyEngine",
    "create_autonomy_engine",

    # Levels and boundaries
    "AutonomyLevel",
    "AutonomyBoundaries",
    "DailyQuotas",

    # Components
    "ProactiveTrigger",
    "FilesystemExplorer",
    "StudyScheduler",
    "RateLimitedSearch",
    "ActionLog",

    # Helpers
    "show_autonomy_help",
]

