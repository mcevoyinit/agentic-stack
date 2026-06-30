---
name: vc-acquirer
description: Analyze how companies raised funding and apply learnings to your fundraise. Use when user says "how did X raise", "vc analysis", "funding playbook for X", or wants to understand a company's investor strategy. Researches VC layout, warm intro paths, and maps applicable tactics to a project directory you supply.
allowed-tools: WebSearch, WebFetch, Read, Glob, Grep
---

# VC Acquirer Analysis

Reverse-engineer how successful companies raised funding. Extract actionable playbooks.

## User Input

```
$ARGUMENTS
```

Parse the input to extract:
- **company**: The company to analyze (required)
- **project_dir**: Optional absolute path to YOUR project, used to apply
  the learnings (e.g. `~/projects/myco`). No default — if omitted, run
  analysis only and skip Phase 4.

Examples:
- `Evervault` → Analyze Evervault only
- `Stripe ~/projects/myco` → Analyze Stripe, apply to your project at that path
- `Harvey AI ~/work/startup` → Analyze Harvey, apply to the project at that path

---

## Phase 1: Funding History Research

WebSearch these queries and compile results:

1. **Funding rounds**
   - `"[company] seed round lead investor amount"`
   - `"[company] Series A funding valuation"`
   - `"[company] total funding raised crunchbase"`

2. **Investor names**
   - `"[company] angel investors who invested"`
   - `"[company] [founder name] how raised Sequoia"`
   - `"[company] YC batch accelerator"`

3. **Founder background**
   - `"[founder name] background before [company]"`
   - `"[founder name] Forbes 30 under 30"`
   - `"[founder name] previous exits companies"`

Output this table:

```markdown
### Funding History

| Round | Date | Amount | Lead Investor | Valuation | Notable Angels |
|-------|------|--------|---------------|-----------|----------------|
| Seed  | ...  | ...    | ...           | ...       | ...            |
| A     | ...  | ...    | ...           | ...       | ...            |
```

---

## Phase 2: The Raise Story

Research and document the **specific path** to funding:

### 2.1 Founder Credentials
- Age at founding
- Prior company/exits
- Forbes/media recognition
- University/accelerator
- Network affiliations (YC, Irish Mafia, PayPal Mafia, etc.)

### 2.2 The First Meeting
Search: `"[founder] how met [lead VC]"`, `"[company] first investor meeting story"`

Document:
- Who made the intro?
- What network/event/trip led to it?
- Did they have other term sheets creating FOMO?

### 2.3 Key Angels (with backgrounds)

```markdown
### Key Angels

| Name | Background | Thesis Alignment | Intro Path |
|------|------------|------------------|------------|
| ...  | Ex-[Company] [Role] | [Why relevant] | [How they got intro] |
```

### 2.4 FOMO Creation
- What competing offers did they have?
- What created urgency for investors?
- Timeline from first meeting to term sheet

---

## Phase 3: Extractable Tactics

Synthesize specific, actionable tactics:

```markdown
### Playbook Tactics

1. **[Tactic Name]**
   - What they did: [specific action]
   - Why it worked: [investor psychology]
   - Evidence: [source/quote]

2. **[Tactic Name]**
   ...
```

Common patterns to look for:
- "Camping trip near Sand Hill Road" moments
- Conference/accelerator networking
- Having term sheets in hand before top-tier meetings
- Strategic angel selection for corp dev intros
- Media narrative timing (Forbes lists, awards)

---

## Phase 4: Application (if project_dir provided)

If user specified a project directory (e.g., `~/projects/myco`):

### 4.1 Read Project Context

```
Read: [project_dir]/CLAUDE.md
Read: [project_dir]/README.md
Glob: [project_dir]/**/pitch*.md
Glob: [project_dir]/**/MA_POSITIONING*.md
```

Identify:
- Product thesis and stage
- Target market
- Exit strategy (M&A vs VC-scale)
- Current traction/metrics

### 4.2 Map Applicable Tactics

```markdown
## Application to [Your Project]

### Directly Applicable
| Their Tactic | Your Version | Why It Works |
|--------------|--------------|--------------|
| ...          | ...          | ...          |

### Target Investors from Their Network
| Name | Background | Relevance to You | Intro Path for You |
|------|------------|------------------|-------------------|
| ...  | ...        | [specific thesis match] | [how you could reach them] |

### Replicating Their FOMO
[Specific strategy given your current state]

### What Won't Transfer
- [Tactic/advantage they had that you don't]
- [Adjustment needed]
```

### 4.3 Immediate Actions

List 3-5 specific next steps with names:
1. Reach out to [Name] via [Path] because [Reason]
2. Create FOMO by [Action]
3. ...

---

## Output Format

Always structure final output as:

```markdown
# [Company] Funding Analysis

## Executive Summary
[2-3 sentences on their raise strategy]

## Funding History
[Table from Phase 1]

## Founder Background
[Key credentials that enabled the raise]

## The Raise Story
[Narrative of how they got funded]

## Key Angels
[Table with backgrounds and relevance]

## Extractable Tactics
[Numbered list of specific tactics]

---

## Application to [Your Project] (if applicable)
[Phase 4 content]
```

---

## Quality Standards

**Always include:**
- Specific names (not "various angels")
- Dollar amounts and dates
- Quoted sources when available
- Confidence level: [High/Medium/Low] for inferences

**Avoid:**
- Generic VC advice
- Unsourced claims
- "Network effects" hand-waving
- Tactics without evidence they worked
