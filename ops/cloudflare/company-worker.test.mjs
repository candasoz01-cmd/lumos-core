// Local unit tests: ASSETS is a stub, not a deployed Cloudflare binding.
import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './company-worker.mjs';

function fixture({ indexable, status = 200, type = 'text/html', body = 'asset' } = {}) {
  const calls = [];
  const env = {
    INDEXABLE: indexable,
    ASSETS: { async fetch(request) {
      calls.push(request);
      return new Response(body, { status, headers: { 'Content-Type': type, 'Cache-Control': 'public, max-age=3600', ETag: 'asset-v1' } });
    } },
  };
  return { calls, run: (path, options, host = 'preview.workers.dev') => worker.fetch(new Request(`https://${host}${path}`, options), env) };
}

test('only exact app routes redirect to the fixed origin, preserving query', async () => {
  const f = fixture();
  for (const path of ['/panel', '/panel/', '/auth', '/auth/']) {
    for (const method of ['GET', 'HEAD']) {
      const response = await f.run(`${path}?q=hello%20world&next=https://evil.example`, { method });
      assert.equal(response.status, 302);
      assert.equal(response.headers.get('location'), `https://app.lumosai.company${path}?q=hello%20world&next=https://evil.example`);
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.equal(response.headers.get('x-robots-tag'), 'noindex, nofollow');
      assert.equal(await response.text(), '');
    }
  }
  assert.equal(f.calls.length, 0);
});

test('API, callback, similar prefixes and unknown routes stay with assets and preserve 404', async () => {
  const f = fixture({ status: 404, body: 'missing' });
  for (const path of ['/api', '/api/bridge/chat', '/auth/google/callback?code=sample', '/panelish', '/unknown']) {
    const response = await f.run(path);
    assert.equal(response.status, 404);
    assert.equal(response.headers.get('location'), null);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.equal(await response.text(), 'missing');
    assert.equal(new URL(f.calls.at(-1).url).hostname, 'preview.workers.dev');
  }
  assert.equal(f.calls.length, 5);
});

test('unsupported methods never reach assets or redirect', async () => {
  const f = fixture();
  for (const method of ['POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']) {
    for (const path of ['/', '/panel', '/auth', '/api/bridge/chat', '/robots.txt']) {
      const response = await f.run(path, { method });
      assert.equal(response.status, 405);
      assert.equal(response.headers.get('allow'), 'GET, HEAD');
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.equal(response.headers.get('x-robots-tag'), 'noindex, nofollow');
    }
  }
  assert.equal(f.calls.length, 0);
});

test('indexing requires both explicit string flag and exact production hostname', async () => {
  for (const indexable of [undefined, false, true, 'false', 'true']) {
    for (const host of ['preview.workers.dev', 'www.lumosai.company', 'lumosai.company.evil.example', 'lumosai.company']) {
      const f = fixture({ indexable });
      const enabled = indexable === 'true' && host === 'lumosai.company';
      const response = await f.run('/', undefined, host);
      assert.equal(response.headers.get('x-robots-tag'), enabled ? null : 'noindex, nofollow');
      const robots = await f.run('/robots.txt', undefined, host);
      assert.equal(robots.headers.get('cache-control'), 'no-store');
      assert.equal(await robots.text(), enabled
        ? 'User-agent: *\nAllow: /\nDisallow: /panel\nDisallow: /auth\nDisallow: /api\n\nSitemap: https://lumosai.company/sitemap.xml\n'
        : 'User-agent: *\nDisallow: /\n');
    }
  }
});

test('security headers cover assets, robots, redirects and errors', async () => {
  for (const [path, options] of [['/'], ['/robots.txt'], ['/panel'], ['/', { method: 'POST' }]]) {
    const response = await fixture().run(path, options);
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
    assert.equal(response.headers.get('x-frame-options'), 'DENY');
    assert.equal(response.headers.get('referrer-policy'), 'strict-origin-when-cross-origin');
  }
});

test('asset headers and body survive; HTML is no-store; HEAD has no body', async () => {
  for (const type of ['text/html; charset=utf-8', 'image/svg+xml']) {
    const f = fixture({ type });
    const response = await f.run('/asset');
    assert.equal(response.headers.get('content-type'), type);
    assert.equal(response.headers.get('etag'), 'asset-v1');
    assert.equal(response.headers.get('cache-control'), type.startsWith('text/html') ? 'no-store' : 'public, max-age=3600');
    assert.equal(await response.text(), 'asset');
    const head = await f.run('/asset', { method: 'HEAD' });
    assert.equal(await head.text(), '');
    assert.equal(f.calls.at(-1).method, 'HEAD');
  }
  assert.equal(await (await fixture().run('/robots.txt', { method: 'HEAD' })).text(), '');
});
