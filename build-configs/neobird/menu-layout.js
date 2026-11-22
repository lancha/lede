	// Only expose routes present in LuCI's ACL-filtered menu tree.
	renderQuickLinks(tree) {
		const container = document.querySelector('#neobird-quicklinks');
		if (!container)
			return;
		const exists = path => {
			let node = tree;
			for (const part of path)
				node = node && node.children && node.children[part];
			return !!node;
		};
		const slots = [
			{ paths: [['admin', 'status', 'overview']], icon: 'home', title: _('Overview') },
			{ paths: [
				['admin', 'services', 'openclash'],
				['admin', 'services', 'shadowsocksr'],
				['admin', 'services', 'passwall'],
				['admin', 'services']
			], icon: 'ssr', title: _('Services') },
			{ paths: [['admin', 'network', 'network']], icon: 'link', title: _('Network') },
			{ paths: [
				['admin', 'status', 'realtime'],
				['admin', 'status', 'realtime', 'traffic']
			], icon: 'rank', title: _('Realtime Graphs') },
			{ paths: [['admin', 'system', 'admin']], icon: 'user', title: _('Administration') }
		];
		container.replaceChildren();
		for (const slot of slots) {
			const path = slot.paths.find(exists);
			if (!path)
				continue;
			const active = path.every((part, index) => L.env.dispatchpath[index] === part);
			const attrs = { href: L.url(...path), title: slot.title, 'aria-label': slot.title };
			if (active)
				attrs['aria-current'] = 'page';
			container.appendChild(E('a', attrs, [
				E('img', { src: L.env.media + '/images/' + slot.icon + '.png', alt: '', 'aria-hidden': 'true' })
			]));
		}
		container.hidden = container.children.length === 0;
	},

	// Wide status tables scroll independently. Form grids are left unwrapped so
	// their native absolute-positioned dropdowns are not clipped by overflow.
	setupTableLayout() {
		const root = document.querySelector('#maincontent');
		if (!root || typeof MutationObserver === 'undefined')
			return;
		const wrap = () => {
			for (const table of root.querySelectorAll('table.table, div.table')) {
				if (table.querySelector('.cbi-dropdown, input, select, button')) {
					table.classList.add('nb-interactive-table');
					// LuCI sometimes supplies column labels through the header only.
					const titles = table.querySelector('.table-titles, .cbi-section-table-titles');
					if (titles)
						for (const row of table.querySelectorAll('.tr:not(.table-titles):not(.cbi-section-table-titles)'))
							Array.from(row.children).forEach((cell, index) => {
								if (!cell.hasAttribute('data-title') && titles.children[index])
									cell.setAttribute('data-title', titles.children[index].textContent.trim());
							});
					continue;
				}
				if (table.closest('.nb-table-scroll, .cbi-value-field, .cbi-section-table'))
					continue;
				const wrapper = E('div', {
					'class': 'nb-table-scroll', 'tabindex': '0',
					'role': 'region', 'aria-label': _('Table')
				});
				table.parentNode.insertBefore(wrapper, table);
				wrapper.appendChild(table);
			}
		};
		wrap();
		let scheduled = false;
		this.tableObserver = new MutationObserver(() => {
			if (scheduled)
				return;
			scheduled = true;
			window.requestAnimationFrame(() => {
				scheduled = false;
				wrap();
			});
		});
		this.tableObserver.observe(root, { childList: true, subtree: true });
	},
