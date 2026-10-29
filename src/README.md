# Source Code / 源代码

This package implements local validation, deterministic policy decisions, analysis, minimal request preparation, and an Azure OpenAI Responses API adapter. The authorized synthetic-data smoke test and full batch run have succeeded; see the dated implementation record.

本包实现本地校验、确定性政策逻辑、内部分析、最小化请求准备和 Azure OpenAI Responses API 适配器。获准的合成数据单条测试和完整批处理均已成功；详见日期化实现记录。

Run from the project root with `python -m src.cli --input "data/input/模拟数据.csv" --dry-run`. For API validation, fill `AZURE_OPENAI_API_KEY` in `.env`, first run `python -m src.cli --input "data/input/模拟数据.csv" --live --synthetic-data --api-smoke`; after success, omit `--api-smoke` to process all records. Final `offers.csv` is published only when every message succeeds.

在项目根目录运行 `python -m src.cli --input "data/input/模拟数据.csv" --dry-run`。如需验证 API，在 `.env` 中填写 `AZURE_OPENAI_API_KEY`，先运行 `python -m src.cli --input "data/input/模拟数据.csv" --live --synthetic-data --api-smoke`；成功后去掉 `--api-smoke` 处理全部记录。仅当全部消息成功时才发布最终 `offers.csv`。
