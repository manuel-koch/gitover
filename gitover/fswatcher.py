import logging
import os
import subprocess
import time

import git

from PyQt5.QtCore import QDir, QProcess, QThread
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileSystemModel

LOGGER = logging.getLogger(__name__)


class RepoFsWatcher(QObject):
    # use signal to start tracking given given repository directory
    track = pyqtSignal(str)

    # signal gets emitted when content of given repository directory has changed
    repoChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trackers = []
        self.track.connect(self.startTracking)

        self._changes = set()
        self._flushChangesTimer = QTimer(self)
        self._flushChangesTimer.setInterval(1000)
        self._flushChangesTimer.setSingleShot(True)
        self._flushChangesTimer.timeout.connect(self._onFlushChanges)

    @pyqtSlot(str)
    def startTracking(self, path):
        tracker = RepoTracker(path, self)
        self._trackers += [tracker]
        tracker.repoChanged.connect(self._onRepoChanged)

    def _onRepoChanged(self, path):
        self._changes.add(path)
        self._flushChangesTimer.start()

    def _onFlushChanges(self):
        for path in self._changes:
            LOGGER.info("Repo changed {}".format(path))
            self.repoChanged.emit(path)
        self._changes = set()

    def stopTracking(self):
        for tracker in self._trackers:
            tracker.stop()
            tracker.deleteLater()
        self._trackers = []


class RepoTracker(QObject):
    # signal gets emitted when content of repository has changed
    repoChanged = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self._path = path
        self._name = os.path.basename(self._path)
        LOGGER.debug("Creating tracker for repo at {}".format(self._path))
        repo = git.Repo(self._path)
        self._working_dir = repo.working_dir
        self._git_dir = repo.git_dir
        distinct_git_dir = not (self._git_dir + os.sep).startswith(self._working_dir)
        self._initial_mtime = time.time()
        self._mods = {}
        if FsWatcher.supported():
            self._fsRoot = FsWatcher(self._working_dir, self)
            self._fsRoot.pathChanged.connect(self._update)
        else:
            self._fsRoot = self._createFsModel(self._working_dir,
                                               self._onRootDirLoaded, self._onRootAboutToBeRemoved)
        if distinct_git_dir:
            if FsWatcher.supported():
                self._fsGit = FsWatcher(self._git_dir, self)
                self._fsGit.pathChanged.connect(self._update)
            else:
                self._fsGit = self._createFsModel(self._git_dir,
                                                  self._onGitDirLoaded, self._onGitAboutToBeRemoved)
        else:
            self._fsGit = None

    def stop(self):
        if isinstance(self._fsRoot, FsWatcher):
            self._fsRoot.stop()
        if isinstance(self._fsGit, FsWatcher):
            self._fsGit.stop()

    def _createFsModel(self, path, onDirLoaded, onAboutToBeRemoved):
        fs = QFileSystemModel(self)
        fs.setFilter(QDir.AllEntries | QDir.Hidden | QDir.NoDot | QDir.NoDotDot)
        fs.setReadOnly(True)
        fs.setRootPath(path)
        fs.directoryLoaded.connect(onDirLoaded)
        fs.rowsAboutToBeRemoved.connect(onAboutToBeRemoved)
        return fs

    @pyqtSlot(str)
    def _update(self, path):
        try:
            if os.path.exists(path):
                old_mtime = self._mods.get(path, 0)
                new_mtime = os.stat(path).st_mtime
                self._mods[path] = new_mtime
                if old_mtime == new_mtime or new_mtime < self._initial_mtime:
                    path = None
            else:
                self._mods.pop(path, None)
            if path:
                if not self.ignored(path) and not self.discarded(path):
                    LOGGER.info("Changed ({}): {}".format(self._name, path))
                    self.repoChanged.emit(self._path)
        except Exception as e:
            LOGGER.error("Failed to update mtime '{}': {}".format(path, e))

    def _onRootDirLoaded(self, path):
        self._onDirLoaded(self._fsRoot, path)

    def _onGitDirLoaded(self, path):
        self._onDirLoaded(self._fsGit, path)

    def _onDirLoaded(self, fs, path):
        if self.ignored(path):
            return
        repo = None
        idx = fs.index(path)
        LOGGER.info("Tracking ({}): {}".format(self._name, path))
        self._update(path)
        for r in range(fs.rowCount(idx)):
            repo = repo or git.Repo(self._working_dir)
            childidx = fs.index(r, 0, idx)
            childpath = fs.filePath(childidx)
            if fs.canFetchMore(childidx) and not self.ignored(childpath, repo):
                fs.fetchMore(childidx)
            self._update(childpath)

    def _onRootAboutToBeRemoved(self, parent, first, last):
        self._onAboutToBeRemoved(self._fsRoot, parent, first, last)

    def _onGitAboutToBeRemoved(self, parent, first, last):
        self._onAboutToBeRemoved(self._fsGit, parent, first, last)

    def _onAboutToBeRemoved(self, fs, parent, first, last):
        for r in range(first, last + 1):
            idx = fs.index(r, 0, parent)
            path = fs.filePath(idx)
            LOGGER.info("Removed ({}): {}".format(self._name, path))
            self._mods.pop(path, None)
            if not self.ignored(path) and not self.discarded(path):
                self.repoChanged.emit(self._path)

    def discarded(self, path):
        """Returns true when changes to given path are discarded"""
        if path in (self._working_dir, self._git_dir):
            return True
        isWithinGit = path.startswith(self._git_dir + os.sep)
        if not isWithinGit and os.path.isdir(path):
            return True
        return False

    def ignored(self, path, repo=None):
        """Returns true when given path is not part of given repository"""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1]
        if name in (".DS_Store", "__pycache__"):
            return True  # a known file type to be ignored

        if path in (self._working_dir, self._git_dir):
            return False

        if os.path.isdir(path) and path.endswith(os.sep + "objects"):
            inside_git_dir = git.Git(path).rev_parse(is_inside_git_dir=True) == "true"
            if inside_git_dir:
                return True

        isWithinGit = path.startswith(self._git_dir + os.sep)
        isWithinWork = path.startswith(self._working_dir + os.sep)
        if not isWithinGit and not isWithinWork:
            return True  # not part of this repository

        if isWithinGit:
            gitRelPath = path[len(self._git_dir) + 1:]
            if ext in (".lock", ".cache"):
                return True  # discard changes to git lock/cache files
            if name == "hooks":
                return True  # discard changes to git hooks directory
            if name == "modules":
                return True  # discard changes to git modules directory
            if name in ("PREPARE_COMMIT_MSG", "COMMIT_EDITMSG", "GIT_COLA_MSG"):
                return True  # discard changes to git commit message file
            if gitRelPath == "objects":
                return True  # discard changes to git object files
            if gitRelPath == "lfs/tmp":
                return True  # discard special lfs paths
            if gitRelPath == "packed-refs":
                return True  # discard packed refs paths
            if gitRelPath == "sourcetreeconfig":
                return True  # discard SourceTree configuration

        repo = repo or git.Repo(self._working_dir)
        submodulRoots = [r.abspath for r in repo.submodules]
        isSubmodule = [r for r in submodulRoots if path == r or path.startswith(r + os.sep)]
        if isSubmodule:
            return True  # path is part of submodule

        if not isWithinGit:
            ignored = repo.git.check_ignore(path, with_exceptions=False).strip()
            if ignored:
                return True  # path is ignored in current repository

        return False


NUL = b"\0"


class FsWatcher(QProcess):
    # signal gets emitted when path changed ( created, modified or deleted )
    pathChanged = pyqtSignal(str)

    _triggerStop = pyqtSignal()

    _is_supported = None

    @classmethod
    def supported(cls):
        if cls._is_supported is None:
            exitcode, out = subprocess.getstatusoutput("fswatch --version")
            if exitcode == 0:
                LOGGER.info("Fswatch is supported: {}".format(out.split("\n")[0]))
                cls._is_supported = True
            else:
                LOGGER.info("Fswatch not supported")
                cls._is_supported = False
        return cls._is_supported

    def __init__(self, path, parent=None):
        """Start watching given base directory"""
        super().__init__(parent)
        self._triggerStop.connect(self._stop)
        self._running = False
        self._path = path
        self._buffer = bytes()
        self.setProcessChannelMode(QProcess.ForwardedErrorChannel)
        self.setWorkingDirectory(self._path)
        cmd = "fswatch -0 -m fsevents_monitor ."
        self.readyReadStandardOutput.connect(self._onStdout)
        LOGGER.info("Starting fswatch for {}...".format(self._path))
        self.start(cmd)
        self.waitForStarted()
        LOGGER.info("Started fswatch for {}".format(self._path))
        self._running = True

    @pyqtSlot()
    def _stop(self):
        LOGGER.debug("Term fswatch for {}...".format(self._path))
        self.terminate()
        if not self.waitForFinished(1):
            LOGGER.debug("Kill fswatch for {}...".format(self._path))
            self.kill()
            self.waitForFinished(1)
        self._running = False

    def stop(self):
        LOGGER.info("Stopping fswatch for {}...".format(self._path))
        self._triggerStop.emit()
        while self._running:
            QThread.sleep(0.1)
        LOGGER.info("Stopped fswatch for {}".format(self._path))

    @pyqtSlot()
    def _onStdout(self):
        """Handle output of `fswatch`, changed paths separated by NUL byte."""
        paths = set()
        self._buffer += bytes(self.readAllStandardOutput())
        while NUL in self._buffer:
            path, self._buffer = self._buffer.split(NUL, maxsplit=1)
            paths.add(path.decode('utf-8'))
        for path in paths:
            LOGGER.debug("Got change for {} in {}".format(path, self._path))
            self.pathChanged.emit(path)
