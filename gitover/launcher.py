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

Helper functionality to spawn a new instance of Gitover.
"""
import logging

from PyQt5.QtCore import QObject, pyqtSignal


from gitover.qml_helpers import QmlTypeMixin

LOGGER = logging.getLogger(__name__)


class Launcher(QObject, QmlTypeMixin):
    """Launch new instance of Gitover"""

    # emit signal to spawn a new window, loading repository at given path
    openNewWindow = pyqtSignal(["QStringList"], [str], [])

    def __init__(self, parent=None):
        super().__init__(parent)
