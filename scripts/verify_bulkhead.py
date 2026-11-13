#!/usr/bin/env python3
"""Independent state-machine oracle. Expectations come from the workload contract, not saved results."""
import collections
import json
import sys


def verify(d):
    assert d['schemaVersion'] == 1 and d['recordType'] == 'measured-virtual-thread-bulkhead'
    assert d['assertionsPassed'] and d['runtime'] == '25.0.5+8-LTS'
    n, c = d['config']['requests'], d['config']['capacity']
    assert 1 <= c <= 6 and c < n <= 40
    expected = {
        'unbounded': (n, n, 0, 0, n, 0),
        'queue': (n, n, 0, 0, c, n-c),
        'reject': (n, c, n-c, 0, c, 0),
        'cancel-cooperative': (c+1, c-1, 0, 2, c, 1),
        'cancel-ignore': (c+1, c-1, 0, 2, c, 1),
    }
    assert len(d['cases']) == 5 and {x['policy'] for x in d['cases']} == set(expected)
    jfr_transitions = collections.Counter()
    for case in d['cases']:
        policy = case['policy']
        offered, completed, rejected, cancelled, peak, queue_peak = expected[policy]
        assert (case['submitted'], case['completed'], case['rejected'], case['cancelled'],
                case['maxActive'], case['maxQueued']) == expected[policy], policy
        assert case['virtualTasks'] == offered and case['terminated']
        assert case['finalActive'] == case['finalQueued'] == 0
        assert case['capacity'] == c
        assert case['permitsRemaining'] == (None if policy == 'unbounded' else c)
        assert case['overCapacityEntries'] == (n-c if policy == 'unbounded' else 0)
        assert case['entered'] == (c if policy.startswith('cancel-') or policy == 'reject' else n)
        active = queued = 0
        states = collections.defaultdict(list)
        active_ids, queue_ids, started_ids, terminal_ids = set(), set(), set(), set()
        last_ms = -1
        for seq, e in enumerate(case['events']):
            s, task = e['state'], e['task']
            assert e['seq'] == seq and e['ms'] >= last_ms >= -1
            last_ms = e['ms']
            assert task == -1 or 0 <= task < offered
            if s == 'started':
                assert e['virtualThread'] and task not in started_ids
                started_ids.add(task)
            if s == 'queued':
                assert task in started_ids and task not in queue_ids and task not in active_ids
                queue_ids.add(task); queued += 1
            if s == 'dequeued':
                assert task in queue_ids
                queue_ids.remove(task); queued -= 1
            if s == 'entered':
                assert task in started_ids and task not in active_ids and task not in queue_ids
                active_ids.add(task); active += 1
            if s == 'exited':
                assert task in active_ids
                active_ids.remove(task); active -= 1
            if s in {'completed', 'rejected', 'cancelled'}:
                assert task not in terminal_ids and task not in active_ids and task not in queue_ids
                terminal_ids.add(task)
            assert e['active'] == active == len(active_ids)
            assert e['queued'] == queued == len(queue_ids)
            assert 0 <= active <= peak and 0 <= queued <= queue_peak
            states[task].append(s)
            jfr_transitions[policy+'/'+s] += 1
        assert active == queued == 0 and len(started_ids) == len(terminal_ids) == offered
        assert max(e['active'] for e in case['events']) == peak
        assert max(e['queued'] for e in case['events']) == queue_peak
        counts = collections.Counter(e['state'] for e in case['events'])
        for name, number in [('submitted', offered), ('completed', completed), ('rejected', rejected), ('cancelled', cancelled)]:
            assert counts[name] == number
        for task in range(offered):
            lifecycle = states[task]
            assert lifecycle[:2] == ['submitted', 'started']
            terminal = [s for s in lifecycle if s in {'completed', 'rejected', 'cancelled'}]
            assert len(terminal) == 1
            assert lifecycle.count('entered') == lifecycle.count('exited') <= 1
            if terminal[0] == 'completed': assert 'exited' in lifecycle
            if terminal[0] == 'rejected': assert lifecycle == ['submitted', 'started', 'rejected']
            if terminal[0] == 'cancelled': assert 'interrupt_observed' in lifecycle
        if policy.startswith('cancel-'):
            snap = case['cancelSnapshot']
            assert case['waiterTimedOut'] and case['queuedCancelAccepted'] and case['activeCancelAccepted']
            assert snap['active'] == (c if policy == 'cancel-ignore' else c-1) and snap['queued'] == 0
            assert snap['targetFutureCancelled'] and snap['targetWorkExited'] == (policy == 'cancel-cooperative')
            assert counts['waiter_timeout'] == 1 and counts['cancel_signal'] == counts['cancel_result'] == 2
            assert states[c].count('entered') == 0, 'queued cancellation consumed a downstream slot'
            assert states[0].index('waiter_timeout') < states[0].index('cancel_signal')
        else:
            snap = case['heldSnapshot']
            assert (snap['active'], snap['queued'], snap['rejected']) == (peak, queue_peak, rejected)
    jfr = d['jfr']
    assert jfr['readable'] and jfr['bytes'] > 0
    assert jfr['transitionCounts'] == dict(jfr_transitions), 'actual JFR transitions differ from JSON'
    counts = jfr['eventCounts']
    assert counts['lab.BulkheadEvent'] == sum(jfr_transitions.values())
    total_tasks = sum(x['submitted'] for x in d['cases'])
    assert counts['jdk.VirtualThreadStart'] >= total_tasks and counts['jdk.VirtualThreadEnd'] >= total_tasks
    assert counts['jdk.ThreadPark'] > 0 and counts['jdk.ThreadSleep'] > 0
    assert set(counts) == set(jfr['enabledEvents'])
    # Pinned/SubmitFailed counts are observations. Neither zero nor nonzero is invented as a pass condition.
    return d


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        verify(json.load(open(filename)))
        print('PASS independent bulkhead state-machine and JFR oracle:', filename)
