"""Affichage conversationnel professionnel - bulles TOP-JURIDIQUE."""

from __future__ import annotations

import html
import re

import streamlit as st

ASSISTANT_AVATAR = "⚖️"
USER_AVATAR = "👤"
ASSISTANT_NAME = "Copilote juridique"
USER_NAME = "Vous"


def _md_to_html(text: str) -> str:
    """Conversion legere du Markdown du chatbot vers du HTML securise."""
    text = html.escape(text or "")
    out: list[str] = []

    def inline(line: str) -> str:
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", line)
        return line

    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.strip() == "---":
                out.append("<hr>")
                i += 1
            elif ln.startswith("&gt;"):
                group = []
                while i < len(lines) and lines[i].startswith("&gt;"):
                    stripped = lines[i][4:].strip()
                    if stripped:
                        group.append(stripped)
                    i += 1
                inner = "".join(f"<div>{inline(g)}</div>" for g in group)
                out.append(f"<blockquote>{inner}</blockquote>")
            else:
                out.append(f"<div>{inline(ln)}</div>")
                i += 1
    return "".join(out)


def _bubble(role: str, content_html: str, timestamp: str) -> str:
    if role == "assistant":
        return f"""
        <div class="tj-chat-row">
            <div class="tj-avatar assistant">{ASSISTANT_AVATAR}</div>
            <div class="tj-bubble assistant">
                <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
                color:#B8956A;margin-bottom:0.3rem;">{ASSISTANT_NAME}</div>
                {content_html}
                <div class="tj-time">{html.escape(timestamp)}</div>
            </div>
        </div>
        """
    return f"""
    <div class="tj-chat-row user">
        <div class="tj-bubble user">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
            opacity:0.75;margin-bottom:0.3rem;">{USER_NAME}</div>
            <div>{content_html}</div>
            <div class="tj-time">{html.escape(timestamp)}</div>
        </div>
        <div class="tj-avatar user">{USER_AVATAR}</div>
    </div>
    """


def render_chat_history(conversation_history: list[dict]):
    if not conversation_history:
        st.html(
            """
            <div class="tj-card" style="text-align:center;padding:2.2rem 1.5rem;">
                <div style="font-size:2rem;margin-bottom:0.4rem;">💬</div>
                <strong>Aucune question pour l'instant</strong>
                <p style="color:#5D6B82;font-size:0.9rem;margin:0.4rem 0 0 0;">
                Posez une question sur le contenu du document analysé ci-dessous.</p>
            </div>
            """
        )
        return

    for entry in conversation_history:
        question = _md_to_html(entry.get("question", ""))
        answer = _md_to_html(entry.get("answer", ""))
        timestamp = entry.get("timestamp", "")
        st.html(
            _bubble("user", question, timestamp) + _bubble("assistant", answer, timestamp)
        )
