"""Gives each enum member the name of its own type as prefix, as in showStatisticsPeriod7d.

mopenapi 2.4 takes the first three capitals of the type name as prefix and numbers the ones it has seen already:
TUpdateProductDataStatus gets upd and TUpsertProductDataStatus upd2. A new enum earlier in the spec then takes upd2
and renames the members of the one after it. A type name is unique, so a prefix made from it never moves.
generate.sh runs this after mopenapi, over every unit, so a default value like sspNone is renamed too.
"""
import re
import sys
from pathlib import Path

ENUM = re.compile(r'(?m)^  (T\w+) = \(\n(.*?)\);$', re.S)
WIDTH = 120


def wrap(members):
    lines, line = [], []
    for member in members:
        if line and len('    ' + ', '.join(line + [member]) + ');') > WIDTH:
            lines.append('    ' + ', '.join(line) + ',')
            line = []
        line.append(member)
    return '\n'.join(lines + ['    ' + ', '.join(line)])


def enum_members(units):
    renames, declarations = {}, {}
    for unit, text in units.items():
        for match in ENUM.finditer(text):
            name, members = match.group(1), [member.strip() for member in match.group(2).split(',')]
            old, new = members[0][:-len('None')], name[1].lower() + name[2:]
            renamed = [new + member[len(old):] for member in members]
            renames.update(zip(members, renamed))
            declarations[match.group(0)] = f'  {name} = (\n{wrap(renamed)});'
    taken = [new for new in renames.values() if any(re.search(rf'\b{new}\b', text) for text in units.values())]
    if taken:
        raise ValueError(f'{", ".join(taken)}: the units already use this name.')
    word = re.compile(r'\b(' + '|'.join(map(re.escape, renames)) + r')\b') if renames else None
    result = {}
    for unit, text in units.items():
        for declaration, renamed in declarations.items():
            text = text.replace(declaration, renamed)
        result[unit] = word.sub(lambda match: renames[match.group(1)], text) if word else text
    return result


if __name__ == '__main__':
    paths = [Path(unit) for unit in sys.argv[1:]]
    for path, text in enum_members({path: path.read_text() for path in paths}).items():
        path.write_text(text)
