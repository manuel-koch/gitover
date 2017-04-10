# -*- coding: utf-8 -*-
"""
This file is part of Gitover.

Gitover is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Gitover is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Gitover. If not, see <http://www.gnu.org/licenses/>.

Copyright 2017 Manuel Koch

----------------------------

Main window of git overview.
"""
import logging
import os
import sys

import git

from PyQt5 import QtCore
from PyQt5.QtCore import qInstallMessageHandler, QSize, Qt, pyqtSlot
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QGuiApplication, QIcon, QPixmap, QPainter, QColor, QFont, QTextOption
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtQuick import QQuickView

import gitover.ui.resources  # Only need this to get access to embedded Qt resources
from gitover.repos_model import ReposModel, Repo

__version__ = "0.3.0"

LOGGER = logging.getLogger(__name__)


def messageHandler(msgType, context, msg):
    if msgType == QtCore.QtCriticalMsg or msgType == QtCore.QtFatalMsg:
        logfunc = LOGGER.error
    if msgType == QtCore.QtWarningMsg:
        logfunc = LOGGER.warning
    if msgType == QtCore.QtDebugMsg:
        logfunc = LOGGER.debug
    else:
        logfunc = LOGGER.info
    logfunc("{}({}): {}".format(context.file, context.line, msg))
    if "Must construct a QGuiApplication first." in msg:
        print("CATCH ME")
        import traceback
        traceback.print_stack()


def getResourceUrl(path):
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    if getattr(sys, 'frozen', False):
        return QUrl("qrc:/"+path)
    else:
        return QUrl.fromLocalFile(os.path.join(base_dir, 'res/'+path))


def run_gui(repo_paths):
    """Run GUI application"""
    LOGGER.info("Starting...")

    # Customize application
    app = QGuiApplication([])
    app.setOrganizationName("MKO")
    app.setOrganizationDomain("mko.com")
    app.setApplicationName("GitOver")
    app.setApplicationVersion("{}".format(__version__))
    app.setWindowIcon(QIcon(':/icon.png'))
    QThread.currentThread().setObjectName('mainThread')

    qInstallMessageHandler(messageHandler)

    ReposModel.registerToQml()
    Repo.registerToQml()

    settings = QSettings()
    settings.beginGroup("MainWindow")
    x = settings.value("x")
    y = settings.value("y")
    w = settings.value("width", 300)
    h = settings.value("height", 600)
    settings.endGroup()

    repos = ReposModel()
    for rootpath in repo_paths:
        repos.addRepo(Repo(rootpath))

    engine = QQmlApplicationEngine(app)
    engine.setOutputWarningsToStandardError(True)
    engine.rootContext().setContextProperty("globalVersion", __version__)
    engine.rootContext().setContextProperty("globalRepositories", repos)
    engine.load(getResourceUrl("qml/Main.qml"))

    wnd = engine.rootObjects()[0]
    wnd.title = app.applicationName()
    wnd.setProperty("title", app.applicationName())
    wnd.setProperty("width", w)
    wnd.setProperty("height", h)
    if x is not None:
        wnd.setProperty("x", x)
    if y is not None:
        wnd.setProperty("y", y)

    # Run the application
    result = app.exec_()

    settings = QSettings()
    settings.beginGroup("MainWindow")
    settings.setValue("x", wnd.x())
    settings.setValue("y", wnd.y())
    settings.setValue("width", wnd.width())
    settings.setValue("height", wnd.height())
    settings.endGroup()
    settings = None

    repos.cleanup()
    wnd = None
    engine = None
    repos = None
    app = None

    LOGGER.info("Done.")
    return result
