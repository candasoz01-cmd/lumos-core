/**
 * Feed → post kartı bağlama referansı (kopyala-yapıştır).
 * Derleme hedefi yok; ürün ekranına taşırken bu akışı kullanın.
 *
 * Kaynak: GET /posts/feed?limit=50 (veya kronoloji için GET /posts)
 * Sözleşme: docs/kando-post-feed-contract.md
 */

import KandoPostCard, { pickPostCardProps } from "./kando-post-card.jsx";

/**
 * GET /posts veya /posts/feed öğesi (serializePost); feed’de ek: feedScore.
 * Kart: KandoPostCard + spread pickPostCardProps(post)
 */
export const examplePostFromBackend = {
  id: "clexample01post",
  content: "Örnek gönderi metni.",
  createdAt: "2025-03-18T10:00:00.000Z",
  userId: "cluser01",
  user: { username: "ornek_kullanici" },
  deletedAt: null,
  ratingCount: 3,
  ratingAvg: 4.3,
  lowRatingCount: 0,
  highRatingCount: 2,
};

/** @param {{ posts: ReadonlyArray<{ id: string } & Record<string, unknown>> }} props */
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
 * Tek kart (örnek nesne):
 *   <KandoPostCard {...pickPostCardProps(examplePostFromBackend)} />
 *
 * Fetch:
 *   const res = await fetch(`${base}/posts`); // veya /posts/feed?limit=50
 *   const posts = await res.json();
 *   <FeedPostListExample posts={posts} />
 */
