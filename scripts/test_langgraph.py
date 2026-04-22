import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestration.langgraph_pipeline import run_pipeline


def main():
    print("\n--- LangGraph RAG Test ---\n")

    while True:
        query = input("Enter query (or type 'exit'): ").strip()

        if query.lower() == "exit":
            print("Exiting test.")
            break

        try:
            answer = run_pipeline(query)

            print("\nAnswer:")
            print(answer)
            print("\n" + "-" * 50 + "\n")

        except Exception as e:
            print("\nError occurred:")
            print(str(e))
            print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    main()
