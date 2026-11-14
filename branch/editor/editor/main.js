const displayNameKey = 'displayName';

async function getDisplayName() {
	const resp = await fetch('/api/oauth/verify');
	if (!resp.ok) window.location = '/api/oauth?return_to=' + encodeURIComponent(window.location.href);
	let displayName = localStorage.getItem(displayNameKey);
	if (displayName === null) {
		const userinfo = await resp.json();
		displayName = prompt('Under what name would you like your proposals and comments to be recorded?', userinfo.name);
		localStorage.setItem(displayNameKey, displayName);
	}
	return displayName;
};

/**
 * @param {string} md
 */
async function parseMarkdown(md) {
	const resp = await fetch('/api/parse', {
		method: 'POST',
		body: md,
		headers: {'Content-Type': 'text/markdown'},
	});
	if (!resp.ok) throw resp;
	const parsed = await resp.text();
	return parsed;
}

async function newProposal() {
	const summary = prompt('Please provide a brief summary of your new proposal (e.g. "Update responsibilities of UTEK Director"). You can change this later.');
	if (!summary) return;
	if (summary.length > 512) {
		alert('Summary too long (max 512 characters); try again');
		return;
	}
	const resp = await fetch('/api/proposals', {
		method: 'PUT',
		body: summary,
		headers: { 'Content-Type': 'text/plain' },
	});
	if (!resp.ok) throw resp;
	await hydrate();
}

/**
 * @param {HTMLSpanElement} span
 */
function getSelectedPosition(span) {
	const selection = window.getSelection();
	if (selection.rangeCount === 0) return 0;
	const range = selection.getRangeAt(0);
	const preCaretRange = range.cloneRange();
	preCaretRange.selectNodeContents(span);
	preCaretRange.setEnd(range.endContainer, range.endOffset);
	return preCaretRange.toString().length;
}

/**
 * @param {HTMLSpanElement} span
 */
function onSpanClick(span) {
	const position = getSelectedPosition(span);
	const textarea = document.createElement('textarea');
	textarea.value = span.parentElement.dataset.md;
	textarea.addEventListener('blur', () => onTextareaBlur(textarea));
	span.replaceWith(textarea);
	textarea.focus();
	textarea.setSelectionRange(position, position);
}
/**
 * @param {HTMLTextAreaElement} textarea
 */
async function onTextareaBlur(textarea) {
	const html = await parseMarkdown(textarea.value);
	textarea.parentElement.dataset.md = textarea.value;
	const span = document.createElement('span');
	span.className = 'title';
	span.innerHTML = html;
	span.addEventListener('click', () => onSpanClick(span));
	textarea.replaceWith(span);
}

/**
 * @param {HTMLSpanElement} span
 * @param {"before" | "after" | "inside"} direction
 */
function onAddSectionClick(span, direction) {
	console.log(`TODO: add section ${direction} ${span.dataset.at}`);
}

async function hydrate() {
	const resp = await fetch('/api/editor' + window.location.search);
	if (!resp.ok) throw resp;
	document.body.innerHTML = await resp.text();
	document.querySelectorAll('span.title').forEach(e => e.addEventListener('click', () => onSpanClick(e)));
	document.querySelectorAll('.add-section').forEach(e => {
		const container = document.createElement('span');
		container.className = 'arrows';
		const before = document.createElement('span');
		const after = document.createElement('span');
		const inside = document.createElement('span');
		before.style.bottom = after.style.top = inside.style.left = '1rem';
		before.innerText = '↑';
		before.addEventListener('click', () => onAddSectionClick(e, 'before'));
		after.innerText = '↓';
		after.addEventListener('click', () => onAddSectionClick(e, 'after'));
		inside.innerText = '→';
		inside.addEventListener('click', () => onAddSectionClick(e, 'inside'));
		container.append(before, after, inside);
		e.append(container);
	});
}

async function main() {
	await getDisplayName();
	await hydrate();
}

main();
