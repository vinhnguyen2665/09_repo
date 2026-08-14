import React, { useState } from 'react';
import { useRepositories, useFileTree, useInspectArtifact, useDeleteArtifact } from '../../api/queries';
import { formatBytes } from '../dashboard/StorageGauge';
import { FileViewerModal } from './FileViewerModal';
import { 
  FolderTree, 
  Folder, 
  FolderOpen, 
  File, 
  FileCode, 
  FileText, 
  Download, 
  Trash2, 
  Eye, 
  Copy, 
  Check, 
  Search, 
  HardDrive, 
  ShieldCheck, 
  Clock, 
  Layers,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { Select, Input, Button, Tag, Modal, message, Empty, Spin } from 'antd';
import { FileTreeNode } from '../../types';

export const StorageExplorer: React.FC = () => {
  const { data: repos, isLoading: reposLoading } = useRepositories();
  const [selectedRepo, setSelectedRepo] = useState<string>('maven-private');
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string>('');

  const { data: treeNodes, isLoading: treeLoading } = useFileTree(selectedRepo);
  const { data: artifactDetails, isLoading: inspectLoading } = useInspectArtifact(selectedRepo, selectedFilePath);
  const deleteMutation = useDeleteArtifact();

  // Handle default selection when repos load
  React.useEffect(() => {
    if (repos && repos.length > 0 && !selectedRepo) {
      setSelectedRepo(repos[0].name);
    }
  }, [repos, selectedRepo]);

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const handleCopyHash = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(type);
    message.success(`${type.toUpperCase()} copied to clipboard`);
    setTimeout(() => setCopiedHash(''), 2000);
  };

  const handleDelete = () => {
    if (!selectedFilePath) return;
    Modal.confirm({
      title: 'Delete Artifact',
      content: `Are you sure you want to permanently delete '${selectedFilePath}' from '${selectedRepo}'?`,
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await deleteMutation.mutateAsync({
            repoName: selectedRepo,
            path: selectedFilePath,
          });
          message.success('Artifact deleted successfully');
          setSelectedFilePath('');
        } catch {
          message.error('Failed to delete artifact');
        }
      },
    });
  };

  const renderTree = (nodes: FileTreeNode[]) => {
    return (
      <ul className="space-y-1 pl-2 text-xs font-mono">
        {nodes.map((node) => {
          const isExpanded = expandedFolders[node.path] !== false; // default expanded
          const isSelected = selectedFilePath === node.path;
          const matchesSearch = !searchTerm || node.name.toLowerCase().includes(searchTerm.toLowerCase()) || node.path.toLowerCase().includes(searchTerm.toLowerCase());

          if (node.is_dir) {
            const hasVisibleChildren = node.children && node.children.some(c => !searchTerm || c.name.toLowerCase().includes(searchTerm.toLowerCase()) || c.path.toLowerCase().includes(searchTerm.toLowerCase()));
            if (searchTerm && !hasVisibleChildren && !matchesSearch) return null;

            return (
              <li key={node.path} className="select-none">
                <div
                  onClick={() => toggleFolder(node.path)}
                  className="flex items-center gap-1.5 py-1 px-2 rounded-lg hover:bg-slate-800/60 cursor-pointer text-slate-300 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                  )}
                  {isExpanded ? (
                    <FolderOpen className="w-4 h-4 text-blue-400" />
                  ) : (
                    <Folder className="w-4 h-4 text-blue-400" />
                  )}
                  <span className="font-medium text-slate-200">{node.name}</span>
                </div>
                {isExpanded && node.children && (
                  <div className="pl-3 border-l border-slate-800/80 ml-2 mt-0.5">
                    {renderTree(node.children)}
                  </div>
                )}
              </li>
            );
          }

          if (!matchesSearch) return null;

          const isCodeFile = node.name.endsWith('.xml') || node.name.endsWith('.pom') || node.name.endsWith('.json') || node.name.endsWith('.yaml');

          return (
            <li key={node.path}>
              <div
                onClick={() => setSelectedFilePath(node.path)}
                className={`flex items-center justify-between py-1.5 px-2.5 rounded-lg cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 font-medium'
                    : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {isCodeFile ? (
                    <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                  ) : (
                    <File className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="truncate">{node.name}</span>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 ml-2">
                  {formatBytes(node.size_bytes || 0)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <FolderTree className="w-5 h-5 text-blue-400" />
            Storage & Artifact Explorer
          </h2>
          <p className="text-xs text-slate-400">Interactive directory inspector and checksum verification</p>
        </div>

        {/* Repository selector */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Repository:</span>
          <Select
            value={selectedRepo}
            onChange={(val) => {
              setSelectedRepo(val);
              setSelectedFilePath('');
            }}
            loading={reposLoading}
            className="w-56"
            options={repos?.map((r) => ({
              label: (
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold">{r.name}</span>
                  <Tag color={r.type === 'hosted' ? 'blue' : r.type === 'proxy' ? 'orange' : 'purple'} className="mr-0 text-[10px]">
                    {r.type.toUpperCase()}
                  </Tag>
                </div>
              ),
              value: r.name,
            }))}
          />
        </div>
      </div>

      {/* Explorer Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Tree Viewer */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-4 space-y-4">
          <div className="space-y-2">
            <Input
              prefix={<Search className="w-4 h-4 text-slate-500" />}
              placeholder="Search file name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
              className="bg-slate-900/90 border-slate-800 text-xs"
            />
          </div>

          <div className="min-h-[420px] max-h-[550px] overflow-y-auto pr-1">
            {treeLoading ? (
              <div className="h-64 flex flex-col items-center justify-center gap-2 text-slate-500 text-xs">
                <Spin />
                <span>Scanning repository tree...</span>
              </div>
            ) : treeNodes && treeNodes.length > 0 ? (
              renderTree(treeNodes)
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs space-y-2">
                <Empty description={<span className="text-slate-500">Repository is empty</span>} />
                <p className="text-[11px]">Deploy an artifact to view directory structure</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: File Details Inspector */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-6 space-y-6">
          {selectedFilePath && artifactDetails ? (
            <div className="space-y-6">
              {/* Header Details */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-5 h-5 text-blue-400" />
                    <h3 className="font-mono text-base font-bold text-slate-100">{artifactDetails.filename}</h3>
                  </div>
                  <p className="text-xs text-slate-400 font-mono break-all">{artifactDetails.path}</p>
                </div>
                <Tag color={artifactDetails.is_cached_proxy ? 'orange' : 'blue'}>
                  {artifactDetails.is_cached_proxy ? 'PROXY CACHED' : 'HOSTED PRIVATE'}
                </Tag>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2.5">
                <Button
                  type="primary"
                  icon={<Eye className="w-4 h-4" />}
                  onClick={() => setPreviewOpen(true)}
                  className="bg-blue-600 hover:bg-blue-500 border-none text-xs flex items-center gap-1.5"
                >
                  View Code / XML
                </Button>
                <Button
                  icon={<Download className="w-4 h-4" />}
                  onClick={() => window.open(`/api/storage/download?repo_name=${encodeURIComponent(selectedRepo)}&path=${encodeURIComponent(selectedFilePath)}`, '_blank')}
                  className="border-slate-700 text-slate-200 text-xs flex items-center gap-1.5"
                >
                  Download
                </Button>
                <Button
                  danger
                  icon={<Trash2 className="w-4 h-4" />}
                  onClick={handleDelete}
                  className="text-xs flex items-center gap-1.5"
                >
                  Delete
                </Button>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 space-y-1">
                  <span className="text-[11px] text-slate-500">File Size</span>
                  <p className="text-sm font-bold text-slate-200 font-mono">{formatBytes(artifactDetails.size_bytes)}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 space-y-1">
                  <span className="text-[11px] text-slate-500">Downloads</span>
                  <p className="text-sm font-bold text-slate-200 font-mono">{artifactDetails.downloads_count} pulls</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 space-y-1">
                  <span className="text-[11px] text-slate-500">Content-Type</span>
                  <p className="text-xs font-semibold text-slate-300 truncate font-mono">{artifactDetails.content_type}</p>
                </div>
              </div>

              {/* Checksum Hashes Panel */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Integrity Checksums (SHA1 / MD5 / SHA256)</span>
                </div>

                <div className="space-y-2 font-mono text-xs">
                  {artifactDetails.sha1 && (
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-[10px] text-slate-500 uppercase w-14 shrink-0 font-bold">SHA1</span>
                        <span className="text-slate-300 truncate">{artifactDetails.sha1}</span>
                      </div>
                      <Button
                        type="text"
                        size="small"
                        icon={copiedHash === 'sha1' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                        onClick={() => handleCopyHash(artifactDetails.sha1!, 'sha1')}
                      />
                    </div>
                  )}

                  {artifactDetails.md5 && (
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-[10px] text-slate-500 uppercase w-14 shrink-0 font-bold">MD5</span>
                        <span className="text-slate-300 truncate">{artifactDetails.md5}</span>
                      </div>
                      <Button
                        type="text"
                        size="small"
                        icon={copiedHash === 'md5' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                        onClick={() => handleCopyHash(artifactDetails.md5!, 'md5')}
                      />
                    </div>
                  )}

                  {artifactDetails.sha256 && (
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-[10px] text-slate-500 uppercase w-14 shrink-0 font-bold">SHA256</span>
                        <span className="text-slate-300 truncate">{artifactDetails.sha256}</span>
                      </div>
                      <Button
                        type="text"
                        size="small"
                        icon={copiedHash === 'sha256' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                        onClick={() => handleCopyHash(artifactDetails.sha256!, 'sha256')}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-80 flex flex-col items-center justify-center text-slate-500 text-xs space-y-3">
              <HardDrive className="w-10 h-10 text-slate-700 stroke-1" />
              <p>Select any file in the tree on the left to inspect metadata & checksums</p>
            </div>
          )}
        </div>
      </div>

      {/* Code Viewer Modal */}
      {previewOpen && (
        <FileViewerModal
          repoName={selectedRepo}
          path={selectedFilePath}
          isOpen={previewOpen}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </div>
  );
};
