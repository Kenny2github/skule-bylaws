from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import StringIO, TextIOWrapper
from itertools import zip_longest
import sys
from typing import Iterable, Self

from diff_to_annotations import gather_diff
from lineno_to_section import section_to_str
from mds_to_html import Section, get_data, clean_html

START = """
<table border="1" frame="border">
<tr><th colspan="2">Deleted</th><th colspan="2">Added</th></tr>
<tr><th>Section</th><th>Text</th><th>Section</th><th>Text</th></tr>
""".strip()

ROW = '''<tr>
<td>{0}</td>
<td>{1}</td>
<td>{2}</td>
<td>{3}</td>
</tr>'''

@dataclass(frozen=True)
class FrozenSection:
    title: str
    body: tuple[FrozenSection, ...]

    @classmethod
    def from_section(cls, section: Section) -> Self:
        title = section['title']
        body = tuple(FrozenSection.from_section(s) for s in section['body'])
        return cls(title, body)

def lines_to_chapters(lines: Iterable[str]) -> tuple[dict[str, str], tuple[FrozenSection, ...]]:
    sio = StringIO()
    sio.writelines(line + '\n' for line in lines)
    sio.seek(0)
    meta, chapters = get_data(sio)
    return meta, tuple(FrozenSection.from_section(chapter) for chapter in chapters)

def diff_sections(body1: tuple[FrozenSection, ...], body2: tuple[FrozenSection, ...],
                  prefix1: tuple[int, ...] = (), prefix2: tuple[int, ...] = ()):
    sm = SequenceMatcher(a=body1, b=body2)
    for tag, i1, j1, i2, j2 in sm.get_opcodes():
        if tag == 'insert':
            assert i1 == j1
            for i in range(i2, j2):
                prefix = (*prefix2, i)
                yield tag, None, '', prefix, body2[i].title
                yield from diff_sections((), body2[i].body, (*prefix1, i1), prefix)
        elif tag == 'delete':
            assert i2 == j2
            for i in range(i1, j1):
                prefix = (*prefix1, i)
                yield tag, prefix, body1[i].title, None, ''
                yield from diff_sections(body1[i].body, (), prefix, (*prefix2, i2))
        elif tag == 'replace':
            for i, j in zip_longest(range(i1, j1), range(i2, j2), fillvalue=None):
                if i is None:
                    assert j is not None
                    prefix = (*prefix2, j)
                    yield 'insert', None, '', prefix, body2[j].title
                    yield from diff_sections((), body2[j].body, (*prefix1, j1), prefix)
                elif j is None:
                    assert i is not None
                    prefix = (*prefix1, i)
                    yield 'delete', prefix, body1[i].title, None, ''
                    yield from diff_sections(body1[i].body, (), prefix, (*prefix2, j2))
                else:
                    prefixi = (*prefix1, i)
                    prefixj = (*prefix2, j)
                    if body1[i].title != body2[i].title:
                        yield tag, prefixi, body1[i].title, prefixj, body2[j].title
                    yield from diff_sections(body1[i].body, body2[j].body, prefixi, prefixj)

def main() -> None:
    print(START)
    for file in gather_diff(sys.stdin):
        for hunk in file.hunks:
            _, a_chapters = lines_to_chapters(line[1:] for line in hunk.del_lines)
            meta, b_chapters = lines_to_chapters(line[1:] for line in hunk.add_lines)
            title = meta['subtitle'] if 'policies' in meta['pdf'].casefold() else meta['title']
            print(f'<tr><th colspan="4">{title}</th></tr>')
            tag = None
            for tag, a_prefix, a_line, b_prefix, b_line in diff_sections(a_chapters, b_chapters):
                if a_prefix is None:
                    a_prefix = ''
                else:
                    a_prefix = section_to_str(a_prefix + (-1,) * (5 - len(a_prefix))) # type: ignore
                if b_prefix is None:
                    b_prefix = ''
                else:
                    b_prefix = section_to_str(b_prefix + (-1,) * (5 - len(b_prefix))) # type: ignore
                a_line = clean_html(a_line)
                b_line = clean_html(b_line)
                print(ROW.format(a_prefix, a_line, b_prefix, b_line))
            if tag is None: # for loop never executed
                print('<tr><td colspan="4"><i>No changes resulted in HTML differences</i></td></tr>')
    print('</table>')

if __name__ == '__main__':
    if isinstance(sys.stdin, TextIOWrapper):
        sys.stdin.reconfigure(encoding='utf8')
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf8')
    main()
