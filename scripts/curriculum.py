#!/usr/bin/env python3
"""Search the source-backed learning registry. --check validates cross-references offline."""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def validate(d):
    assert d['schemaVersion'] == 1 and len(d['courses']) in [1,2,3]
    resources = {r['id']:r for r in d['resources']}
    assert len(resources) == len(d['resources']) and len(d['units']) >= 6
    for course in d['courses']:
        for key in ['school','courseNumber','name','semester','prerequisites','publicMaterials','publicAccess','enrollmentAndFees','url','verifiedOn']:
            assert course[key], key
    for r in resources.values():
        assert r['url'].startswith('https://') and r['verifiedOn'] and r['status'] == 'published'
    for unit in d['units']:
        assert unit['resourceIds'] and all(k in resources for k in unit['resourceIds'])
        assert unit['command'].startswith('python3 scripts/learn.py '+unit['id'])
        for key in ['title','predict','observe','boundary']:
            assert set(unit[key]) == {'en','zh'} and all(unit[key].values())
    return d


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('query',nargs='?',default='')
    p.add_argument('--check',action='store_true')
    a=p.parse_args();d=validate(json.loads((ROOT/'docs/curriculum.json').read_text()))
    if a.check: print('PASS: course identity/access fields, six bilingual runnable units and resource references')
    else:
        hits=[{'category':kind,**row} for kind in ['courses','resources','units'] for row in d[kind]
              if a.query.casefold() in json.dumps(row,ensure_ascii=False).casefold()]
        print(json.dumps(hits,ensure_ascii=False,indent=2))
