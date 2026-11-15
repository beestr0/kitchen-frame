#!/usr/bin/env python3
"""Build a separate launcher-only, same-package/signing-key APK; never install it."""
import json
import os
from pathlib import Path
import subprocess
import zipfile
import sys
from prepare_build import KIOSK,OUT,main as prepare


def main():
    candidate='--auth-candidate' in sys.argv
    rollback='--auth-rollback' in sys.argv
    hiveos='--hiveos' in sys.argv
    hive_rollback='--hiveos-rollback' in sys.argv
    if sum([candidate,rollback,hiveos,hive_rollback])>1:raise RuntimeError('Choose exactly one build variant')
    out=KIOSK/('build-auth-rollback' if rollback else 'build-auth-candidate') if candidate or rollback else OUT
    if hiveos or hive_rollback:out=KIOSK/('build-hiveos-rollback' if hive_rollback else 'build-hiveos')
    prepare(out,offline=candidate or rollback or hiveos or hive_rollback,source_ref='94ccb0d' if candidate or rollback or hive_rollback else None,home=hiveos)
    if rollback:
        # Same version/signature as candidate: reinstall can preserve app data
        # without relying on Android's downgrade permission or uninstalling.
        baseline=subprocess.check_output(['git','show','3a74a35:kiosk/src/com/huntsyea/frame/MainActivity.java'],cwd=KIOSK,text=True)
        anchor='    if (url != null) { web.loadUrl(url); handler.postDelayed(watchdog, WATCHDOG_MS); }'
        end='        + "com.huntsyea.frame/.MainActivity -d &lt;url&gt;</code></body>", "text/html", "utf-8");'
        start=baseline.index(anchor);stop=baseline.index(end,start)+len(end)
        baseline=baseline[:start]+'    LanTlsProxy.install(this, () -> {\n'+baseline[start:stop]+'\n    });'+baseline[stop:]
        source=out/'src/com/huntsyea/frame'
        (source/'MainActivity.java').write_text(baseline)
        for name in ('DeviceAuthController.java','DeviceKey.java','DevicePolicy.java','DeviceTransport.java'):
            (source/name).unlink()
    sdk=Path(os.environ.get('ANDROID_HOME','/opt/homebrew/share/android-commandlinetools'))
    tools=sdk/'build-tools/34.0.0';platform=sdk/'platforms/android-34/android.jar'
    jdk=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@17'))
    env=dict(os.environ,JAVA_HOME=str(jdk),PATH=str(jdk/'bin')+':'+os.environ['PATH'])
    def run(args):subprocess.run([str(x) for x in args],check=True,env=env)
    deps=json.loads((out/'dependencies.json').read_text())
    resources=[]
    for i,path in enumerate(deps['resources']):
        archive=out/('resources-'+str(i)+'.zip');run([tools/'aapt2','compile','--dir',path,'-o',archive]);resources.extend(['-R',str(archive)])
    generated=out/'generated';generated.mkdir(exist_ok=True)
    unsigned=out/'unsigned.apk'
    run([tools/'aapt2','link','--manifest',out/'AndroidManifest.xml','-I',platform,'-o',unsigned,
         '--min-sdk-version','23','--target-sdk-version','27','--version-code','6' if hiveos or hive_rollback else '5' if candidate or rollback else '4','--version-name','1.4-rollback-hiveos-v6' if hive_rollback else '1.5-hiveos' if hiveos else '1.3-rollback-v5' if rollback else '1.4-auth-candidate' if candidate else '1.3-lan-tls',
         '--auto-add-overlay','--java',generated,'--extra-packages',':'.join(deps['packages']),*resources])
    classes=out/'classes';classes.mkdir(exist_ok=True)
    sources=list((out/'src').rglob('*.java'))+list(generated.rglob('*.java'))
    run([jdk/'bin/javac','-nowarn','--release','8','-classpath',str(platform)+':'+':'.join(deps['jars']),'-d',classes,*sources])
    compiler=json.loads((KIOSK/'deps-lan-tls/r8/selected.json').read_text())
    run([jdk/'bin/java','-cp',compiler['path'],'com.android.tools.r8.D8','--min-api','23','--lib',platform,'--output',out,*classes.rglob('*.class'),*deps['jars']])
    with zipfile.ZipFile(unsigned,'a') as archive:
        for dex in out.glob('classes*.dex'):archive.write(dex,dex.name)
    aligned=out/'aligned.apk';run([tools/'zipalign','-f','4',unsigned,aligned])
    key=Path.home()/'.android/debug.keystore'
    if not key.exists():raise RuntimeError('Original signing key missing; refusing to create a replacement')
    apk=out/('hiveos-rollback.apk' if hive_rollback else 'hiveos.apk' if hiveos else 'frame-auth-rollback.apk' if rollback else 'frame-auth-candidate.apk' if candidate else 'frame-test-lan-tls.apk')
    run([tools/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned])
    run([tools/'apksigner','verify','--verbose','--print-certs',apk])
    print('Prepared APK only:',apk)


if __name__=='__main__':main()
