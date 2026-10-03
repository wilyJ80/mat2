import { useEffect, useId, useState } from 'react';

// Custom elements do Chainlit não podem importar pacotes npm arbitrários,
// então o JSXGraph é carregado da CDN uma única vez por página.
const JSXGRAPH_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jsxgraph/1.13.3/jsxgraphcore.js';
const JSXGRAPH_SRI = 'sha512-M4DQBLnPX5RVpkhw4lBBqM2KbzQze0Zq4uIy/AEVinTtnolP9/TPD0q6rtLzTMKDIhi9ftZ/T4XXXrO3FS5s+g==';

function loadJSXGraph() {
  if (window.JXG) return Promise.resolve(window.JXG);
  if (!window.__jsxgraphLoader) {
    window.__jsxgraphLoader = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = JSXGRAPH_URL;
      script.integrity = JSXGRAPH_SRI;
      script.crossOrigin = 'anonymous';
      script.onload = () => resolve(window.JXG);
      script.onerror = () => {
        window.__jsxgraphLoader = null;
        script.remove();
        reject(new Error('JSXGraph failed to load'));
      };
      document.head.appendChild(script);
    });
  }
  return window.__jsxgraphLoader;
}

// Usados se os textos do idioma ainda não tiverem carregado.
const FALLBACK_TEXTS = {
  dragToRotate: 'Arraste para girar',
  revolutionHint: 'Arraste para girar · use o controle θ para formar o sólido',
  loadError: 'Não foi possível carregar o gráfico',
};

// Cores da identidade do Torno (--chart-1/2/3 e neutros do tema). Azul e laranja
// continuam distintos para daltônicos. Superfícies 3D usam o shader do JSXGraph,
// que trabalha com matiz (HSL); curvas e textos usam cores comuns.
const HUES = { main: 217, second: 27, cap: 268 };

function palette(dark) {
  const base = dark
    ? { text: '#F0F1F5', axis: '#9EA5B3', main: '#60A5FA', second: '#FA9E42', note: '#BC8CF2', light: [35, 75] }
    : { text: '#131620', axis: '#575D6A', main: '#2563EB', second: '#DA5E0B', note: '#8041C8', light: [40, 85] };
  return { ...base, hues: HUES };
}

// As expressões são compiladas pelo JessieCode (parser do JSXGraph). Ele não é
// um sandbox completo: a segurança vem da whitelist do backend
// (src/mat2/expressions.py), que só deixa passar aritmética e funções matemáticas.
function compile(board, expr, vars = 'x') {
  return board.jc.snippet(expr, true, vars, false);
}

function view3dAttributes(colors, names, az) {
  const axis = (name) => ({
    name,
    strokeColor: colors.axis,
    label: { strokeColor: colors.text, fontSize: 14 },
  });
  return {
    projection: 'parallel',
    axesPosition: 'center',
    xAxis: axis(names[0]),
    yAxis: axis(names[1]),
    zAxis: axis(names[2]),
    xPlaneRear: { visible: false },
    yPlaneRear: { visible: false },
    zPlaneRear: { visible: false },
    az: { slider: { visible: false, start: az } },
    el: { slider: { visible: false, start: 0.35 } },
    bank: { slider: { visible: false } },
    depthOrder: { enabled: true },
  };
}

function surfaceAttributes(colors, hue, steps) {
  return {
    type: 'shader',
    stepsU: steps[0],
    stepsV: steps[1],
    polyhedron: {
      fillOpacity: 0.85,
      strokeWidth: 0.3,
      strokeColor: colors.axis,
      strokeOpacity: 0.35,
      shader: {
        enabled: true,
        type: 'angle',
        hue,
        saturation: 75,
        minLightness: colors.light[0],
        maxLightness: colors.light[1],
        light: { dir: 0 },
      },
    },
  };
}

function drawRevolution(board, p, colors) {
  const f = compile(board, p.f);
  // Sem g, a região vai de f até o eixo de rotação (eixo x) ou até y = 0 (eixo y).
  const g = p.g ? compile(board, p.g) : () => (p.axis === 'x' ? p.k : 0);

  const theta = board.create('slider', [[-6.5, -7], [-1.5, -7], [0.05, 1.5 * Math.PI, 2 * Math.PI]], {
    name: 'θ',
    snapWidth: 0.05,
    label: { strokeColor: colors.text },
    baseline: { strokeColor: colors.axis },
    highline: { strokeColor: colors.main },
    fillColor: colors.main,
    strokeColor: colors.main,
  });

  const view = board.create('view3d', [[-4.5, -3.5], [9, 9], p.bounds], view3dAttributes(colors, ['x', 'z', 'y'], 2.8));

  // Um ponto (x, y) do plano gira em torno do eixo e vira (X, Y, Z) na cena,
  // onde a altura Z da cena corresponde ao y do plano.
  const rotate =
    p.axis === 'x'
      ? (x, y, t) => [x, (y - p.k) * Math.sin(t), p.k + (y - p.k) * Math.cos(t)]
      : (x, y, t) => [p.k + (x - p.k) * Math.cos(t), (x - p.k) * Math.sin(t), y];

  // Cada face do polígono é um elemento SVG, então os passos ficam baixos
  // para a rotação continuar fluida.
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
      surfaceAttributes(colors, hue, steps),
    );

  const ab = [p.a, p.b];
  const segment = (x) => (s) => [x, g(x) + s * (f(x) - g(x))];
  revolve((x) => [x, f(x)], ab, colors.hues.main, [24, 28]);
  if (p.g) revolve((x) => [x, g(x)], ab, colors.hues.second, [24, 28]);
  // Bordas laterais da região: viram tampas (eixo x) ou paredes cilíndricas (eixo y).
  revolve(segment(p.a), [0, 1], colors.hues.cap, [2, 28]);
  revolve(segment(p.b), [0, 1], colors.hues.cap, [2, 28]);

  // Região geradora destacada no plano.
  const outline = { strokeColor: colors.text, strokeWidth: 3 };
  view.create('curve3d', [(x) => x, () => 0, (x) => f(x), ab], outline);
  view.create('curve3d', [(x) => x, () => 0, (x) => g(x), ab], outline);

  // Eixo de rotação.
  const axisLine = { strokeColor: colors.text, strokeWidth: 1.5, dash: 2 };
  if (p.axis === 'x') view.create('curve3d', [(s) => s, () => 0, () => p.k, p.bounds[0]], axisLine);
  else view.create('curve3d', [() => p.k, () => 0, (s) => s, p.bounds[2]], axisLine);
}

function drawSurface(board, p, colors) {
  const f = compile(board, p.f, 'x, y');
  // O view3d só normaliza x e y; z fica em escala real. Comprimimos z para a
  // altura caber no quadro (os eixos não têm marcações, então é só visual).
  const [[x0, x1], [y0, y1], [z0, z1]] = p.bounds;
  const scale = Math.min(1, Math.max(x1 - x0, y1 - y0) / (z1 - z0));
  const bounds = [p.bounds[0], p.bounds[1], [z0 * scale, z1 * scale]];
  const view = board.create('view3d', [[-4.5, -3.5], [9, 9], bounds], view3dAttributes(colors, ['x', 'y', 'z'], 1.2));
  view.create('functiongraph3d', [(x, y) => f(x, y) * scale, p.bounds[0], p.bounds[1]], surfaceAttributes(colors, colors.hues.main, [24, 24]));
}

function drawRegion(board, p, colors) {
  const f = compile(board, p.f);
  const g = p.g ? compile(board, p.g) : () => 0;
  board.create('functiongraph', [f], { strokeColor: colors.main, strokeWidth: 2.5 });
  if (p.g) board.create('functiongraph', [g], { strokeColor: colors.second, strokeWidth: 2.5 });

  const steps = 200;
  const xs = Array.from({ length: steps + 1 }, (_, i) => p.a + ((p.b - p.a) * i) / steps);
  board.create('curve', [[...xs, ...[...xs].reverse()], [...xs.map(f), ...[...xs].reverse().map(g)]], {
    fillColor: colors.main,
    fillOpacity: 0.25,
    strokeWidth: 0,
    highlight: false,
  });

  // Anotações. Os rótulos chegam do backend sem <, >, & nem aspas, então
  // podem ser renderizados como HTML com segurança.
  const [[x0, x1], [y0, y1]] = p.bounds;
  const fixed = { fixed: true, highlight: false };
  // Acima do eixo e levemente à direita, para não colidir com os números do eixo.
  const axisLabel = (x, text) =>
    board.create('text', [x + (x1 - x0) * 0.008, (y1 - y0) * 0.035, text], {
      ...fixed,
      anchorX: 'left',
      anchorY: 'bottom',
      fontSize: 16,
      cssStyle: 'font-weight: 700',
      strokeColor: colors.note,
    });

  // Intervalo de integração destacado sobre o eixo x.
  board.create('segment', [[p.a, 0], [p.b, 0]], { ...fixed, strokeColor: colors.note, strokeWidth: 5, lineCap: 'round' });
  for (const [x, text] of [[p.a, p.a_label], [p.b, p.b_label]]) {
    board.create('point', [x, 0], { ...fixed, name: '', size: 3, fillColor: colors.note, strokeColor: colors.note });
    axisLabel(x, text);
  }

  for (const mark of p.marks || []) {
    board.create('segment', [[mark.x, y0], [mark.x, y1]], { ...fixed, strokeColor: colors.note, strokeWidth: 1.5, dash: 2 });
    axisLabel(mark.x, mark.label);
  }

  for (const point of p.points || []) {
    board.create('point', [point.x, point.y], {
      ...fixed,
      name: point.label,
      size: 4,
      fillColor: colors.note,
      strokeColor: colors.text,
      strokeWidth: 1,
      label: { strokeColor: colors.text, fontSize: 15, cssStyle: 'font-weight: 700', offset: [8, 10] },
    });
  }
}

export default function Plot() {
  const id = 'plot-' + useId().replace(/:/g, '');
  const [error, setError] = useState(null);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.classList.contains('dark')));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let board;
    let cancelled = false;
    loadJSXGraph()
      .then((JXG) => {
        if (cancelled) return;
        const colors = palette(dark);
        JXG.Options.text.strokeColor = colors.text;
        if (props.kind === 'region') {
          const [[x0, x1], [y0, y1]] = props.bounds;
          board = JXG.JSXGraph.initBoard(id, {
            boundingbox: [x0, y1, x1, y0],
            axis: true,
            defaultAxes: {
              x: { strokeColor: colors.axis, ticks: { label: { strokeColor: colors.text } } },
              y: { strokeColor: colors.axis, ticks: { label: { strokeColor: colors.text } } },
            },
            showCopyright: false,
            showNavigation: false,
            showInfobox: false,
            pan: { enabled: false },
            zoom: { enabled: false },
          });
        } else {
          board = JXG.JSXGraph.initBoard(id, {
            boundingbox: [-8, 8, 8, -8],
            axis: false,
            showCopyright: false,
            showNavigation: false,
            showInfobox: false,
            pan: { enabled: false },
            zoom: { enabled: false },
          });
        }
        board.suspendUpdate();
        if (props.kind === 'revolution') drawRevolution(board, props, colors);
        else if (props.kind === 'surface') drawSurface(board, props, colors);
        else drawRegion(board, props, colors);
        board.unsuspendUpdate();
      })
      .catch((e) => {
        console.error(e);
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
      if (board) window.JXG.JSXGraph.freeBoard(board);
    };
  }, [id, dark, JSON.stringify(props)]);

  // Textos do idioma escolhido (landing/i18n/locales/<código>.json, seção "plot"),
  // carregados pelo public/custom.js.
  const texts = { ...FALLBACK_TEXTS, ...window.tornoStrings?.plot };
  const hint =
    props.kind === 'region' ? null : props.kind === 'revolution' ? texts.revolutionHint : texts.dragToRotate;

  return (
    <div className="w-full max-w-xl rounded-lg border bg-card p-3">
      {props.title && <div className="mb-2 text-sm font-medium">{props.title}</div>}
      {error ? (
        <div className="text-sm text-destructive">{texts.loadError}</div>
      ) : (
        <div id={id} className="w-full" style={{ aspectRatio: '1 / 1', touchAction: 'none' }} />
      )}
      {hint && !error && <div className="mt-2 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
