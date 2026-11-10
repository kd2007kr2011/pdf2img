# pdf2img

使用 PDFium 将 PDF 的每一页渲染为高清 PNG，并按原页序重新生成纯图片 PDF。PDFium 能较好地处理内嵌字体和子集字体，可减少错字、缺字和数字变形问题。

## 功能

- 一次处理一个指定的 PDF。
- 按页输出 PNG 图片。
- 可选择是否保留 PNG。
- 可选择是否生成图片版 PDF。
- 可选择是否在生成的 PDF 末尾追加指定的另一份 PDF（例如简历第二页）。
- 每个源 PDF 使用独立的图片和 PDF 输出文件夹。
- `input/` 和 `output/` 不会提交到 GitHub。

## 安装

需要 Python 3.10 或更高版本。

```bash
python -m venv .venv
```

Windows：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS 或 Linux：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 配置

编辑项目根目录下的 `config.json`：

```json
{
  "input_dir": "input",
  "input_pdf": "example.pdf",
  "images_dir": "output/images",
  "merged_pdf_dir": "output/merged_pdfs",
  "dpi": 300,
  "save_images": true,
  "merge_pdf": true,
  "append_pdf": "简历第二页.pdf",
  "append_pdf_enabled": true
}
```

配置项说明：

- `input_dir`：存放待转换 PDF 的目录。
- `input_pdf`：需要转换的 PDF 文件名，例如 `example.pdf`。
- `images_dir`：逐页图片的输出根目录。
- `merged_pdf_dir`：图片版 PDF 的输出根目录。
- `dpi`：渲染清晰度，推荐 200-300。
- `save_images`：是否永久保存逐页 PNG。
- `merge_pdf`：是否生成图片版 PDF。
- `append_pdf`：要追加到生成 PDF 末尾的 PDF 文件名（相对于 `input_dir`，也可以写绝对路径），留空表示不追加。
- `append_pdf_enabled`：是否追加 `append_pdf` 指定的 PDF，设为 `false` 即可关闭追加。

`save_images` 和 `merge_pdf` 不能同时设置为 `false`。

如果 `input_pdf` 留空，程序会自动处理 `input_dir` 中唯一的 PDF；如果目录里有多个 PDF，程序会停止并要求明确指定文件名。

## 使用

将一个 PDF 放入 `input/`，并在 `config.json` 中填写其文件名：

```text
input/
└── example.pdf
```

运行：

```bash
python pdf2img.py
```

Windows 用户也可以双击 `pdf2img.cmd`。

还可以直接指定 PDF 路径：

```bash
python pdf2img.py example.pdf
```

## 输出结构

默认配置的输出如下：

```text
output/
├── images/
│   └── example/
│       └── 300dpi/
│           ├── page_0001.png
│           ├── page_0002.png
│           └── ...
└── merged_pdfs/
    └── example/
        └── example_image_300dpi.pdf
```

图片文件名使用补零页码，因此按文件名排序时与原 PDF 页序一致。

## GitHub

`.gitignore` 已忽略以下运行数据：

```gitignore
input/
output/
```

仓库中的 `exampleinput/` 提供输入目录和配置示例。

## 注意事项

- DPI 越高，输出越清晰，文件也越大。
- 图片版 PDF 不保留原文件的书签、链接、表单、附件或可搜索文本层。
- 追加的 PDF 在 `merge_pdf` 为 `true` 时生效，且会保留原文件自身的文字与矢量内容。
- 请只处理你有权使用的 PDF 文件。

## License

[MIT](LICENSE)
