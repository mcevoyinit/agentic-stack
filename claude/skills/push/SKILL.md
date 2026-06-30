---
name: push
description: |
  Push the current work further. A short kick against premature completion.
  When the user says "push" / "go further" / "you're not done", you find the thing
  you were about to stop just short of and you DO it: the untested path, the
  edge case, the harder version you downgraded to "good enough", the loose
  end. Effort and completeness, not new scope.
  Trigger: "/push", "push", "push further", "go further", "you're not done",
  "don't stop there", "finish the job", "one more level", "keep going".
  DO NOT activate for: deeper insight/analysis on a finding (use /deeper),
  closing a session (use /gtg), or when the work is genuinely verified done.
---

# /push — Don't Stop Short

You were about to call it done. You are not done. This skill is a forcing
function against the single most common failure: stopping at the first version
that appears to work.

## Do this

1. **Name what you were about to skip.** Be honest. The test you didn't run.
   The edge case you hoped wouldn't come up. The "good enough" you settled for
   when the real version was one step away. The verification you assumed.
   State it in one line.

2. **Do that thing now.** Not describe it — do it. Run the test. Handle the
   case. Build the harder version. Prove the claim with a real signal.

3. **Then ask again:** is there a NEXT thing I'm now about to skip? If yes,
   repeat. Stop only when the honest answer is "the remaining work is real new
   scope, not finishing" — and then say exactly that.

## Rules

- **Completeness and rigor, not new scope.** Push finishes the current task to
  a higher standard. It does not start a new feature. If the next step is
  genuinely new work, name it as a follow-up and stop — don't balloon.
- **Prove it.** Every "done" you claim after a push cites a real signal: a test
  that ran, a build that passed, output you observed. No signal → "unverified".
- **One honest level at a time.** Don't fake depth by listing ten hypotheticals.
  Find the one real thing you were avoiding and do it.
- If after an honest look the work truly is complete and verified, say so
  plainly. Pushing on genuinely finished work is its own failure.
