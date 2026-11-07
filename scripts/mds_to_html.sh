#!/bin/bash
python scripts/mds_to_html.py || exit $?
cp -rf scripts/static/* scripts/images build/ || exit $?
