#!/usr/bin/env python3

import re
import setuptools

with open("yaml_requests/_version.py", "r") as f:
    try:
        version = re.search(
            r"__version__\s*=\s*[\"']([^\"']+)[\"']",f.read()).group(1)
    except:
        raise RuntimeError('Version info not available')

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="yaml_requests",
    version=version,
    author="Toni Kangas",
    description="A simple python app for sending a set of consecutive HTTP requests defined in YAML requests plan.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kangasta/yaml_requests",
    packages=setuptools.find_packages(),
    scripts=["bin/yaml_requests"],
    install_requires=[
        "Jinja2~=2.0",
        "pyyaml~=5.0",
        "requests~=2.0",
    ],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    )
)
