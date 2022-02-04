#!/usr/bin/env bash

SIGN_APP_BUNDLE=true
BUILD_DMG=true
while [ $# -gt 0 ] ; do
    case $1 in
      --build-dmg)
        BUILD_DMG=true
        shift
        ;;
      --no-build-dmg)
        BUILD_DMG=false
        shift
        ;;
      --sign-app)
        SIGN_APP_BUNDLE=true
        shift
        ;;
      --no-sign-app)
        SIGN_APP_BUNDLE=false
        shift
        ;;
      *)
        echo "Invalid argument: ${1}"
        exit 1
        ;;
    esac
done


res/build_resources.sh

# Somehow PyInstaller is unable to find PyQt5 stuff automatically.
# We give it some hints here...
#PYQT5_DIR=$(python -c "import os ; import PyQt5 ; print(os.path.dirname(PyQt5.__file__))")
#export QT5DIR=/usr/local/Cellar/qt5/5.8.0
#export PATH=${QT5DIR}:${PYQT5_DIR}:${PATH}
#echo PYQT5_DIR=${PYQT5_DIR}
#echo QT5DIR=${QT5DIR}

THIS_DIR=$(dirname $0)
BUNDLE_NAME=GitOver
DIST_DIR=${THIS_DIR}/dist
BUNDLE_DIR=${DIST_DIR}/${BUNDLE_NAME}.app
BUNDLE_CONTENTS_DIR=${BUNDLE_DIR}/Contents
BUNDLE_MACOS_DIR=${BUNDLE_CONTENTS_DIR}/MacOS
BUNDLE_ICON=${THIS_DIR}/res/icon.icns
BUNDLE_VERSION=$(grep "gitover_version =" ${THIS_DIR}/gitover/ui/resources.py | cut -d "=" -f 2 | tr -d " '")
BUNDLE_DMG_NAME=${BUNDLE_NAME}_${BUNDLE_VERSION}
SIGNING_CERT="GitOverSigning2"

# When using pyenv virtualenv the Python interpreter must be build with shared option enabled.
# $ env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.2
# See https://github.com/pyinstaller/pyinstaller/wiki/Development
#
# Extended debug while building/running application:
# --log-level=DEBUG --debug
echo ================================================================
echo == Building app bundle
echo ================================================================
pyinstaller --icon ${BUNDLE_ICON} \
    --onefile --windowed --noconfirm --clean \
    --hidden-import PyQt5.sip \
    --osx-bundle-identifier de.manuelkoch.gitover \
    -n ${BUNDLE_NAME} \
    --paths ${THIS_DIR} \
    ${THIS_DIR}/gitover/main.py || exit 1

echo ================================================================
echo == Updating app bundle properties
echo ================================================================
# Add support for high DPI aka retina displays
INFO_PLIST=${BUNDLE_CONTENTS_DIR}/Info.plist
plutil -insert NSPrincipalClass -string NSApplication ${INFO_PLIST}
plutil -insert NSHighResolutionCapable -string True ${INFO_PLIST}
plutil -replace CFBundleShortVersionString -string ${BUNDLE_VERSION} ${INFO_PLIST}

echo ================================================================
echo == Adding other files to app bundle
echo ================================================================
cp ${THIS_DIR}/COPYING ${BUNDLE_MACOS_DIR}
cp ${THIS_DIR}/LICENSE ${BUNDLE_MACOS_DIR}
cp ${THIS_DIR}/README.md ${BUNDLE_MACOS_DIR}

if $SIGN_APP_BUNDLE ; then
  echo ================================================================
  echo == Code signing app bundle using certificate ${SIGNING_CERT}
  echo ================================================================
  # see https://github.com/pyinstaller/pyinstaller/wiki/Recipe-OSX-Code-Signing
  # and https://github.com/pyinstaller/pyinstaller/wiki/Recipe-OSX-Code-Signing-Qt
  ${THIS_DIR}/res/fix_app_qt_folder_names_for_codesign.py ${BUNDLE_DIR}
  echo == Checking code signing cert...
  security find-certificate -c "${SIGNING_CERT}" -p | openssl x509 -noout -text  -inform pem | grep -E "Validity|(Not (Before|After)\s*:)"
  echo == Signing code...
  codesign --verbose=4 --force --deep --sign "${SIGNING_CERT}" ${BUNDLE_DIR}
  echo == Signed app bundle...
  codesign --verbose=4 --display ${BUNDLE_DIR}
fi

if $BUILD_DMG ; then
  echo ================================================================
  echo == Build DMG of app bundle
  echo ================================================================
  test -f ${DIST_DIR}/${BUNDLE_DMG_NAME}.dmg && rm -f ${DIST_DIR}/${BUNDLE_DMG_NAME}.dmg
  create-dmg --volname ${BUNDLE_NAME} --volicon ${BUNDLE_ICON} \
             --icon "${BUNDLE_NAME}.app" 110 150 \
             --app-drop-link 380 150 \
             --background res/dmg_bg.png \
             ${DIST_DIR}/${BUNDLE_DMG_NAME}.dmg \
             ${BUNDLE_DIR}

  echo ================================================================
  echo == Build checksum of DMG
  echo ================================================================
  pushd ${DIST_DIR} >/dev/null
  shasum -a 256 ${BUNDLE_DMG_NAME}.dmg > ${BUNDLE_DMG_NAME}.sha256
  popd >/dev/null
fi
