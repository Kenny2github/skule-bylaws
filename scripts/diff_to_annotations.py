from dataclasses import dataclass, field
from glob import glob
import io
from itertools import permutations, zip_longest
from pathlib import Path
import re
import sys
from typing import LiteralString, TextIO

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
    add_linenos: set[int] = field(default_factory=set)

def update_mod(file: File):
    for hunk in file.hunks:
        for ln, line in enumerate(hunk.add_lines, start=hunk.add_start):
            if line[0] != ' ':
                file.add_linenos.add(ln)

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

def gather_crossrefs_diff(file: File) -> list[tuple[str, int, str, str, LiteralString]]:
    added: dict[tuple[str, int, str], tuple[str, str]] = {}
    deled: dict[tuple[str, int, str], tuple[str, str]] = {}
    for hunk in file.hunks:
        for line in hunk.add_lines:
            if not (m := re.match(r'\+([^:]+):(\d+): ([^:]+): ([^:]+:\d+): ?(.*)', line)):
                continue
            added[m.group(1), int(m.group(2)), m.group(3)] = (m.group(4), m.group(5))
        for line in hunk.del_lines:
            if not (m := re.match(r'-([^:]+):(\d+): ([^:]+): ([^:]+:\d+): ?(.*)', line)):
                continue
            deled[m.group(1), int(m.group(2)), m.group(3)] = (m.group(4), m.group(5))
    lines_moded: dict[tuple[str, int], tuple[set[str], set[str]]] = {}
    for filename, ln, section in added.keys():
        lines_moded.setdefault((filename, ln), (set(), set()))[0].add(section)
    for filename, ln, section in deled.keys():
        lines_moded.setdefault((filename, ln), (set(), set()))[1].add(section)
    lines_changed: dict[tuple[str, int], tuple[set[str], set[str], set[str]]] \
        = {src: (a - b, b - a, a & b) for src, (a, b) in lines_moded.items()}
    result: set[tuple[str, int, str, str, LiteralString]] = set()
    for (filename, ln), (src_added, src_deled, src_moded) in lines_changed.items():
        perm = max(permutations(
            max(src_added, src_deled, key=len),
            r=min(len(src_added), len(src_deled))
        ), key=lambda p: sum(
            added[filename, ln, a][1] == deled[filename, ln, b][1]
            for a, b in (
                zip(src_added, p)
                if len(src_added) < len(src_deled)
                else zip(p, src_deled)
            )
        ))
        for a, b in (
            zip_longest(src_added, perm, fillvalue=None)
            if len(src_added) < len(src_deled)
            else zip_longest(perm, src_deled, fillvalue=None)
        ):
            if a is None:
                assert b is not None
                dest, text = deled[filename, ln, b]
                result.add((filename, ln, b, text[:len(dest) - 3] + '...', 'deleted'))
            elif b is None:
                dest, text = added[filename, ln, a]
                result.add((filename, ln, a, dest, 'added' if text else 'broken'))
            else:
                assert a != b
                add_dest, add_text = added[filename, ln, a]
                del_dest, del_text = deled[filename, ln, b]
                item = (filename, ln, f'{b} -> {a}', add_dest)
                if not add_text:
                    result.add((*item, 'broken'))
                elif add_dest == del_dest:
                    if add_text == del_text:
                        result.add((*item, 'section changed'))
                    else:
                        result.add((*item, 'text and section changed'))
                else:
                    if add_text == del_text:
                        result.add((*item, 'dest and section changed'))
                    else:
                        result.add((*item, 'text and dest and section changed'))
        for section in src_moded:
            add_dest, add_text = added[filename, ln, section]
            del_dest, del_text = deled[filename, ln, section]
            item = (filename, ln, section, add_dest)
            if not add_text:
                result.add((*item, 'broken'))
            elif add_dest == del_dest:
                if add_text == del_text:
                    result.add((*item, 'whitespaced'))
                else:
                    result.add((*item, 'text changed'))
            else:
                if add_text == del_text:
                    result.add((*item, 'dest changed'))
                else:
                    result.add((*item, 'text and dest changed'))
    return sorted(result)

def main(crossrefs_diff: str, files_diff: str):
    with open(files_diff, encoding='utf8') as f:
        files = {Path(filename).name: File(filename)
                 for filename in glob('**/*.md', recursive=True)}
        files.update({Path(file.name).name: file for file in gather_diff(f)})
    with open(crossrefs_diff, encoding='utf8') as f:
        crossrefs = gather_diff(f)[0]
    for filename, lineno, section, dest, status in gather_crossrefs_diff(crossrefs):
        if m := re.match(r'([^:]+):(\d+)', dest):
            dest = f'{files[m.group(1)].name}:{m.group(2)}'
        file = files[filename]
        if status == 'broken':
            print(f'::error file={file.name},line={lineno}::'
                  f'Please fix this invalid reference to {section!r} ({dest}).')
        elif status == 'added':
            if lineno in file.add_linenos: # this file added this reference
                print(f'::notice file={file.name},line={lineno}::'
                      f'New reference to {section} ({dest}).')
            else:
                print(f'::error file={file.name},line={lineno}::'
                      f'Reference to {section!r} ({dest}) magically appeared.')
        elif status == 'deleted':
            print(f'::debug::{file.name}:{lineno}: '
                  f'Reference to {section} ({dest}) deleted.')
        elif status == 'whitespaced':
            print(f'::debug::{file.name}:{lineno}: {section}: {dest}: '
                  f'Lockfile whitespace changed')
        elif status.endswith('changed'):
            if lineno in file.add_linenos: # referrer line newly added
                level = 'notice'
            else: # reference changed without referrer change
                level = 'warning'
            if 'section' in status:
                fr, to = section.split(' -> ', 1)
                changed = []
                if 'text' in status:
                    changed.append('text')
                if 'dest' in status:
                    changed.append('location')
                if changed:
                    changed = f' Referenced {" and ".join(changed)} ' \
                        f'{"have" if len(changed) > 1 else "has"} also changed.'
                else:
                    changed = ''
                print(f'::{level} file={file.name},line={lineno}::'
                      f'Line now refers to {to} ({dest}) instead of {fr}.{changed} '
                      'Make sure your reference is up to date.')
            else:
                changed = []
                if 'text' in status:
                    changed.append('text')
                if 'dest' in status:
                    changed.append('location')
                changed = ' and '.join(changed).capitalize()
                print(f'::{level} file={file.name},line={lineno}::'
                      f'{changed} of {section} ({dest}) changed in this diff. '
                      'Make sure your reference to it here is up to date.')
        else:
            raise ValueError(status)

if __name__ == '__main__':
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf8')
    main(*sys.argv[1:])
