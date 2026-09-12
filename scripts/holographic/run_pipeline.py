"""Build a user-owned Blender/Three.js project from prepared layered artwork."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,os
from ensure_blender import ensure_blender
from validate_assets import validate
from generate_typography import create

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--blender');p.add_argument('--skip-render',action='store_true');p.add_argument('--skip-npm',action='store_true');a=p.parse_args()
    root=Path(a.project).resolve();scripts=Path(__file__).resolve().parent;skill=scripts.parents[1]
    config=root/'card-config.json'
    if not config.exists():raise FileNotFoundError('Write card-config.json from references/config.example.json first')
    if not (root/'assets'/'text.png').exists():create(root)
    validate(root);blender=ensure_blender(root,a.blender)
    env=os.environ.copy();prefs=root/'tools'/'blender-config';prefs.mkdir(parents=True,exist_ok=True);env['BLENDER_USER_CONFIG']=str(prefs)
    cmd=[str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(scripts/'build_card.py'),'--',str(root)]
    if a.skip_render:cmd.append('--skip-render')
    subprocess.run(cmd,check=True,env=env)
    if not (root/'card.blend').exists():raise RuntimeError('Blender did not save card.blend; inspect its log')
    subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(scripts/'export_web.py'),'--',str(root)],check=True,env=env)
    if not (root/'web'/'assets'/'card.glb').exists():raise RuntimeError('GLB export failed')
    web=root/'web';shutil.copytree(skill/'assets'/'web-holographic',web,dirs_exist_ok=True)
    cfg=json.loads(config.read_text(encoding='utf-8-sig'));cfg['assets']={name:'./assets/'+name+'.png' for name in ['subject','background','text','lineart']};cfg['assets']['model']='./assets/card.glb'
    (web/'card-config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    for name in ['subject.png','background.png','text.png','lineart.png']:shutil.copy2(root/'assets'/name,web/'assets'/name)
    if not a.skip_npm:
        npm=shutil.which('npm.cmd') or shutil.which('npm')
        if not npm:raise RuntimeError('Install Node.js/npm, then run npm install --ignore-scripts in web/')
        subprocess.run([npm,'install','--ignore-scripts','--no-audit','--no-fund'],cwd=web,check=True)
    print('Completed:',root/'card.blend');print('Preview: node',web/'server.mjs');print('Open http://127.0.0.1:4173 after starting the server')
if __name__=='__main__':main()
