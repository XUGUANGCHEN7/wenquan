# Shunan Hot Spring Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver two independent WeChat mini programs, operations Web, FastAPI/MySQL backend, and authenticated outbound device-service Mock.

**Architecture:** A versioned FastAPI modular monolith owns business facts and transactions. Native mini programs and Vue Web share its API; the local device service polls persisted tasks through a replaceable adapter.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PyMySQL, pytest; MySQL 8/SQLite tests; Vue 3, TypeScript, Vite, Pinia, Vue Router, Vitest; native WeChat JavaScript/WXML/WXSS; Node.js 24.

**Spec:** `docs/superpowers/specs/2026-11-01-shunan-phase-one-design.md` and `.clinerules/project-rules.md`.

## Global Constraints

- Money is integer cents; clients never choose prices.
- APIs use `/api/v1`; errors contain `code`, `message`, and `request_id`.
- One member/account spans explicitly bound `(appid, openid)` identities; no silent merge.
- Five 120-minute private slots, one final 30-minute cleaning, and 15-minute holds.
- Only verified payment changes state; principal is spent before gift and reversals use original deductions.
- Dining retains `room_use_id`; failed delivery validation enters manual exceptions without automatic refund.
- Tickets admit once; every wristband deposit has one stable refund number.
- Unknown device outcomes never auto-retry/release reservations; real hardware is unverified.
- Development auth/payment/device adapters are visibly non-production and disabled securely in production.

## Review Focus

- Concurrent room/locker holds need database locks and unique constraints.
- Expired holds, duplicate callbacks, and repeated refunds cannot apply twice.
- Continuous booking and delayed assignment need separate interval tests.
- UI money formatting avoids floating point.
- Mock screens never imply real WeChat or hardware acceptance.

## File Map

`backend/app/core` contains configuration/database/auth. Each `backend/app/modules/<domain>` owns models, schemas, services, and routes. Alembic and tests live in `backend`. Each mini program has its own native project and static tests. `frontend_web/src` contains typed API, stores, router, views, and components. `device_service` contains the worker and adapters. Root files provide Compose, environment templates, and delivery docs.

## Task 1 — Repository and contract foundation

- [x] Move the existing native app into `frontend_1`, track project rules, and leave unrelated historical files untouched.
- [x] Add `.gitignore`, `.env.example`, README, Compose MySQL 8, and backend package/test configuration.
- [x] Implement app factory, request-ID errors, settings, sessions, health, Alembic, and role/member auth.
- [x] Test health, stable errors, role denial, ownership, and production rejection of development login.
- [x] Run foundation tests and inspect versioned OpenAPI routes.

## Task 2 — Identity, catalog, wallet, and payment kernel

- [x] Define identity/configuration/account/ledger/order/payment/refund/audit models and migration.
- [x] Test explicit binding, principal-first spending, idempotent references, and original-source refunds.
- [x] Implement binding, server prices/activities/menus, wallet, recharge, gateway protocol, and development-only Mock confirmation.
- [x] Implement transactional balance payment and verified dispatch; duplicate callbacks have no duplicate effects.
- [x] Run tests and SQLite migration upgrade/downgrade/upgrade; MySQL verification is Task 9.

## Task 3 — Tickets and private-room inventory

- [x] Add ticket/admission and room/booking/block/use/cleaning models; seed 17 rooms/five slots.
- [x] Write failing tests for price snapshots, per-person tickets, single admission, consecutive slots, whole-interval same-room availability, final-only cleaning, hold expiry/payment races, and delayed assignment conflicts.
- [x] Implement transactional ticket/room services without exposing internal inventory room as a guest assignment; extension requires confirmed payment, later-interval availability, and an explicit device rewrite task.
- [x] Add member/operations routes for purchase, availability, assignment, extension, room state, cleaning, maintenance, and conflicts.
- [x] Run domain tests and demonstrate invalid-slot and whole-interval-inventory rejection.

## Task 4 — Independent room dining

- [x] Add room QR, merchant/menu, food order/item and fulfillment models/routes; room context grants no member rights.
- [x] Test visitor browsing/payment, active-room creation, identical `room_use_id` payment validation, guest-change rejection, paid-undeliverable exceptions, and exactly-once queue entry.
- [x] Implement server-priced carts, balance/gateway payment, merchant accept/preparing/delivered transitions, and room-code disable/reprint metadata.
- [x] Run dining/payment regressions; introduce no automatic refund or cancellation policy.

## Task 5 — Wristbands, lockers, deposits, and device tasks

- [x] Add visit/card/binding/locker reservation/deposit/device task models and adapter-neutral transitions.
- [x] Test per-person ticket/paid-deposit checks, atomic locker reservation, idempotent issue callbacks, stable per-band refunds, clear-card failure after return, unknown outcomes, and duplicate result delivery.
- [x] Implement front-desk issue/return and finance-visible independent refunds; decouple return from clear-card compensation and never release unknown bindings.
- [x] Implement authenticated device poll/start/result endpoints and audit events with actor, before/after, reason, and request ID.
- [x] Run access/device Mock tests; label real SDK/NFC/lock integration pending.

## Task 6 — Operations API, reports, and documentation

- [x] Add role-scoped queries for orders/tickets, rooms, dining, principal/gift ledger, exceptions, device health, and audit.
- [ ] Implement daily totals separating principal, gift, business revenue, and unredeemed deposits; record reconciliation discrepancies. (Daily totals complete; formal channel reconciliation records remain pending.)
- [x] Add admin routes for holidays/prices, private price, recharge X+gift Y, menus, deposit amount, and room-code status without unapproved refund formulas.
- [x] Test authorization/reports; export OpenAPI notes and document pending decisions.

## Task 7 — Rebuild `frontend_1` and create `frontend_2`

- [x] Refactor `frontend_1` to dynamic server dates/prices, configured 29/49-yuan tickets, per-person quantities, no room-number selection, consecutive private slots, expected arrival, server balance/orders, recharge, and payment polling.
- [x] Remove its dining tab/pages, fixed dates/prices, membership levels/coupons, and client-authoritative totals; retain paper/deep-green styling and loading/empty/error states.
- [x] Build independent `frontend_2` with room-code entry, visible room number, public menu/cart, visitor WeChat option, explicit member login for balance, and order tracking.
- [x] Add integer-cent/date utilities and Node/static tests for app JSON, page files, independent AppID placeholders, and no secret-bearing MCP configs.
- [x] Run both validation suites; record remaining WeChat developer-tools and credential checks.

## Task 8 — Build `frontend_web`

- [x] Scaffold Vue 3/TypeScript with typed API, role auth store, guards, responsive design system, and state/table/modal components.
- [x] Implement ticket verification, assignment/room board/cleaning/maintenance, locker/card/deposit operations, and exception queues with reasons.
- [x] Implement merchant menu/fulfillment, finance ledger/refund/reconciliation, admin configuration/room codes, and daily reports.
- [x] Add Vitest tests for money, roles, API errors, and critical states; run typecheck, tests, and production build.
- [x] Run representative front-desk/merchant API/UI smoke checks without claiming real payment/hardware success.

## Task 9 — Device service, MySQL verification, and delivery

- [x] Implement the Python outbound worker, configured credential, resilient polling, adapter protocol, and explicit Mock results.
- [x] Test polling, unknown outcomes, duplicate delivery, offline recovery, and no automatic unknown retry; document Windows setup without invented DLL names/ports.
- [ ] Start isolated MySQL 8, migrate, run concurrent booking/locker/idempotency integration tests, and clean up only created resources. (Tests implemented; not executed because no isolated MySQL was available.)
- [x] Run all checks, inspect changes/secrets, and update README with commands and unverified items.
- [x] Perform final design-to-code review, resolve findings, and summarize scope, evidence, and pending confirmations.
