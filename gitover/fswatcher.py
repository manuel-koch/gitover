import logging
import os
import queue

import git
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QMetaObject
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QFileSystemWatcher

LOGGER = logging.getLogger(__name__)


class RepoFsWatcher(QObject):
    # use signal to start tracking given given repository directory
    track = pyqtSignal(str)

    # signal gets emitted when content of given repository directory has changed
    repoChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fswatcher = QFileSystemWatcher(self)
        self._fswatcher.fileChanged.connect(self._onFileChanged)
        self._fswatcher.directoryChanged.connect(self._onDirChanged)
        self._changedQueue = queue.Queue()
        self._updateTrackQueue = queue.Queue()
        self._flushChangedTimer = QTimer(self)
        self._flushChangedTimer.setInterval(5000)
        self._flushChangedTimer.setSingleShot(True)
        self._flushChangedTimer.timeout.connect(self._onFlushChanged)
        self._updateTrackTimer = QTimer(self)
        self._updateTrackTimer.setInterval(5000)
        self._updateTrackTimer.setSingleShot(True)
        self._updateTrackTimer.timeout.connect(self._onUpdateTrack)
        self._repos = []
        self._dirSnapshots = {}
        self.track.connect(self.startTracking)

    def ignored(self, repo, path):
        """Returns true when given path is not part of given repository"""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1]
        if name in (".DS_Store", "__pycache__"):
            return True  # a known file type to be ignored

        if path in (repo.working_dir, repo.git_dir):
            return False
        isWithinGit = path.startswith(repo.git_dir + os.sep)
        isWithinWork = path.startswith(repo.working_dir + os.sep)
        if not isWithinGit and not isWithinWork:
            return True  # not part of this repository

        if isWithinGit:
            gitRelPath = path[len(repo.git_dir) + 1:]
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

        submodulRoots = [r.abspath for r in repo.submodules]
        isSubmodule = [r for r in submodulRoots if path == r or path.startswith(r + os.sep)]
        if isSubmodule:
            return True  # path is part of submodule

        if not isWithinGit:
            ignored = repo.git.check_ignore(path, with_exceptions=False).strip()
            if ignored:
                return True  # path is ignored in current repository

        return False

    @pyqtSlot(str)
    def startTracking(self, path):
        self._repos += [git.Repo(path)]
        self._updateTracking(self._repos[-1])

    @pyqtSlot(str)
    def stopTracking(self, path=None):
        if path:
            for repo in self._repos:
                if repo.working_dir == path:
                    self._stopTracking(repo, repo.working_dir)
                    self._stopTracking(repo, repo.git_dir)
                    self._repos.remove(repo)
                    break
        else:
            LOGGER.info("Stop tracking...")
            trackedPaths = self._fswatcher.files() + self._fswatcher.directories()
            if trackedPaths:
                self._fswatcher.removePaths(trackedPaths)
            self._repos = []
            LOGGER.info("Stopped tracking")

    def _stopTracking(self, repo, path):
        LOGGER.debug("Stop tracking\n\t in repo %s\n\tfor path %s", repo.working_dir, path)
        untrackPaths = [p for p in self._fswatcher.files() + self._fswatcher.directories()
                        if (p == path or p.startswith(path + os.sep)) \
                        and not self.ignored(repo, p)]
        untrackPaths += [path]
        self._fswatcher.removePaths(untrackPaths)
        nofFiles = len(self._fswatcher.files())
        nofDirs = len(self._fswatcher.directories())
        LOGGER.debug("Tracking %d files and %d directories", nofFiles, nofDirs)

    def _updateTracking(self, repo, basepath=None):
        if not basepath:
            self._updateTracking(repo, repo.working_dir)
            self._updateTracking(repo, repo.git_dir)
            return
        if not os.path.exists(basepath) or self.ignored(repo, basepath):
            return
        LOGGER.debug("Update tracking\n\t in repo %s\n\tfor path %s", repo.working_dir, basepath)
        addTrackPaths = set([basepath])
        for root, dirs, files in os.walk(basepath):
            if root == repo.git_dir and "objects" in dirs:
                dirs.remove("objects")
            for ignoredDir in [path for path in dirs if
                               self.ignored(repo, os.path.join(root, path))]:
                dirs.remove(ignoredDir)
                LOGGER.debug("IGN %s: %s", repo.working_dir, os.path.join(root, ignoredDir))
            for ignoredFile in [path for path in files if
                                self.ignored(repo, os.path.join(root, path))]:
                files.remove(ignoredFile)
                LOGGER.debug("IGN %s: %s", repo.working_dir, os.path.join(root, ignoredFile))
            [addTrackPaths.add(os.path.join(root, path)) for path in dirs]
            [addTrackPaths.add(os.path.join(root, path)) for path in files]
        trackedPaths = set(self._fswatcher.files() + self._fswatcher.directories())
        addTrackPaths -= trackedPaths
        if not addTrackPaths:
            return
        failedPaths = self._fswatcher.addPaths(addTrackPaths)
        for failedPath in failedPaths:
            LOGGER.error("Failed to track path %s", failedPath)
        trackedPaths = self._fswatcher.files() + self._fswatcher.directories()
        trackedPaths.sort()
        nofFiles = len(self._fswatcher.files())
        nofDirs = len(self._fswatcher.directories())
        LOGGER.debug("Tracking %d files and %d directories", nofFiles, nofDirs)

    @pyqtSlot(str)
    def _onFileChanged(self, path):
        LOGGER.debug("FsWatcher._onFileChanged %s", path)
        self._queueChangedPath(path)

    def _compareDirSnapshots(self, path):
        if not path in self._dirSnapshots:
            self._dirSnapshots[path] = set()
        if os.path.isdir(path):
            paths = set([os.path.join(path, p) for p in os.listdir(path)])
        else:
            paths = set()
        diff = bool(paths.difference(self._dirSnapshots[path]))
        self._dirSnapshots[path] = paths
        return diff

    @pyqtSlot(str)
    def _onDirChanged(self, path):
        LOGGER.debug("FsWatcher._onDirChanged %s", path)
        if self._compareDirSnapshots(path):
            self._queueChangedPath(path)
            self._queueTrackUpdate(path)

    def _queueChangedPath(self, path):
        self._changedQueue.put(path)
        QMetaObject.invokeMethod(self._flushChangedTimer, "start", Qt.QueuedConnection)

    def _queueTrackUpdate(self, path):
        self._updateTrackQueue.put(path)
        QMetaObject.invokeMethod(self._updateTrackTimer, "start", Qt.QueuedConnection)

    @pyqtSlot()
    def _onUpdateTrack(self):
        # gather queued track updates, eliminate duplicates and take the top-most
        # of all directory trees
        paths = set()
        while not self._updateTrackQueue.empty():
            path = self._updateTrackQueue.get_nowait()
            isChild = [p for p in paths if path.startswith(p + os.sep)]
            children = set([p for p in paths if p.startswith(path + os.sep)])
            paths -= children
            if not isChild:
                paths.add(path)
        for path in paths:
            [self._updateTracking(repo, path) for repo in self._repos]

    @pyqtSlot()
    def _onFlushChanged(self):
        """Handle all queued path changes and filter them to forward only one event by repository"""
        # gather queued files and eliminate duplicates
        paths = set()
        while not self._changedQueue.empty():
            paths.add(self._changedQueue.get_nowait())
        # handle all the changed paths, start with the longest root directory, i.e. submodules
        paths = list(paths)
        roots = set()
        for repo in self._repos:
            repoPaths = [path for path in paths if not self.ignored(repo, path)]
            if repoPaths:
                roots.add(repo.working_dir)
        for root in roots:
            LOGGER.info("Repository filesystem change detected: %s", root)
            self.repoChanged.emit(root)
