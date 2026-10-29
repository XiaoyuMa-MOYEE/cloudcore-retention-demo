# Tests / 测试

This directory contains unit and integration tests. Synthetic records are generated in temporary directories; do not use real course/customer records or call paid external APIs in tests. Provider behavior is mocked.

此目录存放单元和集成测试。合成记录在临时目录中生成；不得使用真实课程/客户记录，也不得在测试中调用产生费用的外部 API。Provider 行为使用 mock。

Install development dependencies with `python -m pip install -r requirements-dev.txt`, then run `python -m pytest -q`. The suite covers the 16-row policy fixture, input validation, Playbook precedence, Azure request construction, allowlisted batching, output checks (including internal-workflow and process language), mock-provider retry/recovery, prompt-hash checkpoint invalidation, and governance gating.

使用 `python -m pip install -r requirements-dev.txt` 安装开发依赖，再运行 `python -m pytest -q`。测试覆盖 16 行政策夹具、输入校验、Playbook 优先级、Azure 请求构造、批次字段白名单、输出检查（包含内部工作流和流程用语）、mock Provider 重试/恢复、Prompt 哈希检查点失效和治理授权门槛。
