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
- **Skill em "hold"** — mantém uma tecla/botão pressionado (ataque básico/canalizado).
- **Detecção de cooldown** (⚙ por skill) — só dispara quando o ícone está pronto.
- **Cast condicional** (⚙ por skill) — dispara só quando vida/recurso está acima/abaixo de X%.
- **Combo / sequência** — rotação ordenada com delay por passo (build rotation), com loop.
- **Auto-poção** — lê uma região da barra de vida e usa poção quando a vida cai
  abaixo de um limite (com cooldown). Há um 2º watcher para **recurso/mana**.
- **Jitter de tempo** — variação aleatória nos intervalos (ritmo menos robótico).
- **Foreground-gating** — só envia input quando a janela-alvo está em foco.
- **System tray** — minimizar para a bandeja; troca de perfil por hotkey global.
- **Preview de regiões** — mostra na tela os retângulos das regiões configuradas.
- **Perfis** — salve/carregue configurações por jogo (JSON). Vem com um perfil
  de exemplo para Diablo.
- **Hotkey global** — liga/desliga o macro mesmo com o jogo em foco (padrão `F8`).
- **Tecla de pânico** — para tudo imediatamente (padrão `F9`).
- **Overlay de status** — janelinha sempre-no-topo com ON/OFF, vida, recurso e
  estatísticas (casts, poções, uptime).
- **Multi-monitor** — a captura de região funciona em qualquer monitor.
- **Auto-update** — verifica novas versões no GitHub, **valida o SHA256** e
  instala com um clique.

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
5. **Opções:** botão **Opções** → iniciar minimizado, overlay de status, log em
   arquivo e **tecla de pânico** (padrão `F9`, para tudo na hora).

Perfis ficam em `<repo>/profiles` no modo desenvolvimento e em
`%APPDATA%\Praxis\profiles` quando instalado (junto com `settings.json`).

## Testes & qualidade

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

O workflow `.github/workflows/ci.yml` roda `ruff` + `pytest` a cada push/PR.

## Build a partir do código

```bash
pip install -r requirements.txt pyinstaller
python tools/make_icon.py     # gera assets/icon.ico
python tools/build.py         # gera dist/Praxis.exe
```

Para o instalador, instale o [Inno Setup](https://jrsoftware.org/isinfo.php)
(`winget install -e --id JRSoftware.InnoSetup`) e compile:

```bash
python tools/build_installer.py   # lê a versão da fonte única e chama o ISCC
```

O instalador exige elevação (UAC) e instala em **`C:\Program Files\Praxis`**
(para todos os usuários). Os perfis ficam em `%APPDATA%\Praxis\profiles`.

## Versionamento

O projeto segue [SemVer](https://semver.org/lang/pt-BR/). A versão tem **fonte
única** em `praxis/__init__.py` (`__version__`) e é consumida pelo app, pelo
instalador e pelos releases. Para subir a versão use o script de bump:

```bash
python tools/bump_version.py patch        # 0.1.0 -> 0.1.1
python tools/bump_version.py minor        # 0.1.0 -> 0.2.0
python tools/bump_version.py major        # 0.1.0 -> 1.0.0
python tools/bump_version.py 1.4.2        # versão explícita
python tools/bump_version.py patch --dry-run     # só simula
```

Ele atualiza `__version__` e o `CHANGELOG.md` (move "Não lançado" para a nova
versão). Com `--git` cria commit + tag; com `--push` também envia (o que dispara
o CI a publicar o release).

## Releases & auto-update

Cada tag `vX.Y.Z` enviada ao GitHub dispara o workflow de CI
(`.github/workflows/release.yml`), que builda o instalador e o publica como
Release. O app verifica essa API na inicialização e oferece a atualização.

Fluxo recomendado de lançamento:

```bash
python tools/bump_version.py minor --git --push
```

## Estrutura

```
praxis/        # pacote do app (gui, engine, sender, screen, config, updater, overlay, ...)
tests/         # testes pytest (models, updater, config)
profiles/      # perfis JSON (inclui diablo.json)
tools/         # make_icon.py, build.py, build_installer.py, bump_version.py
installer/     # praxis.iss (Inno Setup)
assets/        # icon.ico
run.py         # ponto de entrada
```

## Licença

[MIT](LICENSE).
