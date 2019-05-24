import datetime
import logging
import time

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from PyQt5.QtCore import QTimer

LOGGER = logging.getLogger(__name__)


class WakeupWatcher(QObject):
    # signal gets emitted when wake has been detected
    awake = pyqtSignal()

    period_seconds = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_ping = None
        self._timer = QTimer(self)
        self._timer.setInterval(self.period_seconds * 1000)
        self._timer.timeout.connect(self._ping)
        self._timer.start()

    def _ping(self):
        now = datetime.datetime.utcnow()
        dt = (now - self._last_ping) if self._last_ping else datetime.timedelta()
        if dt.total_seconds() > 30:
            LOGGER.info(f"Appears awake after {dt}")
            self.awake.emit()
        self._last_ping = now
