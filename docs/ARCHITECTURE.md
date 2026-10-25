# Architecture and limitations

The engine's `libvulkan.so` dependency string is redirected to the equal-length `libogvulk.so` name during local APK assembly. The small ARM64 loader exports the Vulkan entry points imported by the pinned engine. Its constructor loads the separately supplied driver through libadrenotools and resolves those functions. Assembly trampolines preserve the original call arguments.

The liblinkernsbypass constructor-priority patch makes its linker resolver available before the wrapper constructor uses it. Source preparation applies the Android fork's existing dependency patches before this project's additions; those upstream changes are not claimed as new LLM work.

`OPENGOTHIC_TU_DEBUG`, if set in the app's process environment, overrides the default Turnip debug flags. It is a developer option, not a phone-wide setting. The wrapper falls back to the system Vulkan loader if custom loading fails; that fallback is not expected to fix the original device issue.

The tested build disables unsupported VSM on the legacy Adreno path and skips unused SWRT compilation. Conventional rendering remains active. The CPU thumbnail workaround applies to Android saves and produces a black thumbnail. It does not remove save data or disable world rendering.

The loader is tied to the imported Vulkan symbols of the pinned engine. Changing the engine revision can require regenerating or extending its exports. The APK base and driver are fetched externally, not redistributed here. Before distributing any assembled binary, review its complete dependency and asset notices and provide any source required by those licenses.

Known follow-up work: a fresh end-to-end build on a clean host; narrower GPU detection; a real thumbnail that avoids the problematic readback path; removal of inactive investigation code; broader device testing; and a cleaner upstream integration that avoids APK repackaging.
