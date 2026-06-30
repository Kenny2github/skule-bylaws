#!/bin/bash
python scripts/mds_to_html.py
cp -rf scripts/main.{css,js} images scripts/images build/
