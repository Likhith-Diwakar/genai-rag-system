import sys
import os

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
from scripts.restore_sqlite_from_drive import restore_sqlite_if_missing


# ----------------------------------------------------------
# STATIC FALLBACK MESSAGE (MENTOR REQUEST)
# ----------------------------------------------------------

NO_CONTEXT_MESSAGE = (
    "I'm sorry, but I couldn't find relevant information in the indexed documents. "
    "Please try asking a more specific question related to the documents "
    "available in the connected Google Drive."
)


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
# INTRO SECTION
# ----------------------------------------------------------

st.write(
    "This assistant answers questions using documents stored in the connected Google Drive. "
    "It retrieves relevant sections from indexed files and generates responses grounded strictly "
    "in those documents."
)

with st.expander("What this assistant can do"):

    st.markdown(
        """
- Search across uploaded documents using semantic vector search
- Combine semantic retrieval with keyword matching
- Extract information from PDFs, Word documents, and structured files
- Process scanned PDFs and chart-heavy documents using OCR
- Preserve tables and structured content during retrieval
- Generate answers grounded strictly in the retrieved document context
"""
    )

with st.expander("Supported document types"):

    st.markdown(
        """
Currently supported formats:

- PDF documents  
- Word documents (DOCX)  
- CSV datasets  

Documents are automatically synced from the connected Google Drive folder
and indexed for retrieval.
"""
    )

with st.expander("Example questions you can ask"):

    st.markdown(
        """
### ExoHabitAI Dataset
- What is the objective of the ExoHabitAI dataset?
- Which planetary parameters are used to evaluate habitability?
- How is habitability predicted in the dataset?

### Internship Certificate
- What does the No Objection Certificate state?
- What internship duration is mentioned in the certificate?
- Which organization issued the certificate?

### Generative AI and LLMs
- What is Generative AI?
- How is Generative AI different from traditional AI?
- What are Large Language Models (LLMs)?
- What are foundation models?

### AI Concepts
- What is the transformer architecture?
- What are vector embeddings?
- Why are vector databases used in AI systems?
- What is Retrieval-Augmented Generation (RAG)?

### LLM Development
- What is prompt engineering?
- What is zero-shot prompting?
- What is few-shot prompting?
- What is in-context learning?

### AI Project Lifecycle
- What are the stages of the LLM project lifecycle?
- How do you select the right LLM for a project?
- What is fine-tuning in language models?
- What is reinforcement learning from human feedback (RLHF)?
"""
    )


# ----------------------------------------------------------
# STARTUP CHECKS
# ----------------------------------------------------------

if "startup_completed" not in st.session_state:

    try:

        restore_sqlite_if_missing()

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

        logger.error(f"Startup initialization failed: {e}")
        st.error("Failed to initialize system.")

    st.session_state.startup_completed = True


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
            and msg["content"].strip() != NO_CONTEXT_MESSAGE
        ):

            with st.expander("Sources used"):

                for s in msg["sources"]:

                    file_id = s.get("file_id")
                    file_name = s.get("file_name")
                    page_number = s.get("page_number")

                    if file_id:

                        url = f"https://drive.google.com/file/d/{file_id}/view"

                        if page_number:
                            st.markdown(f"- 🔗 [{file_name} — Page {page_number}]({url})")
                        else:
                            st.markdown(f"- 🔗 [{file_name}]({url})")

                    else:

                        if page_number:
                            st.markdown(f"- {file_name} — Page {page_number}")
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

                if answer.strip() == "I do not know based on the provided documents.":
                    answer = NO_CONTEXT_MESSAGE
                    sources = []

            except Exception as e:

                logger.error(f"RAG pipeline failed: {e}")

                answer = "An error occurred while processing your request."
                sources = []

            st.markdown(answer)

            if (
                answer.strip() != NO_CONTEXT_MESSAGE
                and sources
            ):

                with st.expander("Sources used"):

                    for s in sources:

                        file_id = s.get("file_id")
                        file_name = s.get("file_name")
                        page_number = s.get("page_number")

                        if file_id:

                            url = f"https://drive.google.com/file/d/{file_id}/view"

                            if page_number:
                                st.markdown(f"- 🔗 [{file_name} — Page {page_number}]({url})")
                            else:
                                st.markdown(f"- 🔗 [{file_name}]({url})")

                        else:

                            if page_number:
                                st.markdown(f"- {file_name} — Page {page_number}")
                            else:
                                st.markdown(f"- {file_name}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )