import React, { useState } from 'react';
import { Modal, Form, Input, Button, Table, Tag, message, Alert } from 'antd';
import { useUserTokens, useCreateApiToken, useRevokeApiToken } from '../../api/queries';
import { Key, Copy, Check, Trash2, Plus, ShieldAlert } from 'lucide-react';
import { ApiToken } from '../../types';

interface ApiTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ApiTokenModal: React.FC<ApiTokenModalProps> = ({ isOpen, onClose }) => {
  const { data: tokens, isLoading } = useUserTokens();
  const createMutation = useCreateApiToken();
  const revokeMutation = useRevokeApiToken();

  const [form] = Form.useForm();
  const [createdRawToken, setCreatedRawToken] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  const handleCreate = async (values: any) => {
    try {
      const res: any = await createMutation.mutateAsync({ name: values.name.trim() });
      if (res?.raw_token) {
        setCreatedRawToken(res.raw_token);
      }
      message.success('API token generated');
      form.resetFields();
    } catch {
      message.error('Failed to create API token');
    }
  };

  const handleRevoke = async (tokenId: number) => {
    try {
      await revokeMutation.mutateAsync(tokenId);
      message.success('API token revoked');
    } catch {
      message.error('Failed to revoke API token');
    }
  };

  const handleCopyRawToken = () => {
    navigator.clipboard.writeText(createdRawToken);
    setCopied(true);
    message.success('Token copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const columns = [
    {
      title: 'Token Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <span className="font-semibold text-slate-200">{text}</span>,
    },
    {
      title: 'Prefix',
      dataIndex: 'token_prefix',
      key: 'token_prefix',
      render: (prefix: string) => (
        <span className="font-mono text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
          {prefix}...
        </span>
      ),
    },
    {
      title: 'Token',
      key: 'copy_token',
      render: (_: any, record: ApiToken) => {
        const isNewToken = createdRawToken && createdRawToken.startsWith(record.token_prefix);
        if (isNewToken) {
          return (
            <Button
              type="primary"
              ghost
              size="small"
              icon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              onClick={handleCopyRawToken}
              className="border-blue-500/40 text-blue-400 text-[10px] h-7 px-2.5 rounded-lg flex items-center gap-1 hover:border-blue-400"
            >
              {copied ? 'Copied' : 'Copy'}
            </Button>
          );
        }
        return (
          <span className="text-[10px] text-slate-500 italic font-mono select-none">
            [Hashed]
          </span>
        );
      }
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => <span className="text-xs text-slate-400">{new Date(date).toLocaleDateString()}</span>,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: ApiToken) => (
        <Button
          type="text"
          danger
          size="small"
          icon={<Trash2 className="w-3.5 h-3.5 text-rose-400" />}
          onClick={() => handleRevoke(record.id)}
        >
          Revoke
        </Button>
      ),
    },
  ];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <Key className="w-5 h-5 text-blue-400" />
          <span>Personal API & CI/CD Access Tokens</span>
        </div>
      }
      open={isOpen}
      onCancel={() => {
        setCreatedRawToken('');
        onClose();
      }}
      width={680}
      footer={[
        <Button
          key="close"
          onClick={() => {
            setCreatedRawToken('');
            onClose();
          }}
          className="border-slate-700 text-slate-300"
        >
          Done
        </Button>,
      ]}
    >
      <div className="space-y-6 pt-2">
        <p className="text-xs text-slate-400">
          API tokens can be used for automated CI/CD authentication in Maven <code>settings.xml</code>, NPM <code>.npmrc</code>, Docker CLI, and Twine/Pip.
        </p>

        {/* Display New Token Banner */}
        {createdRawToken && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Copy your new API token now. You will not be able to see it again!</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#070b14] border border-amber-500/30">
              <span className="font-mono text-xs text-amber-200 select-all break-all">{createdRawToken}</span>
              <Button
                type="primary"
                size="small"
                icon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                onClick={handleCopyRawToken}
                className="bg-amber-600 hover:bg-amber-500 border-none shrink-0 ml-2"
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
          </div>
        )}

        {/* Generate Token Form */}
        <Form
          form={form}
          layout="inline"
          onFinish={handleCreate}
          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-3"
        >
          <Form.Item
            name="name"
            rules={[{ required: true, message: 'Token name is required' }]}
            className="flex-1 mb-0"
          >
            <Input placeholder="e.g., github-actions-deployer, macbook-local" className="text-xs" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={<Plus className="w-4 h-4" />}
            loading={createMutation.isPending}
            className="bg-blue-600 hover:bg-blue-500 border-none flex items-center gap-1 text-xs"
          >
            Generate Token
          </Button>
        </Form>

        {/* Existing Tokens Table */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-300">Active API Tokens</h4>
          <Table
            dataSource={tokens || []}
            columns={columns}
            rowKey="id"
            loading={isLoading}
            pagination={false}
            size="small"
            className="border border-slate-800 rounded-xl overflow-hidden"
          />
        </div>
      </div>
    </Modal>
  );
};
