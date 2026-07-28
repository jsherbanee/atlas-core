"""Reproduction harness for large-upload memory incident.

Generates deterministic PDF fixtures of approximate sizes and runs the
file-backed intake path to collect measurements.
"""

from pathlib import Path
import json
from atlas_core.services.document_intake_service import DocumentIntakeService


def create_minimal_pdf(path: Path, target_bytes: int) -> None:
    """Create a minimal valid PDF file with a single page whose content stream
    is repeated to reach at least target_bytes in file size.
    """
    header = b"%PDF-1.4\n"
    # small static PDF preamble and objects; we'll compute offsets later
    # We'll craft a simple one-page PDF with a large content stream object.

    # content stream: simple text operations repeated
    line = b"BT /F1 12 Tf 72 720 Td (This is filler line.) Tj ET\n"
    repetitions = max(1, int(target_bytes / max(1, len(line))))
    stream = line * repetitions

    objs = []
    # 1: Catalog
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page
    objs.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    # 4: Font
    objs.append(
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    # 5: Content stream
    objs.append(b"5 0 obj\n<< /Length %d >>\nstream\n" % len(stream))
    objs.append(stream + b"\nendstream\nendobj\n")

    body = b"".join(objs)
    # naive xref: place entries with zeros; many readers accept this minimal form
    pdf = header + body
    # add trailer
    pdf += b"xref\n0 6\n0000000000 65535 f\n"
    # pad with dummy offsets
    for i in range(1, 6):
        pdf += b"0000000000 00000 n\n"
    pdf += b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"

    path.write_bytes(pdf)


def run_repro(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sizes = [
        ("small.pdf", 10 * 1024 * 1024),
        ("medium.pdf", 50 * 1024 * 1024),
        ("large.pdf", 170 * 1024 * 1024),
    ]
    results = []
    service = DocumentIntakeService()
    for name, size in sizes:
        fixture = output_dir / name
        print(f"Creating fixture {fixture} ~{size} bytes")
        create_minimal_pdf(fixture, size)
        # run file-backed intake
        session_id = f"repro-{fixture.stem}"
        result = service.build_session_package_from_file_paths(
            [(name, fixture)],
            uploads_root=output_dir,
            session_id=session_id,
            project_id="repro",
        )
        artifacts = result.package_path / ".artifacts"
        meas = artifacts / "measurements.jsonl"
        if meas.exists():
            for line in meas.read_text(encoding="utf-8").splitlines():
                results.append(json.loads(line))

    out = output_dir / "repro_summary.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote summary to {out}")


if __name__ == "__main__":
    root = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "validation"
        / "artifacts"
        / "large-upload"
    )
    run_repro(root)
