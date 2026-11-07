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
