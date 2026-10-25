"""Pinned source preparation, native build, and local APK assembly. No game data."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
DEPS = json.loads((ROOT / 'dependencies.json').read_text())

def run(*args, cwd=None, env=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run([str(x) for x in args], cwd=cwd, env=env, check=True)

def checkout(spec, dest):
    if dest.exists():
        raise RuntimeError(f'{dest} exists; use an empty work directory')
    run('git', 'clone', '--no-checkout', spec['url'], dest)
    run('git', 'checkout', '--detach', spec['commit'], cwd=dest)
    run('git', 'submodule', 'update', '--init', '--recursive', cwd=dest)

def apply(repo, patch):
    run('git', 'apply', '--check', '--ignore-whitespace', patch, cwd=repo)
    run('git', 'apply', '--ignore-whitespace', patch, cwd=repo)

def fetch(spec, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(spec['url']) as response, path.open('wb') as out:
            shutil.copyfileobj(response, out)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != spec['sha256']:
        raise RuntimeError(f'Checksum mismatch: {path}')
    return path

def prepare(a):
    work = a.work_dir.resolve(); work.mkdir(parents=True, exist_ok=True)
    engine = work / 'OpenGothic'
    checkout(DEPS['opengothic'], engine)
    # Apply the Android fork's own dependency patches first, then our additions.
    apply(engine / 'lib/Tempest', engine / 'patches/tempest-opengothic.patch')
    apply(engine / 'lib/ZenKit', engine / 'patches/zenkit-opengothic.patch')
    apply(engine, ROOT / 'patches/opengothic-adreno610.patch')
    apply(engine / 'lib/Tempest', ROOT / 'patches/tempest-adreno610.patch')
    if a.extra_engine_patch:
        apply(engine, a.extra_engine_patch.resolve())
    checkout(DEPS['adrenotools'], work / 'libadrenotools')
    apply(work / 'libadrenotools/lib/linkernsbypass', ROOT / 'patches/linkernsbypass-constructor.patch')
    checkout(DEPS['vulkan_headers'], work / 'Vulkan-Headers')
    fetch(DEPS['turnip'], work / 'downloads/turnip.zip')
    print('Prepared pinned sources. Upstream licenses remain in their source trees.')

def build(a):
    work = a.work_dir.resolve(); ndk = a.ndk.resolve()
    env = os.environ.copy(); env['VULKAN_SDK'] = str(work / 'Vulkan-Headers')
    toolchain = ndk / 'build/cmake/android.toolchain.cmake'
    common = ['-G', 'Ninja', f'-DCMAKE_TOOLCHAIN_FILE={toolchain}', '-DANDROID_ABI=arm64-v8a', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_POLICY_VERSION_MINIMUM=3.5']
    if a.ninja: common.append(f'-DCMAKE_MAKE_PROGRAM={a.ninja.resolve()}')
    run(a.cmake, '-S', work / 'OpenGothic', '-B', work / 'native-build', *common,
        '-DANDROID_PLATFORM=android-24', f'-DGLSLANGVALIDATOR={a.glslang.resolve()}', env=env)
    run(a.cmake, '--build', work / 'native-build', '--target', 'Gothic2Notr', '--parallel', a.jobs, env=env)
    run(a.cmake, '-S', ROOT / 'loader', '-B', work / 'loader-build', *common,
        '-DANDROID_PLATFORM=android-28', f'-DADRENOTOOLS_SOURCE={work / "libadrenotools"}', env=env)
    run(a.cmake, '--build', work / 'loader-build', '--parallel', a.jobs, env=env)

def redirect_vulkan(data):
    """Same-length DT_NEEDED string replacement; no fixed code offsets."""
    if not data.startswith(b'\x7fELF') or data.count(b'libvulkan.so\0') != 1:
        raise ValueError('Expected an ELF with exactly one libvulkan.so dependency string')
    return data.replace(b'libvulkan.so\0', b'libogvulk.so\0')

def package(a):
    work = a.work_dir.resolve(); sdk = a.sdk.resolve(); buildtools = sdk / 'build-tools/35.0.0'
    out = a.output.resolve(); stage = work / 'package'; stage.mkdir(parents=True, exist_ok=True)
    def tool(name):
        suffix = '.bat' if os.name == 'nt' and name == 'apksigner' else '.exe' if os.name == 'nt' else ''
        return buildtools / (name + suffix)
    base = a.base_apk.resolve() if a.base_apk else fetch(DEPS['base_apk'], work / 'downloads/base.apk')
    # Never publish this assembled APK without reviewing all bundled notices/assets.
    manifest = ET.parse(work / 'OpenGothic/android/AndroidManifest.xml')
    ns = '{http://schemas.android.com/apk/res/android}'
    manifest.getroot().set('package', a.package_name)
    manifest.getroot().set(ns + 'versionCode', str(a.version_code))
    manifest.getroot().set(ns + 'versionName', '0.1.0-adreno610')
    app = manifest.find('application'); app.set(ns + 'label', 'OpenGothic Adreno 610')
    app.set(ns + 'debuggable', 'true' if a.debuggable else 'false')
    ET.SubElement(manifest.getroot(), 'uses-sdk', {ns+'minSdkVersion':'28', ns+'targetSdkVersion':'35'})
    manifest.write(stage / 'AndroidManifest.xml', encoding='utf-8', xml_declaration=True)
    run(tool('aapt2'), 'link', '--manifest', stage / 'AndroidManifest.xml', '-I', sdk / 'platforms/android-35/android.jar', '-o', stage / 'manifest.apk')
    native = (work / 'native-build/opengothic/libGothic2Notr.so').read_bytes()
    with zipfile.ZipFile(stage / 'manifest.apk') as z: manifest_data = z.read('AndroidManifest.xml')
    with zipfile.ZipFile(base) as z, zipfile.ZipFile(stage / 'unsigned.apk','w',zipfile.ZIP_DEFLATED) as target:
        for entry in z.infolist():
            if entry.filename.upper().startswith('META-INF/') or entry.filename.endswith(('libogvulk.so','libturnip.so')): continue
            data = z.read(entry.filename)
            if entry.filename == 'AndroidManifest.xml': data = manifest_data
            elif entry.filename == 'lib/arm64-v8a/libGothic2Notr.so': data = redirect_vulkan(native)
            target.writestr(entry, data)
        target.write(work / 'loader-build/libogvulk.so', 'lib/arm64-v8a/libogvulk.so')
        for p in sorted((work / 'loader-build/adrenotools/src/hook').glob('*.so')):
            target.write(p, 'lib/arm64-v8a/' + p.name)
        driver = fetch(DEPS['turnip'], work / 'downloads/turnip.zip')
        with zipfile.ZipFile(driver) as dz:
            target.writestr('lib/arm64-v8a/libturnip.so', dz.read(DEPS['turnip']['library']))
    run(tool('zipalign'), '-f', '-P', '16', '4', stage / 'unsigned.apk', stage / 'aligned.apk')
    if 'OG_KEYSTORE_PASSWORD' not in os.environ:
        raise RuntimeError('Set OG_KEYSTORE_PASSWORD; signing keys are local inputs only')
    out.parent.mkdir(parents=True, exist_ok=True)
    run(tool('apksigner'), 'sign', '--ks', a.keystore.resolve(), '--ks-key-alias', a.key_alias,
        '--ks-pass','env:OG_KEYSTORE_PASSWORD','--key-pass','env:OG_KEYSTORE_PASSWORD', '--out',out,stage / 'aligned.apk')
    run(tool('apksigner'), 'verify', '--verbose', out)
    print('Local APK:', out)

def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    for name in ['prepare','build','package']:
        q = sub.add_parser(name); q.add_argument('--work-dir',type=Path,default=ROOT/'work')
        if name == 'prepare':q.add_argument('--extra-engine-patch',type=Path)
        if name == 'build':
            q.add_argument('--ndk',type=Path,required=True);q.add_argument('--glslang',type=Path,required=True)
            q.add_argument('--cmake',default='cmake');q.add_argument('--ninja',type=Path);q.add_argument('--jobs',type=int,default=4)
        if name == 'package':
            q.add_argument('--sdk',type=Path,required=True);q.add_argument('--keystore',type=Path,required=True)
            q.add_argument('--key-alias',required=True);q.add_argument('--output',type=Path,required=True)
            q.add_argument('--base-apk',type=Path);q.add_argument('--package-name',default='org.opengothic.adreno610')
            q.add_argument('--version-code',type=int,default=1);q.add_argument('--debuggable',action='store_true')
    a=p.parse_args();{'prepare':prepare,'build':build,'package':package}[a.command](a)
if __name__ == '__main__':main()
