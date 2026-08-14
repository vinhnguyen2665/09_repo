import React, { useState } from 'react';
import { Modal, Form, Input, Radio, Select, InputNumber, Button, Switch, message, Tag } from 'antd';
import { useCreateRepository, useRepositories } from '../../api/queries';
import { RepoFormat, RepoType } from '../../types';
import { Boxes, Globe, Layers, Sparkles, Infinity as InfinityIcon, Clock } from 'lucide-react';

interface CreateRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateRepoModal: React.FC<CreateRepoModalProps> = ({ isOpen, onClose }) => {
  const [form] = Form.useForm();
  const createMutation = useCreateRepository();
  const { data: allRepos } = useRepositories();

  const [selectedFormat, setSelectedFormat] = useState<RepoFormat>('maven');
  const [selectedType, setSelectedType] = useState<RepoType>('hosted');
  const [isPermanentCache, setIsPermanentCache] = useState<boolean>(false);

  const defaultUpstreams: Record<RepoFormat, string> = {
    maven: 'https://repo1.maven.org/maven2',
    npm: 'https://registry.npmjs.org',
    docker: 'https://registry-1.docker.io',
    pypi: 'https://pypi.org',
  };

  const handleFormatChange = (fmt: RepoFormat) => {
    setSelectedFormat(fmt);
    form.setFieldsValue({
      upstream_url: defaultUpstreams[fmt],
    });
  };

  const handleFinish = async (values: any) => {
    try {
      const ttl = isPermanentCache ? 0 : (values.cache_ttl_hours || 720);
      await createMutation.mutateAsync({
        name: values.name.trim(),
        format: values.format,
        type: values.type,
        description: values.description || '',
        is_online: true,
        upstream_url: values.type === 'proxy' ? values.upstream_url : null,
        cache_ttl_hours: values.type === 'proxy' ? ttl : null,
        member_repo_names: values.type === 'group' ? values.member_repo_names : null,
      });
      message.success(`Repository '${values.name}' created successfully`);
      form.resetFields();
      onClose();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to create repository');
    }
  };

  const matchingMembers = allRepos?.filter(
    (r) => r.format === selectedFormat && r.type !== 'group'
  ) || [];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <Boxes className="w-5 h-5 text-blue-400" />
          <span>Create New Repository</span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      width={600}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{
          format: 'maven',
          type: 'hosted',
          cache_ttl_hours: 720,
          upstream_url: defaultUpstreams['maven'],
        }}
        className="pt-3 space-y-4"
      >
        {/* Format Selector */}
        <Form.Item
          name="format"
          label={<span className="text-xs font-semibold text-slate-300">Package Format</span>}
          rules={[{ required: true }]}
        >
          <Radio.Group
            onChange={(e) => handleFormatChange(e.target.value)}
            className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full"
          >
            <Radio.Button value="maven" className="text-center font-semibold">☕ Maven</Radio.Button>
            <Radio.Button value="npm" className="text-center font-semibold">📦 NPM</Radio.Button>
            <Radio.Button value="docker" className="text-center font-semibold">🐳 Docker</Radio.Button>
            <Radio.Button value="pypi" className="text-center font-semibold">🐍 PyPI</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {/* Type Selector */}
        <Form.Item
          name="type"
          label={<span className="text-xs font-semibold text-slate-300">Repository Type</span>}
          rules={[{ required: true }]}
        >
          <Radio.Group
            onChange={(e) => setSelectedType(e.target.value)}
            className="grid grid-cols-3 gap-2 w-full"
          >
            <Radio.Button value="hosted" className="text-center">
              <div className="py-1">
                <span className="font-semibold block">Hosted</span>
                <span className="text-[10px] text-slate-400 block">Private internal</span>
              </div>
            </Radio.Button>
            <Radio.Button value="proxy" className="text-center">
              <div className="py-1">
                <span className="font-semibold block">Proxy</span>
                <span className="text-[10px] text-slate-400 block">Upstream cache</span>
              </div>
            </Radio.Button>
            <Radio.Button value="group" className="text-center">
              <div className="py-1">
                <span className="font-semibold block">Group</span>
                <span className="text-[10px] text-slate-400 block">Merged view</span>
              </div>
            </Radio.Button>
          </Radio.Group>
        </Form.Item>

        {/* Name */}
        <Form.Item
          name="name"
          label={<span className="text-xs font-semibold text-slate-300">Repository Name</span>}
          rules={[
            { required: true, message: 'Please enter a unique repository name' },
            { pattern: /^[a-zA-Z0-9-_]+$/, message: 'Only alphanumeric characters, dashes, and underscores' }
          ]}
        >
          <Input placeholder="e.g., maven-releases, npm-internal, custom-pypi" className="font-mono text-xs" />
        </Form.Item>

        {/* Description */}
        <Form.Item
          name="description"
          label={<span className="text-xs font-semibold text-slate-300">Description (Optional)</span>}
        >
          <Input placeholder="Brief notes about this repository" className="text-xs" />
        </Form.Item>

        {/* Proxy Fields */}
        {selectedType === 'proxy' && (
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-4">
            <Form.Item
              name="upstream_url"
              label={
                <span className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5" />
                  Remote Upstream URL
                </span>
              }
              rules={[{ required: true, message: 'Upstream URL is required for Proxy repos' }]}
            >
              <Input placeholder="https://repo1.maven.org/maven2" className="font-mono text-xs" />
            </Form.Item>

            {/* Cache TTL Section */}
            <div className="space-y-3 pt-2 border-t border-amber-500/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-xs font-semibold text-amber-300">Cache TTL (Thời gian lưu cache)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-300 font-medium">Lưu vĩnh viễn (Permanent):</span>
                  <Switch
                    checked={isPermanentCache}
                    onChange={(checked) => setIsPermanentCache(checked)}
                    checkedChildren={<InfinityIcon className="w-3.5 h-3.5 inline" />}
                    unCheckedChildren="TTL"
                    className={isPermanentCache ? 'bg-amber-600' : 'bg-slate-700'}
                  />
                </div>
              </div>

              {isPermanentCache ? (
                <div className="p-3 rounded-lg bg-amber-900/30 border border-amber-500/30 text-[11px] text-amber-200 flex items-center gap-2">
                  <InfinityIcon className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>
                    <strong>Lưu trữ vĩnh viễn (Never Expire)</strong>: Mọi package khi được tải từ upstream về sẽ được lưu trữ mãi mãi trên ổ đĩa local mà không bao giờ bị xóa theo thời gian.
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  <Form.Item
                    name="cache_ttl_hours"
                    noStyle
                  >
                    <InputNumber min={1} max={87600} placeholder="Số giờ (ví dụ 720 = 30 ngày)" className="w-full text-xs" />
                  </Form.Item>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { label: '7 ngày (168h)', val: 168 },
                      { label: '30 ngày (720h)', val: 720 },
                      { label: '90 ngày (2160h)', val: 2160 },
                      { label: '1 năm (8760h)', val: 8760 },
                    ].map((preset) => (
                      <button
                        type="button"
                        key={preset.val}
                        onClick={() => form.setFieldValue('cache_ttl_hours', preset.val)}
                        className="px-2 py-0.5 rounded text-[10px] bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 border border-amber-500/20 transition-all"
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Group Fields */}
        {selectedType === 'group' && (
          <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-4">
            <Form.Item
              name="member_repo_names"
              label={<span className="text-xs font-semibold text-purple-300">Member Repositories (Priority Order)</span>}
              rules={[{ required: true, message: 'Select at least one member repository' }]}
            >
              <Select
                mode="multiple"
                placeholder="Select Hosted & Proxy members"
                options={matchingMembers.map((m) => ({
                  label: `${m.name} (${m.type})`,
                  value: m.name,
                }))}
                className="w-full"
              />
            </Form.Item>
          </div>
        )}

        <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-800">
          <Button onClick={onClose} className="border-slate-700 text-slate-300">
            Cancel
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={createMutation.isPending}
            className="bg-blue-600 hover:bg-blue-500 border-none px-5 h-9 rounded-xl font-medium"
          >
            Create Repository
          </Button>
        </div>
      </Form>
    </Modal>
  );
};
