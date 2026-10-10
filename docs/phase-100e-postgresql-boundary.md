# Phase 100E — PostgreSQL integration boundary (design only)

Status: READ-ONLY ASSESSMENT. No database connection, migration, credential use, IPC, signing, installation or production modification.

## Existing integration evidence

Production Sophyane source includes `src/sophyane/sli_postgres.py`,
`src/sophyane/postgres_memory.py`, and
`src/sophyane/sli_migrate_postgres.py`. Its integration requirements
include psycopg. This establishes source-level support only: running
server availability, schema, role permissions and Termux connectivity
have not been independently verified.

## Threat boundary

The experimental broker's replay and operation journals currently use
SQLite reference models. Moving them into a PostgreSQL instance controlled
by the untrusted Sophyane proposer would collapse the trust boundary.
Database role separation alone does not help if the proposer controls the
PostgreSQL superuser, database files, operating-system account, or backup
and restore path.

A future PostgreSQL broker store requires:
1. Independently controlled server/storage and credentials inaccessible
   to the proposer; no shared superuser or filesystem ownership.
2. Dedicated least-privilege roles, deny-by-default grants, schema
   ownership outside the proposer role, and explicit credential rotation.
3. Server-enforced unique challenge values and transactional admission
   plus durable PENDING journal insertion in a single transaction.
4. Concurrent duplicate, restart, connection loss, transaction rollback,
   failover and stale-backup tests. No automatic retry of ambiguous PENDING.
5. An independent verifier and trusted reconciliation identity. A Python
   `trusted=True` flag is not authentication.
6. An external rollback/monotonic anchor before claiming rollback resistance.
7. Controlled-device evidence before Android IPC is enabled.

## Decision

Do not connect the current experimental broker to production Sophyane's
PostgreSQL database. Retain the SQLite offline reference and evaluate
PostgreSQL as a separate optional backend after server ownership and
deployment details are verified. No external operations are authorized.
