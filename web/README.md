# React Demo / React 演示前端

React + TypeScript + Vite single-page application. It displays bundled synthetic data on load and calls the same-origin Python Worker only after the user selects **Run AI analysis**. There is no login or browser credential storage. Completed results stay in browser memory until the user downloads the CSV or leaves the page. / React + TypeScript + Vite 单页应用。打开时显示捆绑的模拟数据，只有用户点击 **Run AI analysis** 后才调用同源 Python Worker。不设登录，也不在浏览器保存凭证。分析结果在用户下载 CSV 或离开页面前暂存在浏览器内存。

```powershell
npm ci
npm test
npm run build
npm run deploy:check
```

The build script copies the non-secret YAML config and synthetic CSV into `public/` for Worker asset access. Production assets are `dist/`. / 构建脚本会将不含机密的 YAML 配置和模拟 CSV 复制到 `public/`，供 Worker 读取。正式静态资源位于 `dist/`。
