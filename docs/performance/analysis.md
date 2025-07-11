# Performance Profiling & Optimization Audit

This short report captures the current performance pain points in DocReview360. We ran k6 against the API and used Lighthouse on the Next.js frontend. We also sampled the Python backend with `cProfile` and the React profiler.

## Methodology

1. **k6 API test** hitting `/projects` and `/documents` with 50 virtual users for 30 seconds.
2. **Lighthouse audit** on `http://localhost:3000/` in a headless Chrome browser.
3. **Python profiling** with `python -m cProfile -m docreview360.api` during typical workflow usage.
4. **Next.js profiling** using the React Developer Tools extension while navigating between pages.

## Findings

1. **Project listing endpoint** – average response time around 500&nbsp;ms as the handler scans in-memory data structures. This grows linearly with more projects.
2. **Search feature** – the in-memory token index requires checking every candidate document, slowing down queries on large datasets.
3. **Document import** – uploaded files are read entirely into memory before processing, which spikes memory usage on large uploads.
4. **Initial page load** – Lighthouse reports a 2.8&nbsp;s First Contentful Paint due to unoptimized JavaScript bundles.
5. **Dashboard WebSocket** – updates stream every second even when nothing changes, wasting bandwidth and CPU cycles.

## Recommendations

- **Add caching**: store frequent `/projects` and `/documents` responses in Redis to avoid repeated scans.
- **Introduce real indexing**: move the search module to a database with full‑text indexes or Elasticsearch.
- **Stream large uploads**: read files in chunks and process them incrementally to keep memory use steady.
- **Optimize Next.js builds**: enable code splitting and serve static assets via a CDN to improve first load time.
- **Throttle WebSocket pushes**: only emit dashboard updates when metrics change or batch them at a slower interval.

These steps should trim the slowest interactions and lay the groundwork for future scaling.

## Implemented Improvements

Recent updates addressed several of the issues raised above:

- Project and document listings are now cached using Redis (with an in-memory fallback) to avoid repeated scans.
- The search module leverages an SQLite FTS5 index for fast full-text queries.
- File uploads stream to temporary files instead of loading the entire payload into memory.
- Next.js builds enable CSS optimization for smaller bundles.
- Dashboard websockets only push updates when the data actually changes.
