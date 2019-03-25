PYCs:=$(shell find . -type f -iname '*.pyc')

install: build
	python setup.py install --user --prefix=

build:
	python setup.py sdist bdist_wheel
	python setup.py build -e"/usr/bin/env python"

uninstall:
	pip uninstall -y tst

clean:
	rm -rf build
	rm -rf dist
	rm -rf tst.egg-info
	[ $(PYCs) ] && rm -f $(PYCs) || true
