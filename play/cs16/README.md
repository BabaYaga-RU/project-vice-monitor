# CS 1.6 no navegador: Xash3D + WebAssembly

Esta secao reutiliza builds WebAssembly publicados; nao compila a engine.

- Xash3D-FWGS WASM 1.2.2. Codigo e engine: https://github.com/sealdev224/webxash3d-fwgs-cstrike/tree/main/packages/xash3d-fwgs (MIT).
- CS16 client WASM 0.1.2. Pacote: https://github.com/sealdev224/webxash3d-fwgs-cstrike/tree/main/packages/cs16-client. O pacote npm declarou MIT; o codigo-fonte reverse-engineered relacionado esta em https://github.com/Velaron/cs16-client e traz GPL-2.0 com uma excecao de link para engine/mods Valve.
- Exemplo de pagina crua que orientou a integracao: `examples/raw-html-cs16` no monorepo acima; tambem comparado com https://github.com/modesage/cs1.6-browser.
- `cs16-web` (https://github.com/Elkhan-Isayev/cs16-web) tem gameplay real em de_dust2, mas sua pagina e bundle fazem parte de imagem Docker do servidor. Nao e a base usada.

`game.js` fixa os modulos pelo caminho e versao exata no jsDelivr. `cs16-client@0.1.2` foi despublicado do registro npm em setembro de 2026, mas o CDN ainda fornece os arquivos fixados e estes foram testados. Se o CDN purgar o cache, os arquivos precisam ser re-publicados pelo mantenedor ou compilados do codigo-fonte WebXash3D.

## Arquivos de jogo necessarios

E necessaria uma instalacao legitima do Counter-Strike 1.6, com estas duas pastas no ZIP:

```text
cstrike/  dados e codigo original do jogo, incluindo maps/de_dust2.bsp
valve/    dados base GoldSrc usados pelo jogo/engine
```

A pagina verifica que o BSP existe, mas a engine carrega outros dados dinamicamente. O client/server CS que roda no browser e um modulo WASM separado, baixado do pacote `cs16-client`; DLLs nativas da instalacao local nao sao o executavel WebAssembly.

## Build Lite

`tools/build-lite.ps1` gera a Lite v1. `tools/build-lite-v2.ps1` aplica tambem o manifesto de arquivos que o Xash abriu no teste local e remove modelos `.mdl` nao observados. Ambos leem o ZIP completo sem alterar a instalacao de origem e criam ZIPs locais ignorados pelo Git.

```powershell
& .\play\cs16\tools\build-lite-v2.ps1
```

Ou indique entrada/saida explicitamente:

```powershell
& .\play\cs16\tools\build-lite-v2.ps1 -InputZip .\play\cs16\user-content\cs16-assets.zip -OutputZip .\play\cs16\user-content\cs16-lite-v2.zip
```

O v2 le o lump de entidades do `cstrike/maps/de_dust2.bsp` (GoldSrc BSP30) para identificar WADs e consulta `tools/verified-access-v2.txt`, gerado pelo rastreamento de `FS.open` bem-sucedido no navegador. O manifesto contem so nomes de caminhos, nao assets. Um WAD fica se Dust2 o declara ou se o Xash o abriu; por isso `valve/gfx.wad` continua, pois apareceu no rastreamento. Modelos `.mdl` fora do manifesto sao removidos; sprites ficam intactos enquanto a exibicao/disparo de arma nao puder ser confirmada. WASM/engine nao entram no ZIP, e nenhuma textura e redimensionada ou convertida.

### Classificacao observada

Rastreamento de `FS.open` com sucesso durante a inicializacao single-player em Dust2, mais as dependencias declaradas pelo BSP. Ele nao representa cada acao/rodada futura nem substitui testes em outras versoes dos assets.

| Classificacao | Arquivos/conjuntos |
|---|---|
| REQUIRED | `cstrike/maps/de_dust2.bsp`; WADs declarados no worldspawn (`valve/halflife.wad`, `valve/decals.wad`, `cstrike/cs_dust.wad`); WADs abertos no teste (`cstrike/decals.wad`, `valve/gfx.wad`); 142 modelos `.mdl` e 80 sprites `.spr` no manifesto de acesso; dados observados do HUD, eventos e configs. Os modelos das familias de armas e jogadores vistos no rastreamento permanecem. |
| OPTIONAL | Sprites `.spr` nao vistos, mantidos por falta de um teste visual conclusivo de arma/efeitos; demais arquivos de configuracao e sidecar de Dust2 mantidos pelo filtro conservador. |
| NOT USED (neste rastreamento) | 360 modelos `.mdl` sem abertura bem-sucedida durante carregar o mapa e as entradas automatizadas; removidos no v2. Tambem removidos: audio, outros mapas, demos, video/media, logos/fundos, binarios nativos e WADs fora das referencias/acessos observados. Ausencia no rastreamento nao prova que um arquivo nunca e usado em outro mapa/acao. |

O teste automatizado carregou a Lite v2 pela interface, renderizou Dust2 e enviou WASD e movimento de mouse; a orientacao renderizada mudou. A imagem, porem, nao mostrou HUD completo nem arma. Foram enviados cliques esquerdos e comandos de troca/concessao de arma, mas nenhum disparo visual foi confirmado. Por isso a lista de sprites foi preservada e o v2 nao e declarado validado para combate.

### Medidas desta amostra local

Assets gerados a partir do App 90 do SteamCMD, apenas para teste local:

| Medida | Original | Lite v1 | Lite v2 |
|---|---:|---:|---:|
| Arquivos | 5.405 | 1.899 | 1.539 |
| ZIP | 784,93 MiB | 99,10 MiB | 83,76 MiB |
| Soma descompactada | 784,08 MiB | 184,52 MiB | 160,35 MiB |

O v2 reduziu o ZIP **89,3% frente ao original**, **15,5% frente a v1**. O payload caiu **79,5% frente ao original**. Em relacao a v1, foram retirados mais 360 modelos nao abertos, com 24,17 MiB descompactados, e a saida compactada diminuiu 15,34 MiB. Na reducao total tambem saem 2.955 arquivos/126,35 MiB de audio, mapas e sidecars, overviews, 26 WADs nao referenciados, 16 binarios nativos, demos, videos/media e recursos de menu. WADs de Dust2/Xash e modelos/sprites observados permanecem. Nenhuma medida de RAM e reportada.

### Distribuicao

O site continua aceitando um ZIP escolhido localmente. Uma hospedagem estatica pode servir bytes sem backend, mas nao concede direito de redistribuir conteudo proprietario. Por isso este repositorio nao hospeda assets. O jogador gera o ZIP a partir da propria instalacao legitima. Os ZIPs de teste ficam no `user-content/` local ignorado pelo Git.

## Preparar assets localmente no Windows

Abra PowerShell na raiz do repositorio e rode:

```powershell
.\play\cs16\tools\prepare-assets.ps1
```

O script procura uma instalacao Steam em `steamapps/common/Half-Life` ou `Counter-Strike`, incluindo bibliotecas adicionais listadas no `libraryfolders.vdf`. Se nao encontrar, informe a pasta que contem `cstrike` e `valve`:

```powershell
.\play\cs16\tools\prepare-assets.ps1 -GameFiles 'C:\caminho\para\Half-Life'
```

Ele copia as duas pastas sem alterar a instalacao e gera `play/cs16/user-content/cs16-assets.zip`. Esse ZIP e ignorado pelo Git. Nao o publique nem distribua: os assets pertencem a Valve. O browser abre o arquivo local, conserva seus bytes na memoria e nao os envia para rede.

## Executar localmente

Na raiz do repositorio:

```powershell
python -m http.server 8000
```

Abra `http://localhost:8000/play/cs16/`, escolha `play/cs16/user-content/cs16-lite-v2.zip` e clique em **Iniciar em de_dust2**. O site baixa os binarios fixados do CDN, monta `valve/` e `cstrike/` no filesystem em memoria do WASM, e executa `map de_dust2`. Clique no canvas para capturar o mouse.

## GitHub Pages

Publique o conteudo normal do repositorio. O Pages serve HTML, CSS e JS. O ZIP pessoal nao faz parte do site; cada jogador prepara/selecione seus proprios assets. Nao ha backend ou processo de jogo no Pages. O engine e os modulos CS vem do CDN externo jsDelivr em versoes fixas, entao a primeira carga requer internet. A verificacao foi feita em Edge local e mostrou o interior de de_dust2 renderizado.

O cliente inicia com `-nosound`. Edge/SwiftShader carregou o ZIP v2 pela interface e renderizou Dust2; a camera respondeu a entradas WASD/mouse. O teste nao comprovou spawn com HUD, arma visivel ou disparo; esses pontos seguem pendentes antes de considerar combate funcional. A pagina mostrou um 404 de favicon e um aviso WebGL `INVALID_ENUM`, sem erro fatal de carregamento do mapa. A RAM nao foi medida.
