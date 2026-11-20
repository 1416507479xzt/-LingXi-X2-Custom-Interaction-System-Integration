"""Record/verify exact runtime sources; no credentials or collected data."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runtime_files(root):
    names = ['agent.py', 'feedback_dashboard.py', 'skills.yaml', 'requirements-lock.txt', 'VERSION']
    paths = [root / name for name in names]
    for directory, pattern in [('x2_agent', '*.py'), ('scripts', '*.py'), ('data', '*.json'), ('docker', '*.sh')]:
        paths.extend(sorted((root / directory).glob(pattern)))
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def verify(root, manifest):
    expected = runtime_files(root)
    actual = manifest['files']
    if expected != actual:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
        raise ValueError(f'Container source mismatch: missing={missing} extra={extra} changed={changed}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if bool(args.write) == bool(args.verify):
        parser.error('choose exactly one of --write / --verify')
    if args.write:
        args.write.write_text(json.dumps({'files': runtime_files(ROOT)}, indent=2), encoding='utf-8')
    else:
        verify(ROOT, json.loads(args.verify.read_text(encoding='utf-8')))
        print('Container matches every runtime Python file, public data file and locked dependency list.')


if __name__ == '__main__':
    main()
