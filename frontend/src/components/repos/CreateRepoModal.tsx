import React, { useState } from 'react';
import { Modal, Form, Input, Select, InputNumber, Button, message, Radio } from 'antd';
import { useCreateRepository, useRepositories } from '../../api/queries';
import { RepoFormat, RepoType } from '../../types';
import { Boxes, Globe, Server, Layers } from 'lucide-react';

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
      await createMutation.mutateAsync({
        name: values.name.trim(),
        format: values.format,
        type: values.type,
        description: values.description || '',
        upstream_url: values.type === 'proxy' ? values.upstream_url : null,
        cache_ttl_hours: values.type === 'proxy' ? values.cache_ttl_hours : 720,
        member_repo_names: values.type === 'group' ? values.member_repo_names : [],
        is_online: true,
      });
      message.success(`Repository '${values.name}' created successfully`);
      form.resetFields();
      onClose();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to create repository');
    }
  };

  // Filter possible member repos for Group format matching
  const matchingMembers = allRepos?.filter(
    (r) => r.format === selectedFormat && r.type !== 'group'
  ) || [];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <Boxes className="w-5 h-5 text-blue-400" />
          <span>Create New Package Repository</span>
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
              label={<span className="text-xs font-semibold text-amber-300">Remote Upstream URL</span>}
              rules={[{ required: true, message: 'Upstream URL is required for Proxy repos' }]}
            >
              <Input placeholder="https://repo1.maven.org/maven2" className="font-mono text-xs" />
            </Form.Item>

            <Form.Item
              name="cache_ttl_hours"
              label={<span className="text-xs font-semibold text-amber-300">Cache TTL (Hours)</span>}
            >
              <InputNumber min={1} max={8760} className="w-full text-xs" />
            </Form.Item>
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
            className="bg-blue-600 hover:bg-blue-500 border-none"
          >
            Create Repository
          </Button>
        </div>
      </Form>
    </Modal>
  );
};
