const APP_ROUTES = new Set(['/panel', '/panel/', '/auth', '/auth/']);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const indexable = env.INDEXABLE === 'true' && url.hostname === 'lumosai.company';
    let response;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      response = new Response('Method not allowed', { status: 405, headers: { Allow: 'GET, HEAD' } });
    } else if (APP_ROUTES.has(url.pathname)) {
      response = new Response(null, {
        status: 302,
        headers: { Location: `https://app.lumosai.company${url.pathname}${url.search}` },
      });
    } else if (url.pathname === '/robots.txt') {
      const body = indexable
        ? 'User-agent: *\nAllow: /\nDisallow: /panel\nDisallow: /auth\nDisallow: /api\n\nSitemap: https://lumosai.company/sitemap.xml\n'
        : 'User-agent: *\nDisallow: /\n';
      response = new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } });
    } else {
      response = await env.ASSETS.fetch(request);
    }
    const headers = new Headers(response.headers);
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    headers.set('X-Frame-Options', 'DENY');
    if (!indexable) headers.set('X-Robots-Tag', 'noindex, nofollow');
    if ((headers.get('Content-Type') || '').toLowerCase().includes('text/html') || response.status >= 300) {
      headers.set('Cache-Control', 'no-store');
    }
    return new Response(request.method === 'HEAD' ? null : response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
