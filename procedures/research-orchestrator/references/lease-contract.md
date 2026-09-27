# Lease Contract

> Load this when: reading or writing `.research/leases/*.json`, implementing claim or
> heartbeat scripts, or validating execution ownership.

## File Location

Each task has at most one current lease file:

```text
.research/leases/T004.json
```

Older leases may be retained as released or superseded records, but only one active
lease may exist for a `single_owner` task.

## Minimal Lease

```json
{
  "schema_version": 1,
  "lease_id": "L-T004-20260625T000000Z",
  "task_id": "T004",
  "owner_id": "codex-main",
  "role": "engine-runner",
  "status": "active",
  "acquired_at": "2026-06-25T00:00:00+08:00",
  "heartbeat_at": "2026-06-25T00:00:00+08:00",
  "expires_at": "2026-06-25T01:00:00+08:00",
  "owner_dir": "work/runs/ads-relax/",
  "exclusive_paths": ["work/runs/ads-relax/"]
}
```

## Fields

Required:

| Field | Meaning |
|---|---|
| `schema_version` | Lease schema version; currently `1`. |
| `lease_id` | Stable lease identifier. |
| `task_id` | Task this lease owns. |
| `owner_id` | Agent/session identity chosen by the claimant. |
| `role` | Task role at claim time. |
| `status` | `active`, `released`, `stale`, `cancelled`, or `superseded`. |
| `acquired_at` | ISO 8601 claim time. |
| `heartbeat_at` | ISO 8601 last heartbeat. |
| `expires_at` | ISO 8601 time after which the lease is stale. |
| `owner_dir` | Project-root-relative primary mutable directory. |
| `exclusive_paths` | Project-root-relative mutable paths protected by this lease. |

Recommended:

- `released_at`: ISO 8601 time the owner released the lease.
- `release_status`: final task status requested at release.
- `job_ids`: scheduler/local job IDs submitted under this lease.
- `notes`: short recovery or release note, never secrets.

## Status Meaning

- `active`: owner currently owns the task and exclusive paths.
- `released`: owner voluntarily released the lease.
- `stale`: lease expired and reconciliation has marked it stale.
- `cancelled`: owner cancelled before useful work.
- `superseded`: a later lease replaced this record after explicit recovery decision.

Only `active` leases block claims. Stale leases block blind resubmission until a recovery
decision explains what happened.

Job IDs are a lease-level index, not the authoritative scheduler history. Full attempt
records live under `.research/jobs/` and follow `job-contract.md`. A lease cannot be
released while one of its attempts is `submitting`, `submission_unknown`, `pending`, or
`running`.
