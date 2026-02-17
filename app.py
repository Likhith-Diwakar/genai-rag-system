import streamlit as st
import time
from src.rag import generate_answer
from src.main import run_sync

st.set_page_config(page_title="Google Drive RAG Chatbot", layout="wide")

st.title("Google Drive RAG Chatbot")
st.caption("Ask questions over your Google Drive documents")

# ----------------------------------------------------------
# SESSION STATE INITIALIZATION
# ----------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "sync_running" not in st.session_state:
    st.session_state.sync_running = False

if "auto_synced" not in st.session_state:
    st.session_state.auto_synced = False


# ----------------------------------------------------------
# 🔄 AUTO SYNC ON FIRST LOAD (SILENT)
# ----------------------------------------------------------

if not st.session_state.auto_synced:

    st.session_state.sync_running = True

    with st.spinner("Initial Drive sync..."):
        run_sync(verbose=False)

    st.session_state.sync_running = False
    st.session_state.auto_synced = True


# ----------------------------------------------------------
# 🔄 SIDEBAR MANUAL SYNC (VERBOSE)
# ----------------------------------------------------------

with st.sidebar:
    st.header("System Controls")

    if st.button("🔄 Sync Drive") and not st.session_state.sync_running:

        st.session_state.sync_running = True

        with st.spinner("Syncing documents from Drive..."):
            run_sync(verbose=True)

        st.session_state.sync_running = False
        st.success("Drive synced successfully.")

    elif st.session_state.sync_running:
        st.warning("Sync already in progress...")


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

                    # ✅ Clickable Drive link if file_id exists
                    if file_id:
                        url = f"https://drive.google.com/file/d/{file_id}/view"
                        st.markdown(f"- 🔗 [{file_name}]({url})")
                    else:
                        # ✅ CSV fallback (non-clickable)
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
