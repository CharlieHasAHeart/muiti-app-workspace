#!/usr/bin/env python3
import os
import tempfile
from io import BytesIO
from flask import Flask, jsonify, render_template_string, request, send_file
from werkzeug.utils import secure_filename

from md2word import convert_markdown_to_docx

app = Flask(__name__)

DEFAULT_TEMPLATE = os.path.abspath("assets/reference.docx")
TEMPLATE_PATH_ENV = "DOCX_TEMPLATE_PATH"

HTML = """
<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>md2word Web</title>
  <style>
    :root {
      --bg-1: #f6fbff;
      --bg-2: #e8f3ff;
      --ink: #152238;
      --muted: #4b607d;
      --brand: #1261a6;
      --brand-hover: #0e4f87;
      --card: #ffffff;
      --line: #d6e5f5;
      --error: #b42318;
      --shadow: 0 8px 24px rgba(18, 97, 166, 0.12);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: \"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% -10%, #c9e6ff 0%, transparent 45%),
        radial-gradient(circle at 90% 0%, #d8efff 0%, transparent 35%),
        linear-gradient(180deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
    }

    .wrap {
      max-width: 920px;
      margin: 28px auto;
      padding: 0 16px 24px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0.5px;
    }

    .sub {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 14px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: var(--shadow);
      padding: 18px;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .row { margin: 10px 0; }

    label {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
      color: var(--muted);
      font-weight: 700;
    }

    input[type=\"text\"], input[type=\"file\"] {
      width: 100%;
      border: 1px solid #c3d8ee;
      border-radius: 10px;
      padding: 10px 12px;
      background: #fff;
      font-size: 14px;
    }

    .hint {
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }

    .actions {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
    }

    button {
      border: 0;
      border-radius: 10px;
      background: var(--brand);
      color: #fff;
      padding: 10px 16px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover { background: var(--brand-hover); }
    button:disabled { opacity: 0.65; cursor: not-allowed; }

    .msg {
      margin-top: 10px;
      font-size: 14px;
      color: var(--muted);
      min-height: 20px;
    }

    .msg.error { color: var(--error); }
    .preview {
      margin-top: 16px;
      border-top: 1px dashed var(--line);
      padding-top: 12px;
    }

    .preview pre {
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 260px;
      overflow: auto;
      background: #f8fbff;
      border: 1px solid #e0ecf8;
      border-radius: 10px;
      padding: 12px;
      margin: 8px 0 0;
      font-size: 13px;
      color: #1f2f48;
    }

    @media (max-width: 760px) {
      .grid { grid-template-columns: 1fr; }
      h1 { font-size: 24px; }
    }
  </style>
</head>
<body>
  <main class=\"wrap\">
    <h1>md2word Web</h1>
    <p class=\"sub\">上传 Markdown，填写占位符，生成并下载 Word 文档。</p>

    <section class=\"card\">
      <div class=\"grid\">
        <div class=\"row\">
          <label for=\"mdFile\">Markdown 文件</label>
          <input id=\"mdFile\" type=\"file\" accept=\".md,text/markdown,text/plain\" required />
        </div>
      </div>

      <div class=\"grid\">
        <div class=\"row\">
          <label for=\"title\">占位符 title</label>
          <input id=\"title\" type=\"text\" placeholder=\"例如：支付系统软件说明书\" />
        </div>

        <div class=\"row\">
          <label for=\"outputName\">输出文件名（可选）</label>
          <input id=\"outputName\" type=\"text\" placeholder=\"result.docx\" />
        </div>
      </div>

      <div class=\"actions\">
        <button id=\"generateBtn\" type=\"button\">生成 Word</button>
      </div>

      <div id=\"message\" class=\"msg\"></div>

      <div class=\"preview\">
        <label>Markdown 预览（原文）</label>
        <pre id=\"mdPreview\">尚未选择文件</pre>
      </div>
    </section>
  </main>

  <script>
    const mdFileInput = document.getElementById('mdFile');
    const titleInput = document.getElementById('title');
    const outputNameInput = document.getElementById('outputName');
    const generateBtn = document.getElementById('generateBtn');
    const messageEl = document.getElementById('message');
    const mdPreviewEl = document.getElementById('mdPreview');

    function setMessage(text, isError = false) {
      messageEl.textContent = text;
      messageEl.classList.toggle('error', isError);
    }

    mdFileInput.addEventListener('change', async () => {
      const file = mdFileInput.files && mdFileInput.files[0];
      if (!file) {
        mdPreviewEl.textContent = '尚未选择文件';
        return;
      }
      try {
        const text = await file.text();
        mdPreviewEl.textContent = text || '(空文件)';
      } catch (err) {
        mdPreviewEl.textContent = '读取失败';
      }
    });

    generateBtn.addEventListener('click', async () => {
      const mdFile = mdFileInput.files && mdFileInput.files[0];
      if (!mdFile) {
        setMessage('请先上传 Markdown 文件。', true);
        return;
      }

      setMessage('正在生成，请稍候...');
      generateBtn.disabled = true;

      try {
        const form = new FormData();
        form.append('md_file', mdFile);
        form.append('title', titleInput.value || '');
        form.append('output_name', outputNameInput.value || '');

        const response = await fetch('/api/generate', {
          method: 'POST',
          body: form,
        });

        if (!response.ok) {
          let errText = `请求失败（${response.status}）`;
          try {
            const data = await response.json();
            if (data && data.error) errText = data.error;
          } catch (_) {}
          throw new Error(errText);
        }

        const blob = await response.blob();
        const cd = response.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename=\"?([^\";]+)\"?/i);
        const filename = match ? decodeURIComponent(match[1]) : 'output.docx';

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        setMessage('生成成功，已开始下载。');
      } catch (err) {
        setMessage(`生成失败：${err.message || err}`, true);
      } finally {
        generateBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/api/generate")
def generate_docx():
    md_file = request.files.get("md_file")
    output_name = (request.form.get("output_name") or "").strip()
    title = (request.form.get("title") or "").strip()
    template_path = os.path.abspath(os.getenv(TEMPLATE_PATH_ENV, DEFAULT_TEMPLATE))

    if not md_file:
        return jsonify({"error": "缺少 Markdown 文件（md_file）"}), 400

    if not os.path.exists(template_path):
        return jsonify({"error": f"模板不存在，请检查 {TEMPLATE_PATH_ENV}: {template_path}"}), 400

    with tempfile.TemporaryDirectory(prefix="md2word_web_") as tmpdir:
        md_path = os.path.join(tmpdir, secure_filename(md_file.filename or "input.md"))
        md_file.save(md_path)

        if not output_name:
            base, _ = os.path.splitext(os.path.basename(md_path))
            output_name = f"{base}.docx"
        if not output_name.lower().endswith(".docx"):
            output_name += ".docx"
        output_name = secure_filename(output_name) or "output.docx"

        output_path = os.path.join(tmpdir, output_name)

        try:
            convert_markdown_to_docx(
                md_path=md_path,
                template_path=template_path,
                output_path=output_path,
                title=title,
            )
        except Exception as exc:
            return jsonify({"error": f"转换失败: {exc}"}), 500

        with open(output_path, "rb") as f:
            data = f.read()

    return send_file(
        BytesIO(data),
        as_attachment=True,
        download_name=output_name,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def main() -> None:
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    main()
