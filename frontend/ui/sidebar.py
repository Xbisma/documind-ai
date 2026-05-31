from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import streamlit as st


def render_sidebar(
    *,
    chats: List[Dict[str, Any]],
    active_chat_id: Optional[str],
    active_session_id: Optional[str],
    docs_in_session: List[Dict[str, Any]],
) -> Tuple[Optional[str], str]:
    """
    Renders the sidebar and returns:
    - selected_chat_id (may be the same as active_chat_id)
    - action: one of {"none", "new_chat", "delete_chat", "switch_chat"}
    """

    with st.sidebar:
        st.header("Chats")

        col_a, col_b = st.columns(2)
        new_clicked = col_a.button("New chat", type="primary")
        delete_clicked = col_b.button(
            "Delete chat",
            disabled=not bool(active_chat_id)
        )

        st.divider()
        st.caption("Saved chats")

        selected_chat_id = active_chat_id

        if chats:
            options = {
                f"{c['title']} · {c['created_at']}": c["chat_id"]
                for c in chats
            }

            labels = list(options.keys())

            # preselect current chat
            index = 0
            if active_chat_id:
                for i, (_, cid) in enumerate(options.items()):
                    if cid == active_chat_id:
                        index = i
                        break

            chosen_label = st.selectbox("Open chat", labels, index=index)
            chosen_id = options[chosen_label]
            selected_chat_id = chosen_id

        else:
            st.info("No chats yet. Click New chat.")

        st.divider()
        st.header("Current Session")

        if active_session_id:
            st.code(active_session_id, language="text")
        else:
            st.warning(
                "No session_id yet. Upload PDFs in this chat to create one."
            )

        st.divider()
        st.header("Documents in this chat")

        if active_session_id:
            if docs_in_session:
                for d in docs_in_session:
                    st.write(f"- {d.get('doc_name')}")
            else:
                st.caption("No docs stored for this session yet.")
        else:
            st.caption("Upload PDFs to see documents list.")

        if new_clicked:
            return selected_chat_id, "new_chat"

        if delete_clicked:
            return selected_chat_id, "delete_chat"

        if selected_chat_id != active_chat_id:
            return selected_chat_id, "switch_chat"

        return selected_chat_id, "none"