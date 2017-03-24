import logging
import os
from typing import NamedTuple
import queue

import git
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QMetaObject
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LOGGER = logging.getLogger(__name__)


class RepoFsEvtHandler(FileSystemEventHandler):
    def __init__(self, delegate, root):
        super().__init__()
        self._root = root
        self._delegate = delegate

    @property
    def path(self):
        return self._root

    def on_deleted(self, event):
        # print("RepoFsEvtHandler.on_deleted",event.src_path)
        self._delegate.onEvent(self._root, event.src_path)

    def on_any_event(self, event):
        # print("RepoFsEvtHandler.on_any_event",event.src_path)
        self._delegate.onEvent(self._root, event.src_path)


ScheduledFsEvtHandler = NamedTuple('ScheduledFsEvtHandler',
                                   [('handler', object), ('watch', object)])


class RepoFsWatcher(QObject):
    """Track changes in filesystem within a git repository"""
    # use signal to start tracking given given repository directory
    track = pyqtSignal(str)

    # signal gets emitted when content of given repository directory has changed
    repoChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fsObserver = None
        self._fsEvtHandlers = {}
        self._queue = queue.Queue()
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._onFlushQueue)
        self.track.connect(self.startTracking)

    @pyqtSlot(str)
    def startTracking(self, path):
        """Start tracking changes in given directory"""
        if path in self._fsEvtHandlers:
            LOGGER.warning("Already tracking {}".format(path))
            return
        if not os.path.isdir(path) and not os.path.isfile(path):
            LOGGER.warning("Can't track {}".format(path))
            return
        if not self._fsObserver:
            self._fsObserver = Observer()
            self._fsObserver.start()
        LOGGER.warning("Starting to track {}...".format(path))
        handler = RepoFsEvtHandler(self, path)
        watch = self._fsObserver.schedule(handler, handler.path, True)
        self._fsEvtHandlers[handler.path] = ScheduledFsEvtHandler(handler, watch)
        LOGGER.warning("Tracking {}".format(handler.path))

    @pyqtSlot(str)
    def stopTracking(self, path=None):
        """Stop tracking changes in given directory. Default is to stop tracking on all
         known directories."""
        if not self._fsObserver:
            return
        if path in self._fsEvtHandlers:
            LOGGER.info("Stopping to track {}".format(path))
            scheduled = self._fsEvtHandlers.pop(path)
            self._fsObserver.unschedule(scheduled.watch)
            LOGGER.info("Stopped tracking {}".format(path))
        if not path:
            LOGGER.info("Stopping to track anything...")
            allPaths = list(self._fsEvtHandlers.keys())
            [self.stopTracking(p) for p in allPaths]
            self._fsObserver.stop()
            if self._fsObserver.isAlive():
                self._fsObserver.join()
            self._fsObserver = None
            LOGGER.info("Stopped to track anything")

    def ignored(self, repo, path):
        """Returns true when given path is not part of given repository"""
        valid = repo.git.ls_files(path, with_exceptions=False).strip()
        if not valid:
            return True  # path is not part of current repository
        ignored = repo.git.check_ignore(path, with_exceptions=False).strip()
        if ignored:
            return True  # path is ignored in current repository
        return False

    @pyqtSlot()
    def _onFlushQueue(self):
        """Handle all queued path changes and filter them to forward only one event by repository"""
        # gather queued files by root directory and eliminate duplicates
        roots = {}
        while not self._queue.empty():
            root, path = self._queue.get_nowait()
            if root not in roots:
                roots[root] = set()
            roots[root].add(path)
        # handle all the changed paths, start with the longest root directory, i.e. submodules
        orderedRoots = list(roots.keys())
        orderedRoots.sort(key=lambda x: len(x), reverse=True)
        triggeredPaths = set()  # paths that are already considered changed
        for root in orderedRoots:
            repo = git.Repo(root)
            paths = [p for p in roots[root]
                     if p not in triggeredPaths and not self.ignored(repo, p)]
            if paths:
                LOGGER.debug("RepoFsEvtHandler._onFlushQueue {}".format(root))
                self.repoChanged.emit(root)
                [triggeredPaths.add(p) for p in paths]

    def onEvent(self, root, path):
        """Handle event from fs handler for path within root directory"""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1]
        isWithinGit = ".git" in path.split(os.sep)
        if name == ".git":
            return  # discard changes to git directory
        if isWithinGit:
            gitPathParts = path.split(os.sep)
            gitPathParts = gitPathParts[gitPathParts.index(".git"):]
            dotGitPath = "/".join(gitPathParts)
            if ext.endswith(".lock"):
                return  # discard changes to git lock files
            if name == "index":
                return  # discard changes to git index directory
            if name == "PREPARE_COMMIT_MSG":
                return  # discard changes to git commit message file
            if name in ("tortoisegit.index", "tortoisegit.data"):
                return  # discard changes to tortoisegit cache files
            if "objects" in gitPathParts:
                return  # discard changes to git object files
            if dotGitPath.startswith(r".git/modules") and \
                    os.path.isfile(os.path.join(path, "index")):
                return  # discard special submodule directories
            if dotGitPath.startswith(r".git/hooks"):
                return  # discard special hook paths
            if dotGitPath.startswith(r".git/lfs/tmp"):
                return  # discard special lfs paths

        LOGGER.debug("RepoFsEvtHandler.onEvent {}".format(path))
        self._queue.put((root, path))
        QMetaObject.invokeMethod(self._timer, "start", Qt.QueuedConnection)
