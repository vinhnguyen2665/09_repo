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
  ChevronDown,
  ShieldAlert,
  LogIn,
  Terminal
} from 'lucide-react';
import { Select, Input, Button, Tag, Modal, message, Empty, Spin, Tabs } from 'antd';
import { FileTreeNode } from '../../types';
import { useAuth } from '../../context/AuthContext';

interface MavenDependency {
  groupId: string;
  artifactId: string;
  version: string;
  fileName: string;
}

interface NpmDependency {
  packageName: string;
  version: string;
}

interface DockerDependency {
  imageName: string;
  tag: string;
}

interface PypiDependency {
  packageName: string;
  version: string;
}

const parseMavenPath = (path: string): MavenDependency | null => {
  const parts = path.split('/');
  if (parts.length < 4) return null;
  const fileName = parts[parts.length - 1];
  const version = parts[parts.length - 2];
  const artifactId = parts[parts.length - 3];
  const groupId = parts.slice(0, parts.length - 3).join('.');
  if (!groupId || !artifactId || !version) return null;
  return { groupId, artifactId, version, fileName };
};

const parseNpmPath = (path: string): NpmDependency | null => {
  if (!path) return null;
  const normPath = path.replace(/\\/g, '/');

  // Case 1: contains /-/ (tarball file)
  if (normPath.includes('/-/')) {
    const parts = normPath.split('/-/');
    if (parts.length >= 2) {
      const packageName = parts[0];
      const filename = parts[parts.length - 1];
      const match = filename.match(/-(\d+\.\d+\.\d+.*?)\.tgz$/);
      const version = match ? match[1] : 'latest';
      return { packageName, version };
    }
  }

  // Case 2: ends with package.json
  if (normPath.endsWith('/package.json')) {
    const packageName = normPath.substring(0, normPath.length - '/package.json'.length);
    return { packageName, version: 'latest' };
  }

  // Case 3: generic file under npm format, e.g. "lodash/somefile.txt"
  const parts = normPath.split('/');
  if (parts.length >= 2 && parts[0].startsWith('@')) {
    const packageName = `${parts[0]}/${parts[1]}`;
    return { packageName, version: 'latest' };
  } else if (parts.length >= 1) {
    const packageName = parts[0];
    return { packageName, version: 'latest' };
  }

  return null;
};

const parseDockerPath = (path: string): DockerDependency | null => {
  if (!path) return null;
  const normPath = path.replace(/\\/g, '/');
  if (!normPath.startsWith('manifests/')) return null;
  const cleanPath = normPath.substring('manifests/'.length);
  const parts = cleanPath.split('/');
  if (parts.length < 2) return null;
  const tagWithExt = parts[parts.length - 1];
  if (!tagWithExt.endsWith('.json')) return null;
  const tag = tagWithExt.substring(0, tagWithExt.length - '.json'.length);
  const imageName = parts.slice(0, parts.length - 1).join('/');
  return { imageName, tag };
};

const parsePypiPath = (path: string): PypiDependency | null => {
  if (!path) return null;
  const normPath = path.replace(/\\/g, '/');
  if (!normPath.startsWith('packages/')) return null;
  const filename = normPath.substring('packages/'.length);
  let cleanName = filename;
  if (filename.endsWith('.whl')) {
    cleanName = filename.substring(0, filename.length - '.whl'.length);
  } else if (filename.endsWith('.tar.gz')) {
    cleanName = filename.substring(0, filename.length - '.tar.gz'.length);
  } else if (filename.endsWith('.zip')) {
    cleanName = filename.substring(0, filename.length - '.zip'.length);
  } else {
    return null;
  }
  const parts = cleanName.split('-');
  if (parts.length < 2) return null;
  let versionIndex = -1;
  for (let i = 1; i < parts.length; i++) {
    if (/^\d/.test(parts[i])) {
      versionIndex = i;
      break;
    }
  }
  if (versionIndex === -1) {
    versionIndex = 1;
  }
  const packageName = parts.slice(0, versionIndex).join('-');
  const version = parts[versionIndex];
  return { packageName, version };
};

const getMavenDependencySnippets = (dep: MavenDependency) => {
  const { groupId, artifactId, version } = dep;
  return [
    {
      key: 'maven',
      label: 'Maven',
      code: `<dependency>\n  <groupId>${groupId}</groupId>\n  <artifactId>${artifactId}</artifactId>\n  <version>${version}</version>\n</dependency>`
    },
    {
      key: 'gradle-groovy',
      label: 'Gradle (Groovy)',
      code: `implementation '${groupId}:${artifactId}:${version}'`
    },
    {
      key: 'gradle-kotlin',
      label: 'Gradle (Kotlin)',
      code: `implementation("${groupId}:${artifactId}:${version}")`
    },
    {
      key: 'sbt',
      label: 'SBT',
      code: `libraryDependencies += "${groupId}" % "${artifactId}" % "${version}"`
    },
    {
      key: 'mill',
      label: 'Mill',
      code: `ivy"${groupId}:${artifactId}:${version}"`
    },
    {
      key: 'ivy',
      label: 'Ivy',
      code: `<dependency org="${groupId}" name="${artifactId}" rev="${version}" />`
    },
    {
      key: 'grape',
      label: 'Grape',
      code: `@Grapes(\n  @Grab(group='${groupId}', module='${artifactId}', version='${version}')\n)`
    },
    {
      key: 'leiningen',
      label: 'Leiningen',
      code: `[${groupId}/${artifactId} "${version}"]`
    },
    {
      key: 'buildr',
      label: 'Buildr',
      code: `'${groupId}:${artifactId}:jar:${version}'`
    }
  ];
};

const getNpmDependencySnippets = (dep: NpmDependency) => {
  const { packageName, version } = dep;
  return [
    {
      key: 'npm',
      label: 'npm',
      code: `npm install ${packageName}@${version}`
    },
    {
      key: 'yarn',
      label: 'Yarn',
      code: `yarn add ${packageName}@${version}`
    },
    {
      key: 'pnpm',
      label: 'pnpm',
      code: `pnpm add ${packageName}@${version}`
    },
    {
      key: 'bun',
      label: 'Bun',
      code: `bun add ${packageName}@${version}`
    }
  ];
};

const getDockerDependencySnippets = (dep: DockerDependency) => {
  const { imageName, tag } = dep;
  const host = window.location.host;
  return [
    {
      key: 'docker-pull',
      label: 'Docker Pull',
      code: `docker pull ${host}/${imageName}:${tag}`
    },
    {
      key: 'docker-tag',
      label: 'Docker Tag',
      code: `docker tag ${imageName}:${tag} ${host}/${imageName}:${tag}`
    },
    {
      key: 'docker-push',
      label: 'Docker Push',
      code: `docker push ${host}/${imageName}:${tag}`
    },
    {
      key: 'docker-run',
      label: 'Docker Run',
      code: `docker run -d ${host}/${imageName}:${tag}`
    }
  ];
};

const getPypiDependencySnippets = (dep: PypiDependency, repoName: string) => {
  const { packageName, version } = dep;
  const origin = window.location.origin;
  return [
    {
      key: 'pip-index',
      label: 'pip (index)',
      code: `pip install --index-url ${origin}/repository/${repoName}/simple/ ${packageName}==${version}`
    },
    {
      key: 'pip-simple',
      label: 'pip install',
      code: `pip install ${packageName}==${version}`
    },
    {
      key: 'requirements',
      label: 'requirements.txt',
      code: `--index-url ${origin}/repository/${repoName}/simple/\n${packageName}==${version}`
    },
    {
      key: 'poetry',
      label: 'Poetry',
      code: `# Add source to pyproject.toml first\npoetry add ${packageName}==${version}`
    }
  ];
};

export const StorageExplorer: React.FC = () => {
  const { isAuthenticated, openLoginModal } = useAuth();
  const { data: repos, isLoading: reposLoading } = useRepositories();
  const [selectedRepo, setSelectedRepo] = useState<string>('maven-private');
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [activeSnippetTab, setActiveSnippetTab] = useState<string>('maven');
  const [copiedSnippetKey, setCopiedSnippetKey] = useState<string>('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string>('');

  const { data: treeNodes, isLoading: treeLoading } = useFileTree(selectedRepo);
  const { data: artifactDetails, isLoading: inspectLoading } = useInspectArtifact(selectedRepo, selectedFilePath);
  const deleteMutation = useDeleteArtifact();

  const currentRepo = repos?.find((r) => r.name === selectedRepo);
  const isMaven = currentRepo?.format === 'maven';
  const isNpm = currentRepo?.format === 'npm';
  const isDocker = currentRepo?.format === 'docker';
  const isPypi = currentRepo?.format === 'pypi';

  const mavenDep = isMaven ? parseMavenPath(selectedFilePath) : null;
  const npmDep = isNpm ? parseNpmPath(selectedFilePath) : null;
  const dockerDep = isDocker ? parseDockerPath(selectedFilePath) : null;
  const pypiDep = isPypi ? parsePypiPath(selectedFilePath) : null;

  React.useEffect(() => {
    if (isMaven) setActiveSnippetTab('maven');
    else if (isNpm) setActiveSnippetTab('npm');
    else if (isDocker) setActiveSnippetTab('docker-pull');
    else if (isPypi) setActiveSnippetTab('pip-index');
  }, [selectedFilePath, selectedRepo, isMaven, isNpm, isDocker, isPypi]);

  if (!isAuthenticated) {
    return (
      <div className="glass-panel rounded-3xl p-12 text-center max-w-lg mx-auto my-12 space-y-6 border border-slate-800 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center mx-auto shadow-lg shadow-blue-500/20">
          <ShieldAlert className="w-8 h-8 text-white" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-100">Sign In Required</h2>
          <p className="text-sm text-slate-400">
            Please sign in to browse repositories, inspect artifacts, and verify integrity checksums.
          </p>
        </div>
        <Button
          type="primary"
          size="large"
          icon={<LogIn className="w-4 h-4" />}
          onClick={openLoginModal}
          className="bg-blue-600 hover:bg-blue-500 border-none font-semibold text-sm h-11 px-8 rounded-xl shadow-lg shadow-blue-600/30 flex items-center gap-2 mx-auto"
        >
          Sign In Now
        </Button>
      </div>
    );
  }

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

  const handleCopySnippet = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippetKey(key);
    message.success('Snippet copied to clipboard');
    setTimeout(() => setCopiedSnippetKey(''), 2000);
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

              {/* Dependency Snippets Panel */}
              {(() => {
                let snippets: { key: string; label: string; code: string }[] = [];
                if (mavenDep) {
                  snippets = getMavenDependencySnippets(mavenDep);
                } else if (npmDep) {
                  snippets = getNpmDependencySnippets(npmDep);
                } else if (dockerDep) {
                  snippets = getDockerDependencySnippets(dockerDep);
                } else if (pypiDep) {
                  snippets = getPypiDependencySnippets(pypiDep, selectedRepo);
                }

                if (snippets.length === 0) return null;

                return (
                  <div className="space-y-3 pt-2 border-t border-slate-800/60">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                      <Terminal className="w-4 h-4 text-blue-400" />
                      <span>Dependency Declaration</span>
                    </div>
                    
                    <div className="bg-slate-950/80 rounded-xl border border-slate-800 overflow-hidden">
                      <Tabs
                        activeKey={activeSnippetTab}
                        onChange={setActiveSnippetTab}
                        size="small"
                        type="card"
                        className="snippet-tabs"
                        items={snippets.map((snippet) => ({
                          key: snippet.key,
                          label: <span className="text-[11px] font-medium px-1">{snippet.label}</span>,
                          children: (
                            <div className="relative p-3 font-mono text-xs text-slate-300 bg-slate-950 min-h-[75px] flex items-center justify-between group">
                              <pre className="m-0 overflow-x-auto whitespace-pre-wrap select-all max-w-[90%] leading-relaxed">
                                {snippet.code}
                              </pre>
                              <Button
                                type="text"
                                size="small"
                                icon={copiedSnippetKey === snippet.key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                                onClick={() => handleCopySnippet(snippet.code, snippet.key)}
                                className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity bg-slate-900 border border-slate-800 hover:bg-slate-850"
                              />
                            </div>
                          )
                        }))}
                      />
                    </div>
                  </div>
                );
              })()}

              {/* Checksum Hashes Panel */}
              <div className="space-y-3 pt-2 border-t border-slate-800/60">
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
