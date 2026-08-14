import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, Select, InputNumber, Button, Switch, message, Tag } from 'antd';
import { useUpdateRepository, useRepositories } from '../../api/queries';
import { Repository } from '../../types';
import { Settings2, Globe, Layers, Activity, CheckCircle2, XCircle, Infinity as InfinityIcon, Clock } from 'lucide-react';

interface EditRepoModalProps {
  repo: Repository | null;
  isOpen: boolean;
  onClose: () => void;
}

export const EditRepoModal: React.FC<EditRepoModalProps> = ({ repo, isOpen, onClose }) => {
  const [form] = Form.useForm();
  const updateMutation = useUpdateRepository();
  const { data: allRepos } = useRepositories();
  const [isOnlineState, setIsOnlineState] = useState<boolean>(true);
  const [isPermanentCache, setIsPermanentCache] = useState<boolean>(false);

  useEffect(() => {
    if (repo) {
      const currentOnline = repo.is_online !== false;
      const isPerm = repo.cache_ttl_hours === 0 || repo.cache_ttl_hours === null;
      setIsOnlineState(currentOnline);
      setIsPermanentCache(isPerm);
      form.setFieldsValue({
        description: repo.description || '',
        is_online: currentOnline,
        upstream_url: repo.upstream_url || '',
        cache_ttl_hours: isPerm ? 720 : repo.cache_ttl_hours,
        member_repo_names: repo.member_repo_names || [],
      });
    }
  }, [repo, form]);

  if (!repo) return null;

  const handleFinish = async (values: any) => {
    try {
      const ttl = isPermanentCache ? 0 : (values.cache_ttl_hours || 720);
      await updateMutation.mutateAsync({
        name: repo.name,
        data: {
          description: values.description || '',
          is_online: isOnlineState,
          upstream_url: repo.type === 'proxy' ? values.upstream_url : null,
          cache_ttl_hours: repo.type === 'proxy' ? ttl : null,
          member_repo_names: repo.type === 'group' ? values.member_repo_names : null,
        },
      });
      message.success(`Repository '${repo.name}' updated successfully (Status: ${isOnlineState ? 'ONLINE' : 'OFFLINE'}, TTL: ${isPermanentCache ? 'Vĩnh viễn' : `${ttl}h`})`);
      onClose();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to update repository');
    }
  };

  const matchingMembers = allRepos?.filter(
    (r) => r.format === repo.format && r.type !== 'group' && r.name !== repo.name
  ) || [];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <Settings2 className="w-5 h-5 text-blue-400" />
          <span>Edit Repository: <span className="font-mono text-blue-400">{repo.name}</span></span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      width={600}
      footer={null}
    >
      <div className="pt-2 space-y-4">
        {/* Repo Type & Format Header */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Format:</span>
            <Tag color="blue" className="font-mono font-semibold uppercase">{repo.format}</Tag>
            <span className="text-slate-400 ml-2">Type:</span>
            <Tag color={repo.type === 'hosted' ? 'blue' : repo.type === 'proxy' ? 'orange' : 'purple'} className="font-semibold uppercase">
              {repo.type}
            </Tag>
          </div>
          <span className="text-slate-400 font-mono text-[11px]">ID: #{repo.id}</span>
        </div>

        {/* Status Switch Control */}
        <div className={`p-4 rounded-xl border transition-all ${
          isOnlineState 
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
            : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
        }`}>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2 font-semibold text-xs">
                {isOnlineState ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-300">Status: ONLINE (Active)</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span className="text-rose-300">Status: OFFLINE (Disabled / Maintenance)</span>
                  </>
                )}
              </div>
              <p className="text-[11px] text-slate-400">
                {isOnlineState
                  ? 'Accepts incoming client requests, artifact downloads, and publish uploads.'
                  : 'Blocks all incoming traffic with HTTP 503 and skipped in group repositories.'}
              </p>
            </div>
            <Switch
              checked={isOnlineState}
              onChange={(checked) => {
                setIsOnlineState(checked);
                form.setFieldValue('is_online', checked);
              }}
              checkedChildren="ON"
              unCheckedChildren="OFF"
              className={isOnlineState ? 'bg-emerald-600' : 'bg-slate-700'}
            />
          </div>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          className="space-y-4"
        >
          {/* Description */}
          <Form.Item
            name="description"
            label={<span className="text-xs font-semibold text-slate-300">Description</span>}
          >
            <Input.TextArea rows={2} placeholder="Repository notes and documentation" className="text-xs" />
          </Form.Item>

          {/* Proxy Upstream Config */}
          {repo.type === 'proxy' && (
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-4">
              <Form.Item
                name="upstream_url"
                label={
                  <span className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5" />
                    Remote Upstream Registry URL
                  </span>
                }
                rules={[{ required: true, message: 'Upstream URL cannot be empty' }]}
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
                    <span className="text-[11px] text-slate-300 font-medium">Lưu vĩnh viễn:</span>
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

          {/* Group Members Config */}
          {repo.type === 'group' && (
            <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-4">
              <Form.Item
                name="member_repo_names"
                label={
                  <span className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5" />
                    Member Repositories (Priority Order)
                  </span>
                }
                rules={[{ required: true, message: 'Select at least one member repository' }]}
              >
                <Select
                  mode="multiple"
                  placeholder="Select member repositories"
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
              loading={updateMutation.isPending}
              className="bg-blue-600 hover:bg-blue-500 border-none font-medium text-xs px-5 h-9 rounded-xl"
            >
              Save Changes
            </Button>
          </div>
        </Form>
      </div>
    </Modal>
  );
};
