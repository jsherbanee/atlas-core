from __future__ import annotations

from pathlib import Path
import json
from typing import List, Dict


def read_job_states(session_root: str | Path) -> List[Dict]:
    """Read `.jobs/*.json` files under a session root and return parsed states.

    This is a lightweight helper intended for Streamlit UI usage but does not
    import Streamlit directly so it can be used in tests.
    """
    root = Path(session_root)
    jobs_dir = root / ".jobs"
    states: List[Dict] = []
    if not jobs_dir.exists():
        return states
    for p in sorted(jobs_dir.iterdir()):
        if not p.is_file() or not p.name.endswith(".json"):
            continue
        try:
            states.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return states


def streamlit_show(session_root: str | Path, st_module) -> None:
    """Render a compact intake status surface using the provided Streamlit module.

    `st_module` should be the `streamlit` module (injected) so this helper
    doesn't import Streamlit at runtime if the environment doesn't have it.
    """
    states = read_job_states(session_root)
    if not states:
        st_module.info("No intake jobs found for this session.")
        return
    for js in states:
        cols = st_module.columns([4, 1, 1, 1, 2])
        cols[0].write(js.get("filename") or "<unknown>")
        cols[1].write(js.get("processing_class") or "")
        cols[2].write(js.get("stage") or "")
        cols[3].write(f"{js.get('size_bytes') or ''}")
        # small details
        cols[4].write(f"{js.get('worker_pid') or ''}\n{js.get('failure_reason') or ''}")
