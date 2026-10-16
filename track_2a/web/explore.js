"use strict";

const $ = id => document.getElementById(id);
const el = (tag, className, text) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
};
const fieldLabels = {title: "Title", affair_type_raw: "Affair type", submitter_raw: "Submitted by",
  submitted_date_raw: "Submission date", question_text: "Request / question", answer_text: "Government answer",
  decision_raw: "Decision", decision_date_raw: "Decision date"};
const languageLabels = {de: "German", fr: "French", it: "Italian", en: "English", unknown: "Unknown"};
const filterIds = {q: "query", body: "body", language: "language", topic: "topic", evidence: "evidence", sources: "sources"};
let offset = 0, results = null, searchVersion = 0, dossierVersion = 0, evidenceVersion = 0;
let dossier = null, dossierTab = "overview", searching = true;

async function api(path) {
  const response = await fetch(path);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Could not load the collection.");
  return body;
}

function message(text, error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}

function parameters() {
  const params = new URLSearchParams();
  for (const [key, id] of Object.entries(filterIds)) if ($(id).value) params.set(key, $(id).value);
  params.set("reviewed_only", String($("reviewed-only").checked));
  return params;
}

function updateURL(dossierId = null) {
  const params = parameters();
  if (offset) params.set("offset", offset);
  if (dossierId) params.set("dossier", dossierId);
  history.replaceState(null, "", "/explore?" + params);
}

function fillSelect(id, choices, defaultLabel) {
  const previous = $(id).value;
  $(id).replaceChildren(new Option(defaultLabel, ""), ...choices.map(c => new Option(c.label, c.key)));
  // Keep a requested unknown filter visible so its empty result is understandable.
  if (previous && !choices.some(c => c.key === previous)) $(id).append(new Option(previous, previous));
  $(id).value = previous;
}

function exportsEnabled(enabled) {
  for (const id of ["export-json", "export-csv"]) {
    $(id).setAttribute("aria-disabled", String(!enabled));
    $(id).tabIndex = enabled ? 0 : -1;
    $(id).classList.toggle("disabled", !enabled);
  }
}

async function search(reset = true) {
  if (reset) offset = 0;
  const version = ++searchVersion, params = parameters();
  dossierVersion++;
  if ($("dossier-dialog").open) $("dossier-dialog").close();
  updateURL();
  params.set("offset", offset);
  searching = true;
  exportsEnabled(false);
  $("previous").disabled = true;
  $("next").disabled = true;
  $("results").setAttribute("aria-busy", "true");
  message("Searching the local collection…");
  try {
    const data = await api("/api/explorer?" + params);
    if (version !== searchVersion) return;
    if (offset >= data.total && offset > 0) { offset = 0; return search(false); }
    results = data;
    fillSelect("body", data.facets.bodies, "All parliaments");
    fillSelect("language", data.facets.languages.map(key => ({key, label: languageLabels[key] || key})), "All languages");
    fillSelect("topic", data.facets.topics, "All topics");
    renderResults(data);
    const practice = data.insights.practice_dossiers;
    message(`${data.total} dossier${data.total === 1 ? "" : "s"} in this local sample${practice ? ` · ${practice} practice dossier${practice === 1 ? "" : "s"} included` : ""}.`);
    const exportParams = parameters();
    for (const format of ["json", "csv"]) {
      exportParams.set("format", format);
      $("export-" + format).href = "/api/explorer/export?" + exportParams;
    }
    exportsEnabled(data.total > 0);
  } catch (error) {
    if (version === searchVersion) {
      results = null;
      $("results").replaceChildren();
      $("empty").hidden = true;
      for (const id of ["stat-dossiers", "stat-documents", "stat-answers", "stat-decisions"]) $(id).textContent = "—";
      $("results-caption").textContent = "Collection unavailable";
      $("page-caption").textContent = "";
      $("coverage-note").textContent = "";
      message(error.message, true);
    }
  } finally {
    if (version === searchVersion) { searching = false; $("results").setAttribute("aria-busy", "false"); }
  }
}

function renderResults(data) {
  const stats = data.insights;
  $("stat-dossiers").textContent = stats.dossiers;
  $("stat-documents").textContent = stats.documents;
  $("stat-answers").textContent = stats.with_answer_text;
  $("stat-decisions").textContent = stats.with_decision_text;
  $("coverage-note").textContent = data.scope_note + (stats.pages_needing_ocr ? ` ${stats.pages_needing_ocr} page(s) have no extracted text and need OCR or visual reading.` : "");
  $("results-caption").textContent = `${stats.documents} document${stats.documents === 1 ? "" : "s"} · ${stats.bodies} identified parliament${stats.bodies === 1 ? "" : "s"} · ${$("reviewed-only").checked ? "Document-reviewed values only" : "Unreviewed suggestions included"}`;
  $("results").replaceChildren();
  $("empty").hidden = data.total !== 0;
  const topics = Object.fromEntries(data.facets.topics.map(t => [t.key, t.label]));
  for (const item of data.results) {
    const card = el("article", "result-card"), meta = el("div", "card-meta");
    meta.append(el("span", "", item.body), el("span", "", item.languages.map(l => l.toUpperCase()).join(" / ")));
    if (item.synthetic) meta.append(el("span", "practice", "Practice · fictional"));
    const title = el("button", "result-title", item.title);
    title.type = "button";
    title.addEventListener("click", () => openDossier(item.id));
    card.append(meta, title);
    if (item.snippet) {
      const snippet = el("p", "snippet", item.snippet.quote);
      const cite = el("button", "citation-button snippet-label", `Source text · page ${item.snippet.page} ↗`);
      cite.addEventListener("click", () => showEvidence(item.snippet));
      card.append(snippet, cite);
    } else card.append(el("p", "snippet", "No searchable text in this document. Read the original PDF or add an OCR text layer."));
    const pills = el("div", "evidence-pills");
    for (const [key, label] of [["request", "Request"], ["answer", "Answer"], ["decision", "Decision"]])
      pills.append(el("span", "pill" + (item["has_" + key] ? "" : " unknown"), `${label} ${item["has_" + key] ? "text located" : "not located"}`));
    for (const topic of item.topics) pills.append(el("span", "pill topic", topics[topic] + " · keyword"));
    const bottom = el("div", "card-bottom"), open = el("button", "open-dossier", "Open dossier →");
    open.addEventListener("click", () => openDossier(item.id));
    bottom.append(el("span", "", `${item.document_count} PDF${item.document_count === 1 ? "" : "s"} · ${item.reviewed_fields}/${item.document_count * 8} fields reviewed`), open);
    card.append(pills, bottom);
    $("results").append(card);
  }
  $("previous").disabled = data.offset === 0;
  $("next").disabled = data.offset + data.limit >= data.total;
  $("page-caption").textContent = data.total ? `${data.offset + 1}–${Math.min(data.offset + data.limit, data.total)} of ${data.total}` : "0 results";
}

async function openDossier(id) {
  const version = ++dossierVersion;
  dossier = null;
  $("dossier-content").replaceChildren(el("h2", "", "Loading dossier…"));
  if (!$("dossier-dialog").open) $("dossier-dialog").showModal();
  try {
    const data = await api(`/api/explorer/dossiers/${encodeURIComponent(id)}?reviewed_only=${$("reviewed-only").checked}`);
    if (version !== dossierVersion) return;
    dossier = data;
    dossierTab = "overview";
    updateURL(id);
    renderDossier();
  } catch (error) {
    if (version === dossierVersion) $("dossier-content").replaceChildren(el("h2", "", "Dossier unavailable"), el("p", "notice", error.message));
  }
}

function renderDossier() {
  const root = $("dossier-content"), meta = el("p", "dossier-meta",
    `${dossier.body} · ${dossier.languages.map(l => languageLabels[l] || l).join(" / ")} · ${dossier.document_count} PDF(s)${dossier.affair_id !== null ? ` · Source affair ID ${dossier.affair_id}` : ""}`);
  const title = el("h2", "", dossier.title); title.id = "dossier-title";
  root.replaceChildren(title, meta);
  if (dossier.synthetic) root.append(el("p", "notice", "Practice document from a fictional parliament. These are authored examples, not model inference or real parliamentary findings."));
  root.append(el("p", "notice", "Document-level research: unreviewed suggestions are labelled below. " +
    (dossier.association_status === "unverified_source_metadata" ? "These documents share source metadata; their affair membership has not been verified here. " : "This dossier contains one source document. ") +
    "A missing field does not establish an unanswered request or an undecided affair."));
  const tabs = el("div", "dossier-tabs");
  for (const [key, label] of [["overview", "Requests & answers"], ["timeline", "Timeline"], ["actors", "People involved"], ["documents", "Source documents"]]) {
    const button = el("button", "", label);
    button.id = "dossier-tab-" + key;
    button.setAttribute("aria-pressed", String(dossierTab === key));
    button.addEventListener("click", () => { dossierTab = key; renderDossier(); $("dossier-tab-" + key).focus(); });
    tabs.append(button);
  }
  root.append(tabs);
  const content = el("div");
  if (dossierTab === "overview") {
    for (const doc of dossier.documents) {
      const section = el("section", "dossier-section");
      section.append(el("h3", "document-heading", doc.filename), documentLinks(doc));
      for (const field of ["affair_type_raw", "submitted_date_raw", "question_text", "answer_text", "decision_raw", "decision_date_raw"])
        section.append(fieldBlock(fieldLabels[field], doc.fields[field], doc));
      content.append(section);
    }
    content.append(el("p", "evidence-note", "Each document keeps its own request, answer and decision fields. No question/answer pairing across PDFs is inferred."));
  } else if (dossierTab === "timeline") {
    content.append(el("p", "evidence-note", "Events come from located document fields. Only ISO dates and day.month.year dates are sorted. Each date retains its own evidence and review status."));
    if (!dossier.timeline.length) content.append(el("p", "notice", "No event text or date has been located in the selected field mode. Inspect the source documents or extract them first."));
    let undated = false;
    for (const event of dossier.timeline) {
      if (!event.date_iso && !undated) { content.append(el("h3", "timeline-section-label", "Date unknown or not sortable")); undated = true; }
      const doc = dossier.documents.find(d => d.id === event.document_id), item = el("article", "timeline-item");
      item.append(el("p", "timeline-date", event.date_raw || "Date not located"), el("h3", "", event.kind));
      if (event.date_evidence?.value) item.append(fieldBlock("Date evidence", event.date_evidence, doc));
      item.append(fieldBlock(fieldLabels[event.field], event.content, doc));
      content.append(item);
    }
  } else if (dossierTab === "actors") {
    content.append(el("p", "evidence-note", "Names and signatories remain in their original source block. Roles beyond submitter, identities and party affiliations are not inferred."));
    if (!dossier.actors.length) content.append(el("p", "notice", "No submitter or signatory block is located in the selected field mode. Check the original PDFs."));
    for (const actor of dossier.actors) {
      const section = el("section", "dossier-section"), doc = dossier.documents.find(d => d.id === actor.document_id);
      section.append(fieldBlock(actor.role, actor, doc));
      const button = el("button", "button secondary actor-button", "Search this wording in the collection ↗");
      button.addEventListener("click", () => { $("query").value = actor.value.slice(0, 250); search(); });
      section.append(button); content.append(section);
    }
  } else {
    for (const doc of dossier.documents) {
      const section = el("section", "dossier-section");
      section.append(el("h3", "document-heading", doc.filename), documentLinks(doc));
      section.append(el("p", "document-facts", `${doc.pages.length} page(s) · ${doc.language.toUpperCase()} · Revision ${doc.revision}\nSource role hint: ${doc.role_hint || "unknown"} (unverified)\nRights: ${doc.rights_status}\nPDF SHA-256: ${doc.sha256}`));
      if (doc.textless_pages.length) section.append(el("p", "notice", `Pages with no text layer: ${doc.textless_pages.join(", ")}. Visual review or OCR is needed.`));
      for (const page of doc.pages) {
        const button = el("button", "button secondary", `Read page ${page.number}`);
        button.addEventListener("click", () => showEvidence({document_id: doc.id, page: page.number}, doc));
        section.append(button, document.createTextNode(" "));
      }
      content.append(section);
    }
  }
  root.append(content);
}

function documentLinks(doc) {
  const links = el("div", "document-links"), pdf = el("a", "", "Original PDF ↗"), review = el("a", "", "Extract / review document ↗");
  pdf.href = `/api/documents/${encodeURIComponent(doc.id)}/pdf`; pdf.target = "_blank"; pdf.rel = "noopener";
  review.href = "/?document=" + encodeURIComponent(doc.id);
  links.append(pdf, review);
  if (doc.source_url) { const source = el("a", "", "Publisher source ↗"); source.href = doc.source_url; source.target = "_blank"; source.rel = "noopener noreferrer"; links.append(source); }
  return links;
}

function fieldBlock(label, field, doc) {
  const block = el("div", "field-block"), heading = el("div");
  const reviewed = field.status === "document_reviewed";
  heading.append(el("span", "field-name", label), el("span", "field-status" + (reviewed ? " reviewed" : ""),
    reviewed ? "Document reviewed" : field.value ? "Unreviewed suggestion" : field.status === "withheld_unreviewed" ? "Awaiting review" : "Not located"));
  block.append(heading);
  block.append(el("p", field.value ? "field-copy" : "field-absent", field.value ||
    (field.review_decision === "absent" ? "Reviewer marked absent in this document." :
      field.status === "withheld_unreviewed" ? "Unreviewed proposal hidden in this mode." : "No value located in the selected field mode.")));
  if (field.reviewer) block.append(el("p", "evidence-note", `Document reviewer: ${field.reviewer}`));
  if (field.citation) {
    const links = el("div", "field-links"), cite = el("button", "citation-button", `Read evidence · page ${field.citation.page} ↗`);
    cite.addEventListener("click", () => showEvidence(field.citation, doc));
    const review = el("a", "", "Review this field ↗"); review.href = field.citation.review_url;
    links.append(cite, review); block.append(links);
  }
  return block;
}

async function showEvidence(citation, doc = null) {
  const version = ++evidenceVersion;
  $("evidence-caption").textContent = "Loading original page text…";
  $("source-text").replaceChildren();
  $("source-pdf").hidden = true;
  if (!$("evidence-dialog").open) $("evidence-dialog").showModal();
  try {
    const pages = doc?.pages || (await api(`/api/documents/${encodeURIComponent(citation.document_id)}`)).document.pages;
    if (version !== evidenceVersion) return;
    const page = pages.find(p => p.number === citation.page);
    if (!page) throw new Error("Source page is unavailable.");
    $("evidence-caption").textContent = `Page ${citation.page} · ${citation.basis === "image" ? "Human image transcription; check the PDF. No text offsets claimed." : "Original extracted text. A matching passage still needs a meaning check."}`;
    const chars = Array.from(page.text);
    if (citation.basis !== "image" && Number.isInteger(citation.start) && Number.isInteger(citation.end) && citation.start >= 0 && citation.end <= chars.length && citation.end > citation.start) {
      $("source-text").append(document.createTextNode(chars.slice(0, citation.start).join("")), el("mark", "", chars.slice(citation.start, citation.end).join("")), document.createTextNode(chars.slice(citation.end).join("")));
      requestAnimationFrame(() => $("source-text").querySelector("mark")?.scrollIntoView({block: "center"}));
    } else $("source-text").textContent = (citation.basis === "image" ? `Human transcription:\n${citation.quote}\n\nExtracted page text:\n` : "") + (page.text || "This page has no extracted text. Open the original PDF.");
    $("source-pdf").href = `/api/documents/${encodeURIComponent(citation.document_id)}/pdf#page=${citation.page}`;
    $("source-pdf").hidden = false;
  } catch (error) { if (version === evidenceVersion) $("evidence-caption").textContent = error.message; }
}

function restoreURL() {
  const params = new URLSearchParams(location.search);
  for (const [key, id] of Object.entries(filterIds)) {
    const value = params.get(key) || (key === "sources" ? "all" : "");
    if (key !== "q" && value && !Array.from($(id).options).some(o => o.value === value)) $(id).append(new Option(value, value));
    $(id).value = value;
  }
  $("reviewed-only").checked = params.get("reviewed_only") === "true";
  const requestedOffset = Number(params.get("offset"));
  offset = Number.isSafeInteger(requestedOffset) && requestedOffset >= 0 ? requestedOffset : 0;
  return params.get("dossier");
}

$("search-form").addEventListener("submit", event => { event.preventDefault(); search(); });
for (const id of ["body", "language", "topic", "evidence", "sources", "reviewed-only"]) $(id).addEventListener("change", () => search());
$("reset").addEventListener("click", () => { for (const [key, id] of Object.entries(filterIds)) $(id).value = key === "sources" ? "all" : ""; $("reviewed-only").checked = false; search(); });
document.querySelectorAll("[data-evidence]").forEach(button => button.addEventListener("click", () => { $("evidence").value = button.dataset.evidence; search(); }));
$("previous").addEventListener("click", () => { if (results && !searching) { offset = Math.max(0, offset - results.limit); search(false); } });
$("next").addEventListener("click", () => { if (results && !searching) { offset += results.limit; search(false); } });
$("close-dossier").addEventListener("click", () => $("dossier-dialog").close());
$("dossier-dialog").addEventListener("close", () => { dossierVersion++; updateURL(); });
$("close-evidence").addEventListener("click", () => $("evidence-dialog").close());
$("evidence-dialog").addEventListener("close", () => evidenceVersion++);
for (const id of ["export-json", "export-csv"]) $(id).addEventListener("click", event => { if ($(id).getAttribute("aria-disabled") === "true") event.preventDefault(); });
window.addEventListener("popstate", async () => { const id = restoreURL(); await search(false); if (id) openDossier(id); });
(async () => { exportsEnabled(false); const id = restoreURL(); await search(false); if (id) openDossier(id); })();
