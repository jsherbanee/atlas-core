from atlas_core.domain import SpecificationDiscipline
from atlas_core.services import SpecificationIndexerService


def test_indexes_valid_raw_section():
    sections = SpecificationIndexerService().index_sections(
        [
            {
                "section_number": " 27 41 16 ",
                "title": " Integrated Audio-Video Systems ",
                "source_file": "specs.pdf",
                "page_start": 10,
                "page_end": 15,
            }
        ]
    )

    assert len(sections) == 1
    assert sections[0].section_id == "27-41-16"
    assert sections[0].section_number == "27 41 16"
    assert sections[0].title == "Integrated Audio-Video Systems"
    assert sections[0].discipline is SpecificationDiscipline.AUDIOVISUAL
    assert sections[0].source_file == "specs.pdf"
    assert sections[0].page_start == 10
    assert sections[0].page_end == 15


def test_skips_incomplete_records():
    sections = SpecificationIndexerService().index_sections(
        [
            {"section_number": "27 41 16"},
            {"title": "Integrated Audio-Video Systems"},
            {"section_number": " ", "title": "Integrated Audio-Video Systems"},
            {"section_number": "27 41 16", "title": "Integrated Audio-Video Systems"},
        ]
    )

    assert len(sections) == 1
    assert sections[0].section_number == "27 41 16"


def test_infers_audiovisual_from_27_41():
    discipline = SpecificationIndexerService().infer_discipline("27 41 16")

    assert discipline is SpecificationDiscipline.AUDIOVISUAL


def test_infers_theatrical_from_11_61():
    discipline = SpecificationIndexerService().infer_discipline("11 61 00")

    assert discipline is SpecificationDiscipline.THEATRICAL


def test_infers_drapery_from_title():
    discipline = SpecificationIndexerService().infer_discipline(
        "12 00 00",
        "Stage Curtain and Traveler",
    )

    assert discipline is SpecificationDiscipline.DRAPERY


def test_infers_electrical_from_26():
    discipline = SpecificationIndexerService().infer_discipline("26 05 00")

    assert discipline is SpecificationDiscipline.ELECTRICAL


def test_infers_security_from_28():
    discipline = SpecificationIndexerService().infer_discipline("28 13 00")

    assert discipline is SpecificationDiscipline.SECURITY


def test_section_id_normalization():
    sections = SpecificationIndexerService().index_sections(
        [
            {
                "section_number": " 27 41 16 ",
                "title": "Integrated Audio-Video Systems",
            }
        ]
    )

    assert sections[0].section_id == "27-41-16"


def test_carries_manufacturers():
    sections = SpecificationIndexerService().index_sections(
        [
            {
                "section_number": "27 41 16",
                "title": "Integrated Audio-Video Systems",
                "manufacturers": [" QSC ", "Shure"],
            }
        ]
    )

    assert sections[0].manufacturers == ["QSC", "Shure"]
