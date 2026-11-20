"""Prepare a copyable X2 v1.0 handoff: robot ZIP and Windows dashboard tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

import build_robot_bundle

ROOT = Path(__file__).resolve().parents[1]


def build(output, wheelhouse):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    bundle = build_robot_bundle.build(wheelhouse, output / 'eldercare_x2_aarch64_py310.zip')
    with ZipFile(bundle) as archive:
        if archive.testzip() is not None:
            raise ValueError('Robot ZIP integrity check failed')
        manifest = json.loads(archive.read('eldercare_x2/bundle_manifest.json'))
        for name, digest in manifest['source_files'].items():
            if hashlib.sha256(archive.read('eldercare_x2/' + name)).hexdigest() != digest:
                raise ValueError('Bundle source hash mismatch: ' + name)
        if any(n.endswith(('.env', '.jsonl', '.mp4', '.wav')) for n in archive.namelist()):
            raise ValueError('Unexpected private data or media in robot bundle')
    copies = {
        'open_dining_dashboard.cmd': ROOT / 'open_dining_dashboard.cmd',
        'scripts/open_dining_dashboard.ps1': ROOT / 'scripts/open_dining_dashboard.ps1',
        'scripts/robot_project.py': ROOT / 'scripts/robot_project.py',
        '.env.example': ROOT / '.env.example',
        'START-HERE.md': ROOT / 'docs/zh-CN/v1-offline-handoff.md',
    }
    for name, source in copies.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (output / 'source-commit.txt').write_text(
        f"source_revision={manifest['source_revision']}\nsource_dirty={manifest['source_dirty']}\n",
        encoding='utf-8')
    files = [bundle, *(output / name for name in copies), output / 'source-commit.txt']
    (output / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(output).as_posix() + '\n'
        for p in files), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/x2_v1_handoff')
    parser.add_argument('--wheelhouse', type=Path, default=ROOT / '.robot-wheelhouse')
    parser.add_argument('--download-wheels', action='store_true')
    args = parser.parse_args()
    if args.download_wheels:
        build_robot_bundle.download_wheels(args.wheelhouse)
    output = build(args.output, args.wheelhouse)
    print('X2 v1 handoff ready:', output)


if __name__ == '__main__':
    main()
