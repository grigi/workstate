'''
Simple Asset pipeline toolset
'''
from setuptools import setup

import workstate

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
    test_suite='tests',

    # Dependencies
    install_requires=[],
    tests_require=[],

    # Packages
    packages=['workstate'],
    include_package_data=True,
    package_data={'': ['README.rst']},

    # Scripts
    # scripts=[],

    # Classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: pypy',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Documentation',
    ]
)
