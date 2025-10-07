"""Estruturas e utilitários para metadados de datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass
class Participant:
    """Representa uma pessoa participante do evento."""

    name: str
    role: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_object(cls, value: Any) -> "Participant":
        if isinstance(value, str):
            return cls(name=value)
        if not isinstance(value, Mapping):
            raise ValueError("Participante deve ser string ou mapeamento")
        data = dict(value)
        try:
            name = str(data.pop("name"))
        except KeyError as exc:
            raise ValueError("Participante precisa do campo 'name'") from exc
        aliases_obj = data.pop("aliases", [])
        if isinstance(aliases_obj, str):
            aliases = [aliases_obj]
        elif isinstance(aliases_obj, Iterable):
            aliases = [str(alias) for alias in aliases_obj]
        else:
            raise ValueError("Campo 'aliases' deve ser string ou lista")
        role = data.pop("role", None)
        return cls(name=name, role=role, aliases=aliases, extra=data)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": self.name}
        if self.role is not None:
            payload["role"] = self.role
        if self.aliases:
            payload["aliases"] = list(self.aliases)
        payload.update(self.extra)
        return payload

    def iter_all_names(self) -> Iterable[str]:
        yield self.name
        for alias in self.aliases:
            yield alias


@dataclass
class DatasetMetadata:
    """Modelo estruturado dos metadados do dataset."""

    project: str
    event: str
    participants: List[Participant]
    dates: List[str]
    coverage: Dict[str, Any] = field(default_factory=dict)
    license: str = ""
    editors: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DatasetMetadata":
        mapping = dict(data)
        try:
            project = str(mapping.pop("project"))
            event = str(mapping.pop("event"))
        except KeyError as exc:
            raise ValueError(f"Campo obrigatório ausente: {exc.args[0]}") from exc

        participants_obj = mapping.pop("participants", None)
        if participants_obj is None:
            raise ValueError("Metadados precisam listar 'participants'")
        participants = _parse_participants(participants_obj)

        dates_obj = mapping.pop("dates", [])
        if isinstance(dates_obj, str):
            dates = [dates_obj]
        elif isinstance(dates_obj, Iterable):
            dates = [str(item) for item in dates_obj]
        else:
            raise ValueError("Campo 'dates' deve ser string ou lista")

        coverage_obj = mapping.pop("coverage", {})
        if isinstance(coverage_obj, Mapping):
            coverage = dict(coverage_obj)
        else:
            coverage = {"value": coverage_obj}

        license_value = mapping.pop("license", "")
        license_text = str(license_value) if license_value is not None else ""

        editors_obj = mapping.pop("editors", [])
        if isinstance(editors_obj, str):
            editors = [editors_obj]
        elif isinstance(editors_obj, Iterable):
            editors = [str(item) for item in editors_obj]
        else:
            raise ValueError("Campo 'editors' deve ser string ou lista")

        extra = mapping
        instance = cls(
            project=project,
            event=event,
            participants=participants,
            dates=dates,
            coverage=coverage,
            license=license_text,
            editors=editors,
            extra=extra,
        )
        instance._build_indices()
        return instance

    def _build_indices(self) -> None:
        self._alias_to_name: Dict[str, str] = {}
        for participant in self.participants:
            for label in participant.iter_all_names():
                key = label.casefold()
                if key in self._alias_to_name and self._alias_to_name[key] != participant.name:
                    raise ValueError(
                        f"Alias duplicado nos participantes: {label}"
                    )
                self._alias_to_name[key] = participant.name

    def resolve_speaker(self, speaker: str) -> str:
        if not hasattr(self, "_alias_to_name"):
            self._build_indices()
        key = speaker.casefold()
        try:
            return self._alias_to_name[key]
        except KeyError as exc:
            raise ValueError(f"Speaker não registrado: {speaker}") from exc

    def validate_speakers(self, speakers: Iterable[str]) -> None:
        if not hasattr(self, "_alias_to_name"):
            self._build_indices()
        unknown = sorted(
            {
                speaker
                for speaker in speakers
                if speaker and speaker.casefold() not in self._alias_to_name
            }
        )
        if unknown:
            raise ValueError(
                "Speakers ausentes nos metadados: " + ", ".join(unknown)
            )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "project": self.project,
            "event": self.event,
            "participants": [participant.to_dict() for participant in self.participants],
            "dates": list(self.dates),
            "coverage": dict(self.coverage),
            "license": self.license,
            "editors": list(self.editors),
        }
        payload.update(self.extra)
        return payload


def _parse_participants(obj: Any) -> List[Participant]:
    if isinstance(obj, Mapping):
        normalised: List[Any] = []
        for key, value in obj.items():
            if isinstance(value, Mapping):
                entry = dict(value)
                entry.setdefault("name", str(key))
            elif isinstance(value, str):
                entry = {"name": value}
            else:
                raise ValueError("Valores de 'participants' precisam ser mapeamentos ou strings")
            normalised.append(entry)
        items = normalised
    elif isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        items = obj
    else:
        raise ValueError("Campo 'participants' deve ser lista ou mapeamento")
    participants = [Participant.from_object(item) for item in items]
    if not participants:
        raise ValueError("Lista de participantes não pode estar vazia")
    return participants


__all__ = ["DatasetMetadata", "Participant"]
