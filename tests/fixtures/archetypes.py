ARCHETYPES = {
    "backend-api": ("backend-api", {"framework": "fastapi"}),
    "cli": ("cli", {"framework": "typer", "cli_type": "utility"}),
    "automation": ("automation", {}),
    "chatbot": ("chatbot", {"framework": "pydantic-ai"}),
    "agent": ("agent", {"framework": "pydantic-ai"}),
    "rag": ("rag", {}),
    "data": ("data", {"data_type": "Data Analysis"}),
    "mcp": ("mcp", {}),
    "custom": ("custom", {}),
}
