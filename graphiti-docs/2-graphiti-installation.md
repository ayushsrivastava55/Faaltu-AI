---
title: Installation
subtitle: How to install Graphiti
---

Requirements:

- Python 3.10 or higher
- Neo4j 5.21 or higher
- OpenAI API key (Graphiti defaults to OpenAI for LLM inference and embedding)

Optional:

- Gemini, Anthropic, or Groq API key (for alternative LLM providers)

<Note>
The simplest way to install Neo4j is via [Neo4j Desktop](https://neo4j.com/download/). It provides a user-friendly interface to manage Neo4j instances and databases.
</Note>

```
pip install graphiti-core
```

or

```
poetry add graphiti-core
```

## Alternative LLM Providers

Graphiti supports multiple LLM providers beyond OpenAI. However, Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini). 
Using other services may result in incorrect output schemas and ingestion failures. This is particularly problematic when using smaller models.


To install Graphiti with support for alternative providers, use the following package extras with Poetry:

<Note>
Note that even when using Anthropic for LLM inference, OpenAI is still required for embedding functionality. Make sure to set both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` environment variables when using Anthropic.
</Note>

```
# For Anthropic support
poetry add "graphiti-core[anthropic]"

# For Google Generative AI support
poetry add "graphiti-core[google-genai]"

# For Groq support
poetry add "graphiti-core[groq]"

# For multiple providers
poetry add "graphiti-core[anthropic,groq,google-genai]"
```

These extras automatically install the required dependencies for each provider.

## OpenAI Compatible LLM Providers

Please use the `OpenAIGenericClient` to connect to OpenAI compatible LLM providers. Graphiti makes use of OpenAI Structured Output, which is not supported by other providers.

The `OpenAIGenericClient` ensures that required schema is injected into the prompt, so that the LLM can generate valid JSON output.

<Warning>
Graphiti works best with LLM services that support Structured Output (such as OpenAI and Gemini). 
Using other services may result in incorrect output schemas and ingestion failures. This is particularly problematic when using smaller models.
</Warning>

## Using Graphiti with Azure OpenAI

Graphiti supports Azure OpenAI for both LLM inference and embeddings. To use Azure OpenAI, you'll need to configure both the LLM client and embedder with your Azure OpenAI credentials:

```python
from openai import AsyncAzureOpenAI
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

# Azure OpenAI configuration
api_key = "<your-api-key>"
api_version = "<your-api-version>"
azure_endpoint = "<your-azure-endpoint>"

# Create Azure OpenAI client for LLM
azure_openai_client = AsyncAzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=azure_endpoint
)

# Initialize Graphiti with Azure OpenAI clients
graphiti = Graphiti(
    "bolt://localhost:7687",
    "neo4j",
    "password",
    llm_client=OpenAIClient(
        client=azure_openai_client
    ),
    embedder=OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            embedding_model="text-embedding-3-small"  # Use your Azure deployed embedding model name
        ),
        client=azure_openai_client
    ),
    # Optional: Configure the OpenAI cross encoder with Azure OpenAI
    cross_encoder=OpenAIRerankerClient(
        client=azure_openai_client
    )
)

# Now you can use Graphiti with Azure OpenAI
```

Make sure to replace the placeholder values with your actual Azure OpenAI credentials and specify the correct embedding model name that's deployed in your Azure OpenAI service.

## Using Graphiti with Google Gemini

To use Graphiti with Google Gemini, install the required package:

```
poetry add "graphiti-core[google-genai]"
```

<Note>
When using Google Gemini, you'll need to set the `GOOGLE_API_KEY` environment variable with your Google API key.
</Note>

Here's how to configure Graphiti with Google Gemini:

```python
import os
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

# Google API key configuration
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable must be set")

# Initialize Graphiti with Gemini clients
graphiti = Graphiti(
    "bolt://localhost:7687",
    "neo4j",
    "password",
    llm_client=GeminiClient(
        config=LLMConfig(
            api_key=api_key,
            model="gemini-2.0-flash"
        )
    ),
    embedder=GeminiEmbedder(
        config=GeminiEmbedderConfig(
            api_key=api_key,
            embedding_model="embedding-001"
        )
    )
)
```

## Optional Environment Variables

In addition to the provider-specific API keys, Graphiti supports several optional environment variables:

- `USE_PARALLEL_RUNTIME`: A boolean variable that can be set to true to enable Neo4j's parallel runtime feature for several search queries. Note that this feature is not supported for Neo4j Community Edition or for smaller AuraDB instances, so it's off by default.
