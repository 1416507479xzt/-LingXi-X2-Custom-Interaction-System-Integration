"""Locate an unpacked ZIP deployment without depending on its directory name.

The Windows launcher sends this standard-library-only source over SSH. It does
not read credentials, create directories, or search inside private backups.
"""
import argparse
import base64
import os
from pathlib import Path
import sys


def is_project(path):
    path = Path(path)
    return (not path.is_symlink() and path.is_dir() and
            all((path / name).is_file() for name in (
                'bundle_manifest.json', 'feedback_dashboard.py',
                'scripts/run_robot_agent.py', 'x2_agent/agent.py')))


def discover(home):
    """Inspect only home/<deployment>/eldercare_x2; never recurse into backups."""
    home = Path(home)
    return sorted(child / 'eldercare_x2' for child in home.iterdir()
                  if not child.is_symlink() and child.is_dir()
                  and is_project(child / 'eldercare_x2'))


def select_project(home, explicit=None):
    if explicit is not None:
        path = Path(explicit).expanduser()
        if not path.is_absolute() or not is_project(path):
            raise ValueError('部署目录无效，需指向包含 bundle_manifest.json 的绝对路径')
        return path
    candidates = discover(home)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError('未找到ZIP部署；请先按README上传并解压离线包')
    print('发现多套部署，请选择与本次Agent相同的目录：', flush=True)
    for index, path in enumerate(candidates, 1):
        print('%d. %s' % (index, path), flush=True)
    try:
        choice = int(input('输入目录序号：'))
    except (EOFError, ValueError) as exc:
        raise ValueError('没有选择有效部署，未启动网页') from exc
    if not 1 <= choice <= len(candidates):
        raise ValueError('目录序号无效，未启动网页')
    return candidates[choice - 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir-b64')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--records', choices=(
        'data/dining_feedback.jsonl', 'data/dining_feedback_stage4_test.jsonl'),
        default='data/dining_feedback.jsonl')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('网页端口必须在1024至65535之间')
    try:
        explicit = (base64.b64decode(args.project_dir_b64, validate=True).decode('utf-8')
                    if args.project_dir_b64 else None)
        project = select_project(Path.home(), explicit)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print('网页部署目录：%s；记录：%s' % (project, args.records), flush=True)
    os.chdir(project)
    os.execv(sys.executable, [sys.executable, '-u', 'feedback_dashboard.py',
                            '--records', args.records, '--port', str(args.port)])


if __name__ == '__main__':
    main()
