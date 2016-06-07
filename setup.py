#!/usr/bin/python3
"""
duply_notify -- duplicity wrapper for KDE notification daemon

duply_notify is a duplicity wrapper that shows progress in KDE notification area

@author:     Dmitry Nezhevenko

@license:    GPLv2+

@contact:    dion@dion.org.ua
"""

from distutils.core import setup

setup(
    name='duply_notify',
    version='0.1',
    packages=['duplynotify'],
    url='https://github.com/dionorgua/duply_notify',
    license='GPLv2+',
    author='Dmitry Nezhevenko',
    author_email='dion@dion.org.ua',
    description='duply/duplicity wrapper that shows nice progressbar in KDE notification area',
    scripts=['bin/duply_notify'],
)
