# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Potential Trial Board — actively tests unused potential instead of just
flagging it.

PotentialTracker (cers_regulator.py) only detects that a channel has gone
dormant. That's a hypothesis, not a verdict. This board tests the hypothesis
the same way subsystem_waveforms.py's CrestRegistry already trials new WARP
crests (see CrestRegistry._evaluate_trials, TRIAL_TICKS, PROMOTION_SCORE):
run a bounded trial window, score correlation against every other cluster,
then resolve to one of two outcomes — never leave it in permanent limbo.

    PROMOTED — the dormant channel's rare active moments correlate with a
    specific other cluster's activation. That's real evidence of latent
    cross-pipeline value: this channel isn't dead, it's just not needed on
    ITS OWN pipeline right now. Tag which cluster it benefits and surface
    that as a recognized signal, not blocking dead weight.

    DISSOLVED — no correlation with anything, across the full trial
    window. Confirmed genuinely inert. Safe to stop treating as a reason
    to withhold a deprecation recommendation.

Until a trial resolves one way or the other, the channel keeps blocking —
that's the honest "still testing" state, not indefinite caution.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

TRIAL_TICKS = 40
PROMOTION_CORRELATION = 0.35
_MIN_SAMPLES_FOR_CORRELATION = 12


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < _MIN_SAMPLES_FOR_CORRELATION or n != len(ys):
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    if denom < 1e-9:
        return 0.0
    return cov / denom


@dataclass
class PotentialTrial:
    """One channel's active trial: is its dormancy real, or is it quietly
    correlated with a pipeline it isn't formally wired into?"""

    channel: str
    tick_opened: int
    trial_tick: int = 0
    channel_history: Deque[float] = field(default_factory=lambda: deque(maxlen=TRIAL_TICKS))
    cluster_histories: Dict[str, Deque[float]] = field(default_factory=dict)
    resolved: bool = False
    promoted: bool = False
    benefits_cluster: Optional[str] = None
    best_correlation: float = 0.0

    def observe(self, channel_intensity: float, cluster_scores: Dict[str, float]) -> None:
        if self.resolved:
            return
        self.trial_tick += 1
        self.channel_history.append(channel_intensity)
        for cluster, score in cluster_scores.items():
            self.cluster_histories.setdefault(cluster, deque(maxlen=TRIAL_TICKS)).append(score)
        if self.trial_tick >= TRIAL_TICKS:
            self._resolve()

    def _resolve(self) -> None:
        xs = list(self.channel_history)
        best_cluster, best_corr = None, 0.0
        for cluster, hist in self.cluster_histories.items():
            ys = list(hist)
            if len(ys) < len(xs):
                continue
            ys = ys[-len(xs):]
            corr = _pearson(xs, ys)
            if abs(corr) > abs(best_corr):
                best_corr, best_cluster = corr, cluster
        self.best_correlation = round(best_corr, 4)
        self.resolved = True
        if best_cluster is not None and abs(best_corr) >= PROMOTION_CORRELATION:
            self.promoted = True
            self.benefits_cluster = best_cluster

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "trial_tick": self.trial_tick,
            "resolved": self.resolved,
            "promoted": self.promoted,
            "benefits_cluster": self.benefits_cluster,
            "best_correlation": self.best_correlation,
        }


class PotentialTrialBoard:
    """Opens a trial the first time a channel is flagged dormant, runs it to
    resolution, and remembers the outcome. The deprecation ledger consults
    this to tell 'still actively testing' apart from 'confirmed dead
    weight, stop blocking' apart from 'found real cross-pipeline value.'"""

    def __init__(self) -> None:
        self._tick = 0
        self._active: Dict[str, PotentialTrial] = {}
        self._resolved: Dict[str, PotentialTrial] = {}

    def observe(
        self,
        unused_potential: List[str],
        cluster_scores: Dict[str, float],
        channel_intensities: Dict[str, float],
    ) -> None:
        self._tick += 1
        for channel in unused_potential:
            if channel not in self._active and channel not in self._resolved:
                self._active[channel] = PotentialTrial(channel=channel, tick_opened=self._tick)
        for channel, trial in list(self._active.items()):
            trial.observe(channel_intensities.get(channel, 0.0), cluster_scores)
            if trial.resolved:
                self._resolved[channel] = trial
                del self._active[channel]

    def actively_trialing(self) -> List[str]:
        """Channels whose potential is still being tested — the honest,
        temporary block."""
        return sorted(self._active.keys())

    def confirmed_benefits(self) -> Dict[str, str]:
        """channel -> cluster it demonstrably correlates with. Evidence a
        cross-pipeline reroute would be worth wiring, not a reason to
        deprecate the channel."""
        return {ch: t.benefits_cluster for ch, t in self._resolved.items() if t.promoted and t.benefits_cluster}

    def confirmed_inert(self) -> List[str]:
        """Channels that ran the full trial and correlated with nothing.
        These no longer block a deprecation recommendation."""
        return sorted(ch for ch, t in self._resolved.items() if t.resolved and not t.promoted)

    def status_summary(self) -> Dict[str, Any]:
        return {
            "actively_trialing": self.actively_trialing(),
            "confirmed_benefits": self.confirmed_benefits(),
            "confirmed_inert": self.confirmed_inert(),
        }
