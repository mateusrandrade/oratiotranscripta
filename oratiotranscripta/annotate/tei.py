"""Utilitários para geração de documentos TEI a partir das anotações."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from xml.etree import ElementTree as ET

from ..asr import WordMetadata
from .metadata import DatasetMetadata, Participant
from .parsers import EditedUtterance

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", TEI_NS)


try:  # pragma: no cover - dependência opcional
    from lxml import etree as LET
except ImportError:  # pragma: no cover - fallback
    LET = None  # type: ignore[assignment]


TEI_LITE_RNG = """
<rng:grammar xmlns:rng="http://relaxng.org/ns/structure/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0">
  <rng:start>
    <rng:element name="TEI" ns="http://www.tei-c.org/ns/1.0">
      <rng:zeroOrMore>
        <rng:attribute>
          <rng:anyName />
        </rng:attribute>
      </rng:zeroOrMore>
      <rng:ref name="teiHeader" />
      <rng:ref name="text" />
    </rng:element>
  </rng:start>
  <rng:define name="teiHeader">
    <rng:element name="teiHeader" ns="http://www.tei-c.org/ns/1.0">
      <rng:ref name="fileDesc" />
      <rng:zeroOrMore>
        <rng:choice>
          <rng:text />
          <rng:ref name="anyElement" />
        </rng:choice>
      </rng:zeroOrMore>
    </rng:element>
  </rng:define>
  <rng:define name="fileDesc">
    <rng:element name="fileDesc" ns="http://www.tei-c.org/ns/1.0">
      <rng:zeroOrMore>
        <rng:choice>
          <rng:text />
          <rng:ref name="anyElement" />
        </rng:choice>
      </rng:zeroOrMore>
    </rng:element>
  </rng:define>
  <rng:define name="text">
    <rng:element name="text" ns="http://www.tei-c.org/ns/1.0">
      <rng:zeroOrMore>
        <rng:choice>
          <rng:text />
          <rng:ref name="anyElement" />
        </rng:choice>
      </rng:zeroOrMore>
    </rng:element>
  </rng:define>
  <rng:define name="anyElement">
    <rng:element>
      <rng:anyName />
      <rng:zeroOrMore>
        <rng:attribute>
          <rng:anyName />
        </rng:attribute>
      </rng:zeroOrMore>
      <rng:zeroOrMore>
        <rng:choice>
          <rng:text />
          <rng:ref name="anyElement" />
        </rng:choice>
      </rng:zeroOrMore>
    </rng:element>
  </rng:define>
</rng:grammar>
""".strip()


if LET is not None:  # pragma: no cover - depende do ambiente de testes
    try:
        _RELAX_NG_VALIDATOR = LET.RelaxNG(LET.fromstring(TEI_LITE_RNG.encode("utf-8")))
    except LET.XMLSyntaxError:  # pragma: no cover - schema inválido
        _RELAX_NG_VALIDATOR = None
else:  # pragma: no cover - dependência opcional ausente
    _RELAX_NG_VALIDATOR = None


WordIndex = Mapping[int, Sequence[WordMetadata]]


def build_tei_document(
    metadata: DatasetMetadata,
    utterances: Sequence[EditedUtterance],
    *,
    word_index: Optional[WordIndex] = None,
    validate: bool = True,
) -> bytes:
    """Gera um documento TEI a partir dos metadados e das falas revisadas."""

    if not utterances:
        raise ValueError("É necessário fornecer ao menos uma fala editada")

    speakers = [utt.speaker for utt in utterances if utt.speaker]
    if speakers:
        metadata.validate_speakers(speakers)

    header, speaker_lookup = _build_header(metadata)
    timeline, timeline_lookup = _build_timeline(utterances, word_index)

    root = ET.Element(_tei_tag("TEI"))
    root.append(header)

    text_el = ET.SubElement(root, _tei_tag("text"))
    body_el = ET.SubElement(text_el, _tei_tag("body"))
    body_el.append(timeline)
    div_el = ET.SubElement(body_el, _tei_tag("div"), attrib={"type": "transcript"})

    for index, utterance in enumerate(utterances, start=1):
        words = _collect_words(utterance, word_index)
        u_el = _build_utterance_element(
            utterance,
            words,
            speaker_lookup,
            timeline_lookup,
            position=index,
        )
        div_el.append(u_el)

    tree = ET.ElementTree(root)
    if validate:
        _validate_tree(tree)
    ET.indent(tree, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _build_header(metadata: DatasetMetadata) -> Tuple[ET.Element, Dict[str, str]]:
    header = ET.Element(_tei_tag("teiHeader"))
    header.append(_build_file_desc(metadata))
    profile_desc, speaker_lookup = _build_profile_desc(metadata)
    header.append(profile_desc)
    return header, speaker_lookup


def _build_file_desc(metadata: DatasetMetadata) -> ET.Element:
    file_desc = ET.Element(_tei_tag("fileDesc"))

    title_stmt = ET.SubElement(file_desc, _tei_tag("titleStmt"))
    title_el = ET.SubElement(title_stmt, _tei_tag("title"))
    title_el.text = metadata.project

    event_title = ET.SubElement(title_stmt, _tei_tag("title"), attrib={"type": "event"})
    event_title.text = metadata.event

    if metadata.editors:
        resp_stmt = ET.SubElement(title_stmt, _tei_tag("respStmt"))
        resp_el = ET.SubElement(resp_stmt, _tei_tag("resp"))
        resp_el.text = "Revisão humana"
        for editor in metadata.editors:
            name_el = ET.SubElement(resp_stmt, _tei_tag("name"))
            name_el.text = editor

    publication_stmt = ET.SubElement(file_desc, _tei_tag("publicationStmt"))
    publisher_el = ET.SubElement(publication_stmt, _tei_tag("publisher"))
    publisher_el.text = metadata.project
    availability = ET.SubElement(publication_stmt, _tei_tag("availability"))
    licence_el = ET.SubElement(availability, _tei_tag("licence"))
    licence_el.text = metadata.license or "Licença não informada"

    source_desc = ET.SubElement(file_desc, _tei_tag("sourceDesc"))
    summary = ET.SubElement(source_desc, _tei_tag("p"))
    summary.text = f"Evento: {metadata.event}"
    if metadata.coverage:
        coverage_list = ET.SubElement(source_desc, _tei_tag("list"), attrib={"type": "coverage"})
        for key, value in metadata.coverage.items():
            item = ET.SubElement(coverage_list, _tei_tag("item"), attrib={"type": str(key)})
            item.text = str(value)

    return file_desc


def _build_profile_desc(metadata: DatasetMetadata) -> Tuple[ET.Element, Dict[str, str]]:
    profile_desc = ET.Element(_tei_tag("profileDesc"))

    if metadata.dates:
        creation_el = ET.SubElement(profile_desc, _tei_tag("creation"))
        for date in metadata.dates:
            date_el = ET.SubElement(creation_el, _tei_tag("date"))
            date_el.set("when", date)
            date_el.text = date

    partic_desc = ET.SubElement(profile_desc, _tei_tag("particDesc"))
    list_person, speaker_lookup = _build_list_person(metadata.participants)
    partic_desc.append(list_person)

    if metadata.coverage:
        setting_desc = ET.SubElement(profile_desc, _tei_tag("settingDesc"))
        for key, value in metadata.coverage.items():
            setting = ET.SubElement(setting_desc, _tei_tag("setting"), attrib={"type": str(key)})
            setting.text = str(value)

    return profile_desc, speaker_lookup


def _build_list_person(participants: Sequence[Participant]) -> Tuple[ET.Element, Dict[str, str]]:
    list_person = ET.Element(_tei_tag("listPerson"))
    speaker_lookup: Dict[str, str] = {}
    for index, participant in enumerate(participants, start=1):
        person_el = ET.SubElement(list_person, _tei_tag("person"))
        xml_id = f"P{index:04d}"
        person_el.set(_xml_attr("id"), xml_id)

        name_el = ET.SubElement(person_el, _tei_tag("persName"))
        name_el.text = participant.name

        if participant.role:
            role_el = ET.SubElement(person_el, _tei_tag("roleName"))
            role_el.text = participant.role

        for alias in participant.aliases:
            alias_el = ET.SubElement(person_el, _tei_tag("persName"), attrib={"type": "alias"})
            alias_el.text = alias

        for label in participant.iter_all_names():
            speaker_lookup[label.casefold()] = xml_id

        for key, value in participant.extra.items():
            extra_el = ET.SubElement(person_el, _tei_tag("note"), attrib={"type": str(key)})
            extra_el.text = str(value)

    return list_person, speaker_lookup


def _build_timeline(
    utterances: Sequence[EditedUtterance],
    word_index: Optional[WordIndex],
) -> Tuple[ET.Element, Dict[Decimal, str]]:
    points = _collect_time_points(utterances, word_index)
    timeline = ET.Element(_tei_tag("timeline"), attrib={"unit": "s"})
    lookup: Dict[Decimal, str] = {}
    for index, point in enumerate(points):
        xml_id = f"T{index:04d}"
        when_el = ET.SubElement(timeline, _tei_tag("when"))
        when_el.set(_xml_attr("id"), xml_id)
        when_el.set("absolute", _format_decimal(point))
        lookup[point] = xml_id
    return timeline, lookup


def _collect_time_points(
    utterances: Sequence[EditedUtterance],
    word_index: Optional[WordIndex],
) -> List[Decimal]:
    points: MutableMapping[Decimal, None] = {}
    for utterance in utterances:
        points[_normalise_time(utterance.start)] = None
        points[_normalise_time(utterance.end)] = None
    if word_index:
        for words in word_index.values():
            for word in words:
                if word.start is not None:
                    points[_normalise_time(word.start)] = None
                if word.end is not None:
                    points[_normalise_time(word.end)] = None
    if not points:
        points[Decimal("0.000")] = None
    return sorted(points)


def _collect_words(
    utterance: EditedUtterance,
    word_index: Optional[WordIndex],
) -> List[WordMetadata]:
    if not word_index:
        return []
    collected: List[WordMetadata] = []
    for segment_id in utterance.segments:
        candidates = _lookup_words(word_index, segment_id)
        for word in candidates:
            collected.append(word)
    collected.sort(key=lambda item: (_word_sort_key(item.start), _word_sort_key(item.end)))
    return collected


def _lookup_words(word_index: WordIndex, segment_id: int) -> Sequence[WordMetadata]:
    if segment_id in word_index:
        return word_index[segment_id]
    str_key = str(segment_id)
    if str_key in word_index:  # type: ignore[operator]
        return word_index[str_key]  # type: ignore[index]
    return word_index.get(segment_id, ())  # type: ignore[call-arg]


def _word_sort_key(value: Optional[float]) -> Tuple[int, float]:
    if value is None:
        return (1, 0.0)
    return (0, float(value))


def _build_utterance_element(
    utterance: EditedUtterance,
    words: Sequence[WordMetadata],
    speaker_lookup: Mapping[str, str],
    timeline_lookup: Mapping[Decimal, str],
    *,
    position: int,
) -> ET.Element:
    attributes = {"n": str(position)}
    if utterance.speaker:
        speaker_id = speaker_lookup.get(utterance.speaker.casefold())
        if speaker_id:
            attributes["who"] = f"#{speaker_id}"
    start_ref = _timeline_reference(utterance.start, timeline_lookup)
    end_ref = _timeline_reference(utterance.end, timeline_lookup)
    if start_ref:
        attributes["start"] = start_ref
    if end_ref:
        attributes["end"] = end_ref

    u_el = ET.Element(_tei_tag("u"), attrib=attributes)

    if utterance.text:
        seg_el = ET.SubElement(u_el, _tei_tag("seg"), attrib={"type": "edited"})
        seg_el.text = utterance.text

    if words:
        tokens_el = ET.SubElement(u_el, _tei_tag("seg"), attrib={"type": "tokens"})
        for word in words:
            w_attrib = {}
            start_token = _timeline_reference(word.start, timeline_lookup)
            end_token = _timeline_reference(word.end, timeline_lookup)
            if start_token:
                w_attrib["start"] = start_token
            if end_token:
                w_attrib["end"] = end_token
            w_el = ET.SubElement(tokens_el, _tei_tag("w"), attrib=w_attrib)
            w_el.text = word.word

    return u_el


def _timeline_reference(
    value: Optional[float],
    timeline_lookup: Mapping[Decimal, str],
) -> Optional[str]:
    if value is None:
        return None
    key = _normalise_time(value)
    try:
        xml_id = timeline_lookup[key]
    except KeyError:
        return None
    return f"#{xml_id}"


def _validate_tree(tree: ET.ElementTree) -> None:
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8")
    if _RELAX_NG_VALIDATOR is not None:  # pragma: no cover - depende do ambiente
        _RELAX_NG_VALIDATOR.assertValid(LET.fromstring(xml_bytes))
        return
    _basic_structure_check(tree.getroot())


def _basic_structure_check(root: ET.Element) -> None:
    if root.tag != _tei_tag("TEI"):
        raise ValueError("Documento TEI inválido: raiz deve ser <TEI>")
    header = root.find(_tei_path("teiHeader"))
    if header is None:
        raise ValueError("Documento TEI inválido: elemento <teiHeader> ausente")
    if header.find(_tei_path("fileDesc")) is None:
        raise ValueError("Documento TEI inválido: elemento <fileDesc> ausente")
    if root.find(_tei_path("text")) is None:
        raise ValueError("Documento TEI inválido: elemento <text> ausente")


def _normalise_time(value: float) -> Decimal:
    decimal_value = Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return decimal_value


def _format_decimal(value: Decimal) -> str:
    normalised = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    text = format(normalised, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _tei_tag(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _tei_path(tag: str) -> str:
    return f".//{{{TEI_NS}}}{tag}"


def _xml_attr(name: str) -> str:
    return f"{{{XML_NS}}}{name}"


__all__ = ["build_tei_document"]

