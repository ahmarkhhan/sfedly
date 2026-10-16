# User-supplied research material, 15 October 2026

Preserved verbatim as reference material. It mixes official excerpts, previous
assistant responses and third-party technical advice. It is not itself an
official rulebook or implementation-status record. The current interpretation
is in [project direction](../16-project-direction.md); source access is recorded
in the [source register](../17-source-register.md).

## Resources, official links and earlier project discussion

Attachment SHA-256: 48797d4ed7d3fbb12cf1f7eb9988d0792c3ebc07b1d5e340c2b01a61882be251.

~~~text
3:05 AM







# **Resources & Tools** ## 👉🏼 This page will be fully released on October 1st…Devpost Join a hackathon Host a hackathon Resources karyl1 Notifications Loadin…

https://hackapertus.devpost.com/resources
https://hackapertus.devpost.com/resources
https://hackapertus.devpost.com/resources
https://hackapertus.devpost.com/resources
https://hackapertus.devpost.com/resources
https://hackapertus-document-extraction-26a562.gitlab.io/#/title-slide these are slides for data
https://hackapertus.devpost.com/resources
https://hackapertus.devpost.com/resources
- Devpost (image)
-
- Join a hackathon
-
- Host a hackathon
-
- Resources
-
-
- karyl1 (image)
Notifications
Loading...
Hack Apertus (image)
- Overview
- My projects
- Participants (898)
- Resources
- Rules
- Project gallery
- Updates
- Discussions
📅 TIMELINE

13 AUG 2026	8:00 CEST	Registrations open
1 OCT 2026	12:00 CEST	Challenges are released, Start Hacking
16 OCT 2026	12:00 CEST	Final submission deadline / Submissions to be done here (link will be shared soon)
16 - 22 OCT 2026		Judging period*
23 OCT 2026	12:00 CEST	Estimated winners announcement


*Time required to evaluate results depends on the number of submissions. We, as organizers, reserve the right to update the contest timeline if we deem it necessary.
✅ Eligibility
Aged 18+, open to people from all backgrounds
All countries/territories, excluding standard exceptions: Brazil, Crimea, Cuba, Iran, North Korea, Quebec, Russia per Devpost rules
🤝 Code of Conduct
https://hackapertus.ch/code-of-conduct
Devpost
- About
- Careers
- Contact
- Help
Hackathons
- Browse hackathons
- Explore projects
- Host a hackathon
- Hackathon guides
Portfolio
- Your projects
- Your hackathons
- Settings
Connect
- Twitter
- Discord
- Facebook
- LinkedIn
© 2026 Devpost, Inc. All rights reserved.
- Community guidelines
- Security
- CA notice
- Privacy policy
- Terms of service
Toggle Customer Support
🏋🏻‍♂️Getting Started Guide - Online
You’ve arrived at stage 1 of “Hack Apertus”. Welcome!
This Online hackathon is an invitation to spend just over two weeks building with Apertus, Switzerland's fully open LLM. From 1–16 October, builders everywhere gather online to push Apertus 1.5 further.
If you care about open and trustworthy AI that anyone can use, this is your place.
You'll work with both the 8B and 70B 1.5 models, backed by our partners CSCS and Phoeniqs and experienced mentors alongside you. Everything you ship stays open and reusable.
The winner teams advance to the Grand Finals on 14.05.2027 in St. Gallen, Switzerland, where you'll compete for the Main «Hack Apertus» Award.
Step 1: Get familiar with below information
Step 2: Join Discord & Devpost
 Step 3: Find team members (Solo – 5)
 Step 4: Start building on 1 OCT ‘26, 12:00 CEST
 Step 5: Submit on 16 OCT ‘26, 12:00 CEST on our website
General Information
**Registration on [Devpost**](https://app.notion.com/Registration-on-Devpost-6d6b4fec112a827586b401bee7161bf4?pvs=21)
💡 FAQ
Schedule
Online sessions
Communication Channels
How to team up
🤝 Code of Conduct
Challenges: Track 1. Apertus Readiness
Challenges: Track 2. Apertus Adoption
Resources & Tools
Hackathon Partners
Mentors
Jury & Awards
How to Submit a Project
Recordings & Slides
Great projects will pop up here after 24 Oct ‘26.😇
On-Site Hackathons
📅 Hacks in Liebefeld, Zurich, Basel, Lausanne, St.Gallen
Registrations open step-by-step here on sprintd:
 https://app.sprintd.org/series/hack-apertus
now you have everything, official demos, example projects, data, challenge info sessions slides, and find things that are relavent and important but i didnt mentioned.
so you task is to assess all that data, from all the links from the given text and write the requirements, eligibilty or what or how it can win for my project. also check which things are different from what is asked. also write whole this data and links in md file







3:14 AM






Worked for 15m 33s



Created the [complete Markdown assessment](D:/development/Skony/docs/15-hack-apertus-complete-assessment.md), covering:
- Eligibility and submission requirements.
- All seven PDFs—150 pages—and relevant resources.
- Skony’s gaps, conflicting instructions, and priorities.
- Recommendations to strengthen its chances.
- Source links and the original pasted text.
Important correction: OpenParlData encourages a focused request/answer prototype. Skony’s main remaining priorities are reviewed multilingual evidence, Docker execution, a public repository, and the final report.
The scope clarification comes from D:/development/Skony/tmp/event-assessment/openparldata-qa.pdf.


3:30 AM







so whats missing or what to change?







3:38 AM






Keep the current review interface. Focus on these six gaps:
Priority	Missing	What to change
1	Judge-ready execution	Add Docker and a working make run. Test it from a clean copy without your local setup or private files.
2	Real evaluation	Manually review a small sample across languages, parliaments and government levels. Include both requests and government answers. Measure correctness, completeness, abstention and evidence accuracy.
3	A comparable affair structure	Link related request/answer PDFs to the same affair. Preserve raw wording and add documented normalized categories. Support multiple evidence spans—or explicitly flag that limitation.
4	Cross-parliamentary demonstration	Answer one concrete question using reviewed records from different parliaments, with source citations and a clear coverage limit.
5	Submission artifacts	Publish or verify the public GitHub repository, provide runnable samples, and finish the technical report as a PDF of at most six pages.
6	Licensing and accurate documentation	Resolve sample redistribution rights, state the required licences, and exclude the old reports containing placeholder metrics and unimplemented features.


The biggest missing piece is proof that the extraction works beyond the single Nidau example. Passing 35 engineering tests does not establish model accuracy.
You can keep a narrow request/answer scope. Document unsupported tables, annexes, procedural history and difficult scans; you do not need to implement the entire roadmap before submission.
Start with Docker and reviewed request/answer examples. Those provide the foundation for the comparison and final report. The detailed checklist is in the [assessment](D:/development/Skony/docs/15-hack-apertus-complete-assessment.md).


3:38 AM







Judge-ready executionAdd Docker and a working make run. Test it from a clean copy without your local setup or private files.
if i make it, can it will be easy to update the file and in it the project will be updated?







3:40 AM






Worked for 19s






Yes. You can keep editing Skony normally after adding Docker.
We should configure it so the update workflow is:
1. Edit your project files.
2. Run make run again.
3. Docker rebuilds and starts the app with your latest changes.
You usually only change the Docker configuration when adding dependencies or changing how the app starts. Ordinary Python, HTML, CSS and JavaScript edits stay in their existing files.
Your uploaded PDFs and review decisions should use persistent storage so rebuilding preserves them.
For judges to receive those updates, also publish the latest files to your GitHub repository.
~~~

## Pasted technical recommendations and continuation

Attachment SHA-256: 69b653181e97dc22fc20f0e41c4a8c598a2a801da0c49ce843ed0620b095fa78.

~~~text
Must add (D3 — the evidence):



Batch runner with response caching — cache key = doc_hash + prompt_version + model; second run makes zero HTTP calls (write the test). This makes replay mode, eval, and Friday's clean-room check cheap and deterministic. ~2h.

Gold set: 12–16 human-reviewed docs via your existing workbench (confirm/correct/missing → reviewed-only export → commit as data/gold/*.json + annotations README). Stratify: ≥3 bodies, DE+FR, ≥2 government levels, ≥3 scanned/OCR-poor, and per the Q&A, prefer affairs that have both a submission and a government-response document. This is the long pole — protect ~6h for it.

Deterministic scorer — typed fields exact/normalized; free text token-F1. Report: per-field P/R/F1, abstention rate by reason, source-location accuracy, semantic correctness among located fields (your key differentiator: located ≠ correct), per-language and per-body slices, token/latency table. make eval → docs/eval/report.md. ~3h.

One baseline — a generic unconstrained "extract everything as JSON" prompt on the same frozen docs, same scorer. Cheap (~1h with caching) and directly demonstrates why schema + verification is mandatory. Bonus: rerun the sample through 8B — you already have single-doc evidence that 8B fails structured output; a systematic schema-valid-rate comparison is a real insight.

Should add (D1 — the representation answer):



Minimal derived layer, explicitly labeled derived: affair_type enum

The model reached the length limit for this response, so the content may be incomplete. Send “Continue” to ask it to keep going. You can also adjust Max Output Tokens in Conversation Settings.



Featherless (moonshotai/Kimi-K3)



· 1436487 tokens

continue from where you left





Deeply thought



· The user wants me to continue from where I left off. I was in the middle of section 4, point 5 — the "Should add (D1 — the representation answer)" list. Let me continue from there, keeping it complete but concise since we're running low on time (deadline ~35h away).



Should add (D1 — the representation answer), continued:



Minimal derived layer, explicitly labeled derived: true: a small affair_type enum map (e.g. Motion|Interpellation|Postulat|Anfrage + FR equivalents) applied to affair_type_raw, plus a date normalizer (submitted_date ISO) — both mapping to a versioned vocabulary file, raw values preserved untouched. This is exactly the D1 insight deliverable: you show what can be normalized across bodies and what can't. ~2h.

Request/answer pairing at the affair level — the Q&A explicitly blesses this focused scope. Link documents by affair_id from the OpenParlData metadata (you already store it in the source manifest): a submission PDF and its government-response PDF become one affair record with two document roles. Your schema already has question_text/answer_text; the gap is assembling them across documents. Even 3–4 matched pairs demonstrate the core feasibility claim. ~2–3h.

One cross-parliamentary question answered from verified data (D3) — a deterministic query (no RAG/chatbot) over reviewed extractions, e.g. "Which sampled bodies debated ‹topic›, who submitted, and how did executives respond?" → a table with body / affair / submitter / decision / (doc, page, span) citations, plus an explicit scope statement ("sampled corpus, not all Swiss parliaments"). Ship it as make question + docs/eval/cross_parliamentary_answer.md. ~1–2h once gold exists.

Do not add (absorb into the report's "Future work" section): free-form RAG/chat, OCR pipeline (measure the abstention on scans instead — that is a finding), multi-page field assembly (state the limitation), RDF/JSON-LD export (mention as mapping direction), PostgreSQL, auth, IT language, 8B self-hosting, prompt-optimization search.



5. The feasibility finding — your actual judged deliverable

Frame the report around one question: "Which request/answer fields can share a representation across our sampled parliaments while preserving meaning and traceability?"



Then answer it with a three-bucket table built from your measured slices:



Bucket	Example content

Generalises	Title, affair type, submission date, request text — located verbatim across bodies (with your per-body/per-language numbers)

Partially	Date semantics (your Nidau pilot located the printed date in the submitted-date slot — a located-but-wrong-role case); vocabulary granularity differences cantonal vs municipal

Breaks	Corrupt OCR submitters (your abstention case), scanned annexes, single-page combined question+decision layouts, answers split across pages/documents

That honest partial/negative answer is explicitly a success condition per the brief — and you already have real material for every bucket from one PDF.



6. Revised schedule (you're ~12h behind doc 13's plan — it's Thu 03:35 PKT)

Block	Time (PKT)	Work

Now → Thu 09:00	~5h	Repo hygiene: delete (2).env, rotate CSCS key, fresh template repo, move fixtures to data/sample/, Dockerfile + Makefile + replay mode, server bind fix, docker build overnight sanity. Gates: fresh clone → make run shows seeded workbench with zero key.

Thu 09:00 → 19:00	~10h	Corpus fetch (bodies: Nidau muni DE, Bern canton DE, Fribourg/Vaud canton FR, city of Zürich/Genève — all verified present in bodies.ndjson) → batch runner + caching → gold annotation in the workbench (12–16 docs, ≥3 scans, prefer matched request/response pairs). Batch runs interleave with annotation via cache.

Thu 19:00 → 24:00	~5h	Scorer + baseline + 8B comparison rerun → docs/eval/report.md with real numbers; cross-parliamentary question; derived-type enum if time. Feature freeze at midnight.

Fri 09:00 → 12:00	3h	Report rewrite in the template's 8 sections → PDF ≤ 6 pages, zero placeholders; clean-room check (fresh clone, make run/test/eval, timed); README final.

Fri 12:00 → 13:00	1h	Submit at hackapertus.ch/online-hack/submissions; save confirmation. 2h buffer before the 15:00 PKT hard stop.

Cuts if the gold annotation overruns: 12 docs beats 16 unreviewed; drop the 8B comparison before dropping a body or a language; the cross-parliamentary question can be answered over as few as 3 bodies.



7. The five decisions to lock right now

Rotate the CSCS key — it sat in an unencrypted duplicate file; the repo goes public tomorrow.

Replay-first architecture — the judge experience must not depend on CSCS being up or a key being present. Your caching layer serves replay, eval, and the demo simultaneously.

Gold via the workbench you already built — do not write a separate annotator; export reviewed decisions and commit them.

70B is your scored model; 8B is a finding — document the structured-output reliability gap systematically instead of treating it as an embarrassment.

The report's Section 5 (insight) gets written from measured slices only — every number traceable to make eval output at the pinned commit, per your own pre-registered honesty rules in doc 13.

Want me to start on the highest-leverage pieces now — the Dockerfile + Makefile + replay-mode server fix, and the batch runner with caching — so tonight's annotation block has a working pipeline behind it?
~~~
