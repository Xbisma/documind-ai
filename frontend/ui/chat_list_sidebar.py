# frontend/ui/chat_list_sidebar.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import streamlit as st


def _copy_button(label: str, value: str, key: str) -> None:
    # Streamlit doesn't have a perfect "copy on click" without JS.
    # Fast, reliable: show value in a code block + copy hint.
    with st.popover(label, use_container_width=False):
        st.code(value, language="text")
        st.caption("Select and copy (Ctrl+C / Cmd+C).")


def render_chatgpt_sidebar(
    *,
    chats: List[Dict[str, Any]],
    active_chat_id: Optional[str],
) -> Tuple[Optional[str], str]:
    """
    Returns (selected_chat_id, action)
    action in: {"none","new_chat","select_chat","delete_chat"}
    """

    with st.sidebar:
        st.markdown("## Chats")

        col1, col2 = st.columns(2)
        new_clicked = col1.button("New chat", type="primary", use_container_width=True)
        delete_active_clicked = col2.button("Delete chat", use_container_width=True, disabled=not bool(active_chat_id))

        st.divider()

        # small search filter
        q = st.text_input("Search chats", placeholder="Search…", label_visibility="collapsed")

        filtered = chats
        if q.strip():
            ql = q.strip().lower()
            filtered = [c for c in chats if (c.get("title") or "").lower().find(ql) >= 0]

        # scroll container via fixed-height block
        st.markdown(
            """
            <style>
              .chat-scroll {
                height: 520px;
                overflow-y: auto;
                padding-right: 6px;
              }
              .chat-row {
                border-radius: 10px;
                padding: 10px 10px;
                margin-bottom: 8px;
                border: 1px solid rgba(0,0,0,0.08);
                background: rgba(255,255,255,0.6);
              }
              .chat-row-active {
                border: 1px solid rgba(255,0,0,0.45);
                background: rgba(255,0,0,0.06);
              }
              .chat-title {
                font-weight: 650;
                font-size: 0.95rem;
                margin-bottom: 2px;
              }
              .chat-meta {
                color: rgba(0,0,0,0.55);
                font-size: 0.75rem;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)

        selected_chat_id = active_chat_id
        action = "none"

        if not filtered:
            st.caption("No chats yet.")
        else:
            for c in filtered:
                chat_id = c["chat_id"]
                title = c.get("title") or "Untitled chat"
                created_at = (c.get("created_at") or "")[:19].replace("T", " ")
                session_id = c.get("session_id") or ""

                active = (chat_id == active_chat_id)
                row_class = "chat-row chat-row-active" if active else "chat-row"

                st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)

                # main row click
                if st.button(f"{title}", key=f"open_{chat_id}", use_container_width=True):
                    selected_chat_id = chat_id
                    action = "select_chat"

                st.markdown(f'<div class="chat-meta">{created_at}</div>', unsafe_allow_html=True)

                cols = st.columns([1, 1, 1])
                with cols[0]:
                    if st.button("Delete", key=f"del_{chat_id}", use_container_width=True):
                        selected_chat_id = chat_id
                        action = "delete_chat"
                with cols[1]:
                    if session_id:
                        _copy_button("Session ID", session_id, key=f"copy_{chat_id}")
                    else:
                        st.button("Session ID", key=f"copy_disabled_{chat_id}", disabled=True, use_container_width=True)
                with cols[2]:
                    st.caption(f"{chat_id[:6]}…")

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if new_clicked:
            return selected_chat_id, "new_chat"

        if delete_active_clicked and active_chat_id:
            return active_chat_id, "delete_chat"

        return selected_chat_id, action