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
import datetime
import logging
import os
import random
import subprocess
import threading
import time
from typing import NamedTuple


import git
from git.cmd import handle_process_output
from git.util import finalize_process

from PyQt5.QtCore import QModelIndex, pyqtSlot
from PyQt5.QtCore import QVariant
from PyQt5.QtCore import Qt, pyqtProperty, pyqtSignal, QObject
from PyQt5.QtCore import QAbstractItemModel
from PyQt5.QtCore import QThread

from gitover.fswatcher import RepoFsWatcher
from gitover.qml_helpers import QmlTypeMixin
from gitover.config import Config

LOGGER = logging.getLogger(__name__)


class ReposModel(QAbstractItemModel, QmlTypeMixin):
    """Model of repository data arranged in rows"""

    nofReposChanged = pyqtSignal(int)

    ROLE_REPO = Qt.UserRole + 1

    def __init__(self, parent=None):
        """Construct repositories model"""
        super().__init__(parent)
        self._workerThread = QThread(self, objectName="workerThread")
        self._workerThread.start()

        self._fsWatcher = RepoFsWatcher()
        self._fsWatcher.moveToThread(self._workerThread)
        self._fsWatcher.repoChanged.connect(self._onRepoChanged)

        self._repos = []

        cfg = Config()
        cfg.load(os.path.expanduser("~"))
        gitexe = cfg.general()["git"]
        if gitexe:
            git.Git.GIT_PYTHON_GIT_EXECUTABLE = gitexe

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

    @pyqtSlot(int, result="QVariant")
    def repo(self, idx):
        return self.data(self.index(idx, 0), role=ReposModel.ROLE_REPO)

    @pyqtSlot()
    def triggerUpdate(self):
        for repo in self._repos:
            repo.triggerUpdate()

    @pyqtSlot()
    def triggerFetch(self):
        for repo in self._repos:
            repo.triggerFetch()

    @pyqtSlot()
    def cleanup(self):
        self.stopWorker()
        self.beginResetModel()
        self._repos = []
        self.endResetModel()
        self.nofReposChanged.emit(self.nofRepos)

    @pyqtSlot()
    def stopWorker(self):
        LOGGER.debug("Stopping workers...")
        for repo in self._repos:
            repo.stopWorker()

        self._fsWatcher.stopTracking()

        if self._workerThread.isRunning():
            self._workerThread.quit()
            self._workerThread.wait()
        LOGGER.debug("Stopped worker")

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
        if any([r.path == repo.path for r in self._repos]):
            return

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

        self._fsWatcher.track.emit(rootpath)

    def _onRepoChanged(self, path):
        roots = [(repo.path, repo) for repo in self._repos]
        roots.sort(key=lambda x: len(x[0]), reverse=True)
        for root, repo in roots:
            if path == root or path.startswith(root + os.sep):
                repo.triggerUpdate()
                return


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
        self.untracked = set()
        self.deleted = set()
        self.modified = set()
        self.conflicts = set()
        self.staged = set()

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
            if repo.head and repo.head.commit:
                head = repo.git.rev_parse(repo.head.commit.hexsha, short=8)
                self.branch = "detached {}".format(head)
            else:
                self.branch = ""

        try:
            branches = [b.name for b in repo.branches]
            branches.sort(key=str.lower)
            self.branches = branches
        except:
            LOGGER.exception("Invalid branches for {}".format(self.path))

        try:
            if self.branch in self.branches:
                remote = repo.git.config("branch.{}.remote".format(self.branch),
                                         with_exceptions=False)
                if remote:
                    self.trackingBranch = "{}/{}".format(remote, self.branch)
                    if self.trackingBranch in repo.refs:
                        ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trackingBranch),
                                                          left_right=True, count=True).split("\t")
                        self.trackingBranchAhead, self.trackingBranchBehind = int(ahead), int(
                            behind)
        except:
            LOGGER.exception("Failed to get tracking branch ahead/behind counters for {}"
                             .format(self.path))

        try:
            self.trunkBranch = repo.git.config("gitover.trunkbranch", with_exceptions=False)
            if not self.trunkBranch:
                self.trunkBranch = "origin/develop"
            if self.trunkBranch in repo.refs:
                ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trunkBranch),
                                                  left_right=True, count=True).split("\t")
                self.trunkBranchAhead, self.trunkBranchBehind = int(ahead), int(behind)
        except:
            LOGGER.exception(
                "Failed to get trunk branch ahead/behind counters for {}".format(self.path))

        self.untracked = set(repo.untracked_files)
        for diff in repo.index.diff(other=None):  # diff against working tree
            if diff.deleted_file:
                self.deleted.add(diff.b_path)
            else:
                self.modified.add(diff.b_path)

        try:
            unmergedBlobs = repo.index.unmerged_blobs()
            for path in unmergedBlobs:
                for (stage, dummyBlob) in unmergedBlobs[path]:
                    if stage != 0:  # anything else than zero indicates a conflict that must be resolved
                        self.conflicts.add(path)
        except:
            pass  # unmerged_blobs() seems to raise an exception when there are no conflicts !?

        try:
            staged = repo.git.diff("HEAD", name_only=True, cached=True).split("\n")
            for p in [p for p in staged if p.strip()]:
                self.staged.add(p)
        except:
            pass

        self.modified -= self.conflicts
        self.deleted -= self.conflicts
        self.staged -= self.conflicts

        pass


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

    # signal gets emitted for every generated output line during fetch
    output = pyqtSignal(str)

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
            proc = repo.git.fetch("origin", prune=True,
                                  verbose=True, with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
        except:
            LOGGER.exception("Failed to fetch git repo at {}".format(path))
        self._releaseFetchSlot()
        self.fetchprogress.emit(False)

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


ChangedPath = NamedTuple("ChangedPath", [("path", str), ("status", str)])


class ChangedFilesModel(QAbstractItemModel):
    """Model of changed files of a repository arranged in rows"""

    STATUS_REPO = Qt.UserRole + 1
    PATH_REPO = Qt.UserRole + 2

    def __init__(self, parent=None):
        """Construct changed files model"""
        super().__init__(parent)
        self._entries = []

    def roleNames(self):
        roles = super().roleNames()
        roles[ChangedFilesModel.STATUS_REPO] = b"status"
        roles[ChangedFilesModel.PATH_REPO] = b"path"
        return roles

    def index(self, row, col, parent=None):
        return self.createIndex(row, col)

    def rowCount(self, parent=None):
        return len(self._entries)

    def columnCount(self, idx):
        return 1

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid() or idx.row() >= len(self._entries):
            return None

        entry = self._entries[idx.row()]
        if role == Qt.DisplayRole:
            return entry.path
        if role == ChangedFilesModel.PATH_REPO:
            return entry.path
        if role == ChangedFilesModel.STATUS_REPO:
            return entry.status

        return None

    def setChanges(self, modified=None, staged=None, deleted=None, conflicting=None,
                   untracked=None):
        self.beginResetModel()
        entries = []
        entries += [ChangedPath(p, "modified") for p in modified] if modified else []
        entries += [ChangedPath(p, "staged") for p in staged] if staged else []
        entries += [ChangedPath(p, "deleted") for p in deleted] if deleted else []
        entries += [ChangedPath(p, "conflict") for p in conflicting] if conflicting else []
        entries += [ChangedPath(p, "untracked") for p in untracked] if untracked else []
        self._entries = entries
        self.endResetModel()


OutputLine = NamedTuple("OutputLine", [("timestamp", str), ("line", str)])


class OutputModel(QAbstractItemModel):
    """Model of output lines"""

    TIMESTAMP = Qt.UserRole + 1
    LINE = Qt.UserRole + 2

    def __init__(self, parent=None):
        """Construct changed files model"""
        super().__init__(parent)
        self._entries = []

    def roleNames(self):
        roles = super().roleNames()
        roles[OutputModel.TIMESTAMP] = b"timestamp"
        roles[OutputModel.LINE] = b"line"
        return roles

    def index(self, row, col, parent=None):
        return self.createIndex(row, col)

    def rowCount(self, parent=None):
        return len(self._entries)

    def columnCount(self, idx):
        return 1

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid() or idx.row() >= len(self._entries):
            return None

        entry = self._entries[idx.row()]
        if role == Qt.DisplayRole:
            return entry.line
        if role == OutputModel.TIMESTAMP:
            return entry.timestamp
        if role == OutputModel.LINE:
            return entry.line

        return None

    @pyqtSlot(str)
    def appendOutput(self, line):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        now = datetime.datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        self._entries.append(OutputLine(now, line))
        self.endInsertRows()

    @pyqtSlot()
    def clearOutput(self):
        self.beginResetModel()
        self._entries = []
        self.endResetModel()


class Repo(QObject, QmlTypeMixin):
    """Contains repository information"""

    pathChanged = pyqtSignal(str)
    nameChanged = pyqtSignal(str)
    branchChanged = pyqtSignal(str)
    branchesChanged = pyqtSignal("QStringList")
    trackingBranchChanged = pyqtSignal(str)
    trackingBranchAheadChanged = pyqtSignal(int)
    trackingBranchBehindChanged = pyqtSignal(int)
    trunkBranchChanged = pyqtSignal(str)
    trunkBranchAheadChanged = pyqtSignal(int)
    trunkBranchBehindChanged = pyqtSignal(int)
    untrackedChanged = pyqtSignal(int)
    modifiedChanged = pyqtSignal(int)
    deletedChanged = pyqtSignal(int)
    conflictsChanged = pyqtSignal(int)
    stagedChanged = pyqtSignal(int)

    updatingChanged = pyqtSignal(bool)
    fetchingChanged = pyqtSignal(bool)

    def __init__(self, path, name="", parent=None):
        super().__init__(parent)
        self.destroyed.connect(self.stopWorker)

        self._path = os.path.normpath(os.path.abspath(path))
        self._name = name or os.path.basename(self._path)

        self._changes = ChangedFilesModel(self)
        self._output = OutputModel(self)

        self._workerThread = QThread(self, objectName="workerThread-{}".format(name))
        self._workerThread.start()

        self._statusWorker = GitStatusWorker()
        self._statusWorker.moveToThread(self._workerThread)
        self._statusWorker.statusprogress.connect(self._onUpdating)
        self._statusWorker.statusupdated.connect(self._onStatusUpdated)

        self._fetchWorker = GitFetchWorker()
        self._fetchWorker.moveToThread(self._workerThread)
        self._fetchWorker.fetchprogress.connect(self._setFetching)
        self._fetchWorker.output.connect(self._output.appendOutput)

        self._branch = ""
        self._branches = []
        self._tracking_branch = ""
        self._tracking_branch_ahead = 0
        self._tracking_branch_behind = 0
        self._trunk_branch = ""
        self._trunk_branch_ahead = 0
        self._trunk_branch_behind = 0
        self._untracked = 0
        self._modified = 0
        self._deleted = 0
        self._conflicts = 0
        self._staged = 0

        self._updating = False
        self._updateTriggered = False

        self._fetching = False
        self._fetchTriggered = False

        self.triggerUpdate()

    def __str__(self):
        return self._path

    @pyqtProperty(QObject, constant=True)
    def changes(self):
        return self._changes

    @pyqtProperty(QObject, constant=True)
    def output(self):
        return self._output

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
        def sorteditems(it):
            l = list(it)
            l.sort(key=str.lower)
            return l

        self.branch = status.branch
        self.branches = sorteditems(status.branches)
        self.trackingBranch = status.trackingBranch
        self.trackingBranchAhead = status.trackingBranchAhead
        self.trackingBranchBehind = status.trackingBranchBehind
        self.trunkBranch = status.trunkBranch
        self.trunkBranchAhead = status.trunkBranchAhead
        self.trunkBranchBehind = status.trunkBranchBehind
        self.untracked = len(status.untracked)
        self.modified = len(status.modified)
        self.deleted = len(status.deleted)
        self.conflicts = len(status.conflicts)
        self.staged = len(status.staged)

        self._changes.setChanges(modified=sorteditems(status.modified),
                                 staged=sorteditems(status.staged),
                                 deleted=sorteditems(status.deleted),
                                 conflicting=sorteditems(status.conflicts),
                                 untracked=sorteditems(status.untracked))

    def _config(self):
        cfg = Config()
        cfg.load(self._path)
        return cfg

    @pyqtSlot(str)
    def execCmd(self, name):
        """Executes a named command for current repository"""
        cfg = self._config()

        if name == "update":
            self.triggerUpdate()
            return
        if name == "fetch":
            self.triggerFetch()
            return

        tool = cfg.tool(name)
        if not tool:
            return

        def substVar(txt, variables):
            "Substite named variables in given string"
            for name, value in variables.items():
                txt = txt.replace("{{{}}}".format(name), value)
            return txt

        vars = {"root": self._path}
        cmd = substVar(tool["cmd"], vars)
        cwd = self._path
        LOGGER.info("Executing command {}:\n\tCommand: {}\n\tCwd: {}".format(name, cmd, cwd))
        subprocess.Popen(cmd, shell=True, cwd=cwd, executable="/bin/bash")

    @pyqtSlot(result=QVariant)
    def cmds(self):
        """Returns a list of dict with keys name,title to configure commands for current repository"""
        cfg = self._config()
        tools = [{"name": "update", "title": "Refresh"},
                 {"name": "fetch", "title": "Fetch"},
                 {"title": ""}]
        tools += cfg.tools()
        return QVariant(tools)

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

    @pyqtProperty(int, notify=untrackedChanged)
    def untracked(self):
        return self._untracked

    @untracked.setter
    def untracked(self, untracked):
        if self._untracked != untracked:
            self._untracked = untracked
            self.untrackedChanged.emit(self._untracked)

    @pyqtProperty(int, notify=modifiedChanged)
    def modified(self):
        return self._modified

    @modified.setter
    def modified(self, modified):
        if self._modified != modified:
            self._modified = modified
            self.modifiedChanged.emit(self._modified)

    @pyqtProperty(int, notify=deletedChanged)
    def deleted(self):
        return self._deleted

    @deleted.setter
    def deleted(self, deleted):
        if self._deleted != deleted:
            self._deleted = deleted
            self.deletedChanged.emit(self._deleted)

    @pyqtProperty(int, notify=conflictsChanged)
    def conflicts(self):
        return self._conflicts

    @conflicts.setter
    def conflicts(self, conflicts):
        if self._conflicts != conflicts:
            self._conflicts = conflicts
            self.conflictsChanged.emit(self._conflicts)

    @pyqtProperty(int, notify=stagedChanged)
    def staged(self):
        return self._staged

    @staged.setter
    def staged(self, staged):
        if self._staged != staged:
            self._staged = staged
            self.stagedChanged.emit(self._staged)
