# Java Runtime Lab 1.0 · validation

Date: 2026-11-13, Asia/Shanghai. Workloads are synthetic. The site displays saved actual JVM recordings, not current machine state.

## Runtime evidence

- Fixed Eclipse Temurin 25.0.5+8 LTS, Maven 3.9.11 via checksum-pinned Apache Maven Wrapper 3.3.4. Runtime has no third-party dependencies.
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

The owner workspace ops/java-runtime-lab-release.json records source/output commits, CI/Pages results, final public checks and evidence hashes after deployment. A source push alone is not treated as successful publication.

## Reproduce

Follow README.md or docs/guide.en.md (docs/guide.zh.md). Run doctor → build → test, then node scripts/test_site.mjs, build_site.py and check_site.py. JFR and timing semantics are documented in docs/methods.en.md and docs/methods.zh.md. These are lifecycle observations with JFR enabled; no production-capacity or JMH claim is made.
