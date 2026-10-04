// Seletor de idioma do Torno (homepage e chat). Depende de lib/core.js, que
// precisa ser carregado antes; acrescenta TornoI18n.picker.
(function () {
  // Bandeiras da lib flag-icons (MIT, https://github.com/lipis/flag-icons):
  // "flag" no languages.json é o código ISO 3166-1 do país, em minúsculas.
  var FLAGS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/flag-icons/7.5.0/flags/4x3/';

  function flagImg(lang) {
    var img = document.createElement('img');
    img.src = FLAGS_URL + lang.flag + '.svg';
    img.alt = '';
    img.className = 'torno-flag';
    return img;
  }

  // Seletor de idioma: botão só com a bandeira atual e menu vertical com
  // bandeira e nome. Estilos em lib/picker.css.
  function picker(reg, code, label, onSelect) {
    var wrap = document.createElement('div');
    wrap.className = 'torno-lang-picker';
    var currentLang = reg.languages.filter(function (l) { return l.code === code; })[0] || reg.languages[0];

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'torno-lang-trigger';
    button.title = label + ': ' + currentLang.name;
    button.setAttribute('aria-label', label + ': ' + currentLang.name);
    button.setAttribute('aria-haspopup', 'true');
    button.setAttribute('aria-expanded', 'false');
    button.appendChild(flagImg(currentLang));

    var menu = document.createElement('div');
    menu.className = 'torno-lang-menu';
    menu.setAttribute('role', 'menu');
    menu.hidden = true;

    var items = reg.languages.map(function (lang) {
      var item = document.createElement('button');
      item.type = 'button';
      item.className = 'torno-lang-item';
      item.setAttribute('role', 'menuitemradio');
      item.setAttribute('aria-checked', String(lang.code === code));
      item.lang = lang.code;
      item.appendChild(flagImg(lang));
      var name = document.createElement('span');
      name.textContent = lang.name;
      item.appendChild(name);
      item.addEventListener('click', function () {
        close();
        if (lang.code !== code) onSelect(lang.code);
      });
      menu.appendChild(item);
      return item;
    });

    function open() {
      menu.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      (items.filter(function (i) { return i.getAttribute('aria-checked') === 'true'; })[0] || items[0]).focus();
      document.addEventListener('pointerdown', outside, true);
    }

    function close(refocus) {
      menu.hidden = true;
      button.setAttribute('aria-expanded', 'false');
      document.removeEventListener('pointerdown', outside, true);
      if (refocus) button.focus();
    }

    function outside(event) {
      if (!wrap.contains(event.target)) close();
    }

    button.addEventListener('click', function () {
      menu.hidden ? open() : close();
    });
    wrap.addEventListener('keydown', function (event) {
      var index = items.indexOf(document.activeElement);
      if (event.key === 'Escape' && !menu.hidden) {
        close(true);
      } else if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !menu.hidden) {
        event.preventDefault();
        var step = event.key === 'ArrowDown' ? 1 : -1;
        items[(index + step + items.length) % items.length].focus();
      } else if (event.key === 'ArrowDown' && document.activeElement === button) {
        event.preventDefault();
        open();
      }
    });

    wrap.appendChild(button);
    wrap.appendChild(menu);
    return wrap;
  }

  window.TornoI18n.picker = picker;
})();
