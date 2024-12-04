@echo off

if exist build (
	for /D %%i in (build\*) do rmdir /S /Q %%i
	del /Q build\*
) else mkdir build

for /R %%i in (*.md) do (
	if /I "%%~ni"=="README" (
		rem Skipping %%i
	) else if /I "%%~ni"=="LICENSE" (
		rem Skipping %%i
	) else (
		python scripts\md_to_html.py "%%i" "build/%%~ni.html"
	)
)

copy scripts\main.* build
xcopy scripts\images build\images /S /I
