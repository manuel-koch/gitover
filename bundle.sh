#!/usr/bin/env bash
res/build_resources.sh

# Somehow PyInstaller is unable to find PyQt5 stuff automatically.
# We give it some hints here...
PYQT5_DIR=$(python -c "import os ; import PyQt5 ; print(os.path.dirname(PyQt5.__file__))")
export QT5DIR=/usr/local/Cellar/qt5/5.8.0
export PATH=${QT5DIR}:${PYQT5_DIR}:${PATH}
echo PYQT5_DIR=${PYQT5_DIR}
echo QT5DIR=${QT5DIR}

THIS_DIR=$(dirname $0)
BUNDLE_CONTENTS_DIR=${THIS_DIR}/dist/GitOver.app/Contents
BUNDLE_MACOS_DIR=${BUNDLE_CONTENTS_DIR}/MacOS

# When using pyenv virtualenv the Python interpreter must be build with shared option enabled.
# $ env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.5.3
# See https://github.com/pyinstaller/pyinstaller/wiki/Development
#
# Extended debug while building/running application:
# --log-level=DEBUG --debug
pyinstaller --icon ${THIS_DIR}/res/icon.icns --onefile --windowed --noconfirm --clean -n GitOver --paths ${THIS_DIR} ${THIS_DIR}/gitover/main.py

# Add support for high DPI aka retina displays
INFO_PLIST=${BUNDLE_CONTENTS_DIR}/Info.plist
plutil -insert NSPrincipalClass -string NSApplication ${INFO_PLIST}
plutil -insert NSHighResolutionCapable -string True ${INFO_PLIST}

# Add various info texts too
cp ${THIS_DIR}/COPYING ${BUNDLE_MACOS_DIR}
cp ${THIS_DIR}/LICENSE ${BUNDLE_MACOS_DIR}
cp ${THIS_DIR}/README.md ${BUNDLE_MACOS_DIR}