# Run it, then follow the task

Start with one question: after a request stops waiting, what work still owns a thread? Read the saved run first, then reproduce the exact experiment locally and change one parameter.

## 1. From zero to a checked recording

Use macOS or Linux on ARM64/x64, Python 3.9+, curl, tar and unzip. Windows users can use Linux in WSL. Node 18+ is needed only for reading-site tests. The experiments need no paid model, network downstream, cloud database or service account.

```sh
git clone https://github.com/lynnlee1229/java-runtime-lab.git
cd java-runtime-lab
python3 scripts/setup_jdk.py
python3 scripts/lab.py doctor
python3 scripts/lab.py build
python3 scripts/lab.py test --repeats 3
```

The setup script downloads Eclipse Temurin 25.0.5+8 LTS into ignored local/ and verifies its release SHA-256. It does not change system Java. The Maven 3.9.11 wrapper verifies its committed distribution checksum. First-time build dependencies require Internet access. The actual experiment is offline.

Each suite writes local/run-N.json and local/run-N.jfr. A separate JVM reads the real JFR again; a separate Python checker validates event lifecycles and counters. Three repeats must all pass. The suite has a 25-second subprocess hard timeout and pool shutdown deadlines. Failed runs never become a successful saved recording.

## 2. Queue saturation: follow task 5

Two workers run 60 ms synthetic sleep tasks, with a queue capacity of three. Eighteen submissions each have a 2 ms delay after execute() returns. A start barrier confirms the first two workers entered before the remaining submissions.

Open the pool scenario, compare Abort and CallerRuns, then filter the event table to one task. With Abort, a saturated execute() throws and the task is recorded as rejected. With CallerRuns, the submitting thread executes the task synchronously, delaying later arrivals. This is visible feedback, with work outside the executor's two worker slots.

Check submitted = completed + rejected, started = completed, and every task's terminal transition. Overflow is handler invocation; CallerRuns overflow is not counted as a dropped task. Queue/active curves are event-sampled observations. p50/p95 use nearest-rank latency from submission to completion, excluding rejected tasks.

## 3. Timeout: follow the worker after the waiter returns

The task signals that it has entered, then the caller waits with Future.get(40 ms). Work has an original finite 240 ms deadline. Compare three actual paths: waiting timeout only; cancel(true) with deliberate interruption swallowing; cancel(true) with a cooperative exit.

The red marker is the timeout handler's recorded waiter-return time. The amber marker is immediately before cancel(true). The green bar ends only when the worker records its finally block. All times share one monotonic clock within a path; each path starts its own clock.

A cancelled Future can be done while its task is still running. Filter task 0 and inspect interrupt_observed and work_exited. The noncooperative control always stops at its original finite deadline, keeping this experiment safe to rerun. A scheduler can delay the waiter, so 40 ms is the requested waiting budget, not an exact wall-clock timestamp.

## 4. Retry: count the downstream attempts

```sh
python3 scripts/lab.py run --seed 20261113 --requests 12 --failures 6
python3 scripts/verify.py local/run-1.json
```

The same failure schedule is regenerated independently for all three policies. Even request IDs fail 0–2 times using the seed; odd IDs fail the configured number of times and then recover. Every local attempt sleeps for 2 ms.

Compare no retry, retry-until-success with no attempt cap, and at most three attempts with 5/10 ms exponential backoff plus seeded 0–3 ms jitter. Count attempts/request, successes, failed original requests and actual backoff time. The unlimited policy has a separate 2-second per-request safety watchdog; reaching it fails the experiment. It is never described as proof that unlimited retries are safe against permanent failure.

## 5. Inspect JFR, change code, stop

Use the downloaded JDK's bin/jfr summary on local/run-1.jfr. Use bin/jfr print --events lab.TaskEvent to inspect local transitions. Open that file in a compatible JFR viewer if desired. Raw recordings can contain system metadata, so publish only the count summary already emitted to JSON.

The implementation lives in src/main/java/lab/RuntimeLab.java. Change one bounded workload or cancellation behavior, rebuild, then rerun all three repeats. Use assertions to distinguish a semantic change from timing variation. Do not edit records to match a desired conclusion.

```sh
python3 scripts/lab.py stop
```

Normal runs finish in the foreground, close their pools and leave no running service. Ctrl-C stops only the foreground run. The stop command explains this lifecycle and keeps local evidence. Preview servers are separate foreground commands; stop your own preview with Ctrl-C. Remove local/ only as an explicit cleanup when you no longer need the recordings and downloaded JDK.

## Read and share the evidence

The reading station loads three real saved JSON records. Switch repeat, scenario and policy; filter task events; export the run or selected case; copy a deep link. The same selected case survives switching languages. Files stay in your browser during export. The website neither starts Java nor observes a running machine.
