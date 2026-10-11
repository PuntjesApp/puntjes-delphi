"""Decides what the regenerate workflow does with one spec-published dispatch: refuse it, skip it, or regenerate.

The rules of puntjes-typescript tools/dispatch-plan.ts, line for line.
"""
import re
import sys
from pathlib import Path

TAG = re.compile(r'v(\d+)\.(\d+)\.(\d+)')


def version(reference):
    match = TAG.fullmatch(reference)
    return tuple(int(part) for part in match.groups()) if match else None


def dispatch_plan(args, out, err):
    tag, level, url, source, open_prs = (list(args) + [''] * 5)[:5]
    current = version(tag)
    if current is None:
        err(f'The tag {tag} is not vX.Y.Z.')
        return 1
    if url != f'https://raw.githubusercontent.com/PuntjesApp/puntjes-openapi/{tag}/api.json':
        err(f'The url is not api.json of puntjes-openapi at {tag}.')
        return 1
    if level not in ('major', 'minor', 'patch'):
        err(f'The level {level} is not major, minor or patch.')
        return 1

    sourced = version(source.strip())
    prs = []
    for line in open_prs.split('\n'):
        branch, _, title = line.strip().partition(' ')
        found = version(branch[len('regenerate/'):]) if branch.startswith('regenerate/') else None
        if found is not None:
            prs.append((branch, found, title.strip().startswith('feat!:')))

    skip = (sourced is not None and sourced >= current) or any(found > current for _, found, _ in prs)
    close = [] if skip else [pr for pr in prs if pr[1] < current]
    major = level == 'major' or any(pr[2] for pr in close) or (sourced is not None and sourced[0] < current[0])

    out(f'skip={str(skip).lower()}')
    out(f"commit_type={'feat!' if major else 'feat' if level == 'minor' else 'fix'}")
    out(f'auto_merge={str(not major).lower()}')
    out(f'branch=regenerate/{tag}')
    out(f"close={' '.join(pr[0] for pr in close)}")
    return 0


if __name__ == '__main__':
    tag, level, url, open_prs = (sys.argv[1:] + [''] * 4)[:4]
    source = Path('spec/SOURCE').read_text()
    sys.exit(dispatch_plan([tag, level, url, source, open_prs], print, lambda line: print(line, file=sys.stderr)))
