"""Marketing pages stay on the product origin; application links stay explicit."""

import importlib.util
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "company_builder", ROOT / "ops/cloudflare/build_company.py"
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs)["href"])


def rewritten(*urls):
    html = "".join(f'<a href="{url}">Link</a>' for url in urls)
    parsed = Links()
    parsed.feed(BUILDER.prepare_html(html, "/"))
    return parsed.hrefs


def test_product_marketing_destinations_are_packaged_and_remain_local():
    paths = ("/slack", "/cyber", "/connect/mac")
    assert set(paths).issubset(BUILDER.PAGES)
    for route in paths:
        assert (ROOT / "ui/src/pages" / (route.lstrip("/") + ".astro")).is_file()
    urls = [path + "?from=footer#details" for path in paths]
    assert rewritten(*urls) == urls


def test_only_explicit_application_links_change_origin():
    app_paths = ("/auth?next=panel", "/panel#chat", "/integrations/github")
    assert rewritten(*app_paths) == [BUILDER.APP + path for path in app_paths]
    unchanged = ("/missing-page", "/panel-extra", "//example.org/panel", "https://welockai.com/", "#details")
    assert rewritten(*unchanged) == list(unchanged)
