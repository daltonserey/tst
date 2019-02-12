all: clean uninstall
	python setup.py build -e"/usr/bin/env python"
	python setup.py sdist bdist_wheel
	python setup.py install --user --prefix=

uninstall:
	pip uninstall -y tst

clean:
	rm -rf build
	rm -rf dist
	rm -rf tst.egg-info
