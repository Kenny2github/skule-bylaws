#!/bin/bash
rm -rf build/*
mkdir -p build
# start builds in parallel
pids=()
for f in **/*.md; do
	if [[ $f =~ (README|LICENSE).* ]]; then continue; fi
	python scripts/md_to_html.py "$f" "build/$(basename "${f%.md}.html")" &
	pids+=($!)
done
# wait for all builds
for pid in ${pids[*]}; do
	wait $pid
done
cp -rf scripts/main.{css,js} scripts/images build/
