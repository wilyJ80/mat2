// Homepage: tema e idioma. Os textos vêm de /i18n/locales/<código>.json (seção
// "landing"); o HTML traz o português como conteúdo inicial e sem JavaScript.
(function () {
  var root = document.documentElement;
  var THEME_KEY = 'vite-ui-theme'; // mesma chave do Chainlit: o chat herda o tema

  // --- Tema -----------------------------------------------------------------
  var themeButton = document.getElementById('theme-toggle');
  var systemDark = window.matchMedia('(prefers-color-scheme: dark)');

  function effectiveTheme() {
    return root.dataset.theme || (systemDark.matches ? 'dark' : 'light');
  }

  function syncThemeButton() {
    themeButton.dataset.mode = effectiveTheme();
  }

  themeButton.addEventListener('click', function () {
    var next = effectiveTheme() === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (e) {}
    syncThemeButton();
  });
  systemDark.addEventListener('change', syncThemeButton);
  syncThemeButton();

  // --- Idioma ---------------------------------------------------------------
  var I18n = window.TornoI18n;
  var pickerSlot = document.getElementById('lang-picker');

  function apply(code, texts) {
    root.lang = code;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var value = texts[el.dataset.i18n];
      if (value !== undefined) el.innerHTML = value; // textos nossos, de arquivos do repositório
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.dataset.i18nAttr.split(';').forEach(function (pair) {
        var parts = pair.split(':');
        var value = texts[parts[1]];
        if (value !== undefined) el.setAttribute(parts[0], value);
      });
    });
  }

  function load(reg, code) {
    return I18n.strings(code).then(function (data) {
      apply(code, data.landing);
      // O seletor é refeito para mostrar a bandeira e o rótulo do novo idioma.
      pickerSlot.replaceChildren(
        I18n.picker(reg, code, data.landing['language.label'], function (next) {
          I18n.remember(next);
          load(reg, next).then(function () {
            pickerSlot.querySelector('button').focus();
          });
        })
      );
    });
  }

  Promise.all([I18n.registry(), I18n.current()]).then(function (result) {
    return load(result[0], result[1]);
  });
})();
