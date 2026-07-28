#!/usr/bin/env python3
import subprocess
import time
import os
import json
import csv
import shlex
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(REPO_ROOT, "docs", "validation", "artifacts", "large-upload")
os.makedirs(OUT_DIR, exist_ok=True)

VENV_PY = os.path.join(REPO_ROOT, ".venv", "bin", "python")
PY = VENV_PY if os.path.exists(VENV_PY) else sys.executable

SAMPLE_INTERVAL = 0.5


def pgrep_children(pid):
    try:
        out = subprocess.check_output(["/usr/bin/pgrep", "-P", str(pid)])
    except subprocess.CalledProcessError:
        return []
    lines = out.decode().strip().splitlines()
    return [int(x.strip()) for x in lines if x.strip()]


def collect_descendants(root_pid):
    seen = set()
    stack = [root_pid]
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.add(p)
        try:
            children = pgrep_children(p)
        except Exception:
            children = []
        stack.extend(children)
    return sorted(seen)


def sample_pids(pids):
    samples = []
    for pid in pids:
        try:
            out = subprocess.check_output(
                [
                    "/bin/ps",
                    "-p",
                    str(pid),
                    "-o",
                    "pid=",
                    "-o",
                    "ppid=",
                    "-o",
                    "comm=",
                    "-o",
                    "rss=",
                    "-o",
                    "vsz=",
                ]
            )
            parts = out.decode().strip().split(None, 4)
            if len(parts) >= 5:
                pid_s, ppid_s, comm, rss_s, vsz_s = parts
                samples.append(
                    {
                        "pid": int(pid_s),
                        "ppid": int(ppid_s),
                        "comm": comm,
                        "rss_kb": int(rss_s) if rss_s.isdigit() else None,
                        "vsz_kb": int(vsz_s) if vsz_s.isdigit() else None,
                    }
                )
        except subprocess.CalledProcessError:
            continue
    return samples


def main():
    repro_script = os.path.join(REPO_ROOT, "scripts", "repro_large_uploads.py")
    cmd = [PY, repro_script]
    print("Starting reproduction:", " ".join(shlex.quote(x) for x in cmd))
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", REPO_ROOT)
    proc = subprocess.Popen(cmd, env=env)
    samples = []
    peak_by_pid = {}
    try:
        while proc.poll() is None:
            now = time.time()
            pids = collect_descendants(proc.pid)
            pids.append(proc.pid)
            pids = sorted(set(pids))
            s = sample_pids(pids)
            for entry in s:
                entry["ts"] = now
                samples.append(entry)
                pid = entry["pid"]
                rss = entry.get("rss_kb") or 0
                prev = peak_by_pid.get(pid, 0)
                if rss > prev:
                    peak_by_pid[pid] = rss
            time.sleep(SAMPLE_INTERVAL)
    finally:
        # final capture after exit
        try:
            now = time.time()
            pids = collect_descendants(proc.pid)
            pids.append(proc.pid)
            pids = sorted(set(pids))
            s = sample_pids(pids)
            for entry in s:
                entry["ts"] = now
                samples.append(entry)
                pid = entry["pid"]
                rss = entry.get("rss_kb") or 0
                prev = peak_by_pid.get(pid, 0)
                if rss > prev:
                    peak_by_pid[pid] = rss
        except Exception:
            pass

    samples_f = os.path.join(OUT_DIR, "process-memory-samples.jsonl")
    with open(samples_f, "w") as fh:
        for rec in samples:
            fh.write(json.dumps(rec) + "\n")

    summary = {"peaks_kb": peak_by_pid, "sample_count": len(samples)}
    summary_f = os.path.join(OUT_DIR, "process-memory-summary.json")
    with open(summary_f, "w") as fh:
        json.dump(summary, fh, indent=2)

    # correlate with existing repro_summary.json if present
    repro_json = os.path.join(OUT_DIR, "repro_summary.json")
    if os.path.exists(repro_json):
        with open(repro_json, "r") as fh:
            stages = json.load(fh)
    else:
        stages = []

    # produce stage-memory-summary.csv
    csv_f = os.path.join(OUT_DIR, "stage-memory-summary.csv")
    with open(csv_f, "w", newline="") as csvfh:
        writer = csv.writer(csvfh)
        writer.writerow(
            [
                "stage",
                "pid",
                "ppid",
                "comm",
                "file",
                "size_bytes",
                "page_count",
                "ts_start",
                "ts_end",
                "peak_rss_kb",
                "samples",
            ]
        )
        for st in stages:
            ts_start = st.get("ts_start")
            ts_end = st.get("ts_end")
            extra = st.get("extra", {})
            file = extra.get("file") or extra.get("destination")
            size = extra.get("size")
            page_count = extra.get("page_count")
            # find samples in interval
            relevant = [
                s
                for s in samples
                if ts_start and ts_end and s["ts"] >= ts_start and s["ts"] <= ts_end
            ]
            # group by pid
            bypid = {}
            for r in relevant:
                pid = r["pid"]
                bypid.setdefault(pid, []).append(r)
            if not bypid:
                writer.writerow(
                    [
                        st.get("stage"),
                        "",
                        "",
                        "",
                        file,
                        size,
                        page_count,
                        ts_start,
                        ts_end,
                        "",
                        0,
                    ]
                )
            else:
                for pid, recs in bypid.items():
                    peak = max(r.get("rss_kb") or 0 for r in recs)
                    ppid = recs[0].get("ppid")
                    comm = recs[0].get("comm")
                    writer.writerow(
                        [
                            st.get("stage"),
                            pid,
                            ppid,
                            comm,
                            file,
                            size,
                            page_count,
                            ts_start,
                            ts_end,
                            peak,
                            len(recs),
                        ]
                    )

    # write reproduction.jsonl as newline JSON of stages
    repro_out = os.path.join(OUT_DIR, "reproduction.jsonl")
    with open(repro_out, "w") as fh:
        for st in stages:
            fh.write(json.dumps(st) + "\n")

    print("Wrote:", samples_f, summary_f, csv_f, repro_out)


if __name__ == "__main__":
    main()
