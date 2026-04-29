# md2word

`md2word` 是一个通用 Markdown 到 Word (`.docx`) 转换工具，提供两个入口：

- CLI 命令行版本
- Web 页面版本

## 安装

```bash
pip install -e .
```

## CLI 版本

参数模式：

```bash
md2word -i input.md -t template.docx -o output.docx
```

交互模式：

```bash
md2word
```

## Web 版本

启动：

```bash
python3 web_app.py
```

默认监听：

- `http://127.0.0.1:8000`

页面上传：

- Markdown 文件
- Word 模板（`.docx`，可选；不传则使用 `assets/reference.docx`）
- `title` 占位符文本（可选）

转换后浏览器直接下载结果文档。

## 模板要求

模板中需要有占位符：

- `{{main_content}}`
- `{{title}}`（可选，若模板使用了该字段）

## 示例

可使用 `test/docs_sample.md` 进行测试。

## 许可证

Apache-2.0
