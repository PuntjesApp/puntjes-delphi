"""Fails a PR that removes or changes a public declaration of the units, unless the PR says it is breaking.

The public surface is the interface section of each unit under src, one line per declaration: a public class
member, a record field, an enum value, a type or a constant. A removed line is a break, an added line is not.
The overload directive does not count: adding an overload is additive.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

TOKEN = re.compile(r"\s+|//[^\n]*|\{[^}]*\}|\(\*.*?\*\)|('(?:[^']|'')*')|([A-Za-z_][\w.]*|\d+|\.\.|:=|\S)", re.S)
VISIBILITY = {'private', 'protected', 'public', 'published', 'strict'}
DIRECTIVES = {'override', 'virtual', 'overload', 'reintroduce', 'abstract', 'static', 'dynamic', 'inline', 'final',
              'default', 'deprecated', 'cdecl', 'stdcall', 'register', 'safecall'}
SECTIONS = {'type', 'const', 'var', 'threadvar', 'resourcestring'}
ROUTINES = {'procedure', 'function', 'constructor', 'destructor', 'property', 'class', 'operator'}
BANG = re.compile(r'[a-z]+(\([^)]*\))?!:', re.I)
FOOTER = re.compile(r'^BREAKING[ -]CHANGE:', re.M)


def tokens(text):
    lower = text.lower()
    start, end = re.search(r'^interface\b', lower, re.M).end(), re.search(r'^implementation\b', lower, re.M).start()
    return [m.group(1) or m.group(2) for m in TOKEN.finditer(text, start, end) if m.group(1) or m.group(2)]


def render(parts):
    text = ' '.join(parts)
    text = re.sub(r'\s+([,;:)\]])', r'\1', text)
    return re.sub(r'([(\[^])\s+', r'\1', re.sub(r'(\w)\s+([(\[])', r'\1\2', text))


def statement(toks, i):
    depth, j = 0, i
    while j < len(toks) and not (toks[j] == ';' and depth == 0):
        depth += {'(': 1, '[': 1, ')': -1, ']': -1}.get(toks[j], 0)
        j += 1
    while j + 2 < len(toks) and toks[j + 1].lower() in DIRECTIVES and toks[j + 2] == ';':
        j += 2
    return toks[i:j + 1], j + 1


def signature(parts):
    kept = [part for k, part in enumerate(parts) if part.lower() != 'overload'
            and not (part == ';' and k and parts[k - 1].lower() == 'overload')]
    return render(kept[:-1])


def declarations(toks):
    found, i, section = [], 0, None
    while i < len(toks):
        word = toks[i].lower()
        if word == 'uses':
            i = toks.index(';', i) + 1
        elif word in SECTIONS:
            section, i = word, i + 1
        elif word in ('procedure', 'function'):
            parts, i = statement(toks, i)
            found.append((parts[1], signature(parts)))
        elif section == 'type' and toks[i + 1] == '=':
            i = type_declaration(toks, i, found)
        elif section in ('const', 'var', 'threadvar', 'resourcestring'):
            parts, i = statement(toks, i)
            constant(parts[:-1], found)
        else:
            i += 1
    return found


def constant(parts, found):
    name, depth = parts[0], 0
    split = next((k for k, part in enumerate(parts) if part == '=' and '(' not in parts[:k]), len(parts))
    head, value = parts[:split], parts[split + 1:]
    if value[:1] == ['('] and value[-1:] == [')']:
        found.append((name, render(head)))
        items, current = [], []
        for part in value[1:-1]:
            depth += {'(': 1, ')': -1}.get(part, 0)
            if part == ',' and depth == 0:
                items.append(current)
                current = []
            else:
                current.append(part)
        found.extend((f'{name}[{k}]', render(item)) for k, item in enumerate(items + [current]))
    else:
        found.append((name, render(parts)))


def type_declaration(toks, i, found):
    name, rest = toks[i], [t.lower() for t in toks[i + 2:i + 4]]
    if toks[i + 2] == '(':
        close = toks.index(')', i)
        values = [t for t in toks[i + 3:close] if t != ',']
        found.extend((f'{name}[{k}]', value) for k, value in enumerate(values))
        return close + 2
    if 'record' in rest:
        j = i + 2 + rest.index('record') + 1
        while toks[j].lower() != 'end':
            parts, j = statement(toks, j)
            names, field_type = render(parts[:parts.index(':')]).split(', '), render(parts[parts.index(':') + 1:-1])
            found.extend((f'{name}.{field}', field_type) for field in names)
        return j + 2
    if rest[0] == 'class' and rest[1] not in (';', 'of'):
        return class_declaration(toks, i, found)
    parts, j = statement(toks, i)
    found.append((name, render(parts[:-1])))
    return j


def class_declaration(toks, i, found):
    name, j = toks[i], i + 3
    if toks[j] == '(':
        close = toks.index(')', j)
        found.append((name, render(toks[i:close + 1])))
        j = close + 1
    else:
        found.append((name, render(toks[i:i + 3])))
    public = True
    while toks[j].lower() != 'end':
        word = toks[j].lower()
        if word in VISIBILITY:
            public, j = word in ('public', 'published'), j + 1
            continue
        parts, j = statement(toks, j)
        if not public:
            continue
        if word in ROUTINES:
            member = parts[2] if word == 'class' else parts[1]
            found.append((f'{name}.{member}', signature(parts)))
        else:
            fields = render(parts[:parts.index(':')]).split(', ')
            found.extend((f'{name}.{field}', render(parts[:-1])) for field in fields)
    return j + 2


def surface(units):
    found = {unit: declarations(tokens(text)) for unit, text in units.items()}
    return {f'{unit}: {key}: {text}' for unit, decls in found.items() for key, text in decls}


def announced(message):
    return bool(BANG.match(message.strip()) or FOOTER.search(message))


def check(old_units, new_units, is_announced, base, out, err):
    old, new = surface(old_units), surface(new_units)
    removed = sorted(old - new)
    if not removed:
        out(f'No public declaration of {base} is removed or changed. Added: {len(new - old)}.')
        return 0
    report = [f'Public declarations of {base} that this PR removes or changes ({len(removed)}):']
    for line in removed:
        key = line.rsplit(': ', 1)[0].split(': ')[:2]
        now = [other for other in new if other.split(': ')[:2] == key]
        report.append(f'  - {line}')
        report.extend(f'    now: {other}' for other in sorted(now))
    if is_announced:
        out('\n'.join(report + ['The PR title, its body or a commit since the release says this is breaking.']))
        return 0
    err('\n'.join(report + [
        'A caller that uses them no longer compiles. Retitle the PR to "feat!: ..." (or add a "BREAKING CHANGE:" '
        'line to its body), then say in the body what a caller must change. Auto-merge stays on after a retitle.',
    ]))
    return 1


def units_at(ref):
    names = subprocess.run(['git', 'ls-tree', '--name-only', ref, 'src/'], check=True, capture_output=True,
                           text=True).stdout.split()
    return {Path(name).stem: subprocess.run(['git', 'show', f'{ref}:{name}'], check=True, capture_output=True,
                                            text=True).stdout for name in names if name.endswith('.pas')}


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout.strip()


if __name__ == '__main__':
    tag = git('describe', '--tags', '--abbrev=0', '--match', 'v[0-9]*', 'HEAD')
    base = os.environ.get('BASE') or 'HEAD'
    commits = git('log', '--format=%B%x00', f'{tag}..{base}').split('\0')
    message = os.environ.get('TITLE', '') + '\n\n' + os.environ.get('BODY', '')
    is_announced = announced(message) or any(announced(commit) for commit in commits)
    current = {path.stem: path.read_text() for path in sorted(Path('src').glob('*.pas'))}
    sys.exit(check(units_at(tag), current, is_announced, tag, print, lambda text: print(text, file=sys.stderr)))
