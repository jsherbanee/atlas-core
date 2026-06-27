import pytest

from atlas_core.domain import SpecificationDiscipline, SpecificationSection


def test_creating_valid_specification_section():
    section = SpecificationSection(
        section_id=" 27-4116 ",
        section_number=" 27 41 16 ",
        title=" Integrated Audio-Video Systems ",
        discipline=SpecificationDiscipline.AUDIOVISUAL,
        source_file=" specs.pdf ",
        page_start=10,
        page_end=15,
        manufacturers=[" QSC ", " Shure "],
        notes=[" Coordinate with drawings. "],
        confidence=0.9,
    )

    assert section.section_id == "27-4116"
    assert section.section_number == "27 41 16"
    assert section.title == "Integrated Audio-Video Systems"
    assert section.discipline is SpecificationDiscipline.AUDIOVISUAL
    assert section.source_file == "specs.pdf"
    assert section.page_start == 10
    assert section.page_end == 15
    assert section.manufacturers == ["QSC", "Shure"]
    assert section.notes == ["Coordinate with drawings."]
    assert section.confidence == 0.9


def test_accepting_string_discipline():
    section = SpecificationSection(
        section_id="27-4116",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
        discipline="audiovisual",
    )

    assert section.discipline is SpecificationDiscipline.AUDIOVISUAL


def test_rejecting_blank_section_number():
    with pytest.raises(ValueError, match="section_number cannot be blank"):
        SpecificationSection(
            section_id="27-4116",
            section_number=" ",
            title="Integrated Audio-Video Systems",
        )


def test_rejecting_blank_title():
    with pytest.raises(ValueError, match="title cannot be blank"):
        SpecificationSection(
            section_id="27-4116",
            section_number="27 41 16",
            title=" ",
        )


def test_rejecting_invalid_confidence():
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        SpecificationSection(
            section_id="27-4116",
            section_number="27 41 16",
            title="Integrated Audio-Video Systems",
            confidence=-0.1,
        )


def test_rejecting_negative_page_start():
    with pytest.raises(ValueError, match="page_start cannot be negative"):
        SpecificationSection(
            section_id="27-4116",
            section_number="27 41 16",
            title="Integrated Audio-Video Systems",
            page_start=-1,
        )


def test_rejecting_page_end_before_page_start():
    with pytest.raises(ValueError, match="page_end cannot be less than page_start"):
        SpecificationSection(
            section_id="27-4116",
            section_number="27 41 16",
            title="Integrated Audio-Video Systems",
            page_start=10,
            page_end=9,
        )


def test_adding_manufacturers():
    section = SpecificationSection(
        section_id="27-4116",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
    )

    section.add_manufacturer(" QSC ")
    section.add_manufacturer("Shure")

    assert section.manufacturers == ["QSC", "Shure"]


def test_adding_notes():
    section = SpecificationSection(
        section_id="27-4116",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
    )

    section.add_note(" Confirm acceptable manufacturers. ")
    section.add_note("Review warranty language.")

    assert section.notes == [
        "Confirm acceptable manufacturers.",
        "Review warranty language.",
    ]


def test_to_dict_output():
    section = SpecificationSection(
        section_id="27-4116",
        section_number="27 41 16",
        title="Integrated Audio-Video Systems",
        discipline=SpecificationDiscipline.AUDIOVISUAL,
        source_file="specs.pdf",
        page_start=10,
        page_end=15,
        manufacturers=["QSC", "Shure"],
        notes=["Coordinate with drawings."],
        confidence=0.85,
    )

    assert section.to_dict() == {
        "section_id": "27-4116",
        "section_number": "27 41 16",
        "title": "Integrated Audio-Video Systems",
        "discipline": "audiovisual",
        "source_file": "specs.pdf",
        "page_start": 10,
        "page_end": 15,
        "manufacturers": ["QSC", "Shure"],
        "notes": ["Coordinate with drawings."],
        "confidence": 0.85,
    }
