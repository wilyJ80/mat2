import chainlit as cl
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
)

SYSTEM_PROMPT = """Você é um assistente para auxílio com estudo de Matemática.
Conteúdo Programático:
3.      Aplicações da Integral Definida
a.      Cálculo de área de região limitada por uma função (duas ou mais)
b.      Volume do sólido de revolução
c.      Comprimento do arco
d.      Área da superfície de revolução

Utilize $ para expressões numéricas em LaTeX quando for escrever matemática.
"""


@cl.on_message
async def on_message(message: cl.Message):
    response = cl.Message(content="")

    async for chunk in llm.astream([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message.content),
    ]):
        content = chunk.content

        if isinstance(content, str):
            await response.stream_token(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    await response.stream_token(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    await response.stream_token(block["text"])

    await response.send()
