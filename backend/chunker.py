import re

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_text(text, source, base_id, chunk_size=300, overlap=45):
    text = clean_text(text)
    words = text.split()

    if len(words) <= chunk_size:
        return [{
            "chunk_id": f"{base_id}#1", 
            "source": source, 
            "text": text
        }]

    chunks = []
    start = 0
    num = 1

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append({
            "chunk_id": f"{base_id}#{num}",
            "source": source,
            "text": " ".join(chunk_words),
        })

        if end >= len(words):
            break

        start = end - overlap
        num += 1

    return chunks

if __name__ == "__main__":
    sample = """
    Our return policy allows customers to return items within 30 days of purchase.
    Items must be unused and in their original packaging. Refunds are processed to the
    original payment method within 5 to 7 business days. Shipping costs are non-refundable
    unless the item arrived damaged. To start a return, contact our support team with your
    order number and the reason for the return. We do not accept returns on final sale items.
    """

    for c in chunk_text(sample, "test.txt", "test", chunk_size=5, overlap=1):
        print(c["chunk_id"], "→", c["text"])
