// Exercise the generated LuCI menu without browser or network dependencies.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

class Element {
    constructor(tag, attrs = {}, children = []) {
        this.tag = tag;
        this.attrs = attrs;
        this.style = { width: '' };
        this.children = [];
        this.childNodes = this.children;
        this.events = {};
        const classes = new Set((attrs.class || '').split(/\s+/).filter(Boolean));
        this.classList = {
            contains: value => classes.has(value),
            add: value => classes.add(value),
            remove: value => classes.delete(value)
        };
        this.offsetLeft = 0;
        this.offsetWidth = 100;
        children.forEach(child => this.appendChild(child));
    }
    appendChild(child) {
        if (typeof child === 'object') {
            if (child.parentNode) {
                const siblings = child.parentNode.children;
                siblings.splice(siblings.indexOf(child), 1);
            }
            child.parentNode = child.parentElement = this;
        }
        this.children.push(child);
        return child;
    }
    get nextElementSibling() {
        return this.parentNode?.children[this.parentNode.children.indexOf(this) + 1];
    }
    addEventListener(name, fn) { this.events[name] = fn; }
    setAttribute(name, value) { this.attrs[name] = value; }
    replaceChildren(...children) { this.children.length = 0; children.forEach(child => this.appendChild(child)); }
    blur() {}
}

function setup(width = 1440, dispatchpath = ['admin', 'store', 'pages', 'store']) {
    const elements = Object.fromEntries([
        '#mainmenu', '#modemenu', '#tabmenu', '.showSide', '.darkMask',
        '.main > .loading', '.main-right', '#neobird-quicklinks'
    ].map(selector => [selector, new Element('div')]));
    elements['.main-left'] = elements['#mainmenu'];
    new Element('div', {}, [elements['#modemenu']]);
    const walk = node => [node, ...node.children.filter(x => typeof x === 'object').flatMap(walk)];
    const document = {
        querySelector: selector => elements[selector],
        querySelectorAll: () => walk(elements['#mainmenu']).filter(
            node => node.tag === 'li' && node.classList.contains('slide') && node.classList.contains('active'))
    };
    const window = { innerWidth: width, addEventListener() {} };
    const ui = {
        menu: { getChildren: node => Object.entries(node.children || {}).map(
            ([name, child]) => ({ ...child, name })) },
        createHandlerFn: (self, name) => self[name].bind(self)
    };
    const L = { env: { dispatchpath, requestpath: dispatchpath, media: '/luci-static/neobird' }, url: (...parts) => '/cgi-bin/luci/' + parts.join('/') };
    const E = (tag, attrs, children) => new Element(Array.isArray(tag) ? 'fragment' : tag, attrs, children);
    const code = fs.readFileSync(path.join(__dirname,
        '../../package/luci-theme-neobird/htdocs/luci-static/resources/menu-neobird.js'), 'utf8');
    const menu = new Function('baseclass', 'ui', 'L', 'E', 'document', 'window', '_', code)(
        { extend: object => object }, ui, L, E, document, window, text => text);
    return { menu, elements, window, walk };
}

test('native menu renders services and a direct iStore link', () => {
    const { menu, elements, walk } = setup();
    menu.render({ children: { admin: { title: 'Administration', children: {
        services: { title: 'Services', children: { openclash: { title: 'OpenClash' } } },
        store: { title: 'iStore' }
    } } } });
    const links = walk(elements['#mainmenu']).filter(node => node.tag === 'a');
    assert.ok(links.some(node => node.attrs.href === '/cgi-bin/luci/admin/store'));
    assert.ok(links.some(node => node.attrs.href === '/cgi-bin/luci/admin/services/openclash'));
    assert.equal(links.find(node => node.attrs['data-title'] === 'Services').children[0], 'Services');
    assert.equal(elements['.main > .loading'].style.visibility, 'hidden');
});

test('quick navigation prefers installed OpenClash and marks the current page', () => {
    const { menu, elements } = setup(1440, ['admin', 'services', 'openclash', 'client']);
    const tree = { children: { admin: { children: {
        status: { children: { overview: {}, realtime: {} } },
        services: { children: { openclash: {}, shadowsocksr: {} } },
        network: { children: { network: {} } },
        system: { children: { admin: {} } }
    } } } };
    menu.renderQuickLinks(tree);
    const bar = elements['#neobird-quicklinks'];
    assert.equal(bar.children.length, 5);
    assert.equal(bar.hidden, false);
    assert.equal(bar.children[1].attrs.href, '/cgi-bin/luci/admin/services/openclash');
    assert.equal(bar.children[1].attrs['aria-current'], 'page');
    assert.equal(bar.children[1].children[0].attrs.src, '/luci-static/neobird/images/ssr.png');
    assert.ok(bar.children.every(link => link.attrs['aria-label']));
    menu.renderQuickLinks(tree);
    assert.equal(bar.children.length, 5, 're-render must not duplicate links');
});

test('quick navigation omits unavailable or unauthorized menu routes', () => {
    const { menu, elements } = setup();
    menu.renderQuickLinks({ children: { admin: { children: {
        status: { children: { overview: {} } }
    } } } });
    assert.deepEqual(elements['#neobird-quicklinks'].children.map(link => link.attrs.href),
        ['/cgi-bin/luci/admin/status/overview']);
    menu.renderQuickLinks({ children: {} });
    assert.equal(elements['#neobird-quicklinks'].hidden, true);
});

test('submenu opens and closes even when a nested icon is clicked', () => {
    const { menu } = setup();
    const anchor = new Element('a');
    const list = new Element('ul');
    const parent = new Element('li', { class: 'slide' }, [anchor, list]);
    // querySelectorAll() represents the rendered active menu.
    const click = { currentTarget: anchor, target: new Element('span'), preventDefault() {}, stopPropagation() {} };
    menu.handleMenuExpand(click);
    assert.equal(parent.classList.contains('active'), true);
    // Use a fresh normal DOM setup for collapse; active nodes must be in mainmenu.
    const second = setup();
    second.elements['#mainmenu'].appendChild(parent);
    second.menu.handleMenuExpand(click);
    assert.equal(parent.classList.contains('active'), false);
});

test('mobile sidebar closes on resize and restores desktop width', () => {
    const { menu, elements, window } = setup(390);
    elements['.main-left'].style.width = '0';
    menu.handleSidebarToggle({ type: 'click' });
    assert.equal(elements['.main-left'].style.visibility, 'visible');
    assert.equal(elements['.showSide'].attrs['aria-expanded'], 'true');
    menu.handleSidebarToggle({ type: 'resize' });
    assert.equal(elements['.main-left'].style.width, '0');
    assert.equal(elements['.showSide'].attrs['aria-expanded'], 'false');
    window.innerWidth = 1440;
    menu.handleSidebarToggle({ type: 'resize' });
    assert.equal(elements['.main-left'].style.width, '');
    assert.equal(elements['.darkMask'].style.visibility, '');
});
