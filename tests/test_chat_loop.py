import asyncio

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from mat2 import chat, i18n


class FakeModel:
    """Devolve, a cada chamada, a próxima lista de chunks roteirizada."""

    def __init__(self, script):
        self.script = script
        self.calls = []

    async def astream(self, messages):
        self.calls.append(list(messages))
        for chunk in self.script.pop(0):
            yield chunk


class FakeMessage:
    sent = []

    def __init__(self, content=""):
        self.content = content
        self.elements = []

    async def stream_token(self, token):
        self.content += token

    async def send(self):
        FakeMessage.sent.append(self)


class FakeSession(dict):
    def set(self, key, value):
        self[key] = value


def tool_call_chunk(name, args, call_id="call-1"):
    import json

    return AIMessageChunk(
        content="",
        tool_call_chunks=[{"name": name, "args": json.dumps(args), "id": call_id, "index": 0}],
    )


@pytest.fixture
def run_chat(monkeypatch):
    FakeMessage.sent = []
    session = FakeSession()
    monkeypatch.setattr(chat.cl, "Message", FakeMessage)
    monkeypatch.setattr(chat.cl, "user_session", session)
    monkeypatch.setattr(chat, "plot_element", lambda props: props)

    def run(tool_script, text_script=()):
        tools_model = FakeModel(list(tool_script))
        text_model = FakeModel(list(text_script))
        monkeypatch.setattr(chat, "llm_with_tools", tools_model)
        monkeypatch.setattr(chat, "llm_text_only", text_model)
        asyncio.run(chat.on_message(HumanMessage(content="pergunta")))
        return tools_model, text_model, session

    return run


def test_plain_answer_streams_text(run_chat):
    tools_model, _, session = run_chat([[AIMessageChunk(content="Olá, "), AIMessageChunk(content="aluno")]])
    assert [m.content for m in FakeMessage.sent] == ["Olá, aluno"]
    assert len(session["history"]) == 2
    assert len(tools_model.calls) == 1


def test_tool_call_attaches_plot_and_continues(run_chat):
    args = {"title": "Sólido", "f": "sqrt(x)", "a": 0, "b": 4}
    tools_model, _, session = run_chat(
        [
            [AIMessageChunk(content="Vamos ver:"), tool_call_chunk("PlotRevolution", args)],
            [AIMessageChunk(content="O volume é $8\\pi$.")],
        ]
    )
    first, second = FakeMessage.sent
    assert first.content == "Vamos ver:"
    assert first.elements[0]["kind"] == "revolution"
    assert second.content == "O volume é $8\\pi$."

    tool_message = tools_model.calls[1][-1]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.tool_call_id == "call-1"
    assert "Gráfico exibido" in tool_message.content
    # humano, IA (tool call), tool, IA (resposta final)
    assert len(session["history"]) == 4


def test_invalid_tool_args_send_error_back_without_element(run_chat):
    bad = {"title": "x", "f": "foo(x)", "a": 0, "b": 1}
    tools_model, _, _ = run_chat(
        [
            [tool_call_chunk("PlotRevolution", bad)],
            [AIMessageChunk(content="Desculpe.")],
        ]
    )
    # A rodada da tool não tinha texto nem gráfico, então nada foi enviado nela.
    assert [m.content for m in FakeMessage.sent] == ["Desculpe."]
    assert tools_model.calls[1][-1].content.startswith("Erro:")


def test_tool_rounds_are_capped(run_chat):
    args = {"title": "t", "f": "x", "a": 0, "b": 1}
    script = [[tool_call_chunk("PlotRegion", args, f"call-{i}")] for i in range(chat.MAX_TOOL_ROUNDS)]
    tools_model, text_model, _ = run_chat(script, [[AIMessageChunk(content="Fim.")]])
    assert len(tools_model.calls) == chat.MAX_TOOL_ROUNDS
    assert len(text_model.calls) == 1
    assert FakeMessage.sent[-1].content == "Fim."


def test_history_is_trimmed_at_a_human_message():
    history = [HumanMessage(content=str(i)) for i in range(chat.MAX_HISTORY_MESSAGES + 5)]
    history.insert(6, ToolMessage(content="x", tool_call_id="1"))
    trimmed = chat._trim(history)
    assert len(trimmed) <= chat.MAX_HISTORY_MESSAGES
    assert isinstance(trimmed[0], HumanMessage)


def overload_error():
    from langchain_google_genai.chat_models import GoogleAPIError

    return GoogleAPIError(code=503, response_json={"error": {"message": "high demand", "status": "UNAVAILABLE"}})


class FailingModel(FakeModel):
    def __init__(self, error):
        super().__init__([])
        self.error = error

    async def astream(self, messages):
        self.calls.append(list(messages))
        raise self.error
        yield  # pragma: no cover - torna o método um gerador assíncrono


def test_overload_shows_friendly_message_and_keeps_history_clean(run_chat, monkeypatch):
    session = chat.cl.user_session
    session.set("history", [HumanMessage(content="antes")])
    monkeypatch.setattr(chat, "llm_with_tools", FailingModel(overload_error()))
    asyncio.run(chat.on_message(HumanMessage(content="pergunta")))
    assert [m.content for m in FakeMessage.sent] == [i18n.text(i18n.default_language(), "server", "overload")]
    assert [m.content for m in session["history"]] == ["antes"]


def test_fallback_model_is_used_on_overload():
    from langchain_core.runnables import RunnableLambda

    primary = RunnableLambda(lambda _: (_ for _ in ()).throw(overload_error()))
    fallback = RunnableLambda(lambda _: AIMessageChunk(content="resposta do fallback"))
    chain = primary.with_fallbacks([fallback], exceptions_to_handle=chat.OVERLOAD_ERRORS)

    async def collect():
        return [chunk async for chunk in chain.astream("oi")]

    assert asyncio.run(collect())[0].content == "resposta do fallback"
