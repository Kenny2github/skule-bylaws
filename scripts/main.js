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
