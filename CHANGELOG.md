# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

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

[Não lançado]: https://github.com/Rakjsu/praxis/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Rakjsu/praxis/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Rakjsu/praxis/releases/tag/v0.1.0
