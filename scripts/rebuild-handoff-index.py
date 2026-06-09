#!/usr/bin/env python3
"""rebuild-handoff-index.py — regenerate the handoff README index from the source files.

Eliminates the bilateral race where two repos both hand-edit the README rows + the
file body and step on each other. The README's "Open handoffs" table is a GENERATED
artifact (between the START/END markers); the source of truth is the `Status:` header
inside each handoff file.

Behaviour, per inbox directory:

  1. Scan every `handoff-*.md` in the directory (NOT the `done/` subfolder).
  2. For each file, parse the status from the header.
  3. **Move terminal files** (`accepted` / `closed`) to `done/`. Done files are NOT
     listed in the README — the folder IS the archive (`ls done/` for history).
  4. For the remaining (non-terminal) files, rebuild the table sorted newest-first.
  5. Write between `<!-- HANDOFF-INDEX:START -->` … `<!-- HANDOFF-INDEX:END -->` in
     the directory's README.md.

Both sides invoke this before committing any change to the inbox. Idempotent — a
no-op when nothing changed. Wire it as a pre-commit hook + a `--check` CI gate.

Configure INBOXES for your repo (each tuple = (relative-path, provider-label)).

Usage:
  python3 scripts/rebuild-handoff-index.py            # rewrite all inboxes
  python3 scripts/rebuild-handoff-index.py --check    # exit 1 if dirty (CI/hook)
  python3 scripts/rebuild-handoff-index.py --dry-run  # show what would change
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

START_MARK = '<!-- HANDOFF-INDEX:START -->'
END_MARK = '<!-- HANDOFF-INDEX:END -->'

NON_TERMINAL = {'open', 'acknowledged', 'in-progress', 'answered'}
TERMINAL = {'accepted', 'closed'}

# One tuple per inbox this repo hosts: (relative-dir, provider-label).
# e.g. ('docs/handoffs/<provider-a>', '<provider-a>')
INBOXES = [
    ('docs/handoffs/<provider>', '<provider>'),
]

# Header formats accepted: "- **Status**: `open`" OR "Status: open"
STATUS_RE = re.compile(r'^(?:- \*\*Status\*\*:\s*`?|Status:\s*`?)([a-z-]+)', re.M)
TYPE_RE = re.compile(r'^(?:- \*\*Type\*\*:\s*|Type:\s*)(.+)$', re.M)
DATE_RE = re.compile(r'^(?:- \*\*(?:Date|Raised)\*\*:\s*|(?:Date|Raised):\s*)(\S+)', re.M)


def parse_handoff(path: Path) -> dict:
    """Pull status + type + date from the file header. Resolution narrative is
    intentionally NOT extracted — the reader clicks the file for details; the README
    index is a one-line-per-row lookup, not a copy of every handoff body."""
    text = path.read_text(encoding='utf-8')
    m = STATUS_RE.search(text)
    status = m.group(1) if m else 'open'
    t = TYPE_RE.search(text)
    type_label = t.group(1).strip() if t else '?'
    type_label = re.split(r'\s*[—.]\s+', type_label, maxsplit=1)[0]
    type_label = type_label.replace('|', '\\|')
    d = DATE_RE.search(text)
    date = d.group(1).strip() if d else '?'
    return {'status': status, 'type': type_label, 'date': date}


def render_table(rows: list[tuple[Path, dict]]) -> str:
    header = '| Handoff | Type | Status | Raised |\n|---|---|---|---|'
    lines = [header]
    if not rows:
        lines.append('| _(none — nothing currently open / answered)_ |  |  |  |')
    else:
        for path, info in rows:
            lines.append(
                f"| [{path.name}]({path.name}) | {info['type']} | "
                f"`{info['status']}` | {info['date']} |"
            )
    return '\n'.join(lines)


def archive_terminal(inbox: Path, dry_run: bool) -> list[Path]:
    """Move terminal-status files into `done/`. Returns the moved paths."""
    done = inbox / 'done'
    moved: list[Path] = []
    for path in sorted(inbox.glob('handoff-*.md')):
        info = parse_handoff(path)
        if info['status'] in TERMINAL:
            target = done / path.name
            if target.exists():
                continue  # already archived under the same name — skip to avoid clobber
            if dry_run:
                print(f"  WOULD archive: {path.name} (status={info['status']})")
            else:
                done.mkdir(exist_ok=True)
                shutil.move(str(path), str(target))
                print(f"  archived: {path.name} → done/")
            moved.append(path)
    return moved


def collect_open(inbox: Path) -> list[tuple[Path, dict]]:
    """Return non-terminal handoff files, newest-first by filename."""
    out: list[tuple[Path, dict]] = []
    for path in sorted(inbox.glob('handoff-*.md'), reverse=True):
        info = parse_handoff(path)
        if info['status'] in NON_TERMINAL:
            out.append((path, info))
    return out


def replace_block(text: str, block: str) -> str:
    pattern = re.compile(re.escape(START_MARK) + r'.*?' + re.escape(END_MARK), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(f"{START_MARK}\n\n{block}\n\n{END_MARK}", text)
    return text.rstrip() + f"\n\n## Open handoffs\n\n{START_MARK}\n\n{block}\n\n{END_MARK}\n"


def update_inbox(inbox: Path, dry_run: bool, check: bool) -> bool:
    """Returns True when README is unchanged (clean), False when it changed."""
    if not inbox.exists():
        return True
    print(f"=== {inbox} ===")
    archive_terminal(inbox, dry_run=dry_run)
    rows = collect_open(inbox)
    readme = inbox / 'README.md'
    if not readme.exists():
        print(f"  skip: no README.md in {inbox}")
        return True
    old = readme.read_text(encoding='utf-8')
    new = replace_block(old, render_table(rows))
    if new == old:
        print(f"  clean: {readme}")
        return True
    if dry_run or check:
        print(f"  DIRTY: {readme} would change")
        return False
    readme.write_text(new, encoding='utf-8')
    print(f"  wrote: {readme}")
    return True


def main() -> int:
    args = set(sys.argv[1:])
    dry_run = '--dry-run' in args
    check = '--check' in args
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    all_clean = True
    for rel, _side in INBOXES:
        clean = update_inbox(Path(rel), dry_run=dry_run, check=check)
        all_clean = all_clean and clean
    if check and not all_clean:
        print('\n✗ Handoff index is out of date. Run: python3 scripts/rebuild-handoff-index.py')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
