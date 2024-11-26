from __future__ import annotations
from io import StringIO
from pathlib import Path
import re
import sys
from typing import Never, TextIO, TypedDict
from pprint import pprint

import cmarkgfm
import lxml.etree as etree
import jinja2
import yaml

FILE_RE = r'(?:(?:bylaw|policy)[\w\s-]*,?\s*|[\w\s-]*policy,?\s*)?'
SPLIT_RE = r'(?:chapters?|chaps?\.|chs?\.|sections?|secs?\.|ss?\.|§)\s*'
CHAPTER_SPLIT_RE = r'(?:chapters?|chaps?\.|chs?\.)\s*'
SECTION_SPLIT_RE = r'(?:sections?|secs?\.|ss?\.|§)\s*'
SECTION_RE = r'([0-9]+)(?:\.([0-9]+)(?:\.([1-9][0-9]*)(?:\.?([a-z])(?:\.([ivxlcdm]+))?)?)?)?'
SUBSECTION_RE = r'([0-9]+)\.([0-9]+)(?:\.([1-9][0-9]*)(?:\.?([a-z])(?:\.([ivxlcdm]+))?)?)?'
ROMAN = [
    'i', 'ii', 'iii', 'iv', 'v',
    'vi', 'vii', 'viii', 'ix', 'x',
    'xi', 'xii', 'xiii', 'xiv', 'xv',
    'xvi', 'xvii', 'xviii', 'xix', 'xx',
]

def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9_-]', '', s.strip().casefold().replace(' ', '-'))

def make_crossref(m: re.Match) -> str:
    unquoted = m.group(1).strip()
    split = re.split(SPLIT_RE, unquoted.casefold(), maxsplit=1)
    try:
        file, section = split
    except ValueError: # wrong number of splits
        file = ''
        section = unquoted.casefold()
    else:
        file = slug(file)
    if s := re.match(SECTION_RE, section, re.I):
        a, b, c, d, e = s.groups()
        href = '#' + a
        if b:
            href += '-' + b
        if c:
            href += '-' + str(int(c) - 1)
        if d:
            href += '-' + str(ord(d) - ord('a'))
        if e:
            try:
                href += '-' + str(ROMAN.index(e))
            except IndexError:
                return m.group(0)
        if file:
            href = f'{file}.html{href}'
        return f'<a href="{href}">{unquoted}</a>'
    else:
        return m.group(0)

def crossref(s: str) -> str:
    return re.sub(fr'({FILE_RE}{CHAPTER_SPLIT_RE}{SECTION_RE}'
                  fr'|{FILE_RE}{SECTION_SPLIT_RE}{SUBSECTION_RE})(?:\.(?=\S))?',
                  make_crossref, s, flags=re.I)

class Section(TypedDict):
    title: str
    body: list[Section]

def innerHTML(e: etree._Element) -> str:
    return (
        (e.text or '')
        + b''.join(etree.tostring(c) for c in e.iterchildren()
                   if c.tag != 'ol').decode()
    ).strip()

def parse_error(html: str, element: etree._Element) -> Never:
    lines = html.splitlines()
    msg = f'Unexpected {element.tag} at line {element.sourceline} of HTML:\n'
    if element.sourceline - 2 >= 0:
        msg += f'{" "*14}{lines[element.sourceline - 2]}\n'
    msg += f'{" "*12}! {lines[element.sourceline - 1]}\n'
    if element.sourceline < len(lines):
        msg += f'{" "*14}{lines[element.sourceline]}\n'
    raise ValueError(msg.strip())

def parse(html: str) -> list[Section]:
    chapters: list[Section] = []
    stack: list[list[Section]] = [chapters]

    root = etree.fromstring(f'<body>{html}</body>')

    for element in root.cssselect('h1, h2, body > ol'):
        # pprint(element, sort_dicts=False, stream=sys.stderr)
        if len(stack) == 1:
            if element.tag != 'h1':
                parse_error(html, element)
            stack[-1].append({'title': innerHTML(element), 'body': []})
            stack.append(stack[-1][-1]['body'])
        elif len(stack) == 2:
            if element.tag == 'h1':
                stack.pop()
            elif element.tag != 'h2':
                parse_error(html, element)
            stack[-1].append({'title': innerHTML(element), 'body': []})
            stack.append(stack[-1][-1]['body'])
        elif len(stack) == 3:
            if element.tag in 'h1 h2':
                stack.pop()
                if element.tag == 'h1':
                    stack.pop()
                stack[-1].append({'title': innerHTML(element), 'body': []})
                stack.append(stack[-1][-1]['body'])
                continue
            if element.tag != 'ol':
                parse_error(html, element)
            for li in element.iterchildren('li'):
                stack[-1].append({'title': innerHTML(li), 'body': []})
                for ol in li.iterchildren('ol'):
                    stack.append(stack[-1][-1]['body'])
                    for li in ol.iterchildren('li'):
                        stack[-1].append({'title': innerHTML(li), 'body': []})
                        for ol in li.iterchildren('ol'):
                            stack.append(stack[-1][-1]['body'])
                            for li in ol.iterchildren('li'):
                                stack[-1].append({'title': innerHTML(li), 'body': []})
                                # max depth supported by bylaws
                            stack.pop()
                    stack.pop()

    # pprint(chapters, sort_dicts=False, stream=sys.stderr)
    return chapters

def render(metadata: dict[str, str], chapters: list) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent.absolute()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template('template.jinja2')
    return template.render(**metadata, chapters=chapters)

def get_data(file: TextIO) -> tuple[dict[str, str], list[Section]]:
    with file:
        text = file.read()
    *_, meta, md = text.split('---')
    meta = yaml.safe_load(StringIO(meta))
    html = crossref(cmarkgfm.github_flavored_markdown_to_html(
        md, cmarkgfm.Options.CMARK_OPT_UNSAFE))
    # pprint(html, sort_dicts=False, stream=sys.stderr)
    chapters = parse(html)
    return meta, chapters

def main(argv: list[str] = sys.argv) -> None:
    if len(argv) > 1:
        file = sys.stdin if argv[1] == '-' else open(argv[1], 'r', encoding='utf8')
    else:
        file = open(input('File: '), 'r', encoding='utf8')
    if len(argv) > 2 and argv[2] != '-':
        outfile = open(argv[2], 'w', encoding='utf8')
    else:
        outfile = sys.stdout
    print(render(*get_data(file)), file=outfile)

if __name__ == '__main__':
    main()
