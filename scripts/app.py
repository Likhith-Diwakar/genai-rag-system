import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from src.llm.rag import generate_answer
from src.ingestion.main import run_sync


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

if "initial_sync_done" not in st.session_state:
    st.session_state.initial_sync_done = False

if "scheduler_started" not in st.session_state:
    st.session_state.scheduler_started = False


# ----------------------------------------------------------
# BACKGROUND SYNC FUNCTION (SILENT)
# ----------------------------------------------------------

def background_sync():
    # Silent incremental sync
    run_sync(verbose=False)


# ----------------------------------------------------------
# INITIAL SYNC (RUNS ONCE)
# ----------------------------------------------------------

if not st.session_state.initial_sync_done:
    with st.spinner("Initial Drive sync..."):
        run_sync(verbose=True)   # allow logs on first run

    st.session_state.initial_sync_done = True


# ----------------------------------------------------------
# START BACKGROUND SCHEDULER
# ----------------------------------------------------------

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        background_sync,
        trigger="interval",
        minutes=2,          # > sync runtime
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    return scheduler


if not st.session_state.scheduler_started:
    start_scheduler()
    st.session_state.scheduler_started = True


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
