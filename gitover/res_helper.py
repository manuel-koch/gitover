import os
import sys

from PyQt5.QtCore import QUrl


def getResourceUrl(path):
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    if getattr(sys, 'frozen', False):
        return QUrl("qrc:/"+path)
    else:
        return QUrl.fromLocalFile(os.path.join(base_dir, 'res/'+path))


