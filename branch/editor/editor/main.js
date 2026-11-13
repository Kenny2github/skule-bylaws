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

function appendProposal(proposal) {
	const pending = document.getElementById('pending');
	const passed = document.getElementById('passed');
	const row = document.createElement('tr');
	const td = document.createElement('td');
	const a = document.createElement('a');
	a.innerText = proposal.summary;
	a.href = '?proposal=' + encodeURIComponent(proposal.id);
	td.appendChild(a);
	row.appendChild(td);
	if (proposal.adopted === null) {
		pending.appendChild(row);
	} else {
		const td2 = document.createElement('td');
		td2.innerText = proposal.adopted;
		row.appendChild(td2);
		passed.appendChild(row);
	}
}

async function fetchProposals() {
	const resp = await fetch('/api/proposals');
	if (!resp.ok) throw resp;
	for (const proposal of await resp.json()) {
		appendProposal(proposal);
	}
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
	appendProposal(await resp.json());
}

async function parseFile(path) {
	const resp = await fetch(`/api/master/${path}`);
	if (!resp.ok) throw resp;
	const { meta, html } = await resp.json();
	document.body.innerHTML = `
		<h1 class="cover-page">
			${meta.title}<br/>${meta.subtitle}
			<br/>University of Toronto Engineering Society
		</h1>
		${html}
	`;
}

async function main() {
	await getDisplayName();
	const query = new URLSearchParams(window.location.search);
	if (query.has('proposal')) {
		proposalId = +query.get('proposal');
		if (query.has('file')) {
			await parseFile(query.get('file'));
		}
	}
}

main();
