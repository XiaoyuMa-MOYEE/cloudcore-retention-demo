# Provider Architecture / Provider 架构

Provider adapter hides vendor-specific request details from pipeline logic. The initial implementation may use an OpenAI API provider; another OpenAI-compatible provider can be added behind the same contract.

Provider 适配器将供应商请求细节与流水线逻辑隔离。首版可使用 OpenAI API，后续可在同一接口后增加其他 OpenAI 兼容提供商。

## Contract / 接口约定

- Input: batch-local IDs and only approved allowlisted context, including the selected offer code.
- 输入：批次内 ID，以及包含选定 Offer 代码的允许字段上下文。
- Output: structured JSON containing one message per requested ID; provider output never supplies final offer or reason.
- 输出：每个请求 ID 对应一条消息的结构化 JSON；Provider 不提供最终 Offer 或 Reason。
- Configuration: provider, model, base URL when supported, timeout, retries, and API key environment-variable name.
- 配置：provider、模型、支持时的 base URL、超时、重试次数和 API 密钥环境变量名。
- Never log credentials or full sensitive request bodies.
- 不得记录凭据或完整敏感请求正文。

The current adapter is `OpenAIResponsesProvider`, configured for Azure OpenAI v1 or another OpenAI-compatible Responses endpoint. It submits structured JSON output and disables response storage. No local-model adapter is implemented.

当前适配器为 `OpenAIResponsesProvider`，可配置 Azure OpenAI v1 或其他 OpenAI 兼容 Responses endpoint。请求采用结构化 JSON 输出并关闭响应存储。目前未实现本地模型适配器。
