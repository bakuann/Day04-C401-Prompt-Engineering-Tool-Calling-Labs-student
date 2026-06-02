"""Research Agent — Live Trace UI (Streamlit).

UI đơn giản một trang: nhập yêu cầu, xem agent làm việc TỪNG BƯỚC theo thời gian thực:
  🧠 suy nghĩ & chọn tool  →  🔧 gọi tool (kèm args)  →  📦 kết quả tool  →  ✅ trả lời.

Chạy:  cd starter_v0 && streamlit run app.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import streamlit as st

from chat import assistant_tool_message, execute_tool_call, tool_results_message, trim_history
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
load_lab_env(ROOT)

PROVIDERS = ["openai", "openrouter", "anthropic", "gemini"]
TOOL_ICONS = {
    "lookup": "🔍", "fetch": "🌐", "timeline": "📘", "social_search": "🐦",
    "clarify": "❓", "format": "📋", "send": "📤", "papers": "📚",
    "paper_text": "📄", "policy": "🏢", "keywords": "🏷️",
}

st.set_page_config(page_title="Agent Live Trace", page_icon="🛰️", layout="centered")
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.5rem; max-width: 820px; }
      .step { border-left: 3px solid #cbd5e1; padding: .15rem 0 .6rem 1rem;
              margin-left: .35rem; position: relative; }
      .step::before { content:''; position:absolute; left:-7px; top:.25rem;
              width:11px; height:11px; border-radius:50%; background:#fff; border:3px solid #94a3b8; }
      .step.think::before { border-color:#6366f1; }
      .step.tool::before  { border-color:#06b6d4; }
      .step.done::before  { border-color:#16a34a; background:#16a34a; }
      .step .h { font-weight:600; font-size:.92rem; }
      .step .t { color:#94a3b8; font-size:.72rem; margin-left:.4rem; font-weight:400; }
      .args { background:#0f172a; color:#cbd5e1; border-radius:8px; padding:.4rem .6rem;
              font-family:ui-monospace,Menlo,monospace; font-size:.78rem; margin-top:.25rem; }
      .args code { color:#5eead4; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_provider(name: str):
    return make_provider(name)


@st.cache_data(show_spinner=False)
def load_tools(path: str, mtime: float):
    decls = load_tool_declarations(Path(path))
    return decls, to_openai_tools(decls)


# ----------------------------- Sidebar -----------------------------
with st.sidebar:
    st.header("⚙️ Cấu hình")
    provider_name = st.selectbox("Provider", PROVIDERS, index=0)
    version = st.selectbox("Version", ["v0", "v1", "v2", "v3"], index=3)
    model_override = st.text_input("Model (trống = mặc định)", value="")
    provider = get_provider(provider_name)
    model = model_override.strip() or getattr(provider, "default_model", None)
    av = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    st.caption(f"`{av.artifact_version}`")
    st.caption(f"Model: `{model}`")
    if st.button("🗑️ Xoá hội thoại", use_container_width=True):
        st.session_state.pop("turns", None)
        st.session_state.pop("history", None)
        st.rerun()

system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
declarations, openai_tools = load_tools(str(TOOLS_PATH), TOOLS_PATH.stat().st_mtime)

st.title("🛰️ Research Agent — Live Trace")
st.caption("Nhập yêu cầu, xem agent làm việc từng bước theo thời gian thực.")


# ----------------------------- Step rendering -----------------------------
def step_think(round_no: int, elapsed: float | None = None):
    t = f"<span class='t'>{elapsed:.1f}s</span>" if elapsed is not None else ""
    st.markdown(f"<div class='step think'><span class='h'>🧠 Bước {round_no} · Suy nghĩ & chọn tool</span>{t}</div>",
                unsafe_allow_html=True)


def step_tool(name: str, args: dict, result: dict | None, elapsed: float | None = None):
    icon = TOOL_ICONS.get(name, "🔧")
    args_str = ", ".join(f"{k}=<code>{json.dumps(v, ensure_ascii=False)}</code>" for k, v in args.items()) or "—"
    t = f"<span class='t'>{elapsed:.1f}s</span>" if elapsed is not None else ""
    st.markdown(
        f"<div class='step tool'><span class='h'>{icon} Gọi tool <code>{name}</code></span>{t}"
        f"<div class='args'>{args_str}</div></div>",
        unsafe_allow_html=True,
    )
    if result is None:
        return
    if isinstance(result, dict) and result.get("awaiting_user"):
        st.info(f"⏸ Tool dừng để hỏi user: {result.get('question', '')}")
    elif isinstance(result, dict) and result.get("error"):
        st.error(f"❌ {result.get('error')} — {result.get('message', '')}")
    else:
        n = len(result.get("items", [])) if isinstance(result, dict) else 0
        with st.expander(f"📦 Kết quả tool" + (f" · {n} item" if n else ""), expanded=False):
            st.json(result)


def render_steps(steps: list[dict]):
    """Render lại các bước đã lưu (cho lịch sử, không có spinner)."""
    for s in steps:
        if s["kind"] == "think":
            step_think(s["round"], s.get("elapsed"))
        elif s["kind"] == "tool":
            step_tool(s["name"], s["args"], s.get("result"), s.get("elapsed"))


# ----------------------------- Agent runner (streaming) -----------------------------
def run_agent_live(history, user_text, max_rounds=4):
    """Chạy agent, yield event để render real-time. Theo semantics chat.py (per-round)."""
    working = [
        {"role": "system", "content": system_prompt},
        *trim_history(history, 5),
        {"role": "user", "content": user_text},
    ]
    for i in range(1, max_rounds + 1):
        t0 = time.perf_counter()
        yield {"type": "think", "round": i}
        resp = provider.complete(working, openai_tools, model=model, temperature=0.0)
        calls = resp.tool_calls
        yield {"type": "think_done", "round": i, "elapsed": time.perf_counter() - t0}
        if not calls:
            yield {"type": "answer", "text": resp.text or "", "status": "answered"}
            return
        working.append(assistant_tool_message(resp.text, calls))
        non_clar: list[dict[str, Any]] = []
        for c in calls:
            tt = time.perf_counter()
            ev = execute_tool_call(c)
            res = ev.get("result", {})
            yield {"type": "tool", "name": c.name, "args": c.args, "result": res,
                   "elapsed": time.perf_counter() - tt}
            if isinstance(res, dict) and res.get("awaiting_user"):
                q = res.get("question") or c.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                yield {"type": "answer", "text": q, "status": "waiting_for_user"}
                return
            non_clar.append(ev)
        working.append(tool_results_message(non_clar))
    yield {"type": "answer", "text": "Đã dừng sau số vòng tool tối đa.", "status": "max_rounds"}


# ----------------------------- Render history -----------------------------
if "turns" not in st.session_state:
    st.session_state.turns = []     # [{user, steps, answer, status}]
    st.session_state.history = []   # messages cho model

for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        render_steps(turn["steps"])
        icon = {"waiting_for_user": "❓", "answered": "✅", "max_rounds": "⚠️"}.get(turn["status"], "✅")
        st.markdown(f"<div class='step done'><span class='h'>{icon} Trả lời</span></div>", unsafe_allow_html=True)
        st.markdown(turn["answer"])


# ----------------------------- New turn -----------------------------
if prompt := st.chat_input("Nhập yêu cầu nghiên cứu…"):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        steps: list[dict] = []
        answer, status = "", "answered"
        # KHÔNG dùng st.status ở đây: st.status là expander, mà step_tool mở expander
        # cho kết quả tool -> sẽ bị "expander lồng expander". Dùng st.spinner + container.
        steps_box = st.container()
        try:
            with st.spinner("🚀 Agent đang xử lý…"):
                for ev in run_agent_live(st.session_state.history, prompt):
                    if ev["type"] == "think":
                        with steps_box:
                            step_think(ev["round"])
                    elif ev["type"] == "think_done":
                        steps.append({"kind": "think", "round": ev["round"], "elapsed": ev["elapsed"]})
                    elif ev["type"] == "tool":
                        with steps_box:
                            step_tool(ev["name"], ev["args"], ev["result"], ev["elapsed"])
                        steps.append({"kind": "tool", "name": ev["name"], "args": ev["args"],
                                      "result": ev["result"], "elapsed": ev["elapsed"]})
                    elif ev["type"] == "answer":
                        answer, status = ev["text"], ev["status"]
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
            answer, status = f"Lỗi: {exc}", "error"

        icon = {"waiting_for_user": "❓", "answered": "✅", "max_rounds": "⚠️", "error": "❌"}.get(status, "✅")
        st.markdown(f"<div class='step done'><span class='h'>{icon} Trả lời</span></div>", unsafe_allow_html=True)
        st.markdown(answer)

    st.session_state.turns.append({"user": prompt, "steps": steps, "answer": answer, "status": status})
    st.session_state.history.append({"role": "user", "content": prompt})
    st.session_state.history.append({"role": "assistant", "content": answer})
