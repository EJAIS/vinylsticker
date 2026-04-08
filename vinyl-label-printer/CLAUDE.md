# Claude Code Project Instructions

## Language Rules
- All code comments: English
- README.md and all documentation files: English
- Commit messages: English
- Variable names, function names, class names: English
- All UI strings must be implemented bilingually (DE + EN), switchable during runtime by the language selector and maintained in i18n. See also existing i18n implementation.
- Log messages and error output: English

## Project Context
- Desktop app for printing 7" vinyl record labels
- Target platform: Windows 11 & Linux (Ubuntu/Debian-based)
- Stack: Python 3.10+, PyQt6, ReportLab, openpyxl, pyqtdarktheme

## Code Style
- Follow PEP 8
- Max line length: 100 characters
- Use type hints where possible

## Testing
- Test after each prompt: App must start and all existing features must remain functional

## Git
- Branch naming: feature/xyz, bugfix/xyz
- Commit messages: Conventional Commits format
  feat: add dark mode
  fix: correct country field in tracklist
  docs: update README
  chore: update requirements.txt
