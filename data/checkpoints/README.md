# Checkpoints / 检查点

Store resumable batch state here. A checkpoint is reusable only when the input digest, prompt version, provider/model, and applicable record identity signatures match. Use atomic writes where practical; never include API keys or sensitive request bodies.

在此保存可恢复的批次状态。只有输入摘要、提示词版本、provider/model 及适用记录身份签名一致时，才能复用检查点。尽量采用原子写入；不得包含 API 密钥或敏感请求正文。

Checkpoint files are runtime artifacts and must not be committed.

检查点属于运行产物，不应提交到版本库。
