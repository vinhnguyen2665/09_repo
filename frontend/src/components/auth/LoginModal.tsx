import React, { useState } from 'react';
import { Modal, Form, Input, Button, message, Alert } from 'antd';
import { useAuth } from '../../context/AuthContext';
import apiClient from '../../api/client';
import { TokenResponse } from '../../types';
import { LogIn, Lock, User, Server } from 'lucide-react';

export const LoginModal: React.FC = () => {
  const { isLoginModalOpen, closeLoginModal, login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleFinish = async (values: any) => {
    setLoading(true);
    setErrorMsg('');
    try {
      const { data } = await apiClient.post<TokenResponse>('/auth/login', {
        username: values.username.trim(),
        password: values.password,
      });
      login(data.access_token, data.user);
      message.success(`Welcome back, ${data.user.username}!`);
      closeLoginModal();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={isLoginModalOpen}
      onCancel={closeLoginModal}
      footer={null}
      width={420}
      centered
    >
      <div className="py-4 space-y-6">
        {/* Title & Logo */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center mx-auto shadow-lg shadow-blue-500/20">
            <Server className="w-6 h-6 text-white" />
          </div>
          <h3 className="text-xl font-bold text-slate-100">Sign in to Zero9Repo</h3>
          <p className="text-xs text-slate-400">Enterprise Registry Management & Package Deployment</p>
        </div>

        {errorMsg && (
          <Alert message={errorMsg} type="error" showIcon className="text-xs bg-rose-950/40 border-rose-500/30" />
        )}

        <Form
          layout="vertical"
          onFinish={handleFinish}
          initialValues={{ username: 'admin', password: 'admin123' }}
          className="space-y-4"
        >
          <Form.Item
            name="username"
            label={<span className="text-xs font-semibold text-slate-300">Username</span>}
            rules={[{ required: true, message: 'Please enter your username' }]}
          >
            <Input
              prefix={<User className="w-4 h-4 text-slate-500" />}
              placeholder="Username"
              className="text-xs"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label={<span className="text-xs font-semibold text-slate-300">Password</span>}
            rules={[{ required: true, message: 'Please enter your password' }]}
          >
            <Input.Password
              prefix={<Lock className="w-4 h-4 text-slate-500" />}
              placeholder="Password"
              className="text-xs"
            />
          </Form.Item>

          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 space-y-1 font-mono">
            <span className="text-slate-300 font-semibold block">Default Admin Credentials:</span>
            <div>Username: <strong className="text-blue-400">admin</strong></div>
            <div>Password: <strong className="text-blue-400">admin123</strong></div>
          </div>

          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<LogIn className="w-4 h-4" />}
            className="w-full bg-blue-600 hover:bg-blue-500 border-none font-semibold text-sm h-10 rounded-xl"
          >
            Sign In
          </Button>
        </Form>
      </div>
    </Modal>
  );
};
