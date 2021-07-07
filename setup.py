from setuptools import setup, find_packages
import codecs

setup(name='tst',
      version="0.12.0",
      description='TST Student Testing',
      url='http://github.com/daltonserey/tst',
      author='Dalton Serey',
      author_email='daltonserey@gmail.com',
      license='MIT',
      packages=find_packages(),
      include_package_data=True,
      scripts=[
        'bin/runjava',
        'tst/commands/tst-test',
      ],
      python_requires='>=3.6',
      install_requires=[
        'pyyaml>=5.1',
        'requests>=2.6.1',
        'cachecontrol[filecache]'
      ],
      entry_points = {
        'console_scripts': [
            'tst=tst.commands:main',
        ]
      },
      zip_safe=False)
