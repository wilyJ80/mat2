import os

# Importar o pacote `mat2` instancia o cliente do Gemini, que exige uma chave.
# Os testes nunca chamam a API.
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
