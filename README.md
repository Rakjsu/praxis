# Praxis

Suite de automação de input para jogos, em Python. Rotação de skills,
auto-poção por leitura de tela, perfis por jogo, hotkey global e auto-update
via GitHub.

> **Aviso legal.** Macros podem violar os Termos de Serviço de jogos online e
> resultar em banimento. O Praxis foi feito para uso pessoal, preferencialmente
> em jogos **single-player / offline**. Ele **não** implementa qualquer técnica
> de evasão de anti-cheat. Use por sua conta e risco.

## Recursos

- **Rotação de skills** — cada skill dispara uma tecla em um intervalo configurável.
- **Auto-poção** — lê uma região da barra de vida e usa poção quando a vida cai
  abaixo de um limite (com cooldown).
- **Perfis** — salve/carregue configurações por jogo (JSON). Vem com um perfil
  de exemplo para Diablo.
- **Hotkey global** — liga/desliga o macro mesmo com o jogo em foco (padrão `F8`).
- **Auto-update** — verifica novas versões no GitHub e instala com um clique.

## Instalação

### Opção 1 — Instalador (recomendado)
Baixe o `Praxis-Setup-x.y.z.exe` mais recente em
[Releases](https://github.com/Rakjsu/praxis/releases) e execute.

### Opção 2 — Rodar do código-fonte
Requer Python 3.10+.

```bash
pip install -r requirements.txt
python run.py
```

> Se o jogo roda como administrador, rode o Praxis como administrador também —
> senão o Windows bloqueia o envio de teclas para a janela do jogo.

## Uso

1. **Skills:** em "Rotação de Skills", defina tecla e intervalo (ms) de cada
   habilidade; marque "On".
2. **Auto-poção:** clique em **Selecionar região** e arraste sobre a barra de
   vida → **Detectar cor** captura a cor da vida → **Testar leitura** mostra o %
   atual. A poção dispara quando a vida cai abaixo do limite.
3. **Hotkey:** padrão `F8` liga/desliga; troque no campo e clique em
   **Aplicar hotkey**.
4. **Salvar:** grava o perfil. Você pode ter vários (um por jogo).

Perfis ficam em `<repo>/profiles` no modo desenvolvimento e em
`%APPDATA%\Praxis\profiles` quando instalado.

## Build a partir do código

```bash
pip install -r requirements.txt pyinstaller
python tools/make_icon.py     # gera assets/icon.ico
python tools/build.py         # gera dist/Praxis.exe
```

Para o instalador, instale o [Inno Setup](https://jrsoftware.org/isinfo.php)
(`winget install -e --id JRSoftware.InnoSetup`) e compile:

```bash
iscc installer/praxis.iss     # gera installer/Output/Praxis-Setup-x.y.z.exe
```

## Releases & auto-update

Cada tag `vX.Y.Z` enviada ao GitHub dispara o workflow de CI
(`.github/workflows/release.yml`), que builda o instalador e o publica como
Release. O app verifica essa API na inicialização e oferece a atualização.

Para lançar manualmente:

```bash
gh release create v0.1.0 installer/Output/Praxis-Setup-0.1.0.exe \
  --title "Praxis 0.1.0" --notes-file CHANGELOG.md
```

## Estrutura

```
praxis/        # pacote do app (gui, engine, sender, screen, config, updater, ...)
profiles/      # perfis JSON (inclui diablo.json)
tools/         # make_icon.py, build.py
installer/     # praxis.iss (Inno Setup)
assets/        # icon.ico
run.py         # ponto de entrada
```

## Licença

[MIT](LICENSE).
