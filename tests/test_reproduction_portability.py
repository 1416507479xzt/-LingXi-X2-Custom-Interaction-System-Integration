"""Reproduce deployment-path and audio-focus failures without a robot."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from scripts.robot_project import discover, select_project

ROOT = Path(__file__).resolve().parents[1]


def deployment(home, parent):
    path = home / parent / 'eldercare_x2'
    for name in ('bundle_manifest.json', 'feedback_dashboard.py',
                 'scripts/run_robot_agent.py', 'x2_agent/agent.py'):
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('', encoding='utf-8')
    return path


class ReproductionPortabilityTests(unittest.TestCase):
    def test_versioned_project_detected_without_searching_private_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            live = deployment(home, 'eldercare-x2-bf4c9d9c')
            deployment(home / 'eldercare-backup.private', 'eldercare-x2')
            (home / 'incomplete' / 'eldercare_x2').mkdir(parents=True)
            self.assertEqual(discover(home), [live])
            self.assertEqual(select_project(home), live)

    def test_multiple_deployments_require_selection_instead_of_wrong_records(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            deployment(home, 'eldercare-x2')
            selected = deployment(home, 'eldercare-x2-versioned')
            with patch('builtins.input', return_value='2'), redirect_stdout(io.StringIO()):
                self.assertEqual(select_project(home), selected)
            with patch('builtins.input', return_value='0'), redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):
                    select_project(home)

    def test_missing_project_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with self.assertRaises(ValueError):
                select_project(home)
            self.assertEqual(list(home.iterdir()), [])

    def test_explicit_project_with_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            project = deployment(home, 'project with spaces')
            self.assertEqual(select_project(home, str(project)), project)

    def test_default_tts_focus_matches_successful_robot_priority(self):
        from scripts import aimdk_tts_probe as probe
        with patch.object(probe, 'load_env'), patch.dict(os.environ, {
            'DOUBAO_SPEECH_API_KEY': 'test-only', 'X2_ONLY_VOICE_CONFIRMED': '1'}), \
                patch.object(probe, 'synthesize', new_callable=AsyncMock, return_value=b'\0\0'), \
                patch.object(probe, 'play', new_callable=AsyncMock) as play:
            probe.main(['--play'])
            play.assert_awaited_once_with(b'\0\0', 6)

    @unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows launcher test')
    def test_windows_remote_payload_runs_from_versioned_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            project = deployment(home, 'eldercare-x2-versioned')
            (project / 'feedback_dashboard.py').write_text(
                'import os,sys,json;print(json.dumps([os.getcwd(),sys.argv[1:]]))', encoding='utf-8')
            command = "& '" + str(ROOT / 'scripts/open_dining_dashboard.ps1') + \
                "' -RobotIp 192.0.2.1 -Port 18765 -CheckOnly | ConvertTo-Json -Compress"
            import json
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-Command', command], capture_output=True, text=True, check=True)
            remote = json.loads(result.stdout)['RemoteCommand']
            argv = shlex.split(remote)
            self.assertEqual(argv[:3], ['python3', '-u', '-c'])
            self.assertLess(len(remote), 30000)
            result = subprocess.run([os.sys.executable, *argv[1:]], capture_output=True,
                text=True, check=True, env={**os.environ, 'USERPROFILE': str(home), 'HOME': str(home)})
            actual = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(Path(actual[0]), project)
            self.assertEqual(actual[1], ['--records', 'data/dining_feedback.jsonl', '--port', '18765'])
