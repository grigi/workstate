"Simple Asset pipeline toolset"
import sys
from setuptools import setup

import workstate

if sys.version_info[0:2] == (2, 6):
    DEPS = ['ordereddict']
    TEST_DEPS = ['unittest2']
else:
    DEPS = []
    TEST_DEPS = []

setup(
    name='workstate',
    version=workstate.VERSION,
    description=workstate.__doc__,
    long_description=open('README.rst').read(),
    author='Nickolas Grigoriadis',
    author_email='nagrigoriadis@gmail.com',
    url='https://github.com/grigi/workstate',
    license='MIT',
    zip_safe=False,
    test_suite='workstate.test_suite',

    # Dependencies
    install_requires=DEPS,
    tests_require=TEST_DEPS,

    # Packages
    packages=['workstate'],
    include_package_data=True,
    package_data={'': ['README.rst']},

    # Scripts
    #scripts=[],

    # Classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
