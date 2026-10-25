# Validation status

The device prototype was exercised on one Redmi Note 8 / Adreno 610 with Android 16 and 4 KiB pages. Checks covered world rendering, player movement, inventory, and native save/reload. No benchmark or full-game compatibility claim is made.

For this extracted source package, the patches were applied to clean snapshots of their pinned upstream files; the Android fork's dependency-patch reverse check still passed afterward. The renamed loader was compiled with NDK 27.2.12479018. The packaging CLI assembled and signed a local APK and passed `apksigner verify`. That APK was not separately installed as a new device test.

Source-only unit tests check the same-length Vulkan dependency redirect and rejection of unexpected payloads. A full clean-checkout build and installation of the extracted public workflow remains pending. The optional source-check workflow is a template in `docs/ci-workflow.yml`; this publication does not enable GitHub Actions. It contains no game data.

An optional source-check workflow template is included as `docs/ci-workflow.yml`. To enable it, copy it to `.github/workflows/check.yml` using credentials with workflow-write permission. It is not an active Actions workflow in this repository.
