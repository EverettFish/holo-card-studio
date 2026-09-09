"""Validate four equal-size image layers and genuine transparent alpha."""
from pathlib import Path
from PIL import Image,ImageStat
import argparse,json

def validate(project):
    root=Path(project);report={};size=None
    for name in ['subject','background','lineart','text']:
        file=root/'assets'/(name+'.png')
        with Image.open(file) as im:
            if im.format!='PNG':raise ValueError(str(file)+' is not a PNG')
            if not size:size=im.size
            if im.size!=size:raise ValueError('Layer dimensions differ: '+name)
            if min(im.size)<256:raise ValueError('Artwork is too small')
            item={'size':im.size,'mode':im.mode}
            if name in ['subject','text']:
                if 'A' not in im.getbands():raise ValueError(name+' lacks real alpha; a painted checkerboard is invalid')
                alpha=im.getchannel('A');hist=alpha.histogram();transparent=sum(hist[:16])/sum(hist);solid=sum(hist[128:])/sum(hist)
                if transparent<.01 or solid<.001:raise ValueError(name+' needs both visible and truly transparent pixels')
                item.update(transparent_fraction=round(transparent,4),visible_fraction=round(solid,4))
            if name=='lineart':
                lo,hi=im.convert('L').getextrema()
                if lo>80 or hi<230:raise ValueError('Line art needs dark contours on white')
            report[name]=item
    (root/'asset-validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project');a=p.parse_args();print(json.dumps(validate(a.project),indent=2))
