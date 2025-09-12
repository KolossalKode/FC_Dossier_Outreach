## 🔐 Non‑Negotiables (pinned at top)
- **Change scope:** Only modify files/lines explicitly requested. If a dependency forces wider edits, stop and propose the minimal diff first.
- **Explain clearly:** For every change, include a short “What/Why/Risk” note in simple language.
- **Risk callouts:** If a task risks breaking the project (build, data, infra, security), stop and insert a **RISK** block (template below) before proceeding.
- **Read context first:** Always read `TODO` and `README` end‑to‑end before planning work. Summarize key constraints in your plan.
- **No dummy data / fake tests:** Use real fixtures, sanitized samples, or contract tests. Delete any scaffolding you create.
- **Changelog required:** Every PR must update the **Change Log** section below.

---

## 🧭 Execution Protocol (Do this in order, every time)
1. **Intake**  
   - Read `TODO` + `README`. Extract requirements, constraints, environment, and acceptance criteria.
2. **Plan (max 8 bullets)**  
   - List the smallest viable approach. Note alternatives (1–2 lines each) and why not chosen.
3. **Diff‑first**  
   - Propose a unified diff showing *only* the intended changes. Keep functions, signatures, and file touch count minimal.
4. **Test plan**  
   - Enumerate test cases (happy path, edge, failure, performance). State how each is verified (unit/integration/contract).
5. **Implement**  
   - Code to the plan. Keep commits atomic and reversible.
6. **Self‑review**  
   - Run lint, type checks, tests, and any CI scripts locally if available. Paste summaries + key outputs.
7. **Explain**  
   - Write a simple “What changed, why, risks, how to roll back” paragraph.
8. **Update docs**  
   - Update `README` snippets, `.env.example`, and usage notes if behavior changed.
9. **Change Log**  
   - Add an entry using the template below.

---

## ✅ Definition of Done (gatekeeper)
- [ ] All acceptance criteria from `TODO` are satisfied.  
- [ ] Only requested areas changed; unrelated refactors deferred.  
- [ ] Tests added/updated; **no fake data**; coverage not reduced.  
- [ ] CI/lint/type checks pass locally.  
- [ ] Risks documented with mitigation or explicit approval.  
- [ ] `README`/examples updated if usage or setup changed.  
- [ ] **Change Log** entry added.  
- [ ] Rollback plan stated.

---

## 🧪 Testing Policy (no dummy data)
**Allowed:**  
- Sanitized real samples (PII removed).  
- Factories generating valid domain objects.  
- Contract tests (e.g., OpenAPI/GraphQL schema, file format contracts).  
- Record‑replay (e.g., VCR/pytest‑recording) against **sandbox** endpoints with secrets stripped.

**Disallowed:**  
- Invented payloads not conforming to real schemas.  
- Tests that pass without asserting behavior (snapshots with no meaning).  
- Hitting production services or using real secrets.

**Test Matrix (fill as you code):**
- Happy path  
- Edge (null/empty, max length, special chars, timezones)  
- Failure (network, 4xx/5xx, timeouts, partial writes)  
- Performance (N=1, N=1k, cold vs warm)  
- Security (authz boundaries, injection attempts, XXE/SSRF vectors)

---

## 🧩 Risk & Safeguards
Use this block before risky work:

```
RISK
- Area: <build/runtime/data/security>
- What could break: <plain-English>
- Blast radius: <files/services/users affected>
- Early warning: <log/metric/error to watch>
- Mitigation: <feature flag, canary, toggle, try/except, timeout>
- Rollback: <git revert/flag off/previous image tag>
```

Escalate if any of these are true:
- Unclear or conflicting requirements in `TODO` vs `README`.
- Requires schema/data migration without a reversible plan.
- Introduces a new dependency affecting licensing or supply chain.
- Touches auth, payments, PHI/PII, or infra credentials.

---

## 🧠 Decision Rubric (use, then summarize)
- **First Principles:** Restate the problem, constraints, and invariants.  
- **Pareto 80/20:** Ship the smallest PR that delivers 80% of value.  
- **Ockham:** Prefer the simplest design that meets requirements.  
- **Second‑Order:** Note at least one downstream effect (perf, UX, ops).  
- **Inverse/Pre‑mortem:** List the top 3 ways this could fail and countermeasures.  
- **Tree of Thoughts:** Write 2–3 solution options in one‑liners; pick one and say why.

---

## 🔧 Code Quality & Conventions
- **Errors:** Fail fast; return typed results or raised errors with actionable messages.  
- **Logging:** Structured logs at boundaries; no secrets; include correlation IDs if present.  
- **Config:** All knobs via env or config files; update `.env.example`.  
- **Dependencies:** Pin versions; explain any new transitive risk; run audit if available.  
- **Performance budgets:** Note any big‑O or latency changes if touching hot paths.  
- **Accessibility/i18n (if UI):** Respect contrast, keyboard nav, and locale strings.

---

## 🔑 Secrets & Environment
- No secrets in code, tests, or logs.  
- Read from env vars or secret manager only.  
- Provide **exact** setup steps for any new env var in `.env.example` + `README`.  
- When mocking, use placeholders like `"<TOKEN>"` not realistic keys.

---

## 🔀 Git Workflow & PR Hygiene
**Branching:** `feature/<ticket>-<slug>`  
**Commit message:**
```
<type>(scope): <summary>

Context: <link to TODO/issue>
Why: <1–2 lines>
What: <key changes>
Tests: <areas covered>
Risks: <if any>
```

**PR Template:**
```
Summary
- What changed:
- Why this approach:

Scope
- Files/areas touched:
- Out of scope:

Test Evidence
- Unit:
- Integration/contract:
- Screenshots/log excerpts (if UI/ops):

Risk & Rollback
- Risks:
- Mitigation/feature flags:
- Rollback plan:

Docs
- README updated?:
- .env.example updated?:

Checklist
- [ ] Definition of Done met
- [ ] Change Log updated
```

---

## 🗒️ Change Log (append per PR)
```
## [YYYY-MM-DD] <short title>
- Author: <name or bot/agent id>
- Ticket/Context: <link or TODO ref>
- Summary: <1–3 lines in plain English>
- Files changed: <count> (list key files)
- Tests: <new/updated tests and coverage impact>
- Risk level: <Low|Med|High>, rollback: <how>
```

---

## 🛠️ Troubleshooting Ladder (when stuck)
1. Restate the problem in one sentence.  
2. Re‑read `TODO` + `README`; extract acceptance criteria.  
3. Run the smallest reproducible example.  
4. Add an **Observation Log**: what you tried, what changed, actual error text.  
5. Create a minimal patch/diff and run only the impacted tests.  
6. If still blocked, propose **two** alternative paths with pros/cons and ask for approval.

---

## 🗣️ User‑Facing Explainers (keep it simple)
For each substantive change, include this short block in your response:
```
WHAT: <plain-language description of the change>
WHY: <problem it solves, tied to TODO/README>
HOW TO VERIFY: <exact command/click path or test to run>
RISKS: <top 1–2 with mitigations/rollback>
```

---

## 🧱 Feature Flags & Rollbacks (if applicable)
- Wrap risky behavior behind a flag with a safe default.  
- Provide a one‑line rollback command (e.g., `export FEATURE_X=off` or `helm rollback <release>`).  
- Keep migrations backward compatible or provide a down‑migration.

---

## 🔍 Security Quick‑Scan
Before merging, answer:
- Any new inputs parsed? Validate/limit size/timeout?  
- Any external calls? Timeouts/retries/circuit breakers set?  
- Any file/network I/O? Paths sanitized?  
- Any user data stored/serialized? Encryption at rest/in transit?  
- Any third‑party libs added? License and audit checked?

---

## 📚 ADR (Architecture Decision Record) Template (when design changes)
```
Title: <concise decision>
Date:
Status: Proposed | Accepted | Superseded by <ADR#>

Context
- Requirements, constraints, relevant TODO/README excerpts.

Decision
- Chosen approach in 3–6 bullets.

Alternatives
- Option A: <1–2 lines pros/cons>
- Option B: <...>

Consequences
- Positive:
- Negative:
- Follow-ups:
```

---

# Why these additions help (concise rationale)
- **Execution Protocol & DoD**: Enforces predictable, repeatable delivery and prevents scope creep.  
- **Risk blocks + Rollbacks**: Makes breakage less likely and faster to recover.  
- **Testing policy (no dummy data)**: Raises signal quality; avoids brittle or misleading tests.  
- **Decision rubric**: Bakes in first‑principles, Pareto, second‑order, and inverse thinking without verbosity.  
- **Git/PR hygiene**: Produces reviewable, auditable changes; speeds merges.  
- **Secrets & env**: Prevents the most common, costly security mistakes.  
- **User‑facing explainers**: Satisfies your “explain in simple language” rule every time.  
- **ADR**: Captures why we chose a path; reduces future rework.  
- **Troubleshooting ladder**: Keeps agents moving forward without thrash.

---

## Anything else I think you should change (and why)
- **Pin a “Minimal Diff Rule”** explicitly (already implied): prevents silent refactors and keeps merges safe.  
- **Add a `.env.example` requirement** to `README`: reduces setup friction and misconfig bugs.  
- **Introduce feature flags** section if you don’t have it: safer rollouts.  
- **Adopt a PR template in your repo** (mirrors above): forces consistency even if a different assistant submits the PR.  
- **Automate checks** (pre‑commit hooks for lint/format/type): catches issues before CI, accelerates iteration.

If you want, I can tailor this to your stack (language/framework/test tools) and produce concrete commands and example tests that comply with “no dummy data.”
