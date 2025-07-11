#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="filespacer",
    version="1.0.0",
    author="Your Name",
    description="A powerful tool for compressing and decompressing files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tilltmk/filespacer",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "filespacer=filespacer.__main__:main",
            "filespacer-cli=filespacer.cli:cli",
        ],
    },
)