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

import git
import os

from PyQt5.QtCore import QModelIndex, pyqtSlot
from PyQt5.QtCore import QVariant
from PyQt5.QtCore import Qt, pyqtProperty, pyqtSignal, QObject
from PyQt5.QtCore import QAbstractItemModel

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
    def refresh(self):
        for repo in self._repos:
            repo.refresh()

    @pyqtProperty(int, notify=nofReposChanged)
    def nofRepos(self):
        return self.rowCount()

    def addRepo(self, repo):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        repo.setParent(self)
        self._repos += [repo]
        LOGGER.debug("Added repo {}".format(repo))
        self.endInsertRows()
        self.nofReposChanged.emit(self.nofRepos)


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
    refreshingChanged = pyqtSignal(bool)

    def __init__(self, path, name="", parent=None):
        super().__init__(parent)
        self._path = path
        self._name = name or os.path.basename(self._path)
        self._branch = ""
        self._tracking_branch = ""
        self._tracking_branch_ahead = 0
        self._tracking_branch_behind = 0
        self._trunk_branch = ""
        self._trunk_branch_ahead = 0
        self._trunk_branch_behind = 0
        self._branches = []
        self._refreshing = False
        self.refresh()

    def __str__(self):
        return self._path

    @pyqtProperty(bool, notify=refreshingChanged)
    def refreshing(self):
        return self._refreshing

    def _setRefreshing(self, refreshing):
        if self._refreshing != refreshing:
            self._refreshing = refreshing
            self.refreshingChanged.emit(self._refreshing)

    @pyqtSlot()
    def refresh(self):
        try:
            self._setRefreshing(True)
            self._refresh()
        finally:
            self._setRefreshing(False)

    def _refresh(self):
        try:
            repo = git.Repo(self._path)
        except:
            LOGGER.exception("Invalid repository at {}".format(self._path))
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
            self.branches = []
            LOGGER.exception("Invalid branches for {}".format(self._path))

        try:
            if self._branch and self._branch != "detached":
                remote = repo.git.config("branch.{}.remote".format(self._branch))
                self.trackingBranch = "{}/{}".format(remote, self._branch)
                ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trackingBranch),
                                                  left_right=True, count=True).split("\t")
                self.trackingBranchAhead, self.trackingBranchBehind = int(ahead), int(behind)
            else:
                self._resetTrackingBranch()
        except:
            self._resetTrackingBranch()
            LOGGER.exception(
                "Failed to get tracking branch ahead/behind counters for {}".format(self._path))

        try:
            if self._branch and self._branch != "detached":
                try:
                    self.trunkBranch = repo.git.config("custom.devbranch")
                except git.GitCommandError:
                    self.trunkBranch = "origin/develop"
                ahead, behind = repo.git.rev_list("{}...HEAD".format(self.trunkBranch),
                                                  left_right=True, count=True).split("\t")
                self.trunkBranchAhead, self.trunkBranchBehind = int(ahead), int(behind)
            else:
                self._resetTrunkBranch()
        except:
            self._resetTrunkBranch()
            LOGGER.exception(
                "Failed to get trunk branch ahead/behind counters for {}".format(self._path))

        pass

    def _resetTrackingBranch(self):
        self.trackingBranch = ""
        self.trackingBranchAhead = 0
        self.trackingBranchBehind = 0

    def _resetTrunkBranch(self):
        self.trunkBranch = ""
        self.trunkBranchAhead = 0
        self.trunkBranchBehind = 0

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
