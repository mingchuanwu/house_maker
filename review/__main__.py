"""python -m house_maker.review {build DIR | collect [--inbox DIR] | summary [FILE...]}"""

import argparse
import glob
import json
import os
import pathlib
import shutil
import sys

from . import DEFAULT_INBOX
from .builder import build_review

FEEDBACK_DIR = pathlib.Path(__file__).resolve().parent / 'feedback'


def _summary(path: pathlib.Path) -> str:
    d = json.loads(path.read_text(encoding='utf-8'))
    lines = [f"== {path.name}  (run {d.get('run')}, exported {d.get('exported_at', '?')[:19]})"]
    for case, c in d.get('cases', {}).items():
        if c.get('notes'):
            lines.append(f"  [{case}] NOTE: {c['notes']}")
        if c.get('poses'):
            lines.append(f"  [{case}] moved panels: {', '.join(c['poses'])}")
        for i, p in enumerate(c.get('pins', []), 1):
            t = p.get('target', {})
            where = p.get('panel') or 'sheet'
            if t.get('type') in ('edge', 'finger'):
                where += f" · {t['edge']}" + (f" finger#{t['finger'] + 1}" if t.get('finger') is not None else '')
            elif t.get('type') == 'slot':
                where += f" · slot#{t['slot'] + 1}"
            lines.append(f"  [{case}] #{i} {p['category'].upper()}/{p['severity']}/{p['status']} @ {where}: {p['text']}")
    return '\n'.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='python -m house_maker.review')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build', help='build DIR/review.html from pytest --svg-dir output')
    b.add_argument('dir')
    c = sub.add_parser('collect', help='move downloaded house_review_*.json files into the repo and summarise')
    c.add_argument('--inbox', action='append', help=f'folder to scan (default {DEFAULT_INBOX} and ~/Downloads)')
    c.add_argument('--dest', default=str(FEEDBACK_DIR), help='where collected files are stored (default: review/feedback/)')
    s = sub.add_parser('summary', help='print collected feedback')
    s.add_argument('files', nargs='*')
    args = ap.parse_args(argv)

    if args.cmd == 'build':
        print(build_review(args.dir))
    elif args.cmd == 'collect':
        folders = args.inbox or [DEFAULT_INBOX, os.path.expanduser('~/Downloads')]
        dest_dir = pathlib.Path(args.dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = []
        for folder in folders:
            for f in sorted(glob.glob(os.path.join(os.path.expanduser(folder), 'house_review_*.json'))):
                dest = dest_dir / os.path.basename(f)
                shutil.move(f, dest)
                moved.append(dest)
        if not moved:
            print(f"No house_review_*.json found in: {', '.join(folders)}")
            return 1
        for dest in moved:
            print(_summary(dest))
    else:
        files = [pathlib.Path(f) for f in args.files] or sorted(FEEDBACK_DIR.glob('house_review_*.json'))
        for f in files:
            print(_summary(f))
    return 0


if __name__ == '__main__':
    sys.exit(main())
