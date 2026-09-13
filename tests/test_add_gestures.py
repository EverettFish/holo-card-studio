"""Focused checks for the reusable add-on, with no camera, npm, or network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gesture_installer', ROOT / 'scripts/add_gestures.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class GestureInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / 'card with spaces'
        self.web = self.project / 'web'
        (self.web / 'assets').mkdir(parents=True)
        self.config = {'title': 'Different card', 'font': '/private/build/font.ttf',
                       'parameters': {'foil': 0.8}, 'assets': {}}
        for role in installer.ROLES:
            filename = role + ('.glb' if role == 'model' else '.png')
            self.config['assets'][role] = './assets/' + filename
            (self.web / 'assets' / filename).write_bytes(('fixture-' + role).encode())
        self.save()

    def save(self):
        (self.web / 'card-config.json').write_text(json.dumps(self.config), encoding='utf-8-sig')

    def run_install(self, **options):
        return installer.add_gestures(self.project, skip_npm=True, skip_model=True, **options)

    def test_fresh_viewer_preserves_source_and_card_specific_content(self):
        before = {p.relative_to(self.web): p.read_bytes() for p in self.web.rglob('*') if p.is_file()}
        output = self.run_install()
        result = json.loads((output / 'card-config.json').read_text())
        self.assertEqual(result['title'], self.config['title'])
        self.assertEqual(result['parameters'], self.config['parameters'])
        self.assertNotIn('font', result)
        for role, reference in result['assets'].items():
            self.assertEqual((output / reference).read_bytes(), ('fixture-' + role).encode())
        self.assertEqual(before, {p.relative_to(self.web): p.read_bytes() for p in self.web.rglob('*') if p.is_file()})
        self.assertTrue((output / 'gestures/gesture-engine.js').is_file())
        self.assertFalse((output / 'models/hand_landmarker.task').exists())

    def test_existing_output_is_not_overwritten(self):
        output = self.run_install()
        sentinel = output / 'user-change.txt'
        sentinel.write_text('keep me')
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertEqual(sentinel.read_text(), 'keep me')

    def test_output_must_be_outside_source_viewer_and_skill(self):
        for output in (self.web, self.web / 'nested', self.project, ROOT / 'example-output'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.run_install(output=output)

    def test_lenticular_or_missing_assets_fail_before_output(self):
        self.config['mode'] = 'lenticular'
        self.save()
        with self.assertRaises(ValueError):
            self.run_install()
        self.config['mode'] = 'holographic'
        del self.config['assets']['model']
        self.save()
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse((self.project / 'web-gesture').exists())

    def test_external_and_escaping_paths_are_rejected(self):
        outside = self.project / 'outside.png'
        outside.write_bytes(b'not for export')
        for reference in ('../outside.png', str(outside), 'https://example.com/card.png',
                          '//example.com/card.png', './assets/text.png?query=1', '%2e%2e/outside.png'):
            self.config['assets']['text'] = reference
            self.save()
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                self.run_install()

    def test_asset_symlink_cannot_escape_source(self):
        outside = self.project / 'outside.png'
        outside.write_bytes(b'not for export')
        link = self.web / 'assets/text.png'
        link.unlink()
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):
            self.run_install()

    def test_dependency_failure_leaves_no_output_or_staging_directory(self):
        with patch.object(installer.shutil, 'which', return_value='/fake/npm'), \
                patch.object(installer.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'npm')):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.add_gestures(self.project, skip_model=True)
        self.assertFalse((self.project / 'web-gesture').exists())
        self.assertFalse(list(self.project.glob('.gesture-*')))


if __name__ == '__main__':
    unittest.main()
