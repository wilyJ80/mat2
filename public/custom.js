// Ajustes do chat do Torno que o Chainlit não oferece por configuração:
// idioma (compartilhado com a homepage, via landing/i18n/lib), botão de
// voltar para a homepage.
(function () {
  var KEY = 'torno-lang';

  // 1. Síncrono, antes do bundle do Chainlit (que escolhe o idioma pelo
  //    navigator.language e só carrega as traduções na inicialização).
  var lang = null;
  try {
    lang = localStorage.getItem(KEY);
  } catch (e) {}
  if (lang) {
    try {
      Object.defineProperty(navigator, 'language', { get: function () { return lang; }, configurable: true });
      Object.defineProperty(navigator, 'languages', { get: function () { return [lang]; }, configurable: true });
    } catch (e) {}
    // O cookie leva o idioma ao servidor, para a resposta sair nele.
    document.cookie = KEY + '=' + encodeURIComponent(lang) + '; path=/; max-age=31536000; SameSite=Lax';
    document.documentElement.lang = lang;
  }

  // 2. Assíncrono: carrega os módulos de idioma da homepage (landing/i18n/lib),
  //    valida o idioma no registro e monta a interface.
  var LIB = '/i18n/lib/';

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  var styles = document.createElement('link');
  styles.rel = 'stylesheet';
  styles.href = LIB + 'picker.css';
  document.head.appendChild(styles);

  // picker.js estende o TornoI18n criado pelo core.js: a ordem importa.
  loadScript(LIB + 'core.js')
    .then(function () {
      return loadScript(LIB + 'picker.js');
    })
    .then(function () {
      return Promise.all([window.TornoI18n.registry(), window.TornoI18n.current()]);
    })
    .then(function (result) {
      var I18n = window.TornoI18n;
      var reg = result[0];
      var code = result[1];
      // Primeira visita direto no chat, ou idioma salvo que não existe mais:
      // recarrega para o Chainlit e o servidor usarem o idioma certo. Só se a
      // preferência foi gravada, senão (storage bloqueado) recarregaria sem fim.
      if (code !== lang && I18n.stored() === code) {
        location.reload();
        return;
      }
      return I18n.strings(code).then(function (data) {
        window.tornoStrings = data;
        start(reg, code, data.chat);
      });
    });

  var HOUSE_ICON =
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/></svg>';

  function buttonClass() {
    var ref = document.getElementById('theme-toggle');
    return ref ? ref.className : '';
  }

  function homeLink(texts) {
    var a = document.createElement('a');
    a.id = 'torno-home';
    a.href = '/';
    a.title = texts.homeTitle;
    a.setAttribute('aria-label', texts.homeTitle);
    a.className = buttonClass();
    a.innerHTML = HOUSE_ICON;
    return a;
  }

  function languagePicker(reg, code, texts) {
    var picker = window.TornoI18n.picker(reg, code, texts.language, function (next) {
      window.TornoI18n.remember(next);
      // As traduções do Chainlit só são carregadas na inicialização.
      location.reload();
    });
    picker.id = 'torno-lang';
    return picker;
  }

  function start(reg, code, texts) {
    // O React pode redesenhar o cabeçalho; os elementos são recolocados.
    function decorate() {
      var newChat = document.getElementById('new-chat-button');
      if (newChat && !document.getElementById('torno-home')) {
        newChat.parentElement.parentElement.insertBefore(homeLink(texts), newChat.parentElement);
      }
      var theme = document.getElementById('theme-toggle');
      if (theme && !document.getElementById('torno-lang')) {
        theme.parentElement.insertBefore(languagePicker(reg, code, texts), theme);
      }
    }
    decorate();
    new MutationObserver(decorate).observe(document.body, { childList: true, subtree: true });
  }
})();
