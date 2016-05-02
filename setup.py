#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION="0.7.3"

COPYRIGHT="Copyright 2016 by Revar Desmera"
LONG_DESCR = """\
An offline tokenizer, interpreter, and debugger for MUF, a stack-based
forth-alike MUCK extension language."""

APP = ['mufgui/mufgui.py']
DATA_FILES = []
OPTIONS = dict(
    argv_emulation=True,
    plist=dict(
        CFBundleIdentifier="com.belfry.mufsimulator",
        CFBundleGetInfoString="MufSimulator v%s, %s" % (VERSION, COPYRIGHT),
        NSHumanReadableCopyright=COPYRIGHT,
        NSHighResolutionCapable=True,
        CFBundleDocumentTypes=[
            dict(
                CFBundleTypeName="MUF File",
                CFBundleTypeRole="Viewer",
                LSHandlerRank="Alternate",
                CFBundleTypeMIMETypes=["text/x-muf", "application/x-muf"],
                LSItemContentTypes=["org.fuzzball.muf"],
                CFBundleTypeExtensions=["muf"],
            ),
            dict(
                CFBundleTypeName="MUV File",
                CFBundleTypeRole="Viewer",
                LSHandlerRank="Alternate",
                CFBundleTypeMIMETypes=["text/x-muv", "application/x-muv"],
                LSItemContentTypes=["com.belfry.muv"],
                CFBundleTypeExtensions=["muv"],
            ),
        ]
    )
)

setup(
    app=APP,
    name='MufSim',
    version=VERSION,
    description='Muf language simulator and debugger.',
    long_description=LONG_DESCR,
    author='Revar Desmera',
    author_email='revarbat@gmail.com',
    url='https://github.com/revarbat/mufsim',
    download_url='https://github.com/revarbat/mufsim/archive/master.zip',
    packages=find_packages(exclude=['examples', 'tools', 'docs', 'tests']),
    license='BSD 2-clause',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Compilers',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Software Development :: Testing',
    ],
    keywords='muf debugger development',
    entry_points={
        'console_scripts': [
            'mufsim=mufconsole.mufconsole:main'
        ],
        'gui_scripts': [
            'mufsimgui=mufgui.mufgui:main'
        ]
    },
    install_requires=[
        'setuptools',
    ],
    data_files=DATA_FILES,
    options={
        'py2app': OPTIONS
    },
    setup_requires=[
        'py2app'
    ],
)
