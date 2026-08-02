# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip integration phase C: the exception-instrumentation injector itself
(scripts/aurora_fault_instrumentation_injector.py). The zip's uploaded
snapshot demonstrated 3336 instrumented call sites across 198 files but
did not include the tool that produced them -- this is a fresh injector
built against the same detection rules as the already-ported
aurora_fault_audit.py (imported directly, not re-implemented).

These tests exercise the injector against small synthetic source
strings covering the shapes that a repo-wide dry run against the real
current codebase (3295 handlers / 196 files, 0 skips) surfaced,
including the one genuine bug caught during development: single-line
handlers (`except Exception: pass`) had their instrumentation block
inserted BEFORE the except line instead of splitting the line, which
produced a syntax error. Fixed by always locating the header's
terminating colon via `tokenize` and rebuilding the header/body split
from there, uniformly for both single-line and multi-line handlers.
"""
import ast
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import aurora_fault_instrumentation_injector as inj  # noqa: E402


def _instrument_source(source: str, tmp_path: Path) -> str:
    """Run the real instrument_file() against a throwaway file placed
    inside the actual repo tree (production_files()/relative_to() both
    require this), then return the resulting source and clean up."""
    target = REPO_ROOT_PATH / f"_test_injector_scratch_{os.getpid()}.py"
    target.write_text(source, encoding="utf-8")
    try:
        count = inj.instrument_file(target, dry_run=False)
        return count, target.read_text(encoding="utf-8")
    finally:
        target.unlink(missing_ok=True)


REPO_ROOT_PATH = Path(REPO_ROOT)


def test_single_line_handler_body_is_split_not_prepended():
    """The exact bug found during development: `except Exception: pass`
    must become a header line followed by the injected block followed
    by the original inline body -- not have the block dumped before the
    except clause, which breaks try/except structure entirely."""
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception: pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    ast.parse(result)  # must not raise
    assert "except Exception as _aurora_boundary_exc:\n" in result
    lines = result.splitlines()
    except_idx = next(i for i, l in enumerate(lines) if "except Exception as _aurora_boundary_exc:" in l)
    assert "_aurora_record_exception_from_locals(" in lines[except_idx + 1]
    # original inline body ("pass") must survive, after the injected block
    tail = "\n".join(lines[except_idx:])
    assert tail.rstrip().endswith("pass")


def test_multiline_handler_body_unaffected_in_placement():
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        do_fallback()\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    ast.parse(result)
    assert "_aurora_record_exception_from_locals(" in result
    assert "do_fallback()" in result
    # the original body statement must still come after the injected block
    block_idx = result.index("_aurora_record_exception_from_locals(")
    fallback_idx = result.index("do_fallback()")
    assert block_idx < fallback_idx


def test_existing_as_clause_is_reused_not_duplicated():
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception as original_name:\n"
        "        pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    ast.parse(result)
    assert "except Exception as original_name:" in result
    # only one " as " in the function body itself -- the import line's
    # own "import X as Y" alias is a separate, expected occurrence.
    body = result[result.index("def f():"):]
    assert body.count(" as ") == 1
    assert "exc=original_name," in result


def test_multiline_tuple_exception_header_is_handled():
    """No real multi-line except header exists anywhere in the current
    codebase (confirmed by scanning production_files() during
    development) -- this synthetic case exercises that path directly
    since tokenize-based colon detection doesn't care about line
    boundaries, but it was never proven against real repo content."""
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except (\n"
        "        TypeError,\n"
        "        ValueError,\n"
        "    ):\n"
        "        pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    ast.parse(result)
    assert "_aurora_record_exception_from_locals(" in result
    assert " as _aurora_boundary_exc:" in result


def test_intentional_marker_comment_is_respected():
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:  # aurora-fault-boundary: intentional\n"
        "        pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 0
    assert "_aurora_record_exception_from_locals(" not in result


def test_already_visible_handler_is_left_alone():
    source = (
        "import logging\n"
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception as e:\n"
        "        logging.error(str(e))\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 0
    assert "_aurora_record_exception_from_locals(" not in result


def test_import_line_inserted_once_after_module_docstring():
    source = (
        '"""A module docstring."""\n'
        "import os\n"
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    assert result.count(inj.IMPORT_LINE) == 1
    lines = result.splitlines()
    docstring_idx = next(i for i, l in enumerate(lines) if l.strip() == '"""A module docstring."""')
    import_idx = next(i for i, l in enumerate(lines) if inj.IMPORT_LINE in l)
    assert import_idx > docstring_idx


def test_import_not_duplicated_if_already_present():
    source = (
        inj.IMPORT_LINE + "\n"
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 1
    assert result.count(inj.IMPORT_LINE) == 1


def test_nested_except_handlers_both_instrumented_correctly():
    """An except body that itself contains another try/except -- the
    bottom-up-by-lineno ordering this injector relies on must handle
    nesting without corrupting indices."""
    source = (
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        try:\n"
        "            fallback()\n"
        "        except ValueError:\n"
        "            pass\n"
        "        finish_up()\n"
    )
    count, result = _instrument_source(source, REPO_ROOT_PATH)
    assert count == 2
    ast.parse(result)
    assert "finish_up()" in result
    assert result.index("fallback()") < result.index("finish_up()")


def test_real_repo_dry_run_has_zero_skips():
    """The actual acceptance bar for this tool: every production file
    in the real current repo must parse both before and after a
    (dry-run) rewrite. This is the same check that caught the original
    single-line-handler bug against aurora.py, aurora_acm_bridge.py,
    aurora_internal/aurora_room_operator.py, and
    aurora_reflexive_interpreter.py during development."""
    from aurora_internal.aurora_fault_audit import production_files
    skipped = []
    for path in production_files(REPO_ROOT_PATH):
        if inj.instrument_file(path, dry_run=True) < 0:
            skipped.append(str(path))
    assert not skipped, f"{len(skipped)} files failed a dry-run rewrite: {skipped[:5]}"
