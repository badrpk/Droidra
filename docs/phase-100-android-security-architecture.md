# Phase 100 — Android security architecture decision record

Status: DESIGN-ONLY / NO RUNTIME AUTHORITY. Supersedes no existing security
contract. The experimental APK remains inert, unsigned and uninstalled.

## Security principals and ownership

| Principal | Trust | Android identity | Authority |
|---|---|---|---|
| Termux Sophyane proposer | untrusted | Termux app UID | propose bounded content; no broker-private filesystem access |
| RSI broker | trusted minimal TCB | dedicated installed app UID, **not yet implemented** | broker-private staging, validation, audit |
| Independent verifier | separately trusted | independently reviewed process/app identity, **not yet implemented** | verify immutable candidate; no promotion |
| Promoter | separately trusted, future | distinct explicitly authorized principal, **not yet implemented** | none in current protocol |
| Human owner | approval authority | authenticated user interaction, **not yet implemented** | future narrowly scoped approval only |

Distinct packages do not automatically prove distinct trust domains. Actual
installed package identities, signing provenance, UID assignments, process
isolation, and file ownership must be independently measured on a controlled
Android device. A shared UID or running verifier code inside the untrusted
proposer invalidates the proposed separation.

## IPC admission

1. A future exported endpoint must verify the **OS-reported Binder calling UID**
   at the entrypoint before parsing or acting on request data. Do not use
   caller-supplied UID, PID, package, challenge or signature claims as identity.
2. Resolve all packages belonging to the calling UID; account for shared UID,
   multiple users/work profiles, package changes, and signature verification.
   Signature permissions alone do not solve onboarding a separately signed
   Termux client. No IPC route is approved until that authorization is designed.
3. Non-exported components cannot be directly called from Termux's distinct UID.
   Do not mark components exported merely to make a demo work.
4. A broker-issued challenge is bound to the authenticated caller, operation,
   protocol version, expiry, exact request digest, and durable replay state.
   A challenge is anti-replay context, not proof of Android identity.
5. Bound transaction size and parsing time; reject unknown operations, excess
   file descriptors, oversized parcels, nested payloads and ambiguous encoding.
6. Reject all calls until a separately reviewed and tested IPC admission policy
   exists. There is **no approved Android IPC transport** in this phase.

## Verifier and receipt trust

- Verifier runs independently of the proposer and receives an immutable
  candidate snapshot plus pinned base digest and policy/version.
- Verifier results must be authenticated through OS identity and/or
  cryptographic signatures whose keys are inaccessible to the proposer.
- The broker rejects self-reported `verifier_ok`, arbitrary JSON evidence,
  unrecognized verifier versions, stale digests, crashes and timeouts.
- Receipts bind candidate, base, verifier identity, verdict, policy, monotonic
  sequence and prior receipt digest. A plain hash chain is not rollback proof.
- Trusted monotonic state / rollback anchor is a separate unresolved design
  decision. Until resolved, do not claim rollback resistance.

## Filesystem and commit boundary

- Phase 99 descriptor-relative Python tests are useful reference tests, not
  proof of protection from a same-UID adversary or hostile writable directory.
- Broker-private storage must be inaccessible to the proposer UID; broker must
  verify ownership/mode and reject shared writable directories.
- No symlinks, hardlink aliases, mount crossings or attacker-selected targets.
- Atomic rename and fsync do not by themselves prevent concurrent same-UID
  replacement. Treat writable directory compromise as a broken trust boundary.

## Evidence gates for any future implementation

1. Static manifest review: exported surfaces, permissions, debuggability,
   backups, network, SDK behavior and signing.
2. Controlled-device proof of distinct UIDs, package signatures, SELinux
   contexts and private-directory access denial across principals.
3. Real Binder negative tests: unauthorized UID, spoofed package, replay,
   cross-profile calls, malformed parcel, oversized input and crash recovery.
4. Independent verifier negative tests: forged verdict, tampered receipt,
   changed candidate, verifier timeout and process termination.
5. Rollback and storage fault injection with external trusted anchor.
6. Explicit human authorization before any signing, installation or execution
   authority. This design document is **not** that authorization.

## Hard prohibitions

No arbitrary shell/Git commands, no package installation, no promoter,
no autonomous production writes, no modification of production Sophyane,
no signing or installation of the inert APK.
