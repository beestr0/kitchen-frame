#!/usr/bin/env python3
"""Build only a tiny separate-UID Keystore probe using retained tools; no downloads/install."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
KIOSK=HERE.parent
OUT=KIOSK/'build-auth-probe'


def main():
    sdk=Path(os.environ.get('ANDROID_HOME','/opt/homebrew/share/android-commandlinetools'))
    tools=sdk/'build-tools/34.0.0'; platform=sdk/'platforms/android-34/android.jar'
    jdk=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@17'))
    env=dict(os.environ,JAVA_HOME=str(jdk),PATH=str(jdk/'bin')+':'+os.environ['PATH'])
    def run(args): subprocess.run([str(x) for x in args],check=True,env=env)
    OUT.mkdir(mode=0o700,exist_ok=True)
    classes=OUT/'classes';classes.mkdir(exist_ok=True)
    unsigned=OUT/'unsigned.apk'
    run([tools/'aapt2','link','--manifest',HERE/'AndroidManifest.xml','-I',platform,'-o',unsigned,
         '--min-sdk-version','23','--target-sdk-version','27','--version-code','1','--version-name','auth-probe-1'])
    webview='--webview' in sys.argv
    candidate=KIOSK/'build-auth-candidate'
    sources=[HERE/'AuthProbeActivity.java']
    if webview:sources.append(HERE/'BrowserBoundaryProbe.java')
    if not webview:sources += [KIOSK/'src/com/huntsyea/frame'/name for name in ['DeviceKey.java','DevicePolicy.java','DeviceTransport.java']]
    jars=json.loads((candidate/'dependencies.json').read_text())['jars'] if webview else []
    classpath=str(platform)+(':'+str(candidate/'classes')+':'+':'.join(jars) if webview else '')
    # Keep this directory independent of earlier plain-probe compilations.
    if webview:
        classes=OUT/'webview-classes';classes.mkdir(exist_ok=True)
    run([jdk/'bin/javac','-nowarn','--release','8','-classpath',classpath,'-d',classes,*sources])
    compiler=json.loads((KIOSK/'deps-lan-tls/r8/selected.json').read_text())
    extra=list(candidate.glob('classes*.dex')) if webview else []
    if webview and not extra:raise RuntimeError('Build the offline auth candidate first')
    run([jdk/'bin/java','-cp',compiler['path'],'com.android.tools.r8.D8','--min-api','23','--lib',platform,'--output',OUT,*classes.rglob('*.class'),*extra])
    with zipfile.ZipFile(unsigned,'a') as archive: archive.write(OUT/'classes.dex','classes.dex')
    aligned=OUT/'aligned.apk';run([tools/'zipalign','-f','4',unsigned,aligned])
    key=Path.home()/'.android/debug.keystore'
    if not key.exists():raise RuntimeError('Retained signing key missing; no replacement generated')
    apk=OUT/'auth-probe.apk'
    run([tools/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned])
    run([tools/'apksigner','verify',apk])
    print('Built separate disposable probe:',apk)


if __name__=='__main__':main()
