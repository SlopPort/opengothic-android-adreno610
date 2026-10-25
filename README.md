# OpenGothic Android: Adreno 610 compatibility

Experimental source patches and an app-local Vulkan loader for [OpenGothic-Android](https://github.com/borsuczyna/OpenGothic-Android), pinned to commit `118afdc10d79a7f3357e28c6ee52f6fc2fba8586`.

**Created by an LLM (OpenAI Codex).** This attribution covers the new integration, tooling, and documentation. OpenGothic, the Android port, and all dependencies retain their original authorship and licenses.

This project is separate from the [experimental save converter](https://github.com/SlopPort/gothic2-opengothic-save-converter). It does not provide original Gothic save compatibility by itself.

## What it changes

- Loads Mesa Turnip through libadrenotools inside this app. It does **not** replace the phone's system driver, require a system-driver installation, or modify other apps.
- Avoids virtual shadow-map shaders on the affected Adreno path and avoids compiling unused software ray-tracing shaders.
- Fixes Vulkan depth-attachment layout and extension dependency handling in the tested configuration.
- Adds the Android input-handler bridge required by this pinned engine/dependency combination and small compiler compatibility fixes.
- Uses a CPU-created black save thumbnail on Android, avoiding the GPU screenshot/readback path that stalled during testing. The save itself remains a normal OpenGothic save.

The full 3D renderer remains enabled. The shader patch includes compatibility edits used during the investigation; its optional flat-varying macro is not enabled by the build tool.

## Tested scope

One Redmi Note 8 with Adreno 610, Android 16, ARM64, and 4 KiB memory pages. World rendering, movement, inventory, and saving/reloading were exercised with a locally assembled build. This is a limited device smoke test, not a compatibility matrix, performance benchmark, or full-game test.

The selected driver is **Turnip 24.3 R9v2**, distributed by [K11MCH1/AdrenoToolsDrivers](https://github.com/K11MCH1/AdrenoToolsDrivers). It is downloaded separately and verified against the hash in `dependencies.json`. The loader's default `TU_DEBUG` flags are `sysmem,nobin,nolrz,noubwc`; they favor the tested compatibility configuration. No FPS improvement is claimed.

Android 9+ is required by the custom-loader configuration. Other GPUs, ROMs, kernel versions, and 16 KiB-page devices are untested. Existing Android lifecycle limitations of the upstream port still apply: save before backgrounding or locking the phone.

## Build locally

This repository contains source and patches only. No game data, saves, signing keys, drivers, or APK binaries are committed. Supply your own legally obtained Gothic II installation.

Requirements: Python 3.10+, Git, CMake 3.22+ (CMake 4.x was used for the device build), Ninja, a host `glslangValidator`, JDK 17+, Android SDK 35/build-tools 35.0.0, and Android NDK 27.2.12479018. Use a short, ordinary build path; platform-specific path and tool discovery may need adjustment.

```sh
python tools/build.py prepare --work-dir work
python tools/build.py build --work-dir work --ndk /path/to/ndk --glslang /path/to/glslangValidator
```

`prepare` fetches pinned upstream source trees, preserves their licenses, applies the upstream Android dependency patches, and then applies this project's patches. It refuses an existing source checkout rather than resetting it.

For the save converter's playtime fix, pass its patch when preparing the engine:

```sh
python tools/build.py prepare --work-dir work --extra-engine-patch ../gothic2-opengothic-save-converter/patches/preserve-playtime.patch
```

To assemble a local APK, create your own keystore, set `JAVA_HOME`/`PATH`, and set the environment variable `OG_KEYSTORE_PASSWORD`. Do not commit the keystore or password.

```sh
python tools/build.py package --work-dir work --sdk /path/to/android-sdk --keystore /path/to/local.jks --key-alias local --output dist/OpenGothic-Adreno610.apk
```

Packaging uses the hash-pinned upstream APK as a Java/resources base and replaces the native library and manifest. You can provide a local base using `--base-apk`; compatibility with a different base is not guaranteed. The default package ID is `org.opengothic.adreno610`, so it can coexist with upstream. Different signing keys cannot update each other's installations. The upstream launcher's update mechanism is not a distribution channel for these custom builds.

This build recipe packages local binaries; it does not promise byte-identical artifacts across toolchains. The prototype device build predates this extracted packaging CLI. The CLI is checked separately; a complete clean-checkout-to-device run is still a follow-up task.

## Development and reporting

See [architecture and limitations](docs/ARCHITECTURE.md) and [third-party notices](THIRD_PARTY.md). Run `python -m unittest discover -s tests` for the source-only checks. Hardware reports should include the GPU, Android/ROM version, driver version, and the failing operation. Remove account details, local paths, and device serial numbers from logs.

This is an unofficial project. It is not affiliated with the Gothic rights holders, the OpenGothic maintainers, or the Mesa developers.
