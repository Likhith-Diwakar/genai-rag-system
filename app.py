import streamlit as st
from src.rag import generate_answer

st.set_page_config(page_title="Google Drive RAG Chatbot", layout="wide")

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")

# ----------------------------------------------------------
# Initialize chat history
# ----------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------------------------------------
# Display previous messages (WITH sources persistence)
# ----------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # ✅ Show sources if stored
        if (
            msg["role"] == "assistant"
            and msg.get("sources")
            and msg["content"].strip()
            != "I do not know based on the provided documents."
        ):
            with st.expander("Sources used"):
                for s in msg["sources"]:
                    st.write(f"- **{s['file_name']}**")

# ----------------------------------------------------------
# Chat input
# ----------------------------------------------------------

query = st.chat_input("Ask something about your documents...")

if query:

    # Save user message
    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):

            answer, sources = generate_answer(query)

            st.markdown(answer)

            # ✅ Show sources only if valid
            if (
                answer.strip()
                != "I do not know based on the provided documents."
                and sources
            ):
                with st.expander("Sources used"):
                    for s in sources:
                        st.write(f"- **{s['file_name']}**")

    # ✅ IMPORTANT: Store sources along with answer
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )
