# Authors: Sunni (Sir) Morningstar & Cael Devo
import sys, os
sys.path.insert(0, os.getcwd())
from aurora import boot_aurora
from aurora_constraint_emission import EmissionContextBuilder, InputFrame as _IF

if __name__ == "__main__":
    systems = boot_aurora(state_dir="aurora_state", verbose=False)
    ce = systems.get("constraint_emitter")
    if ce:
        _if = _IF(text="how are you", is_directed=True)
        ec = EmissionContextBuilder().build(systems, input_frame=_if)
        try:
            ce.emit(ec)
            print("EMIT SUCCESS")
        except Exception as e:
            print(f"EMIT CRASHED: {e}")
