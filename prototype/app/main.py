from pathlib import Path
from statistics import mean
from time import perf_counter
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.models import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStep,
    BenchmarkRequest,
    BenchmarkResponse,
    BenchmarkRun,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    SiteGenerationRequest,
    SiteGenerationResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    VideoGenerationRequest,
    VideoGenerationResponse,
    WebAskRequest,
    WebAskResponse,
    WebPageRequest,
    WebPageResponse,
)
from app.providers import get_image_provider, get_text_provider, get_video_provider

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
GENERATED_SITES_DIR = Path(settings.generated_sites_dir)
if not GENERATED_SITES_DIR.is_absolute():
    GENERATED_SITES_DIR = (APP_DIR.parent / GENERATED_SITES_DIR).resolve()
GENERATED_SITES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated-sites", StaticFiles(directory=GENERATED_SITES_DIR), name="generated-sites")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "text_backend": settings.text_backend,
        "text_model": settings.text_model,
        "image_backend": settings.image_backend,
        "image_model": settings.image_model,
        "video_backend": settings.video_backend,
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    prompt_chars = sum(len(message.content) for message in request.messages)
    if prompt_chars > settings.max_prompt_chars:
        raise HTTPException(status_code=413, detail="Prompt is too large")
    provider = get_text_provider()
    return await provider.complete(request)


@app.post("/v1/images/generations")
async def image_generations(request: ImageGenerationRequest) -> ImageGenerationResponse:
    provider = get_image_provider()
    return await provider.generate(request)


@app.post("/v1/videos/generations")
async def video_generations(request: VideoGenerationRequest) -> VideoGenerationResponse:
    provider = get_video_provider()
    return await provider.generate(request)


@app.post("/v1/bench/chat")
async def benchmark_chat(request: BenchmarkRequest) -> BenchmarkResponse:
    provider = get_text_provider()
    runs: list[BenchmarkRun] = []
    for index in range(request.runs):
        chat_request = ChatCompletionRequest(
            model=request.model,
            messages=[ChatMessage(role="user", content=request.prompt)],
            max_tokens=request.max_tokens,
        )
        started = perf_counter()
        response = await provider.complete(chat_request)
        latency = perf_counter() - started
        content = response.choices[0].message.content if response.choices else ""
        estimated_tokens = response.usage.get("completion_tokens") or max(1, len(content) // 4)
        runs.append(
            BenchmarkRun(
                run=index + 1,
                latency_seconds=round(latency, 4),
                output_chars=len(content),
                estimated_output_tokens=estimated_tokens,
                estimated_tokens_per_second=round(estimated_tokens / max(latency, 0.001), 2),
            )
        )
    return BenchmarkResponse(
        model=request.model,
        backend=settings.text_backend,
        runs=runs,
        average_latency_seconds=round(mean(run.latency_seconds for run in runs), 4),
        average_estimated_tokens_per_second=round(
            mean(run.estimated_tokens_per_second for run in runs), 2
        ),
    )


def detect_agent_mode(prompt: str, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    normalized = prompt.lower()
    image_markers = [
        "сгенерируй картин",
        "создай картин",
        "нарисуй",
        "изображени",
        "картинку",
        "картинка",
        "generate image",
        "create image",
        "draw ",
    ]
    bench_markers = ["замерь", "скорость", "benchmark", "bench"]
    if any(marker in normalized for marker in image_markers):
        return "image"
    if any(marker in normalized for marker in bench_markers):
        return "benchmark"
    return "chat"


def clean_image_prompt(prompt: str) -> str:
    replacements = [
        "сгенерируй картинку",
        "сгенерируй изображение",
        "создай картинку",
        "создай изображение",
        "нарисуй",
    ]
    cleaned = prompt.strip()
    lowered = cleaned.lower()
    for prefix in replacements:
        if lowered.startswith(prefix):
            return cleaned[len(prefix) :].strip() or cleaned
    return cleaned


@app.post("/v1/agent/runs")
async def agent_run(request: AgentRunRequest) -> AgentRunResponse:
    prompt = request.input.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Task input is empty")

    mode = detect_agent_mode(prompt, request.mode)
    steps = [
        AgentStep(title="Принял задачу", detail=prompt),
        AgentStep(title="Выбрал режим", detail=mode),
    ]

    try:
        if mode == "image":
            steps.append(AgentStep(title="Подготовил image prompt", detail=clean_image_prompt(prompt)))
            provider = get_image_provider()
            result = await provider.generate(
                ImageGenerationRequest(
                    prompt=clean_image_prompt(prompt),
                    size="512x512",
                    steps=30,
                    guidance_scale=8,
                )
            )
            artifacts = result.data
            steps.append(AgentStep(title="Сгенерировал изображение", detail=result.status))
            return AgentRunResponse(
                mode="image",
                status="completed",
                steps=steps,
                message="Изображение готово.",
                artifacts=artifacts,
            )

        if mode == "benchmark":
            bench = await benchmark_chat(BenchmarkRequest(prompt=prompt, runs=1, max_tokens=128))
            steps.append(AgentStep(title="Замерил скорость", detail=f"{bench.average_estimated_tokens_per_second} tok/s"))
            return AgentRunResponse(
                mode="benchmark",
                status="completed",
                steps=steps,
                message="Benchmark завершен.",
                artifacts=[{"kind": "benchmark", "json": bench.model_dump_json()}],
                metrics={
                    "latency_seconds": bench.average_latency_seconds,
                    "estimated_tokens_per_second": bench.average_estimated_tokens_per_second,
                },
            )

        provider = get_text_provider()
        completion = await provider.complete(
            ChatCompletionRequest(
                model="local-default",
                messages=[ChatMessage(role="user", content=prompt)],
                max_tokens=1024,
            )
        )
        answer = completion.choices[0].message.content if completion.choices else ""
        steps.append(AgentStep(title="Получил ответ модели", detail=settings.text_model))
        return AgentRunResponse(
            mode="chat",
            status="completed",
            steps=steps,
            message=answer,
            metrics=completion.metrics,
        )
    except Exception as exc:
        steps.append(AgentStep(title="Ошибка выполнения", detail=str(exc), status="failed"))
        return AgentRunResponse(mode=mode, status="failed", steps=steps, message=str(exc))


def slugify_site_name(name: str) -> str:
    allowed = []
    for char in name.lower().strip():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_"}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "local-site"


def site_copy(prompt: str) -> dict[str, str]:
    lower = prompt.lower()
    if "ресторан" in lower or "кафе" in lower or "кофей" in lower or "coffee" in lower:
        return {
            "title": "Doha Coffee Room",
            "subtitle": "Спешелти-кофе, спокойная роскошь и посадка, где хочется задержаться.",
            "cta": "Забронировать",
            "section": "Меню и атмосфера",
        }
    if "портфолио" in lower:
        return {
            "title": "Selected Work",
            "subtitle": "Портфолио с сильной подачей, кейсами и аккуратной структурой.",
            "cta": "Смотреть кейсы",
            "section": "Ключевые проекты",
        }
    if "магазин" in lower or "товар" in lower:
        return {
            "title": "Modern Storefront",
            "subtitle": "Чистая витрина продукта с быстрым сравнением и уверенным checkout-намерением.",
            "cta": "Открыть каталог",
            "section": "Подборка",
        }
    return {
        "title": "Local Launch",
        "subtitle": prompt[:160] or "Локальный сайт, созданный агентом.",
        "cta": "Начать",
        "section": "Что внутри",
    }


@app.post("/v1/sites/generate")
async def generate_site(request: SiteGenerationRequest) -> SiteGenerationResponse:
    slug = slugify_site_name(request.name)
    site_dir = GENERATED_SITES_DIR / slug
    site_dir.mkdir(parents=True, exist_ok=True)
    copy = site_copy(request.prompt)
    html = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{copy["title"]}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main>
      <section class="hero">
        <nav><strong>{copy["title"]}</strong><a href="#content">{copy["cta"]}</a></nav>
        <div class="hero-grid">
          <div>
            <p class="kicker">Сгенерировано локальным агентом</p>
            <h1>{copy["title"]}</h1>
            <p class="lead">{copy["subtitle"]}</p>
            <a class="button" href="#content">{copy["cta"]}</a>
          </div>
          <div class="visual" aria-label="Абстрактная визуальная композиция"></div>
        </div>
      </section>
      <section id="content" class="content">
        <h2>{copy["section"]}</h2>
        <div class="cards">
          <article><span>01</span><h3>Структура</h3><p>Первый экран сразу объясняет предложение и ведет к действию.</p></article>
          <article><span>02</span><h3>Стиль</h3><p>Спокойная палитра, плотная типографика и адаптивная сетка.</p></article>
          <article><span>03</span><h3>Рост</h3><p>Сайт можно расширять секциями, формами и интеграциями.</p></article>
        </div>
      </section>
    </main>
  </body>
</html>
"""
    css = """:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#142024;background:#eef1ed}body{margin:0}main{min-height:100vh}.hero{min-height:88vh;padding:28px clamp(18px,5vw,72px);background:linear-gradient(135deg,#f8faf8,#dfe9e4)}nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:8vh}nav a,.button{color:white;background:#145347;text-decoration:none;border-radius:8px;padding:12px 18px;display:inline-block}.hero-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,42vw);gap:48px;align-items:center}h1{font-size:clamp(52px,8vw,120px);line-height:.9;margin:0 0 24px;letter-spacing:-.035em}.lead{font-size:clamp(20px,2.4vw,34px);line-height:1.2;max-width:820px;color:#4c5b57}.kicker{text-transform:uppercase;letter-spacing:.14em;color:#6b766f;font-size:13px}.visual{aspect-ratio:4/5;border-radius:18px;background:radial-gradient(circle at 30% 20%,#d6a15b,transparent 28%),radial-gradient(circle at 70% 45%,#145347,transparent 30%),linear-gradient(160deg,#f5eadb,#7f9c91);box-shadow:0 28px 80px rgba(20,32,36,.22)}.content{padding:72px clamp(18px,5vw,72px)}h2{font-size:clamp(32px,4vw,64px);margin:0 0 28px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.cards article{background:white;border:1px solid #cbd6d0;border-radius:12px;padding:24px}.cards span{color:#9b7448;font-weight:800}h3{font-size:24px;margin:18px 0 10px}.cards p{color:#5d6a64;line-height:1.5}@media(max-width:820px){.hero-grid,.cards{grid-template-columns:1fr}.visual{min-height:360px}}"""
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    (site_dir / "styles.css").write_text(css, encoding="utf-8")
    return SiteGenerationResponse(
        id=slug,
        path=str(site_dir),
        url=f"/generated-sites/{slug}/index.html",
        files=["index.html", "styles.css"],
    )


def normalize_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        values = parse_qs(parsed.query).get("uddg")
        if values:
            return values[0]
    return url


def clean_page_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 2]
    deduped: list[str] = []
    seen = set()
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)
    return title, "\n".join(deduped)[:24000]


@app.post("/v1/search")
async def web_search(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query is empty")
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"user-agent": "LocalAIAgent/0.1 (+local user search)"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[SearchResult] = []
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        if not link:
            continue
        href = link.get("href") or ""
        title = link.get_text(" ", strip=True)
        snippet_node = result.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        clean_url = normalize_duckduckgo_url(href)
        if title and clean_url.startswith(("http://", "https://")):
            results.append(SearchResult(title=title, url=clean_url, snippet=snippet))
        if len(results) >= request.max_results:
            break
    return SearchResponse(query=query, results=results)


@app.post("/v1/web/page")
async def read_web_page(request: WebPageRequest) -> WebPageResponse:
    url = request.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported")
    headers = {"user-agent": "LocalAIAgent/0.1 (+local user page reader)"}
    async with httpx.AsyncClient(timeout=45, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
    title, text = clean_page_text(response.text)
    return WebPageResponse(url=str(response.url), title=title or url, text=text)


@app.post("/v1/web/ask")
async def ask_web_page(request: WebAskRequest) -> WebAskResponse:
    question = request.question.strip()
    page_text = request.page_text.strip()[:18000]
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty")
    if not page_text:
        raise HTTPException(status_code=400, detail="Page text is empty")
    prompt = (
        "Ты отвечаешь только по тексту выбранного сайта. "
        "Если ответа нет в тексте, скажи, что на странице недостаточно данных.\n\n"
        f"URL: {request.url}\n"
        f"TITLE: {request.title}\n\n"
        f"PAGE TEXT:\n{page_text}\n\n"
        f"QUESTION:\n{question}"
    )
    provider = get_text_provider()
    completion = await provider.complete(
        ChatCompletionRequest(
            model="local-default",
            messages=[ChatMessage(role="user", content=prompt)],
            max_tokens=900,
        )
    )
    answer = completion.choices[0].message.content if completion.choices else ""
    return WebAskResponse(answer=answer, metrics=completion.metrics)
