# AI Engineering Architecture Handbook · JR Academy

Public educational materials by JR Academy. All identities and business data are fictional.

Start with the complete artifacts:

- [RAG retrieval results and cited extracts](examples/rag-retrieval/RESULTS.md): hand-authored vectors, lexical overlap, RRF and explicit evidence filters. No embedding or reranker model is evaluated.
- [MCP transcript and policy outcomes](examples/mcp-lifecycle/RESULTS.md): offline message simulation against a fixed 2025-11-25 reference. No live MCP server, OAuth flow or network requests.
- [Checkpoint recovery traces and receipts](examples/agent-recovery/RESULTS.md): real local child-process crashes, with SQLite stores standing in for the workflow and an independent provider. No distributed exactly-once claim.

Chinese guides accompany each artifact. Scripts require Python 3.9+ and the standard library only. No credentials, paid models or installation are required. Outputs are already included.

Website topic links are proposed continuation paths, not evidence that these examples are integrated into the live product. See [sources](SOURCES.md) and [publication status](PUBLICATION.md). No open-source license has been applied. See SOURCES.md for attribution and scope.
