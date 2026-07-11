# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the concept-imager silent-failure bug (2026-07-11):
concept_images_ingested read 0 on every scheduled run since the feature
was wired in, even though 26 OETS nodes have reached SEMANTIC level and
a real fetched image (aurora_state/vision_seeds/concepts/aurora.jpg)
sat there unused.

Root cause (two parts, both in aurora_concept_imager.ingest_concept_image):

1. `from aurora_expression_perception import LinuxCamera` -- LinuxCamera
   actually lives in aurora_hardware_io; aurora_expression_perception only
   re-exports it inside a local lazy-import function
   (_lazy_import_hardware), never as a module-level name. This import has
   raised ImportError since the file's first commit, silently caught by
   `except ImportError: return False`, so every ingestion attempt failed
   before ever touching a frame.

2. Even with the import path fixed, `LinuxCamera.__new__(LinuxCamera)`
   bypassed __init__ and only set device_id/running/last_frame, leaving
   _mediapipe, _mp_face_detector, _mp_pose, etc. unset -- extract_features()
   then raised AttributeError on first use.

Existing coverage in test_concept_imager_cycle.py explicitly monkeypatches
fetch_concept_image out and never exercises ingest_concept_image's real
import path, which is exactly how this got through unnoticed. This test
exercises the real function against the real committed fixture image.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_concept_imager import ingest_concept_image

_FIXTURE = (
    Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    / "aurora_state" / "vision_seeds" / "concepts" / "aurora.jpg"
)


class _FakeSensoryCrystal:
    def __init__(self):
        self.observe_frame_calls = []

    def observe_frame(self, *args, **kwargs):
        self.observe_frame_calls.append(kwargs)

    def _register_concept_visual(self, word, tag):
        pass


def test_linux_camera_imports_from_its_real_module():
    """LinuxCamera must resolve from aurora_hardware_io -- the module it is
    actually defined in -- not from aurora_expression_perception, which only
    exposes it inside a function-local lazy import."""
    from aurora_hardware_io import LinuxCamera as _RealLinuxCamera
    assert _RealLinuxCamera.__module__ == "aurora_hardware_io"


def test_ingest_concept_image_succeeds_against_real_fixture():
    """The exact real-world case: a genuinely fetched concept image sitting
    on disk (aurora.jpg) must actually reach the sensory crystal instead of
    silently no-op'ing on a broken import."""
    assert _FIXTURE.exists(), "fixture image missing from repo"

    sc = _FakeSensoryCrystal()
    ok = ingest_concept_image(_FIXTURE, "aurora", None, sc)

    assert ok is True
    assert len(sc.observe_frame_calls) == 1
    assert sc.observe_frame_calls[0]["session_id"] == "concept:aurora"


def test_ingest_concept_image_extracted_camera_has_detector_attrs():
    """A LinuxCamera built via __new__() without __init__() lacks
    _mediapipe/_mp_face_detector/etc. -- confirm extract_features() runs
    against a properly constructed instance instead of a half-built one."""
    from aurora_hardware_io import LinuxCamera
    cam = LinuxCamera(device_id=-1)
    for attr in ("_mediapipe", "_mp_face_detector", "_mp_pose", "_ultralytics_detector"):
        assert hasattr(cam, attr), f"LinuxCamera() must initialize {attr}"
