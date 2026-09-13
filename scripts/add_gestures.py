"""Create an opt-in gesture viewer from a finished holographic card's web assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('subject', 'background', 'lineart', 'text', 'model')


def read_card(project):
    web = (Path(project).resolve() / 'web').resolve()
    config = json.loads((web / 'card-config.json').read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or config.get('mode', 'holographic') != 'holographic':
        raise ValueError('Gesture control currently supports the holographic route only.')
    assets = config.get('assets')
    if not isinstance(assets, dict):
        raise ValueError('Missing assets in web/card-config.json; finish the card pipeline first.')
    sources = {}
    for role in ROLES:
        reference = assets.get(role)
        if not isinstance(reference, str):
            raise ValueError(f'Missing asset: {role}')
        url = urlsplit(reference)
        if (url.scheme or url.netloc or url.query or url.fragment or '\\' in reference
                or '%' in reference or Path(reference).is_absolute()):
            raise ValueError(f'{role} must reference a local file inside the existing web directory.')
        source = (web / reference).resolve()
        if not source.is_relative_to(web) or not source.is_file():
            raise ValueError(f'Missing or out-of-directory asset: {role}')
        suffix = '.glb' if role == 'model' else '.png'
        if source.suffix.lower() != suffix:
            raise ValueError(f'{role} must be a {suffix} file.')
        sources[role] = source
    return web, config, sources


def add_gestures(project, output=None, *, skip_npm=False, skip_model=False):
    project = Path(project).resolve()
    web, config, sources = read_card(project)
    output = Path(output).resolve() if output else project / 'web-gesture'
    if output == web or output.is_relative_to(web) or web.is_relative_to(output):
        raise ValueError('Choose an output directory separate from the original web directory.')
    if output == ROOT or output.is_relative_to(ROOT):
        raise ValueError('Generated viewers belong outside the reusable skill.')
    if output.exists():
        raise ValueError('Output already exists; choose a new --out directory to preserve it.')
    if not skip_npm and not shutil.which('npm'):
        raise ValueError('Node.js and npm are required. Install them or use --skip-npm.')
    if not skip_model and not shutil.which('node'):
        raise ValueError('Node.js 18+ is required for the model download, or use --skip-model.')

    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the destination. Invalid input or a failed installation cannot
    # leave an apparently complete viewer or overwrite the source project.
    with tempfile.TemporaryDirectory(prefix='.gesture-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'viewer'
        shutil.copytree(ROOT / 'assets/web-gesture', staging,
                        ignore=shutil.ignore_patterns('node_modules', '*.task', '*.download'))
        (staging / 'assets').mkdir()
        manifest = []
        for role, source in sources.items():
            filename = ('card' if role == 'model' else role) + source.suffix.lower()
            target = staging / 'assets' / filename
            shutil.copy2(source, target)
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            copied_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            if original_hash != copied_hash:
                raise ValueError(f'Asset copy failed verification: {role}')
            manifest.append({'role': role, 'file': f'assets/{filename}',
                             'sha256': copied_hash, 'bytes': target.stat().st_size})
        # Export only fields consumed by the browser. Build-only settings can
        # contain machine-local paths and have no purpose in a web deliverable.
        public_keys = ('title', 'subtitle', 'technique', 'tagline', 'edition',
                       'collection', 'description', 'parameters', 'safeArea')
        viewer_config = {key: config[key] for key in public_keys if key in config}
        viewer_config['mode'] = 'holographic'
        viewer_config['assets'] = {item['role']: './' + item['file'] for item in manifest}
        (staging / 'card-config.json').write_text(
            json.dumps(viewer_config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (staging / 'gesture-assets.json').write_text(
            json.dumps({'assets': manifest}, indent=2) + '\n', encoding='utf-8')
        if not skip_npm:
            subprocess.run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=staging, check=True)
        if not skip_model:
            subprocess.run(['node', 'scripts/setup-model.mjs'], cwd=staging, check=True)
        staging.rename(output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Finished card project containing web/')
    parser.add_argument('--out', help='New viewer directory; defaults to <project>/web-gesture')
    parser.add_argument('--skip-npm', action='store_true')
    parser.add_argument('--skip-model', action='store_true')
    args = parser.parse_args(argv)
    try:
        output = add_gestures(args.project, args.out,
                              skip_npm=args.skip_npm, skip_model=args.skip_model)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Gesture viewer not created: {error}\n')
    print(f'Gesture viewer created: {output}')
    print('From that directory:')
    if args.skip_npm:
        print('  npm ci')
    if args.skip_model:
        print('  npm run setup:model')
    print('  npm start')
    print('Open the printed localhost URL in Chrome. Enable the camera explicitly.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
