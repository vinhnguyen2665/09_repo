import React from 'react';
import { Modal, Form, Input, Select, Button, message } from 'antd';
import { useCreateUser } from '../../api/queries';
import { UserPlus } from 'lucide-react';

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateUserModal: React.FC<CreateUserModalProps> = ({ isOpen, onClose }) => {
  const [form] = Form.useForm();
  const createMutation = useCreateUser();

  const handleFinish = async (values: any) => {
    try {
      await createMutation.mutateAsync({
        username: values.username.trim(),
        email: values.email.trim(),
        password: values.password,
        role: values.role,
      });
      message.success(`User '${values.username}' created successfully`);
      form.resetFields();
      onClose();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to create user');
    }
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <UserPlus className="w-5 h-5 text-blue-400" />
          <span>Add New User Account</span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={480}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ role: 'developer' }}
        className="pt-3 space-y-3"
      >
        <Form.Item
          name="username"
          label={<span className="text-xs font-semibold text-slate-300">Username</span>}
          rules={[{ required: true, message: 'Please enter username' }]}
        >
          <Input placeholder="developer_john" className="text-xs" />
        </Form.Item>

        <Form.Item
          name="email"
          label={<span className="text-xs font-semibold text-slate-300">Email Address</span>}
          rules={[
            { required: true, message: 'Please enter email' },
            { type: 'email', message: 'Enter a valid email' },
          ]}
        >
          <Input placeholder="john@example.com" className="text-xs" />
        </Form.Item>

        <Form.Item
          name="password"
          label={<span className="text-xs font-semibold text-slate-300">Password</span>}
          rules={[{ required: true, min: 6, message: 'Password must be at least 6 characters' }]}
        >
          <Input.Password placeholder="••••••••" className="text-xs" />
        </Form.Item>

        <Form.Item
          name="role"
          label={<span className="text-xs font-semibold text-slate-300">RBAC Role</span>}
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { label: 'Admin (Full system and repo management)', value: 'admin' },
              { label: 'Developer (Can deploy & download artifacts)', value: 'developer' },
              { label: 'Reader (Read-only artifact downloads)', value: 'reader' },
            ]}
          />
        </Form.Item>

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
            Create User
          </Button>
        </div>
      </Form>
    </Modal>
  );
};
