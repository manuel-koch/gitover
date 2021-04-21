PIP_COMPILE := CUSTOM_COMPILE_COMMAND="'make compile_deps' or 'make upgrade_deps'" pip-compile

bundle::
	./bundle.sh

bundle_without_signed_dmg::
	./bundle.sh --no-sign-app --no-build-dmg

compile_deps::
	${PIP_COMPILE} requirements.in

list_outdated_deps::
	pip list --outdated

upgrade_deps::
	${PIP_COMPILE} --upgrade requirements.in

install_deps::
	pip install --upgrade pip pip-tools wheel
	pip-sync requirements.txt

build_resources::
	res/build_resources.sh
