#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
import platform
from glob import glob

VERSION = "0.8.1"


APP = ['mufgui/mufgui.py']
COPYRIGHT = "Copyright 2016 by Revar Desmera"
LONG_DESCR = """\
An offline tokenizer, interpreter, and debugger for MUF, a stack-based
forth-alike MUCK extension language."""

extra_options = {}
data_files = []

py2app_options = dict(
    argv_emulation=True,
    plist=dict(
        CFBundleIconFile="MufSim.icns",
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

py2exe_options = dict(
    bundle_files=1,
    excludes=["tests", "dist", "build"],
)

if platform.system() == 'Windows':
    data_files.append(
        (
            "Microsoft.VC90.CRT",
            glob(
                r'C:\Program Files\Microsoft Visual Studio 9.0\VC\redist' +
                r'\x86\Microsoft.VC90.CRT\*.*'
            )
        )
    )
    sys.path.append(
        r'C:\Program Files\Microsoft Visual Studio 9.0\VC\redist' +
        r'\x86\Microsoft.VC90.CRT'
    )
    extra_options['windows'] = APP

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
    packages=find_packages(
        exclude=[
            'build', 'dist', 'docs', 'examples', 'osxbundlefiles',
            'tests', 'tools',
        ]
    ),
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Compilers',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Software Development :: Testing',
    ],
    keywords='muf muv debugger development',
    entry_points={
        'console_scripts': ['mufsim=mufconsole.mufconsole:main'],
        'gui_scripts': ['mufsimgui=mufgui.mufgui:main']
    },
    install_requires=['setuptools'],
    data_files=data_files,
    options={
        'py2app': py2app_options,
        'py2exe': py2exe_options,
    },
    # setup_requires=['py2app'],
    **extra_options
)
