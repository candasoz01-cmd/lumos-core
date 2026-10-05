"""Build a limited company-site artifact without moving the application backend."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import json
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIST = ROOT / 'ui/dist'
SITE = HERE / '.generated/site'
ORIGIN = 'https://lumosai.company'
APP = 'https://app.lumosai.company'
PAGES = ('/', '/accessibility', '/education', '/lab', '/integrations', '/privacy', '/terms', '/data-and-trust', '/slack', '/cyber', '/connect/mac')
MEDIA = {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.mp4', '.webm'}


def gate(extra=()):
    config = json.loads((ROOT / 'config/publication/gate_config.json').read_text())
    config['public_surfaces'] += list(extra)
    with tempfile.NamedTemporaryFile('w', suffix='.json') as f:
        json.dump(config, f)
        f.flush()
        subprocess.run(['python3', 'ops/publication_gate/gate.py', '--config', f.name], cwd=ROOT, check=True)


def source(path):
    candidate = DIST / path.lstrip('/')
    if not candidate.resolve().is_relative_to(DIST.resolve()) or candidate.is_symlink():
        raise ValueError('Asset path escapes build output')
    if not candidate.is_file():
        raise FileNotFoundError(path)
    return candidate


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('src', 'poster'):
            if a.get(key, '').startswith('/'):
                self.paths.add(urlsplit(a[key]).path)
        if tag == 'link' and a.get('rel') in ('stylesheet', 'icon', 'apple-touch-icon', 'modulepreload'):
            if a.get('href', '').startswith('/'):
                self.paths.add(urlsplit(a['href']).path)


def company_text(text):
    replacements = {
        'https://welockai.com/chatlumos-task-focus.png': ORIGIN + '/chatlumos-task-focus.png',
        'Lumos Company · welockai.com': 'Lumos Company · lumosai.company',
        'Bu bildirim, welockai.com': 'Bu bildirim, lumosai.company, welockai.com',
        'Bu bildirim welockai.com': 'Bu bildirim lumosai.company, welockai.com',
        'processing across welockai.com': 'processing across lumosai.company, welockai.com',
        'This notice covers welockai.com': 'This notice covers lumosai.company, welockai.com',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def prepare_html(text, route):
    canonical = ORIGIN + route
    text = re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")[^"]+', lambda m: m[1] + canonical, text)
    text = re.sub(r'(<meta\b[^>]*property="og:url"[^>]*content=")[^"]+', lambda m: m[1] + canonical, text)
    text = company_text(text)
    # The company shell has its own install identity; the product uses its own application origin.
    text = text.replace('href="/chat-lumos-mark.svg"', 'href="/lumos-tree-logo.svg"')
    def link(match):
        tag = match[0]
        def attr(m):
            url = m[2]
            path = urlsplit(url).path.rstrip('/') or '/'
            is_app_path = path in {'/auth', '/panel'} or path.startswith(('/auth/', '/api/', '/integrations/'))
            if url.startswith('/') and not url.startswith('//') and path not in PAGES and is_app_path:
                return m[1] + APP + url + '"'
            return m[0]
        return re.sub(r'((?:href|action)=")([^"]+)"', attr, tag)
    text = re.sub(r'<(?:a|form)\b[^>]*>', link, text)
    if route == '/':
        data = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Lumos AI',
                'url': ORIGIN + '/', 'publisher': {'@type': 'Organization', 'name': 'We Lock AI', 'url': 'https://welockai.com/'}}
        text = text.replace('</head>', '<script type="application/ld+json">' + json.dumps(data) + '</script></head>')
    return text


def main():
    snapshot = HERE / '.generated/source'
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in ('company-worker.mjs', 'build_company.py'):
        shutil.copyfile(HERE / name, snapshot / name)
    gate(['ops/cloudflare/.generated/source'])
    subprocess.run(['npm', 'run', 'build'], cwd=ROOT / 'ui', check=True)
    # Keep the previous generated candidate recoverable, never mix stale pages into a new one.
    if SITE.exists():
        SITE.rename(SITE.with_name('previous-' + str(time.time_ns())))
    SITE.mkdir(parents=True)
    pending = {'/chatlumos-task-focus.png', '/lumos-tree-logo.svg'}
    for route in PAGES:
        relative = 'index.html' if route == '/' else route.lstrip('/') + '/index.html'
        text = prepare_html(source(relative).read_text(), route)
        target = SITE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        parser = Assets()
        parser.feed(text)
        pending.update(parser.paths)
    copied = set()
    while pending:
        path = pending.pop()
        if path in copied:
            continue
        src = source(path)
        if src.suffix not in MEDIA | {'.js', '.css'}:
            raise ValueError('Unexpected asset type: ' + path)
        target = SITE / path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in {'.js', '.css'}:
            text = company_text(src.read_text())
            target.write_text(text)
            # Include locale-selected images, CSS URLs and relative bundled imports.
            for ref in re.findall(r'''["'(]((?:/|\./|\.\./)[^"'()\s<>]+)["')]''', text):
                clean = urlsplit(ref).path
                if Path(clean).suffix not in MEDIA | {'.js', '.css'}:
                    continue
                dep = clean if clean.startswith('/') else '/' + (src.parent / clean).resolve().relative_to(DIST.resolve()).as_posix()
                pending.add(dep)
        else:
            shutil.copyfile(src, target)
        copied.add(path)
    (SITE / 'manifest.webmanifest').write_text(json.dumps({
        'name': 'Lumos AI', 'short_name': 'Lumos', 'id': '/', 'start_url': '/', 'scope': '/',
        'display': 'browser', 'theme_color': '#0a0e14', 'background_color': '#0a0e14',
        'icons': [{'src': '/lumos-tree-logo.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]
    }, indent=2))
    (SITE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        ''.join('<url><loc>' + ORIGIN + route + '</loc></url>' for route in PAGES) + '</urlset>\n')
    gate(['ops/cloudflare/.generated/source', 'ops/cloudflare/.generated/site'])
    print(f'Company candidate: {len(PAGES)} pages, {len(copied)} assets; {SITE}')


if __name__ == '__main__':
    main()
