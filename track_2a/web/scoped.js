"use strict";
const $=id=>document.getElementById(id);
const labels={title:"Title",affair_type_raw:"Affair type",submitter_raw:"Submitters",submitted_date_raw:"Submission date",question_text:"Request / question",answer_text:"Executive response",decision_raw:"Parliamentary decision",decision_date_raw:"Decision date"};
const element=(tag,text,className)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;};
let state,scopes=[],affairs=[],reviews=[],selectedScope,currentText,comparisonResult,comparisonVersion=0;
const enc=encodeURIComponent;
function message(text,error=false){$("message").textContent=text;$("message").classList.toggle("error",error);}
function reviewer(){const name=$("reviewer").value.trim();if(!name)throw new Error("Enter your reviewer name before recording a decision.");return name;}
async function api(path,data){const response=await fetch(path,{method:data===undefined?"GET":"POST",headers:data===undefined?{}:{"Content-Type":"application/json","X-Skony-Token":state.csrf_token},...(data===undefined?{}:{body:JSON.stringify(data)})});const value=await response.json();if(!response.ok)throw new Error(value.error||"The operation could not finish.");return value;}
async function act(work){try{await work();}catch(error){message(error.message,true);}}
function option(value,label){const n=element("option",label);n.value=value;return n;}
function scopeName(scope){const doc=state.documents.find(d=>d.id===scope.binding.scope_id.replace(/^legacy:/,""));return `${doc?.filename||scope.binding.subject_id} · ${scope.binding.role.replaceAll("_"," ")} · ${scope.binding.membership}`;}
function checkedPages(scope){return [...new Set(scope.binding.windows.map(w=>w.page))].sort((a,b)=>a-b);}
async function refresh(){
  clearComparison();
  const previous=$("scope").value;state=await api("/api/state");
  [scopes,affairs,reviews]=await Promise.all([api("/api/v2/scopes"),api("/api/v2/affairs"),api("/api/v2/reviews")]);
  $("scope").replaceChildren(...scopes.map(s=>option(s.id,scopeName(s))));if(scopes.some(s=>s.id===previous))$("scope").value=previous;
  $("existing-affair").replaceChildren(option("","Register an affair"),...affairs.map(a=>option(a.id,`${a.value.body_key} · ${a.value.official_affair_id||a.id}`)));
  if(scopes.length)await selectScope();else message("Add a PDF in Review documents, then register its source scope.");
  renderDecisions();await loadSnapshots();
}
async function selectScope(){
  selectedScope=scopes.find(s=>s.id===$("scope").value);if(!selectedScope)return;
  const b=selectedScope.binding;currentText=await api(`/api/v2/objects/${enc(b.text_snapshot_id)}`);
  $("scope-summary").textContent=`${b.subject_id} · pages ${checkedPages(selectedScope).join(", ")} · ${b.role.replaceAll("_"," ")} · ${b.membership==="reviewed"?"Membership reviewed":"Membership unresolved; acceptance is blocked"}`;
  $("association").open=b.membership!=="reviewed";$("role").value=b.role;$("existing-affair").value=affairs.some(a=>a.id===b.subject_id)?b.subject_id:"";toggleAffair();
  $("source-page").replaceChildren(...currentText.pages.map((p,i)=>option(String(i),`Page ${p.page} · ${p.layer_id}`)));showCurrentText();
  const artifact=await findArtifact(b.artifact_id);$("original").href=artifact?`/api/v2/artifacts/${enc(artifact.sha256)}/pdf`:"#";
  $("segments").replaceChildren();addSegment();await loadClaims();
}
async function findArtifact(artifactId,snapshot){
  if(snapshot){for(const obj of Object.values(snapshot.objects)){if(obj.kind==="artifact"&&obj.value.sha256===artifactId)return obj.value;}}
  // Source artifacts are addressed by digest; the server resolves local paths.
  return api(`/api/v2/artifacts/${enc(artifactId)}`);
}
function showCurrentText(){const p=currentText?.pages[Number($("source-page").value)];$("source-text").hidden=false;$("source-image").hidden=true;$("transcription").hidden=true;$("source-text").textContent=p?.text||"No text in this layer. Inspect the original page.";$("source-caption").textContent="Original immutable text. A text match still requires a meaning check.";}
function toggleAffair(){$("new-affair").hidden=!!$("existing-affair").value;}
function addSegment(){
  if(!currentText)return;const row=element("div",undefined,"segment"),label=element("label","Source page / layer"),select=element("select");select.className="segment-page";
  select.append(...currentText.pages.map((p,i)=>option(String(i),`Page ${p.page} · ${p.layer_id}`)));label.append(select);
  const quoteLabel=element("label","Exact passage or visual transcription"),quote=element("textarea");quote.className="segment-quote";quoteLabel.append(quote);
  const remove=element("button","Remove passage");remove.type="button";remove.addEventListener("click",()=>row.remove());row.append(label,quoteLabel,remove);$("segments").append(row);
}
function checkLabel(text){const label=element("label",undefined,"check"),input=element("input");input.type="checkbox";label.append(input,document.createTextNode(text));return {label,input};}
async function loadClaims(){
  const claims=await api(`/api/v2/scopes/${enc(selectedScope.id)}/claims`);$("claims").replaceChildren();
  if(!claims.length)$("claims").append(element("p","No scoped proposals yet. Add a correction below or import a recorded v0.2 extraction.","muted"));
  for(const claim of claims){
    const card=element("article",undefined,"claim");card.append(element("h4",labels[claim.predicate]||claim.predicate),element("span",claim.source_assessment.replaceAll("_"," "),"tag"),element("p",claim.value??"No value claimed for this source disposition.","value"));
    for(const [i,cite] of claim.citations.entries()){const button=element("button",`Evidence ${i+1} · page ${cite.page}`);button.type="button";button.addEventListener("click",()=>act(()=>showCitation(cite)));card.append(button);}
    const saved=reviews.find(r=>r.decision.request.claim_id===claim.id&&r.decision.request.coverage==="document");
    if(saved)card.append(element("p",saved.eligible?`Accepted · completeness: ${saved.decision.completeness.semantic_completeness.replaceAll("_"," ")}`:`Requires review: ${saved.reasons.join(", ").replaceAll("_"," ")}`,"muted"));
    const noteLabel=element("label","Review note"),note=element("textarea");noteLabel.append(note);card.append(noteLabel);
    const checked=checkLabel(`I checked this field's meaning across scope pages ${checkedPages(selectedScope).join(", ")}.`);
    const complete=checkLabel("I checked section boundaries and all required clauses; the section is complete in this scope.");
    const conflicts=checkLabel("My note resolves the competing assertions and explains this choice.");
    card.append(checked.label);if(["answer_text","question_text"].includes(claim.predicate))card.append(complete.label);card.append(conflicts.label);
    const save=element("button","Accept scoped decision","primary");save.type="button";
    save.addEventListener("click",()=>act(async()=>{if(!checked.input.checked)throw new Error("Check the declared source scope before accepting.");
      await api("/api/v2/reviews",{claim_id:claim.id,revision:claim.review_revision,action:"accepted",reviewer:reviewer(),note:note.value,
        checked_scope:{[selectedScope.id]:checkedPages(selectedScope)},resolve_conflicts:conflicts.input.checked,
        boundary_checked:complete.input.checked,required_clauses_checked:complete.input.checked,section_complete:complete.input.checked?true:null});
      await refresh();message("Scoped decision saved. Its dependencies will be checked again before export.");}));
    card.append(save);$("claims").append(card);
  }
}
function renderDecisions(){
  $("decisions").replaceChildren();
  for(const review of reviews){const decision=review.decision,deps=decision.dependencies,label=element("label",undefined,"decision"),input=element("input");input.type="checkbox";input.value=review.decision_id;input.disabled=!review.eligible;input.dataset.scope=decision.request.checked_scope?Object.keys(decision.request.checked_scope)[0]:"";
    label.append(input,document.createTextNode(`${deps.subject_id} · ${labels[deps.predicate]||deps.predicate} · ${review.eligible?"eligible":review.reasons.join(", ").replaceAll("_"," ")}`));$("decisions").append(label);}
  if(!reviews.length)$("decisions").append(element("p","No scoped review decisions yet.","muted"));
}
async function loadSnapshots(selectId){const previous=selectId||$("snapshot").value,snapshots=await api("/api/v2/snapshots");$("snapshot").replaceChildren(...snapshots.map(s=>option(s.id,`${s.id.slice(0,12)} · ${s.scope_ids.length} scopes · ${s.reviewed_fields} reviewed fields`)));if(snapshots.some(s=>s.id===previous))$("snapshot").value=previous;}
function clearComparison(){comparisonVersion++;comparisonResult=null;$("comparison").replaceChildren();$("download-comparison").disabled=true;$("historical").hidden=true;}
async function showCitation(cite,snapshot){
  $("citation-label").textContent=cite.capability==="text_highlight"?`Exact text-layer highlight · page ${cite.page} · ${cite.layer_id}`:cite.label;
  const box=$("citation-content");box.replaceChildren();
  if(cite.capability==="text_highlight"){
    const text=snapshot?.objects[cite.text_snapshot_id]?.value||await api(`/api/v2/objects/${enc(cite.text_snapshot_id)}`),page=text.pages.find(p=>p.page===cite.page&&p.layer_id===cite.layer_id);
    if(!page)throw new Error("The cited immutable text layer is unavailable.");const chars=Array.from(page.text);if(chars.slice(cite.start,cite.end).join("")!==cite.quote)throw new Error("Citation no longer matches its frozen text.");
    const pre=element("pre");pre.append(document.createTextNode(chars.slice(0,cite.start).join("")),element("mark",chars.slice(cite.start,cite.end).join("")),document.createTextNode(chars.slice(cite.end).join("")));box.append(pre);
  }else{
    const artifact=await findArtifact(cite.artifact_id,snapshot);if(!artifact)throw new Error("Original source artifact unavailable.");
    const src=`/api/v2/artifacts/${enc(artifact.sha256)}/pages/${cite.page}.png`,image=element("img");image.alt=`Original source page ${cite.page}`;image.src=src;
    image.addEventListener("error",()=>{box.prepend(element("p","Page preview unavailable. Open the original PDF to inspect the transcription.","notice"));});
    box.append(image);const link=element("a","Open original PDF");link.href=`/api/v2/artifacts/${enc(artifact.sha256)}/pdf#page=${cite.page}`;link.target="_blank";link.rel="noopener";box.append(link);
    if(cite.capability==="pdf_region")image.addEventListener("load",()=>{
      const r=cite.region;if(image.naturalWidth!==r.render_width||image.naturalHeight!==r.render_height){box.prepend(element("p","The current page render differs from the recorded anchor. Showing the page and transcription without a region highlight.","notice"));return;}
      const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg"),pageImage=document.createElementNS(ns,"image"),rect=document.createElementNS(ns,"rect");svg.setAttribute("viewBox",`0 0 ${r.render_width} ${r.render_height}`);svg.setAttribute("role","img");svg.setAttribute("aria-label",`Recorded PDF region, page ${cite.page}`);pageImage.setAttribute("href",src);pageImage.setAttribute("width",r.render_width);pageImage.setAttribute("height",r.render_height);
      for(const key of ["x","y","width","height"])rect.setAttribute(key,r[key]);rect.setAttribute("fill","#ffcc4470");rect.setAttribute("stroke","#9c6415");rect.setAttribute("stroke-width","3");svg.append(pageImage,rect);image.replaceWith(svg);
    });
    box.append(element("blockquote",cite.quote),element("p",cite.note||"Human visual evidence.","muted"));
  }
  if(!$("citation-dialog").open)$("citation-dialog").showModal();requestAnimationFrame(()=>box.querySelector("mark")?.scrollIntoView({block:"center"}));
}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"})),a=element("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function compare(){
  clearComparison();const version=comparisonVersion,snapshotId=$("snapshot").value,question=$("question").value;
  if(!snapshotId)throw new Error("Save or select a reviewed snapshot first.");
  const columns=[...$("columns").querySelectorAll("input:checked")].map(i=>i.value);if(!columns.length)throw new Error("Select at least one comparison field.");
  let snapshot,result;
  try{
    snapshot=await api(`/api/v2/snapshots/${enc(snapshotId)}`);if(version!==comparisonVersion)return;
    result=await api("/api/v2/comparisons",{spec:{schema_version:"skony.comparison.v0.2",question,snapshot_id:snapshot.snapshot_id,scope_ids:snapshot.snapshot.scope_ids,columns,permitted_mapping_relations:["exact_in_scope"],ordering:"subject_scope_predicate",unknown_policy:"preserve"},current:false});
  }catch(error){if(version!==comparisonVersion)return;throw error;}
  if(version!==comparisonVersion)return;comparisonResult=result;
  $("historical").hidden=!comparisonResult.historical_warning;$("comparison").replaceChildren();
  const table=element("table"),thead=element("thead"),header=element("tr");header.append(element("th","Affair / scope"),...columns.map(c=>element("th",labels[c])));thead.append(header);const tbody=element("tbody");
  for(const row of comparisonResult.result.rows){const tr=element("tr"),first=element("td");first.append(element("strong",row.subject_id),element("p",row.scope_id,"muted"));if(!row.compatible_for_aggregation)first.append(element("p",row.caveats.length?"Incompatible mapping: original wording only.":"No reviewed equivalence mapping: original wording only.","muted"));tr.append(first);
    for(const col of columns){const field=row.fields[col],td=element("td");td.append(element("div",field.value??(field.source_assessment==="absent_in_reviewed_scope"?"Not present in the reviewed material":"Unknown / not assessed"),"cell-value"));td.append(element("p",field.source_assessment.replaceAll("_"," "),"muted"));if(field.completeness)td.append(element("p",`Completeness: ${field.completeness.semantic_completeness.replaceAll("_"," ")}`,"muted"));
      for(const [i,cite] of field.citations.entries()){const button=element("button",`Source ${i+1} · p. ${cite.page}`);button.addEventListener("click",()=>act(()=>showCitation(cite,snapshot.snapshot)));td.append(button);}tr.append(td);}tbody.append(tr);}
  table.append(thead,tbody);$("comparison").append(table);$("download-comparison").disabled=false;message("Comparison reproduced from frozen reviewed evidence. Unknown fields remain explicit.");
}
$("scope").addEventListener("change",()=>act(selectScope));$("refresh").addEventListener("click",()=>act(refresh));$("source-page").addEventListener("change",showCurrentText);$("existing-affair").addEventListener("change",toggleAffair);$("add-segment").addEventListener("click",addSegment);$("close-citation").addEventListener("click",()=>$("citation-dialog").close());
$("association-form").addEventListener("submit",event=>{event.preventDefault();act(async()=>{const name=reviewer(),note=$("association-note").value.trim();if(!note)throw new Error("Record the evidence for this association.");let subject=$("existing-affair").value;
  if(!subject){subject=$("affair-id").value.trim();await api("/api/v2/affairs",{revision:0,affair:{internal_id:subject,provider_namespace:$("provider").value.trim(),body_id:$("body-id").value.trim(),body_key:$("body-key").value.trim(),official_affair_id:$("official-id").value.trim()||null,jurisdiction_level:$("level").value,source_ids:selectedScope.source_ids}});}
  await api("/api/v2/scopes",{revision:selectedScope.revision,reviewer:name,note,scope:{binding:{...selectedScope.binding,subject_id:subject,membership:"reviewed",role:$("role").value},source_ids:selectedScope.source_ids,mapping_ids:selectedScope.mapping_ids}});await refresh();message("Association saved. Dependent reviews are checked against its new version.");});});
$("correction-form").addEventListener("submit",event=>{event.preventDefault();act(async()=>{const assessment=$("assessment").value,segments=[],image_segments=[];if(assessment==="present")for(const row of $("segments").querySelectorAll(".segment")){const page=currentText.pages[Number(row.querySelector("select").value)],quote=row.querySelector("textarea").value;if(!quote.trim())throw new Error("Enter each supporting passage.");if($("basis").value==="text")segments.push({page:page.page,layer_id:page.layer_id,quote,context_anchor:null});else image_segments.push({artifact_id:selectedScope.binding.artifact_id,text_snapshot_id:null,page:page.page,layer_id:null,quote,basis:"image",note:$("visual-note").value});}
  await api("/api/v2/corrections",{scope_id:selectedScope.id,predicate:$("field").value,assessment,segments,image_segments});await refresh();message("Proposal saved with its source evidence. Review its meaning before accepting.");});});
$("freeze").addEventListener("click",()=>act(async()=>{const selected=[...$("decisions").querySelectorAll("input:checked")];if(!selected.length)throw new Error("Select eligible reviewed decisions to freeze.");const result=await api("/api/v2/snapshots",{decision_ids:selected.map(i=>i.value),scope_ids:[...new Set(selected.map(i=>i.dataset.scope))],exclusions:[]});clearComparison();await loadSnapshots(result.snapshot_id);message(`Snapshot saved: ${result.snapshot_id.slice(0,12)}. Its source evidence and decisions are frozen.`);}));
$("snapshot").addEventListener("change",clearComparison);
$("columns").addEventListener("change",clearComparison);$("question").addEventListener("input",clearComparison);
$("compare-button").addEventListener("click",()=>act(compare));$("download-snapshot").addEventListener("click",()=>act(async()=>{const value=await api(`/api/v2/snapshots/${enc($("snapshot").value)}`);download(value,`skony-snapshot-${value.snapshot_id.slice(0,12)}.json`);}));$("download-comparison").addEventListener("click",()=>{if(comparisonResult)download(comparisonResult,`skony-comparison-${comparisonResult.result_id.slice(0,12)}.json`);});
$("reviewer").addEventListener("change",()=>{try{localStorage.setItem("skony.reviewer",$("reviewer").value);}catch{}});
for(const [key,label] of Object.entries(labels)){$("field").append(option(key,label));const c=checkLabel(label);c.input.value=key;c.input.checked=["question_text","answer_text","decision_raw"].includes(key);$("columns").append(c.label);}
try{$("reviewer").value=localStorage.getItem("skony.reviewer")||"";}catch{}
act(async()=>{await refresh();message("Local scoped records loaded. Existing legacy decisions remain historical until revalidated.");});

