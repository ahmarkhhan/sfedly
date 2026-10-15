"use strict";

const $ = id => document.getElementById(id);
const labels = {title:"Title",affair_type_raw:"Affair type",submitter_raw:"Submitted by",submitted_date_raw:"Date on the document",question_text:"Request / question",answer_text:"Government answer",decision_raw:"Decision",decision_date_raw:"Decision date"};
let state = null, current = null, page = 1, view = "image", activeEvidence = null, polling = null, toastTimer = null, formAction = null, loading = false;
const node = (tag, className, text) => {const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=text;return n;};
const apiPath = (suffix="", id=current?.id) => `/api/documents/${encodeURIComponent(id)}${suffix}`;

async function api(path, options={}) {
  const response=await fetch(path,{...options,headers:{...(options.body?{"X-Skony-Token":state?.csrf_token}:{}),...options.headers}});
  const data=await response.json();
  if(!response.ok){const error=new Error(data.error||"The operation could not finish.");error.status=response.status;throw error;}
  return data;
}
function toast(message,error=false){$("toast").textContent=message;$("toast").classList.toggle("error",error);$("toast").hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("toast").hidden=true,6500);}
function reviewer(){return $("reviewer").value.trim()||"Local reviewer";}
function countReviewed(){return Object.values(current.fields).filter(f=>f.review).length;}
function shortModel(model){return model?.split("/").pop()?.replace("Apertus-v1.5-","Apertus 1.5 · ")||"Apertus";}

async function refreshState(){
  state=await api("/api/state");
  $("model-status").replaceChildren(node("span","status-dot"),document.createTextNode(state.mode==="replay"?"Replay mode · live extraction disabled":state.api_configured?`${shortModel(state.configured_model)} · API configured` : "Configure Apertus to extract"));
  $("model-status").classList.toggle("offline",!state.api_configured);
  $("document-count").textContent=state.documents.length;
  renderQueue();
}
function renderQueue(){
  $("document-list").replaceChildren();
  for(const doc of state.documents){
    const button=node("button",`document-item${current?.id===doc.id?" selected":""}`);
    button.setAttribute("aria-current",current?.id===doc.id?"page":"false");
    button.append(node("span","doc-symbol","PDF"),node("strong","",doc.title),node("small","",`${doc.source.body_label||"Parliamentary document"} · ${doc.pages} pages`),node("small","",`${doc.reviewed}/8 reviewed${doc.extraction_state==="running"?" · Extracting…":""}`));
    button.addEventListener("click",()=>selectDocument(doc.id));$("document-list").append(button);
  }
}
async function selectDocument(id){
  try{current=await api(apiPath("",id));page=1;activeEvidence=null;renderDocument();renderQueue();ensurePolling();}
  catch(error){toast(error.message,true);}
}
function renderDocument({preserveSource=false}={}){
  $("empty-state").hidden=!!current;$("workspace").hidden=!current;if(!current)return;
  const doc=current.document,source=current.source,title=current.fields.title;
  $("document-title").textContent=(title.review?.value||title.suggestion.value||current.filename);
  $("document-meta").textContent=[source.body_label,source.language_label,`${doc.pages.length} pages`].filter(Boolean).join("   /   ");
  const recorded=["recorded_pilot","cached_batch"].includes(current.extraction_origin);
  $("document-description").textContent=current.extraction_origin==="synthetic_fixture"?"Practice document. Suggested values are authored examples, not model output or reviewed data.":current.model?`${recorded?"Recorded Apertus extraction":"Apertus extraction"}${current.source.synthetic?" on a practice document":""} · ${shortModel(current.model)} · ${current.latency_seconds?.toFixed(1)||"—"}s · Review each field before export.`:state.mode==="replay"?"Live extraction is disabled in replay mode. You can review this document manually.":"Ready for Apertus. Extraction starts only when you choose it.";
  const reviewed=countReviewed(),located=Object.values(current.fields).filter(f=>f.suggestion.status==="source_located").length;
  $("reviewed-count").textContent=reviewed;$("progress-fill").className=`progress-fill progress-${reviewed}`;
  $("located-count").textContent=`${located} source-located suggestions · ${8-reviewed} awaiting review`;
  $("export-button").disabled=reviewed===0;
  $("extract-button").disabled=!state.api_configured||current.extraction_state==="running";
  $("extract-button").textContent=current.extraction_state==="running"?"Extracting…":current.model?"Run Apertus again":"Extract with Apertus";
  $("extraction-notice").hidden=current.extraction_state==="idle";
  $("extraction-notice").textContent=current.extraction_state==="running"?"Apertus is reading this document. Your saved review decisions will be kept.":current.extraction_error||"";
  $("original-link").href=apiPath("/pdf");
  renderFields();if(!preserveSource)renderSource();
}
function reasonText(reason){
  if(reason==="not_run")return "Run Apertus to suggest a value, or enter a correction after checking the source.";
  if(reason?.includes("corrupt")||reason?.includes("ocr_noise"))return "The extracted name contains unclear characters. Check the original page and enter the name you can read.";
  if(reason?.includes("absent")||reason?.includes("abstain"))return "Apertus did not provide a supported value. Check the source before marking this field absent.";
  return "No supported value was accepted. Check the original document before adding a correction or marking this field absent.";
}
function renderFields(){
  $("field-list").replaceChildren();
  for(const [key,label] of Object.entries(labels)){
    const field=current.fields[key],suggestion=field.suggestion,review=field.review,effective=review||suggestion;
    const card=node("article","field-card");card.id=`field-${key}`;
    const heading=node("div","field-heading");heading.append(node("span","field-label",label));
    const status=review?"reviewed":suggestion.status==="source_located"?"located":suggestion.status==="not_extracted"?"waiting":"missing";
    heading.append(node("span",`badge ${status}`,review?(review.decision==="absent"?"✓ Reviewed absent":"✓ Reviewed"):status==="located"?"Source located":status==="waiting"?"Awaiting extraction":"Needs review"));card.append(heading);
    card.append(node("p",`field-value${effective.value===null?" absent":""}`,effective.value??(review?"Not present in the checked source":"No value accepted")));
    if(review)card.append(node("p","review-attribution",`${review.decision==="corrected"?"Corrected":review.decision==="absent"?"Marked absent":"Confirmed"} by ${review.reviewer}${review.provenance?.basis==="image"?" · Original page checked":""}${review.note?` · ${review.note}`:""}`));
    else if(suggestion.value===null)card.append(node("p","field-hint",reasonText(suggestion.reason)));
    const actions=node("div","field-actions"),provenance=effective.provenance;
    if(provenance){const source=node("button","source-action",`Page ${provenance.page} · View evidence ↗`);source.addEventListener("click",()=>showEvidence(key,provenance));actions.append(source);}
    if(review){const undo=node("button","text-button","Undo review");undo.addEventListener("click",()=>saveAction(key,"undo"));actions.append(undo);}
    else if(suggestion.value!==null){const confirm=node("button","confirm-action","Confirm ✓");confirm.disabled=current.extraction_state==="running";confirm.addEventListener("click",()=>saveAction(key,"confirm"));actions.append(confirm);}
    const correct=node("button","text-button",review?"Edit correction":"Correct");correct.disabled=current.extraction_state==="running";correct.addEventListener("click",()=>openReview(key,"correct"));actions.append(correct);
    if(!review){const absent=node("button","text-button","Mark absent");absent.disabled=current.extraction_state==="running";absent.addEventListener("click",()=>openReview(key,"missing"));actions.append(absent);}
    card.append(actions);$("field-list").append(card);
  }
}
function renderSource(){
  const pages=current.document.pages,currentPage=pages.find(p=>p.number===page)||pages[0];page=currentPage.number;
  $("page-number").textContent=`${page} / ${pages.length}`;$("previous-page").disabled=page<=1;$("next-page").disabled=page>=pages.length;
  $("image-tab").classList.toggle("selected",view==="image");$("image-tab").setAttribute("aria-pressed",view==="image");
  $("text-tab").classList.toggle("selected",view==="text");$("text-tab").setAttribute("aria-pressed",view==="text");
  $("image-view").hidden=view!=="image";$("text-view").hidden=view!=="text";$("zoom-button").hidden=view!=="image";
  $("source-footer-caption").textContent=view==="image"?"The original page is the reference for review.":"Extracted text can contain OCR errors. Check the page image.";
  if(view==="image"){
    const src=apiPath(`/pages/${page}.png`);
    if($("page-image").getAttribute("src")!==src){$("page-image").hidden=true;$("image-message").hidden=false;$("image-message").textContent="Loading original page…";$("page-image").src=src;}
    $("page-image").alt=`Original document · page ${page}`;
    const imageEvidence=activeEvidence?.provenance;
    if(imageEvidence?.basis==="image"&&imageEvidence.page===page){
      const review=current.fields[activeEvidence.field]?.review;
      $("source-footer-caption").textContent=`Page and human transcription · no region coordinates recorded. ${imageEvidence.quote}${review?.note?` — ${review.note}`:""}`;
    }
  }else{
    $("page-text").replaceChildren();
    const p=activeEvidence?.provenance;
    if(p&&p.page===page&&p.basis!=="image"&&Number.isInteger(p.start)&&Number.isInteger(p.end)){
      // Python offsets count Unicode characters; JavaScript strings count UTF-16 units.
      const text=Array.from(currentPage.text);$("page-text").append(document.createTextNode(text.slice(0,p.start).join("")),node("mark","",text.slice(p.start,p.end).join("")),document.createTextNode(text.slice(p.end).join("")));
      $("evidence-caption").textContent=`Supporting passage for ${labels[activeEvidence.field].toLowerCase()}. A matching passage still needs a meaning check.`;
      requestAnimationFrame(()=>$("page-text").querySelector("mark")?.scrollIntoView({block:"center"}));
    }else{
      $("page-text").textContent=currentPage.text||"This page has no extractable text. Check the original PDF.";
      $("evidence-caption").textContent="Original extracted page text. Line breaks and unclear characters are preserved.";
    }
  }
}
function showEvidence(field,provenance){page=provenance.page;activeEvidence={field,provenance};view=provenance.basis==="image"?"image":"text";renderSource();if(window.innerWidth<=800)$("source-stage").scrollIntoView({block:"center",behavior:"smooth"});}
function openReview(field,action){
  formAction={field,action,revision:current.revision,documentId:current.id};const item=current.fields[field],value=item.review||item.suggestion,p=value.provenance;
  $("dialog-title").textContent=`${action==="missing"?"Mark absent":"Correct"}: ${labels[field].toLowerCase()}`;
  $("correction-controls").hidden=action==="missing";$("save-review").textContent=action==="missing"?"Save absence review":"Save correction";
  $("review-value").value=value.value||"";$("review-quote").value=p?.quote||"";$("review-note").value=item.review?.note||"";$("review-basis").value=p?.basis||"text";
  $("review-page").replaceChildren(...current.document.pages.map(p=>{const o=node("option","",`Page ${p.number}`);o.value=p.number;return o;}));$("review-page").value=p?.page||page;
  $("form-error").hidden=true;updateDialogHelp();$("review-dialog").showModal();
}
function updateDialogHelp(){
  const missing=formAction?.action==="missing",image=$("review-basis").value==="image";
  $("dialog-help").textContent=missing?"Only mark this field absent after checking all relevant pages. Add a note describing what you checked.":image?"Read the original page and transcribe the value and supporting passage. Add a note identifying its location. This saves your visual review without claiming a match in the extracted text.":"Copy the value and supporting passage from the selected page's extracted text. The passage must contain the value. For unclear OCR, choose the original page image instead.";
  $("note-label").textContent=missing||image?"Review note · required":"Review note · optional";$("review-note").required=missing||image;$("review-note").minLength=missing||image?8:0;
  $("review-value").required=!missing;$("review-quote").required=!missing;
}
async function saveAction(field,action,extra={},context={id:current.id,revision:current.revision}){
  if(loading)return;loading=true;
  try{
    const result=await api(apiPath("/review",context.id),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({field,action,revision:context.revision,reviewer:reviewer(),...extra})});
    if(current.id===context.id){current=result;renderDocument({preserveSource:true});}
    await refreshState();$("review-dialog").close();toast(action==="undo"?"Review undone. The original suggestion is preserved.":"Review saved. Your decision is included in the reviewed export.");return true;
  }catch(error){
    if(error.status===409){current=await api(apiPath());renderDocument({preserveSource:true});$("review-dialog").close();toast(`${error.message} The latest fields are now shown.`,true);return false;}
    if($("review-dialog").open){$("form-error").textContent=error.message;$("form-error").hidden=false;}else toast(error.message,true);return false;
  }finally{loading=false;}
}
function ensurePolling(){
  if(polling)clearTimeout(polling);polling=null;
  if(!state.documents.some(d=>d.extraction_state==="running")&&current?.extraction_state!=="running")return;
  polling=setTimeout(async()=>{try{await refreshState();if(current){current=await api(apiPath());renderDocument({preserveSource:true});}ensurePolling();}catch(error){toast("The workbench connection was interrupted. Reload to reconnect.",true);}},2000);
}
async function upload(file){
  if(!file)return;$("upload-button").disabled=true;toast("Reading the PDF…");
  try{const data=await api(`/api/upload?filename=${encodeURIComponent(file.name)}`,{method:"POST",body:file,headers:{"Content-Type":"application/pdf"}});await refreshState();await selectDocument(data.id);toast(state.mode==="replay"?"PDF added. Review it manually, or restart in live mode to use Apertus.":"PDF added. Choose Extract with Apertus when you are ready.");}
  catch(error){toast(error.message,true);}finally{$("upload-button").disabled=false;$("upload-input").value="";}
}
async function exportReviewed(){
  try{const data=await api(apiPath("/export"));const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const link=node("a");link.href=url;link.download=`skony-reviewed-${current.document.sha256.slice(0,10)}.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`Exported ${Object.keys(data.fields).length} reviewed fields. ${data.unreviewed_fields.length} fields remain unreviewed.`);}
  catch(error){toast(error.message,true);}
}
async function showHistory(){
  try{const entries=await api(apiPath("/audit"));$("history-list").replaceChildren();
    if(!entries.length)$("history-list").append(node("p","history-empty","No review decisions yet. Confirm, correct or mark a field absent to start the audit trail."));
    for(const item of entries){const entry=node("article","history-entry"),after=item.snapshot.after;
      entry.append(node("strong","",`${labels[item.field]||item.field} · ${item.action}`),node("p","",`${item.reviewer} · ${new Date(item.created_at).toLocaleString()}`));
      if(after?.note)entry.append(node("p","",after.note));const details=node("details"),summary=node("summary","","Before / after");details.append(summary,node("pre","",JSON.stringify(item.snapshot,null,2)));entry.append(details);$("history-list").append(entry);}
    $("history-dialog").showModal();
  }catch(error){toast(error.message,true);}
}
$("upload-button").addEventListener("click",()=>$("upload-input").click());$("empty-upload").addEventListener("click",()=>$("upload-input").click());$("upload-input").addEventListener("change",event=>upload(event.target.files[0]));
$("reviewer").addEventListener("change",()=>{try{localStorage.setItem("skony.reviewer",reviewer());}catch{}});
$("previous-page").addEventListener("click",()=>{page--;activeEvidence=null;renderSource();});$("next-page").addEventListener("click",()=>{page++;activeEvidence=null;renderSource();});
$("image-tab").addEventListener("click",()=>{view="image";renderSource();});$("text-tab").addEventListener("click",()=>{view="text";renderSource();});
$("zoom-button").addEventListener("click",()=>{const zoomed=$("image-view").classList.toggle("zoomed");$("zoom-button").textContent=zoomed?"Fit page −":"Zoom in ＋";});
$("page-image").addEventListener("load",()=>{$("image-message").hidden=true;$("page-image").hidden=false;});$("page-image").addEventListener("error",()=>{$("page-image").hidden=true;$("image-message").hidden=false;$("image-message").textContent="Page preview unavailable. Open the original PDF above, or inspect extracted text.";});
$("extract-button").addEventListener("click",async()=>{try{await api(apiPath("/extract"),{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});current=await api(apiPath());await refreshState();renderDocument({preserveSource:true});ensurePolling();toast("Apertus extraction started. Saved reviews will be kept.");}catch(error){toast(error.message,true);}});
$("export-button").addEventListener("click",exportReviewed);$("audit-button").addEventListener("click",showHistory);$("close-history").addEventListener("click",()=>$("history-dialog").close());
$("close-review").addEventListener("click",()=>$("review-dialog").close());$("cancel-review").addEventListener("click",()=>$("review-dialog").close());$("review-basis").addEventListener("change",updateDialogHelp);
$("review-form").addEventListener("submit",async event=>{event.preventDefault();$("save-review").disabled=true;const missing=formAction.action==="missing";await saveAction(formAction.field,formAction.action,{note:$("review-note").value,...(!missing?{value:$("review-value").value,page:Number($("review-page").value),quote:$("review-quote").value,basis:$("review-basis").value}:{})},{id:formAction.documentId,revision:formAction.revision});$("save-review").disabled=false;});
(async()=>{try{try{$("reviewer").value=localStorage.getItem("skony.reviewer")||"Local reviewer";}catch{}await refreshState();if(state.documents.length)await selectDocument(state.documents[0].id);else renderDocument();}catch(error){toast("Could not load the workbench. Reload after starting the local server.",true);}})();
