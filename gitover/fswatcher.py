import logging
import os
import time

import git

from PyQt5.QtCore import QDir
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
        self._flushChangesTimer.setInterval(2000)
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
            tracker.deleteLater()
        self._trackers = []


class RepoTracker(QObject):
    # signal gets emitted when content of repository has changed
    repoChanged = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self._path = path
        self._name = os.path.basename(self._path)
        repo = git.Repo(self._path)
        self._working_dir = repo.working_dir
        self._git_dir = repo.git_dir
        distinct_git_dir = not (self._git_dir + os.sep).startswith(self._working_dir)
        self._initial_mtime = time.time()
        self._mods = {}
        self._fsRoot = self._createFsModel(self._working_dir,
                                           self._onRootDirLoaded, self._onRootAboutToBeRemoved)
        if distinct_git_dir:
            self._fsGit = self._createFsModel(self._git_dir,
                                              self._onGitDirLoaded, self._onGitAboutToBeRemoved)
        else:
            self._fsGit = None

    def _createFsModel(self, path, onDirLoaded, onAboutToBeRemoved):
        fs = QFileSystemModel(self)
        fs.setFilter(QDir.AllEntries | QDir.Hidden | QDir.NoDot | QDir.NoDotDot)
        fs.setReadOnly(True)
        fs.setRootPath(path)
        fs.directoryLoaded.connect(onDirLoaded)
        fs.rowsAboutToBeRemoved.connect(onAboutToBeRemoved)
        return fs

    def _update(self, path):
        try:
            old_mtime = self._mods.get(path, 0)
            new_mtime = os.stat(path).st_mtime
            self._mods[path] = new_mtime
            if old_mtime != new_mtime and new_mtime >= self._initial_mtime:
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
