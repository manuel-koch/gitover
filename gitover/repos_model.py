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

Data model for all repositiories.
"""
import logging
import os
import random
import threading
import time

import git
from PyQt5.QtCore import QModelIndex, pyqtSlot
from PyQt5.QtCore import QVariant
from PyQt5.QtCore import Qt, pyqtProperty, pyqtSignal, QObject
from PyQt5.QtCore import QAbstractItemModel
from PyQt5.QtCore import QThread

from gitover.qml_helpers import QmlTypeMixin

LOGGER = logging.getLogger(__name__)


class ReposModel(QAbstractItemModel, QmlTypeMixin):
    """Model of repository data arranged in rows"""

    nofReposChanged = pyqtSignal(int)

    ROLE_REPO = Qt.UserRole + 1

    def __init__(self, parent=None):
        """Construct repositories model"""
        super().__init__(parent)
        self._repos = []

    def roleNames(self):
        roles = super().roleNames()
        roles[ReposModel.ROLE_REPO] = b"repo"
        return roles

    def index(self, row, col, parent=None):
        return self.createIndex(row, col)

    def rowCount(self, parent=None):
        return len(self._repos)

    def columnCount(self, idx):
        return 1

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid() or idx.row() >= len(self._repos):
            return None

        repo = self._repos[idx.row()]
        if role == Qt.DisplayRole:
            return str(repo)
        if role == ReposModel.ROLE_REPO:
            return QVariant(repo)

        return None

    @pyqtSlot()
    def triggerUpdate(self):
        for repo in self._repos:
            repo.triggerUpdate()

    @pyqtSlot()
    def triggerFetch(self):
        for repo in self._repos:
            repo.triggerFetch()

    @pyqtSlot()
    def stopWorker(self):
        for repo in self._repos:
            repo.stopWorker()

    @pyqtProperty(int, notify=nofReposChanged)
    def nofRepos(self):
        return self.rowCount()

    @pyqtSlot('QUrl')
    def addRepoByUrl(self, url):
        path = url.toLocalFile()
        try:
            is_git = bool(git.Repo(path).head)
            self.addRepo(Repo(path))
        except:
            LOGGER.exception("Path is not a git repo: {}".format(path))

    def addRepo(self, repo):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        repo.setParent(self)
        self._repos += [repo]
        LOGGER.debug("Added repo {}".format(repo))
        self.endInsertRows()
        self.nofReposChanged.emit(self.nofRepos)

        rootpath = repo.path
        subpaths = [r.abspath for r in git.Repo(rootpath).submodules]
        subpaths.sort(key=str.lower)
        for subpath in subpaths:
            name = subpath[len(rootpath) + 1:]
            self.addRepo(Repo(subpath, name))


class GitStatus(object):
    def __init__(self, path):
        self.path = path
        self.branch = ""
        self.branches = []
        self.trackingBranch = ""
        self.trackingBranchAhead = 0
        self.trackingBranchBehind = 0
        self.trunkBranch = ""
        self.trunkBranchAhead = 0
        self.trunkBranchBehind = 0

    def update(self):
        """Update info from current git repository"""
        try:
            LOGGER.info("Updating status repository at {}".format(self.path))
            repo = git.Repo(self.path)
        except:
            LOGGER.exception("Invalid repository at {}".format(self.path))
            return

        try:
            self.branch = repo.active_branch.name
        except TypeError:
            self.branch = "detached"

        try:
            branches = [b.name for b in repo.branches]
            branches.sort(key=str.lower)
            self.branches = branches
        except:
            LOGGER.exception("Invalid branches for {}".format(self.path))

        try:
            if self.branch and self.branch != "detached":
                remote = repo.git.config("branch.{}.remote".format(self.branch))
                self.trackingBranch = "{}/{}".format(remote, self.branch)
                ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trackingBranch),
                                                  left_right=True, count=True).split("\t")
                self.trackingBranchAhead, self.trackingBranchBehind = int(ahead), int(behind)
        except:
            LOGGER.exception(
                "Failed to get tracking branch ahead/behind counters for {}".format(self.path))

        try:
            if self.branch and self.branch != "detached":
                try:
                    self.trunkBranch = repo.git.config("custom.devbranch")
                except git.GitCommandError:
                    self.trunkBranch = "origin/develop"
                ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trunkBranch),
                                                  left_right=True, count=True).split("\t")
                self.trunkBranchAhead, self.trunkBranchBehind = int(ahead), int(behind)
        except:
            LOGGER.exception(
                "Failed to get trunk branch ahead/behind counters for {}".format(self.path))


class GitStatusWorker(QObject):
    """Host git status update within worker thread"""

    # signal gets emitted to trigger updating given GitStatus
    updatestatus = pyqtSignal(object)

    # signal gets emitted when starting/stopping to update status
    statusprogress = pyqtSignal(bool)

    # signal gets emitted when given GitStatus has been updated
    statusupdated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.updatestatus.connect(self._onUpdateStatus)

    @pyqtSlot(object)
    def _onUpdateStatus(self, status):
        """Update selected GitStatus of a git repo"""
        self.statusprogress.emit(True)
        try:
            status.update()
        except:
            LOGGER.exception("Failed to update git status at {}".format(status.path))
        self.statusupdated.emit(status)
        self.statusprogress.emit(False)


class GitFetchWorker(QObject):
    """Host git fetch action within worker thread"""

    concurrent_fetch_count = 0
    concurrent_fetch_lock = threading.Lock()
    max_concurrent_fetch_count = 8

    # signal gets emitted to trigger updating given repo root path
    fetch = pyqtSignal(str)

    # signal gets emitted when starting/stopping fetch action
    fetchprogress = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.fetch.connect(self._onFetch)

    def _aquireFetchSlot(self):
        """Try to aquire fetch slot, returns true on success.
        Caller should retry with delay to aquire again."""
        with GitFetchWorker.concurrent_fetch_lock:
            if GitFetchWorker.concurrent_fetch_count > GitFetchWorker.max_concurrent_fetch_count:
                return False
            GitFetchWorker.concurrent_fetch_count += 1
        return True

    def _releaseFetchSlot(self):
        """Release fetch slot"""
        with GitFetchWorker.concurrent_fetch_lock:
            if GitFetchWorker.concurrent_fetch_count > 0:
                GitFetchWorker.concurrent_fetch_count -= 1

    @pyqtSlot(str)
    def _onFetch(self, path):
        """Fetch selected repo"""
        self.fetchprogress.emit(True)
        try:
            while not self._aquireFetchSlot():
                # prevent multiple fetch starting instantly
                time.sleep(1 + 1.0 / random.randint(1, 10))
            repo = git.Repo(path)
            repo.git.fetch(prune=True)
        except:
            LOGGER.exception("Failed to fetch git repo at {}".format(path))
        self._releaseFetchSlot()
        self.fetchprogress.emit(False)


class Repo(QObject, QmlTypeMixin):
    """Contains repository information"""

    pathChanged = pyqtSignal(str)
    nameChanged = pyqtSignal(str)
    branchChanged = pyqtSignal(str)
    trackingBranchChanged = pyqtSignal(str)
    trackingBranchAheadChanged = pyqtSignal(int)
    trackingBranchBehindChanged = pyqtSignal(int)
    trunkBranchChanged = pyqtSignal(str)
    trunkBranchAheadChanged = pyqtSignal(int)
    trunkBranchBehindChanged = pyqtSignal(int)
    branchesChanged = pyqtSignal("QStringList")
    updatingChanged = pyqtSignal(bool)
    fetchingChanged = pyqtSignal(bool)

    def __init__(self, path, name="", parent=None):
        super().__init__(parent)
        self.destroyed.connect(self.stopWorker)

        self._path = path
        self._name = name or os.path.basename(self._path)

        self._workerThread = QThread(self, objectName="workerThread-{}".format(name))
        self._workerThread.start()

        self._statusWorker = GitStatusWorker()
        self._statusWorker.moveToThread(self._workerThread)
        self._statusWorker.statusprogress.connect(self._onUpdating)
        self._statusWorker.statusupdated.connect(self._onStatusUpdated)

        self._fetchWorker = GitFetchWorker()
        self._fetchWorker.moveToThread(self._workerThread)
        self._fetchWorker.fetchprogress.connect(self._setFetching)

        self._branch = ""
        self._tracking_branch = ""
        self._tracking_branch_ahead = 0
        self._tracking_branch_behind = 0
        self._trunk_branch = ""
        self._trunk_branch_ahead = 0
        self._trunk_branch_behind = 0
        self._branches = []

        self._updating = False
        self._updateTriggered = False

        self._fetching = False
        self._fetchTriggered = False

        self.triggerUpdate()

    def __str__(self):
        return self._path

    @pyqtSlot()
    def stopWorker(self):
        if self._workerThread.isRunning():
            LOGGER.debug("Stopping worker of {}...".format(self._path))
            self._workerThread.quit()
            self._workerThread.wait()
            LOGGER.debug("Stopped worker of {}".format(self._path))

    @pyqtProperty(bool, notify=updatingChanged)
    def updating(self):
        return self._updating

    def _onUpdating(self, updating):
        if self._updating != updating:
            self._updating = updating
            self.updatingChanged.emit(self._updating)
        if not updating:
            self._updateTriggered = False

    @pyqtSlot()
    def triggerUpdate(self):
        if self._updateTriggered:
            LOGGER.debug("Status update already triggered...")
            return
        self._statusWorker.updatestatus.emit(GitStatus(self._path))
        self._updateTriggered = True

    @pyqtProperty(bool, notify=fetchingChanged)
    def fetching(self):
        return self._fetching

    def _setFetching(self, fetching):
        if self._fetching != fetching:
            self._fetching = fetching
            self.fetchingChanged.emit(self._fetching)
        if not fetching:
            self._fetchTriggered = False
            self.triggerUpdate()

    @pyqtSlot()
    def triggerFetch(self):
        if self._fetchTriggered:
            LOGGER.debug("Fetch already triggered...")
            return
        self._fetchWorker.fetch.emit(self._path)
        self._fetchTriggered = True

    @pyqtSlot(object)
    def _onStatusUpdated(self, status):
        self.branch = status.branch
        self.branches = status.branches
        self.trackingBranch = status.trackingBranch
        self.trackingBranchAhead = status.trackingBranchAhead
        self.trackingBranchBehind = status.trackingBranchBehind
        self.trunkBranch = status.trunkBranch
        self.trunkBranch_ahead = status.trunkBranchAhead
        self.trunkBranch_behind = status.trunkBranchBehind

    @pyqtProperty(str, notify=pathChanged)
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        if self._path != path:
            self._path = path
            self.pathChanged.emit(self._path)

    @pyqtProperty(str, notify=nameChanged)
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if self._name != name:
            self._name = name
            self.nameChanged.emit(self._name)

    @pyqtProperty(str, notify=branchChanged)
    def branch(self):
        return self._branch

    @branch.setter
    def branch(self, branch):
        if self._branch != branch:
            self._branch = branch
            self.branchChanged.emit(self._branch)

    @pyqtProperty(str, notify=trackingBranchChanged)
    def trackingBranch(self):
        return self._tracking_branch

    @trackingBranch.setter
    def trackingBranch(self, branch):
        if self._tracking_branch != branch:
            self._tracking_branch = branch
            self.trackingBranchChanged.emit(self._tracking_branch)

    @pyqtProperty(int, notify=trackingBranchAheadChanged)
    def trackingBranchAhead(self):
        return self._tracking_branch_ahead

    @trackingBranchAhead.setter
    def trackingBranchAhead(self, ahead):
        if self._tracking_branch_ahead != ahead:
            self._tracking_branch_ahead = ahead
            self.trackingBranchAheadChanged.emit(self._tracking_branch_ahead)

    @pyqtProperty(int, notify=trackingBranchBehindChanged)
    def trackingBranchBehind(self):
        return self._tracking_branch_behind

    @trackingBranchBehind.setter
    def trackingBranchBehind(self, behind):
        if self._tracking_branch_behind != behind:
            self._tracking_branch_behind = behind
            self.trackingBranchBehindChanged.emit(self._tracking_branch_behind)

    @pyqtProperty(str, notify=trunkBranchChanged)
    def trunkBranch(self):
        return self._trunk_branch

    @trunkBranch.setter
    def trunkBranch(self, branch):
        if self._trunk_branch != branch:
            self._trunk_branch = branch
            self.trunkBranchChanged.emit(self._trunk_branch)

    @pyqtProperty(int, notify=trunkBranchAheadChanged)
    def trunkBranchAhead(self):
        return self._trunk_branch_ahead

    @trunkBranchAhead.setter
    def trunkBranchAhead(self, ahead):
        if self._trunk_branch_ahead != ahead:
            self._trunk_branch_ahead = ahead
            self.trunkBranchAheadChanged.emit(self._trunk_branch_ahead)

    @pyqtProperty(int, notify=trunkBranchBehindChanged)
    def trunkBranchBehind(self):
        return self._trunk_branch_behind

    @trunkBranchBehind.setter
    def trunkBranchBehind(self, behind):
        if self._trunk_branch_behind != behind:
            self._trunk_branch_behind = behind
            self.trunkBranchBehindChanged.emit(self._trunk_branch_behind)

    @pyqtProperty("QStringList", notify=branchesChanged)
    def branches(self):
        return self._branches

    @branches.setter
    def branches(self, branches):
        if self._branches != branches:
            self._branches = branches
            self.branchesChanged.emit(self._branches)
