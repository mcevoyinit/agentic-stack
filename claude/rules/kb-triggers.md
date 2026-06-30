# Knowledge Base Auto-Triggers

When the user asks about a topic, entity, person, company, project,
or technology:
- **ALWAYS** call `get_topic("<name>")` BEFORE answering from memory
- Trigger phrases: "what do I know about", "tell me about", "context
  on", "background on", "recap on", "status of", any proper noun
  question
- If the user says "kb <topic>" — that's shorthand for `get_topic`
- When the user says "remember that..." or "note that..." about a
  topic — call `add_insight`
- When exploring a new domain — call `list_topics(category=...)` or
  `search_knowledge`
- **DO NOT** answer topic questions from your own memory without
  checking the knowledge base first

<!-- CUSTOMISE: requires the knowledge-base MCP server (see
     infra-templates/knowledge-base/) wired up with get_topic,
     add_insight, list_topics, search_knowledge tools. Without it,
     these triggers have nothing to call — either install the
     server or delete this rule. -->
