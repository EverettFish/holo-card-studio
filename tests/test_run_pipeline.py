"""Run with: python -m unittest discover -s tests -v."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('card_dispatcher', ROOT / 'scripts/run_pipeline.py')
dispatcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatcher)


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve() / 'card with spaces'
        self.project.mkdir()

    def config(self, value):
        (self.project / 'card-config.json').write_text(json.dumps(value), encoding='utf-8-sig')

    def dispatch(self, extra=(), status=0):
        with patch.object(dispatcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], status)) as run:
            result = dispatcher.main(['--project', str(self.project), *extra])
        return result, run.call_args.args[0]

    def test_missing_mode_defaults_to_holographic(self):
        self.config({'title': 'Card'})
        result, command = self.dispatch()
        self.assertEqual(result, 0)
        self.assertEqual(Path(command[1]), ROOT / 'scripts/holographic/run_pipeline.py')

    def test_config_mode_selects_lenticular(self):
        self.config({'mode': 'lenticular'})
        _, command = self.dispatch()
        self.assertEqual(Path(command[1]), ROOT / 'scripts/lenticular/run_pipeline.py')

    def test_explicit_mode_overrides_config_and_forwards_options(self):
        self.config({'mode': 'lenticular'})
        options = ['--mode', 'holographic', '--blender', '/path with spaces/Blender', '--skip-render', '--skip-npm']
        _, command = self.dispatch(options)
        self.assertEqual(command, [sys.executable, str(ROOT / 'scripts/holographic/run_pipeline.py'),
                                  '--project', str(self.project), '--blender', '/path with spaces/Blender',
                                  '--skip-render', '--skip-npm'])

    def test_child_failure_is_returned(self):
        self.config({})
        result, _ = self.dispatch(status=23)
        self.assertEqual(result, 23)

    def test_invalid_config_does_not_start_a_child(self):
        for value in [{'mode': '../unexpected'}, {'mode': None}, []]:
            with self.subTest(value=value):
                self.config(value)
                with patch.object(dispatcher.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        dispatcher.main(['--project', str(self.project)])
                    self.assertEqual(error.exception.code, 2)
                    run.assert_not_called()

    def test_missing_or_malformed_config_reports_cli_error(self):
        for content in [None, '{bad json']:
            if content is not None:
                (self.project / 'card-config.json').write_text(content)
            with patch.object(dispatcher.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    dispatcher.main(['--project', str(self.project)])
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()


@unittest.skipIf(os.name == 'nt', 'The fake Blender executable uses a POSIX shebang')
class HolographicFailureTests(unittest.TestCase):
    def test_failed_blender_stops_even_when_old_outputs_exist(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve() / 'card with spaces'
            assets = project / 'assets'
            assets.mkdir(parents=True)
            (project / 'card-config.json').write_text('{}')
            for name in ('subject', 'text'):
                image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
                image.paste((255, 100, 0, 255), (40, 40, 100, 140))
                image.save(assets / (name + '.png'))
            Image.new('RGB', (256, 256), 'white').save(assets / 'background.png')
            line = Image.new('RGB', (256, 256), 'white')
            line.paste('black', (40, 40, 100, 42))
            line.save(assets / 'lineart.png')
            (project / 'card.blend').write_text('stale project')
            web_assets = project / 'web/assets'
            web_assets.mkdir(parents=True)
            (web_assets / 'card.glb').write_text('stale export')

            fake = Path(temporary) / 'blender'
            fake.write_text(
                '#!' + sys.executable + '\n'
                'import json, os, pathlib, sys\n'
                'root = pathlib.Path(sys.argv[sys.argv.index("--") + 1])\n'
                'with (root / "calls.jsonl").open("a") as out:\n'
                '    out.write(json.dumps({"args": sys.argv, "prefs": os.environ.get("BLENDER_USER_CONFIG")}) + "\\n")\n'
                'raise SystemExit(1 if "--python-exit-code" in sys.argv else 0)\n'
            )
            fake.chmod(0o755)
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_pipeline.py'),
                                     '--project', str(project), '--blender', str(fake),
                                     '--skip-render', '--skip-npm'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            calls = [json.loads(line) for line in (project / 'calls.jsonl').read_text().splitlines()]
            self.assertEqual(len(calls), 1, 'A failed build must not continue to export')
            self.assertEqual(calls[0]['prefs'], str(project / 'tools/blender-config'))
            self.assertEqual((project / 'card.blend').read_text(), 'stale project')
            self.assertFalse((project / 'web/index.html').exists())


if __name__ == '__main__':
    unittest.main()
