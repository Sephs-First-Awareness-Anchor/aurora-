# Re-export shim: delegate the bare module name `aurora_surface_daemon` to its real
# implementation in aurora_core_ai/.
#
# The previous body was `from aurora_surface_daemon import *`, which self-imported THIS stub
# (already registered in sys.modules during its own import) and therefore
# re-exported nothing -- callers received an empty module and imports such as
# `from aurora_surface_daemon import GrammarEngine` raised ImportError. When repo-root sits
# ahead of aurora_core_ai on sys.path, this stub shadows the real module and
# the empty result gets cached, poisoning every later import of the same name.
#
# We instead load the real file explicitly and replace this module object in
# sys.modules so all names resolve to the real implementation.
import importlib.util as _ilu, sys as _sys, os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CORE = _os.path.join(_HERE, "aurora_core_ai")
if _CORE not in _sys.path:
    _sys.path.insert(0, _CORE)

_REAL = _os.path.join(_CORE, "aurora_surface_daemon.py")
_spec = _ilu.spec_from_file_location(__name__, _REAL)
_mod = _ilu.module_from_spec(_spec)
_sys.modules[__name__] = _mod
_spec.loader.exec_module(_mod)
