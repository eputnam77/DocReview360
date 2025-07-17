# Performance Optimization Recommendations

The recent profiling runs (k6, Lighthouse, cProfile, py-spy and React Profiler) revealed several areas where DocReview360 can be optimized further. The table below captures actionable items.

## Safe to Try

### Recommendation: Cache search results via Redis
- Expected Impact: Moderate (reduces repeat query time)
- Effort: Low
- Breakage Risk: Low
- Dependencies: None
- Priority: P1 (quick win)
- ready-for:builder
- Status: implemented via ``cache_get``/``cache_set`` in
  ``docreview360.search.search``.

## Review Needed

### Recommendation: Add SQL indexes for frequent lookups
- Expected Impact: Moderate (better DB performance)
- Effort: Moderate
- Breakage Risk: Moderate
- Dependencies: Migration scripts
- Priority: P2
- ready-for:builder

### Recommendation: Enable GZipMiddleware in FastAPI
- Expected Impact: Low (smaller responses)
- Effort: Low
- Breakage Risk: Low
- Dependencies: None
- Priority: P2
- ready-for:builder
- Status: implemented via ``FastAPI.add_middleware`` in
  ``docreview360.api``.

### Recommendation: Use dynamic imports for editor packages
- Expected Impact: Moderate (smaller frontend bundle)
- Effort: Moderate
- Breakage Risk: Low
- Dependencies: Next.js build changes
- Priority: P2
- ready-for:builder

### Recommendation: Offload SharePoint sync to Celery workers
- Expected Impact: Moderate (frees API threads)
- Effort: Moderate
- Breakage Risk: Moderate
- Dependencies: Celery queue setup
- Priority: P3
- ready-for:builder

