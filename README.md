GitOver
=======

Show overview of multiple git repositories incl. sub-repositories and provide basic
git interactions :

* Show current branch
* Show current branch's tracking/remote branch and ahead/behind counters
* Show current branch's trunk branch and ahead/behind counters
* Show remote branches
* Show status info for modified, staged, untracked, deleted or conflicting files
* Checkout to another local branch by selecting a local branch from dropdown list
* Basic git functions like
    * status
    * fetch
    * pull
    * push (forced)
    * show diff of changed files
* Customizable context menu to trigger functionality, e.g. to start terminal or tool
  at current repositories root
* Automatically update repository status when filesystem changes are detected

## GitOver makes use of...

* [Python][1]
* [PyQt5][2], to implement a cross platform UI
* [GitPython][3], to display repository info and trigger git actions
* [PyInstaller][4], to bundle an easy to distribute application bundle

[1]: https://docs.python.org "Python"
[2]: http://pyqt.sourceforge.net/Docs/PyQt5/ "PyQt5"
[3]: http://gitpython.readthedocs.io/en/stable/ "GitPython"
[4]: http://www.pyinstaller.org/ "PyInstaller"
