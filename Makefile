.PHONY: help venv dist test install
.DEFAULT: help

SHELL := /bin/bash
PYCs := $(shell find . -type f -iname '*.pyc')
PYTHONPATH := $(PKG_INSTALL_DIR)/$(PYTHON_PKG_DIR)
SYS_PYTHON=python3
VENV?=venv
INSTALLED=$(VENV)/installed
PYTHON=$(VENV)/bin/python3
TWINE=$(VENV)/bin/twine
PIP=$(PYTHON) -m pip

help:
	@echo "uso: make [ help | venv | clean | install | upload ]"

vars:
	echo SHELL = $(SHELL)
	echo PYCs = $(PYCs)
	echo PYTHONPATH = $(PYTHONPATH)
	echo PKG_INSTALL_DIR = $(PKG_INSTALL_DIR)
	echo PKG_PKG_DIR = $(PKG_PKG_DIR)

venv: $(VENV)/bin/activate
$(VENV)/bin/activate: setup.py requirements.txt
	test -d $(VENV) || $(SYS_PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install wheel
	$(PIP) install --requirement requirements.txt
	touch $(VENV)/bin/activate

install: venv $(INSTALLED)
$(INSTALLED): $(shell find $(MODULE))
	$(PIP) install -e .
	touch $(INSTALLED)

dist: venv requirements.txt
	$(PYTHON) setup.py sdist bdist_wheel
	$(PYTHON) setup.py build -e"/usr/bin/env python3"

clean:
	$(PYTHON) setup.py clean --all
	find . -type f -name "*.pyc" -exec rm '{}' +
	find . -type d -name "__pycache__" -exec rmdir '{}' +
	rm -rf *.egg-info .coverage
	rm -rf dist
	rm -rf build
	rm -rf venv

uptest: clean dist
	$(PYTHON) -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* --skip-existing

$(VENV)/bin/twine:
	$(PIP) install twine

upload: dist $(VENV)/bin/twine
	$(PYTHON) -m twine upload dist/*
