# ADR 0001: Telegram first, no mobile app

**Status:** accepted (May 2025).

## Context

The first idea was a mobile app with maps. Building and publishing an app for two stores, alone, would take months
before anyone could use it.

## Decision

Start as a Telegram bot. Hiking groups in Argentina already coordinate on Telegram and WhatsApp.

## Consequences

- No maps in the answer, only names, distances and a link. Offline maps stay in the backlog.
- The whole product is one webhook ([ARCHITECTURE.md](../ARCHITECTURE.md)).
