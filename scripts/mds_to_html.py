from __future__ import annotations
from glob import glob
from io import StringIO
import json
from pathlib import Path
import re
import shutil
from typing import Never, TextIO, TypedDict

import cmarkgfm
import lxml.etree as etree
import jinja2
import yaml

from lineno_to_section import section_to_str, ROMAN

SPLIT_RE = r'(?:chapters?|chaps?\.|chs?\.|sections?|secs?\.|ss?\.|§|&#167;|&#xa7;)\s*'
CHAPTER_SPLIT_RE = r'(?:chapters?|chaps?\.|chs?\.)\s*'
SECTION_SPLIT_RE = r'(?:sections?|secs?\.|ss?\.|§|&#167;|&#xa7;)\s*'
SECTION_RE = r'([0-9]+)(?:\.([0-9]+)(?:\.([1-9][0-9]*)(?:\.?([a-z])(?:\.([ivxlcdm]+))?)?)?)?'
SUBSECTION_RE = r'([0-9]+)\.([0-9]+)(?:\.([1-9][0-9]*)(?:\.?([a-z])(?:\.([ivxlcdm]+))?)?)?'
REF_RE = fr'({CHAPTER_SPLIT_RE}(?P<chapter>{SECTION_RE})|{SECTION_SPLIT_RE}(?P<section>{SUBSECTION_RE}))(?:\.(?=\S))?'

def crossref_href(section: str) -> str | None:
    section = section.casefold()
    if s := re.search(SECTION_RE, section, re.I):
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
                return None
        return href
    else:
        return None

def make_crossref(m: re.Match[str]) -> str:
    unquoted = m.group(1).strip()
    section = (m.group('chapter') or '') + (m.group('section') or '')
    href = crossref_href(section)
    if href is not None:
        return f'[{unquoted}]({href})'
    else:
        return m.group(0)

def crossref(s: str) -> str:
    return re.sub(REF_RE, make_crossref, s, flags=re.I)

class Section(TypedDict):
    title: str
    md: str
    lineno: int
    body: list[Section]

def clean_html(line: str) -> str:
    return re.sub(r'</?(?![biu]|strong|em)(\w+)[^>]*>', '', line)

def walk_sections(sections: list[Section], prefix: tuple[int, ...] = ()):
    for i, section in enumerate(sections):
        num = (*prefix, i, *((-1,) * (5 - len(prefix) - 1)))
        num = (num[0], num[1], num[2], num[3], num[4])
        href = '#' + '-'.join(map(str, (*prefix, i)))
        yield (('section ' if prefix else 'Chapter ') + section_to_str(num),
               (href, clean_html(section['title'])))
        yield from walk_sections(section['body'], (*prefix, i))

def innerHTML(e: etree._Element) -> str:
    return (
        (e.text or '')
        + b''.join(etree.tostring(c) for c in e.iterchildren()
                   if c.tag != 'ol').decode()
    ).strip()

def parse_error(lineno: int, line: str, expected: str) -> Never:
    msg = f'Expected {expected} at line {lineno} of Markdown, got:\n'
    c = len('ValueError: ')
    msg += ' ' * c + line
    raise ValueError(msg.strip()) from None

def parse_line(md: str) -> str:
    # "Refer to [Bylaw 3, section 1.0](bylaw-3.md)
    #  for [an example](https://example.com)"
    # -> "Refer to []() for []()"
    # -> "... [Bylaw 3, section 1.0](bylaw-3.md#1-0) ..."
    links: list[str] = []
    link_re = re.compile(r'\[([^]]+)\]\(([^)]+)\)')
    sentinel = '[]()'
    def handle_link(m: re.Match[str]) -> str:
        href = m.group(2).split('#', 1)[0]
        if not href.endswith('.md') or re.search(r'^[a-z]*://', href):
            links.append(m.group(0))
            return sentinel
        ref = re.search(REF_RE, m.group(1), flags=re.I)
        if ref is None:
            links.append(m.group(0))
            return sentinel
        section = (ref.group('chapter') or '') + (ref.group('section') or '')
        frag = crossref_href(section)
        if frag is None:
            links.append(m.group(0))
            return sentinel
        href += frag
        links.append(f'[{m.group(1)}]({href})')
        return sentinel
    md = re.sub(link_re, handle_link, md)
    md = crossref(md)
    links.reverse()
    md = re.sub(re.escape(sentinel), lambda _: links.pop(), md)
    # now produce html
    html = cmarkgfm.github_flavored_markdown_to_html(md)
    root = etree.fromstring(html)
    for elem in root.cssselect('a[href*=".md"]'):
        href = elem.attrib.get('href', '')
        elem.attrib['href'] = href.replace('.md', '.html')
    # should return root for h1/h2, and first child of root for li
    return innerHTML(root.cssselect('h1, h2, li')[0])

def parse_lines(md: str) -> str:
    first, *rest = md.splitlines()
    # construct:
    # 1. xyz
    #    abc
    md = '1. ' + first + ''.join('\n   ' + line for line in rest)
    return parse_line(md)

def process_body_line(lineno: int, line: str, stack: list[list[Section]], indents: list[str]) -> None:
    assert len(stack) > 0
    def append():
        nonlocal stack, line, md
        stack[-1].append({
            'title': parse_lines(md) if len(stack) > 2 else parse_line(line),
            'md': md.strip(), 'lineno': lineno, 'body': []
        })
    def push():
        nonlocal stack
        stack.append(stack[-1][-1]['body'])
    if len(stack) == 1:
        # inside body: we expect to advance into h1
        try:
            _, md = re.split(r'^#(?!#)\s*', line, maxsplit=1)
        except ValueError:
            parse_error(lineno, line, '#')
        append()
        push()
    elif len(stack) == 2:
        # inside h1: we expect to advance into h2, or
        # complete the current h1 and start a new one
        try:
            _, h, md = re.split(r'^(#{1,2})(?!#)\s*', line, maxsplit=1)
        except ValueError:
            parse_error(lineno, line, '# or ##')
        if h == '#':
            # complete the current h1
            stack.pop()
        append()
        push()
    else: # len(stack) > 2
        # inside h2 or ol li: we expect to add text to the current
        # li, add a new li, advance into a new ol, or complete
        # the current ol/h2/h1 and start a new one
        try:
            _, prefix, md = re.split(r'^(#{1,2}|\s*\d+\.|\s*)(?!#)\s*', line, maxsplit=1)
        except ValueError:
            parse_error(lineno, line, '#, ##, 1., or an indented line')
        if '#' in prefix: # case 1: heading
            # complete the current h2
            stack[2:] = []
            indents[1:] = [] # reset all indents
            if prefix == '#':
                # complete the current h1
                stack.pop()
            append()
            push()
            return
        if not prefix.strip(): # case 3: continued li
            if len(stack) <= 2:
                parse_error(lineno, line, '"1." before an unprefixed line')
            # note that even this is permissible, apparently:
            # 1. a
            #    1. b
            # c
            # (parses as {a, {b\nc}})
            # add text to the current li
            stack[-1][-1]['md'] += '\n' + md.strip()
            stack[-1][-1]['title'] = parse_lines(stack[-1][-1]['md'])
            return
        # case 2: new li or ol
        indent, _ = re.split(r'\d+\.', line, maxsplit=1)
        assert not indent.strip()
        if indent == indents[-1]: # new li, not ol
            append()
        elif indent.startswith(indents[-1]): # advance into a new ol
            push()
            append()
            indents.append(indent)
        else: # complete one or more ol's, then new li
            old_indents = indents[:]
            while indents and indent != indents[-1]:
                indents.pop()
                stack.pop()
            # since indents starts as [''], if it becomes empty that can only
            # be because an invalid indent was used
            if not indents:
                parse_error(lineno, line, f'indent matching one of {old_indents!r}')
            append()

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
    meta = StringIO()
    with file:
        state = 'awaiting-meta'
        chapters: list[Section] = []
        stack: list[list[Section]] = [chapters]
        indents: list[str] = ['']
        for lineno, line in enumerate(file, start=1):
            if state == 'awaiting-meta':
                if line.startswith('---'):
                    state = 'awaiting-md'
                continue
            if state == 'awaiting-md':
                if line.startswith('---'):
                    state = 'md'
                else:
                    meta.write(line)
                continue
            if not line.strip():
                continue
            process_body_line(lineno, line, stack, indents)
    meta.seek(0)
    meta = yaml.safe_load(meta)
    return meta, chapters

def main() -> None:
    build_dir = Path('build')
    build_dir.mkdir(exist_ok=True)
    # empty build folder
    for root, dirs, files in build_dir.walk():
        for f in files:
            (root / f).unlink()
        for d in dirs:
            shutil.rmtree(root / d)
        dirs.clear()
    # generate htmls
    index: dict[str, tuple[str, dict[str, tuple[str, str]]]] = {}
    for filename in glob('**/*.md', recursive=True):
        if 'README' in filename or 'LICENSE' in filename: # NOTE: index.md is included
            continue
        htmlname = Path(re.sub(r'\.md$', '.html', filename))
        outpath = build_dir / htmlname
        outpath.parent.mkdir(exist_ok=True)
        with (
            open(filename, encoding='utf8') as infile,
            open(outpath, 'w', encoding='utf8') as outfile
        ):
            meta, chapters = get_data(infile)
            assert meta, f'Missing Markdown frontmatter in {filename}'
            print(render(meta, chapters), file=outfile)
        if 'index' in meta['pdf'].casefold():
            continue
        title = meta['subtitle'] if 'policies' in meta['pdf'].casefold() \
            else meta['title']
        index[htmlname.as_posix()] = (title, dict(walk_sections(chapters)))
    with open(build_dir / 'index.js', 'w', encoding='utf8') as f:
        f.write('window.index = ')
        json.dump(index, f)
        f.write(';\n')

if __name__ == '__main__':
    main()
