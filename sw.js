// 아주 단순한 서비스 워커: 색칠놀이 그림(coloring/)은 한 번 받으면 절대 안 바뀌는
// 파일들이라 캐시 우선으로 저장해서 오프라인(자동차 안, 와이파이 없는 곳 등)에서도
// 색칠놀이를 쓸 수 있게 한다. index.html 등 앱 코드는 항상 최신을 우선 시도하고,
// 오프라인일 때만 마지막으로 받아둔 캐시를 보여준다(업데이트가 캐시에 막히지 않도록).
const CACHE_VERSION = 'v1';
const CACHE_NAME = 'kids-playground-' + CACHE_VERSION;

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

function isImmutableAsset(url) {
  return url.pathname.includes('/coloring/') || /\.(png|jpe?g)$/i.test(url.pathname);
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (isImmutableAsset(url)) {
    // 캐시 우선: 있으면 바로 쓰고, 없으면 받아서 캐시에 저장
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(req).then(
          (cached) =>
            cached ||
            fetch(req).then((res) => {
              if (res.ok) cache.put(req, res.clone());
              return res;
            })
        )
      )
    );
    return;
  }

  // 앱 코드(HTML/JS 등): 네트워크 우선, 실패하면(오프라인) 캐시로 대체
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
