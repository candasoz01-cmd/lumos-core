/**
 * Feed → post kartı bağlama referansı (kopyala-yapıştır).
 * Derleme hedefi yok; ürün ekranına taşırken bu akışı kullanın.
 *
 * Kaynak: GET /posts/feed?limit=50 (veya kronoloji için GET /posts)
 * Sözleşme: docs/kando-post-feed-contract.md
 */

import KandoPostCard, { pickPostCardProps } from "./kando-post-card.jsx";

/** @param {{ posts: Array<{ id: string } & Record<string, unknown>> }} props */
export function FeedPostListExample({ posts }) {
  return (
    <>
      {posts.map((post) => (
        <KandoPostCard key={post.id} {...pickPostCardProps(post)} />
      ))}
    </>
  );
}

/*
 * --- Fetch örneği ---
 * const base = "http://127.0.0.1:3000";
 * const res = await fetch(`${base}/posts/feed?limit=50`);
 * const posts = await res.json();
 * // posts.forEach(...) veya <FeedPostListExample posts={posts} />
 */
