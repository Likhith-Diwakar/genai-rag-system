def chunk_text(text: str, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        start = end - overlap
        if start < 0:
            start = 0

    return chunks


if __name__ == "__main__":
    sample_text = "A" * 1200
    chunks = chunk_text(sample_text)
    print(f"Chunks created: {len(chunks)}")