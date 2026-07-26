# AV-01 MAW Validation Scoring

Date: 2026-07-26

Scope:

- Project ID: `BID-2026-0002`
- Project name: `Music Academy of the West`
- Source-set status: duplicate retries cleaned, accidental `MAW_MBD-013` removed, seven real MAW source documents restored

## Baseline

Current live source set:

- `07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf`
- `Div 11 Equipment.pdf`
- `Div 27 Communications.pdf`
- `2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf`
- `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf`

Excluded from the source set:

- `MAW_MBD-013_Interior Scaffold Phasing.pdf` moved to `review/validation_artifacts/`
- `av00c-navigation-refresh-validation.pdf` moved to `review/validation_artifacts/`

## Preliminary Classification Pass

| File | Current Bucket | Content-Based Classification | Status |
| --- | --- | --- | --- |
| `07_Electrical for AV Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf` | drawings | drawing, electrical discipline | clear |
| `08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf` | drawings | drawing, audiovisual discipline | clear |
| `09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf` | drawings | drawing, theater/performance discipline | clear |
| `Div 11 Equipment.pdf` | schedules | specification-like section (`11 31 00`) with schedule packaging | mixed |
| `Div 27 Communications.pdf` | specifications | specification, audiovisual systems | clear |
| `2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf` | reports | acoustics report / narrative | clear |
| `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf` | drawings | design narrative / general document | mixed |

## Preliminary Scorecard

- Source-set completeness: `7/7`
- Duplicate hygiene: `0` remaining duplicate groups
- Classification clarity: `5/7` clear, `2/7` mixed
- Extraction note: all seven restored source documents have embedded text; `Div 11 Equipment.pdf` is partial but still readable without OCR

## Notes

- The accidental `MAW_MBD-013_Interior Scaffold Phasing.pdf` was removed from the live project source set and is no longer part of the AV-01 baseline.
- `Div 11 Equipment.pdf` is the main classification ambiguity in this set. Its filename and current bucket say “schedule,” but the content reads like a specification section.
- `MAW_MBD-018_Aurora Element - Design Narrative FINAL.pdf` is also content-ambiguous. It behaves like a narrative/general document more than a drawing.
- No retry-copy duplicates remain in the live project document tree.
