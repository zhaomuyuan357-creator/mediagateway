import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// 开发环境启用 Mock 服务（无后端时模拟任务流程）
if (import.meta.env.DEV) {
  import('./lib/mockTaskService').then(({ enableMock }) => enableMock())
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
