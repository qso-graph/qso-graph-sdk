// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 the QGSDK contributors (see AUTHORS). Part of QGSDK; see LICENSE.
// Opens a window. With --smoke it closes again once the event loop is running and exits 0, so CI can
// prove the program starts (run with QT_QPA_PLATFORM=offscreen where there is no display).
#include <QApplication>
#include <QLabel>
#include <QTimer>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    QLabel window(QStringLiteral("QGSDK fixture: Qt %1").arg(QString::fromLatin1(qVersion())));
    window.resize(360, 120);
    window.show();
    if (app.arguments().contains(QStringLiteral("--smoke")))
        QTimer::singleShot(0, &app, &QApplication::quit);
    return app.exec();
}
