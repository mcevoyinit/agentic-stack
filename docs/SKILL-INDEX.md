# Skill index

66 skills ship in `claude/skills/`. One line each — read the skill's own
`SKILL.md` for full detail. Grouped by what they're for, not
alphabetically.

## Thinking modes (apply to any task)

| Skill | What it does |
|-------|---------------|
| `brainstorm` | Socratic spec refinement before any code is written |
| `cartographer` | Architecture/system-design "zoom out" mode |
| `forensic` | Scientific-method debugging — reproduce before fixing |
| `triage` | Incident-response, containment-first under time pressure |
| `paranoid` | Security-first: assume hostile input, check every boundary |
| `profiler` | Measurement-obsessed perf mode, refuses to guess |
| `surgeon` | Minimal-change mode — smallest diff that solves it |
| `archaeologist` | Safe modification of legacy code you don't fully understand |
| `ironclad` | Verification-driven — proves it works, never claims it |
| `reviewer` | Read-only code review, max 5 high-evidence findings |
| `oracle` | Routes your problem to the best-fit skill automatically |
| `deeper` | Push one level past the first-order answer |
| `push` | Push past premature completion — finish the untested path |
| `red-team` | CIA Tradecraft 4-pass decision stress-test, GO/KILL verdict |

## Research & analysis

| Skill | What it does |
|-------|---------------|
| `feynman` | Source-heavy deep research with adversarial verification |
| `literature-review` | Citation-graph academic literature survey |
| `due-diligence` | Investment due-diligence orchestrator |
| `cap-table` | Cap table reconstruction from public filings |
| `market-size` | TAM/SAM/SOM with the "Constrained Potential" framework |
| `tokenomics` | Token economics reconstruction for any crypto protocol |
| `regulatory-landscape` | Regulatory/licensing mapping across jurisdictions |
| `competitive-analysis` | Competitor analysis + AI council deliberation |
| `vc-acquirer` | Reverse-engineer how a company raised funding |
| `prior-art` | Patent/IP landscape research |
| `narrative-tracker` | Media coverage / public discourse tracking over time |
| `person-research` | Discrepancy engine for researching individuals (diligence prep) |
| `software-estate` | Document a company/protocol's full software architecture |
| `domain` | Domain-name availability checker (RDAP + DNS fallback) |

## Multi-model deliberation

| Skill | What it does |
|-------|---------------|
| `gemini` / `openai` / `grok` | Single second-opinion call to one model |
| `gemini-loop` / `openai-loop` / `grok-loop` | Utility libs a model argues with itself through (used by `looper`) |
| `looper` | Runs all three self-deliberation loops in parallel |
| `kamikaze` | Recursive multi-AI strategic deliberation, adaptive depth |
| `phoenix` | Two-model "twin dragon" dialectic for the hardest questions |
| `best-models` | Audits which model IDs your setup calls are still valid |

## Writing & docs

| Skill | What it does |
|-------|---------------|
| `academic-format` | LaTeX-inspired academic formatting + PDF export |
| `humanizer` | Strips AI-writing tells from text |
| `learn` | Feynman-method active-recall learning loop |
| `airplane` | Offline-readable study PDF on any topic |

## Frontend / UI

| Skill | What it does |
|-------|---------------|
| `agent-browser-ui-testing` | Methodology for browser-driving UI tests |
| `frontend-mix-explore` → `-plan` → `-design` → `-integrate` → `-validate` → `-fix-validation` → `-smoke` → `-deploy` | Mixed-provider full-stack build pipeline, one stage per skill — see `frontend-mix-example` for a worked run |

## Operational / meta

| Skill | What it does |
|-------|---------------|
| `morning-brief` | Flagship daily briefing — see its own `INTEGRATION.md` |
| `backup` | Generic Claude Code setup backup/restore template |
| `session-survey` | Survey + recover recent Claude Code sessions |
| `restore` | Bulk-reopen recent sessions into terminal tabs |
| `recall` | Search past conversations (needs `infra-templates/recall-db`) |
| `kb` | Query the structured knowledge base (needs `infra-templates/knowledge-base`) |
| `codex-review` | Cross-provider review via OpenAI Codex CLI |
| `mac-health` | macOS memory-pressure / zombie-process triage |
| `autoresearch-loop` | Autonomous investigate-and-fix loop over a task list |
| `archon` | Run/author Archon CLI workflows in isolated git worktrees |

## Travel / personal-productivity utilities (generic)

| Skill | What it does |
|-------|---------------|
| `cheap-flights` | Flight search across nearby airports, split tickets, hidden city |
| `x-intel` | Read-only X/Twitter intelligence briefs |
| `x-bookmark-export-cdp` | Export your X bookmarks via Chrome DevTools Protocol |
| `x-bookmarks-iterate` | Open one Claude Code tab per recent bookmark |

---

Skills intentionally NOT shipped (personal-data skills, or skills tied
to one person's specific life/business/relationships) are listed in
`SANITISATION-REPORT.md`, kept with the bundle's source — ask whoever
gave you this bundle if you want it.
