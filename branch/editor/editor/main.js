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

getDisplayName();
