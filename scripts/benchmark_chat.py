import argparse
import json
import time
import urllib.request


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument(
        "--prompt",
        default="Напиши краткий production-план для ИИ-сервиса на открытых весах.",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    result = post_json(
        f"{args.url}/v1/bench/chat",
        {"prompt": args.prompt, "runs": args.runs, "max_tokens": args.max_tokens},
    )
    result["wall_seconds"] = round(time.perf_counter() - started, 4)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
