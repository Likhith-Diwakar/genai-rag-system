import streamlit as st
from src.rag import generate_answer

st.set_page_config(page_title="Google Drive RAG Chatbot", layout="wide")

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Ask something about your documents...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents..."):
            answer, sources = generate_answer(query)
            st.markdown(answer)

            if sources:
                with st.expander("Sources used"):
                    for s in sources:
                        st.write(f"- **{s['file_name']}**")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
