from setuptools import setup, find_packages

setup(
    name='tst',
    version="0.19.0",
    description='TST Simple Test Runner',
    url='http://github.com/daltonserey/tst',
    author='Dalton Serey',
    author_email='daltonserey@gmail.com',
    maintainer='Dalton Serey',
    maintainer_email='daltonserey@gmail.com',
    license='MIT',
    packages=find_packages(),
    py_modules = ['undertst'],
    include_package_data=True,
    scripts=[
        'bin/runjava',
    ],
    python_requires='>=3.8',
    install_requires=[
        'pyyaml>=5.4.1',
        'requests>=2.6.1',
        'cachecontrol[filecache]'
    ],
    entry_points = {
        'console_scripts': [
            'tst=tst.commands:main',
        ]
    },
    zip_safe=False
)
