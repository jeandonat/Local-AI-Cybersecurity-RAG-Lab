# Wikipedia RAG (planned next)

Goal: build an offline reference knowledge base.

## Strategy
- Start with a smaller sample to validate chunking and retrieval
- Then ingest the full dataset

## Where to store data
Use a larger SSD if you want to keep the OS disk lean:
- `rag/datasets/wikipedia/`

## Next steps
- Pick a dump format (html/text/json)
- Chunk + embed into OpenWebUI Knowledge Base
