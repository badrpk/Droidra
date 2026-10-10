# Sophyane RSI Android broker — security contract draft v0

Status: DESIGN ONLY. Not an implementation approval. The accepted APK remains unsigned, inert, uninstalled, without DEX, permissions, or components. Do not change that baseline in this phase.

## Boundary and principals

- **Untrusted proposer:** Sophyane/LLM process running in Termux. Treat prompts, generated patches, filenames, Git metadata, test output, and proposed commands as attacker-controlled.
- **Trusted broker:** future separately installed Android package `com.sophyane.rsi.broker`, with a distinct Android application UID. A package name or unsigned APK alone does **not** create a UID boundary. Android package signature and install/update provenance must be validated before any deployment phase.
- **Repository owner:** user-authorized working tree and dedicated staging area; the broker must never infer authorization merely because a path exists.
- **Verifier:** independently checks staged candidate against frozen preconditions and explicit policy; cannot be replaced by LLM prose or self-reported success.
- **Promoter:** narrow capability granted only after successful verification and explicit approval according to a separately documented approval policy.

## Interface contract (future, not yet implemented)

Request envelope: protocol version, request ID, bounded operation enum, broker-issued challenge/session binding, expected base revision and content digest, relative path(s), byte-count limits, and proposed content digest. No arbitrary shell strings, environment variables, absolute paths, or URL fetches.

Transport: prefer explicit Android IPC with OS-verified caller identity and a dedicated permission/authorization design. **Never** trust caller-provided UID, package name, token, or PID as proof. Do not expose exported components by default. If a component must be exported later, require a threat-reviewed caller verification mechanism and tests for unauthorized callers, replay, confused-deputy calls, and cross-user/profile access. A non-exported component cannot be invoked directly by a separate Termux UID; connectivity must be explicitly designed rather than assumed.

Allowed operations initially: `health` (no secrets), `stage_candidate` (broker-controlled staging only), `verify_candidate` (read-only), `get_receipt` (redacted), `discard_candidate`. Promotion, rollback, Git commands, package installation, process spawning, and arbitrary file writes are **not** in the initial allowlist.

## Filesystem and race controls

1. Broker owns a private staging directory and does not accept attacker-selected absolute destinations.
2. Resolve each path relative to an already-open trusted directory descriptor; reject traversal, empty segments, alternate separators, symlinks, hardlink aliases, device files, and unexpected mount crossings.
3. Require exact regular-file types and enforce per-request/aggregate byte, count, and depth limits. Reject duplicate, case-fold-colliding, and normalization-colliding paths.
4. Hold stable handles during validation and use atomic no-follow creation/rename patterns where supported; revalidate inode/device and base digests at commit. Path string checks alone are insufficient against TOCTOU.
5. No access to Termux private files is implied by the broker UID. Future cross-UID data transfer must use explicit narrowly scoped IPC/FD grants, not shared-storage assumptions.

## State machine and authority

`RECEIVED -> AUTHENTICATED -> VALIDATED -> STAGED -> VERIFIED -> RECEIPT_ISSUED`; any failure -> `DENIED` with no side effects outside broker-owned staging.

Verification cannot authorize promotion by itself. A future promotion protocol must bind user approval to the exact immutable candidate digest, target revision, verifier version, and receipt; it must fail closed on changed inputs, expired approval, or ambiguous rollback state. No unattended/continuous RSI in this phase.

## Evidence

Receipt records request ID, policy/protocol versions, source/base digest, candidate digest, verifier identity, checks executed, verdict, and monotonic sequence. Preserve tamper-evident local records; hash chaining alone does not make a log immutable against a compromised broker. Never include secrets, raw prompt content, or unnecessary personal data. Missing evidence means denial, not success.

## Required tests before implementation approval

- Unauthorized UID/caller, spoofed package identity, replay, wrong user/profile, stale challenge, oversized input, and unknown operation all denied.
- Traversal, symlink/hardlink, race during validation, path alias, mount escape, and changed base revision denied without mutation.
- Tampered receipt, verifier crash/timeout, partial write, low storage, process death, and concurrent conflicting requests fail closed.
- No exported attack surface without explicit review; no implicit permission escalation; no shell execution; no network dependency.
- Separate integration proof on a controlled Android test device for real distinct UIDs and OS-enforced caller identity, only after an independently authorized deployment phase.

## Current gate

The inert prototype and its 77 offline tests do not prove any of these future runtime properties. This document authorizes **no** APK signing, installation, promotion, production-tree modification, or autonomous execution.
