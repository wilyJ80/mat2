// Núcleo de idiomas do Torno, compartilhado pela homepage e pelo chat.
// A preferência fica em localStorage (para as páginas) e num cookie (para o
// servidor responder no idioma escolhido). Veja landing/i18n/README.md.
// O seletor de idioma é um módulo à parte: lib/picker.js.
(function () {
  var BASE = '/i18n/';
  var KEY = 'torno-lang';
  var registryPromise = null;
  var stringsCache = {};

  function getJSON(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error(url + ': ' + res.status);
      return res.json();
    });
  }

  function registry() {
    registryPromise = registryPromise || getJSON(BASE + 'languages.json');
    return registryPromise;
  }

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  // Código exato, depois só o idioma ("pt-PT" -> "pt-BR"), depois o padrão.
  function resolve(reg, wanted) {
    var codes = reg.languages.map(function (l) { return l.code; });
    if (wanted && codes.indexOf(wanted) !== -1) return wanted;
    var base = String(wanted || '').split('-')[0].toLowerCase();
    for (var i = 0; i < codes.length; i++) {
      if (codes[i].split('-')[0].toLowerCase() === base) return codes[i];
    }
    return reg.default;
  }

  function remember(code) {
    try {
      localStorage.setItem(KEY, code);
    } catch (e) {}
    document.cookie = KEY + '=' + encodeURIComponent(code) + '; path=/; max-age=31536000; SameSite=Lax';
  }

  // Idioma atual já validado contra o registro (e gravado, se ainda não estava).
  function current() {
    return registry().then(function (reg) {
      var code = resolve(reg, stored() || navigator.language);
      remember(code);
      return code;
    });
  }

  function strings(code) {
    stringsCache[code] = stringsCache[code] || getJSON(BASE + 'locales/' + code + '.json');
    return stringsCache[code];
  }

  window.TornoI18n = {
    KEY: KEY,
    registry: registry,
    stored: stored,
    resolve: resolve,
    remember: remember,
    current: current,
    strings: strings,
  };
})();
