"""Check Git's publication set without ever printing credential values.

Run from any directory. Optional --env-file checks known local secret values
against every indexed file as well as all reachable Git history.
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = (
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b',
    rb'\bgithub_pat_[A-Za-z0-9_]{50,}\b',
    rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}\b',
    rb'\bAKIA[0-9A-Z]{16}\b',
)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blobs(specs):
    process = subprocess.run(
        ['git', '-C', str(ROOT), 'cat-file', '--batch'],
        input=('\n'.join(specs) + '\n').encode(), stdout=subprocess.PIPE, check=True)
    output = process.stdout
    offset = 0
    for spec in specs:
        end = output.index(b'\n', offset)
        header = output[offset:end].split()
        size = int(header[2])
        offset = end + 1
        data = output[offset:offset + size]
        offset += size + 1
        if header[1] == b'blob':
            yield spec, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    known = []
    if args.env_file:
        for line in args.env_file.read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            value = value.strip().strip('\"\'')
            if sep and re.search(r'KEY|TOKEN|SECRET|PASSWORD', key, re.I) and len(value) >= 8:
                known.append(value.encode())
    failures = []
    files = git('ls-files', '-z').decode().split('\0')
    indexed = list(filter(None, files))
    for name in indexed:
        path = Path(name)
        if (path.name.startswith('.env') and path.name != '.env.example'
                or path.suffix in {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db'}
                or any(p in path.parts for p in ('private', 'output', '__pycache__', 'tmp'))):
            failures.append(f'Forbidden publication path: {name}')
    for spec, data in blobs([':' + name for name in indexed]):
        name = spec[1:]
        if any(re.search(pattern, data) for pattern in PATTERNS) or any(value in data for value in known):
            failures.append(f'Possible credential in indexed file: {name}')
    # History is scanned by object, with no source or secret value echoed.
    objects = git('rev-list', '--objects', '--all').decode().splitlines()
    names = dict(row.partition(' ')[::2] for row in objects)
    for oid, data in blobs(list(names)):
        name = names[oid]
        if any(re.search(pattern, data) for pattern in PATTERNS) or any(value in data for value in known):
            failures.append(f'Possible credential in history object {oid[:12]} ({name})')
    for failure in failures:
        print(failure)
    print(f'Publication scan: {len(list(filter(None, files)))} indexed files; '
          f'{len(objects)} reachable history objects; {len(failures)} findings. Values are never printed.')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
