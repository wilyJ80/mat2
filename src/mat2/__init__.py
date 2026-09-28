import chainlit as cl
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
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
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message.content),
    ])

    await cl.Message(content=response.content).send()
