# Java Runtime Lab

Real JVM experiments for bounded pools, timeout/cancellation, retry amplification and **virtual threads with finite downstream capacity**. The bilingual reading site displays saved local measurements; it does not run a JVM in your browser.

- [English reading site](https://lynnlee1229.github.io/java-runtime-lab/en/)
- [中文阅读站](https://lynnlee1229.github.io/java-runtime-lab/zh/)
- [English guide](docs/guide.en.md) · [中文指南](docs/guide.zh.md)
- [Methods and scope](docs/methods.en.md) · [方法与范围](docs/methods.zh.md)
- [Validation](VALIDATION.md)
- [Six-unit learning path · English](https://lynnlee1229.github.io/java-runtime-lab/en/curriculum/) · [六个可执行学习单元](https://lynnlee1229.github.io/java-runtime-lab/zh/curriculum/)
- [Virtual-thread evidence · English](https://lynnlee1229.github.io/java-runtime-lab/en/bulkhead/) · [虚拟线程实测](https://lynnlee1229.github.io/java-runtime-lab/zh/bulkhead/)
- [Structured course/resource registry](docs/curriculum.json) · [Depth audit](docs/AUDIT-2026-11-14.md)

## Learn by executing

After doctor → build, run one original exercise. These commands execute real local Java, check the complete recording, then focus on one question:

```sh
python3 scripts/learn.py measure
python3 scripts/learn.py pool
python3 scripts/learn.py capacity --requests 7 --capacity 2
python3 scripts/learn.py cancel
python3 scripts/learn.py retry
python3 scripts/learn.py evidence
python3 scripts/curriculum.py cancellation
```

The curriculum selects MIT **6.172, Performance Engineering of Software Systems, Fall 2018** (C), with exact lecture links, prerequisites and access conditions. Java-specific contracts come from JEP 444/491 and Java SE 25 docs. Each unit has a prediction, runnable command, observation and boundary. All exercises are original; no university assignment solutions are reproduced. Archived public reading is separate from enrollment, fees or certificates. `docs/curriculum.json` is searchable with the CLI and the bilingual reading site. Optional `python3 scripts/check_resources.py` anonymously rechecks official resource URLs and discards response bodies.

## Virtual threads and the downstream bulkhead

```sh
python3 scripts/lab.py bulkhead --requests 12 --capacity 3
python3 scripts/verify_bulkhead.py local/bulkhead-1.json
python3 scripts/learn.py capacity --record records/bulkhead-1.json
```

`BulkheadLab.java` uses `Executors.newVirtualThreadPerTaskExecutor()`, real `Semaphore` permits and bounded latch watchdogs. Three admission policies run the same finite burst: no bulkhead, wait for a permit, reject if full. The controlled first wave independently predicts peak occupancy N / C / C, maximum registered waiters 0 / N−C / 0 and rejections 0 / 0 / N−C. A capacity declaration is not a measured remote-server throughput limit. The unbounded control records excess occupancy without inventing server errors. The wait policy has no separate queue bound; only this offered burst is finite.

Two cancellation paths start C holders and one waiter. `Future.get(35 ms)` times out without releasing a slot; the waiter is cancelled first, then holder 0. Cooperative work exits and returns its permit. An interrupt-ignoring control keeps its permit until the finite gate releases. Future state and actual work exit are recorded separately. Every task has one terminal outcome and all permits must return; interrupted lifecycles are counted as cancelled even when the ignoring control later finishes its gated work.

The independent Python oracle replays every active/waiting transition and checks counts against N and C. A second JVM rereads the real JFR, including virtual starts/ends, parks, sleeps, custom transitions and explicit pinned/submit-failed counts. Scenario/transition counts must agree with JSON. The standard `test` command runs both old and new suites three times plus invalid-input and deliberately corrupted-evidence checks. The latter are negative verifier tests, never measurements.

The pin remains **Temurin 25.0.5+8 LTS**. JEP 444 delivered virtual threads in JDK 21; its historical synchronized pinning discussion is superseded by JEP 491 (delivered in JDK 24) for this runtime. Recorded pinning events can still exist and cannot be attributed to a cause from counts alone. Structured concurrency is optional preview reading only; no preview is enabled. There is no model call, API key, paid dependency or listening service.

## From zero

Prerequisites: macOS or Linux (ARM64/x64), Python 3.9+, curl, tar, unzip; Node 18+ only for the reading-site tests. Windows users can use Linux in WSL. No Docker, model API, database or persistent service is needed.

```sh
git clone https://github.com/lynnlee1229/java-runtime-lab.git
cd java-runtime-lab
python3 scripts/setup_jdk.py
python3 scripts/lab.py doctor
python3 scripts/lab.py build
python3 scripts/lab.py test --repeats 3
python3 scripts/lab.py stop
```

This pins Eclipse Temurin **25.0.5+8 LTS** and Maven **3.9.11**, with Apache Maven Wrapper 3.3.4 (only-script). The JDK archive is verified against the release SHA-256; the wrapper distribution has a committed SHA-256. JDK installation stays in ignored `local/`. To reuse this exact build elsewhere, set `JAVA_LAB_JDK` to its JDK home. Do not use a different patch version silently. Maven downloads build plugins on its first run; the Java experiments themselves use only JDK classes.

`build` creates `target/classes` and `target/java-runtime-lab-1.0.0.jar`. `test` runs each suite in a new JVM three times, reads each real JFR again in a separate JVM, independently checks JSON lifecycles, and verifies rejection of invalid parameters. Each suite has a 25-second hard timeout; each JFR reader has 10 seconds. A watchdog failure is a failed run. `subprocess.run` kills and reaps only its own child on timeout. Worker pools also have explicit graceful shutdown deadlines and daemon fallback, and no process-name kill is used.

## Run and inspect

```sh
python3 scripts/lab.py run --seed 20261113 --requests 12 --failures 6
python3 scripts/verify.py local/run-1.json
# Optional: use the installed JDK's bin/jfr summary local/run-1.jfr
# Use bin/jfr print --events lab.TaskEvent local/run-1.jfr for local event inspection.
```

`--failures` accepts 3–20, `--requests` 2–40; larger values fail fast. `--repeats` accepts 1–5 for tests. Every normal run exits and leaves no service. Ctrl-C interrupts only the owned foreground experiment. `stop` documents this lifecycle and preserves evidence; it does not delete data. `local/` holds raw JSON/JFR and downloaded tools and is ignored by Git. Delete that directory yourself only when you intend to remove local recordings and the local JDK.

`records/` contains three audited measurements captured on one macOS ARM64 machine. CI creates new measurements under `local/` and checks the committed reading records separately. Timings depend on scheduling, sleep accuracy, JFR and the machine. This is a lifecycle experiment, not a JMH microbenchmark or capacity estimate.

## Reading-site export

```sh
node --test scripts/test_site.mjs
python3 scripts/build_site.py
python3 scripts/check_site.py
python3 -m http.server 18912 --bind 127.0.0.1 --directory dist
# Open /java-runtime-lab/en/ or /java-runtime-lab/zh/.
# Ctrl-C stops this foreground preview server.
```

The exporter uses only allowlisted authored pages, assets and independently verified legacy/bulkhead reference JSON plus the curriculum registry and anonymous resource receipts; a SHA-256 manifest covers the output. It never copies `local/`, runtime sources, raw JFR, the JDK or Maven cache. The reading site's avatar/favicon reference the preserved assets on Lynn Lee's homepage. Deep links include run, scenario, policy and task. Run/case JSON exports contain actual recorded events.

To update saved evidence: run the exact pinned environment, independently verify each local JSON and JFR, copy only reviewed JSON into `records/`, rebuild and audit the export. Do not copy raw JFR: it can include machine metadata even when the visible event fields appear harmless.

## Visibility

This MIT companion is public because downloading, editing, debugging threads and inspecting JFR are necessary to the workflow. The personal homepage source repository remains private. All workloads and failures are synthetic local code. There are no real downstream services, personal records or internal company material.
