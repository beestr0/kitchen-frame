#!/usr/bin/env python3
"""Prepare a separate test APK source tree with official pinned Maven libraries."""
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE=Path(__file__).resolve().parent
KIOSK=HERE.parent
OUT=KIOSK/'build-lan-tls'
CACHE=KIOSK/'deps-lan-tls'
NS={'m':'http://maven.apache.org/POM/4.0.0'}


def fetch(group,artifact,version,extension):
    base='https://dl.google.com/dl/android/maven2/' if group.startswith('androidx.') else 'https://repo.maven.apache.org/maven2/'
    relative=group.replace('.','/')+'/'+artifact+'/'+version+'/'+artifact+'-'+version+'.'+extension
    path=CACHE/relative
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(base+relative,timeout=30) as response:data=response.read()
        path.write_bytes(data)
    return path,base+relative


def version_key(value):return tuple(int(v) for v in re.findall(r'\d+',value))


def main():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(exist_ok=True)
    queue=deque([('androidx.webkit','webkit','1.14.0')]);selected={}
    while queue:
        group,artifact,version=queue.popleft();key=(group,artifact)
        version=version.strip('[]')
        if key in selected and version_key(selected[key]['version'])>=version_key(version):continue
        pom,_=fetch(group,artifact,version,'pom');tree=ET.fromstring(pom.read_bytes())
        properties={item.tag.split('}')[-1]:item.text for item in tree.findall('m:properties/*',NS)}
        packaging=tree.findtext('m:packaging','jar',NS)
        data,url=fetch(group,artifact,version,packaging)
        selected[key]={'group':group,'artifact':artifact,'version':version,'path':str(data),'type':packaging,'url':url,'sha256':hashlib.sha256(data.read_bytes()).hexdigest()}
        for dep in tree.findall('m:dependencies/m:dependency',NS):
            if dep.findtext('m:scope','compile',NS) not in ['compile','runtime'] or dep.findtext('m:optional','false',NS)=='true':continue
            target=[dep.findtext('m:'+field,namespaces=NS) for field in ['groupId','artifactId','version']]
            if not all(target):raise RuntimeError('Unresolved Maven dependency; review POM before building')
            if target[2].startswith('${'):target[2]=properties.get(target[2][2:-1],'')
            if not target[2]:raise RuntimeError('Unresolved Maven property')
            queue.append(tuple(target))
    jars=[];resources=[];packages=[]
    for item in selected.values():
        path=Path(item['path'])
        if item['type']=='aar':
            unpack=OUT/'libraries'/(item['group']+'.'+item['artifact'])
            unpack.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(path) as z:z.extractall(unpack)
            manifest=ET.parse(unpack/'AndroidManifest.xml').getroot()
            minimum=manifest.find('uses-sdk')
            if minimum is not None and int(minimum.attrib.get('{http://schemas.android.com/apk/res/android}minSdkVersion','1'))>23:
                raise RuntimeError('Library requires newer Android than the frame')
            jars.append(str(unpack/'classes.jar'))
            if (unpack/'res').exists():resources.append(str(unpack/'res'))
            if manifest.attrib.get('package'):packages.append(manifest.attrib['package'])
        else:jars.append(str(path))
    source=OUT/'src';source.mkdir(exist_ok=True)
    for original in (KIOSK/'src').rglob('*.java'):
        target=source/original.relative_to(KIOSK/'src');target.parent.mkdir(parents=True,exist_ok=True)
        text=original.read_text()
        if original.name=='MainActivity.java':
            anchor='    if (url != null) { web.loadUrl(url); handler.postDelayed(watchdog, WATCHDOG_MS); }'
            end='        + "com.huntsyea.frame/.MainActivity -d &lt;url&gt;</code></body>", "text/html", "utf-8");'
            start=text.index(anchor);stop=text.index(end,start)+len(end)
            startup=text[start:stop]
            text=text[:start]+'    LanTlsProxy.install(this, () -> {\n'+startup+'\n    });'+text[stop:]
        target.write_text(text)
    shutil.copy2(HERE/'LanTlsProxy.java',source/'com/huntsyea/frame/LanTlsProxy.java')
    manifest=(KIOSK/'AndroidManifest.xml').read_text()
    manifest=re.sub(r'^.*<category android:name="android.intent.category.HOME".*\n','',manifest,flags=re.M)
    (OUT/'AndroidManifest.xml').write_text(manifest)
    (OUT/'dependencies.json').write_text(json.dumps({'jars':jars,'resources':resources,'packages':packages},indent=2))
    (KIOSK/'lan-tls/dependencies.lock.json').write_text(json.dumps([{k:v for k,v in item.items() if k!='path'} for item in selected.values()],indent=2))
    print('Prepared independent test build with',len(jars),'official libraries; original APK preserved; configuration is not changed by building.')


if __name__=='__main__':main()
