import streamlit as st
from src.rag import generate_answer

st.set_page_config(page_title="Google Drive RAG Chatbot", layout="wide")

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
query = st.chat_input("Ask something about your documents...")

if query:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Generate answer via RAG
    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):
            answer, sources = generate_answer(query)

            st.markdown(answer)

            if sources:
                with st.expander("Sources used"):
                    seen = set()
                    for s in sources:
                        key = (s["file_id"], s["file_name"])
                        if key not in seen:
                            seen.add(key)
                            st.write(f"- **{s['file_name']}** ({s['file_id']})")

    # Save assistant message (answer only)
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
