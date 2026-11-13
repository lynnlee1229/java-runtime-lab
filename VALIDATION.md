# Java Runtime Lab 1.1 · current validation

Date: 2026-11-14, Asia/Shanghai. The earlier 1.0 release evidence is retained below as history. This iteration keeps its source and reference captures, and adds a real virtual-thread/downstream-resource exercise.

## What the new capability actually establishes

- With N=12 real virtual tasks and C=3 declared downstream slots, all three committed captures observed unbounded peak occupancy 12, queue-policy occupancy 3 with 9 registered waiters, and reject-policy 3 completions with 9 rejections. The latch protocol forces that first wave before releasing work. This demonstrates resource admission, not a throughput advantage.
- Each cancellation path starts three holders plus one queued task. The queued cancellation never entered downstream. Cooperative cancellation reduced occupied slots to 2 before the snapshot. The interrupt-ignoring holder had a cancelled Future but still occupied its slot (3 active); actual work exit later returned it. All terminal counts close and all 3 permits return.
- An independent Python state-machine oracle reconstructed task sets and resource counters; it checked every snapshot and terminal outcome against formulas from N/C. The implementation's assertionsPassed flag alone is insufficient. Invalid configurations fail. Deliberately corrupted records test rejection of permit leaks, forged virtual thread observations, false work-exit claims, resource trace contradictions, missing JFR transitions and forged terminal closure.
- All three real JFRs were read again by separate JVMs. Every recording has 44 actual virtual starts, 44 ends and 239 custom transitions; each scenario/transition count matches JSON. Pinned-event observations are 3, 2, 0. Counts are retained rather than forced to zero. No cause, synchronized pinning or universal absence is inferred from those numbers. Raw JFR remains ignored/local.
- Executed the documented doctor → build → test --repeats 3. Both the full original suite and new suite passed. Also executed all six learn.py entry points and the exact documented capacity --requests 7 --capacity 2 command, producing peak 7/2/2, five waiters and five rejections as predicted. A second JVM reread each new JFR. Evidence and source hashes are in records/bulkhead-validation.json.

## Learning and delivery checks

- Audited four gaps before choosing the virtual-thread resource boundary. docs/AUDIT-2026-11-14.md records the decision and preserved baseline.
- The structured registry selects MIT 6.172, Performance Engineering of Software Systems, Fall 2018 (C), with exact course identity, prerequisites, access/enrollment distinction and four lecture links. Java SE 25/JEP sources and one specifically identified Vanderbilt 2020 interrupt lecture supplement Java behavior; the latter is not assigned an invented semester or presented as a new 2026 offering. Six original exercises map sources → prediction → actual command → evidence → limitation.
- All 14 source URLs were anonymously fetched, with capture dates, byte counts and SHA-256 receipts in records/resource-checks.json; response bodies were discarded. JEP 444/491 were read from the official source. The installed JDK and official Temurin release were checked, and the existing 25.0.5+8 LTS pin was retained. No preview or paid/model API is used.
- Original browser checks remain. New display-contract checks reject empty/missing records, forged thread observations, impossible resource snapshots, false cancellation conclusions and mismatched actual JFR. Curriculum references and six bilingual executable units validate offline.
- Real browser preview: queue/reject selection; ignored-interrupt holder; task 0 filtering; run 3 selection; EN→ZH state preservation; Chinese curriculum search; complete-case JSON download parsed and matched to actual run 1 (all 28 events despite 9 visible task events). Both new pages at viewport 390 have document/body width 390. No browser console errors were observed. Injecting an empty record hid all results with an evidence-unavailable error; restoration recovered the actual viewer.
- The exporter audits legacy and new records and exports only authored assets, registry/anonymous receipts and verified synthetic JSON. Complete manifest, local links and privacy checks pass. Source visibility remains PUBLIC for this companion and PRIVATE for the homepage source.

Deployment 1.1: private homepage source 02c1864 passed CI; output 0aad525 was built by Pages at 2026-11-13T19:02:18Z. Anonymous HTTP matched all 26 manifest entries and the manifest. Public browser checks passed for both new views, a complete run-3 download matching the audited capture, six learning commands, search, language/deep-link state, sharing and viewport 390. The original CallerRuns view still completed all 18 tasks. The release changed only the Java static prefix; 573 other source files and 526 other output files remained byte-identical. Existing foreign uncommitted changes were preserved and were not staged or deployed. Temporary source responses, downloads, duplicate runs, the owned preview and isolated private build were cleaned; pinned dependencies, sanitized evidence and local raw JFRs remain. See release.json for receipts.

---

# Java Runtime Lab 1.0 · validation

Date: 2026-11-13, Asia/Shanghai. Workloads are synthetic. The site displays saved actual JVM recordings, not current machine state.

## Runtime evidence

- The public companion CI also ran the complete suite on a fresh Ubuntu runner, independently of the reference macOS captures.
- Fixed Eclipse Temurin 25.0.5+8 LTS, Maven 3.9.11 via checksum-pinned Apache Maven Wrapper 3.3.4. Runtime has no third-party dependencies.
- Executed the documented JDK setup entry: downloaded the pinned archive, verified official SHA-256 and extracted only under local/. Finite retry handles transient download/TLS errors.
- Built the public companion and executed three complete suites in separate JVMs; repeated the suite after final runtime-source cleanup. All task lifecycle assertions, counter closures and worker-pool termination checks passed.
- Each suite covers two bounded-pool rejection policies, three wait/cancel/interruption paths and three retry policies. Each actual JFR was independently read again in another JVM. Each JSON was checked by an independent Python verifier, including per-task terminal outcomes and equality of recorded transition count with JFR lab.TaskEvent count.
- Final saved records: all three Abort runs completed 5 / rejected 13 of 18 tasks; CallerRuns completed 18 / rejected 0 with 5 caller executions. Queue capacity 3 was never exceeded.
- Final wait-only work continued 196.720–202.118 ms after waiter return; interrupt-ignoring control 195.337–200.016 ms; cooperative interrupt exit 0.095–1.033 ms. Requested wait budget was 40 ms, finite work budget 240 ms. These ranges are three machine observations, not accuracy guarantees.
- Each seeded 12-request retry comparison observed 12 attempts and 1 success without retry; 55 attempts and 12 successes under retry-until-success; 31 attempts, 6 successes and 6 failed requests under the three-attempt budget with backoff. All policies regenerated the same failure schedule.
- Every final JFR had 383 actual lab.TaskEvent transitions, ThreadSleep and ThreadPark events, plus 1–2 ExecutionSample events. Raw JFR remains ignored under local/reference-jfr/ and is not exported. Public data contains only the audited event-count summary.
- Invalid retry configuration and unknown CLI option fail with nonzero status. Runs have a 25-second hard timeout, separate JFR readers 10 seconds, finite request watchdogs and pool shutdown deadlines. Only owned child processes can be killed; no process-name kill is used.

## Reading site and distribution

- Six localized content pages plus English-default redirect, canonical/hreflang metadata, sitemap, no external JS dependencies, complete SHA-256 export manifest.
- Nine browser-data/deep-link/curve unit tests passed, including empty/failed records, bad counters, missing events and backwards time. Static export, links, manifest and privacy checks passed.
- Real Chrome control checks: Abort/CallerRuns switch, task 5 lifecycle filter, cancellation view, run 3 selection, noncooperative interrupt path, retry budget comparison, EN→ZH switch preserving selected state, guide navigation, share-button success state, run JSON and selected-case JSON downloads.
- Actual downloaded JSON files were independently parsed and checked against the selected source recording. Case export matched the complete ignore-interrupt scenario, not only the visible filtered rows.
- Injected an empty record into the disposable preview export: the browser displayed an evidence-unavailable error and hid all measurement results. Restored the generated file and verified recovery. No fabricated fallback curves.
- Chinese reading station at 390 CSS pixels: document/body scrollWidth 390. Table scrolling stays inside its container. Desktop/mobile evidence is retained in the owner workspace ops directory; release metadata provides screenshot hashes.
- Public companion contains only its own audited code, guides and synthetic records. Homepage source remains PRIVATE. No raw JFR, hostnames, absolute machine paths, personal contacts, credentials, imported company material, paid APIs, cloud databases or persistent services are included.

## Deployment evidence

GitHub Pages built output d5ea7880395ba98809415fb4e00320a815aaecc8 successfully at 2026-11-13T12:15:10Z. Homepage source f124c7a608d788e94767529bc5f2c8d857807a6a passed CI. Anonymous HTTP checks matched all 14 exported file hashes and the complete manifest, both language discovery cards and robots sitemap. Existing Agent, GeoData, Streaming and Search/Recommendation/Ads entries remained reachable. Public browser checks covered timeout/retry controls, the EN/ZH transition, a real JSON download matching the audited record, mobile scrollWidth 390 at viewport 390, and navigation from the homepage directory card.

See release.json for public evidence. The owner workspace ops/java-runtime-lab-release.json also retains raw local JFR and screenshot hashes. Raw JFR remains local. A source push alone is not treated as successful publication.

## Reproduce

Follow README.md or docs/guide.en.md (docs/guide.zh.md). Run doctor → build → test, then node scripts/test_site.mjs, build_site.py and check_site.py. JFR and timing semantics are documented in docs/methods.en.md and docs/methods.zh.md. These are lifecycle observations with JFR enabled; no production-capacity or JMH claim is made.
