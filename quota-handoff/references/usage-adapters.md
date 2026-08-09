# Usage adapter contract

The monitor is deliberately provider-neutral. An adapter should write one JSON object containing a measured usage window. At least one of these forms is required:

```json
{
  "provider": "example-tool",
  "window": "weekly",
  "remaining_percent": 4.2,
  "captured_at": "2026-08-09T11:00:00Z",
  "source": "provider-cli"
}
```

or:

```json
{
  "provider": "example-tool",
  "window": "weekly",
  "used": 95.8,
  "limit": 100,
  "captured_at": "2026-08-09T11:00:00Z",
  "source": "usage-export.json"
}
```

The checker accepts `remaining_percent`, `remaining` + `limit`, `used` + `limit`, or `used_percent`. It rejects missing, non-numeric, and out-of-range percentages as `unknown`.

## Provider integration patterns

- Prefer a documented CLI or API that returns the account's usage window.
- Keep credentials in the provider's normal secret store or process environment. Never put them in the JSON snapshot, the handoff, or command output.
- Schedule the adapter outside the skill: Task Scheduler, launchd, cron, CI, or a supported app automation. Invoke `check_usage.py` at a sensible interval and pass `--project-root` and `--handoff-output`.
- Add debouncing or a cooldown in the scheduler if it runs repeatedly. The handoff generator itself is intentionally stateless.
- Record the source and capture time so a future agent can distinguish fresh evidence from a stale export.

## Codex limitation

Codex usage can vary by plan, task size, and execution context. If the current Codex client does not expose a machine-readable balance, there is no safe provider adapter for this skill to invent. Use a supported export/API/browser adapter or provide a snapshot manually; otherwise the checker must remain `unknown`.
