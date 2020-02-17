SHELL := /bin/bash
PYCs := $(shell find . -type f -iname '*.pyc')

install: build
	python setup.py install --user --prefix= --record /tmp/tst-files.txt

build:
	python setup.py sdist bdist_wheel
	python setup.py build -e"/usr/bin/env python"

uninstall:
	[ -f /tmp/tst-files.txt ] && (for f in $$(cat /tmp/tst-files.txt); do rm -f $$f; done) || echo "oops"
	[ -f /tmp/tst-files.txt ] && rm -f /tmp/tst-files.txt || true
	pip uninstall -y tst

clean:
	rm -rf build
	rm -rf dist
	rm -rf tst.egg-info
	[ "$(PYCs)" ] && rm -f $(PYCs) || true

uptest: clean build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/* --skip-existing

upload: clean build
	twine upload dist/*
