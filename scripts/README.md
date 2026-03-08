# Build and CI documentation

## Purposes of scripts

Script | Inputs | Outputs
-------|--------|---------
`diff_to_annotations.py` | Full-context diff of all Markdown files as stdin, and all Markdown files in their current state | [Workflow commands](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#setting-a-warning-message) that set debug, notice, warning, and error messages on all Markdown files
`diff_to_table.py` | Full-context diff of all Markdown files as stdin, and the tag names for deleted sections (`s`/`del`) and added sections (`u`/`ins`) as command-line arguments | Markdown-HTML table unified diff of section changes
`mds_to_html.*` | Contents of repository | `build` directory with GitHub Pages-ready build

## Other files in `scripts`
`lineno_to_section.py` is a helper module used by the Python scripts.

`requirements.txt` is a Pip requirements file for the Python scripts.

`main.js`, `main.css`, and `images` are the static content for the GitHub Pages build.

`template.jinja2` is used by `mds_to_html.py` for individual HTML generation.

## GitHub Actions workflows

### `branch-deleted.yml`
Deletes branch-specific GitHub Pages builds when the corresponding branch is deleted.

### `generate-html-pdfs.yml`
This does two main things on push, if the push modified Markdown or `scripts` files:
- Generates and commits the GitHub Pages build for the pushed commit, putting it under `branch/<branch>` if the commit is not on the default branch.
- Uses the generated Pages build to generate PDFs for each Markdown file (using headless Chrome print-to-PDF), uploads them as artifacts, and if the commit is on the default branch, commits and pushes the PDFs.

### `pr-opened.yml`
This comments links to the following things on newly opened PRs which modify Markdown or `scripts` files:
- The PR diff, to draw attention to annotations
- The GitHub Pages build, for easy access
- The workflow run listing, to draw attention to PDF build artifacts

This also closes the PR if the source repository does not have GitHub Pages set up, noting that fact in the process, to ensure they can see the Pages build.

### `pr-synced-noindex.yml`
This is a simple check that fails if, in a modified file other than [`index.md`](../index.md) which already had a `revdate:` field in the Markdown frontmatter, that field was not modified.

### `pr-synced-target.yml`
This generates and comments (if non-empty) a section-by-section diff of Markdown changes, in unified diff format tabulated by section number and text. The table is given in both GitHub and Google Docs flavored markdown, the latter for copying.

> [!CAUTION]
> This is a `pull_request_target` workflow that checks out the HEAD version of the repository to get the modifications to the Markdown. It prevents malicious script injection by then checking out the base version of the scripts. Care should be taken that the latter mechanism is not broken or bypassed.

### `pr-synced.yml`
This generates [workflow commands](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#setting-a-warning-message) that set the following messages:
- `notice` messages for:
   - Unchanged sections that refer to sections that did not exist previously, as a reminder to check that the reference was made correctly.
   - Sections that have changed and refer to sections that have not changed, as a reminder to check the references.
   - Sections that have changed and refer to sections that have changed, as a reminder to check the references.
- `warning` messages for unchanged sections that refer to other sections which have changed, and may therefore be out of date.
- `error` messages for sections which refer to nonexistent sections.
