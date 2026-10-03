# 0004: Linux: Qt's GCC build, the system compiler, a pinned Python

**Decided:** on Linux, QGSDK installs Qt's own `linux_gcc_64` build with aqtinstall, and CMake and Ninja
from Qt's tools, as on Windows. The compiler is the system's GCC, and QGSDK's Python is
python-build-standalone, pinned and checked like the Windows one. The system packages Qt needs are
listed, checked for, and left to the developer to install.

**Why:**

- **Qt from Qt, not the distribution.** Distributions ship different Qt versions (Rocky 9 has none
  recent enough). Qt's own build gives every developer the same Qt as `manifest.json` says, on any
  distribution, without root.
- **The system's GCC.** Qt's Linux build is made with GCC, and GCC keeps its C++ library compatible
  across versions, so the system compiler matches. Qt publishes no compiler for Linux.
- **A pinned Python, not the system's.** System Pythons differ in version, and some distributions split
  out `venv` (Debian needs `python3-venv`). python-build-standalone is the relocatable CPython build uv
  uses: a tarball, no root, the same 3.13.16 as on Windows.
- **System packages: checked, never installed.** Installing them takes root, which QGSDK never asks
  for. `bootstrap/install.sh` checks for each library Qt loads and prints the one command, for dnf or
  apt, that installs them all. The lists were proved on clean Rocky 9 and Debian 12 containers.

**Packages.** QGLogger's Linux package is a tarball (`QGLogger-<version>-linux-x86_64.tar.gz`) carrying Qt; it
needs the same system libraries at run time, which a desktop has. A Flatpak, which needs none, comes
later.
