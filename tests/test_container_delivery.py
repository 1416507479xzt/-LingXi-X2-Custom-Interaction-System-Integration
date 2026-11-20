"""Detect stale image contents and test launcher isolation without a robot."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.container_manifest import runtime_files, verify

ROOT = Path(__file__).resolve().parents[1]


class ContainerDeliveryTests(unittest.TestCase):
    def test_manifest_rejects_older_optimized_module(self):
        manifest = {'files': runtime_files(ROOT)}
        verify(ROOT, manifest)
        manifest['files']['x2_agent/model_dialogue.py'] = 'old'
        with self.assertRaisesRegex(ValueError, 'model_dialogue.py'):
            verify(ROOT, manifest)

    def test_manifest_rejects_missing_runtime_file(self):
        manifest = {'files': runtime_files(ROOT)}
        del manifest['files']['scripts/aimdk_motion_probe.py']
        with self.assertRaisesRegex(ValueError, 'aimdk_motion_probe.py'):
            verify(ROOT, manifest)

    def test_manifest_excludes_secrets_records_and_media(self):
        for name in runtime_files(ROOT):
            self.assertFalse(name.endswith(('.env', '.jsonl', '.mp4', '.wav')))

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Linux launcher test')
    def test_launcher_refuses_unconfirmed_motion_without_starting_container(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            shutil.copy(ROOT / 'docker/run.sh', target / 'run.sh')
            engine = target / 'podman'
            engine.write_text('#!/bin/sh\necho invoked >> "$CAPTURE"\n', encoding='utf-8')
            engine.chmod(0o755)
            env = {**os.environ, 'PATH': str(target) + os.pathsep + os.environ['PATH'],
                   'CONTAINER_ENGINE': 'podman', 'X2_ONLY_VOICE_CONFIRMED': '0',
                   'CAPTURE': str(target / 'capture')}
            result = subprocess.run(['bash', str(target / 'run.sh'), 'full-agent'],
                                    env=env, capture_output=True)
            self.assertEqual(result.returncode, 23)
            self.assertFalse((target / 'capture').exists())

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Linux launcher test')
    def test_dashboard_uses_persistent_state_without_sdk_or_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            shutil.copy(ROOT / 'docker/run.sh', target / 'run.sh')
            engine = target / 'podman'
            engine.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE"\n', encoding='utf-8')
            engine.chmod(0o755)
            env = {**os.environ, 'PATH': str(target) + os.pathsep + os.environ['PATH'],
                   'CONTAINER_ENGINE': 'podman', 'CAPTURE': str(target / 'capture')}
            result = subprocess.run(['bash', str(target / 'run.sh'), 'dashboard', '--port', '18765'],
                                    env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = (target / 'capture').read_text().splitlines()
            self.assertIn('type=bind,src=' + str(target) + '/state,dst=/var/lib/eldercare', args)
            self.assertEqual(args[-3:], ['dashboard', '--port', '18765'])
            self.assertFalse(any('/home/agi/aimdk' in a or '/opt/eldercare/.env' in a for a in args))
            self.assertNotIn('--privileged', args)
