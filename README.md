# Java Runtime Lab

Real JVM experiments for bounded pools, timeout/cancellation and retry amplification. The bilingual reading site displays saved local measurements; it does not run a JVM in your browser.

- [English reading site](https://lynnlee1229.github.io/java-runtime-lab/en/)
- [中文阅读站](https://lynnlee1229.github.io/java-runtime-lab/zh/)
- [English guide](docs/guide.en.md) · [中文指南](docs/guide.zh.md)
- [Methods and scope](docs/methods.en.md) · [方法与范围](docs/methods.zh.md)
- [Validation](VALIDATION.md)

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

The exporter uses only allowlisted authored pages, assets and verified `records/run-{1,2,3}.json`; a SHA-256 manifest covers the output. It never copies `local/`, runtime sources, raw JFR, the JDK or Maven cache. The reading site's avatar/favicon reference the preserved assets on Lynn Lee's homepage. Deep links include run, scenario, policy and task. Run/case JSON exports contain actual recorded events.

To update saved evidence: run the exact pinned environment, independently verify each local JSON and JFR, copy only reviewed JSON into `records/`, rebuild and audit the export. Do not copy raw JFR: it can include machine metadata even when the visible event fields appear harmless.

## Visibility

This MIT companion is public because downloading, editing, debugging threads and inspecting JFR are necessary to the workflow. The personal homepage source repository remains private. All workloads and failures are synthetic local code. There are no real downstream services, personal records or internal company material.
