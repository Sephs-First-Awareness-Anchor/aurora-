from concurrent.futures import ThreadPoolExecutor

import pytest

from aurora_internal.dual_strata.surface_device_presence import (
    SurfaceDevicePresence,
    SurfacePresenceError,
)
from aurora_internal.dual_strata import surface_device_presence


INITIAL = b'{"working_memory":{"topic":"garden"}}'
AFTER_TURN = b'{"working_memory":{"topic":"river","pending_clarification":"which bank?"}}'


@pytest.fixture
def devices(tmp_path):
    now = [0.0]
    path = tmp_path / "devices.json"
    hub = SurfaceDevicePresence(path, lease_s=10, online_s=20, clock=lambda: now[0])
    hub.register("phone", "Galaxy A16")
    hub.register("laptop", "Windows laptop")
    hub.heartbeat("phone")
    hub.heartbeat("laptop")
    hub.request_transfer("phone", expected_epoch=0)
    phone = hub.heartbeat("phone")
    hub.save_checkpoint("phone", phone.epoch, INITIAL, expected_revision=0)
    return hub, now, path


def restore(hub, device):
    staged = hub.heartbeat(device)
    assert staged.state == "restoring" and staged.valid_for_s == 0
    checkpoint = hub.restore_checkpoint(device, staged.epoch)
    hub.acknowledge_restore(device, staged.epoch, checkpoint.revision, checkpoint.digest)
    return checkpoint, hub.heartbeat(device)


def test_handoff_moves_the_same_surface_and_its_exact_state(devices):
    hub, _, _ = devices
    first = hub.heartbeat("phone")
    hub.begin_turn("phone", first.epoch, "one")
    hub.request_transfer("laptop", expected_epoch=first.epoch)

    assert hub.heartbeat("phone").state == "draining"
    assert hub.heartbeat("laptop").state == "asleep"
    with pytest.raises(SurfacePresenceError, match="preparing to sleep"):
        hub.begin_turn("phone", first.epoch, "two")
    with pytest.raises(SurfacePresenceError, match="no handoff ready"):
        hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)

    hub.finish_turn("phone", first.epoch, "one")
    hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    staged = hub.heartbeat("laptop")
    with pytest.raises(SurfacePresenceError, match="stale"):
        hub.begin_turn("laptop", staged.epoch, "too early")
    with pytest.raises(SurfacePresenceError, match="no checkpoint ready"):
        hub.restore_checkpoint("phone", staged.epoch)
    with pytest.raises(SurfacePresenceError, match="did not restore"):
        hub.acknowledge_restore("laptop", staged.epoch, 2, "incorrect digest")
    assert hub.status()["active_device"] is None

    checkpoint, second = restore(hub, "laptop")
    assert checkpoint.data == AFTER_TURN and checkpoint.revision == 2
    assert second.state == "awake" and second.epoch > first.epoch
    assert second.surface_id == first.surface_id
    assert hub.heartbeat("phone").state == "asleep"
    with pytest.raises(SurfacePresenceError, match="stale"):
        hub.require_awake("phone", first.epoch)
    with pytest.raises(SurfacePresenceError, match="stale"):
        hub.finish_turn("phone", first.epoch, "one")
    hub.begin_turn("laptop", second.epoch, "two")
    hub.finish_turn("laptop", second.epoch, "two")
    hub.request_transfer("phone", expected_epoch=second.epoch)
    laptop_state = b'{"working_memory":{"topic":"river","referent":"east bank"}}'
    hub.acknowledge_sleep("laptop", second.epoch, laptop_state, expected_revision=2)
    checkpoint, back_on_phone = restore(hub, "phone")
    assert checkpoint.revision == 3 and checkpoint.data == laptop_state
    assert back_on_phone.surface_id == first.surface_id


def test_failed_checkpoint_commit_keeps_the_source_in_charge(devices, monkeypatch):
    hub, _, _ = devices
    first = hub.heartbeat("phone")
    hub.request_transfer("laptop", expected_epoch=first.epoch)
    with monkeypatch.context() as patch:
        patch.setattr(surface_device_presence, "atomic_write_json", lambda *_args: False)
        with pytest.raises(OSError, match="could not commit"):
            hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    assert hub.heartbeat("laptop").state == "asleep"
    assert hub.heartbeat("phone").state == "draining"
    assert hub.status()["checkpoint_revision"] == 1
    hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    checkpoint, _ = restore(hub, "laptop")
    assert checkpoint.data == AFTER_TURN


def test_offline_or_unknown_targets_leave_current_surface_awake(devices):
    hub, now, _ = devices
    for moment in (6.0, 12.0, 18.0, 21.0):
        now[0] = moment
        lease = hub.heartbeat("phone")
    with pytest.raises(SurfacePresenceError, match="offline"):
        hub.request_transfer("laptop", expected_epoch=lease.epoch)
    with pytest.raises(SurfacePresenceError, match="unregistered"):
        hub.request_transfer("unknown", expected_epoch=lease.epoch)
    assert hub.heartbeat("phone").state == "awake"


def test_disconnected_source_requires_explicit_checkpoint_recovery(devices):
    hub, now, _ = devices
    first = hub.heartbeat("phone")
    hub.request_transfer("laptop", expected_epoch=first.epoch)
    now[0] = 9
    assert hub.heartbeat("laptop").state == "asleep"
    now[0] = 10
    standby = hub.heartbeat("laptop")
    assert standby.state == "asleep" and standby.epoch > first.epoch
    assert hub.status()["recovery_required"]
    with pytest.raises(SurfacePresenceError, match="stale"):
        hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    with pytest.raises(SurfacePresenceError, match="no matching"):
        hub.recover_checkpoint(expected_epoch=standby.epoch, revision=2)
    hub.recover_checkpoint(expected_epoch=standby.epoch, revision=1)
    checkpoint, second = restore(hub, "laptop")
    assert checkpoint.data == INITIAL and second.surface_id == first.surface_id


def test_target_returns_to_the_frozen_state_after_disconnecting(devices):
    hub, now, _ = devices
    first = hub.heartbeat("phone")
    hub.begin_turn("phone", first.epoch, "last")
    hub.request_transfer("laptop", expected_epoch=first.epoch)
    for moment in (6.0, 12.0, 18.0, 21.0):
        now[0] = moment
        assert hub.heartbeat("phone").state == "draining"
    hub.finish_turn("phone", first.epoch, "last")
    hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    assert hub.status()["active_device"] is None
    assert hub.status()["requested_device"] == "laptop"
    assert hub.heartbeat("phone").state == "asleep"
    checkpoint, _ = restore(hub, "laptop")
    assert checkpoint.data == AFTER_TURN


def test_restart_between_freeze_and_restore_keeps_one_checkpoint(devices):
    hub, now, path = devices
    first = hub.heartbeat("phone")
    hub.request_transfer("laptop", expected_epoch=first.epoch)
    hub.acknowledge_sleep("phone", first.epoch, AFTER_TURN, expected_revision=1)
    restarted = SurfaceDevicePresence(path, lease_s=10, online_s=20, clock=lambda: now[0])
    assert restarted.status()["active_device"] is None
    assert restarted.heartbeat("phone").state == "asleep"
    checkpoint, lease = restore(restarted, "laptop")
    assert checkpoint.data == AFTER_TURN
    assert lease.surface_id == first.surface_id


def test_hub_restart_waits_out_the_old_lease_before_recovery(devices):
    old_hub, now, path = devices
    first = old_hub.heartbeat("phone")
    old_hub.request_transfer("laptop", expected_epoch=first.epoch)
    new_hub = SurfaceDevicePresence(path, lease_s=5, online_s=20, clock=lambda: now[0])
    assert new_hub.status()["devices"]["phone"]["label"] == "Galaxy A16"
    assert new_hub.status()["requested_device"] == "laptop"
    now[0] = 9
    standby = new_hub.heartbeat("laptop")
    with pytest.raises(SurfacePresenceError, match="waiting for the previous lease"):
        new_hub.recover_checkpoint(expected_epoch=standby.epoch, revision=1)
    now[0] = 10
    new_hub.recover_checkpoint(expected_epoch=standby.epoch, revision=1)
    _, second = restore(new_hub, "laptop")
    assert second.state == "awake" and second.epoch > first.epoch
    with pytest.raises(SurfacePresenceError, match="stale"):
        new_hub.begin_turn("phone", first.epoch, "old")


def test_concurrent_admission_has_one_winner_and_blocks_midturn_saves(devices):
    hub, _, _ = devices
    lease = hub.heartbeat("phone")

    def admit(turn_id):
        try:
            hub.begin_turn("phone", lease.epoch, turn_id)
        except SurfacePresenceError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(admit, ["one", "two"])).count(True) == 1
    with pytest.raises(SurfacePresenceError, match="completed turn boundary"):
        hub.save_checkpoint("phone", lease.epoch, AFTER_TURN, expected_revision=1)
