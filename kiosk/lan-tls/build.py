#!/usr/bin/env python3
"""Build a separate launcher-only, same-package/signing-key APK; never install it."""
import json
import os
from pathlib import Path
import subprocess
import zipfile
from prepare_build import KIOSK,OUT,main as prepare


def main():
    prepare()
    sdk=Path(os.environ.get('ANDROID_HOME','/opt/homebrew/share/android-commandlinetools'))
    tools=sdk/'build-tools/34.0.0';platform=sdk/'platforms/android-34/android.jar'
    jdk=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@17'))
    env=dict(os.environ,JAVA_HOME=str(jdk),PATH=str(jdk/'bin')+':'+os.environ['PATH'])
    def run(args):subprocess.run([str(x) for x in args],check=True,env=env)
    deps=json.loads((OUT/'dependencies.json').read_text())
    resources=[]
    for i,path in enumerate(deps['resources']):
        archive=OUT/('resources-'+str(i)+'.zip');run([tools/'aapt2','compile','--dir',path,'-o',archive]);resources.extend(['-R',str(archive)])
    generated=OUT/'generated';generated.mkdir(exist_ok=True)
    unsigned=OUT/'unsigned.apk'
    run([tools/'aapt2','link','--manifest',OUT/'AndroidManifest.xml','-I',platform,'-o',unsigned,
         '--min-sdk-version','23','--target-sdk-version','27','--version-code','4','--version-name','1.3-lan-tls',
         '--auto-add-overlay','--java',generated,'--extra-packages',':'.join(deps['packages']),*resources])
    classes=OUT/'classes';classes.mkdir(exist_ok=True)
    sources=list((OUT/'src').rglob('*.java'))+list(generated.rglob('*.java'))
    run([jdk/'bin/javac','-nowarn','--release','8','-classpath',str(platform)+':'+':'.join(deps['jars']),'-d',classes,*sources])
    compiler=json.loads((KIOSK/'deps-lan-tls/r8/selected.json').read_text())
    run([jdk/'bin/java','-cp',compiler['path'],'com.android.tools.r8.D8','--min-api','23','--lib',platform,'--output',OUT,*classes.rglob('*.class'),*deps['jars']])
    with zipfile.ZipFile(unsigned,'a') as archive:
        for dex in OUT.glob('classes*.dex'):archive.write(dex,dex.name)
    aligned=OUT/'aligned.apk';run([tools/'zipalign','-f','4',unsigned,aligned])
    key=Path.home()/'.android/debug.keystore'
    if not key.exists():raise RuntimeError('Original signing key missing; refusing to create a replacement')
    apk=OUT/'frame-test-lan-tls.apk'
    run([tools/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned])
    run([tools/'apksigner','verify','--verbose','--print-certs',apk])
    print('Prepared APK only:',apk)


if __name__=='__main__':main()
