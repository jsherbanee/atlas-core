"""Profile PDF extraction steps and record memory/GC/tracemalloc snapshots.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/profile_extraction.py <pdf_path> <out_json>

This is a profiling-only helper; it should not modify production code.
"""

from pathlib import Path
import time
import json
import resource
import tracemalloc
import gc
import sys
import os

try:
    import psutil
except Exception:
    psutil = None

from pypdf import PdfReader


def snapshot(label):
    r = resource.getrusage(resource.RUSAGE_SELF)
    tracemem = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
    objs = len(gc.get_objects())
    proc_rss = None
    if psutil:
        proc = psutil.Process(os.getpid())
        try:
            proc_rss = proc.memory_info().rss
        except Exception:
            proc_rss = None
    return {
        "label": label,
        "ts": time.time(),
        "ru_maxrss": getattr(r, "ru_maxrss", None),
        "tracemalloc_current": tracemem[0],
        "tracemalloc_peak": tracemem[1],
        "gc_objects": objs,
        "psutil_rss": proc_rss,
    }


def main(pdf_path: str, out_json: str):
    path = Path(pdf_path)
    out = Path(out_json)
    results = {"pid": os.getpid(), "steps": []}

    tracemalloc.start()
    gc.collect()
    results["steps"].append(snapshot("start"))

    reader = PdfReader(str(path))
    results["steps"].append(snapshot("after_open"))

    # Step: metadata
    results["steps"].append(snapshot("after_metadata"))

    # Step: enumerate pages
    page_count = len(reader.pages)
    results["page_count"] = page_count
    results["steps"].append(snapshot("after_enumerate"))

    # Step: extract text per page
    pages_text = []
    for i, page in enumerate(reader.pages, start=1):
        pages_text.append(page.extract_text() or "")
        if i % 10 == 0:
            # intermediate snapshot every 10 pages
            results["steps"].append(snapshot(f"after_text_page_{i}"))

    results["steps"].append(snapshot("after_text_extraction"))

    # Step: serialization
    serial = [{"page": i + 1, "text_len": len(t)} for i, t in enumerate(pages_text)]
    results["steps"].append(snapshot("after_serialization"))

    # capture tracemalloc top stats for investigation
    try:
        snap = tracemalloc.take_snapshot()
        stats = snap.statistics("lineno")[:20]
        top = []
        for s in stats:
            top.append({"trace": str(s.traceback), "size": s.size, "count": s.count})
        results["tracemalloc_top"] = top
    except Exception:
        results["tracemalloc_top"] = []

    # Cleanup
    del pages_text
    del serial
    del reader
    gc.collect()
    results["steps"].append(snapshot("after_cleanup"))

    tracemalloc.stop()

    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote profile to {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: profile_extraction.py <pdf_path> <out_json>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
