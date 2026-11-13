#!/usr/bin/env python3
import collections,json,sys

def verify(d):
    assert d['recordType']=='measured-local-jvm' and d['assertionsPassed']
    for p in d['pools']:
        events=p['events'];states=collections.Counter(e['state'] for e in events)
        assert states['submitted']==p['submitted']==p['completed']+p['rejected']
        assert states['started']==p['started']==states['completed']==p['completed']
        assert states['rejected']==p['rejected'] and states['caller_runs']==p['callerRuns']
        assert p['terminated'] and p['overflow']>0
        assert max(e.get('queue',0) for e in events)<=d['config']['queueCapacity']
        for task in range(p['submitted']):
            lifecycle=[e['state'] for e in events if e['task']==task]
            assert lifecycle[0]=='submitted'
            assert (lifecycle.count('completed'),lifecycle.count('rejected')) in [(1,0),(0,1)]
            if 'completed' in lifecycle:assert lifecycle.index('started')<lifecycle.index('completed')
    modes={p['mode']:p for p in d['cancellation']}
    for c in modes.values():
        assert c['terminated'] and c['workExitedMs']>=c['waiterReturnedMs']
        assert sum(e['state']=='work_exited' for e in c['events'])==1
    assert modes['wait-only']['workAfterWaiterMs']>120 and not modes['wait-only']['futureCancelled']
    assert modes['ignore-interrupt']['workAfterWaiterMs']>120 and modes['ignore-interrupt']['interruptObserved']
    assert modes['cooperative']['interruptObserved'] and modes['cooperative']['outcome']=='interrupted'
    schedules=[]
    for r in d['retries']:
        states=collections.Counter(e['state'] for e in r['events']);schedules.append(r['failureSchedule'])
        assert states['request']==r['requests']==r['success']+r['failed']
        assert states['attempt']==r['attempts'] and states['success']==r['success'] and states['request_failed']==r['failed']
        if r['policy']=='bounded-backoff':assert r['attempts']<=3*r['requests'] and r['failed']>0
        if r['policy']=='unbounded-policy':assert r['failed']==0
    assert all(s==schedules[0] for s in schedules)
    assert d['jfr']['allowedEventCounts']['lab.TaskEvent']==sum(len(s['events']) for s in d['pools']+d['cancellation']+d['retries'])
    assert d['jfr']['readable'] and d['jfr']['allowedEventCounts']['lab.TaskEvent']>0 and d['jfr']['allowedEventCounts']['jdk.ThreadSleep']>0

if __name__=='__main__':
    for f in sys.argv[1:]:verify(json.load(open(f)));print('PASS independent lifecycle verification:',f)
