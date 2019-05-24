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

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, qInstallMessageHandler, QThreadPool, QTimer, QMetaObject, QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtQuick import QQuickView

from gitover.ui.resources import gitover_commit_sha, gitover_version
from gitover.repos_model import ReposModel, Repo, ChangedFilesModel, OutputModel, CommitDetails
from gitover.formatter import GitDiffFormatter
from gitover.res_helper import getResourceUrl
from gitover.wakeup import WakeupWatcher

LOGGER = logging.getLogger(__name__)


def messageHandler(msgType, context, msg):
    if msgType == QtCore.QtCriticalMsg or msgType == QtCore.QtFatalMsg:
        logfunc = LOGGER.error
    elif msgType == QtCore.QtWarningMsg:
        logfunc = LOGGER.warning
    elif msgType == QtCore.QtDebugMsg:
        logfunc = LOGGER.debug
    else:
        logfunc = LOGGER.info
    logfunc("{}({}): {}".format(context.file, context.line, msg))


def position_window(wnd, x, y):
    if x is not None:
        wnd.setProperty("x", x)
    if y is not None:
        wnd.setProperty("y", y)


def size_window(wnd, w, h):
    if w is not None:
        wnd.setProperty("width", w)
    if h is not None:
        wnd.setProperty("height", h)


def reposition_window(wnd):
    LOGGER.info("Workaround: reposition window")
    x = wnd.x()
    y = wnd.y()
    position_window(wnd, x + 1, y + 1)
    position_window(wnd, x, y)


def resize_window(wnd):
    LOGGER.info("Workaround: resize window")
    w = wnd.width()
    h = wnd.height()
    size_window(wnd, w - 32, h - 32)
    size_window(wnd, w, h)


def open_and_close_about_dlg(wnd):
    LOGGER.info("Workaround: opening about dialog")
    aboutDialog = wnd.findChildren(QObject, "theAboutDialog")[0]
    try:
        QMetaObject.invokeMethod(aboutDialog, "openDialog")
        QTimer.singleShot(50, lambda: QMetaObject.invokeMethod(aboutDialog, "closeDialog"))
    except:
        LOGGER.exception("Failed to apply workaround")


def fix_hanging_qml_renderer(wnd):
    resize_window(wnd)
    open_and_close_about_dlg(wnd)


def run_gui(repo_paths, watch_filesystem, nof_bg_threads):
    """Run GUI application"""
    LOGGER.info("Starting...")

    # Customize application
    app = QGuiApplication([])
    app.setOrganizationName("MKO")
    app.setOrganizationDomain("mko.com")
    app.setApplicationName("GitOver")
    app.setApplicationVersion("{}".format(gitover_version))
    app.setWindowIcon(QIcon(":/icon.png"))

    QThread.currentThread().setObjectName("mainThread")
    QThreadPool.globalInstance().setMaxThreadCount(nof_bg_threads)

    wakeupWatcher = WakeupWatcher()

    LOGGER.info("{} ({})".format(app.applicationName(), app.applicationVersion()))

    qInstallMessageHandler(messageHandler)

    ReposModel.registerToQml()
    Repo.registerToQml()
    ChangedFilesModel.registerToQml()
    OutputModel.registerToQml()
    GitDiffFormatter.registerToQml()
    CommitDetails.registerToQml()

    settings = QSettings()
    settings.beginGroup("MainWindow")
    x = settings.value("x")
    y = settings.value("y")
    w = settings.value("width", 300)
    h = settings.value("height", 600)
    settings.endGroup()

    repos = ReposModel(watch_filesystem=watch_filesystem)
    [repos.addRepoByPath(path, defer=True) for path in repo_paths]

    engine = QQmlApplicationEngine(app)
    engine.setOutputWarningsToStandardError(True)
    engine.rootContext().setContextProperty("globalVersion", gitover_version)
    engine.rootContext().setContextProperty("globalCommitSha", gitover_commit_sha)
    engine.rootContext().setContextProperty("globalRepositories", repos)
    engine.load(getResourceUrl("qml/Main.qml"))

    wnd = engine.rootObjects()[0]
    wnd.title = app.applicationName()
    wnd.setProperty("title", app.applicationName())
    wnd.setProperty("width", w)
    wnd.setProperty("height", h)
    position_window(wnd, x, y)

    # workaround context menus at wrong position after wakeup from sleeping !?
    wakeupWatcher.awake.connect(lambda: reposition_window(wnd))

    # workaround QML renderer that appears stuck
    wakeupWatcher.awake.connect(lambda: fix_hanging_qml_renderer(wnd))

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
    wakeupWatcher = None
    app = None

    LOGGER.info("Done.")
    return result
