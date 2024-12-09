from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
from typing import TextIO


@dataclass
class Hunk:
    del_start: int
    del_count: int
    add_start: int
    add_count: int
    del_lines: list[str] = field(default_factory=list)
    add_lines: list[str] = field(default_factory=list)

@dataclass
class File:
    name: str
    hunks: list[Hunk] = field(default_factory=list)
    del_linenos: set[int] = field(default_factory=set)
    add_linenos: set[int] = field(default_factory=set)

def gather_del(hunk: Hunk, del_offset: int):
    del_start = hunk.del_start - 1 + del_offset
    del_count = 0
    for ln, line in enumerate(hunk.del_lines, start=del_start + 1):
        if line[0] != ' ':
            yield ln - del_count
            del_count += 1

def update_mod(file: File):
    del_offset = 0
    for hunk in file.hunks:
        file.del_linenos.update(gather_del(hunk, del_offset))
        for ln, line in enumerate(hunk.add_lines, start=hunk.add_start):
            if line[0] != ' ':
                file.add_linenos.add(ln)
        del_offset += hunk.add_count - hunk.del_count

def gather_diff(f: TextIO) -> list[File]:
    files: list[File] = []
    for line in f:
        if re.match(r'(---|\+\+\+) (a/|b/|/dev/null)', line):
            continue # these interfere with regular add/del prefixes
        if m := re.match(r'diff --git a/.+? b/(.+)', line):
            files.append(File(m.group(1)))
        elif m := re.match(r'@@ -?(\d+),(\d+) \+?(\d+),(\d+) @@', line):
            files[-1].hunks.append(Hunk(int(m.group(1)), int(m.group(2)),
                                        int(m.group(3)), int(m.group(4))))
        elif line[0] == ' ':
            files[-1].hunks[-1].del_lines.append(line.rstrip('\n'))
            files[-1].hunks[-1].add_lines.append(line.rstrip('\n'))
        elif line[0] == '-':
            files[-1].hunks[-1].del_lines.append(line.rstrip('\n'))
        elif line[0] == '+':
            files[-1].hunks[-1].add_lines.append(line.rstrip('\n'))
    for file in files:
        update_mod(file)
    return files

def main(crossrefs_diff: str, files_diff: str):
    with open(files_diff, encoding='utf8') as f:
        files = {Path(file.name).name: file for file in gather_diff(f)}
    with open(crossrefs_diff, encoding='utf8') as f:
        crossrefs = gather_diff(f)[0]
    for hunk in crossrefs.hunks:
        for line in hunk.del_lines:
            if not (m := re.match(r'-([^:]+):(\d+): ([^:]+): ([^:]+):(\d+): ?(.*)', line)):
                continue
            file = files[m.group(1)]
            if int(m.group(2)) in file.add_linenos: # referrer line newly added
                print(f'::notice file={file.name},line={m.group(2)}::'
                      f'{m.group(3)} was modified in this diff. Make sure '
                      'your new reference to it here is up to date.')
            elif m.group(6): # referrer line stale
                print(f'::warning file={file.name},line={m.group(2)}::'
                      f'{m.group(3)} was modified in this diff. Please '
                      'consider updating this reference to it.')
        for line in hunk.add_lines:
            if not (m := re.match(r'\+([^:]+):(\d+): ([^:]+): ([^:]+):(\d+): ?(.*)', line)):
                continue
            file = files[m.group(1)]
            if not m.group(6): # new reference to invalid section
                print(f'::error file={file.name},line={m.group(2)}::'
                      f'{m.group(3)} is an invalid reference.')

if __name__ == '__main__':
    main(*sys.argv[1:])
