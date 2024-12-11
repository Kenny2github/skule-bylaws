@echo off

python scripts\mds_to_html.py
copy scripts\main.* build
xcopy scripts\images build\images /S /I
