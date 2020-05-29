SHELL := /bin/bash
PYCs := $(shell find . -type f -iname '*.pyc')
PYTHONPATH := $(PKG_INSTALL_DIR)/$(PYTHON_PKG_DIR)

vars:
	echo SHELL = $(SHELL)
	echo PYCs = $(PYCs)
	echo PYTHONPATH = $(PYTHONPATH)
	echo PKG_INSTALL_DIR = $(PKG_INSTALL_DIR)
	echo PKG_PKG_DIR = $(PKG_PKG_DIR)

install: build
	python3 setup.py install --user --prefix= --record /tmp/tst-files.txt

build:
	python3 setup.py sdist bdist_wheel
	python3 setup.py build -e"/usr/bin/env python3"

uninstall:
	[ -f /tmp/tst-files.txt ] && (for f in $$(cat /tmp/tst-files.txt); do rm -f $$f; done) || echo "oops"
	[ -f /tmp/tst-files.txt ] && rm -f /tmp/tst-files.txt || true
	pip3 uninstall -y tst

clean:
	rm -rf build
	rm -rf dist
	rm -rf tst.egg-info
	[ "$(PYCs)" ] && rm -f $(PYCs) || true

uptest: clean build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/* --skip-existing

upload: clean build
	twine upload dist/*
