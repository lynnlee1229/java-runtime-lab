"""Deliberately corrupt real evidence to verify that the independent oracle fails closed."""
import copy
import json
from pathlib import Path
import unittest
from verify_bulkhead import verify


class BulkheadOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((Path(__file__).resolve().parent.parent/'records/bulkhead-1.json').read_text())

    def test_actual_capture(self):
        verify(self.record)

    def corrupt(self, change):
        record = copy.deepcopy(self.record)
        change(record)
        with self.assertRaises(AssertionError):
            verify(record)

    def test_permit_leak(self):
        self.corrupt(lambda d: d['cases'][1].update(permitsRemaining=2))

    def test_invented_virtual_thread(self):
        self.corrupt(lambda d: next(e for e in d['cases'][0]['events'] if e['state']=='started').update(virtualThread=False))

    def test_false_cancel_means_work_exited(self):
        self.corrupt(lambda d: d['cases'][4]['cancelSnapshot'].update(targetWorkExited=True))

    def test_counter_snapshot_not_just_summary(self):
        self.corrupt(lambda d: next(e for e in d['cases'][1]['events'] if e['state']=='entered').update(active=9))

    def test_missing_actual_jfr_transition(self):
        self.corrupt(lambda d: d['jfr']['transitionCounts'].update({'queue/entered':11}))

    def test_absent_virtual_start_is_not_evidence(self):
        self.corrupt(lambda d: d['jfr']['eventCounts'].update({'jdk.VirtualThreadStart':0}))

    def test_forged_completed_and_rejected_closure(self):
        self.corrupt(lambda d: d['cases'][2].update(completed=12,rejected=0))


if __name__ == '__main__':
    unittest.main()
