import logging
import re

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, QTimer
from PyQt5.QtGui import QSyntaxHighlighter, QColor, QTextCharFormat, QBrush, QFontMetrics, QFont
from PyQt5.QtQuick import QQuickTextDocument

from gitover.qml_helpers import QmlTypeMixin

LOGGER = logging.getLogger(__name__)


class GitDiffHightlighter(QSyntaxHighlighter):
    """Highlight parts of document containing git diff output"""

    HEADER_DIFF_RE = re.compile("""^diff --git a/(?P<a>.+) b/(?P<b>.+)""")
    HEADER_INDEX_RE = re.compile("""^index \S+\.\.\S+ \S+""")
    HEADER_NAME_A_RE = re.compile("""^--- a/.+""")
    HEADER_NAME_B_RE = re.compile("""^\+\+\+ b/.+""")
    HEADER_HUNK_RE = re.compile("""^@@ [-\+]?\d+,[-\+]?\d+ [-\+]?\d+,[-\+]?\d+ @@""")
    HEADER_CHANGE_A_RE = re.compile("""^-.+""")
    HEADER_CHANGE_B_RE = re.compile("""^\+.+""")

    def __init__(self, doc=None):
        super().__init__(doc)

    def highlightBlock(self, text):
        """Apply highlighting format by analyzing given text"""
        self._applyFormat(text, self.HEADER_DIFF_RE, {"fg": "blue"})
        self._applyFormat(text, self.HEADER_INDEX_RE, {"fg": "blue"})
        self._applyFormat(text, self.HEADER_NAME_A_RE, {"fg": "red"})
        self._applyFormat(text, self.HEADER_NAME_B_RE, {"fg": "green"})
        self._applyFormat(text, self.HEADER_HUNK_RE, {"fg": "orange"})
        self._applyFormat(text, self.HEADER_CHANGE_A_RE, {"fg": "red"})
        self._applyFormat(text, self.HEADER_CHANGE_B_RE, {"fg": "green"})

    def _applyFormat(self, text, regexp, fmt):
        for m in regexp.finditer(text):
            fmt_ = fmt(m.group(0)) if callable(fmt) else fmt
            if not fmt_:
                return
            grp = "subject" if "subject" in m.groupdict() else 0
            s = m.start(grp)
            e = m.end(grp)
            charfmt = QTextCharFormat()
            if fmt_.get("fg", "") and QColor.isValidColor(fmt_.get("fg")):
                charfmt.setForeground(QBrush(QColor(fmt_.get("fg"))))
            if fmt_.get("bg", "") and QColor.isValidColor(fmt_.get("bg")):
                charfmt.setBackground(QBrush(QColor(fmt_.get("bg"))))
            self.setFormat(s, e - s, charfmt)


class GitDiffFormatter(QObject, QmlTypeMixin):
    """Takes a QTextDocument and applies formatting on it"""

    textDocumentChanged = pyqtSignal(QQuickTextDocument)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._txtdoc = None
        self._highlighter = None

    @pyqtProperty(QQuickTextDocument, notify=textDocumentChanged)
    def textDocument(self):
        return self._doc

    def _setTabWidth(self):
        """Set tab width for document based on current font"""
        if not self._txtdoc:
            return
        spaces = " " * 4
        metrics = QFontMetrics(self._txtdoc.defaultFont())
        tabWidth = metrics.width(spaces);
        textOptions = self._txtdoc.defaultTextOption()
        textOptions.setTabStop(tabWidth)
        self._txtdoc.setDefaultTextOption(textOptions)

    @textDocument.setter
    def textDocument(self, doc):
        if self._doc != doc:
            self._doc = doc
            self._txtdoc = self._doc.textDocument() if self._doc else None
            if self._highlighter:
                self._highlighter.setDocument(self._txtdoc)
            else:
                self._highlighter = GitDiffHightlighter(self._txtdoc)
            self.textDocumentChanged.emit(self._doc)
            self._highlighter.rehighlight()

            # setting highlighter and tabwidth immediately seems to trigger strange
            # raising condition that leads to Qt crash !?
            # Postpone setting tab width avoids the crash (temporarily) !?
            QTimer.singleShot(50, self._setTabWidth)
