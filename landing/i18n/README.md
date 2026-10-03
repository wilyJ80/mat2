# Idiomas do Torno

Os textos e o código de idiomas do Torno ficam aqui, separados em dados (`languages.json`, `locales/`) e código (`lib/`):

```
landing/i18n/
├── README.md
├── languages.json     registro dos idiomas: código, nome, sigla e bandeira; e o idioma padrão
├── locales/           um arquivo de textos por idioma
│   ├── pt-BR.json
│   └── en-US.json
└── lib/               módulos usados pela homepage e pelo chat
    ├── core.js        escolhe o idioma, guarda a preferência e carrega os textos (TornoI18n)
    ├── picker.js      seletor de idioma com bandeiras (TornoI18n.picker); carregar depois do core.js
    └── picker.css     estilos do seletor
```

Cada `locales/<código>.json` tem as seções `landing` (homepage), `chat` (botões do chat), `plot` (gráficos)
e `server` (mensagens do backend). Quem usa cada parte:

- Homepage: `landing/index.html` e `landing/site.js`.
- Chat: `public/custom.js` (carrega `lib/` sob demanda) e `public/elements/Plot.jsx`.
- Servidor: `src/mat2/i18n.py`, que lê `languages.json` e `locales/` para o prompt e as mensagens.

A interface do próprio Chainlit (placeholder, menus, botões) usa outro arquivo:
`.chainlit/translations/<código>.json`.

## Como o idioma escolhido chega a cada parte

- A preferência fica no `localStorage` (`torno-lang`), que a homepage e o chat compartilham por estarem na mesma origem.
- O mesmo valor vai num cookie `torno-lang`, que o servidor lê para o modelo responder no idioma escolhido (`src/mat2/i18n.py`).
- Sem preferência salva, vale o idioma do navegador, se houver um parecido no registro; senão, o `default`.

## Adicionar um idioma

Exemplo com espanhol (`es-ES`):

1. Copie `locales/pt-BR.json` para `locales/es-ES.json` e traduza os valores. Mantenha as chaves e o HTML dentro dos textos (`<em>`, `<span class="math">`).
2. Acrescente o idioma em `languages.json`:
   ```json
   { "code": "es-ES", "name": "Español", "short": "ES", "flag": "es" }
   ```
   O `name` também entra no prompt do modelo ("Responda sempre em Español"). O `flag` é o
   código ISO 3166-1 do país, em minúsculas; a bandeira vem da biblioteca
   [flag-icons](https://github.com/lipis/flag-icons) (MIT), carregada da cdnjs com versão fixa em `lib/picker.js`.
3. Crie `.chainlit/translations/es-ES.json`. O Chainlit já traz um `es.json` como ponto de partida; o nome do arquivo precisa ser o código completo.
4. Rode `uv run pytest`. Os testes acusam chaves faltando em qualquer um dos arquivos.

O seletor de idioma da homepage e do chat é montado a partir do registro, então não é preciso mexer em HTML nem em JavaScript.
