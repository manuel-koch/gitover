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
from collections import OrderedDict
import copy
import datetime
import logging
import os
import random
import string
import subprocess
import threading
import time
from typing import NamedTuple

import git
from git.cmd import handle_process_output
from git.util import finalize_process

from PyQt5.QtCore import QModelIndex, pyqtSlot, Q_ENUMS
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

    def __init__(self, watch_filesystem=True, parent=None):
        """Construct repositories model"""
        super().__init__(parent)
        self._workerThread = QThread(self, objectName="workerThread")
        self._workerThread.start()

        self._watchFs = watch_filesystem
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

        if self._watchFs:
            self._fsWatcher.track.emit(rootpath)

    def _onRepoChanged(self, path):
        roots = [(repo.path, repo) for repo in self._repos]
        roots.sort(key=lambda x: len(x[0]), reverse=True)
        for root, repo in roots:
            if path == root or path.startswith(root + os.sep):
                repo.triggerUpdate()
                return


CommitDetail = NamedTuple("CommitDetail", (("rev", str),
                                           ("user", str),
                                           ("msg", str),
                                           ("changes", list)))

CommitChange = NamedTuple("CommitChange", (("change", str),
                                           ("path", str)))


class CachedCommitDetails(object):
    """Caching commit info for sake of performance"""

    def __init__(self):
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def _create(self, rev, repo):
        """Create and return CommitDetail for selected revision from repository instance"""
        c = repo.commit(rev)
        msg = c.message.split("\n")[0].strip()
        shortrev = repo.git.rev_parse(c.hexsha, short=8)
        changes = repo.git.diff_tree(rev, no_commit_id=True, name_status=True, r=True).split("\n")
        changes = [CommitChange(*c.split("\t")) for c in changes if c.strip()]
        cd = CommitDetail(shortrev, c.author.name, msg, changes)
        self._cache[rev] = cd
        return cd

    def get(self, rev, repo=None):
        """Returns CommitDetail for selected revision from repository instance"""
        with self._lock:
            if rev in self._cache:
                c = copy.copy(self._cache[rev])
            elif repo:
                c = self._create(rev, repo)
            else:
                c = None
            while len(self._cache) > 250:
                self._cache.popitem()
        return c


CACHED_COMMIT_DETAILS = CachedCommitDetails()


class GitStatus(object):
    def __init__(self, path):
        self.path = path  # root directory of repository
        self.branch = ""  # current branch
        self.branches = []  # all local branches
        self.remoteBranches = []  # all remote branches that could be checked-out
        self.mergedToTrunkBranches = []  # all local branches that have been merged to trunk
        self.trackingBranch = ""  # tracking branch of current branch
        self.trackingBranchAhead = []  # list of commits that tracking branch is ahead of current branch
        self.trackingBranchBehind = []  # list of commits that tracking branch is behind of current branch
        self.trunkBranch = ""  # trunk branch of repositiory
        self.trunkBranchAhead = []  # list of commits that trunk branch is ahead of current branch
        self.trunkBranchBehind = []  # list of commits that trunk branch is ahead of current branch
        self.untracked = set()  # set of untracked paths in repository
        self.deleted = set()  # set of deleted paths in repository
        self.modified = set()  # set of modified paths in repository
        self.conflicts = set()  # set of conflict paths in repository
        self.staged = set()  # set of staged paths in repository

    def _commitsAheadBehind(self, repo, branch):
        """Returns tuple of commit hash lists for commits of HEAD that are ahead/behind
        given repository branch"""
        ahead, behind = [], []
        if branch in repo.refs:
            lines = repo.git.rev_list("{}...HEAD".format(branch), left_right=True).split("\n")
            lines = [line.strip() for line in lines if line.strip()]
            for commit in lines:
                dir, commit = commit[0], commit[1:]
                if dir == "<":
                    ahead += [commit]
                else:
                    behind += [commit]
                CACHED_COMMIT_DETAILS.get(commit, repo)
        return (ahead, behind)

    def _trackingBranch(self, repo, branch):
        remote = repo.git.config("branch.{}.remote".format(branch), with_exceptions=False)
        if remote:
            return "{}/{}".format(remote, branch)
        else:
            return ""

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
            trackedBranches = [self._trackingBranch(repo, b) for b in self.branches]
            remoteBranches = [r.name for r in repo.references
                              if isinstance(r, git.RemoteReference) and
                              r.name != (r.remote_name + "/HEAD") and
                              r.name not in trackedBranches]
            remoteBranches.sort(key=str.lower)
            self.remoteBranches = remoteBranches
        except:
            LOGGER.exception("Invalid branches for {}".format(self.path))

        try:
            if self.branch in self.branches:
                self.trackingBranch = self._trackingBranch(repo, self.branch)
                if self.trackingBranch:
                    ahead, behind = self._commitsAheadBehind(repo, self.trackingBranch)
                    self.trackingBranchAhead = ahead
                    self.trackingBranchBehind = behind
        except:
            LOGGER.exception("Failed to get tracking branch ahead/behind counters for {}"
                             .format(self.path))

        try:
            self.trunkBranch = repo.git.config("gitover.trunkbranch", with_exceptions=False)
            if not self.trunkBranch:
                self.trunkBranch = "origin/develop"
            ahead, behind = self._commitsAheadBehind(repo, self.trunkBranch)
            self.trunkBranchAhead = ahead
            self.trunkBranchBehind = behind
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

        try:
            merged_branches = [b.replace("*", "").strip()
                               for b in repo.git.branch(self.trunkBranch, merged=True).split("\n")]
            merged_branches = [(b, self._trackingBranch(repo, b)) for b in merged_branches]
            self.mergedToTrunkBranches = [b[0] for b in merged_branches if
                                          b[1] != self.trunkBranch]
        except:
            LOGGER.exception("Failed to detect branches that are already merged to trunk")


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

    # signal gets emitted when an error happened during pull
    error = pyqtSignal(str)

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
            self.error.emit("Failed to fetch")
        self._releaseFetchSlot()
        self.fetchprogress.emit(False)

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


class GitPullWorker(QObject):
    """Host git pull action within worker thread"""

    # signal gets emitted to trigger pulling given repo root path
    pull = pyqtSignal(str)

    # signal gets emitted when starting/stopping pull action
    pullprogress = pyqtSignal(bool)

    # signal gets emitted for every generated output line during pull
    output = pyqtSignal(str)

    # signal gets emitted when an error happened during pull
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.pull.connect(self._onPull)

    @pyqtSlot(str)
    def _onPull(self, path):
        """Pull selected repo"""
        self.pullprogress.emit(True)
        try:
            repo = git.Repo(path)

            err_hint = "stash save"
            stash_name = "Automatic stash before pull: {}".format(
                "".join(random.sample(string.ascii_letters + string.digits, 32)))
            dirty = repo.is_dirty()
            if dirty:
                proc = repo.git.stash("save", stash_name,
                                      with_extended_output=True, as_process=True)
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

            err_hint = "pull"
            proc = repo.git.pull(prune=True,
                                 verbose=True, with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

            err_hint = "stash pop"
            stashed = repo.git.stash("list").split("\n")
            stashed = stash_name in stashed[0] if stashed else False
            if stashed:
                proc = repo.git.stash("pop",
                                      with_extended_output=True, as_process=True)
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

        except:
            LOGGER.exception("Failed to pull git repo at {}".format(path))
            self.error.emit("Failed to " + err_hint)

        self.pullprogress.emit(False)

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


class GitCheckoutWorker(QObject):
    """Host git checkout action within worker thread"""

    # signal gets emitted to trigger checkout given repo branch
    checkoutBranch = pyqtSignal(str)

    # signal gets emitted when starting/stopping pull action
    checkoutprogress = pyqtSignal(bool)

    # signal gets emitted for every generated output line during checkout
    output = pyqtSignal(str)

    # signal gets emitted when an error happened during pull
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self._path = path
        self.checkoutBranch.connect(self._onCheckoutBranch)

    @pyqtSlot(str)
    def _onCheckoutBranch(self, branch):
        """Checkout selected (remote) branch and create a (local) branch if necessary"""
        try:
            self.checkoutprogress.emit(True)
            repo = git.Repo(self._path)

            if branch not in repo.references:
                LOGGER.warning("Skipped checkout of invalid branch {}".format(branch))
                return

            ref = repo.references[branch]
            if isinstance(ref, git.RemoteReference):
                branch = ref.remote_head

            err_hint = "stash save"
            stash_name = "Automatic stash before checkout: {}".format(
                "".join(random.sample(string.ascii_letters + string.digits, 32)))
            dirty = repo.is_dirty()
            if dirty:
                proc = repo.git.stash("save", stash_name,
                                      with_extended_output=True, as_process=True)
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

            err_hint = "checkout"
            proc = repo.git.checkout(branch,
                                     with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

            err_hint = "stash pop"
            stashed = repo.git.stash("list").split("\n")
            stashed = stash_name in stashed[0] if stashed else False
            if stashed:
                proc = repo.git.stash("pop",
                                      with_extended_output=True, as_process=True)
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

        except:
            LOGGER.exception("Failed to checkout git repo at {}".format(self._path))
            self.error.emit("Failed to " + err_hint)
        finally:
            self.checkoutprogress.emit(False)

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


class GitRebaseWorker(QObject):
    """Host git rebase action within worker thread"""

    # signal gets emitted to trigger rebase onto given reference
    rebase = pyqtSignal(str)

    # signal gets emitted to trigger skip of current patch while rebasing
    skip = pyqtSignal()

    # signal gets emitted to trigger continue rebasing
    cont = pyqtSignal()

    # signal gets emitted to trigger abort of rebase
    abort = pyqtSignal()

    # signal gets emitted to trigger check if rebase is still in progress
    check = pyqtSignal()

    # signal gets emitted when starting/stopping rebase action
    rebaseprogress = pyqtSignal(bool)

    # signal gets emitted for every generated output line during rebase
    output = pyqtSignal(str)

    # signal gets emitted when an error/conflict happened during rebase
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self._path = path
        self._repo = git.Repo(self._path)
        self._rebasing = False
        self._rebaseStash = ""
        self._testPaths = [os.path.join(self._repo.git_dir, "rebase-merge", "done"),
                           os.path.join(self._repo.git_dir, "rebase-apply", "rebasing")]
        self.rebase.connect(self._onStartRebase)
        self.skip.connect(self._onSkipRebase)
        self.cont.connect(self._onContinueRebase)
        self.abort.connect(self._onAbortRebase)
        self.check.connect(self.checkRebasing)

    @pyqtSlot(result=bool)
    def checkRebasing(self):
        """Check whether rebase is still in progress"""
        rebasing = any([os.path.exists(p) for p in self._testPaths])
        if self._rebasing != rebasing:
            self._rebasing = rebasing
            self.rebaseprogress.emit(self._rebasing)
            if not self._rebasing and self._rebaseStash:
                self._stashPop()
        return self._rebasing

    def _stash(self):
        """Stash dirty changes as preparation of rebase"""
        dirty = self._repo.is_dirty()
        if dirty:
            self._rebaseStash = "Automatic stash before rebase: {}".format(
                "".join(random.sample(string.ascii_letters + string.digits, 32)))
            proc = self._repo.git.stash("save", self._rebaseStash,
                                        with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

    def _stashPop(self):
        """Pop stash to finalize after rebase finished"""
        if not self._rebaseStash:
            return
        stashed = self._repo.git.stash("list").split("\n")
        stashed = self._rebaseStash in stashed[0] if stashed else False
        if stashed:
            proc = self._repo.git.stash("pop",
                                        with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
        self._rebaseStash = ""

    @pyqtSlot(str)
    def _onStartRebase(self, ref):
        """Rebase onto selected reference"""
        try:
            if self._rebasing:
                return
            self._rebasing = True
            self.rebaseprogress.emit(True)

            if ref not in self._repo.references:
                commits = list(self._repo.iter_commits(rev=ref))
                if ref not in commits:
                    return

            self._stash()

            proc = self._repo.git.rebase(ref,
                                         with_extended_output=True, as_process=True)
            try:
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
            except git.exc.GitCommandError as e:
                LOGGER.error("Rebase git repo at {} failed or found conflicts: {}"
                             .format(self._path, e))
                self.error.emit("Failed to rebase")

            if not self.checkRebasing():
                self._stashPop()
        except:
            LOGGER.exception("Failed to rebase git repo at {}".format(self._path))

    @pyqtSlot()
    def _onContinueRebase(self):
        """Continue rebase"""
        try:
            if not self._rebasing:
                return
            # can't use "continue" argument directly due to reserved keyword
            kwargs = {"continue": True}
            proc = self._repo.git.rebase(**kwargs,
                                         with_extended_output=True, as_process=True)
            try:
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
            except git.exc.GitCommandError as e:
                LOGGER.error("Continue rebase git repo at {} failed or found conflicts: {}"
                             .format(self._path, e))
                self.error.emit("Failed to continue rebase")

            if not self.checkRebasing():
                self._stashPop()
        except:
            LOGGER.exception("Failed to continue rebase git repo at {}".format(self._path))

    @pyqtSlot()
    def _onSkipRebase(self):
        """Skip current patch while rebasing"""
        try:
            if not self._rebasing:
                return
            proc = self._repo.git.rebase(skip=True,
                                         with_extended_output=True, as_process=True)
            try:
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
            except git.exc.GitCommandError as e:
                LOGGER.error("Skip rebase git repo at {} failed or found conflicts: {}"
                             .format(self._path, e))
                self.error.emit("Failed to skip rebase")

            if not self.checkRebasing():
                self._stashPop()
        except:
            LOGGER.exception("Failed to skip rebase git repo at {}".format(self._path))

    @pyqtSlot()
    def _onAbortRebase(self):
        """Abort rebase"""
        try:
            if not self._rebasing:
                return
            proc = self._repo.git.rebase(abort=True,
                                         with_extended_output=True, as_process=True)
            try:
                handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)
            except git.exc.GitCommandError as e:
                LOGGER.error("Abort rebase git repo at {} failed or found conflicts: {}"
                             .format(self._path, e))
                self.error.emit("Failed to abort rebase")

            if not self.checkRebasing():
                self._stashPop()
        except:
            LOGGER.exception("Failed to abort rebase git repo at {}".format(self._path))

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


class GitPushWorker(QObject):
    """Host git push action within worker thread"""

    # signal gets emitted to trigger pushing given repo branch w/ or w/o force
    pushBranch = pyqtSignal(str, bool)

    # signal gets emitted when starting/stopping push action
    pushprogress = pyqtSignal(bool)

    # signal gets emitted for every generated output line during push
    output = pyqtSignal(str)

    # signal gets emitted when an error happened during push
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self._path = path
        self.pushBranch.connect(self._onPushBranch)

    @pyqtSlot(str, bool)
    def _onPushBranch(self, branch, force=False):
        """Push selected branch to remote, setting upstream when no tracking branch is set yet"""
        try:
            self.pushprogress.emit(True)
            repo = git.Repo(self._path)

            if not repo.active_branch.name:
                return

            remote = repo.git.config("branch.{}.remote".format(repo.active_branch.name),
                                     with_exceptions=False)

            kwargs = {}
            args = []
            if not remote:
                kwargs["set_upstream"] = True
                args.append("origin")
                args.append(repo.active_branch.name)
            if force:
                kwargs["force"] = True

            proc = repo.git.push(*args, **kwargs,
                                 with_extended_output=True, as_process=True)
            handle_process_output(proc, self._onOutput, self._onOutput, finalize_process)

        except:
            LOGGER.exception("Failed to push git repo at {}".format(self._path))
            self.error.emit("Failed to push")
        finally:
            self.pushprogress.emit(False)

    def _onOutput(self, line):
        line = line.rstrip()
        LOGGER.debug(line)
        self.output.emit(line)


ChangedPath = NamedTuple("ChangedPath", [("path", str), ("status", str)])


class ChangedFilesModel(QAbstractItemModel, QmlTypeMixin):
    """Model of changed files of a repository arranged in rows"""

    class Role:
        Status = Qt.UserRole + 1
        Path = Qt.UserRole + 2

    Q_ENUMS(Role)

    def __init__(self, parent=None):
        """Construct changed files model"""
        super().__init__(parent)
        self._entries = []

    def roleNames(self):
        roles = super().roleNames()
        roles[ChangedFilesModel.Role.Status] = b"status"
        roles[ChangedFilesModel.Role.Path] = b"path"
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
        if role == ChangedFilesModel.Role.Path:
            return entry.path
        if role == ChangedFilesModel.Role.Status:
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
    remoteBranchesChanged = pyqtSignal("QStringList")
    mergedToTrunkBranchesChanged = pyqtSignal("QStringList")

    trackingBranchChanged = pyqtSignal(str)
    trackingBranchAheadChanged = pyqtSignal(int)
    trackingBranchAheadCommitsChanged = pyqtSignal("QStringList")
    trackingBranchBehindChanged = pyqtSignal(int)
    trackingBranchBehindCommitsChanged = pyqtSignal("QStringList")

    trunkBranchChanged = pyqtSignal(str)
    trunkBranchAheadChanged = pyqtSignal(int)
    trunkBranchAheadCommitsChanged = pyqtSignal("QStringList")
    trunkBranchBehindChanged = pyqtSignal(int)
    trunkBranchBehindCommitsChanged = pyqtSignal("QStringList")

    untrackedChanged = pyqtSignal(int)
    modifiedChanged = pyqtSignal(int)
    deletedChanged = pyqtSignal(int)
    conflictsChanged = pyqtSignal(int)
    stagedChanged = pyqtSignal(int)

    updatingChanged = pyqtSignal(bool)
    fetchingChanged = pyqtSignal(bool)
    pullingChanged = pyqtSignal(bool)
    checkingoutChanged = pyqtSignal(bool)
    rebasingChanged = pyqtSignal(bool)
    pushingChanged = pyqtSignal(bool)

    statusUpdated = pyqtSignal()

    error = pyqtSignal(str, arguments=["msg"])

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
        self._fetchWorker.error.connect(self.error)

        self._pullWorker = GitPullWorker()
        self._pullWorker.moveToThread(self._workerThread)
        self._pullWorker.pullprogress.connect(self._setPulling)
        self._pullWorker.output.connect(self._output.appendOutput)
        self._pullWorker.error.connect(self.error)

        self._checkoutWorker = GitCheckoutWorker(self._path)
        self._checkoutWorker.moveToThread(self._workerThread)
        self._checkoutWorker.checkoutprogress.connect(self._setCheckingOut)
        self._checkoutWorker.output.connect(self._output.appendOutput)
        self._checkoutWorker.error.connect(self.error)

        self._rebaseWorker = GitRebaseWorker(self._path)
        self._rebaseWorker.moveToThread(self._workerThread)
        self._rebaseWorker.rebaseprogress.connect(self._setRebasing)
        self._rebaseWorker.output.connect(self._output.appendOutput)
        self._rebaseWorker.error.connect(self.triggerUpdate)
        self._rebaseWorker.error.connect(self.error)

        self._pushWorker = GitPushWorker(self._path)
        self._pushWorker.moveToThread(self._workerThread)
        self._pushWorker.pushprogress.connect(self._setPushing)
        self._pushWorker.output.connect(self._output.appendOutput)
        self._pushWorker.error.connect(self.error)

        self._branch = ""
        self._branches = []
        self._remote_branches = []
        self._merged_to_trunk_branches = []

        self._tracking_branch = ""
        self._tracking_branch_ahead_commits = []
        self._tracking_branch_behind_commits = []

        self._trunk_branch = ""
        self._trunk_branch_ahead_commits = []
        self._trunk_branch_behind_commits = []

        self._untracked = 0
        self._modified = 0
        self._deleted = 0
        self._conflicts = 0
        self._staged = 0

        self._updating = False
        self._updateTriggered = False

        self._fetching = False
        self._fetchTriggered = False

        self._pulling = False
        self._pullTriggered = False

        self._checkingout = False
        self._checkoutTriggered = False

        self._rebasing = False
        self._rebaseTriggered = False

        self._pushing = False
        self._pushTriggered = False

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

    @pyqtProperty(bool, notify=pullingChanged)
    def pulling(self):
        return self._pulling

    def _setPulling(self, pulling):
        if self._pulling != pulling:
            self._pulling = pulling
            self.pullingChanged.emit(self._pulling)
        if not pulling:
            self._pullTriggered = False
            self.triggerUpdate()

    @pyqtSlot()
    def triggerPull(self):
        if self._pullTriggered:
            LOGGER.debug("Pull already triggered...")
            return
        self._pullWorker.pull.emit(self._path)
        self._pullTriggered = True

    @pyqtProperty(bool, notify=checkingoutChanged)
    def checkingout(self):
        return self._checkingout

    def _setCheckingOut(self, checkingout):
        if self._checkingout != checkingout:
            self._checkingout = checkingout
            self.checkingoutChanged.emit(self._checkingout)
        if not checkingout:
            self._checkoutTriggered = False
            self.triggerUpdate()

    @pyqtSlot(str)
    def triggerCheckoutBranch(self, branch):
        if self._checkoutTriggered:
            LOGGER.debug("Checkout already triggered...")
            return
        self._checkoutWorker.checkoutBranch.emit(branch)
        self._checkoutTriggered = True

    @pyqtProperty(bool, notify=rebasingChanged)
    def rebasing(self):
        return self._rebasing

    def _setRebasing(self, rebasing):
        if self._rebasing != rebasing:
            self._rebasing = rebasing
            self.rebasingChanged.emit(self._rebasing)
        if not rebasing:
            self._rebaseTriggered = False
            self.triggerUpdate()

    @pyqtSlot(str)
    def triggerRebase(self, ref):
        if self._rebaseTriggered:
            LOGGER.debug("Rebase already triggered...")
            return
        self._rebaseWorker.rebase.emit(ref)
        self._rebaseTriggered = True

    @pyqtProperty(bool, notify=pushingChanged)
    def pushing(self):
        return self._pushing

    def _setPushing(self, pushing):
        if self._pushing != pushing:
            self._pushing = pushing
            self.pushingChanged.emit(self._pushing)
        if not pushing:
            self._pushTriggered = False
            self.triggerUpdate()

    @pyqtSlot(str, bool)
    def triggerPush(self, branch, force):
        if self._pushTriggered:
            LOGGER.debug("Push already triggered...")
            return
        self._pushWorker.pushBranch.emit(branch, force)
        self._pushTriggered = True

    @pyqtSlot(object)
    def _onStatusUpdated(self, status):
        def sorteditems(it):
            l = list(it)
            l.sort(key=str.lower)
            return l

        self.branch = status.branch
        self.branches = sorteditems(status.branches)
        self.remoteBranches = sorteditems(status.remoteBranches)
        self.mergedToTrunkBranches = sorteditems(status.mergedToTrunkBranches)
        self.trackingBranch = status.trackingBranch
        self.trackingBranchAheadCommits = status.trackingBranchAhead
        self.trackingBranchBehindCommits = status.trackingBranchBehind
        self.trunkBranch = status.trunkBranch
        self.trunkBranchAheadCommits = status.trunkBranchAhead
        self.trunkBranchBehindCommits = status.trunkBranchBehind
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

        self._rebaseWorker.check.emit()
        self.statusUpdated.emit()

    def _config(self):
        cfg = Config()
        cfg.load(self._path)
        return cfg

    @pyqtSlot(str)
    def execCmd(self, name):
        """Executes a named command for current repository"""
        cfg = self._config()

        if name == "__update":
            self.triggerUpdate()
            return
        if name == "__fetch":
            self.triggerFetch()
            return
        if name == "__pull":
            self.triggerPull()
            return
        if name == "__push":
            self.triggerPush(self.branch, False)
            return
        if name == "__pushforced":
            self.triggerPush(self.branch, True)
            return
        if name == "__rebasetrunk":
            self.triggerRebase(self._trunk_branch)
            return
        if name == "__rebasecont":
            self._rebaseWorker.cont.emit()
            return
        if name == "__rebaseskip":
            self._rebaseWorker.skip.emit()
            return
        if name == "__rebaseabort":
            self._rebaseWorker.abort.emit()
            return

        tool = cfg.tool(name)
        if not tool:
            return

        def substVar(txt, variables):
            """Substite named variables in given string"""
            for name, value in variables.items():
                txt = txt.replace("{{{}}}".format(name), value)
            return txt

        vars = {"root": self._path,
                "branch": self._branch,
                "trackingbranch": self._tracking_branch,
                "trunkbranch": self._trunk_branch}
        cmd = substVar(tool["cmd"], vars)
        cwd = self._path
        LOGGER.info("Executing command {}:\n\tCommand: {}\n\tCwd: {}".format(name, cmd, cwd))
        subprocess.Popen(cmd, shell=True, cwd=cwd, executable="/bin/bash")

    @pyqtSlot(result=QVariant)
    def cmds(self):
        """Returns a list of dict with keys name,title to configure commands for current repository"""
        cmds = [dict(name="__update", title="Refresh", shortcut="Ctrl+R"),
                dict(name="__fetch", title="Fetch", shortcut="Ctrl+F"),
                dict(name="__pull", title="Pull")]
        if not self._rebasing:
            cmds.append({"name": "__rebasetrunk", "title": "Rebase onto trunk"})
        else:
            cmds.append({"name": "__rebasecont", "title": "Continue rebase"})
            cmds.append({"name": "__rebaseskip", "title": "Skip rebase"})
            cmds.append({"name": "__rebaseabort", "title": "Abort rebase"})
        if not self._tracking_branch or self._tracking_branch_behind_commits or self._tracking_branch_ahead_commits:
            cmds.append({"name": "__push", "title": "Push"})
        if self._tracking_branch_behind_commits or self._tracking_branch_ahead_commits:
            cmds.append({"name": "__pushforced", "title": "Push (force)"})
        return QVariant(cmds)

    @pyqtSlot(result=QVariant)
    def toolCmds(self):
        """Returns a list of dict with keys name,title to configure tool commands for current repository"""
        cfg = self._config()
        return QVariant(cfg.tools())

    @pyqtSlot(str, str, result=str)
    def diff(self, path, status):
        """Returns textual diff of given repository path using given status"""
        repo = git.Repo(self._path)
        diff = ""
        if path:
            if status in ("modified", "conflict"):
                diff = repo.git.diff("--", path)
            elif status == "staged":
                diff = repo.git.diff("--", path, cached=True)
            elif status == "untracked":
                diff = open(os.path.join(self._path, path), "r").read()
        return diff

    @pyqtSlot(str, result=QVariant)
    def commit(self, rev):
        """Returns details for commit of given shahex revision"""
        details = CACHED_COMMIT_DETAILS.get(rev)
        if details:
            changes = [{"change": c.change, "path": c.path} for c in details.changes]
            return dict(rev=details.rev, user=details.user,
                        msg=details.msg, changes=changes)
        else:
            return dict(rev=rev, user="", msg="", changes=[])

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
        return len(self._tracking_branch_ahead_commits)

    @pyqtProperty("QStringList", notify=trackingBranchAheadCommitsChanged)
    def trackingBranchAheadCommits(self):
        return self._tracking_branch_ahead_commits

    @trackingBranchAheadCommits.setter
    def trackingBranchAheadCommits(self, ahead):
        if self._tracking_branch_ahead_commits != ahead:
            nofChanged = len(self._tracking_branch_ahead_commits) != len(ahead)
            self._tracking_branch_ahead_commits = ahead
            self.trackingBranchAheadCommitsChanged.emit(self._tracking_branch_ahead_commits)
            if nofChanged:
                self.trackingBranchAheadChanged.emit(self.trackingBranchAhead)

    @pyqtProperty(int, notify=trackingBranchBehindChanged)
    def trackingBranchBehind(self):
        return len(self._tracking_branch_behind_commits)

    @pyqtProperty("QStringList", notify=trackingBranchBehindCommitsChanged)
    def trackingBranchBehindCommits(self):
        return self._tracking_branch_behind_commits

    @trackingBranchBehindCommits.setter
    def trackingBranchBehindCommits(self, behind):
        if self._tracking_branch_behind_commits != behind:
            nofChanged = len(self._tracking_branch_behind_commits) != len(behind)
            self._tracking_branch_behind_commits = behind
            self.trackingBranchBehindCommitsChanged.emit(self._tracking_branch_behind_commits)
            if nofChanged:
                self.trackingBranchBehindChanged.emit(self.trackingBranchBehind)

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
        return len(self._trunk_branch_ahead_commits)

    @pyqtProperty("QStringList", notify=trunkBranchAheadCommitsChanged)
    def trunkBranchAheadCommits(self):
        return self._trunk_branch_ahead_commits

    @trunkBranchAheadCommits.setter
    def trunkBranchAheadCommits(self, ahead):
        if self._trunk_branch_ahead_commits != ahead:
            nofChanged = len(self._trunk_branch_ahead_commits) != len(ahead)
            self._trunk_branch_ahead_commits = ahead
            self.trunkBranchAheadCommitsChanged.emit(self._trunk_branch_ahead_commits)
            if nofChanged:
                self.trunkBranchAheadChanged.emit(self.trunkBranchAhead)

    @pyqtProperty(int, notify=trunkBranchBehindChanged)
    def trunkBranchBehind(self):
        return len(self._trunk_branch_behind_commits)

    @pyqtProperty("QStringList", notify=trunkBranchBehindCommitsChanged)
    def trunkBranchBehindCommits(self):
        return self._trunk_branch_behind_commits

    @trunkBranchBehindCommits.setter
    def trunkBranchBehindCommits(self, behind):
        if self._trunk_branch_behind_commits != behind:
            nofChanged = len(self._trunk_branch_behind_commits) != len(behind)
            self._trunk_branch_behind_commits = behind
            self.trunkBranchBehindCommitsChanged.emit(self._trunk_branch_behind_commits)
            if nofChanged:
                self.trunkBranchBehindChanged.emit(self.trunkBranchBehind)

    @pyqtProperty("QStringList", notify=branchesChanged)
    def branches(self):
        return self._branches

    @branches.setter
    def branches(self, branches):
        if self._branches != branches:
            self._branches = branches
            self.branchesChanged.emit(self._branches)

    @pyqtProperty("QStringList", notify=remoteBranchesChanged)
    def remoteBranches(self):
        return self._remote_branches

    @remoteBranches.setter
    def remoteBranches(self, branches):
        if self._remote_branches != branches:
            self._remote_branches = branches
            self.remoteBranchesChanged.emit(self._remote_branches)

    @pyqtProperty("QStringList", notify=mergedToTrunkBranchesChanged)
    def mergedToTrunkBranches(self):
        return self._merged_to_trunk_branches

    @mergedToTrunkBranches.setter
    def mergedToTrunkBranches(self, branches):
        if self._merged_to_trunk_branches != branches:
            self._merged_to_trunk_branches = branches
            self.mergedToTrunkBranchesChanged.emit(self._merged_to_trunk_branches)

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
