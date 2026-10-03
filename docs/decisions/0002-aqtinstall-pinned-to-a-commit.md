# 0002: aqtinstall, pinned to a commit

**Decided:** Qt and its tools are installed with [aqtinstall](https://github.com/miurahr/aqtinstall),
pinned to an exact commit, installed from its source zip.

**Why aqtinstall.** Qt's own installer needs a Qt account and interaction. aqtinstall downloads the same
packages from Qt's repositories, checks them against Qt's published hashes, and needs neither.

**Why a commit, not a release (2026-10).** Starting with 6.11, Qt split its Windows packages per compiler
in its repositories. aqtinstall's fix for that was merged in March 2026 (its pull request #1000), but the
newest release, 3.3.0, is from June 2025 and cannot install Qt 6.11 or 6.12. So QGSDK pins the commit
that works (`3.3.1.dev166`). **When aqtinstall publishes a release that includes the fix, switch to it.**

**Why the source zip.** Installing from a git URL needs git on the machine; the zip of the same commit
doesn't. A zip carries no git history, so the bootstrap gives aqtinstall its version explicitly.

**Why it isn't hashed, when Python is.** The commit SHA in the URL already fixes exactly which files are
installed. A hash of the zip would pin the *archive bytes*, and GitHub generates source archives on
demand: their bytes have changed before without the content changing, which would break every bootstrap
for no real reason. Python's NuGet package is a published file that never changes, so its hash is safe.
Please don't "fix" this into a hash pin.

**Its dependencies are locked.** Everything aqtinstall needs, and the build tools that build it, are in
`bootstrap/tooling-requirements.txt`, pinned with hashes and installed with `--require-hashes`;
aqtinstall itself is then installed with `--no-deps --no-build-isolation`, so nothing else is fetched.
