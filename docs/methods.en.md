# What the measurements establish

These are real local JVM observations using synthetic work. The site replays saved evidence, not a live JVM or an animated prediction. The source and raw recording workflow are available for local debugging.

## Version, environment and repeat design

The reference implementation requires Eclipse Temurin JDK 25.0.5+8 LTS. The build uses Apache Maven 3.9.11 via a checksum-pinned 3.3.4 only-script wrapper, with compiler plugin 3.14.1 and jar plugin 3.4.2. Runtime code depends only on the JDK. The complete suite was run three times in separate JVM processes with seed 20261113.

Each JSON record retains UTC capture time, JDK/runtime build, vendor, OS/version, architecture and logical processor count. Hostnames, usernames, environment variables, command lines, absolute paths and real personal identifiers are excluded. Logical processor count describes the machine, not exclusive CPU allocation. Repeat selection shows the individual observations; it does not imply a statistical confidence interval.

There is no warm-up isolation, CPU pinning, randomized policy order, fork calibration or GC control. JFR is enabled during all experiments. Sleep and OS scheduling affect timings. These results establish task lifecycle and count relationships under this workload, not production throughput or microbenchmark rankings. Use JMH separately for a defensible JVM microbenchmark.

## Pool counters and boundaries

The pool uses core = max = 2 platform threads and ArrayBlockingQueue capacity 3, with 18 numbered tasks and 60 ms synthetic sleep work. A 2 ms delay follows each execute() call. CallerRuns changes arrival times because execute() itself blocks while running rejected work. It can temporarily add work on the submitting thread beyond the two executor workers.

submitted is an offered task before execute(). started and completed cover both worker and caller execution. rejected counts only AbortPolicy-style rejection that drops the task. overflow counts rejection-handler entry; callerRuns counts successful caller execution. At quiescence, submitted = completed + rejected and started = completed. Every task is checked for exactly one terminal outcome. No silent discard policy is used.

Queue depth and executor active counts are samples at transitions. An active executor thread can still be completing its wrapper when completed is emitted, so that sample need not be zero at task completion. Curves connect event samples with step segments; no claim is made about unsampled states. p50/p95 use nearest-rank submitted-to-completed durations for successful executions only. Comparing policy latency alone would ignore rejected work and changed offered load.

## Timeout and cancellation boundaries

Each path has one actual worker and task 0. A latch confirms worker entry before get(timeout). The caller records waiter_returned only after catching TimeoutException; cancel_signal is recorded immediately before cancel(true). work_exited is emitted by the worker's finally block. These timestamps use System.nanoTime relative to each path's origin, with millisecond output rounded to microsecond precision; that formatting is not a claim of clock accuracy.

The worker's deadline is 240 ms from entry. The wait budget is 40 ms from get(), not submission. Scheduling and instrumentation affect the observed return time. Wait-only leaves the Future uncancelled. Both other paths call cancel(true); one deliberately swallows InterruptedException until its finite deadline, and one returns when interruption is caught. No unsafe Thread.stop is used. Future state and actual worker lifecycle are reported separately.

Pool termination is checked. Each wait is bounded, then graceful shutdown gets 3 seconds followed by a 1-second interrupt cleanup. The outer suite has a 25-second hard timeout. A failed shutdown fails the run; daemon workers prevent a broken experiment from pinning its owned JVM indefinitely.

## Retry failure model and accounting

Twelve original requests run sequentially. Even IDs get a seeded 0–2 failures; odd IDs get six failures in the saved records. The attempt after those failures succeeds. Each policy regenerates that same schedule with java.util.Random, seed 20261113. The model does not feed timing or queue load back into failure probability and does not claim to reproduce a cascading outage.

Each attempt has a real 2 ms local sleep. No-retry allows one attempt. Unbounded-policy retries until success without an attempt limit, guarded by a separate 2-second per-request safety watchdog that fails the experiment if reached. Finite failures keep the reference run terminable; permanent failure is not tested. Bounded-backoff allows three attempts total, waiting 5 then 10 ms plus 0–3 ms deterministic jitter seeded from request ID, attempt and seed.

requests = success + failed. attempts is every downstream invocation, including initial calls. Amplification = attempts / requests. backoffActualMs sums real measured sleeps, not planned delays or total request wall time. Successful unlimited retries spend more attempts; bounded retries intentionally expose failures after budget exhaustion. No idempotency, deduplication, concurrency, circuit breaker or distributed deadline claim is made.

## JFR export and privacy

The JVM starts an actual jdk.jfr.Recording, enables custom lab.TaskEvent transitions, ThreadSleep/ThreadPark with zero threshold, and ExecutionSample at 20 ms. It dumps a real local .jfr file and reads it through RecordingFile. A second JVM reads each file independently. Sample events are nondeterministic and may be absent in short, mostly sleeping workloads; custom transition and sleep events must exist.

The JSON publishes only file byte count, total events read, observed event span and counts for four allowlisted event types. It does not publish thread objects/names, stacks, environment events, class paths or raw JFR. The observed span covers enabled events, not a calibrated program runtime. No raw JFR or local tool archive is copied into the static site or public Git history.

## Authoritative references

- [ThreadPoolExecutor: queues and rejection policies](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html)
- [Future: timeout and cancellation contracts](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Future.html)
- [RecordingFile: reading actual JFR](https://docs.oracle.com/en/java/javase/25/docs/api/jdk.jfr/jdk/jfr/consumer/RecordingFile.html)
- [Pinned Temurin 25.0.5+8 release](https://github.com/adoptium/temurin25-binaries/releases/tag/jdk-25.0.5%2B8)
- [Apache Maven Wrapper](https://maven.apache.org/tools/wrapper/)
- [OpenJDK JMH](https://github.com/openjdk/jmh)
