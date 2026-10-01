# Search Workflow

The app has a `Поиск` tab for web retrieval.

Endpoints:

- `POST /v1/search` - search query, returns results.
- `POST /v1/web/page` - fetch and clean selected page text.
- `POST /v1/web/ask` - answer a question using only selected page text.

The retrieval step uses ordinary HTTP requests. The answer step uses the local
configured text model.

Limitations:

- Search results depend on the reachable search HTML endpoint.
- Some pages block scraping or require JavaScript.
- The selected page text is truncated before being sent to the local model.
- For production, add source caching, robots policy handling, citations, and
  domain allow/deny controls.
