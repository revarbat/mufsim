#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
import platform
from glob import glob

VERSION = "0.9.0"


APP = ['kickstart.py']
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
    bundle_files=2,
    dist_dir='dist-win',
    excludes=["tests", "dist", "build"],
)

if platform.system() == 'Windows':
    import py2exe
    data_files.append(
        (
            "Microsoft.VC90.CRT",
            glob(r'C:\Windows\WinSxS\x86_microsoft.vc90.crt_*\*.*')
        )
    )
    sys.path.append(
        glob(r'C:\Windows\WinSxS\x86_microsoft.vc90.crt_*')
    )
    extra_options['windows'] = APP
    extra_options['zipfile'] = None
elif platform.system() == 'Darwin':
    extra_options['app'] = APP

setup(
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
            'build', 'dist', 'docs', 'examples', 'icons',
            'tests', 'tools',
        ]
    ),
    license='MIT License',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: MIT License',
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
        'console_scripts': ['mufsim=mufsim.console:main'],
        'gui_scripts': ['mufsimgui=mufsim.gui:main']
    },
    install_requires=[
        'setuptools',
        'belfrywidgets>=0.9.4',
        'mudclientprotocol>=0.1.0'
    ],
    data_files=data_files,
    options={
        'py2app': py2app_options,
        'py2exe': py2exe_options,
    },
    # setup_requires=['py2app'],
    **extra_options
)
