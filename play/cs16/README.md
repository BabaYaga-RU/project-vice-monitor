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

O script `tools/build-lite.ps1` recebe o ZIP completo criado por `prepare-assets.ps1` e escreve `play/cs16/user-content/cs16-lite.zip`. A origem nunca e alterada. O ZIP Lite e gerado localmente e ignorado pelo Git.

```powershell
& .\play\cs16\tools\build-lite.ps1
```

Ou indique entrada/saida explicitamente:

```powershell
& .\play\cs16\tools\build-lite.ps1 -InputZip .\play\cs16\user-content\cs16-assets.zip -OutputZip .\play\cs16\user-content\cs16-lite.zip
```

O filtro le o lump de entidades do `cstrike/maps/de_dust2.bsp` (GoldSrc BSP30) e mantem os WADs declarados pelo worldspawn. Alem deles, conserva `valve/gfx.wad`, dependencia base aberta pelo Xash no teste. Se o BSP nao declarar WADs, o script preserva todos os WADs por seguranca. WASM e engine nao entram no ZIP; texturas/modelos mantidos nao sao alterados nem redimensionados.

### Classificacao observada

Rastreamento de `FS.open` com sucesso durante a inicializacao single-player em Dust2, mais as dependencias declaradas pelo BSP. Ele nao representa cada acao/rodada futura nem substitui testes em outras versoes dos assets.

| Estado | Arquivos/conjuntos |
|---|---|
| Necessario | `cstrike/maps/de_dust2.bsp`; WADs `valve/halflife.wad`, `valve/decals.wad`, `cstrike/cs_dust.wad`; `valve/gfx.wad`; arquivos abertos sob `models/`, `sprites/`, `events/`, configs e recursos de idioma/HUD listados pelo rastreamento. Todos os modelos/sprites originais sao mantidos para preservar armas, HUD e compatibilidade. |
| Opcional, preservado | `cstrike/maps/de_dust2.res`, overview `de_dust2`, configs adicionais, outros modelos/sprites do CS nao observados nesta inicializacao. Alguns so podem ser necessarios em telas, armas, entidades ou acoes nao exercitadas no teste. |
| Nao utilizado no teste e removido | Audio (diretorios `sound/` e formatos comuns de audio), demos, media, sprays/logos, cache de downloads, addons, mapas BSP exceto Dust2, mapas/overviews do Half-Life, overviews de outros mapas, fundos/logos de menu e WADs que nao aparecem nas dependencias do BSP (exceto `gfx.wad`). Binarios nativos sao substituidos pelos modulos WASM do cliente. |

Isso e uma reducao conservadora por caminhos observados/declarados, nao uma afirmacao de que cada outro recurso foi provado impossivel de usar em todos os cenarios. Nao removemos modelos ou sprites por extensao, nem reduzimos texturas.

### Medidas desta amostra local

Assets gerados a partir do App 90 do SteamCMD, apenas para teste local:

| Medida | Original | Lite |
|---|---:|---:|
| Arquivos | 5.405 | 1.899 |
| ZIP | 784,93 MiB | 99,10 MiB |
| Soma descompactada | 784,08 MiB | 184,52 MiB |

Reducao do ZIP: **87,4%**. Reducao do payload: **76,5%**. Foram removidos 3.506 arquivos/599,56 MiB, principalmente audio (3.011 arquivos/126,35 MiB), mapas/sidecars e overviews (362/329,81 MiB), WADs nao referenciados (26/64,03 MiB), binarios nativos (16/43,86 MiB), media (4/10,18 MiB), logos/fundos (143/25,32 MiB) e outros itens menores.

### Distribuicao

O site continua aceitando um ZIP escolhido localmente. Uma hospedagem estatica pode servir bytes sem backend, mas nao concede direito de redistribuir conteudo proprietario. Por isso este repositorio nao hospeda nem baixa automaticamente WADs, mapas ou outros arquivos comerciais. O jogador gera o ZIP a partir de uma instalacao legitima. O ZIP Lite de teste tem 99,10 MiB, mas tamanho abaixo do limite tecnico de um host nao altera a licenca.

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

Abra `http://localhost:8000/play/cs16/`, escolha `play/cs16/user-content/cs16-assets.zip` e clique em **Iniciar em de_dust2**. O site baixa os binarios fixados do CDN, monta `valve/` e `cstrike/` no filesystem em memoria do WASM, inicia Xash3D e executa `map de_dust2`. O cliente entra na equipe Terrorista automaticamente. Clique no canvas para capturar o mouse.

## GitHub Pages

Publique o conteudo normal do repositorio. O Pages serve HTML, CSS e JS. O ZIP pessoal nao faz parte do site; cada jogador prepara/selecione seus proprios assets. Nao ha backend ou processo de jogo no Pages. O engine e os modulos CS vem do CDN externo jsDelivr em versoes fixas, entao a primeira carga requer internet. A verificacao foi feita em Edge local e mostrou o interior de de_dust2 renderizado.

O cliente inicia com `-nosound`; os arquivos de audio nao sao incluidos no ZIP Lite e Dust2 foi confirmado carregando nessa configuracao. O mapa e movimentacao foram testados localmente usando Edge/SwiftShader. Uma medicao de RAM antes/depois nao ficou comparavel: as execucoes do ZIP original excederam o tempo do navegador de automacao antes de disponibilizar o canvas. O processo carrega os arquivos extraidos na memoria do WASM, portanto reduzir o payload deve reduzir a memoria transitoria de montagem, mas nao registramos aqui uma porcentagem de RAM.
