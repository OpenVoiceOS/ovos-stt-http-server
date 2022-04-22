#!/usr/bin/env python3
from setuptools import setup

setup(
    name='ovos-stt-http-server',
    version='0.0.2a1',
    description='simple aiohttp server to host OpenVoiceOS stt plugins as a service',
    url='https://github.com/OpenVoiceOS/ovos-stt-http-server',
    author='JarbasAi',
    author_email='jarbasai@mailfence.com',
    license='Apache-2.0',
    packages=['ovos_stt_http_server'],
    install_requires=["ovos-plugin-manager", "flask"],
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='plugin STT OVOS OpenVoiceOS',
    entry_points={
        'console_scripts': [
            'ovos-stt-server=ovos_stt_http_server.__main__:main'
        ]
    }
)
