"""Servidor do Torno: homepage estática em `/` e o chat do Chainlit em `/chat`.

Rode com `uv run mat2` (ou `uvicorn mat2.server:app`) a partir da raiz do
repositório: o Chainlit procura `.chainlit/`, `public/` e `.env` no diretório atual.
"""

import os
from pathlib import Path

from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Mesma raiz que o Chainlit usa para achar .chainlit/ e public/.
ROOT = Path(os.getenv("CHAINLIT_APP_ROOT", os.getcwd()))
CHAT_PATH = "/chat"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


# A montagem do Chainlit só casa com "/chat/..."; os links da homepage usam "/chat".
@app.get(CHAT_PATH, include_in_schema=False)
async def chat_redirect() -> RedirectResponse:
    return RedirectResponse(f"{CHAT_PATH}/")


mount_chainlit(app=app, target=str(ROOT / "src" / "mat2" / "chat.py"), path=CHAT_PATH)
# Montada por último: "/" casaria com qualquer caminho, inclusive /chat.
app.mount("/", StaticFiles(directory=ROOT / "landing", html=True), name="landing")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT") or 8000))
