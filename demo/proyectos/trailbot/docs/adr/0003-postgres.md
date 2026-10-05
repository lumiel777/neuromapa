# ADR 0003: PostgreSQL instead of SQLite

**Status:** accepted (July 2025).

## Context

The first version used SQLite. With two workers writing ratings at the same time, we saw "database is locked"
errors on busy Saturday mornings.

## Decision

Move to a small managed PostgreSQL.

## Consequences

- Real unique constraints for ratings ([DATA.md](../DATA.md)).
- Daily backups handled by the provider.
- One more monthly cost, small enough for now.
