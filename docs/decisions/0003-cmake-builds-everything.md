# 0003: CMake builds everything; QGSDK's wrappers are optional

**Decided:** QGLogger's build is plain CMake, with presets (`release`, `debug`). QGSDK provides the tools and
the environment, plus a thin `qgsdk build` wrapper for convenience.

**Why.** If the build only works through the SDK's own scripts, the build knowledge is locked inside the
SDK. With plain CMake, any developer who has Qt and a compiler can build QGLogger, with or without QGSDK, and
any IDE that understands CMake (Qt Creator, VS Code, CLion) works.

**How it is enforced.** CI's deletion test builds without the wrapper on every change.
