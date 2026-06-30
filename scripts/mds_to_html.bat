@echo off

python scripts\mds_to_html.py
copy scripts\main.* build
xcopy images build\images /S /I /Y
xcopy scripts\images build\images /S /I /Y
