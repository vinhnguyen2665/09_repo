import React, { useState } from 'react';
import { Modal, Button, message } from 'antd';
import { usePreviewFile } from '../../api/queries';
import { FileCode, Copy, Download, Check } from 'lucide-react';
import { formatBytes } from '../dashboard/StorageGauge';

interface FileViewerModalProps {
  repoName: string;
  path: string;
  isOpen: boolean;
  onClose: () => void;
}

export const FileViewerModal: React.FC<FileViewerModalProps> = ({
  repoName,
  path,
  isOpen,
  onClose,
}) => {
  const { data: preview, isLoading } = usePreviewFile(repoName, path);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (preview?.content) {
      navigator.clipboard.writeText(preview.content);
      setCopied(true);
      message.success('Code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    window.open(`/api/storage/download?repo_name=${encodeURIComponent(repoName)}&path=${encodeURIComponent(path)}`, '_blank');
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <FileCode className="w-5 h-5 text-blue-400" />
          <span className="font-mono text-sm">{preview?.filename || path}</span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      width={850}
      footer={[
        <Button key="close" onClick={onClose} className="border-slate-700 text-slate-300">
          Close
        </Button>,
        <Button
          key="download"
          icon={<Download className="w-4 h-4" />}
          onClick={handleDownload}
          className="border-slate-700 text-slate-200"
        >
          Download File
        </Button>,
        <Button
          key="copy"
          type="primary"
          icon={copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          onClick={handleCopy}
          className="bg-blue-600 hover:bg-blue-500 border-none"
        >
          {copied ? 'Copied!' : 'Copy Code'}
        </Button>,
      ]}
    >
      <div className="space-y-4 pt-2">
        {/* Metadata Bar */}
        <div className="flex items-center justify-between text-xs text-slate-400 bg-slate-900/80 px-4 py-2 rounded-lg border border-slate-800 font-mono">
          <span>Format: <strong className="text-slate-200">{preview?.content_type}</strong></span>
          <span>Size: <strong className="text-slate-200">{preview ? formatBytes(preview.size_bytes) : '0 B'}</strong></span>
          <span>Repository: <strong className="text-blue-400">{repoName}</strong></span>
        </div>

        {/* Code Content Box */}
        <div className="relative rounded-xl border border-slate-800 bg-[#070b14] overflow-hidden font-mono text-xs max-h-[500px] overflow-y-auto">
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">Loading preview...</div>
          ) : (
            <pre className="p-4 text-slate-200 leading-relaxed overflow-x-auto selection:bg-blue-600 selection:text-white">
              <code>{preview?.content}</code>
            </pre>
          )}
        </div>
      </div>
    </Modal>
  );
};
