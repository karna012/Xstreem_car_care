import asyncio
import os
import textwrap

import httpx
from dotenv import load_dotenv

load_dotenv()

with open("business_info.txt", "r", encoding="utf-8") as f:
    BUSINESS_INFO = f.read()

BUSINESS_LINES = BUSINESS_INFO.splitlines()
CORE_CONTEXT = "\n".join(BUSINESS_LINES[:50])

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
OLLAMA_KEEPALIVE = os.getenv("OLLAMA_KEEPALIVE", "30m").strip()
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "18"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "140"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


def _ollama_base_url() -> str:
    host = OLLAMA_HOST or "http://127.0.0.1:11434"
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host.rstrip("/")


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client and not _client.is_closed:
        return _client

    async with _client_lock:
        if not _client or _client.is_closed:
            _client = httpx.AsyncClient(
                base_url=_ollama_base_url(),
                timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=3.0),
            )
        return _client


def _build_prompt(question: str) -> str:
    context = _relevant_business_info(question)
    return textwrap.dedent(
        f"""
        You are Xtreem Car Care's customer assistant.
        Answer only from the business information below.
        Keep replies short, friendly, and under 80 words.
        If the answer is unavailable, reply exactly:
        Please contact our executive at +91 8197180012 for more details.

        BUSINESS INFORMATION:
        {context}

        Customer: {question}
        Assistant:
        """
    ).strip()


def _relevant_business_info(question: str) -> str:
    question_lower = question.lower()
    keyword_groups = {
        ("service", "price", "cost", "wash", "clean", "foam", "interior", "wax", "deep", "bike", "car"): (77, 107),
        ("book", "appointment", "slot", "reserve", "schedule"): (30, 50),
        ("location", "address", "map", "where", "directions"): (39, 49),
        ("hour", "open", "close", "time", "timing", "sunday"): (39, 50),
        ("pickup", "drop", "collect", "delivery"): (171, 188),
        ("payment", "pay", "upi", "cash", "gpay", "google pay", "phonepe", "paytm"): (77, 82),
        ("offer", "discount", "membership", "package", "plan", "silver", "gold", "platinum"): (190, 205),
        ("complaint", "refund", "damage", "bad", "terrible", "unhappy", "disappointed", "angry"): (109, 132),
        ("staff", "quality", "equipment", "product", "3m", "brand"): (51, 74),
        ("scratch", "engine", "warranty", "guarantee", "reschedule", "cancel", "luxury", "suv"): (208, 221),
    }

    sections = [CORE_CONTEXT]
    for keywords, (start, end) in keyword_groups.items():
        if any(keyword in question_lower for keyword in keywords):
            sections.append("\n".join(BUSINESS_LINES[start - 1:end]))

    if len(sections) == 1:
        sections.append("\n".join(BUSINESS_LINES[84:107]))
        sections.append("\n".join(BUSINESS_LINES[157:168]))
        sections.append("\n".join(BUSINESS_LINES[190:205]))

    return "\n\n".join(dict.fromkeys(sections))


async def ask_ai(question: str) -> str:
    question = question.strip()
    if not question:
        return "Please contact our executive at +91 8197180012 for more details."

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _build_prompt(question),
        "stream": False,
        "keep_alive": OLLAMA_KEEPALIVE,
        "options": {
            "temperature": 0.2,
            "top_p": 0.85,
            "num_predict": OLLAMA_NUM_PREDICT,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }

    try:
        client = await _get_client()
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Start Ollama and make sure it is running on "
            f"{_ollama_base_url()}."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError("Ollama took too long to respond.") from exc
    except httpx.HTTPStatusError as exc:
        error_msg = exc.response.text.strip() or "Ollama returned an error."
        raise RuntimeError(error_msg) from exc

    answer = (response.json().get("response") or "").strip()
    return answer or "Please contact our executive at +91 8197180012 for more details."


async def warm_up_ollama() -> None:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "Reply with OK.",
        "stream": False,
        "keep_alive": OLLAMA_KEEPALIVE,
        "options": {"num_predict": 2},
    }
    client = await _get_client()
    await client.post("/api/generate", json=payload)


async def close_ollama_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None
