from setuptools import setup

setup(name='tst',
      version='0.9.1',
      description='TST Student Testing',
      url='http://github.com/daltonserey/tst',
      author='Dalton Serey',
      author_email='daltonserey@gmail.com',
      license='MIT',
      packages=['tstlib', 'datagen', 'jsonfile'],
      scripts=[
        'bin/gen2.py',
        'bin/runjava',
        'bin/tst',
        'commands/tst-test',
        'commands/tst-check',
        'commands/tst-config',
        'commands/tst-gentests',
        'commands/tst-status',
        'commands/tst-update',
        'commands/tst-checkout', #
        'commands/tst-commit',
        'commands/tst-delete',
        'commands/tst-download',
        'commands/tst-install',
        'commands/tst-list',
        'commands/tst-login',
        'commands/tst-new',
        'commands/tst-release',
      ],
      install_requires=[
        'pyyaml',
      ],
      zip_safe=False)
