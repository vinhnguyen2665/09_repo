import React, { useState } from 'react';
import { useUsers, useDeleteUser } from '../../api/queries';
import { CreateUserModal } from './CreateUserModal';
import { ApiTokenModal } from './ApiTokenModal';
import { 
  Users as UsersIcon, 
  UserPlus, 
  Key, 
  Trash2, 
  ShieldCheck, 
  ShieldAlert, 
  User as UserIcon,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { Table, Button, Tag, Modal, message, Spin, Empty } from 'antd';
import { User, UserRole } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const UserManager: React.FC = () => {
  const { user: currentUser } = useAuth();
  const { data: users, isLoading } = useUsers();
  const deleteMutation = useDeleteUser();

  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [tokenModalOpen, setTokenModalOpen] = useState(false);

  const handleDelete = (user: User) => {
    Modal.confirm({
      title: 'Delete User Account',
      content: `Are you sure you want to permanently delete user '${user.username}'?`,
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await deleteMutation.mutateAsync(user.id);
          message.success(`User ${user.username} deleted`);
        } catch (err: any) {
          message.error(err.response?.data?.detail || 'Failed to delete user');
        }
      },
    });
  };

  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return <Tag color="red" className="font-semibold text-xs">ADMIN</Tag>;
      case 'developer':
        return <Tag color="blue" className="font-semibold text-xs">DEVELOPER</Tag>;
      case 'reader':
        return <Tag color="green" className="font-semibold text-xs">READER</Tag>;
    }
  };

  const columns = [
    {
      title: 'User',
      key: 'user',
      render: (_: any, record: User) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xs">
            {record.username[0].toUpperCase()}
          </div>
          <div>
            <div className="font-semibold text-slate-100">{record.username}</div>
            <div className="text-xs text-slate-400">{record.email}</div>
          </div>
        </div>
      ),
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: UserRole) => getRoleBadge(role),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <span className="flex items-center gap-1.5 text-xs font-medium">
          {isActive ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-400">Active</span>
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 text-rose-400" />
              <span className="text-rose-400">Disabled</span>
            </>
          )}
        </span>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => <span className="text-xs text-slate-400 font-mono">{new Date(date).toLocaleDateString()}</span>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: User) => (
        <Button
          type="text"
          danger
          size="small"
          icon={<Trash2 className="w-3.5 h-3.5" />}
          onClick={() => handleDelete(record)}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <UsersIcon className="w-5 h-5 text-blue-400" />
            User & Access Control Management
          </h2>
          <p className="text-xs text-slate-400">Role-Based Access Control (Admin, Developer, Reader) & API Tokens</p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            icon={<Key className="w-4 h-4" />}
            onClick={() => setTokenModalOpen(true)}
            className="border-slate-700 text-slate-200 text-xs flex items-center gap-1.5 h-9 rounded-xl"
          >
            My API Tokens
          </Button>
          <Button
            type="primary"
            icon={<UserPlus className="w-4 h-4" />}
            onClick={() => setCreateUserOpen(true)}
            className="bg-blue-600 hover:bg-blue-500 border-none text-xs flex items-center gap-1.5 h-9 px-4 rounded-xl"
          >
            Add User
          </Button>
        </div>
      </div>

      {/* Users Table */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <Table
          dataSource={users || []}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
          className="border border-slate-800 rounded-xl overflow-hidden"
        />
      </div>

      {/* Modals */}
      {createUserOpen && (
        <CreateUserModal
          isOpen={createUserOpen}
          onClose={() => setCreateUserOpen(false)}
        />
      )}

      {tokenModalOpen && (
        <ApiTokenModal
          isOpen={tokenModalOpen}
          onClose={() => setTokenModalOpen(false)}
        />
      )}
    </div>
  );
};
