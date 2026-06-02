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

       
        # chat list container with scroll
        list_container = st.container(height=520)

        selected_chat_id = active_chat_id
        action = "none"

        with list_container:
            if not filtered:
                st.caption("No chats yet.")
            else:
                for c in filtered:
                    chat_id = c["chat_id"]
                    title = c.get("title") or "Untitled chat"
                    created_at = (c.get("created_at") or "")[:19].replace("T", " ")
                    session_id = c.get("session_id") or ""

                    active = (chat_id == active_chat_id)

                    # Row style
                    border = "2px solid rgba(255,0,0,0.35)" if active else "1px solid rgba(0,0,0,0.08)"
                    bg = "rgba(255,0,0,0.06)" if active else "rgba(255,255,255,0.6)"

                    st.markdown(
                        f"""
                        <div style="border:{border}; background:{bg}; border-radius:10px; padding:10px; margin-bottom:8px;">
                        <div style="font-weight:650;">{title}</div>
                        <div style="color:rgba(0,0,0,0.55); font-size:0.75rem;">{created_at}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    colA, colB, colC = st.columns([6, 2, 2])

                    with colA:
                        if st.button("Open", key=f"open_{chat_id}", use_container_width=True):
                            selected_chat_id = chat_id
                            action = "select_chat"

                    with colB:
                        if st.button("🗑️", key=f"del_{chat_id}", help="Delete chat", use_container_width=True):
                            selected_chat_id = chat_id
                            action = "delete_chat"

                    with colC:
                        if session_id:
                            _copy_button("ID", session_id, key=f"copy_{chat_id}")
                        else:
                            st.button("ID", key=f"copy_disabled_{chat_id}", disabled=True, use_container_width=True)

        if new_clicked:
            return selected_chat_id, "new_chat"

        if delete_active_clicked and active_chat_id:
            return active_chat_id, "delete_chat"

        return selected_chat_id, action