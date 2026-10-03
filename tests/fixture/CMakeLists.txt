# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
# A tiny Qt Widgets program that proves an QGSDK installation can build and run a Qt application,
# without needing the QGLogger repository. QGLogger itself is the real acceptance test (docs/m0.md).
cmake_minimum_required(VERSION 3.25)
project(qgsdk-fixture VERSION 0.1 LANGUAGES CXX)

find_package(Qt6 6.11 REQUIRED COMPONENTS Widgets)
qt_standard_project_setup()

qt_add_executable(qgsdk-fixture WIN32 src/main.cpp)
target_link_libraries(qgsdk-fixture PRIVATE Qt6::Widgets)
