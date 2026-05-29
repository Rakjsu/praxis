# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.4.0] - 2026-05-28
### Adicionado
- **Detecção de cooldown por ícone** (⚙ por skill): só dispara quando a skill
  está pronta na tela.
- **Cast condicional**: skill dispara só quando vida/recurso está acima/abaixo
  de X%.
- **System tray** (pystray): minimizar para a bandeja com menu Mostrar/Toggle/Sair.
- **Troca de perfil por hotkey** global.
- **Preview de regiões**: mostra na tela os retângulos das regiões configuradas.
- Testes do motor (condição/cooldown) no CI.
### Alterado
- O motor passa a **ler a barra de vida/recurso mesmo com a auto-poção
  desligada** (desacopla leitura de uso), alimentando as condições de cast.

## [0.3.0] - 2026-05-28
### Adicionado
- **Combo/sequência** ordenada com delay por passo e loop (build rotation).
- **Skill em "hold"**: mantém tecla/botão pressionado (ataque básico/canalizado).
- **Auto-poção de recurso/mana**: 2º watcher de cor além da vida.
- **Jitter de tempo** por perfil nos intervalos de skill e passos do combo.
- **Foreground-gating**: só envia input quando a janela-alvo está em foco.
- **Painel de stats** (casts, poções, uptime) no overlay.
### Alterado
- UI com corpo rolável; seção de poção reutilizável para vida e recurso.

## [0.2.0] - 2026-05-28
### Adicionado
- Suíte de testes (pytest) e CI de qualidade (`ruff` + `pytest`) em push/PR.
- Overlay de status sempre-no-topo (ON/OFF + vida lida).
- Painel de Opções: iniciar minimizado, log em arquivo e **tecla de pânico**
  (padrão `F9`, para tudo na hora).
- Captura de tela multi-monitor (seleção de região em qualquer monitor).
### Alterado
- Auto-update agora **verifica o SHA256** do instalador antes de executar; o
  release passa a publicar o arquivo `.exe.sha256`.

## [0.1.1] - 2026-05-28
### Adicionado
- Sistema de versionamento SemVer com fonte única (`praxis/__init__.py`):
  `tools/bump_version.py` (bump major/minor/patch/X.Y.Z + CHANGELOG + git tag).
- `tools/build_installer.py`: compila o instalador passando a versão automaticamente.
### Alterado
- Instalador agora exige elevação (UAC) e instala em `C:\Program Files\Praxis`
  para todos os usuários (`PrivilegesRequired=admin`).

## [0.1.0] - 2026-05-28
### Adicionado
- Rotação de skills configurável (tecla + intervalo por habilidade).
- Auto-poção por leitura da barra de vida na tela (seleção visual de região,
  detecção de cor, limite percentual e cooldown).
- Sistema de perfis por jogo (salvar/carregar/excluir em JSON), com perfil
  padrão para Diablo.
- Hotkey global de liga/desliga (padrão `F8`).
- Envio de input via SendInput (scancodes) compatível com jogos.
- Auto-update via GitHub Releases (checagem na inicialização + botão manual).
- Instalador `.exe` (Inno Setup) e build de executável portátil (PyInstaller).
- Ícone próprio do app.

[Não lançado]: https://github.com/Rakjsu/praxis/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Rakjsu/praxis/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Rakjsu/praxis/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Rakjsu/praxis/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/Rakjsu/praxis/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Rakjsu/praxis/releases/tag/v0.1.0
