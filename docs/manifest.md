# manifest.json

Every version QGSDK installs is in [`manifest.json`](../manifest.json), and nowhere else. The
bootstrap, the `qgsdk` command and CI all read it.

| Entry | What it pins |
|---|---|
| `python` | QGSDK's own Python, for every profile, per platform and machine (`windows`, `linux-x86_64`, `macos-arm64`, `macos-x86_64`): python.org's Windows build, python-build-standalone elsewhere, each with its SHA-256 |
| `aqtinstall` | the tool that installs Qt without an account: an exact commit (see decision 0002) |
| `profiles` | one entry per profile (decision 0005), each with a `description` and what it installs: |
| `profiles.<p>.qt` | the Qt version, the oldest Qt the application supports (`floor`), and Qt's build for each platform |
| `profiles.<p>.tools` | per platform: the compiler, CMake and Ninja, as Qt publishes them |
| `profiles.<p>.downloads` | per platform: tools from their publishers (NSIS, uv, MinGit), each with its SHA-256; an entry with `machine` is used only on that machine |
| `profiles.<p>.python_versions` | the Pythons uv installs into the prefix (mcp) |

To change a version, change it here, open a pull request saying why, and let CI prove it builds.

QGSDK's own Python dependencies (aqtinstall's, and the build tools for it) are locked separately, with
hashes, in [`bootstrap/tooling-requirements.txt`](../bootstrap/tooling-requirements.txt); the file says
how to regenerate it.
