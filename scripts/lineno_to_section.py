import re

Section = tuple[int, int, int, int, int]
ROMAN = [
    'i', 'ii', 'iii', 'iv', 'v',
    'vi', 'vii', 'viii', 'ix', 'x',
    'xi', 'xii', 'xiii', 'xiv', 'xv',
    'xvi', 'xvii', 'xviii', 'xix', 'xx',
]

def lineno_to_section(lineno: int, lines: list[str]) -> Section:
    if lineno < 0:
        raise ValueError(f'Line {lineno} is before first line 0')
    section = [-1, -1, -1, -1, -1]
    for ln, line in enumerate(lines):
        if re.match(r'^#\s+', line):
            section[0] += 1
            section[1:] = [-1] * 4
        elif re.match(r'^##\s+', line):
            section[1] += 1
            section[2:] = [-1] * 3
        elif re.match(r'^\d+\.\s+', line):
            section[2] += 1
            section[3:] = [-1] * 2
        elif re.match(r'^(    ?|\t)\d+\.\s+', line):
            section[3] += 1
            section[4] = -1
        elif re.match(r'^(    ?|\t){2}\d+\.\s+', line):
            section[4] += 1
        if ln == lineno:
            return (section[0], section[1], section[2], section[3], section[4])
    raise ValueError(f'Line {lineno} is past last line {len(lines) - 1}')

def section_to_lineno(sect: Section, lines: list[str]) -> int:
    section = [-1, -1, -1, -1, -1]
    for ln, line in enumerate(lines):
        if re.match(r'^#\s+', line):
            section[0] += 1
            section[1:] = [-1] * 4
        elif re.match(r'^##\s+', line):
            section[1] += 1
            section[2:] = [-1] * 3
        elif re.match(r'^\d+\.\s+', line):
            section[2] += 1
            section[3:] = [-1] * 2
        elif re.match(r'^(    ?|\t)\d+\.\s+', line):
            section[3] += 1
            section[4] = -1
        elif re.match(r'^(    ?|\t){2}\d+\.\s+', line):
            section[4] += 1
        if tuple(section) == sect:
            return ln
    raise ValueError(f'No such section {sect}')

def section_to_str(section: Section) -> str:
    s = str(section[0])
    if section[1] >= 0:
        s += '.' + str(section[1])
        if section[2] >= 0:
            s += '.' + str(section[2] + 1)
            if section[3] >= 0:
                s += '.' + chr(ord('a') + section[3])
                if section[4] >= 0:
                    s += '.' + ROMAN[section[4]]
    return s
