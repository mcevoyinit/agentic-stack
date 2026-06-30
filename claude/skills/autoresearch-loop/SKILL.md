---
name: autoresearch-loop
description: |
  Karpathy-style autonomous investigation and fix loop for codebases. Use when:
  (1) you have a tasks.json with 5+ open problems to investigate or fix,
  (2) user says "autoresearch", "run the loop", "investigate all tasks", "spawn agents",
  "overnight investigation", "autonomous research", "fix all bugs",
  (3) you want to produce implementation plans OR execute existing plans.
  Two modes: RESEARCH (produce plans/*.md) and FIX (execute plans with coding agents).
  Key pattern: constraints are the supervisor, not infrastructure. Verify tasks are
  still open before running (37% stale rate observed). Output is either plans or commits.
author: Claude Code
version: 2.0.0
date: 2026-03-10
---

# AutoResearch Loop — Autonomous Investigation & Fix

You are the loop controller. You read `tasks.json`, verify tasks are current, then spawn parallel agents to either investigate (produce plans) or fix (execute plans).

## Mode Selection

Determine mode from context:

| User Says | Mode | Output |
|---|---|---|
| "investigate", "research", "find solutions", "produce plans" | RESEARCH | `plans/*.md` |
| "fix", "execute", "code the fixes", "run autofix" | FIX | Git commits |
| "autoresearch" (default) | RESEARCH | `plans/*.md` |
| Tasks have `status: "investigated"` + plans exist | FIX | Git commits |
| Tasks have `status: "pending"` + no plans | RESEARCH | `plans/*.md` |

## Phase 1: Load & Verify Tasks

```
Read: tools/autoresearch/tasks.json
```

**Verification (CRITICAL — 37% stale rate):**

For each task with `status: "pending"` or `status: "investigated"`:
1. Read the first file listed in `files[]`
2. Check if the bug/pattern described still exists at the referenced location
3. Check `git log --oneline -5 -- <file>` for recent fixes

Spawn 2-3 parallel Explore agents to verify batches of tasks simultaneously. Mark results:
- Still open → keep as-is
- Already fixed → set `status: "verified_fixed"`, skip
- Code restructured but bug likely exists elsewhere → update `files[]` and `description`

Report verification results before proceeding:
```
Verified: 8/12 still open, 3 fixed, 1 stale
Proceeding with 8 tasks.
```

## Phase 2: RESEARCH Mode — Spawn Investigation Agents

For each verified pending task, spawn a background Agent:

```
Agent(
  description: "Investigate {TASK_ID} {short_title}",
  mode: "bypassPermissions",
  run_in_background: true,
  prompt: <see investigation prompt below>
)
```

**Investigation Agent Prompt Template:**
```
You are an autonomous research agent investigating an open bug in the codebase.
Your job is NOT to write code. Produce a detailed implementation plan.

## Task
**ID**: {task.id}
**Title**: {task.title}
**Description**: {task.description}
**Files to investigate**: {task.files}
**Acceptance criteria**: {task.acceptance}

## Research Workflow
1. Read the files listed above
2. Trace the execution path — follow function calls, imports, references
3. Search for related code — grep for function names, class names, patterns
4. Understand the full context before writing the plan
5. Be precise — include exact line numbers, exact code snippets, exact file paths

## Output
Write a plan file to: tools/autoresearch/plans/{task.id}-plan.md

Structure:
# {task.id}: {task.title}
## Problem Statement
## Root Cause Analysis (code-traced, with file:line references)
## Current Behavior (exact code snippets)
## Desired Behavior
## Implementation Plan
### Files to Modify (table: File | Change | Lines)
### Step-by-Step Changes (exact current code → exact new code per step)
## Test Strategy
## Risk Assessment
## Estimated Effort

Do NOT modify any source code files. Only write to tools/autoresearch/plans/.
```

**Parallelism rules:**
- Spawn up to 6 agents simultaneously
- If more than 6 tasks, batch into waves of 6
- Wait for each wave to complete before starting the next
- Report results as each agent completes

## Phase 3: FIX Mode — Spawn Coding Agents

For each task with `status: "investigated"` and a plan file:

**Option A: Bash runner (autonomous, overnight)**
```bash
cd tools/autoresearch && ./autoresearch-fix.sh
```
This runs the coding agent loop with test verification and auto-revert on failure.

**Option B: In-session agents (interactive, immediate)**

For each plan, spawn a background Agent:
```
Agent(
  description: "Fix {TASK_ID} {short_title}",
  mode: "bypassPermissions",
  run_in_background: true,
  prompt: <see coding prompt below>
)
```

**Coding Agent Prompt Template:**
```
You are an autonomous coding agent executing a pre-researched implementation plan.

## Task
Read and execute: tools/autoresearch/plans/{task.id}-plan.md

## Rules
1. Read the plan file FIRST
2. Read every file in "Files to Modify" BEFORE editing
3. Make changes exactly as described in "Step-by-Step Changes"
4. If line numbers shifted, match by code snippet instead
5. After ALL changes, run: {task.test_command}
6. If tests PASS: commit with message "fix({area}): {title}"
7. If tests FAIL from your change: fix and retry (max 3)
8. If tests FAIL pre-existing: note in log, proceed
9. Do NOT make changes beyond the plan. No refactoring.
```

**Execution order matters:**
- Fix dependency chains first (e.g., APP-005 before APP-001)
- Fix quick wins first within a priority tier
- Never run coding agents in parallel on the SAME file

## Phase 4: Report Results

After all agents complete:

1. Check which plan files were created (RESEARCH) or which commits landed (FIX)
2. Update `tasks.json` statuses
3. Present summary table:

```
| ID | Title | Status | Output |
|----|-------|--------|--------|
| APP-005 | Consensus gap | fixed | commit abc123 |
| APP-001 | Seal fail-open | fixed | commit def456 |
| APP-003 | NS0 bypass | fix_failed | see logs/APP-003-fix.log |
```

4. For failures: read the log file and summarize what went wrong
5. Suggest next steps (re-investigate failed tasks, move to next tier, etc.)

## The Three Files

The entire system is three files per Karpathy's pattern:

| File | Purpose | Equivalent |
|---|---|---|
| `program.template.md` | Research agent instructions | Karpathy's `program.md` |
| `coding-agent.template.md` | Coding agent instructions | (extension) |
| `tasks.json` | Task queue with scoped files | Karpathy's training config |
| `autoresearch-research.sh` | Research loop (< 100 lines) | Karpathy's run script |
| `autoresearch-fix.sh` | Coding loop (< 150 lines) | (extension) |

## Constraints

- **Research mode**: NEVER modify source code. Only write to `tools/autoresearch/plans/`
- **Fix mode**: Only modify files listed in the plan. Test gate is mandatory.
- **Both modes**: Verify tasks before running. 37% stale rate is real.
- **Overnight runs**: Use the bash scripts (`autoresearch-research.sh`, `autoresearch-fix.sh`) for unattended operation
- **Interactive runs**: Use Agent tool with `run_in_background: true` for parallel investigation

## Quick Start

```bash
# Research mode (overnight — produces plans)
cd tools/autoresearch && ./autoresearch-research.sh

# Fix mode (overnight — executes plans, commits fixes)
cd tools/autoresearch && ./autoresearch-fix.sh

# Dry run (preview what would happen)
./autoresearch-research.sh --dry-run
./autoresearch-fix.sh --dry-run

# Single task
./autoresearch-research.sh --task APP-007
./autoresearch-fix.sh --task APP-001

# Morning review
ls plans/
git log --oneline --since="12 hours ago"
```
