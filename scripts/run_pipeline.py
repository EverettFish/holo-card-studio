"""Dispatch a prepared card project to its holographic or lenticular pipeline."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

MODES = ('holographic', 'lenticular')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--mode', choices=MODES)
    parser.add_argument('--blender')
    parser.add_argument('--skip-render', action='store_true')
    parser.add_argument('--skip-npm', action='store_true')
    args = parser.parse_args(argv)
    project = Path(args.project).resolve()
    mode = args.mode
    if mode is None:
        config = project / 'card-config.json'
        try:
            metadata = json.loads(config.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as error:
            parser.error(f'Cannot read {config}: {error}')
        if not isinstance(metadata, dict):
            parser.error('card-config.json must contain a JSON object')
        mode = metadata.get('mode', 'holographic')
    if mode not in MODES:
        parser.error(f'Unsupported card mode: {mode!r}; choose one of {MODES}')
    script = Path(__file__).resolve().parent / mode / 'run_pipeline.py'
    command = [sys.executable, str(script), '--project', str(project)]
    if args.blender:
        command.extend(['--blender', args.blender])
    if args.skip_render:
        command.append('--skip-render')
    if args.skip_npm:
        command.append('--skip-npm')
    return subprocess.run(command).returncode


if __name__ == '__main__':
    raise SystemExit(main())
