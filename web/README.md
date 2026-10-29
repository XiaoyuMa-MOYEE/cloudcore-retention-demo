# React Demo / React 演示前端

React + TypeScript + Vite single-page application. It stores no credentials in localStorage; `fetch` uses same-origin HttpOnly session cookies. The initial 45-row grid is synthetic and never starts an analysis until the user selects **Run AI analysis**. / React + TypeScript + Vite 单页应用。不使用 localStorage 保存密钥；接口请求使用同源 HttpOnly 会话 Cookie。初始 45 条记录均为模拟数据，用户点击 **Run AI analysis** 前不会发起模型调用。

```powershell
npm ci
npm run dev
npm test
npm run build
```

Vite proxies `/api` to local FastAPI at `127.0.0.1:8000`. Production static output is `dist/`; Cloudflare Pages settings are in `../docs/deployment/README.md`. / 本地开发由 Vite 将 `/api` 代理到 `127.0.0.1:8000`；生产输出为 `dist/`，Cloudflare Pages 配置见部署手册。
