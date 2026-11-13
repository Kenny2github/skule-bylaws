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

async function hydrate() {
	const resp = await fetch('/api/editor' + window.location.search);
	if (!resp.ok) throw resp;
	document.body.innerHTML = await resp.text();
}

async function main() {
	await getDisplayName();
	await hydrate();
}

main();
