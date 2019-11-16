PIP_COMPILE := CUSTOM_COMPILE_COMMAND="'make compile_deps' or 'make upgrade_deps'" pip-compile

bundle::
	./bundle.sh

compile_deps::
	${PIP_COMPILE} requirements.in

upgrade_deps::
	${PIP_COMPILE} --upgrade requirements.in

install_deps::
	pip-sync requirements.txt

build_resources::
	res/build_resources.sh