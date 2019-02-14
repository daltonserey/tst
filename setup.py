from setuptools import setup, find_packages

setup(name='tst',
      version='0.9a18',
      description='TST Student Testing',
      url='http://github.com/daltonserey/tst',
      author='Dalton Serey',
      author_email='daltonserey@gmail.com',
      license='MIT',
      packages=find_packages(),
      include_package_data=True,
      scripts=[
        'bin/runjava',
        'bin/tst',
        'etc/tst.completion.sh',
        'commands/tst-test',
        'commands/tst-completion',
        'commands/tst-config',
        'commands/tst-status',
        'commands/tst-checkout',
        'commands/tst-checkout2',
        'commands/tst-commit',
        'commands/tst-delete',
        'commands/tst-login',
        'commands/tst-new',
      ],
      install_requires=[
        'pyyaml',
        'requests'
      ],
      entry_points = {
        'console_scripts': [
            'tst=tst.commands:main',
        ]
      },
      zip_safe=False)
