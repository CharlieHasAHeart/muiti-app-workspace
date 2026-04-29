# md2word

`md2word` 是一个通用 Markdown 到 Word (`.docx`) 转换工具，提供两个入口：

- CLI 命令行版本
- Web 页面版本

## 安装

```bash
uv sync
```

如需在虚拟环境中执行命令：

```bash
uv run md2word -i input.md -t template.docx -o output.docx
```

## CLI 版本

参数模式：

```bash
uv run md2word -i input.md -t template.docx -o output.docx
```

交互模式：

```bash
uv run md2word
```

## Web 版本

启动：

```bash
uv run python web_app.py
```

可通过环境变量指定内置模板路径（默认 `assets/reference.docx`）：

```bash
DOCX_TEMPLATE_PATH=assets/reference.docx uv run python web_app.py
```

默认监听：

- `http://127.0.0.1:8000`

页面上传：

- Markdown 文件
- `title` 占位符文本（可选）
- 模板由服务端环境变量 `DOCX_TEMPLATE_PATH` 指定，不允许前端上传

转换后浏览器直接下载结果文档。

## 模板要求

模板中需要有占位符：

- `{{main_content}}`
- `{{title}}`（可选，若模板使用了该字段）

## 示例

可使用 `test/docs_sample.md` 进行测试。

## 许可证

Apache-2.0

## Docker

构建并启动：

```bash
docker compose up --build
```

访问：

- `http://127.0.0.1:8000`

后台运行：

```bash
docker compose up -d --build
```

停止：

```bash
docker compose down
```
