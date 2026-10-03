# 0001: MinGW, not MSVC, on Windows

**Decided:** QGLogger is built on Windows with MinGW (GCC), using the MinGW build Qt publishes.

**Why.** MSVC needs Visual Studio or its Build Tools installed first: a large install, admin rights, and
a Microsoft licence to accept. MinGW comes with Qt's own packages and installs into QGSDK's folder like
everything else. That keeps QGSDK at **zero prerequisites**, which is the property that let JTSDK64
(the same idea for WSJT-X) be handed between maintainers. The cost of MinGW falls on us once, in QGSDK;
the cost of MSVC would fall on every future maintainer, every time they set up a machine.

**Watch for.** Qt's MinGW binaries are matched to one compiler version (MinGW 13.1.0 for Qt 6.12).
Mixing versions produces crashes that look like application bugs, so the compiler is pinned in
`manifest.json` beside Qt. Libraries that ship only MSVC builds have to be built from source or avoided.
