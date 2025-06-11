---
title: Overview
subtitle: Temporal Knowledge Graphs for Agentic Applications
---

<Card title="What is a Knowledge Graph?" icon="duotone chart-network">
  Graphiti helps you create and query Knowledge Graphs that evolve over time. A
  knowledge graph is a network of interconnected facts, such as *“Kendra loves
  Adidas shoes.”* Each fact is a *“triplet”* represented by two entities, or
  nodes (*”Kendra”, “Adidas shoes”*), and their relationship, or edge
  (*”loves”*).
  <br />
  Knowledge Graphs have been explored extensively for information retrieval.
  What makes Graphiti unique is its ability to autonomously build a knowledge
  graph while handling changing relationships and maintaining historical
  context.
</Card>

![graphiti intro slides](file:c8d6f42a-b36f-446a-a3c1-99754776357d)

Graphiti builds dynamic, temporally-aware knowledge graphs that represent complex, evolving relationships between entities over time. It ingests both unstructured and structured data, and the resulting graph may be queried using a fusion of time, full-text, semantic, and graph algorithm approaches.

With Graphiti, you can build LLM applications such as:

- Assistants that learn from user interactions, fusing personal knowledge with dynamic data from business systems like CRMs and billing platforms.
- Agents that autonomously execute complex tasks, reasoning with state changes from multiple dynamic sources.

Graphiti supports a wide range of applications in sales, customer service, health, finance, and more, enabling long-term recall and state-based reasoning for both assistants and agents.

## Graphiti and Zep Memory

Graphiti powers the core of [Zep's memory layer](https://www.getzep.com) for LLM-powered Assistants and Agents.

We're excited to open-source Graphiti, believing its potential reaches far beyond memory applications.

## Why Graphiti?

We were intrigued by Microsoft’s GraphRAG, which expanded on RAG text chunking by using a graph to better model a document corpus and making this representation available via semantic and graph search techniques. However, GraphRAG did not address our core problem: It's primarily designed for static documents and doesn't inherently handle temporal aspects of data.

Graphiti is designed from the ground up to handle constantly changing information, hybrid semantic and graph search, and scale:

- **Temporal Awareness:** Tracks changes in facts and relationships over time, enabling point-in-time queries. Graph edges include temporal metadata to record relationship lifecycles.
- **Episodic Processing:** Ingests data as discrete episodes, maintaining data provenance and allowing incremental entity and relationship extraction.
- **Custom Entity Types:** Supports defining domain-specific entity types, enabling more precise knowledge representation for specialized applications.
- **Hybrid Search:** Combines semantic and BM25 full-text search, with the ability to rerank results by distance from a central node e.g. "Kendra".
- **Scalable:** Designed for processing large datasets, with parallelization of LLM calls for bulk processing while preserving the chronology of events.
- **Supports Varied Sources:** Can ingest both unstructured text and structured JSON data.


| Aspect                     | GraphRAG                              | Graphiti                                         |
| -------------------------- | ------------------------------------- | ------------------------------------------------ |
| **Primary Use**            | Static document summarization         | Dynamic data management                          |
| **Data Handling**          | Batch-oriented processing             | Continuous, incremental updates                  |
| **Knowledge Structure**    | Entity clusters & community summaries | Episodic data, semantic entities, communities    |
| **Retrieval Method**       | Sequential LLM summarization          | Hybrid semantic, keyword, and graph-based search |
| **Adaptability**           | Low                                   | High                                             |
| **Temporal Handling**      | Basic timestamp tracking              | Explicit bi-temporal tracking                    |
| **Contradiction Handling** | LLM-driven summarization judgments    | Temporal edge invalidation                       |
| **Query Latency**          | Seconds to tens of seconds            | Typically sub-second latency                     |
| **Custom Entity Types**    | No                                    | Yes, customizable                                |
| **Scalability**            | Moderate                              | High, optimized for large datasets               |

Graphiti is specifically designed to address the challenges of dynamic and frequently updated datasets, making it particularly suitable for applications requiring real-time interaction and precise historical queries.


![graphiti demo slides](file:730a1e08-08fa-4989-9951-952157a82798)

