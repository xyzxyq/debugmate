# Quick Task: DebugMate 交付源码打包

## 目标

生成一个可提交、可复核、可在 Windows + Python 3.13 环境重建运行的 DebugMate V0.1 源码包，并将打包规则、清单和验证结果纳入仓库。

## 范围

- 纳入 README、`pyproject.toml`、`.env.example`、源码、契约、知识库源文件、提示词、Dify DSL、脚本、测试、课程材料、运行证据和 PPT 工程源文件。
- 排除 `.git`、`.venv`、`.env`、API Key/Token、缓存、临时预览、备份目录和本地 Agent/GSD 内部文件。
- 生成 `deliverables/DebugMate-V0.1-source.zip` 与外部 `deliverables/source-package-manifest.json`。
- 对 ZIP 做完整性、禁止项、清单哈希、源码编译和核心导入验证。

## 验收

- ZIP 可被 Python `zipfile` 完整读取和解压。
- 压缩包包含根 README、安装入口、Dify DSL、知识库源文件、源码和测试。
- 压缩包不包含 `.env`、密钥、虚拟环境、Git 元数据或临时目录。
- 解压后的源码可被 Python 3.13 编译并导入，清单中的文件 SHA-256 全部匹配。
- 打包后工作区清洁，提交推送后本地与 `origin/master` 一致。
