# 输入示例

实际使用时，请把需要转换的一个 PDF 放到项目根目录的 `input` 文件夹中，例如：

```text
input/
└── example.pdf
```

然后在项目根目录的 `config.json` 中指定文件名：

```json
{
  "input_dir": "input",
  "input_pdf": "example.pdf"
}
```

如果 `input_pdf` 留空，程序会自动处理 `input` 中唯一的 PDF。

`input/` 和 `output/` 都已被 Git 忽略，里面的原始文件和转换结果不会上传到 GitHub。
