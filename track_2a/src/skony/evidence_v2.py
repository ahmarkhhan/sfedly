"""Resolve closed-set proposals against immutable text, then project explicitly."""

from .contracts import (CandidateV2, EvidenceSegment, FIELDS, PROJECTION_VERSION,
                        ResolvedItem, ResolvedSlot, ResolvedTarget, ResolvedV2,
                        RunEnvelope, TextSnapshot)
from .schema import CandidateExtraction, CandidateField
from .verify import find_span


def _references(structure):
    if hasattr(structure, "name"):
        return [structure.name] + ([structure.role] if structure.role else [])
    if hasattr(structure, "content"):
        return structure.content + ([structure.label] if structure.label else [])
    if hasattr(structure, "act"):
        return structure.act + ([structure.date] if structure.date else [])
    return structure.evidence + ([structure.printed_label] if structure.printed_label else [])


def validate_contract(candidate: CandidateV2, run: RunEnvelope, text: TextSnapshot):
    if run.artifact_id != text.artifact_id or run.text_snapshot_id != text.id:
        raise ValueError("Run/text identity mismatch")
    scopes = {s.scope_id: s for s in run.scopes}
    target_ids = [t.scope_id for t in candidate.targets]
    if len(target_ids) != len(set(target_ids)) or set(target_ids) != set(scopes):
        raise ValueError("Exactly one target per allowed scope is required")
    for scope in scopes.values():
        seen = set()
        for window in scope.windows:
            key = (window.page, window.layer_id, window.start, window.end)
            if key in seen or window.end > len(text.page_text(window.page, window.layer_id)):
                raise ValueError("Invalid or duplicate scope window")
            seen.add(key)
    ids = {e.id for e in run.allowed_endpoints}
    endpoints = {e.id: (e.kind, e.scope_id, e.event_kind) for e in run.allowed_endpoints}
    items = {}
    for target in candidate.targets:
        for name in FIELDS:
            for item in getattr(target.fields, name).items:
                if item.proposal_id in ids:
                    raise ValueError("Duplicate proposal ID")
                ids.add(item.proposal_id)
                items[item.proposal_id] = (target.scope_id, item)
                windows = scopes[target.scope_id].windows
                for segment in item.segments:
                    if not any(w.page == segment.page and w.layer_id == segment.layer_id for w in windows):
                        raise ValueError("Segment page/layer outside allowed scope")
        for key, kind in [("actors", None), ("question_items", "question"),
                          ("response_items", "response"), ("events", "event"), ("relations", None)]:
            for obj in getattr(target, key) or []:
                if obj.proposal_id in ids:
                    raise ValueError("Duplicate proposal ID")
                ids.add(obj.proposal_id)
                if kind:
                    endpoints[obj.proposal_id] = (kind, target.scope_id, getattr(obj, "kind", None))
    for target in candidate.targets:
        actor_ids = {a.proposal_id for a in target.actors or []}
        for key in ("actors", "question_items", "response_items", "events", "relations"):
            for obj in getattr(target, key) or []:
                for ref in _references(obj):
                    if ref.item_id not in items:
                        raise ValueError("Dangling evidence reference")
                    owner, item = items[ref.item_id]
                    if owner != target.scope_id or ref.segment_index >= len(item.segments):
                        raise ValueError("Cross-scope or dangling segment reference")
                if key == "events" and (len(obj.actor_ids) != len(set(obj.actor_ids))
                                         or not set(obj.actor_ids).issubset(actor_ids)):
                    raise ValueError("Unknown or cross-scope actor reference")
                if key == "relations":
                    for endpoint in (obj.source, obj.target):
                        if endpoint.id not in endpoints or endpoints[endpoint.id][0] != endpoint.kind:
                            raise ValueError("Dangling or incorrectly typed endpoint")
                        if endpoints[endpoint.id][1] != target.scope_id:
                            raise ValueError("Cross-scope relation endpoint requires explicit trusted registration")
                    if obj.kind == "response_decision" and endpoints[obj.target.id][2] != "decision":
                        raise ValueError("A recommendation cannot be linked as a decision")


def _locate(segment, text, scope):
    page_text = text.page_text(segment.page, segment.layer_id)
    base = 0
    haystack = page_text
    if segment.context_anchor is not None:
        # Context anchors are exact and unique, never fuzzy repairs.
        base = page_text.find(segment.context_anchor)
        if base < 0 or page_text.find(segment.context_anchor, base + 1) >= 0:
            return None, "ambiguous_or_missing_context"
        haystack = segment.context_anchor
    span, reason = find_span(haystack, segment.quote)
    if span is None:
        return None, reason
    start, end, method = span
    start, end = start + base, end + base
    if not any(w.page == segment.page and w.layer_id == segment.layer_id and
               w.start <= start < end <= w.end for w in scope.windows):
        return None, "outside_subject_scope"
    return EvidenceSegment(artifact_id=text.artifact_id, text_snapshot_id=text.id,
                           page=segment.page, layer_id=segment.layer_id, start=start, end=end,
                           quote=page_text[start:end], match_method=method), None


def verify_v2(candidate: CandidateV2 | str, run: RunEnvelope, text: TextSnapshot) -> ResolvedV2:
    if isinstance(candidate, str):
        candidate = CandidateV2.model_validate_json(candidate)
    validate_contract(candidate, run, text)
    scopes = {s.scope_id: s for s in run.scopes}
    targets = []
    for target in candidate.targets:
        fields, resolved_items = {}, {}
        for name in FIELDS:
            slot = getattr(target.fields, name)
            items = []
            for proposal in slot.items:
                evidence, failure, previous = [], None, None
                for segment in proposal.segments:
                    located, reason = _locate(segment, text, scopes[target.scope_id])
                    if located is None:
                        failure = reason
                        break
                    position = (located.page, located.start)
                    if previous is not None and (position < previous[:2] or
                            (located.page == previous[0] and located.start < previous[2])):
                        raise ValueError("Evidence segments must follow source order without overlap")
                    previous = (located.page, located.start, located.end)
                    evidence.append(located)
                item = ResolvedItem(proposal_id=proposal.proposal_id,
                                    value=None if failure else "\n\n".join(e.quote for e in evidence),
                                    evidence=[] if failure else evidence,
                                    evidence_outcome=("ambiguous_location" if "ambiguous" in (failure or "")
                                                      else "not_located" if failure else "located"),
                                    reason=failure)
                items.append(item)
                resolved_items[item.proposal_id] = item
            fields[name] = ResolvedSlot(outcome=slot.outcome, items=items,
                                        abstention_reason=slot.abstention_reason)
        structures, statuses = {}, {}
        for key in ("actors", "question_items", "response_items", "events", "relations"):
            proposals = getattr(target, key)
            statuses[key] = "not_extracted" if proposals is None else "proposed"
            structures[key] = []
            for proposal in proposals or []:
                citations, reason = [], None
                for ref in _references(proposal):
                    parent = resolved_items[ref.item_id]
                    if parent.value is None:
                        reason = "parent_evidence_not_located"
                        break
                    segment = parent.evidence[ref.segment_index]
                    span, reason = find_span(segment.quote, ref.quote)
                    if span is None:
                        break
                    start, end, method = span
                    citations.append(segment.model_copy(update={
                        "start": segment.start + start, "end": segment.start + end,
                        "quote": segment.quote[start:end], "match_method": method}).model_dump())
                structures[key].append({"proposal": proposal.model_dump(),
                                        "evidence": [] if reason else citations,
                                        "evidence_outcome": "not_located" if reason else "located",
                                        "reason": reason, "semantic_review_required": True})
        targets.append(ResolvedTarget(scope_id=target.scope_id, fields=fields,
                                      structures=structures, structure_status=statuses))
    return ResolvedV2(run=run, targets=targets)


def select_target(result: ResolvedV2, scope_id: str | None):
    if scope_id is None:
        if len(result.targets) != 1:
            raise ValueError("Select an explicit target for a multi-affair artifact")
        return result.targets[0]
    for target in result.targets:
        if target.scope_id == scope_id:
            return target
    raise ValueError("Unknown projection scope")


def benchmark_projection(result: ResolvedV2, scope_id: str | None = None, *, selections=None):
    """One document-plus-target-scope unit; unresolved alternatives stay visible."""
    target = select_target(result, scope_id)
    selections = selections or {}
    if set(selections) - set(FIELDS):
        raise ValueError("Unknown projection field")
    fields = {}
    for name, slot in target.fields.items():
        chosen = selections.get(name)
        items = [i for i in slot.items if i.proposal_id == chosen] if chosen else slot.items
        if chosen and len(items) != 1:
            raise ValueError("Unknown designated assertion")
        item = items[0] if len(items) == 1 else None
        fields[name] = {"value": item.value if item else None,
                        "disposition": "unresolved_alternatives" if len(items) > 1 else
                            "abstained" if not items else item.evidence_outcome,
                        "evidence": [e.model_dump() for e in item.evidence] if item else [],
                        "alternatives": [i.proposal_id for i in slot.items], "selected": chosen}
    return {"projection_version": PROJECTION_VERSION, "artifact_id": result.run.artifact_id,
            "scope_id": target.scope_id, "unit_id": result.run.artifact_id + ":" + target.scope_id,
            "fields": fields}


def legacy_projection(result: ResolvedV2, scope_id: str | None = None) -> CandidateExtraction:
    target = select_target(result, scope_id)
    if any(target.structures.values()):
        raise ValueError("Lossy v0.1 export: typed structures are not representable")
    fields = {}
    for name, slot in target.fields.items():
        if slot.outcome == "abstained":
            fields[name] = CandidateField(value=None, page=None, quote=None)
        else:
            if len(slot.items) != 1 or len(slot.items[0].evidence) != 1 or slot.items[0].value is None:
                raise ValueError("Lossy v0.1 export: alternatives/multi-segment/unlocated value")
            item = slot.items[0]
            segment = item.evidence[0]
            if segment.basis != "text":
                raise ValueError("Lossy v0.1 export: image transcription")
            fields[name] = CandidateField(value=item.value, page=segment.page, quote=segment.quote)
    return CandidateExtraction(**fields)
