# manifest.json

Every version QGSDK installs is in [`manifest.json`](../manifest.json), and nowhere else. The
bootstrap, the `qgsdk` command and CI all read it.

| Entry | What it pins |
|---|---|
| `python` | QGSDK's own Python: the official python.org build as a NuGet package (a zip), with its SHA-256 |
| `aqtinstall` | the tool that installs Qt without an account: an exact commit (see decision 0002) |
| `qt` | the Qt version, and the oldest Qt QGLogger supports (`floor`) |
| `tools` | per platform: the compiler, CMake and Ninja, as Qt publishes them |

To change a version, change it here, open a pull request saying why, and let CI prove it builds.

QGSDK's own Python dependencies (aqtinstall's, and the build tools for it) are locked separately, with
hashes, in [`bootstrap/tooling-requirements.txt`](../bootstrap/tooling-requirements.txt); the file says
how to regenerate it.
