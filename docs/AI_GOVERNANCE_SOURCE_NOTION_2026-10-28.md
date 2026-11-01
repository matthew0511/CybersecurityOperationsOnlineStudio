# AI Governance

## AI governance at a glance

AI governance connects business value with patient safety, privacy, cybersecurity, reliability, and accountable human decisions. For a healthcare and dental-services environment, the unit of governance should be the **specific AI feature, use case, data flow, and level of autonomy**—not simply the vendor name or an “AI-enabled” product label.

<aside>
🧭

**Working reference—not an approved policy.** The workflows, risk tiers, review intervals, approval gates, and templates below are recommended operating practices for adaptation and formal approval. They do not establish the organization’s current policy, assign actual personnel, certify a vendor, or determine legal compliance. Source-backed framework descriptions and regulatory guidance are cited separately.

</aside>

### Executive comparison: which resource does what?

| Resource | Primary contribution | Practical use | Important limit |
| --- | --- | --- | --- |
| HSCC Third-Party AI Risk and Supply Chain Transparency Guide | Lifecycle-based management of third-party AI and its supply chain. | Structure intake, vendor diligence, contracting, deployment, monitoring, incident coordination, and exit. | Industry guidance; adapt it to the use case and applicable obligations. |
| HSCC AI Cyber Governance Framework Implementation Guide | Governance of AI-related cybersecurity risk in the health sector. | Establish oversight, accountability, cyber safeguards, resilience, and governance for generative and agentic AI. | Its cybersecurity focus is only one part of broader AI governance; clinical, ethical, legal, and other risks also need attention. |
| NIST AI RMF 1.0 | AI risk management through GOVERN, MAP, MEASURE, and MANAGE. | Connect organizational accountability to context, evaluation, treatment, and ongoing review. | Voluntary framework—not a certification or a compliance determination. |
| NIST Generative AI Profile, AI 600-1 | Generative-AI-specific risk considerations and suggested actions. | Extend evaluations to issues such as confabulation, information integrity, privacy, security, and human–AI interaction. | A companion to the AI RMF, not a substitute for local validation. |
| NIST CSF 2.0 and SP 800-161 Rev. 1 | Enterprise cybersecurity outcomes and cybersecurity supply-chain risk management. | Integrate AI into existing security governance, vendor oversight, incident response, and dependency management. | General security diligence alone does not establish AI suitability or clinical safety. |
| Applicable law and authoritative regulatory guidance | Legal obligations determined by entity, relationship, data, function, and jurisdiction. | Establish the legal baseline with privacy, compliance, and legal reviewers. | Framework adoption, a BAA, or a vendor assurance statement is not a blanket compliance finding. |

The two HSCC guides are complementary: use the third-party guide for lifecycle and dependency decisions and the cyber governance guide for oversight and cyber operating practices. Use NIST resources as organizing and assessment tools, while separately determining applicable legal requirements.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)[[3]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)[[4]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)[[5]](https://www.nist.gov/cyberframework)[[6]](https://csrc.nist.gov/pubs/sp/800/161/r1/final)

**Related workspace references:** [Third-Party Risk Management and Vendor Oversight Register](Third-Party%20Risk%20Management%20and%20Vendor%20Oversight%20R%20bc00be56313383319c2b81385aeb3bdf.md) for supplier oversight and evidence; [Comparison Standard Page](Comparison%20Standard%20Page%204880be56313383f2b9af815c3fb6eeab.md) for the relationship between HIPAA, CSF outcomes, and detailed security controls. Keep AI use-case decisions linked to—not confused with—the vendor’s overall assessment.

## 1. Scope and operating principles

**Recommended scope:** purchased AI products; AI features added to existing software; internally built models; generative assistants; transcription, summarization, and documentation tools; patient-facing chatbots; imaging or clinical decision support; revenue-cycle and administrative automation; and agents that can use tools or take actions. Include pilots, free trials, browser extensions, integrations, and vendor-enabled features before they encounter organizational data.

Apply these principles:

- **Purpose before product:** document the problem, expected benefit, non-AI alternative, affected people, and consequences of failure.
- **Minimum necessary exposure:** limit data, access, integrations, retention, and autonomy to the approved purpose.
- **Accountable human ownership:** name a business owner and the reviewers needed for the actual risk; a committee does not replace an accountable operator.
- **Evidence before assurance:** distinguish a vendor claim from documentation, independent assessment, and local testing.
- **Human oversight that works:** define what reviewers must check, when they can intervene, and how they stop or override the system.
- **Lifecycle approval:** approval applies to a defined configuration and workflow, not every future feature or model release.
- **Safe failure and exit:** plan containment, manual fallback, data disposition, and decommissioning before production.

These practices operationalize lifecycle and governance themes in the HSCC guidance; they are proposed local implementation choices rather than a verbatim mandatory checklist.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)

## 2. Accountability and decision rights

| Role | Recommended accountability | Evidence of the role working |
| --- | --- | --- |
| Executive sponsor / designated governing body | Set risk tolerance, resource the program, review material exposure, and resolve escalations. | Approved charter, decisions, escalation records, and risk reporting. |
| AI governance review group | Coordinate cross-functional review, approve within delegated authority, and maintain consistent decision criteria. | Decision log, conditions of approval, exceptions, and follow-up actions. |
| Business / use-case owner | Own intended use, benefits, workflow, training, monitoring, and ongoing suitability. | Intake, operating procedure, metrics, and periodic attestations. |
| Clinical / patient-safety lead, when relevant | Evaluate clinical impact, validation, limitations, supervision, and safe fallback. | Clinical evaluation and documented release criteria. |
| Security / IT | Assess architecture, identities, permissions, logging, integrations, threats, and containment. | Technical assessment, configuration evidence, and test results. |
| Privacy / compliance / legal | Determine applicable obligations, permitted data uses, contracting needs, and transparency requirements. | Documented review and applicable contractual/privacy decisions. |
| Procurement / vendor-risk owner | Collect supplier evidence, coordinate contract requirements, track dependencies and reassessments. | Linked vendor record, diligence findings, and contract obligations. |
| System operator / incident lead | Maintain configuration, detect issues, execute shutdown/fallback, and coordinate response. | Runbook, alerts, exercises, change records, and incident records. |

**Decision rule:** approval should identify the authorized approver, permitted use and data, exact feature/configuration, conditions, residual risk, expiry or next review, and stop conditions. Do not invent an approval authority; leadership should designate it explicitly. Cross-functional oversight should extend beyond cybersecurity when the use case can affect clinical care or other consequential outcomes.[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)

### 2.1 Establish a charter with actual decision authority

A useful governance charter answers questions that a list of committee members does not:

- **Jurisdiction:** which entities, practices, affiliates, environments, tools, and pilots are covered? Who resolves a disagreement about scope?
- **Delegation:** who may authorize a low-risk use, a PHI-processing pilot, a clinical deployment, or a privileged agent? Which decisions require executive escalation?
- **Required concurrence:** which reviews must be completed before a decision? A business sponsor’s support should not be recorded as clinical, privacy, or security approval.
- **Quorum and conflicts:** which functions must participate for a particular decision, and how are commercial or operational conflicts disclosed?
- **Emergency authority:** who can suspend use immediately, who is notified, and who can authorize restoration? Suspension should not depend on waiting for the next committee meeting.
- **Recordkeeping:** where are approvals, evidence, dissent, conditions, exceptions, and follow-up actions retained? Who maintains the record when ownership changes?

**Suggested meeting design:** use routine intake triage to route cases, a cross-functional decision meeting for material risk, and periodic executive reporting for exposure and unresolved decisions. These are proposed operating mechanisms—not a claim that new committees are required. Existing privacy, clinical-quality, IT change, and vendor-risk structures may be reused if decision rights are explicit.

### 2.2 Separate four decisions that are often conflated

| Decision | Question answered | What it does not establish |
| --- | --- | --- |
| Business sponsorship | Is there a credible purpose, owner, and benefit? | That the tool is safe or legally permissible. |
| Technical / professional review | What did security, privacy, clinical, and other reviewers conclude within their scope? | That every risk is accepted or every reviewer has release authority. |
| Residual-risk acceptance | Who is authorized to accept the specifically described remaining exposure? | Permission to waive applicable law or contractual obligations. |
| Release authorization | May this exact configuration enter this workflow under these conditions? | Approval for future use cases, permissions, or model changes. |

**Recommended exception rule:** every exception has a defined scope, justification, compensating controls, owner, authorized approver, expiry, and trigger for early termination. “Accepted risk” without these elements becomes an indefinite gap rather than a controlled decision. Repeated renewal should prompt review of whether the use remains appropriate.

## 3. Inventory the use case—not just the vendor

Maintain an AI use-case record linked to the existing vendor record. A single vendor can support several use cases with different data access and risk. Likewise, a single use case can depend on a platform vendor, model provider, hosting provider, retrieval service, and subprocessors.

| Field group | Minimum recommended information |
| --- | --- |
| Identity and purpose | Use-case ID; product and AI feature; workflow; intended users; business owner; proposed benefit; environment; status. |
| Impact | Patient-facing or clinical role; affected populations; consequences of error; proposed risk tier; rationale. |
| Data | Input sources; PHI/ePHI and other sensitive data; outputs; storage; retention; geography; permitted training/reuse; deletion process. |
| Dependencies | Vendor; relevant model/provider and version where available; hosting; subprocessors; connectors; external tools; known visibility gaps. |
| Access and autonomy | Human and service identities; read/write permissions; actions allowed; approval points; network access; stop mechanism. |
| Evaluation | Test scope; representative scenarios; acceptance criteria; limitations; results; evidence date; unresolved findings. |
| Decision and lifecycle | Reviewers; approval/conditions; residual-risk decision; contract links; go-live date; monitoring owner; next review; change triggers; exit plan. |

**Suggested statuses:** Proposed → Under review → Approved for limited pilot → Approved for production → Suspended → Retired. Keep “approved with conditions” explicit; do not interpret missing evidence or an unanswered questionnaire as a pass. Feature-level inventory and dependency visibility support the third-party lifecycle approach.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)

### 3.1 Build a data and authority map

Document the path from a user’s input to the final downstream action. A generic vendor diagram is insufficient if it omits the customer’s connectors, logging, or workflow.

**Illustrative path:** user or clinical system → application → retrieval/indexing service → model endpoint → output → reviewer → chart, message, or business transaction. Side paths can include telemetry, abuse monitoring, support access, human evaluation, backups, and subprocessors. Not every product has every path; verify rather than assume.

For each hop, record:

1. **Data:** what enters, what is transformed, and what leaves? Include audio, images, transcripts, prompts, retrieved records, generated notes, and derived metadata as applicable.
2. **Authority:** which user or service identity authorizes access? Does the service enforce the current user’s permissions or use a more privileged shared connection?
3. **Boundary:** which organization, tenant, region, or external service receives it? Is the path governed by the reviewed agreement and configuration?
4. **Persistence:** what is stored, indexed, cached, or logged; for how long; with what access and deletion limits?
5. **Action:** can the output only be viewed, or can it update a chart, contact a patient, initiate a transaction, or trigger another system?
6. **Evidence:** which document, setting, test, or contractual term supports the answer? Mark unknowns explicitly.

**Illustrative failure:** the chat interface enforces user permissions, but the retrieval index was built with an administrator account and returns documents the user cannot otherwise access. An interface-level permission check does not prove end-to-end authorization. Test both ingestion and retrieval boundaries, including what happens after access is revoked.

### 3.2 Discover unregistered AI without overstating coverage

Recommended discovery sources include procurement records, software renewals, approved application inventories, vendor release notes, browser-extension inventories, sanctioned network/security telemetry, service-account and connector reviews, and staff attestations. Use only lawful, authorized monitoring consistent with organizational policy.

Reconcile discoveries against the use-case inventory. Treat “AI feature discovered but not assessed” as a separate state from “approved” or “prohibited.” Report the populations actually reviewed; an inventory cannot demonstrate that undiscovered use does not exist.

## 4. Risk tiering and review depth

The following is a **proposed local model**, not an HSCC or NIST classification. Use the highest credible impact and escalate when scope is uncertain. A clinical or regulated function may require a specialized pathway regardless of its initial tier.

| Proposed tier | Illustrative use | Recommended review |
| --- | --- | --- |
| Lower | Drafting public, nonsensitive text without integrations or consequential decisions. | Approved tool; acceptable-use training; basic supplier/data review; human verification. |
| Moderate | Internal workflow support using confidential information, with bounded access and reviewable outputs. | Business, security, privacy, and vendor review; local testing; documented operating limits. |
| High | PHI processing, patient-facing interaction, clinical documentation, influential decision support, or broad system integration. | Cross-functional review; clinical review where relevant; stronger validation; contract review; tested containment and fallback; explicit approval. |
| Critical / restricted pending special review | Autonomous consequential actions, changes to clinical records or care workflows, high-impact recommendations without reliable oversight, or poorly bounded privileged agents. | Do not deploy through routine approval. Require specialized evaluation, explicit delegated authority, and demonstrably effective controls; reject if risk cannot be bounded. |

**Escalation factors:** sensitive data; vulnerable populations; clinical consequences; irreversible or difficult-to-detect errors; high transaction volume; broad permissions; opaque dependencies; weak evidence; model volatility; and inability to stop, recover, or operate manually. A “no PHI” claim does not by itself make a use case low risk.

### 4.1 Write a risk scenario before assigning a tier

A useful scenario is: **Because of [condition or threat], the AI may [failure or action], affecting [people/data/workflow], resulting in [harm]. Existing controls are [controls], evidence is [evidence], and uncertainty remains [gap].**

**Illustrative dental-documentation scenario:** because a transcription system can confuse speaker identity or omit negation in noisy audio, it may produce an inaccurate allergy or medication statement that enters a patient record. The potential harm is not simply “inaccurate AI”; it is subsequent reliance on an incorrect clinical fact. Candidate controls include source comparison, explicit clinician verification of high-consequence fields, a controlled sign-off workflow, and testing with representative audio. These controls must be demonstrated, not presumed effective because a reviewer exists.

Evaluate each scenario across:

- **Impact:** clinical/patient harm; privacy; confidentiality/integrity/availability; financial loss; operational disruption; and legal or contractual exposure.
- **Likelihood and exposure:** frequency of use, number of affected people, triggering conditions, threat access, and opportunities for an error to propagate.
- **Detectability and reversibility:** whether a competent reviewer can notice the failure before harm, whether actions can be undone, and whether correction reaches downstream recipients.
- **Control effectiveness:** design, actual implementation, observed operation, and bypass opportunities.
- **Uncertainty:** incomplete supplier information, limited local samples, changing models, or inadequate visibility into failures.

Record **inherent risk**, **controls and evidence**, and **residual risk** separately. Do not reduce a tier simply because a policy has been written. A critical impact can remain important even if its observed frequency is low, and an absence of observed incidents may reflect poor detection.

### 4.2 Use mandatory escalation triggers alongside judgment

Recommended escalation triggers include an inability to isolate PHI from unapproved processing; no effective way to halt consequential actions; unresolved cross-tenant access; unsupported clinical use; and a supplier change that invalidates a material approval assumption. Uncertainty about these issues should result in a hold or restricted scope while it is resolved—not a favorable score by default.

Avoid averaging away a severe clinical or privacy scenario with several low-risk attributes. If numerical scoring is later adopted, define each scale, preserve the underlying scenarios, explain uncertainty, and set escalation rules independent of the total score. This page does not prescribe a quantitative risk formula.

## 5. Lifecycle gates and required evidence

| Gate | Decision to make | Recommended minimum evidence | Hold / stop condition |
| --- | --- | --- | --- |
| 1. Intake and justification | Is the purpose appropriate, valuable, and within scope? | Owner, workflow, intended users, expected benefit, alternatives, initial data map and tier. | No accountable owner or unclear intended use. |
| 2. Vendor and dependency diligence | Can the supplier and architecture support the intended use? | Data flows, dependencies, AI-specific evidence, security/privacy review, limitations and findings. | Material unknowns about sensitive-data handling, access, or critical dependencies. |
| 3. Contract and design | Are use, responsibilities, safeguards, and exit terms defined? | Applicable BAA decision, contract review, approved architecture, access design, change and incident obligations. | Unacceptable reuse rights, unbounded access, or unresolved contractual risk. |
| 4. Controlled pilot | Does the system work safely in the local workflow? | Approved test plan, representative cases, predefined criteria, human-review procedure, incident/fallback test. | Critical test failure or inability to detect/contain unsafe operation. |
| 5. Production release | Is remaining risk acceptable to the authorized approver? | Results, closed findings or approved exceptions, training, monitoring, runbook, recorded sign-off. | No decision record, no operating owner, or unresolved release-blocking findings. |
| 6. Ongoing operation and change | Does approval remain valid? | Metrics, incidents, supplier changes, access reviews, evaluation results, reassessment decision. | Material unreviewed change or breach of an approved operating limit. |
| 7. Retirement | Can the service be safely removed? | Replacement/fallback plan, revoked credentials, disconnected integrations, data export/deletion evidence. | Orphaned access, unresolved retention, or unsafe workflow disruption. |

Use the gates as decision points, not paperwork milestones. A pilot approval does not authorize unrestricted production or real patient data. The lifecycle structure is informed by the HSCC third-party guide; these specific release artifacts and stop conditions are recommended local controls.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)

## 6. Vendor diligence: questions and evidence that matter

| Ask the supplier | Request evidence | Why it matters |
| --- | --- | --- |
| What happens to prompts, files, outputs, logs, embeddings, and backups? | Product-specific data-flow and retention documentation, configuration options, and contract terms. | “We do not train on your data” does not answer storage, human access, logging, or deletion questions. |
| Which model providers, subprocessors, hosting services, and tools participate? | Dependency map, current subprocessor list, responsibilities, and notification process. | Risk can change downstream even when the primary vendor stays the same. |
| What data is used for training, improvement, evaluation, or human review? | Binding terms and product/tenant-specific controls; scope of any opt-out. | Marketing statements may not cover the purchased service or configuration. |
| How are tenants, identities, secrets, and connectors protected? | Architecture, access-control design, assurance reports with scope, relevant test summaries, and remediation status. | General certification is useful evidence but may not cover the AI feature, model risks, or connector permissions. |
| How is the AI evaluated for the intended workflow? | Test methods, relevant performance evidence, known failure modes, limitations, and update/rollback process. | Broad benchmark scores do not establish local clinical or operational suitability. |
| How are attacks and unsafe actions addressed? | Relevant prompt-injection, data-exfiltration, tool-abuse, and access-control test evidence; logging and containment capabilities. | AI can expand the attack surface beyond a conventional application boundary. |
| What changes will the customer be told about? | Terms for material model, feature, data-use, subprocessor, hosting, or autonomy changes. | Silent changes can invalidate prior testing and approval. |
| What happens during an incident or service exit? | Notification commitments, response cooperation, evidence preservation, recovery, export, and deletion procedures. | Containment and continuity require coordination across the supply chain. |

**Evidence discipline:** record the product, service boundary, evidence date, coverage period, reviewer, finding, and limitation. If a supplier cannot disclose a dependency or assessment detail, document the gap and decide whether compensating measures are sufficient; do not infer a favorable answer. AI-specific diligence should supplement existing supplier security and supply-chain risk practices.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)[[6]](https://csrc.nist.gov/pubs/sp/800/161/r1/final)

### 6.1 Judge evidence quality, not questionnaire completion

| Evidence state | Interpretation | Appropriate follow-up |
| --- | --- | --- |
| Supplier assertion only | A claim has been made, but implementation and scope are not established. | Request product-specific supporting evidence and identify the unverified assumption. |
| Documented design | The supplier describes how a safeguard should work. | Confirm it applies to the purchased service, customer settings, and actual data path. |
| Implementation evidence | Configuration, contractual terms, or other artifacts support that the safeguard exists. | Evaluate whether it is enabled and whether dependencies or exceptions undermine it. |
| Operating / assessment evidence | Testing or other review supports operation for a stated scope and period. | Inspect methods, independence where relevant, limitations, findings, and relevance to the local use. |
| Local validation | The organization has tested relevant behavior in its configured workflow. | Retain reproducible results and assess whether coverage is sufficient for the consequences of failure. |

These states are not a mandatory linear certification scheme. Different questions need different evidence: a technical test cannot establish a contractual right, and a contractual promise cannot demonstrate runtime isolation. Evidence can also become stale after a material change.

### 6.2 Translate diligence into enforceable operating conditions

For each material finding, connect **claim → evidence → limitation → control or contract commitment → validation → decision**.

**Illustrative example:** the vendor says customer data is not used for model training. Review whether that statement covers the exact service, all participating model providers, support access, evaluation, and future changes. Confirm the governing terms and relevant settings. Separately assess retention and disclosure; “no training” is not equivalent to “no storage” or “no external processing.” If the claim cannot be verified sufficiently, narrow the permitted data or defer the use rather than recording the issue as resolved.

Recommended contracting review should also address the practicality of promised safeguards. For example: does notification arrive early enough to evaluate a model change; can the customer defer the change; is rollback available; and what happens if the supplier cannot support either? Where a vendor cannot pin versions, approval should acknowledge that limitation and define proportionate regression tests, monitoring, and suspension triggers. The aim is a usable operating agreement, not a clause that nobody can execute.

## 7. Privacy, HIPAA, and contracting guardrails

**Determine the relationship, not just the label.** HHS explains that business-associate status depends on the service performed and the handling of PHI on behalf of a covered entity or another business associate. Its guidance includes a third-party AI chatbot used through a patient portal as an example. Have qualified reviewers evaluate the actual arrangement and whether a BAA is required.[[7]](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html)

**A BAA is not the whole assessment.** Where required, the agreement is one part of the relationship. It does not establish that the particular AI configuration is safe, appropriate, secure, or suitable for its intended workflow. Keep the data-flow review, risk assessment, technical diligence, permitted-use decision, and local validation separate.

Recommended contract-review topics include:

- Defined service, approved purpose, data categories, and responsibilities across the supplier chain.
- Permitted and prohibited training, reuse, disclosure, and human access; retention and deletion commitments.
- Relevant security controls, assurance evidence, incident cooperation, and notification commitments reviewed against applicable law.
- Material-change notification, evaluation opportunities, and remedies if changes create unacceptable risk.
- Data portability, termination assistance, access revocation, and deletion/retention evidence, including disclosed exceptions.
- Patient transparency, consent or authorization, records handling, and other legal questions where applicable to the actual use.

**Rulemaking caution:** the HHS HIPAA Security Rule NPRM page consulted for this reference states that the current Security Rule remains in effect while rulemaking proceeds. A proposed requirement should not be presented as an effective requirement merely because it appears in an NPRM. Recheck current authoritative sources before a compliance decision.[[8]](https://www.hhs.gov/hipaa/for-professionals/security/hipaa-security-rule-nprm/index.html)

### 7.1 Complete a use-specific privacy review

Recommended review questions include:

- **Purpose and authority:** why is each data element needed, and what authorizes its use or disclosure for this workflow? Do not treat a broad commercial contract as the answer to every privacy question.
- **Data minimization:** can the task be completed with less detail, narrower retrieval, shorter retention, synthetic data, or another approved approach? Removing obvious identifiers alone should not be treated as a formal de-identification determination.
- **Secondary use:** are prompts, transcripts, images, outputs, and derived data used for supplier improvement, human evaluation, analytics, or purposes unrelated to the approved service?
- **Patient and workforce expectations:** is recording involved; what transparency or consent/authorization analysis is needed; and what happens if a person declines where a choice is offered or required?
- **Rights and records handling:** which outputs become part of an official record, and how are access, correction, retention, legal hold, and downstream reconciliation managed where applicable?
- **Cross-border and subcontracted processing:** what locations and entities participate, and what additional review does that require?

**Important distinctions:** notification that AI is being used, consent to recording, HIPAA authorization, and a business-associate agreement answer different questions. Do not use one as a substitute for another. Whether a particular requirement applies must be determined from the facts and applicable law by qualified reviewers; this section is a review agenda, not a legal conclusion.

### 7.2 Make transparency operational

Where appropriate to the use and legal review, explain what the AI does, its material limitations, the role of human review, and how a patient or staff member can seek correction or assistance. Avoid language implying independent clinical judgment when the system only drafts or supports a clinician.

For a patient-facing chatbot, consider a clear distinction between administrative information and clinical questions; an accessible route to a person; explicit handling of unsupported questions; and an organization-approved escalation workflow for urgent or safety-related statements. Test the routing and fallback rather than relying on a disclaimer alone. Do not invent clinical triage rules in a technology deployment; have the appropriate clinical authority define them.

## 8. Validation, clinical safety, and human oversight

Define success and failure criteria **before** testing. Evaluate the configured system in the intended workflow, using representative cases and authorized test data. Separate supplier performance claims from local evidence.

Recommended evaluation domains:

1. **Utility and accuracy:** task completion, factual correctness, omissions, unsupported claims, and source traceability where relevant.
2. **Clinical and patient impact:** clinically significant errors, misleading advice, inappropriate escalation, and the consequences of incorrect documentation or recommendations. Qualified clinicians should define relevant criteria.
3. **Privacy and security:** inappropriate disclosure, retrieval across access boundaries, prompt injection, sensitive-data extraction, and unauthorized actions.
4. **Human factors:** whether reviewers can recognize errors, understand limitations, override outputs, and avoid overreliance under realistic workload.
5. **Reliability and resilience:** downtime, degraded output, latency, model/service changes, rollback, and manual fallback.
6. **Relevant population and workflow variation:** performance across the contexts and groups the deployment will actually serve; document coverage gaps rather than claiming universal validity.

**Release evidence:** test plan; system/model/configuration identifiers where available; data provenance and permissions; scenarios; results; failure severity; reviewer; limitations; required mitigations; and explicit acceptance decision. No universal accuracy threshold is recommended here—criteria should reflect the task and consequences of error.

Generative-AI risks warrant evaluation beyond conventional security assurance. NIST’s GenAI Profile complements the AI RMF with generative-AI-specific risk considerations; neither removes the need for local validation and accountable release decisions.[[4]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)[[3]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)

### 8.1 Build an evaluation plan that can support a decision

A recommended test record contains: **test ID; risk scenario; input and expected behavior; system/configuration; data permissions; reviewer; observed output/action; severity; result; defect link; and retest outcome**. Preserve enough detail to reproduce the issue without exposing unnecessary sensitive information.

| Test family | Example question | Evidence to retain |
| --- | --- | --- |
| Ordinary workflow | Does the configured system perform the intended task on representative cases? | Reviewed cases, scoring criteria, observed results, and comparison with the defined baseline. |
| Boundary and ambiguity | What happens with incomplete records, ambiguous phrasing, conflicting sources, or an unsupported request? | Whether uncertainty is surfaced and whether the system defers or escalates appropriately. |
| High-consequence error | Can a wrong patient, omitted negation, incorrect date, or unsupported clinical fact pass into an official record? | Error examples, detection before release, and evidence that the blocking/review control worked. |
| Authorization | Can one role retrieve or modify data outside its approved scope? | Role/identity used, expected denial, observed response, and downstream access results. |
| Adversarial content | Can a malicious document or message induce disclosure, policy bypass, or an unauthorized tool call? | Attack scenario, boundary tested, attempted action, and enforcement outcome. |
| Degraded operation | What happens during model timeout, connector failure, incomplete retrieval, or interrupted execution? | Whether the workflow fails safely, avoids duplicate actions, and enables recovery. |
| Human review | Do trained reviewers identify important errors under realistic workload? | Detection, correction, rejection, escalation, and review-effort observations. |
| Change regression | Does a candidate update preserve approved behavior and safeguards? | Baseline comparison, new failures, review decision, and rollback/fallback result. |

### 8.2 Define measures without hiding serious failures

Choose measures appropriate to the task: factual correctness; unsupported-claim rate; clinically significant omission rate; source-support accuracy; inappropriate disclosure; unauthorized-action attempts and successful actions; escalation quality; and completion/review time. Clearly define each denominator and distinguish system output quality from final human-corrected quality.

Do not combine all failures into one accuracy percentage. A punctuation error and an incorrect medication statement should not carry the same clinical significance. Report severity and failure type, including examples, alongside any aggregate measure. If the workflow claims to save time, account for verification, corrections, exception handling, and downstream rework—not generation speed alone.

**Coverage limitations matter:** state how cases were selected, what environments and populations are represented, what was excluded, and what remains unknown. Small or convenience samples support limited conclusions. Zero observed failures does not establish zero risk. Have qualified clinical and evaluation personnel determine appropriate sample design and statistical interpretation where the decision warrants it.

### 8.3 Separate the pilot into controlled stages

1. **Offline evaluation:** authorized test data; no production actions; define the initial failure set.
2. **Shadow operation:** where appropriate and approved, compare outputs with the existing workflow without allowing them to drive consequential action.
3. **Supervised limited use:** restricted users, data, sites, or volume; active review and rapid suspension capability.
4. **Production release:** only after the evidence supports the intended scope and the authorized decision is recorded.

These stages are proposed rollout patterns, not permission to introduce real patient data without review. Expand scope only when evidence justifies it. A successful single-site pilot does not automatically establish suitability across different practices, recording conditions, specialties, languages, or integrations.

## 9. Additional controls for generative and agentic AI

An assistant that suggests text and an agent that can act on systems are different risk propositions. For any tool-using system, document **what it can read, what it can change, whose authority it uses, and how it can be stopped**.

| Control area | Recommended operating requirement |
| --- | --- |
| Identity and permissions | Use attributable, narrowly scoped service identities where supported; avoid shared administrator credentials; review connector scopes and effective downstream access. |
| Trust boundaries | Treat retrieved pages, documents, messages, and tool outputs as untrusted inputs, not authority to change instructions or permissions. |
| Tool execution | Allowlist necessary tools and destinations; validate action parameters; restrict arbitrary code/network access according to risk. |
| Consequential actions | Require meaningful human approval for defined high-impact actions; display target, data, change, and consequence before execution. |
| Secrets and sensitive data | Keep secrets out of prompts and ordinary logs; minimize sensitive context; apply appropriate data-loss and access controls. |
| Auditability | Record tool calls, approvals, relevant configuration/version, and outcomes with access restrictions and retention appropriate to the data. |
| Containment | Provide a tested way to disable the AI feature, revoke tokens, disconnect tools, and halt queued or repeating actions. |
| Adversarial testing | Test indirect prompt injection, unauthorized retrieval, excessive permissions, unsafe action chains, and failure of approval boundaries. |

“Human in the loop” is not an adequate control description by itself. State **who** reviews, **what** they inspect, **when** approval is required, **how** rejection works, and **what** happens when review is unavailable. These are recommended implementations of the generative/agentic governance and security themes in the HSCC and NIST guidance.[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)[[4]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

### 9.1 Engineer approvals outside the model’s discretion

A prompt saying “ask permission first” is not equivalent to an enforced approval boundary. For consequential tool use, the application or execution layer should verify authorization independently of the model’s generated text.

A recommended approval transaction binds the reviewer’s decision to **the specific action, target record or recipient, parameters, data, and permitted execution window**. Material changes after approval should require a new approval. A generic “continue” click should not authorize additional unreviewed actions or a different patient record.

Consider enforcement of:

- **Read versus write separation:** a system that can search for information should not inherit update or deletion authority merely because a connector supports it.
- **Action and volume limits:** constrain bulk updates, repeated messages, financial amounts, or other consequential activity according to the use case.
- **Replay and duplicate protection:** detect retried actions and partial execution so a timeout does not create duplicate messages, notes, or transactions.
- **Scoped execution:** where supported, use short-lived, purpose-limited access and verify the intended tenant, patient, record, and destination.
- **Fail-closed behavior:** if the approval service, identity check, or logging required for safe execution is unavailable, hold the action or enter a documented safe alternative rather than silently proceeding.
- **Revocation:** confirm that disabling a feature also addresses running jobs, queued actions, active tokens, scheduled tasks, and downstream workflows.

### 9.2 Distinguish retrieval quality from retrieval authorization

A retrieval-augmented system can produce a well-cited answer from information the user was never authorized to see. Test permission filtering, document ingestion, index isolation, stale access after role changes, and deletion propagation separately from answer relevance.

Likewise, a citation is not proof that the source supports the claim. Check whether the retrieved source actually contains the stated information, is current and appropriate for the purpose, and was not maliciously crafted to manipulate tool use. Limit source content to its role as evidence or task data; it should not gain authority to expand permissions or replace approved operating rules.

These engineering patterns are recommended ways to implement the broader trust-boundary and oversight objectives described in the GenAI and cyber governance resources; their effectiveness must be tested in the actual product.[[1]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)

## 10. Monitoring and material-change review

**Suggested starting cadence—not a framework mandate:** monitor operational alerts as the use case requires; have owners review high-risk deployments at least quarterly and lower-risk deployments at least annually, with more frequent review where impact or volatility warrants. Time-based review never replaces event-driven reassessment.

Trigger reassessment when there is:

- A new model/provider, material model update, new AI feature, or significant performance change.
- A change in data categories, training/reuse terms, retention, hosting, or subprocessors.
- A new connector, broader permissions, additional tools, or greater autonomy.
- A new clinical, patient-facing, or otherwise consequential purpose or population.
- A security/privacy incident, harmful output, credible vulnerability, or repeated near miss.
- An expired exception, overdue remediation, or changed legal/contractual requirement.

| Leadership measure | Recommended definition |
| --- | --- |
| Inventory and ownership coverage | Share of discovered in-scope use cases with complete records and accountable owners; separately report discovery limitations. |
| Approval coverage | Active production use cases with current documented approval ÷ active production use cases. |
| High-risk evidence coverage | High-risk deployments with current required validation and fallback evidence ÷ active high-risk deployments. |
| Review / remediation debt | Overdue reviews, expired exceptions, and unresolved findings, separated by severity and age. |
| Material changes assessed | Known material changes assessed before release; also report changes discovered after release. |
| Safety, privacy, and security signals | Incidents, near misses, unsupported outputs, overrides, and policy violations, with volume/exposure context. |
| Demonstrated value | Measured benefit against a baseline, alongside quality and risk outcomes—not adoption or usage alone. |

Avoid a single “AI compliance score.” Report evidence gaps, residual risk, and operating performance separately. Ongoing monitoring and reassessment are central to lifecycle governance.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)

### 10.1 Establish an approved configuration baseline

Record the elements that materially affect behavior: feature and model identifier where exposed; system instructions and prompt templates; retrieval sources/index configuration; safety and data-use settings; connector scopes; permitted tools; approval rules; and the evaluation set used for release. Do not store secrets in this record.

An AI change can occur without a traditional software release. Prompt edits, new documents in a retrieval source, broader connector access, supplier routing changes, and a different default model may all affect the approved behavior. Classify changes by their actual impact rather than the vendor’s label of “minor update.”

**Recommended change-review sequence:** identify changed assumptions → determine affected risk scenarios → select regression tests → review supplier/local evidence → decide whether a controlled pilot is needed → authorize or hold → monitor after release. If version pinning or rollback is unavailable, document that constraint and define an alternative safe state, such as disabling the feature or returning to the manual workflow.

### 10.2 Distinguish drift, incidents, and workflow change

- **Performance drift:** outputs become less suitable over time, potentially because inputs, populations, or underlying models changed.
- **Workflow drift:** users begin applying an approved tool to a different task, relying on it more heavily, or skipping required review.
- **Permission drift:** connectors, service identities, or tool access gradually expand beyond the approved boundary.
- **Control failure:** a safeguard does not operate as designed, even if no harm has yet been confirmed.

Recommended response thresholds should state an **observable condition, owner, immediate action, escalation path, and restart criterion**. For example: confirmed unauthorized cross-patient retrieval prompts suspension of the affected retrieval path, security/privacy triage, scope investigation, and revalidation before restart. This is a proposed operating response, not an automatic legal breach determination.

Do not monitor sensitive prompts or outputs indiscriminately. Define the minimum telemetry needed, who may access it, its retention, and how protected data is handled. Monitoring itself introduces data and access risks.

## 11. Incident response, fallback, and retirement

Integrate AI events with existing security, privacy, clinical-safety, and business-continuity processes. An AI incident may involve harmful recommendations, incorrect records, disclosure through an output, unauthorized tool execution, compromised dependencies, or silent deterioration—not only a conventional data breach.

**Recommended response sequence:**

1. **Triage and protect:** assess patient, operational, privacy, and security impact; escalate through the relevant established response paths.
2. **Contain:** disable the affected feature or action path; revoke credentials or connectors; stop automation and queued actions as needed.
3. **Preserve:** retain relevant logs, outputs, approvals, timestamps, configuration/version information, and supplier notices under appropriate access and evidence-handling controls.
4. **Scope:** identify affected data, records, patients/users, workflows, time window, integrations, and downstream actions; distinguish confirmed effects from unknowns.
5. **Coordinate:** involve the vendor and relevant internal leads; let qualified teams determine notification and reporting obligations rather than assuming every AI error is a reportable breach.
6. **Operate safely:** use the tested manual or alternate workflow and reconcile any incomplete or incorrect actions.
7. **Recover deliberately:** retest, close release-blocking issues, document residual risk, and obtain reauthorization before restoration.
8. **Learn:** update evaluation cases, permissions, training, supplier findings, and governance decisions.

**Retirement checklist:** communicate the replacement workflow; export necessary records; revoke identities and tokens; remove connectors, scheduled jobs, and retrieval indexes as appropriate; address prompts, outputs, embeddings, caches, logs, and backups according to applicable retention and contractual obligations; obtain available deletion evidence; record remaining dependencies and exceptions. Do not promise immediate deletion where legal retention or backup limitations apply. Incident coordination, resilience, and safe end-of-life should be planned throughout the lifecycle.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)

### 11.1 Prepare an AI-specific incident evidence packet

Where available and appropriate, preserve the use-case ID; affected feature; discovery time and relevant event timestamps/time zones; model/configuration identifiers; user/service identities; data and retrieval sources involved; prompts/outputs necessary to understand the event; tool parameters and results; approval records; known affected recipients or records; supplier communications; and containment actions. Separate confirmed facts, working hypotheses, and unknowns.

Do not indiscriminately copy patient records into ordinary tickets or broad chat channels. Use the established evidence-handling process and restrict access. Preserve original records and audit trails while qualified personnel determine the appropriate correction and reconciliation process.

### 11.2 Tabletop exercise: unreviewed model update in a documentation tool

**Illustrative scenario—not an actual incident:** a supplier changes the model behind an ambient documentation feature. Staff report omitted negations and misattributed statements. Some drafts may have been signed into records.

| Exercise stage | Questions for the team | Expected decision artifact |
| --- | --- | --- |
| Detection and triage | Who receives staff reports? Can the team identify when behavior changed and which sites/configurations were exposed? | Initial event record, accountable lead, and uncertainty statement. |
| Immediate protection | Who can pause the feature? Can clinicians continue documentation without it? Are queued drafts or automated exports still active? | Containment log and activated fallback workflow. |
| Scope and clinical review | Which drafts and signed records need review? How will clinical significance be assessed without assuming every note is wrong? | Risk-based review plan led by appropriate clinical authority. |
| Supplier coordination | What changed, when, and for whom? Is the previous configuration recoverable? What evidence will the supplier preserve? | Supplier escalation and change/evidence record. |
| Correction and communication | Who determines necessary record correction, patient communication, privacy analysis, or other reporting? | Authorized decisions with rationale and assigned actions. |
| Restoration | Which regression tests and workflow checks must pass, and who can authorize restart? | Retest results, residual-risk decision, and restart approval. |

**Exercise completion means demonstrated capability:** record time to locate the right owner, disable the feature, revoke access where needed, activate fallback, and reconcile unfinished work. A runbook that cannot be executed by the available team is a finding, even if the written process is complete.

## 12. Reusable decision record

Copy this structure into the appropriate use-case or vendor record; it is a template, not evidence that a review has occurred.

| Decision field | Record |
| --- | --- |
| Use-case ID / name | [Enter identifier and specific workflow] |
| Product, AI feature, and configuration | [Enter service, model/version where available, environment, and relevant settings] |
| Owner and reviewers | [Name accountable owner and applicable clinical, security, privacy, legal, and operational reviewers] |
| Intended use and prohibited use | [Define approved purpose and clear boundaries] |
| Data and dependencies | [Link data flows, sensitive-data categories, vendor record, and dependency map] |
| Proposed tier and rationale | [Explain impact, likelihood considerations, uncertainty, and autonomy] |
| Evidence reviewed | [Link source, scope, date, test results, and known gaps] |
| Decision | [Reject / defer / limited pilot / approve with conditions / approve / suspend / retire] |
| Conditions and residual risk | [List mitigations, limitations, risk owner, and authorized acceptance] |
| Operational controls | [Human review, access limits, monitoring, incident contact, stop mechanism, and fallback] |
| Change and review triggers | [List triggers, review date, and approval expiry if applicable] |
| Authorization | [Approver, delegated authority, decision date, and record of sign-off] |

**Example decision wording:** “Approved for a limited pilot in [workflow], using [permitted data] and [configuration], until [review date]. Outputs require [defined review]. [Specified actions/data uses] remain prohibited. Production release requires [evidence and approver].”

## 13. Recommended first 90 days

| Period | Priority work | Useful completion evidence |
| --- | --- | --- |
| Days 1–30: establish visibility | Designate sponsor and review authority; discover AI features and shadow use; identify PHI, clinical, patient-facing, and agentic deployments; publish interim boundaries; link use cases to vendor records. | Initial inventory, ownership list, documented triage criteria, and urgent risk decisions. |
| Days 31–60: evaluate priority exposure | Review highest-impact deployments; fill data-flow and dependency gaps; evaluate contracts; test local performance, containment, and fallback; train owners and reviewers. | Prioritized assessments, decision records, test results, and remediation owners. |
| Days 61–90: make governance repeatable | Formalize intake and release gates; implement change review, monitoring, exception handling, and incident exercises; establish leadership reporting. | Approved operating process, review calendar, tracked exceptions, exercise results, and initial dashboard definitions. |

Prioritize existing exposure over creating a large committee or an elaborate scoring tool. This roadmap is a proposed implementation sequence, not an externally mandated timeline.

## 14. Common mistakes to avoid

- **“The vendor signed a BAA, so the AI is approved.”** Determine the relationship and complete the separate risk, technical, workflow, and release reviews.
- **“The vendor is certified, so the AI feature is safe.”** Verify assessment scope and obtain AI-specific and local evidence.
- **“We approved the platform last year.”** Reassess new features, data uses, dependencies, permissions, and material model changes.
- **“It only drafts, so it cannot cause harm.”** Drafts can disclose information, omit clinical facts, or be accepted without adequate review.
- **“A human checks everything.”** Test whether the review is specific, feasible, informed, and able to stop the action.
- **“No PHI means no material risk.”** Security, financial, clinical, operational, and reputational harms can still exist.
- **“An inventory is the governance program.”** Inventory enables governance; it does not replace decisions, controls, evaluation, or monitoring.
- **“The framework proves compliance.”** Keep legal applicability, implementation, effectiveness, and residual-risk decisions distinct.

## 15. Healthcare and dental use-case playbooks

The examples below are illustrative assessment patterns—not approved deployments, clinical instructions, or claims about any specific vendor. Apply the actual workflow, legal review, patient population, product capabilities, and delegated authority.

### 15.1 Ambient transcription and clinical-note drafting

**Value hypothesis:** reduce documentation effort while preserving or improving record quality. Compare with a defined baseline and include review/correction time.

**Key exposure:** audio and transcripts may contain sensitive information about several people; a fluent note can introduce unsupported facts, omit negation, confuse speakers, or place information into the wrong encounter.

**Recommended boundaries and tests:**

- Review recording, privacy, permitted data use, retention, and relevant agreements before collection.
- Confirm patient/encounter binding and whether the tool produces a draft or can write/sign into the record.
- Have clinical reviewers identify fields requiring explicit verification and test noisy audio, interruptions, speaker changes, incomplete statements, and relevant language variation.
- Keep drafting distinct from clinician authentication or sign-off; do not let polished prose imply verified accuracy.
- Test downtime, interrupted recording, duplicate export, and reconciliation of an unsigned or partially transferred draft.

**Release packet:** approved workflow; data map; relevant contractual/privacy decisions; representative test results; clinical review instructions; fallback; owner; and configuration-specific release decision.

### 15.2 Patient-facing scheduling or information chatbot

**Value hypothesis:** improve access to routine administrative assistance without misrepresenting clinical capability.

**Key exposure:** a patient may disclose clinical information even when the intended task is scheduling. Conversation history, appointment details, and identity verification can introduce sensitive-data risk. An apparently administrative exchange can become clinically consequential.

**Recommended boundaries and tests:** distinguish public information from authenticated patient functions; limit record retrieval to the permitted task; define clinical-question and urgent-message routing with qualified leadership; provide a workable human handoff; test misleading requests, wrong-patient access, unsupported clinical questions, connector failure, and after-hours behavior. A disclaimer does not compensate for a broken handoff.

**Release packet:** approved content sources; authentication/access tests; defined routing and fallback; privacy and business-associate analysis as applicable; transcript retention decision; monitored launch plan; and accountable operating owner.

### 15.3 Imaging or clinical decision support

**Value hypothesis:** support a specifically defined clinical task—not a broad assertion that the AI “improves diagnosis.”

**Key exposure:** false negatives, false positives, inappropriate generalization to different equipment or patient populations, and overreliance on an output outside its intended use.

**Recommended review:** qualified clinical and legal/regulatory personnel should determine the relevant intended use and whether product-specific regulatory requirements or authorizations apply. Do not assume that all AI software is a regulated medical device, or that a vendor’s regulatory status establishes suitability for every workflow.

Evaluate the product’s documented intended use, supporting evidence, contraindications/limitations where relevant, local equipment and image quality, reader workflow, escalation, and the effect of updates. Maintain clinician accountability and an appropriate alternative when the service is unavailable. Do not extend approval to unsupported uses based on vendor demonstrations alone.

### 15.4 Revenue-cycle or administrative agent

**Value hypothesis:** reduce manual work in a bounded process while preserving transaction accuracy and auditability.

**Key exposure:** a tool-using agent can access patient or financial data, send information to the wrong destination, duplicate transactions, alter records, or make unsupported assertions in documentation.

**Recommended boundaries and tests:** separate draft/preparation tasks from submission; independently authorize consequential changes; restrict destinations and transaction types; test patient/account matching, duplicate prevention, partial completion, retries, and rollback/reconciliation. Appropriate reviewers should assess billing accuracy and legal/compliance implications. Do not let automation create unsupported clinical or financial representations.

**Release packet:** permitted actions and data; identity/permissions; approval enforcement tests; transaction audit trail; duplicate-handling and recovery results; fraud/error monitoring responsibilities; and clear suspension authority.

## 16. Connect governance to evidence and existing frameworks

### 16.1 Use NIST AI RMF as an organizing layer

NIST AI RMF 1.0 uses the functions GOVERN, MAP, MEASURE, and MANAGE. The following is a practical organizing interpretation—not an official one-to-one mapping or a claim that the listed artifacts satisfy every framework outcome.[[3]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)

| Function | Governance question | Example local artifacts |
| --- | --- | --- |
| GOVERN | Who is accountable, what boundaries apply, and how are decisions sustained? | Charter, delegated authorities, policies, role training, exception process, reporting, and decision log. |
| MAP | What is the system doing, in which context, for whom, and with what potential effects? | Use-case scope, data/authority map, dependency inventory, affected stakeholders, intended-use limits, and risk scenarios. |
| MEASURE | What evidence describes performance, failures, safeguards, and uncertainty? | Evaluation plan, local test results, clinical review, security testing, monitoring definitions, and documented limitations. |
| MANAGE | What will be prioritized, treated, accepted, restricted, monitored, or stopped? | Remediation, release conditions, authorized residual-risk decisions, change controls, incident/fallback plans, and retirement actions. |

The functions should support an ongoing process rather than a one-time paperwork sequence. Use CSF 2.0 to connect AI-related cybersecurity outcomes to the enterprise security program and SP 800-161 to strengthen supplier/dependency practices; neither replaces the broader AI risk review.[[4]](https://www.nist.gov/cyberframework)[[5]](https://csrc.nist.gov/pubs/sp/800/161/r1/final)

### 16.2 Build a small, testable control library

The identifiers below are **suggested local labels**, not NIST or HSCC control IDs. Adopt only after tailoring and approval.

| Local label | Control objective | Example implementation evidence | Example effectiveness test |
| --- | --- | --- | --- |
| AI-GOV-01 | Every active use case has an accountable owner and defined scope. | Inventory, ownership acceptance, and decision record. | Sample deployments and reconcile observed use to approved scope. |
| AI-DATA-01 | Data processing follows the approved purpose and boundary. | Data map, terms, retention settings, and connector configuration. | Trace representative inputs/outputs and inspect permitted data paths. |
| AI-ACCESS-01 | Retrieval and action permissions do not exceed approved authority. | Identity inventory, role design, token scopes, and access reviews. | Attempt prohibited retrieval/actions and verify denial at enforcement points. |
| AI-VALID-01 | Local evaluation supports the intended use and states limitations. | Test plan, reviewed results, release criteria, and clinical input where relevant. | Reproduce selected tests and verify closure of release-blocking defects. |
| AI-HUMAN-01 | Required human approval is specific, meaningful, and enforced. | Workflow design, reviewer training, and approval records. | Attempt bypass, changed parameters, unavailable reviewer, and approval replay. |
| AI-CHANGE-01 | Material changes are assessed before continued authorized use. | Baseline, supplier notices, change records, and regression results. | Trace a material change from detection to release or suspension decision. |
| AI-RESP-01 | The deployment can be contained and operated without safely. | Stop procedure, token revocation process, fallback and reconciliation plan. | Exercise shutdown, queued-action handling, fallback, and authorized restart. |
| AI-EXIT-01 | Retirement removes access and addresses data disposition. | Decommission checklist, revoked access, export/deletion evidence, and retained exceptions. | Verify removed connections and follow unresolved retention/dependency items. |

A policy or diagram generally demonstrates design, not necessarily operation. Retain the actual results, exceptions, and follow-up from each test. Coordinate these controls with existing security/privacy requirements rather than creating parallel evidence for the same implementation.

## 17. Workforce readiness, assurance, and leadership decisions

### 17.1 Train people for their actual responsibilities

| Audience | Practical competency | Suggested demonstration |
| --- | --- | --- |
| General workforce | Recognize approved tools, permitted data, unsafe requests, and reporting channels. | Route a realistic use request and identify a prohibited disclosure. |
| Clinical users | Understand intended use and limitations, verify consequential facts, reject unsafe output, and use fallback. | Review a seeded-error example and execute the escalation workflow. |
| Owners and managers | Maintain scope, recognize changes, review metrics, and act on incidents or expired conditions. | Explain the current approval and respond to a simulated supplier change. |
| IT / security / operators | Enforce identities, permissions, logs, containment, and recovery. | Demonstrate access denial, token revocation, queue handling, and restoration controls. |
| Procurement / legal / privacy | Evaluate service-specific evidence, responsibilities, data rights, and contract changes. | Identify gaps in an example supplier assurance package. |
| Executives / approvers | Distinguish benefit, evidence quality, residual risk, legal constraints, and decision authority. | Make and document a scoped decision with conditions and unresolved uncertainty. |

Training completion is not proof of competence. Use realistic tasks and refresh training after material workflow changes, recurring errors, or role transitions. Give staff a clear way to report mistakes and near misses without having to diagnose whether the cause was the model, configuration, or workflow.

### 17.2 Review the governance program—not only the tools

Periodically sample actual deployments to test whether the inventory is accurate, decisions match use, conditions are enforced, evidence is current, and escalation/fallback works. Where feasible, use reviewers sufficiently independent of implementation to challenge assumptions. This is a recommended assurance practice, not a prescribed audit mandate.

Useful review questions include: Are pilots silently becoming production? Are expired conditions still open? Do users bypass review because the approved workflow is too slow? Do supplier notices reach the owner? Can the team identify affected records after a failure? Are retired connectors actually disabled? Track findings to closure and verify the fix rather than accepting a status update alone.

### 17.3 Put decisions—not just activity—before leadership

A useful leadership brief contains:

1. **Exposure:** material active use cases, affected workflows/data, autonomy, and known discovery gaps.
2. **Evidence:** which important approvals or safeguards lack current support and what uncertainty means for the decision.
3. **Outcomes:** demonstrated benefit alongside quality, safety, privacy, security, and operational signals.
4. **Exceptions:** unresolved high-impact findings, age, compensating controls, accountable owners, and expiry.
5. **Changes and incidents:** what materially changed, what was suspended, and what lessons affect other deployments.
6. **Decision requested:** a specific authorization, restriction, resource allocation, remediation priority, or retirement action, with options and consequences.

**Illustrative decision request:** “Continue the limited pilot with mandatory review while resolving the documented data-retention gap; prohibit expansion and new data categories; fund the required validation work; return for a scope decision after evidence review.” This is more actionable than reporting that a vendor questionnaire is 95% complete.

## Primary sources and reference points

- **HSCC Third-Party AI Risk and Supply Chain Transparency Guide — April 2026:** third-party lifecycle, vendor and dependency transparency, ongoing oversight, and exit considerations.[[1]](https://healthsectorcouncil.org/wp-content/uploads/2026/04/AI-Third-Party-Risk-Guide.pdf)
- **HSCC AI Cyber Governance Framework Implementation Guide — May 2026:** health-sector AI cybersecurity governance, oversight, resilience, and generative/agentic AI considerations; broader AI governance also needs non-cyber disciplines.[[2]](https://healthsectorcouncil.org/wp-content/uploads/2026/05/AI-Cyber-Governance-Framework-Implementation-Guide.pdf)
- **NIST AI RMF 1.0:** voluntary AI risk-management framework organized around GOVERN, MAP, MEASURE, and MANAGE.[[3]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
- **NIST AI 600-1, Generative AI Profile:** companion resource for identifying and managing generative-AI risks.[[4]](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
- **NIST CSF 2.0:** enterprise cybersecurity risk outcomes and governance context.[[5]](https://www.nist.gov/cyberframework)
- **NIST SP 800-161 Rev. 1:** cybersecurity supply-chain risk-management practices.[[6]](https://csrc.nist.gov/pubs/sp/800/161/r1/final)
- **HHS Business Associates guidance and FAQs:** relationship-based business-associate analysis, including the patient-portal AI chatbot example.[[7]](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html)
- **HHS HIPAA Security Rule NPRM:** rulemaking status and the distinction between the current rule and proposed changes; verify again before relying on a legal conclusion.[[8]](https://www.hhs.gov/hipaa/for-professionals/security/hipaa-security-rule-nprm/index.html)

**Use note:** This page is a governance and implementation reference, not legal advice, a clinical validation, an audit opinion, or a declaration of organizational compliance. Confirm current source versions, applicable obligations, local policies, and delegated approval authority before adopting these recommendations.