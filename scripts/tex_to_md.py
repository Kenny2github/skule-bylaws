import io
from pathlib import Path
import re
import sys

def main(argv: list[str] = sys.argv) -> None:
    if len(argv) > 1:
        file = sys.stdin if argv[1] == '-' else open(argv[1], 'r', encoding='utf8')
    else:
        file = open(input('File: '), 'r', encoding='utf8')
    if len(argv) > 2 and argv[2] != '-':
        outfile = open(argv[2], 'w', encoding='utf8')
    else:
        outfile = sys.stdout
    with file, outfile:
        section = [0, 0, 0]
        in_list = False
        meta = 0
        print('---', file=outfile)
        for line in file:
            line = re.sub(r"``|''", '"', line)
            line = re.sub(r"\\([$%&])", r'\1', line)
            if not line.strip():
                continue
            if meta == 1:
                print('title:', line.strip(), file=outfile)
                # output PDF filename based on original TeX filename
                if len(argv) > 1 and argv[1] != '-':
                    print('pdf:', Path(argv[1].rsplit('.', 1)[0]).resolve().relative_to(Path.cwd()).as_posix(), file=outfile)
                else:
                    print('pdf:', line.strip(), file=outfile)
                meta = 2
                continue
            if meta == 2:
                print('subtitle:', line.strip(), file=outfile)
                print('---', end='', file=outfile)
                meta = 3
                continue
            if not in_list:
                if m := re.match(r'\\newcommand\s*\{\s*\\revdate\s*\}\s*\{\s*([^}]+)\s*\}', line):
                    print('revdate:', m.group(1), file=outfile)
                if meta == 0 and re.match(r'\\Large\s*\\bfseries\s*\\uppercase\s*\{', line):
                    meta = 1
                if m := re.match(r'\\section\s*\{\s*([^}]+)\s*\}', line):
                    print('\n\n#', m.group(1), end='', file=outfile)
                    continue
                if re.match(r'\\begin\s*\{\s*easylist\s*\}', line):
                    in_list = True
                    section[:] = [-1, -1, -1]
                    continue
                continue
            if in_list:
                if re.match(r'\\end\s*\{\s*easylist\s*\}', line):
                    in_list = False
                    continue
                if re.match(r'^\\', line):
                    continue
            if m := re.match(r'\s*(&+)\s*', line):
                if len(m.group(1)) == 2:
                    print('\n\n##', line.removeprefix(m.group(0)).rstrip(), end='', file=outfile)
                    section[:] = [0, 0, 0]
                else:
                    if section == [-1, -1, -1]:
                        print('\n\n##', 'General', end='', file=outfile)
                        section[:] = [0, 0, 0]
                    i = (len(m.group(1)) - 3)
                    section[i] += 1
                    section[i+1:] = [0] * (2 - i)
                    print('\n' + ' ' * (3 * i) + '1.',
                          line.removeprefix(m.group(0)).rstrip(), end='', file=outfile)
            else:
                print('', line.strip(), end='', file=outfile)

if __name__ == '__main__':
    if isinstance(sys.stdin, io.TextIOWrapper):
        sys.stdin.reconfigure(encoding='utf8')
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf8')
    main()
