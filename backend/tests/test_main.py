from pathlib import Path

from fastapi.testclient import TestClient

from backend import main

client = TestClient(main.app)


def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_templates_returns_profiles():
    response = client.get('/api/md2word/templates')
    assert response.status_code == 200
    body = response.json()
    assert any(item['id'] == 'reference' for item in body)
    assert all('preview' in item for item in body)


def test_analyze_extracts_title_and_output_name():
    response = client.post(
        '/api/md2word/analyze',
        files={'markdown_file': ('demo.md', '# 测试标题\n\n正文'.encode('utf-8'), 'text/markdown')},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['title'] == '测试标题'
    assert body['header_title'] == '测试标题'
    assert body['output_name'] == 'demo.docx'


def test_convert_rejects_unknown_template():
    response = client.post(
        '/api/md2word/convert',
        data={'template_id': 'missing', 'title': '', 'header_title': '', 'output_name': 'demo'},
        files={'markdown_file': ('demo.md', b'# title', 'text/markdown')},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Unknown template id'


def test_convert_returns_docx(monkeypatch):
    def fake_convert_markdown_to_docx(md_path: str, template_path: str, output_path: str, title: str = ''):
        Path(output_path).write_bytes(b'fake-docx')
        return output_path

    monkeypatch.setattr(main, 'convert_markdown_to_docx', fake_convert_markdown_to_docx)

    response = client.post(
        '/api/md2word/convert',
        data={'template_id': 'reference', 'title': '封面', 'header_title': '', 'output_name': 'result'},
        files={'markdown_file': ('demo.md', b'# title', 'text/markdown')},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    assert response.content == b'fake-docx'
    assert 'filename="result.docx"' in response.headers['content-disposition']


def test_convert_appends_docx_extension(monkeypatch):
    def fake_convert_markdown_to_docx(md_path: str, template_path: str, output_path: str, title: str = ''):
        Path(output_path).write_bytes(b'fake-docx')
        return output_path

    monkeypatch.setattr(main, 'convert_markdown_to_docx', fake_convert_markdown_to_docx)

    response = client.post(
        '/api/md2word/convert',
        data={'template_id': 'reference', 'title': '', 'header_title': '', 'output_name': 'named-output'},
        files={'markdown_file': ('demo.md', b'# title', 'text/markdown')},
    )

    assert response.status_code == 200
    assert 'filename="named-output.docx"' in response.headers['content-disposition']


def test_convert_rejects_missing_template_file(monkeypatch):
    class MissingPath:
        def exists(self):
            return False

    missing_profile = type('MissingProfile', (), {
        'id': 'reference',
        'template_path': MissingPath(),
        'label': 'missing',
        'notes': '',
        'family': 'builtin',
        'variant': 'reference',
        'supports_cover': True,
        'supports_toc': True,
    })()

    monkeypatch.setattr(main, 'list_template_profiles', lambda: [missing_profile])

    response = client.post(
        '/api/md2word/convert',
        data={'template_id': 'reference', 'title': '', 'header_title': '', 'output_name': 'demo'},
        files={'markdown_file': ('demo.md', b'# title', 'text/markdown')},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Template file is missing'
