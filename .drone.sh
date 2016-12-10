#!/bin/bash

set -e

# This is the script run on the drone.io CI service.

pip install -q tox codecov wheel --use-mirrors

# Run tox:
tox --version
tox -e py33,cover,flake8,doctest
codecov

# Run setup script:
python setup.py -q sdist bdist_wheel
