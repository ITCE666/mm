---
name: quota-handoff
description: Create or update a truthful project handoff document when a verified usage provider reports that the remaining quota is below a configurable threshold, usually 5%. Use for Codex or other software limits when a JSON, CLI, API, or user-provided usage snapshot is available, and for preparing a continuation README before a quota window is exhausted.
---

# Quota Handoff

Use this skill to preserve project continuity when a verified usage window is nearly exhausted. The default trigger is remaining quota `< 5%`; allow the caller to override the threshold.

## Operating rules

- Require a verified usage snapshot. Never infer a provider's remaining quota from the current conversation, model token budget, a generic rate-limit error, or a screenshot that was not supplied for inspection.
- Treat an unavailable or ambiguous usage source as `unknown`; do not generate a low-quota alert from it.
- Inspect the project before writing. Read the repository instructions and the relevant source/configuration files, then record evidence instead of guessing.
- Write `HANDOFF.md` by default. Use `README_HANDOFF.md` when the project already has a meaningful `README.md`. Never overwrite `README.md` unless the user explicitly requests it.
- Preserve the prototype-versus-production boundary. Label unverified behavior, missing credentials, unrun commands, and future work explicitly.
- Do not copy secrets into the handoff. Redact tokens, passwords, private keys, cookies, and credential-bearing URLs.

## Workflow

1. Normalize the usage input with `scripts/check_usage.py`. It accepts `remaining_percent`, `remaining` plus `limit`, or `used` plus `limit`.

   ```powershell
   python scripts/check_usage.py --input usage.json --threshold 5
   ```

2. Continue only when the result is `low` and `should_handoff` is `true`. A result of `ok` means no handoff is needed; `unknown` means obtain a better usage source or ask the user to provide one.

3. Generate a deterministic evidence baseline from the current project:

   ```powershell
   python scripts/generate_handoff.py --project-root . --usage-json usage.json --output HANDOFF.md
   ```

4. Improve the generated document using the inspected project context. Keep these sections, adapting them to the project:

   - trigger evidence: provider, window, remaining percentage, threshold, source, and capture time;
   - project purpose and current implementation status;
   - files and entry points that the next agent should open first;
   - exact run, test, build, and deployment commands that were verified;
   - current branch/commit and working-tree changes;
   - known limitations, missing access, and unverified assumptions;
   - pending work ordered by the next safest action;
   - decisions, blockers, and the exact continuation prompt if the current task is incomplete.

5. Re-read the final document, check that paths and commands match the project, and report what was verified versus what was not.

## Automation contract

An external scheduler, provider adapter, or Codex automation may call the two scripts. The adapter must produce a JSON snapshot; see [references/usage-adapters.md](references/usage-adapters.md). The scripts are provider-neutral and do not log credentials.

Codex-specific usage is a special case: if the client or account does not expose a machine-readable remaining percentage, this skill cannot read it directly. Use a supported export/API/browser adapter when available, or pass a user-supplied snapshot. Do not claim that a live Codex weekly balance was checked when it was not.

For a one-shot automated action, run the checker and generator in the same command:

```powershell
python scripts/check_usage.py --input usage.json --threshold 5 --project-root . --handoff-output HANDOFF.md
```

The generator runs only for a verified low result. It leaves the project unchanged when the status is `ok` or `unknown`.
