# Policy source documents

These are sample seed documents based on publicly available summaries of the Ghana NHIS Benefit Package, membership guidelines, dispute procedures, accreditation rules and the NHIS Medicines List. They are intended as a working corpus for the RAG pipeline.

**Before using the system for real evaluation**, replace each file with the corresponding authoritative source from the NHIA:
- Benefit Package PDF
- Membership and Renewal guidelines
- Member rights and complaints procedure
- Accredited facilities directory and referral guidelines
- The latest NHIS Medicines List

The ingestion script at `backend/scripts/ingest.py` will pick up `.md`, `.txt` and `.pdf` files placed in this directory and add them to the vector store. PDFs are extracted page by page.

Each file's frontmatter `category` field is preserved as metadata on every chunk, so the retriever can filter by category (`coverage`, `enrollment`, `disputes`, `facilities`, `medicines`).
