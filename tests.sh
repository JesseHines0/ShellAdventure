#!/bin/bash
mypy shell_adventure shell_adventure/docker_scripts tests
python3.7 -m pytest --cov --cov-report html --cov-report term