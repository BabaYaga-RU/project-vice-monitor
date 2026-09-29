(() => {
  const ENGINE = 'https://cdn.jsdelivr.net/npm/xash3d-fwgs@1.2.2/dist/';
  const CS = 'https://cdn.jsdelivr.net/npm/cs16-client@0.1.2/dist/cstrike/';
  const $ = (id) => document.getElementById(id);
  const status = $('status');
  const button = $('start');
  const zipInput = $('assets');
  let engineReady = false;
  let gameZip = null;
  let busy = false;

  const runtimeFiles = {
    'xash.wasm': ENGINE + 'xash.wasm',
    'filesystem_stdio.wasm': ENGINE + 'filesystem_stdio.wasm',
    '/rodir/filesystem_stdio.wasm': ENGINE + 'filesystem_stdio.wasm',
    'libref_webgl2.wasm': ENGINE + 'libref_webgl2.wasm',
    'cl_dlls/menu_emscripten_wasm32.wasm': CS + 'cl_dlls/menu_emscripten_wasm32.wasm',
    'cl_dlls/client_emscripten_wasm32.wasm': CS + 'cl_dlls/client_emscripten_wasm32.wasm',
    'dlls/cs_emscripten_wasm32.wasm': CS + 'dlls/cs_emscripten_wasm32.wasm',
    'extras.pk3': CS + 'extras.pk3'
  };

  async function checkRuntime() {
    try {
      if (!window.Xash3D || !window.JSZip) throw new Error('Biblioteca do motor/ZIP não carregou. Verifique a conexão com jsDelivr.');
      const urls = [...new Set(Object.values(runtimeFiles))];
      await Promise.all(urls.map(async (url) => {
        const response = await fetch(url, { method: 'HEAD' });
        if (!response.ok) throw new Error(`Não foi possível obter ${url.split('/').pop()} (${response.status})`);
      }));
      engineReady = true;
      status.textContent = 'Motor e módulos CS disponíveis. Selecione o ZIP dos assets.';
      refresh();
    } catch (error) {
      status.textContent = `Falha ao preparar o motor: ${error.message}`;
      console.error(error);
    }
  }

  function refresh() { button.disabled = busy || !engineReady || !gameZip; }

  zipInput.addEventListener('change', async () => {
    const file = zipInput.files && zipInput.files[0];
    if (!file) return;
    busy = true;
    refresh();
    status.textContent = `Abrindo ZIP (${(file.size / 1048576).toFixed(0)} MiB)…`;
    try {
      const zip = await JSZip.loadAsync(file);
      const names = Object.keys(zip.files);
      const has = (path) => names.some((name) => name.toLowerCase() === path.toLowerCase());
      if (!has('cstrike/maps/de_dust2.bsp')) throw new Error('O ZIP precisa conter cstrike/maps/de_dust2.bsp. Use o script de preparação.');
      if (!names.some((name) => /^valve\//i.test(name))) throw new Error('O ZIP precisa conter as pastas valve/ e cstrike/.');
      gameZip = zip;
      status.textContent = `Assets prontos (${names.length} entradas). Ao iniciar, os arquivos serão carregados na memória.`;
    } catch (error) {
      gameZip = null;
      status.textContent = `ZIP inválido: ${error.message}`;
    } finally {
      busy = false;
      refresh();
    }
  });

  $('fullscreen').addEventListener('click', () => $('canvas').requestFullscreen?.());

  button.addEventListener('click', async () => {
    if (busy || !engineReady || !gameZip) return;
    busy = true;
    refresh();
    $('setup').hidden = true;
    $('game').hidden = false;
    status.textContent = 'Carregando arquivos de jogo…';
    const canvas = $('canvas');
    const files = {};
    try {
      await Promise.all(Object.keys(gameZip.files).map(async (name) => {
        const entry = gameZip.files[name];
        if (!entry.dir) files[`/rodir/${name}`] = await entry.async('uint8array');
      }));
      status.textContent = `Inicializando Xash3D (${Object.keys(files).length} arquivos)…`;
      const extraResponse = await fetch(CS + 'extras.pk3');
      if (!extraResponse.ok) throw new Error(`extras.pk3: HTTP ${extraResponse.status}`);
      files['/rodir/cstrike/extras.pk3'] = new Uint8Array(await extraResponse.arrayBuffer());
      window.Xash3D({
        arguments: ['-windowed', '-nosound', '-game', 'cstrike', '-ref', 'webgl2', '+_vgui_menus', '0', '+map', 'de_dust2', '+jointeam', '1', '+joinclass', '5'],
        canvas,
        ctx: canvas.getContext('webgl2', { alpha: false, depth: true, stencil: true, antialias: false, powerPreference: 'low-power' }),
        dynamicLibraries: [
          'filesystem_stdio.wasm', 'libref_webgl2.wasm',
          'cl_dlls/menu_emscripten_wasm32.wasm',
          'dlls/cs_emscripten_wasm32.wasm',
          'cl_dlls/client_emscripten_wasm32.wasm', '/rodir/filesystem_stdio.wasm'
        ],
        onRuntimeInitialized: function () {
          for (const [path, data] of Object.entries(files)) {
            const dir = path.split('/').slice(0, -1).join('/');
            this.FS.mkdirTree(dir);
            this.FS.writeFile(path, data);
          }
          this.FS.mkdirTree('/rwdir');
          this.FS.chdir('/rodir');
          if (new URLSearchParams(window.location.search).has('trace-assets')) {
            const fs = this.FS;
            const originalOpen = fs.open.bind(fs);
            fs.open = (path, ...args) => {
              const result = originalOpen(path, ...args);
              if (typeof path === 'string' && path.startsWith('/rodir/')) console.info('[XASH_ASSET]', path.slice(7));
              return result;
            };
          }
          status.textContent = 'Arquivos montados. Entrando em de_dust2…';
        },
        locateFile: (path) => runtimeFiles[path] || path,
        print: (line) => { console.log('[Xash]', line); if (/de_dust2|Host_InitError|couldn't|could not load/i.test(line)) status.textContent = line; },
        printErr: (line) => { console.error('[Xash]', line); status.textContent = line; }
      });
    } catch (error) {
      console.error(error);
      status.textContent = `Não foi possível iniciar o jogo: ${error.message}`;
      $('setup').hidden = false;
      $('game').hidden = true;
      busy = false;
      refresh();
    }
  });

  checkRuntime();
})();
