import sys, os; from pathlib import Path
_HERE = Path(__file__).resolve().parent; _CORE = _HERE / "aurora_core_ai"
if str(_CORE) not in sys.path: sys.path.insert(0, str(_CORE))
from corpus_runner import *
if __name__ == '__main__':
    main()
