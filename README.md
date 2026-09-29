# Lab

Site estático com duas áreas:

- `/study/` reúne as matérias, documentos e simuladores.
- `/play/` reúne jogos; o CS 1.6 para navegador fica em `/play/cs16/`.

Para servir localmente, execute `python -m http.server 8000` na raiz deste repositório e abra `http://localhost:8000/`.

O CS usa Xash3D/WebAssembly. Seus assets devem ser preparados localmente a partir de uma instalação legítima; os ZIPs e arquivos de jogo ficam ignorados pelo Git. Consulte [as instruções do CS](play/cs16/README.md).
