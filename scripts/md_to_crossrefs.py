from functools import partial
from glob import glob
import io
from pathlib import Path
import re
import sys

from mds_to_html import REF_RE, crossref_href
from lineno_to_section import section_to_lineno, section_to_str

def print_crossref(src: str, files: dict[str, list[str]], frag: str, text: str, link: str) -> None:
    section = list(map(int, frag.removeprefix('#').split('-')))
    section[len(section):5] = [-1] * (5 - len(section))
    section = (section[0], section[1], section[2], section[3], section[4])
    filename = Path(link).name
    try:
        lineno = section_to_lineno(section, files[filename])
    except ValueError:
        print(f'{src}: warning: could not find {text!r} (section '
              f'{section_to_str(section)}?) in {link!r}', file=sys.stderr)
        dest = f'{filename}:??'
        line = ''
    else:
        dest = f'{filename}:{lineno + 1}'
        line = files[filename][lineno]
    print(f'{src}: {text}: {dest}: {line.rstrip("\n")}')

def check_textref(file: str, lineno: int, files: dict[str, list[str]], m: re.Match[str]) -> None:
    if not (href := crossref_href((m.group('chapter') or '') + (m.group('section') or ''))):
        return # no real crossref
    print_crossref(f'{file}:{lineno}', files, href, m.group(1), file)

def check_linkref(src: str, files: dict[str, list[str]], m: re.Match[str]) -> str:
    text, href = m.groups()
    n = re.search(REF_RE, text, flags=re.I)
    if n is None:
        return m.group(0)
    frag = crossref_href((n.group('chapter') or '') + (n.group('section') or ''))
    if frag is None:
        return m.group(0)
    print_crossref(src, files, frag, text, href)
    return '' # so it doesn't get hit again by the internal-section checker

def main() -> None:
    files: dict[str, list[str]] = {}
    for filename in glob('**/*.md', recursive=True):
        with open(filename, encoding='utf8') as f:
            files[Path(filename).name] = f.readlines()
    for filename, lines in files.items():
        for ln, line in enumerate(lines):
            fn = partial(check_linkref, f'{filename}:{ln+1}', files)
            lines[ln] = line = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', fn, line, flags=re.I)
            for m in re.finditer(REF_RE, line, re.I):
                check_textref(filename, ln+1, files, m)

if __name__ == '__main__':
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf8')
    main()
