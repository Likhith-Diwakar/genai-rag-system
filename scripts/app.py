import sys
import os

# ----------------------------------------------------------
# FIX PYTHON PATH (so 'src' can be imported correctly)
# ----------------------------------------------------------

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import streamlit as st

# ----------------------------------------------------------
# IMPORT BUSINESS LOGIC
# ----------------------------------------------------------

from src.llm.rag import generate_answer
from src.embedding.vector_store import VectorStore
from src.utils.logger import logger


# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------

st.set_page_config(
    page_title="Google Drive RAG Chatbot",
    layout="wide"
)

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")


# ----------------------------------------------------------
# INITIALIZE VECTOR STORE (QUERY ONLY)
# ----------------------------------------------------------

if "vector_store_initialized" not in st.session_state:

    try:

        vector_store = VectorStore()

        total_vectors = vector_store.count()

        logger.info(f"Vector store connected | total_vectors={total_vectors}")

        if total_vectors == 0:

            logger.warning(
                "Vector store is empty. Ensure ingestion pipeline has run."
            )

            st.warning(
                "Document index is empty. Run the ingestion pipeline to load documents."
            )

    except Exception as e:

        logger.error(f"Vector store initialization failed: {e}")

        st.error("Failed to connect to vector database.")

    st.session_state.vector_store_initialized = True


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

            try:

                answer, sources = generate_answer(query)

            except Exception as e:

                logger.error(f"RAG pipeline failed: {e}")

                answer = "An error occurred while processing your request."
                sources = []

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