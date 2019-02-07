all:
	rm -rf build
	pip uninstall -y tst
	python setup.py build -e"/usr/bin/env python"
	python setup.py sdist bdist_wheel
	python setup.py install --user --prefix=
