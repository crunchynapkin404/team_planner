# Orchestrator Findings and Production Roadmap

This document captures the current state of the shift orchestrator, key findings from a deep code inspection, alignment with the Shift Scheduling Specification, and a step‑by‑step roadmap to make it production‑ready.

## Executive summary
- Two parallel orchestrator designs and two fairness systems create complexity and drift.
- UnifiedOrchestrator bridges the gap but forces special cases (notably for waakdienst).
- Advanced fairness calculators are partially used (V2 + waakdienst) while incidents/standby use a simpler fairness model.
- Leave/availability rules at the model layer are powerful (daytime‑only vs full‑unavailable), but constraint usage isn’t fully consistent across orchestrators.
- V2 API endpoints are in place and rely on the unified layer; coverage/availability queries need stronger department scoping.
- Reassignment logic exists and supports split coverage for incidents; it should be consistently integrated post‑plan.

## Architecture map (as‑is)
- Backend stack: Django, DRF (+ DRF Spectacular), management commands.
- Orchestrators (team_planner/orchestrators):
  - base.py: BaseOrchestrator with `generate_schedule`/`apply_schedule`; uses fairness.py + constraints.py. Used by `incidents.py`, `incidents_standby.py`.
  - base_orchestrator.py: Alternative BaseOrchestrator with `generate_assignments` (day‑by‑day, constraint‑first); uses fairness_calculators.py. Used by `waakdienst.py`.
  - unified.py: UnifiedOrchestrator/ShiftOrchestrator that coordinates per‑type orchestrators and persistence.
  - fairness.py: Simple per‑type fairness calculators (ratios).
  - fairness_calculators.py: Advanced fairness (weighted hours, historical decay, availability, comprehensive views).
  - constraints.py: Base + per‑type constraint checkers. Incidents favors permissive handling of recurring leave to enable reassignment/splitting.
  - reassignment.py: Detects recurring/approved leave and double‑assignment conflicts, resolves via split coverage (incidents) or next‑best.
  - models.py: OrchestrationRun, OrchestrationResult, OrchestrationConstraint for audit/tracking.
- APIs and routing:
  - orchestrators/api_v2.py: V2 endpoints calling ShiftOrchestrator (unified). Health/metrics/coverage/availability included.
  - orchestrators/api.py: Legacy endpoints (v1) also exist and operate through UnifiedOrchestrator.
  - config/api_router.py: Wires v2 routes under `/api/orchestrator/*` and status endpoints.
- Models referenced:
  - shifts/models.py: ShiftType (incidents, incidents_standby, waakdienst), ShiftTemplate, Shift (+ metadata), FairnessScore.
  - employees/models.py: EmployeeProfile (+ availability toggles), EmployeeSkill, RecurringLeavePattern.
  - leaves/models.py: LeaveType (conflict_handling), LeaveRequest (effective time windows, conflict detection), Holiday.
- Commands: management/commands include orchestrator runners; some map to the older API model.

## Key findings
1) Dual base orchestrators with incompatible method contracts
- base.py exposes `generate_schedule`/`apply_schedule`; base_orchestrator.py exposes `generate_assignments` and a different lifecycle.
- Result: UnifiedOrchestrator contains special logic for waakdienst.

2) Two fairness systems in active use
- incidents/incidents_standby use fairness.py (simple ratios).
- waakdienst + V2 (and legacy api.py paths) rely on fairness_calculators.py (advanced, availability‑aware).
- Result: Different selection behavior and fairness reporting across shift types.

3) Waakdienst has duplicated helper logic
- Week start (Wednesday 17:00 to next Wednesday 08:00) is computed in multiple places in `waakdienst.py`.

4) Constraint/availability handling is uneven
- Model‑level rules are rich: `LeaveType.conflict_handling` supports DAYTIME_ONLY to allow waakdienst during daytime leave.
- Incidents recurring leave is handled permissively and corrected by reassignment/split coverage; this is sensible but should be a documented policy used consistently wherever conflicts are evaluated.

5) API V2 is the right surface, but queries need scoping
- Coverage/availability endpoints compute over `Shift` and `ShiftTemplate.shift_type`; department/team scoping is recognized but not strictly filtered yet.

6) Reassignment module is strong but not uniformly leveraged
- Detects: recurring leave, approved leave, double assignment (incidents vs incidents_standby).
- Strategies: split coverage for incidents, next‑best reassignment fallback; fairness‑aware sorting is supported.
- Result: Good foundation; ensure it runs post‑plan and its audit entries (OrchestrationConstraint) are recorded for every conflict.

## Alignment with SHIFT_SCHEDULING_SPEC
- Incidents (Primary): Mon–Fri 08:00‑17:00; same engineer gets all 5 daily shifts each week; weekly rotation starts Monday. Current incidents orchestrator follows this pattern and supports split coverage when recurring leave creates partial conflicts.
- Incidents‑Standby (Secondary): Same weekday hours; optional; same engineer per business week; separate fairness/rotation counter from Incidents. Current module mirrors incidents with separate fairness tracking.
- Waakdienst (On‑Call): Wednesday 17:00 to next Wednesday 08:00; same engineer covers 7 daily blocks: weeknight 17:00‑08:00 (15h) and 24h weekend days; handover on Wednesday between 08:00‑17:00. Current `waakdienst.py` uses the Wednesday‑to‑Wednesday cadence and generates proper evening/weekend coverage.
- No time gaps: Incidents covers weekdays 08:00‑17:00; Waakdienst covers everything else (weeknights/weekends). Leave type DAYTIME_ONLY explicitly keeps waakdienst available during daytime leave.

Conclusion: The current logic can implement the spec, but inconsistency across bases/fairness and duplicated logic increase risk and maintenance cost.

## Risks and gaps
- Drift between orchestrator bases leads to hidden behavior differences and special‑case maintenance.
- Mixed fairness behavior undermines predictability (selection and reporting).
- Department/team scoping in analysis endpoints can cause misleading coverage/availability views.
- Duplicate waakdienst helpers risk divergence during fixes.
- Legacy API paths remain; unclear deprecation can confuse clients.
- Test coverage for orchestration rules (esp. handover Wednesday and split coverage) is likely insufficient.

## Target architecture (to‑be)
- One orchestrator base and contract:
  - Standardize on a single interface (recommended: `generate_schedule` + `apply_schedule`), returning a uniform assignment schema used across all shift types.
  - Add an adapter layer (temporary) for waakdienst while migrating its logic to the unified base.
- One fairness system:
  - Adopt advanced `fairness_calculators.py` end‑to‑end; provide a thin factory/adaptor so incidents/standby call the same API.
- UnifiedOrchestrator simplified:
  - Remove special‑casing once all shift types share the same base/fairness.
- Consistent constraints:
  - Centralize checks so both incidents and waakdienst honor model‑level rules (LeaveType.conflict_handling, RecurringLeavePattern) and the same constraint checker strategy.
- API V2 only:
  - Keep v2 as the supported surface; lock down department/team filtering in coverage/availability; mark v1 as deprecated with a timed removal plan.

## Production‑ready roadmap

Phase 0 — Stabilization and alignment (1–2 days)
- Freeze orchestrator public contracts; document desired assignment schema and lifecycle.
- Catalog all call sites (V2 endpoints, commands, management tasks). 
- Add feature flag: `ORCHESTRATOR_UNIFIED_BASE=true` to gate new path.

Exit criteria:
- Specs and contracts published; toggled path deployable without behavior change.

Phase 1 — Unify base interface (3–5 days)
- Create a single BaseOrchestrator (keep name in `base.py`) with the canonical methods.
- Add a waakdienst adapter that wraps current logic into `generate_schedule` output shape.
- Remove duplicated helpers from `waakdienst.py`; move week start/time window utilities to a shared module (e.g., `orchestrators/utils/time_windows.py`).

Exit criteria:
- Incidents, incidents‑standby, and waakdienst all consumed via the same base API in UnifiedOrchestrator.
- No behavior regression in basic smoke tests.

Phase 2 — Consolidate fairness (3–5 days)
- Introduce a new `FairnessCalculatorFactory` that returns advanced calculators for all shift types.
- Update incidents/incidents‑standby to use advanced fairness; preserve prior outputs via adapter if needed.
- Update UnifiedOrchestrator metrics to read from the advanced calculator consistently.

Exit criteria:
- Single fairness system in use; parity on selection and scoring confirmed by tests.

Phase 3 — Constraints and reassignment coherence (3–5 days)
- Centralize constraint evaluation so both incidents and waakdienst use the same policy surface.
- Ensure recurring leave is uniformly handled: permissive plan generation + reassignment pass.
- Always run `ShiftReassignmentManager` post‑plan; store OrchestrationConstraint audit events.

Exit criteria:
- Deterministic constraint/resolution flow; conflict audit visible in OrchestrationRun detail.

Phase 4 — API hardening and scoping (2–3 days)
- Tighten department/team scoping in V2 coverage/availability queries (add joins or team relation fields on `Shift`).
- Add pagination and input validation where missing; enrich health/metrics with timings.
- Mark legacy v1 endpoints as deprecated; add deprecation headers and docs.

Exit criteria:
- V2 endpoints pass scoping tests; v1 usage tracked and trending down.

Phase 5 — Observability, resilience, and rollout (3–4 days)
- Instrument orchestrations: timings, fairness distribution histograms, reassignment counters, constraint violations.
- Add idempotency for apply path; protect against duplicate shift creation; double‑submit safe.
- Background task support (celery) for long runs; store partial progress and errors.

Exit criteria:
- Metrics visible on dashboards; idempotent apply; async pathway validated.

Phase 6 — Tests, documentation, and deprecation removal (3–5 days)
- Unit tests: time windows, rotation boundaries, fairness selections, reassignment strategies, leave conflict permutations.
- Integration tests: end‑to‑end weekly runs per spec; no gaps, correct overlaps (Wednesday handover).
- Documentation: update README/DEV docs; migration notes; finalize v1 removal window; train on-call.

Exit criteria:
- Test suite green with coverage targets; v1 removal scheduled; runbooks updated.

## Quality gates
- Build: linters/type checks pass; no Django migration conflicts.
- Tests: 
  - Unit > 80% coverage for orchestrator modules.
  - Integration: spec conformance tests pass (no coverage gaps, correct Wednesday handover, no double assignments).
- Runtime: 
  - Canary runs match historical fairness distribution within tolerance.
  - Observability: metrics emitted and dashboards populated.

## Minimal test plan (additive)
- Incidents weekly assignment:
  - Same engineer receives Mon–Fri 08:00–17:00 shifts; rotation advances weekly.
  - Split coverage when recurring leave conflicts with one or more weekdays; confirm reassignment only covers conflicted days.
- Incidents‑Standby:
  - Mirrors incidents; track separate fairness counters; verify no double‑assignment with incidents for same employee.
- Waakdienst weekly cadence:
  - Wednesday 17:00 start to next Wednesday 08:00; generate 7 daily blocks with correct durations (weeknights: 15h, weekend days: 24h).
  - Wednesday handover overlap permitted during 08:00–17:00 (incidents hours) without gaps.
- Leave handling:
  - DAYTIME_ONLY leave does not block waakdienst; FULL_UNAVAILABLE blocks all.
  - Approved leave forces reassignment; audit entries created.
- Department scoping:
  - Coverage/availability endpoints return only relevant shifts/employees by department/team.
- Idempotent apply:
  - Re‑applying a preview plan doesn’t duplicate shifts (unique constraints honored; idempotency key tested).

## Open questions (to resolve early)
- How are teams linked to shifts today (explicit relation vs derivation via templates)? If implicit, add a team field to `Shift` for accurate scoping.
- Confirm which frontend endpoints are in active use (V2 only vs any v1 fallback) to plan deprecation safely.
- Define fairness weighting/decay parameters for production and document governance for adjustments.

## Appendix — Spec recap
- Incidents & Incidents‑Standby: Mon–Fri 08:00–17:00; same engineer per week; standby optional; separate fairness trackers.
- Waakdienst: Wed 17:00 → Wed 08:00; same engineer per week; 7 blocks covering all non‑business hours + weekends; Wednesday handover window.
- No time gaps; Europe/Amsterdam timezone.

## Status update (2025-09-10)

- Implemented shared time window utilities in `team_planner/orchestrators/utils/time_windows.py` and migrated Waakdienst/Incidents to use them (tz-aware, Europe/Amsterdam).
- Fixed structural/indentation issues in `team_planner/orchestrators/waakdienst.py`; restored week-based selection and availability checks using the shared utilities.
- Added integration test `team_planner/orchestrators/tests/test_waakdienst_integration.py` validating:
  - Single engineer covers a full Wed 17:00 → next Wed 08:00 week (7 blocks).
  - First start/last end align with computed week bounds.
  - Durations pattern [15, 15, 15, 24, 24, 15, 15].
- Hardened API v2 endpoints (auth behavior, payload shapes, shift-type aliases, metrics keys, malformed JSON handling) and aligned the Users API detail route to `username`.
- Full test suite result: 123 passed, 1 skipped. Non-fatal sqlite concurrency warnings persist only in the threaded API perf test.

Next steps (short):
- Silence or adapt the sqlite warning in the concurrent-requests test (skip on sqlite or use file-based WAL).
- Consolidate fairness systems behind a factory and migrate incidents/standby to advanced calculators.
- Start Phase 1 of the roadmap: unify the base orchestrator interface and add a temporary adapter for Waakdienst.
