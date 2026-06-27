"""Drawing sheet indexing helpers for Atlas Core services."""

from typing import Any

from atlas_core.domain import DrawingDiscipline, DrawingSheet


class DrawingIndexerService:
    def index_sheets(self, raw_sheets: list[dict]) -> list[DrawingSheet]:
        sheets: list[DrawingSheet] = []

        for raw_sheet in raw_sheets:
            sheet_number = self._text(raw_sheet.get("sheet_number"))
            title = self._text(raw_sheet.get("title"))
            if sheet_number is None or title is None:
                continue

            discipline = raw_sheet.get("discipline")
            if discipline is None:
                discipline = self.infer_discipline(sheet_number, title)

            sheets.append(
                DrawingSheet(
                    sheet_id=self._sheet_id(sheet_number),
                    sheet_number=sheet_number,
                    title=title,
                    discipline=discipline,
                    revision=raw_sheet.get("revision"),
                    issue_date=raw_sheet.get("issue_date"),
                    source_file=raw_sheet.get("source_file"),
                    page_number=raw_sheet.get("page_number"),
                )
            )

        return sheets

    def infer_discipline(
        self,
        sheet_number: str,
        title: str = "",
    ) -> DrawingDiscipline:
        normalized_sheet_number = sheet_number.strip().upper()
        normalized_title = title.strip().casefold()

        if normalized_sheet_number.startswith("AV"):
            return DrawingDiscipline.AUDIOVISUAL

        if normalized_sheet_number.startswith(("TL", "LX")):
            return DrawingDiscipline.LIGHTING

        if normalized_sheet_number.startswith("FA"):
            return DrawingDiscipline.FIRE_ALARM

        if normalized_sheet_number.startswith(("TCOM", "T-")):
            return DrawingDiscipline.TELECOM

        if normalized_sheet_number.startswith("SEC"):
            return DrawingDiscipline.SECURITY

        if normalized_sheet_number.startswith("A"):
            return DrawingDiscipline.ARCHITECTURAL

        if normalized_sheet_number.startswith("E"):
            return DrawingDiscipline.ELECTRICAL

        if normalized_sheet_number.startswith("T"):
            return DrawingDiscipline.THEATRICAL

        if normalized_sheet_number.startswith("S"):
            return DrawingDiscipline.STRUCTURAL

        if normalized_sheet_number.startswith("M"):
            return DrawingDiscipline.MECHANICAL

        if normalized_sheet_number.startswith("P"):
            return DrawingDiscipline.PLUMBING

        if (
            "audiovisual" in normalized_title
            or "audio visual" in normalized_title
        ):
            return DrawingDiscipline.AUDIOVISUAL

        if "theatrical" in normalized_title:
            return DrawingDiscipline.THEATRICAL

        if "lighting" in normalized_title:
            return DrawingDiscipline.LIGHTING

        return DrawingDiscipline.UNKNOWN

    @staticmethod
    def _sheet_id(sheet_number: str) -> str:
        return "-".join(sheet_number.strip().casefold().split())

    @staticmethod
    def _text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        return normalized or None
