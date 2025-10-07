from __future__ import annotations

import sys
from xml.etree import ElementTree as ET

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate.metadata import DatasetMetadata, Participant
from oratiotranscripta.annotate.parsers import EditedUtterance
from oratiotranscripta.annotate.tei import build_tei_document
from oratiotranscripta.asr import WordMetadata


NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _make_metadata() -> DatasetMetadata:
    return DatasetMetadata(
        project="Projeto X",
        event="Evento de Teste",
        participants=[
            Participant(name="Ana", role="moderadora", aliases=["Speaker 1"]),
            Participant(name="Bruno", role="palestrante", aliases=["Speaker 2"]),
        ],
        dates=["2024-01-01"],
        coverage={"spatial": "Online"},
        license="CC-BY-4.0",
        editors=["Maria Editor"],
    )


def test_build_tei_document_generates_valid_structure() -> None:
    metadata = _make_metadata()
    utterances = [
        EditedUtterance(
            start=0.0,
            end=1.5,
            speaker="Speaker 1",
            text="Olá mundo",
            segments=(1,),
        ),
        EditedUtterance(
            start=1.5,
            end=2.5,
            speaker="Speaker 2",
            text="Tudo bem?",
            segments=(2,),
        ),
    ]
    word_index = {
        1: [
            WordMetadata(word="Olá", start=0.0, end=0.5),
            WordMetadata(word="mundo", start=0.5, end=1.5),
        ],
        2: [
            WordMetadata(word="Tudo", start=1.5, end=2.0),
            WordMetadata(word="bem?", start=2.0, end=2.5),
        ],
    }

    xml_bytes = build_tei_document(metadata, utterances, word_index=word_index)

    root = ET.fromstring(xml_bytes)

    header = root.find("tei:teiHeader", NS)
    assert header is not None
    file_desc = header.find("tei:fileDesc", NS)
    assert file_desc is not None
    licence = file_desc.find(".//tei:licence", NS)
    assert licence is not None
    assert licence.text == "CC-BY-4.0"

    resp_stmt = file_desc.find(".//tei:respStmt", NS)
    assert resp_stmt is not None
    resp_names = [name.text for name in resp_stmt.findall("tei:name", NS)]
    assert resp_names == ["Maria Editor"]

    list_person = header.find(".//tei:listPerson", NS)
    assert list_person is not None
    people = list_person.findall("tei:person", NS)
    assert len(people) == 2
    assert people[0].attrib.get("{http://www.w3.org/XML/1998/namespace}id") == "P0001"

    timeline = root.find(".//tei:timeline", NS)
    assert timeline is not None
    points = {when.attrib["{http://www.w3.org/XML/1998/namespace}id"]: when.attrib["absolute"] for when in timeline}
    assert "T0000" in points and "T0003" in points

    first_u = root.find(".//tei:div[@type='transcript']/tei:u[1]", NS)
    assert first_u is not None
    assert first_u.attrib["who"] == "#P0001"
    assert first_u.attrib["start"].startswith("#T")
    edited_seg = first_u.find("tei:seg[@type='edited']", NS)
    assert edited_seg is not None and edited_seg.text == "Olá mundo"
    token_words = first_u.findall("tei:seg[@type='tokens']/tei:w", NS)
    assert [w.text for w in token_words] == ["Olá", "mundo"]
    assert token_words[0].attrib["start"].startswith("#T")


def test_build_tei_document_requires_utterances() -> None:
    metadata = _make_metadata()
    try:
        build_tei_document(metadata, [])
    except ValueError as exc:
        assert "al menos uma".split()[-1] in str(exc).lower()
    else:  # pragma: no cover - verificação negativa
        raise AssertionError("Era esperado ValueError para lista vazia de falas")

