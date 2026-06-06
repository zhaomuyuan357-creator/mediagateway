import { useState } from 'react';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';

function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  return (
    <div className="relative w-screen h-screen bg-slate-950 overflow-hidden">
      {/* 渐变光晕背景 */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-900/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-900/20 rounded-full blur-3xl animate-pulse" />

      {/* 登录卡片 */}
      <div className="relative z-10 flex items-center justify-center w-full h-full">
        <Card className="w-[380px] p-6 backdrop-blur-md bg-slate-900/60 border border-slate-700/50 rounded-2xl shadow-2xl">
          <h1 className="text-2xl font-bold text-center text-white mb-6">
            LumenRoute AI
          </h1>

          <Tabs value={mode} onValueChange={(v) => setMode(v as 'login' | 'register')}>
            <TabsList className="w-full">
              <TabsTrigger value="login">登录</TabsTrigger>
              <TabsTrigger value="register">注册</TabsTrigger>
            </TabsList>
          </Tabs>

          <form className="space-y-4 mt-4" onSubmit={(e) => e.preventDefault()}>
            <Input
              type="email"
              placeholder="邮箱"
              className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
            />
            <Input
              type="password"
              placeholder="密码"
              className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500"
            />
            <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white">
              {mode === 'login' ? '登录' : '注册'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

export default Login;
