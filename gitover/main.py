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

Display over information of git repository and it's submodules.
"""
import argparse
import logging
import signal
import sys

from gitover.ui.mainwindow import run_gui

ROOT_LOGGER = logging.getLogger(__name__.split(".")[0])
LOGGER = logging.getLogger(__name__)

# PyQt5 hack to see _all_ exceptions

sys._excepthook = sys.excepthook


def exception_hook(exctype, value, traceback):
    "Log exception info otherwise silently swallowed by PyQt"
    LOGGER.error("Unknown exception", exc_info=(exctype, value, traceback))
    sys._excepthook(exctype, value, traceback)


sys.excepthook = exception_hook


# End of PyQt5 hack


def setupLogging(verbose, path=None):
    "Setup logging functionality"
    rootlogger = logging.getLogger()
    hdl = logging.StreamHandler(sys.stdout)
    if verbose:
        hdl.setLevel(logging.DEBUG)
    else:
        hdl.setLevel(logging.INFO)
    rootlogger.addHandler(hdl)
    if path:
        fhdl = logging.FileHandler(path, mode="w", encoding="utf-8")
        fhdl.setLevel(logging.DEBUG)
        fhdl.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(pathname)s(%(lineno)d): %(message)s"))
        rootlogger.addHandler(fhdl)
    rootlogger.setLevel(logging.DEBUG)


def main():
    "Main entry point of program"
    parser = argparse.ArgumentParser(description="""Show git overview in graphical widget.""")
    parser.add_argument('repos', nargs="*")
    grpMisc = parser.add_argument_group('Misc')
    grpMisc.add_argument('--version', action='version', version='%(prog)s')
    grpMisc.add_argument('--verbose', dest='verbose', action="store_true",
                         help='Be more verbose on console.')
    grpMisc.add_argument('--log', dest='logPath', metavar="PATH",
                         help='Store verbose messages during processing in given file too.')
    grpMisc.add_argument('--no-fs-watch', dest='watchFs', action="store_false", default=True,
                         help="Don't watch filesystem changes in repositories.")
    args = parser.parse_args()

    setupLogging(args.verbose, args.logPath)

    if sys.platform == "win32":
        # The default SIGBREAK action remains to call Win32 ExitProcess().
        # We want to handle it as interrupt instead
        signal.signal(signal.SIGBREAK, signal.default_int_handler)

    return run_gui(repo_paths=args.repos, watch_filesystem=args.watchFs)


if __name__ == '__main__':
    try:
        ret = 1
        ret = main()
    except KeyboardInterrupt:
        LOGGER.error("Aborted by user.")
    except SystemExit as exitCode:
        ret = exitCode
    except:
        LOGGER.exception("Unknown exception occurred")
    sys.exit(ret)
