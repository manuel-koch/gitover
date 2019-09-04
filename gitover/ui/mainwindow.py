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
from collections import namedtuple

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, qInstallMessageHandler, QThreadPool, pyqtSlot, QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtQuick import QQuickView

from gitover.ui.resources import gitover_commit_sha, gitover_version, gitover_build_time
from gitover.repos_model import ReposModel, Repo, ChangedFilesModel, OutputModel, CommitDetails
from gitover.formatter import GitDiffFormatter
from gitover.res_helper import getResourceUrl
from gitover.wakeup import WakeupWatcher
from gitover.updater import get_latest_version, is_version_greater
from gitover.launcher import Launcher

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


def reposition_window(wnd):
    LOGGER.info(f"Repositioning {wnd}")
    x = wnd.x()
    y = wnd.y()
    position_window(wnd, x + 1, y + 1)
    position_window(wnd, x, y)


WindowContext = namedtuple("WindowContext", ("engine", "window", "repos"))


class Windows(QObject):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._contexts = []

    def create(self, watch_filesystem=True, paths=None, context=None):
        paths = paths or []
        context = (context or {}).copy()

        repos = ReposModel(watch_filesystem=watch_filesystem)
        [repos.addRepoByPath(path, defer=True) for path in paths]

        engine = QQmlApplicationEngine(self._app)
        engine.setOutputWarningsToStandardError(True)

        context["globalRepositories"] = repos
        for k, v in context.items():
            if k.startswith("global"):
                engine.rootContext().setContextProperty(k, v)

        engine.load(getResourceUrl("qml/Main.qml"))

        settings = QSettings()
        settings.beginGroup("MainWindow")
        x = settings.value("x")
        y = settings.value("y")
        w = settings.value("width", 300)
        h = settings.value("height", 600)
        settings.endGroup()

        wnd = engine.rootObjects()[0]
        wnd.title = self._app.applicationName()
        wnd.setProperty("title", self._app.applicationName())
        wnd.setProperty("width", w)
        wnd.setProperty("height", h)
        position_window(wnd, x, y)
        wnd.closing.connect(self._onClose)

        self._contexts.append(WindowContext(engine, wnd, repos))

    def _onClose(self, closeEvt):
        wnd = self.sender()
        if len(self._contexts) == 1:
            settings = QSettings()
            settings.beginGroup("MainWindow")
            settings.setValue("x", wnd.x())
            settings.setValue("y", wnd.y())
            settings.setValue("width", wnd.width())
            settings.setValue("height", wnd.height())
            settings.endGroup()
        for idx in range(len(self._contexts)):
            if self._contexts[idx].window == wnd:
                self._cleanup_context(self._contexts.pop(idx))
                return

    def cleanup(self):
        while self._contexts:
            self._cleanup_context(self._contexts.pop(-1))

    def _cleanup_context(self, context):
        context.repos.cleanup()

    def reposition_windows(self):
        for idx in self._contexts:
            reposition_window(self._contexts[idx].window)


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

    LOGGER.info("{} ({})".format(app.applicationName(), app.applicationVersion()))

    qInstallMessageHandler(messageHandler)

    Launcher.registerToQml()
    ReposModel.registerToQml()
    Repo.registerToQml()
    ChangedFilesModel.registerToQml()
    OutputModel.registerToQml()
    GitDiffFormatter.registerToQml()
    CommitDetails.registerToQml()

    latest_version, latest_version_url = get_latest_version()

    windows = Windows(app)
    wakeupWatcher = WakeupWatcher()
    launcher = Launcher()
    context = dict(
        globalLauncher=launcher,
        globalVersion=gitover_version,
        globalVersionCanUpdate=is_version_greater(latest_version, gitover_version),
        globalVersionExperimental=is_version_greater(gitover_version, latest_version),
        globalLatestVersion=latest_version,
        globalLatestVersionUrl=latest_version_url,
        globalCommitSha=gitover_commit_sha,
        globalBuildTime=gitover_build_time,
    )
    launcher.openNewWindow[str].connect(
        lambda paths: windows.create(
            watch_filesystem=watch_filesystem, paths=paths, context=context
        )
    )

    windows.create(app, paths=repo_paths, context=context)

    # workaround context menus at wrong position after wakeup from sleeping !?
    wakeupWatcher.awake.connect(lambda: windows.reposition_windows)

    # Run the application
    result = app.exec_()

    windows.cleanup()
    wakeupWatcher = None
    launcher = None
    app = None

    LOGGER.info("Done.")
    return result
