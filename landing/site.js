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
    if (window.JXG && window._initLandingPlot) {
      window._initLandingPlot();
    }
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

  // --- Gráfico Interativo ---
  function initPlot() {
    const plotId = 'landing-plot';
    if (!document.getElementById(plotId)) return;
    
    const isDark = effectiveTheme() === 'dark';
    const textCol = isDark ? '#F0F1F5' : '#131620';
    const axisCol = isDark ? '#9EA5B3' : '#575D6A';
    const mainCol = isDark ? '#60A5FA' : '#2563EB';
    const secondCol = isDark ? '#FA9E42' : '#DA5E0B';
    const light = isDark ? [35, 75] : [40, 85];

    if (window._landingBoard) window.JXG.JSXGraph.freeBoard(window._landingBoard);

    window.JXG.Options.text.strokeColor = textCol;

    const board = window.JXG.JSXGraph.initBoard(plotId, {
      boundingbox: [-8, 8, 8, -8],
      axis: false,
      showCopyright: false,
      showNavigation: false,
      showInfobox: false,
      pan: { enabled: false },
      zoom: { enabled: false },
    });
    window._landingBoard = board;

    const view = board.create('view3d', [[-4.5, -3.5], [9, 9], [[-3.5, 3.5], [-6.5, 6.5], [-6.5, 6.5]]], {
      projection: 'parallel',
      axesPosition: 'center',
      xAxis: { name: 'x', strokeColor: axisCol, label: { strokeColor: textCol, fontSize: 14 } },
      yAxis: { name: 'z', strokeColor: axisCol, label: { strokeColor: textCol, fontSize: 14 } },
      zAxis: { name: 'y', strokeColor: axisCol, label: { strokeColor: textCol, fontSize: 14 } },
      xPlaneRear: { visible: false },
      yPlaneRear: { visible: false },
      zPlaneRear: { visible: false },
      az: { slider: { visible: false, start: 2.8 } },
      el: { slider: { visible: false, start: 0.35 } },
      bank: { slider: { visible: false } },
      depthOrder: { enabled: true },
    });

    const theta = board.create('slider', [[-6.5, -7], [-1.5, -7], [0.05, 1.5 * Math.PI, 2 * Math.PI]], {
      name: 'θ',
      snapWidth: 0.05,
      label: { strokeColor: textCol },
      baseline: { strokeColor: axisCol },
      highline: { strokeColor: mainCol },
      fillColor: mainCol,
      strokeColor: mainCol,
    });

    const f = (x) => 4;
    const g = (x) => x * x;
    const k = -1;
    const ab = [-2, 2];

    const rotate = (x, y, t) => [x, (y - k) * Math.sin(t), k + (y - k) * Math.cos(t)];

    const surfaceAttributes = (hue, steps) => ({
      type: 'shader',
      stepsU: steps[0],
      stepsV: steps[1],
      polyhedron: {
        fillOpacity: 0.85,
        strokeWidth: 0.3,
        strokeColor: axisCol,
        strokeOpacity: 0.35,
        shader: {
          enabled: true,
          type: 'angle',
          hue,
          saturation: 75,
          minLightness: light[0],
          maxLightness: light[1],
          light: { dir: 0 },
        },
      },
    });

    const revolve = (curve, range, hue, steps) =>
      view.create(
        'parametricsurface3d',
        [
          (u, t) => rotate(...curve(u), t)[0],
          (u, t) => rotate(...curve(u), t)[1],
          (u, t) => rotate(...curve(u), t)[2],
          range,
          [0, () => theta.Value()],
        ],
        surfaceAttributes(hue, steps)
      );

    const segment = (x) => (s) => [x, g(x) + s * (f(x) - g(x))];
    revolve((x) => [x, f(x)], ab, 217, [24, 28]);
    revolve((x) => [x, g(x)], ab, 27, [24, 28]);
    revolve(segment(-2), [0, 1], 268, [2, 28]);
    revolve(segment(2), [0, 1], 268, [2, 28]);

    const outline = { strokeColor: textCol, strokeWidth: 3 };
    view.create('curve3d', [(x) => x, () => 0, (x) => f(x), ab], outline);
    view.create('curve3d', [(x) => x, () => 0, (x) => g(x), ab], outline);

    const axisLine = { strokeColor: textCol, strokeWidth: 1.5, dash: 2 };
    view.create('curve3d', [(s) => s, () => 0, () => k, [-3.5, 3.5]], axisLine);
  }
  window._initLandingPlot = initPlot;

  if (document.getElementById('landing-plot')) {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsxgraph/1.13.3/jsxgraphcore.js';
    script.crossOrigin = 'anonymous';
    script.onload = () => initPlot();
    document.head.appendChild(script);
  }

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
