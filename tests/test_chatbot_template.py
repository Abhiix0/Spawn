from spawn.templates.chatbot import ChatbotTemplate


def test_chatbot_template_default():
    t = ChatbotTemplate()
    assert t.name == "AI Chatbot"
    assert t.framework == "pydantic-ai"
    assert t.extras == []


def test_chatbot_template_openai_sdk():
    t = ChatbotTemplate(framework="openai-sdk")
    assert t.framework == "openai-sdk"


def test_chatbot_template_folders():
    t = ChatbotTemplate()
    assert "src/chatbot" in t.folders
    assert "src/providers" in t.folders
    assert "src/prompts" in t.folders
    assert "src/utils" in t.folders
    assert "tests" in t.folders


def test_chatbot_template_starter_files():
    t = ChatbotTemplate()
    paths = [path for path, _ in t.starter_files]
    assert "src/main.py" in paths
    assert "src/chatbot/chat.py" in paths
    assert "src/providers/llm.py" in paths
    assert "src/prompts/system_prompt.py" in paths
    assert "src/utils/env.py" in paths
    assert "tests/test_chatbot.py" in paths
    assert ".env.example" in paths


def test_chatbot_pydantic_ai_dependencies():
    t = ChatbotTemplate(framework="pydantic-ai")
    deps = t.get_dependencies()
    assert "pydantic-ai" in deps
    assert "python-dotenv" in deps
    assert "openai" not in deps


def test_chatbot_openai_sdk_dependencies():
    t = ChatbotTemplate(framework="openai-sdk")
    deps = t.get_dependencies()
    assert "openai" in deps
    assert "python-dotenv" in deps
    assert "pydantic-ai" not in deps


def test_chatbot_extras_add_deps():
    t = ChatbotTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_chatbot_no_extras_excludes_optional_deps():
    t = ChatbotTemplate()
    deps = t.get_dependencies()
    assert "pytest" not in deps
    assert "ruff" not in deps


def test_chatbot_pydantic_ai_readme_contains_project_name():
    t = ChatbotTemplate(framework="pydantic-ai")
    readme = t.get_readme_content({"project_name": "my-bot"})
    assert "my-bot" in readme
    assert "PydanticAI" in readme


def test_chatbot_openai_sdk_readme_contains_project_name():
    t = ChatbotTemplate(framework="openai-sdk")
    readme = t.get_readme_content({"project_name": "my-bot"})
    assert "my-bot" in readme
    assert "OpenAI" in readme


def test_chatbot_pydantic_ai_llm_file_differs_from_openai():
    t1 = ChatbotTemplate(framework="pydantic-ai")
    t2 = ChatbotTemplate(framework="openai-sdk")
    files1 = dict(t1.starter_files)
    files2 = dict(t2.starter_files)
    assert files1["src/providers/llm.py"] != files2["src/providers/llm.py"]


def test_chatbot_starter_file_paths_are_strings():
    t = ChatbotTemplate()
    for path, _ in t.starter_files:
        assert isinstance(path, str)


def test_chatbot_next_steps_contain_run_command():
    t = ChatbotTemplate()
    assert any("src.main" in step for step in t.next_steps)


def test_chatbot_next_steps_contain_env_instruction():
    t = ChatbotTemplate()
    assert any("API_KEY" in step for step in t.next_steps)
