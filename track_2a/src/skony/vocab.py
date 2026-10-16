"""Controlled vocabularies: loading, normalisation, deterministic mapping.

Maps *reviewed or extracted* raw labels (e.g. ``affair_type_raw``) to stable
vocabulary term IDs. The mapping is a separate, versioned object: the raw
source value is never overwritten, and every mapping records its rule and
relation, compatible with ``review_contracts.MappingRule``.

No third-party dependencies: the bundled ``*.yaml`` files use a restricted
subset parsed here (single-level ``key: value`` scalars, ``[a, b]`` inline
lists, ``{k: v}`` inline dicts, 2-space indents, ``#`` comments). Anything
outside that subset raises ``VocabParseError`` instead of being silently
misread.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VOCAB_DIR = Path(__file__).resolve().parent / "vocab"

VOCAB_FILES = {
    "affair_type": "affair_types.yaml",
    "actor_role": "actor_roles.yaml",
    "procedural_state": "procedural_states.yaml",
    "decision_outcome": "decision_outcomes.yaml",
}

Relation = Literal["exact_in_scope", "broader", "narrower", "related", "unmapped"]


class VocabParseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Restricted-subset parser
# ---------------------------------------------------------------------------

_SCALAR_RE = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z0-9_.\-]+):(?: (?P<val>.*))?$")
_LIST_ITEM_RE = re.compile(r"^(?P<indent> *)- (?P<val>.*)$")


def _parse_inline(text: str):
    """Parse ``[a, b]`` / ``{k: v}`` / plain scalar (no nested collections)."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [v.strip() for v in inner.split(",")] if inner else []
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        out = {}
        if not inner:
            return out
        for part in inner.split(","):
            if ":" not in part:
                raise VocabParseError(f"Bad inline dict item: {part!r}")
            k, _, v = part.partition(":")
            out[k.strip()] = v.strip()
        return out
    return text


def load_vocab_file(path: Path) -> dict:
    """Parse one restricted-subset vocabulary file into plain dicts."""
    header: dict[str, str] = {}
    terms: list[dict] = []
    current: dict | None = None
    current_key: str | None = None
    section: str | None = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()

        # top-level section markers
        if stripped in ("vocabulary:", "terms:"):
            section = stripped[:-1]
            current_key = None
            continue

        item = _LIST_ITEM_RE.match(line)
        if item:
            indent = len(item.group("indent"))
            val = item.group("val")
            if section == "terms" and indent == 2 and val.startswith("id:"):
                current = {"id": _parse_inline(val.split(":", 1)[1])}
                terms.append(current)
                current_key = None
                continue
            if current is not None and current_key is not None and indent >= 4:
                target = current.setdefault(current_key, [])
                if not isinstance(target, list):
                    raise VocabParseError(f"{path.name}:{lineno}: list under non-list key {current_key!r}")
                target.append(_parse_inline(val))
                continue
            raise VocabParseError(f"{path.name}:{lineno}: unexpected list item {stripped!r}")

        kv = _SCALAR_RE.match(line)
        if not kv:
            raise VocabParseError(f"{path.name}:{lineno}: cannot parse line {stripped!r}")
        indent = len(kv.group("indent"))
        key, val = kv.group("key"), kv.group("val")
        if indent == 0:
            raise VocabParseError(f"{path.name}:{lineno}: unexpected top-level key {key!r}")

        if section == "vocabulary":
            if val is None or val == "":
                raise VocabParseError(f"{path.name}:{lineno}: vocabulary header must be scalar")
            header[key] = _parse_inline(val)
            continue

        if section == "terms":
            if current is None:
                raise VocabParseError(f"{path.name}:{lineno}: key before first term id")
            if val is None or val == "":
                # opening a nested block; decide list-vs-dict lazily
                current[key] = {}
                current_key = key
                continue
            if indent == 4:
                parsed = _parse_inline(val)
                current[key] = parsed
                current_key = key if isinstance(parsed, dict) and not parsed else None
                # empty inline dict `{...}` handled above; keep key for nested alias blocks
                if key == "aliases" and parsed == {}:
                    current_key = key
                continue
            if indent >= 6 and current_key:
                block = current.get(current_key)
                if isinstance(block, dict):
                    block[key] = _parse_inline(val)
                elif isinstance(block, list):
                    raise VocabParseError(f"{path.name}:{lineno}: key inside list block {current_key!r}")
                else:
                    raise VocabParseError(f"{path.name}:{lineno}: dangling nested key {key!r}")
                continue
            raise VocabParseError(f"{path.name}:{lineno}: bad indent for {key!r}")

    if "id" not in header or "version" not in header:
        raise VocabParseError(f"{path.name}: vocabulary header needs id and version")
    if not terms:
        raise VocabParseError(f"{path.name}: no terms parsed")
    return {"header": header, "terms": terms}


# ---------------------------------------------------------------------------
# Vocabulary model
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Deterministic label normalisation: NFKD, strip diacritics, casefold,
    collapse all whitespace/punctuation runs to single spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    folded = stripped.casefold()
    return " ".join(re.sub(r"[^\w]+", " ", folded, flags=re.UNICODE).split())


@dataclass(frozen=True)
class Term:
    id: str
    pref: dict[str, str]
    definition: str
    broader: str | None
    maps: dict[str, str]
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Vocabulary:
    id: str
    version: str
    terms: tuple[Term, ...]

    @property
    def index(self) -> dict[str, Term]:
        return {t.id: t for t in self.terms}

    def alias_table(self) -> dict[str, str]:
        """normalised surface form -> term id (pref labels included)."""
        table: dict[str, str] = {}
        for term in self.terms:
            forms = list(term.pref.values())
            for lang_aliases in term.aliases.values():
                forms.extend(lang_aliases)
            for form in forms:
                key = normalize(form)
                if key in table and table[key] != term.id:
                    raise VocabParseError(
                        f"Alias collision {key!r}: {table[key]} vs {term.id}")
                table[key] = term.id
        return table


def load_vocabulary(kind: str, vocab_dir: Path = VOCAB_DIR) -> Vocabulary:
    if kind not in VOCAB_FILES:
        raise KeyError(f"Unknown vocabulary kind {kind!r}; expected one of {sorted(VOCAB_FILES)}")
    data = load_vocab_file(vocab_dir / VOCAB_FILES[kind])
    terms = []
    for raw in data["terms"]:
        aliases = {lang: tuple(vals) for lang, vals in (raw.get("aliases") or {}).items()}
        terms.append(Term(
            id=raw["id"],
            pref=raw.get("pref") or {},
            definition=raw.get("def", ""),
            broader=raw.get("broader"),
            maps=raw.get("maps") or {},
            aliases=aliases,
        ))
    return Vocabulary(id=data["header"]["id"], version=data["header"]["version"], terms=tuple(terms))


def load_all(vocab_dir: Path = VOCAB_DIR) -> dict[str, Vocabulary]:
    return {kind: load_vocabulary(kind, vocab_dir) for kind in VOCAB_FILES}


# ---------------------------------------------------------------------------
# Deterministic mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Mapping:
    """One raw label -> vocabulary assignment, rule-recorded and replayable."""
    vocabulary_id: str
    vocabulary_version: str
    source_label: str
    destination: str | None
    relation: Relation
    rule: str          # which deterministic rule fired
    rationale: str

    def as_mapping_rule(self, *, body_id: str, reviewer: str = "mapper-v1") -> dict:
        """Render compatible with review_contracts.MappingRule."""
        return {
            "key": f"{self.vocabulary_id}@{self.vocabulary_version}:{normalize(self.source_label)}",
            "body_id": body_id,
            "source_label": self.source_label,
            "destination": self.destination,
            "relation": self.relation,
            "rationale": self.rationale,
            "reference": f"{self.vocabulary_id} {self.vocabulary_version} rule {self.rule}",
            "reviewer": reviewer,
        }


def map_label(vocab: Vocabulary, raw_label: str | None) -> Mapping:
    """Map one raw label to a term. Never guesses: unknown -> unmapped."""
    if raw_label is None or not raw_label.strip():
        return Mapping(vocab.id, vocab.version, raw_label or "", None, "unmapped",
                       "empty", "No source label to map.")
    key = normalize(raw_label)
    table = vocab.alias_table()
    hit = table.get(key)
    if hit is not None:
        return Mapping(vocab.id, vocab.version, raw_label, hit, "exact_in_scope",
                       "alias-exact", f"Normalised label matches alias/prefLabel of {hit}.")
    # substring-free conservative fallback: none. Deliberately no fuzzy match —
    # unmapped is a first-class, reviewable outcome.
    return Mapping(vocab.id, vocab.version, raw_label, None, "unmapped",
                   "no-alias", "No exact normalised alias match; left unmapped for review.")


def map_fields(vocabs: dict[str, Vocabulary], fields: dict[str, str | None],
               *, field_kind: dict[str, str] | None = None) -> dict[str, Mapping]:
    """Map a record's raw fields. ``field_kind`` overrides the default
    field-name -> vocabulary-kind routing."""
    routing = {
        "affair_type_raw": "affair_type",
        "decision_raw": "decision_outcome",
        **(field_kind or {}),
    }
    out: dict[str, Mapping] = {}
    for field_name, kind in routing.items():
        if field_name in fields:
            out[field_name] = map_label(vocabs[kind], fields[field_name])
    return out


def main() -> None:  # small CLI: python -m skony.vocab
    vocabs = load_all()
    summary = {k: {"id": v.id, "version": v.version, "terms": len(v.terms),
                   "aliases": len(v.alias_table())} for k, v in vocabs.items()}
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
