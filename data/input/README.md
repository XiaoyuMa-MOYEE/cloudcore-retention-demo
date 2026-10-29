# Input Data / 输入数据

Place the upstream `high_risk_customers.csv` here for local runs. The application must validate the exact input contract read-only and must not modify the source file.

本地运行时可将上游 `high_risk_customers.csv` 放在此处。程序必须只读验证输入契约，不得修改源文件。

Do not commit real course/customer data. Synthetic fixtures belong in `tests/fixtures/`.

请勿提交真实课程/客户数据。合成测试样本应放在 `tests/fixtures/`。

`模拟数据.csv` is the explicitly synthetic 45-row demo dataset supplied for initial development. It is the only input CSV permitted in Git and the only dataset eligible for Azure processing by default; the server verifies its SHA-256 before each live analysis.

用户提供的 `模拟数据.csv` 是明确标记的 45 行合成演示数据，是唯一允许进入 Git 的输入 CSV，也是默认唯一可提交 Azure 分析的文件；服务端每次分析前校验其 SHA-256。
