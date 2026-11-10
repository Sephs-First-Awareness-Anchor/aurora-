from types import SimpleNamespace

from aurora_internal.dual_strata import predictive_stager as staging


SCOPE = ("same-surface", 7, "context-before-next-turn")


def test_subsurface_stages_and_surface_reads_without_file_or_network_io(monkeypatch):
    now = [0.0]
    inbox = staging.PushedPredictiveFrames(clock=lambda: now[0])
    inbox.bind(SCOPE)

    def fail_file_io(*_args):
        raise AssertionError("a connected Surface must use its pushed frames")

    monkeypatch.setattr(staging, "_load_queue", fail_file_io)
    monkeypatch.setattr(staging, "_save_queue", fail_file_io)

    reads = []

    class Agency:
        @property
        def polarity(self):
            reads.append("axis")
            return 1.0

    batches = []

    def publish(frames):
        batches.append(frames)
        assert inbox.offer(SCOPE, 1, 5.0, frames)

    subsurface = {
        "lattice": SimpleNamespace(vertices=SimpleNamespace(axes={"A": Agency()})),
        "_publish_predictive_frames": publish,
    }
    anticipatory_context = SimpleNamespace(dominant_theme="river", active_concepts=["bank"])
    count, _ = staging.PredictiveStager.stage_passes_for_tick(subsurface, anticipatory_context, None)
    assert count == staging.n_passes_for_density("A")
    assert len(batches) == 1 and len(batches[0]) == count and reads == ["axis"]

    surface = {"_pushed_predictive_frames": inbox}
    assert staging.PredictiveStager.harvest_into_systems(surface) == count
    frame = surface["_staged_subsurface_frame"]
    assert frame["working_memory"]["dominant_theme"] == "river"
    assert any(item["token"] == "bank" for item in frame["slot_projections"])
    assert staging.PredictiveStager.harvest_into_systems(surface) == 0
    assert surface["_staged_subsurface_frame"] is frame

    now[0] = 5
    assert staging.PredictiveStager.harvest_into_systems(surface) == 0
    assert "_staged_subsurface_frame" not in surface


def test_late_and_out_of_scope_predictions_cannot_replace_current_data():
    inbox = staging.PushedPredictiveFrames()
    inbox.bind(SCOPE)
    assert inbox.offer(SCOPE, 4, 5, [{"topic": "river"}])
    assert not inbox.offer(SCOPE, 3, 5, [{"topic": "old"}])
    next_scope = (SCOPE[0], SCOPE[1], "newly-resolved-context")
    inbox.bind(next_scope)
    assert not inbox.offer(SCOPE, 5, 5, [{"topic": "old-context"}])
    assert not inbox.offer(next_scope, 1, 0, [{"topic": "already expired"}])
    assert inbox.harvest(None, 8) == (None, [])
    assert inbox.offer(next_scope, 1, 5, [{"topic": "resolved riverbank"}])
    assert inbox.harvest(None, 8)[1] == [{"topic": "resolved riverbank"}]

    laptop_scope = (SCOPE[0], SCOPE[1] + 2, next_scope[2])
    inbox.bind(laptop_scope)
    assert not inbox.offer(next_scope, 2, 5, [{"topic": "old phone lease"}])
    assert inbox.harvest(None, 8) == (None, [])


def test_existing_file_stager_batches_perspectives_into_one_write(monkeypatch):
    writes = []
    monkeypatch.setattr(staging, "_load_queue", lambda: [])
    monkeypatch.setattr(staging, "_save_queue", writes.append)
    systems = {"lattice": SimpleNamespace(vertices=SimpleNamespace(
        axes={"A": SimpleNamespace(polarity=0.7)},
    ))}
    count, _ = staging.PredictiveStager.stage_passes_for_tick(systems, None, None)
    assert len(writes) == 1 and len(writes[0]) == count
    assert [f["projection"]["perspective_index"] for f in writes[0]] == list(range(count))
