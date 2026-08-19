import React, { useState } from 'react';
import { Modal, Tabs, Button, Select, message } from 'antd';
import { useRepositories } from '../../api/queries';
import { Terminal, Copy, Check, ExternalLink } from 'lucide-react';

interface SnippetModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialRepoName?: string;
}

export const SnippetModal: React.FC<SnippetModalProps> = ({
  isOpen,
  onClose,
  initialRepoName,
}) => {
  const { data: repos } = useRepositories();
  const [selectedRepoName, setSelectedRepoName] = useState<string>(initialRepoName || 'maven-group');
  const [activeTab, setActiveTab] = useState<string>('maven');
  const [copiedKey, setCopiedKey] = useState<string>('');

  React.useEffect(() => {
    if (initialRepoName) {
      setSelectedRepoName(initialRepoName);
      const repo = repos?.find((r) => r.name === initialRepoName);
      if (repo) {
        setActiveTab(repo.format);
      }
    }
  }, [initialRepoName, repos]);

  const origin = window.location.origin;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    message.success('Snippet copied to clipboard');
    setTimeout(() => setCopiedKey(''), 2000);
  };

  const handleTabChange = (tabKey: string) => {
    setActiveTab(tabKey);
    if (!repos) return;
    const matchingRepos = repos.filter((r) => r.format === tabKey);
    if (matchingRepos.length === 0) return;
    const groupRepo = matchingRepos.find((r) => r.type === 'group');
    if (groupRepo) {
      setSelectedRepoName(groupRepo.name);
    } else {
      setSelectedRepoName(matchingRepos[0].name);
    }
  };

  // ================== SNIPPETS BUILDERS ==================

  const mavenSettingsXml = `<settings>
  <servers>
    <server>
      <id>zero9repo</id>
      <username>admin</username>
      <password>admin123</password> <!-- or your z9r_ API Token -->
    </server>
  </servers>
  <mirrors>
    <mirror>
      <id>zero9repo-mirror</id>
      <mirrorOf>*</mirrorOf>
      <url>${origin}/repository/${selectedRepoName}/</url>
    </mirror>
  </mirrors>
</settings>`;

  const mavenPomXml = `<project>
  ...
  <distributionManagement>
    <repository>
      <id>zero9repo</id>
      <name>Zero9Repo Private Hosted</name>
      <url>${origin}/repository/maven-private/</url>
    </repository>
  </distributionManagement>

  <repositories>
    <repository>
      <id>zero9repo</id>
      <url>${origin}/repository/${selectedRepoName}/</url>
    </repository>
  </repositories>
</project>`;

  const gradleBuild = `// build.gradle (Groovy DSL)
repositories {
    maven {
        url "${origin}/repository/${selectedRepoName}/"
        credentials {
            username = "admin"
            password = "admin123" // or z9r_ API Token
        }
    }
}

publishing {
    repositories {
        maven {
            url = "${origin}/repository/maven-private/"
            credentials {
                username = "admin"
                password = "admin123"
            }
        }
    }
}`;

  const npmrcContent = `registry=${origin}/repository/${selectedRepoName}/
//${window.location.host}/repository/${selectedRepoName}/:_authToken=z9r_YOUR_API_TOKEN
always-auth=true`;

  const npmPublishCmd = `# 1. Configure login or .npmrc
npm config set registry ${origin}/repository/npm-private/

# 2. Publish package
npm publish`;

  const dockerSnippets = `# 1. Login to Zero9Repo Registry
docker login ${window.location.host}
# Username: admin
# Password: admin123 (or API Token)

# 2. Tag your image
docker tag my-app:latest ${window.location.host}/my-app:1.0.0

# 3. Push container image
docker push ${window.location.host}/my-app:1.0.0

# 4. Pull container image
docker pull ${window.location.host}/my-app:1.0.0`;

  const pipConfContent = `# ~/.pip/pip.conf (Linux/macOS) or %APPDATA%\\pip\\pip.ini (Windows)
[global]
index-url = ${origin}/repository/${selectedRepoName}/simple/
trusted-host = ${window.location.hostname}`;

  const pypircContent = `# ~/.pypirc
[distutils]
index-servers =
    zero9repo

[zero9repo]
repository = ${origin}/repository/pypi-private/
username = __token__
password = z9r_YOUR_API_TOKEN`;

  const twineUploadCmd = `# Upload package via Twine
twine upload --repository-url ${origin}/repository/pypi-private/ dist/* -u __token__ -p z9r_YOUR_API_TOKEN`;

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-100">
          <Terminal className="w-5 h-5 text-blue-400" />
          <span>Client Connect & Configuration Snippets</span>
        </div>
      }
      open={isOpen}
      onCancel={onClose}
      width={780}
      footer={[
        <Button key="close" onClick={onClose} className="border-slate-700 text-slate-300">
          Close
        </Button>,
      ]}
    >
      <div className="space-y-4 pt-2">
        {/* Repo selector */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Active Repository:</span>
          <Select
            value={selectedRepoName}
            onChange={(val) => {
              setSelectedRepoName(val);
              const r = repos?.find((x) => x.name === val);
              if (r) setActiveTab(r.format);
            }}
            className="w-64"
            options={repos?.map((r) => ({
              label: `${r.name} (${r.format.toUpperCase()} ${r.type.toUpperCase()})`,
              value: r.name,
            }))}
          />
        </div>

        {/* Ecosystem Tabs */}
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={[
            {
              key: 'maven',
              label: <span className="font-semibold text-xs">☕ Maven</span>,
              children: (
                <div className="space-y-4">
                  {/* Maven settings.xml */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>1. Maven Configuration (<code>~/.m2/settings.xml</code>)</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'm2' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(mavenSettingsXml, 'm2')}
                      >
                        Copy settings.xml
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{mavenSettingsXml}</code>
                    </pre>
                  </div>

                  {/* Maven pom.xml */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>2. Project Deployment (<code>pom.xml</code>)</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'pom' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(mavenPomXml, 'pom')}
                      >
                        Copy pom.xml
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{mavenPomXml}</code>
                    </pre>
                  </div>
                </div>
              ),
            },
            {
              key: 'gradle',
              label: <span className="font-semibold text-xs">🐘 Gradle</span>,
              children: (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                    <span>Gradle Build File (<code>build.gradle</code>)</span>
                    <Button
                      size="small"
                      icon={copiedKey === 'gradle' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      onClick={() => handleCopy(gradleBuild, 'gradle')}
                    >
                      Copy build.gradle
                    </Button>
                  </div>
                  <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                    <code>{gradleBuild}</code>
                  </pre>
                </div>
              ),
            },
            {
              key: 'npm',
              label: <span className="font-semibold text-xs">📦 NPM</span>,
              children: (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>1. NPM Project Config (<code>.npmrc</code>)</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'npmrc' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(npmrcContent, 'npmrc')}
                      >
                        Copy .npmrc
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{npmrcContent}</code>
                    </pre>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>2. Publish Package CLI</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'npm-pub' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(npmPublishCmd, 'npm-pub')}
                      >
                        Copy Commands
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{npmPublishCmd}</code>
                    </pre>
                  </div>
                </div>
              ),
            },
            {
              key: 'docker',
              label: <span className="font-semibold text-xs">🐳 Docker</span>,
              children: (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                    <span>Docker CLI Workflow</span>
                    <Button
                      size="small"
                      icon={copiedKey === 'docker' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      onClick={() => handleCopy(dockerSnippets, 'docker')}
                    >
                      Copy Commands
                    </Button>
                  </div>
                  <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                    <code>{dockerSnippets}</code>
                  </pre>
                </div>
              ),
            },
            {
              key: 'pypi',
              label: <span className="font-semibold text-xs">🐍 Pip / PyPI</span>,
              children: (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>1. Pip Client Configuration (<code>pip.conf</code>)</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'pip' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(pipConfContent, 'pip')}
                      >
                        Copy pip.conf
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{pipConfContent}</code>
                    </pre>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span>2. Twine Upload Config (<code>~/.pypirc</code>)</span>
                      <Button
                        size="small"
                        icon={copiedKey === 'twine' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={() => handleCopy(twineUploadCmd, 'twine')}
                      >
                        Copy Twine Cmd
                      </Button>
                    </div>
                    <pre className="p-3 rounded-xl bg-[#070b14] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto">
                      <code>{twineUploadCmd}</code>
                    </pre>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </div>
    </Modal>
  );
};
