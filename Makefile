.PHONY: help venv dist test install
.DEFAULT: help

SHELL := /bin/bash
PYCs := $(shell find . -type f -iname '*.pyc')
PYTHONPATH := $(PKG_INSTALL_DIR)/$(PYTHON_PKG_DIR)
VENV?=venv
INSTALLED=$(VENV)/installed
PYTHON=$(VENV)/bin/python3
PIP=$(PYTHON) -m pip

help:
	@echo "uso: make [venv | test | vars | install]"

vars:
	echo SHELL = $(SHELL)
	echo PYCs = $(PYCs)
	echo PYTHONPATH = $(PYTHONPATH)
	echo PKG_INSTALL_DIR = $(PKG_INSTALL_DIR)
	echo PKG_PKG_DIR = $(PKG_PKG_DIR)

venv: $(VENV)/bin/activate
$(VENV)/bin/activate: setup.py requirements.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install --requirement requirements.txt
	touch $(VENV)/bin/activate

install: venv $(INSTALLED)
$(INSTALLED): $(shell find $(MODULE))
	$(PIP) install -e .
	touch $(INSTALLED)

dist: requirements.txt
	python3 setup.py sdist bdist_wheel
	python3 setup.py build -e"/usr/bin/env python3"

clean:
	rm -rf venv
	rm -rf build
	rm -rf dist
	rm -rf tst.egg-info

uptest: clean dist
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* --skip-existing

upload: venv dist
	twine upload dist/*
