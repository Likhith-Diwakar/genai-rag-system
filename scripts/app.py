import sys
import os

# ----------------------------------------------------------
# FIX PYTHON PATH (so 'src' can be imported correctly)
# ----------------------------------------------------------

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import streamlit as st
from src.llm.rag import generate_answer


# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------

st.set_page_config(page_title="Google Drive RAG Chatbot", layout="wide")

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")


# ----------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ----------------------------------------------------------
# DISPLAY CHAT HISTORY
# ----------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if (
            msg["role"] == "assistant"
            and msg.get("sources")
            and msg["content"].strip()
            != "I do not know based on the provided documents."
        ):
            with st.expander("Sources used"):
                for s in msg["sources"]:

                    file_id = s.get("file_id")
                    file_name = s.get("file_name")

                    if file_id:
                        url = f"https://drive.google.com/file/d/{file_id}/view"
                        st.markdown(f"- 🔗 [{file_name}]({url})")
                    else:
                        st.markdown(f"- {file_name}")


# ----------------------------------------------------------
# CHAT INPUT
# ----------------------------------------------------------

query = st.chat_input("Ask something about your documents...")

if query:

    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):

            answer, sources = generate_answer(query)

            st.markdown(answer)

            if (
                answer.strip()
                != "I do not know based on the provided documents."
                and sources
            ):
                with st.expander("Sources used"):
                    for s in sources:

                        file_id = s.get("file_id")
                        file_name = s.get("file_name")

                        if file_id:
                            url = f"https://drive.google.com/file/d/{file_id}/view"
                            st.markdown(f"- 🔗 [{file_name}]({url})")
                        else:
                            st.markdown(f"- {file_name}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )