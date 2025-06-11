---
title: Custom Entity Types
subtitle: Enhancing Graphiti with Custom Ontologies
---

Graphiti supports custom ontologies, allowing you to define specific types with custom attributes for the nodes in your knowledge graph. This feature enables more precise and domain-specific knowledge representation. This guide explains how to create user-defined entities to model your domain knowledge.

### Defining Custom Ontologies
You can define custom entity types as Pydantic models when adding episodes to your knowledge graph. 

#### Creating Entity Types
The code below is an example of defining new entity types, Customer and Product, by extending the `BaseModel` class from Pydantic:

```python
from pydantic import BaseModel, Field

class Customer(BaseModel):
    """A customer of the service"""
    name: str | None = Field(..., description="The name of the customer")
    email: str | None = Field(..., description="The email address of the customer")
    subscription_tier: str | None  = Field(..., description="The customer's subscription level")


class Product(BaseModel):
    """A product or service offering"""
    price: float | None  = Field(..., description="The price of the product or service")
    category: str | None  = Field(..., description="The category of the product")
```

#### Adding Data with Entities
Now when you add episodes to your graph, you can pass in a dictionary of the Pydantic models you created above - this will ensure that new nodes are classified into one of the provided types (or none of the provided types) and the attributes of that type are automatically populated:

```python
entity_types = {"Customer": Customer, "Product": Product}

await client.add_episode(
            name='Message',
            episode_body="New customer John (john@example.com) signed up for premium tier and purchased our Analytics Pro product ($199.99) from the Software category." ,
            reference_time=datetime.now(),
            source_description='Support Ticket Log',
            group_id=group_id,
            entity_types=entity_types,
        )
```

#### Results
When you provide custom entity types, Graphiti will:

- Extract entities and classify them according to your defined types
- Identify and populate the provided attributes of each type

This will affect the `node.labels` and `node.attributes` fields of the extracted nodes:

```python
# Example Customer Node Attributes
{
    ...
    "labels": ["Entity","Customer"],
    "attributes": {
        "name": "John",
        "email": "john@example.com",
        "subscription_tier": "premium",
    }
}

# Example Product Node Attributes
{
    ...
    "labels": ["Entity", "Product"],
    "attributes": {
        "price": 199.99,
        "category": "Software",
    }
}
```

### Schema Evolution
Your knowledge graph's schema can evolve over time as your needs change. You can update entity types by adding new attributes to existing types without breaking existing nodes. When you add new attributes, existing nodes will preserve their original attributes while supporting the new ones for future updates. This flexible approach allows your knowledge graph to grow and adapt while maintaining backward compatibility with historical data. 

For example, if you initially defined a "Customer" type with basic attributes like name and email, you could later add attributes like "loyalty_tier" or "acquisition_channel" without needing to modify or migrate existing customer nodes in your graph.

### Best Practices
When extracting attributes, maintain consistent naming conventions across related entity types and include a clear and thorough description of each attribute.

Additionally, attributes should be broken down into their smallest meaningful units rather than storing compound information. 

Instead of:
```python
class Employment(BaseModel):
    """User's current employment"""
    employment: str | None = Field(..., description="Employment details")
```

Use:
```python
class Employment(BaseModel):
    """User's current employment"""
    role: str | None = Field(..., description="Job title")
    employer: str | None = Field(..., description="Employer name")
    ...
```
### Migration Guide
If you're upgrading from a previous version of Graphiti:
- You can add entity types to new episodes, even if existing episodes in the graph did not have entity types. Existing nodes will continue to work without being classified.
-  To add types to previously ingested data, you need to re-ingest it with entity types set into a new graph.
