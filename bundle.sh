#!/usr/bin/env bash
res/build_resources.sh

# Somehow PyInstaller is unable to find PyQt5 stuff automatically.
# We give it some hints here...
PYQT5_DIR=$(python -c "import os ; import PyQt5 ; print(os.path.dirname(PyQt5.__file__))")
export QT5DIR=/usr/local/Cellar/qt5/5.8.0
export PATH=${QT5DIR}:${PYQT5_DIR}:${PATH}
echo PYQT5_DIR=${PYQT5_DIR}
echo QT5DIR=${QT5DIR}

# When using pyenv virtualenv the Python interpreter must be build with shared option enabled.
# $ env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.5.3
# See https://github.com/pyinstaller/pyinstaller/wiki/Development
#
pyinstaller --icon $(dirname $0)/res/icon.icns --log-level=DEBUG --debug --onefile --windowed --noconfirm --clean -n GitOver --paths $(dirname $0) $(dirname $0)/gitover/main.py

# Add support for high DPI aka retina displays
INFO_PLIST=$(dirname $0)/dist/GitOVer.app/Contents/info.plist
plutil -insert NSPrincipalClass -string NSApplication ${INFO_PLIST}
plutil -insert NSHighResolutionCapable -string True ${INFO_PLIST}
