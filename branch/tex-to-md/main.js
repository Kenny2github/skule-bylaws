matchMedia('print').addEventListener('change', m => {
	if (!m.matches) return;
	const spans = Array.from(document.querySelectorAll('section.contents a + span'));
	const h1s = Array.from(document.querySelectorAll('h1[id]'));
	// get inch to px conversion
	const elem = document.createElement('test');
	elem.style.fontSize = '1in';
	document.body.appendChild(elem);
	const inch = +getComputedStyle(elem).fontSize.slice(0, -2);
	document.body.removeChild(elem);
	for (let i = 0; i < h1s.length; ++i) {
		spans[i].innerText = Math.floor(h1s[i].getBoundingClientRect().top / (9 * inch)) + 1;
	}
});

/**
 * @param {string} needle Value to search for.
 */
function search() {
	let needle = document.getElementById('search').value;
	if (needle.length < 3) return;
	/**
	 * @type {{string: [string, {string: [string, string]}]}}
	 */
	const index = window.index;
	const repl = '<b>$&</b>';
	const results = document.getElementById('search-results');
	const regex = document.getElementById('regex-search').checked;
	if (regex) {
		needle = new RegExp(needle, 'ig');
	} else {
		needle = new RegExp(needle.replace(/[/\-\\^$*+?.()|[\]{}]/g, '\\$&'), 'ig')
	}
	results.textContent = '';
	const files = Object.entries(index);
	files.sort(([a,], [b,]) => a.localeCompare(b));
	for (const [file, [title, content]] of files) {
		const sections = Object.entries(content);
		sections.sort(([, [a,]], [, [b,]]) => a.localeCompare(b));
		for (const [section, [href, text]] of sections) {
			const line = text.replaceAll(needle, repl);
			if (line == text) continue;
			const result = document.createElement('li');
			result.innerHTML = `<a href="${file}${href}">${title} ${section}</a>: ${line}`
			results.appendChild(result);
		}
	}
}
