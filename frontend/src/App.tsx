import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Gallery from './pages/Gallery';
import Settings from './pages/Settings';
import Login from './pages/Login';
import TaskWorkspace from './pages/TaskWorkspace';
import { ErrorBoundary } from './components/ErrorBoundary';

/**
 * App.tsx — 路由配置（重构后）
 *
 * /login        → 登录页（独立全屏布局）
 * /             → 主工作台（TaskWorkspace）
 * /gallery/*    → 素材库
 * /settings     → 设置
 */

function App() {
  return (
    <Router>
      <Routes>
        {/* 登录页 — 独立全屏布局 */}
        <Route path="/login" element={<Login />} />

        {/* 主工作台 */}
        <Route path="/" element={<TaskWorkspace />} />

        {/* 素材库 */}
        <Route
          path="/gallery/*"
          element={
            <div className="min-h-screen bg-slate-950">
              <ErrorBoundary>
                <Gallery />
              </ErrorBoundary>
            </div>
          }
        />

        {/* 设置 */}
        <Route
          path="/settings"
          element={
            <div className="min-h-screen bg-slate-950">
              <ErrorBoundary>
                <Settings />
              </ErrorBoundary>
            </div>
          }
        />

        {/* 默认重定向到工作台 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
