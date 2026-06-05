from types import SimpleNamespace

from backend import main


def _decision(title_text: str = ''):
    return SimpleNamespace(heading_plan=SimpleNamespace(title_text=title_text))


def test_derive_title_prefers_decision_plan(monkeypatch):
    monkeypatch.setattr(main, 'build_decision_plan', lambda _md: _decision('计划标题'))
    assert main.derive_title('# 原始标题', 'demo.md') == '计划标题'


def test_derive_title_falls_back_to_markdown_heading(monkeypatch):
    monkeypatch.setattr(main, 'build_decision_plan', lambda _md: _decision(''))
    assert main.derive_title('# Markdown 标题\n\n内容', 'demo.md') == 'Markdown 标题'


def test_derive_title_falls_back_to_file_stem(monkeypatch):
    monkeypatch.setattr(main, 'build_decision_plan', lambda _md: _decision(''))
    assert main.derive_title('没有一级标题', 'fallback-name.md') == 'fallback-name'


def test_cleanup_temp_file_ignores_missing_file(tmp_path):
    missing = tmp_path / 'missing.docx'
    main.cleanup_temp_file(str(missing))
    assert not missing.exists()
