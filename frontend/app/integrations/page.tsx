'use client';

import { useEffect, useState } from 'react';
import { api, type Integration } from '@/lib/api';
import { Plug, CheckCircle2, XCircle, AlertCircle, RefreshCw } from 'lucide-react';

const platformIcons: Record<string, string> = {
  zoom: '🎥',
  slack: '💬',
  discord: '🎮',
  gmail: '📧',
  outlook: '📨',
  monday: '📋',
  notion: '📝',
  loom: '🎬',
  fireflies: '🔥',
  otter: '🦦',
  granola: '📊',
  zerodb: '🗄️',
  zerovoice: '🎤',
};

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getIntegrations();
      setIntegrations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch integrations');
      // Show empty state even on error for demo
      setIntegrations([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'connected':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'pending':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
      default:
        return <Plug className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'connected':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  // Supported platforms for demo
  const supportedPlatforms = [
    { name: 'Zoom', platform: 'zoom', description: 'Meeting recordings and transcripts' },
    { name: 'Slack', platform: 'slack', description: 'Team communication and messages' },
    { name: 'Discord', platform: 'discord', description: 'Community and voice channels' },
    { name: 'Gmail', platform: 'gmail', description: 'Email management' },
    { name: 'Outlook', platform: 'outlook', description: 'Microsoft email and calendar' },
    { name: 'Monday.com', platform: 'monday', description: 'Task and project management' },
    { name: 'Notion', platform: 'notion', description: 'Notes and documentation' },
    { name: 'Loom', platform: 'loom', description: 'Video messages and screen recordings' },
    { name: 'Fireflies', platform: 'fireflies', description: 'AI meeting notes' },
    { name: 'Otter.ai', platform: 'otter', description: 'Voice transcription' },
    { name: 'Granola', platform: 'granola', description: 'KPI and metrics tracking' },
    { name: 'ZeroDB', platform: 'zerodb', description: 'Vector database' },
    { name: 'ZeroVoice', platform: 'zerovoice', description: 'Voice commands' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Integrations</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Connect and manage your platform integrations
          </p>
        </div>
        <button
          onClick={fetchIntegrations}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors inline-flex items-center"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
            <p className="text-yellow-800 dark:text-yellow-300">
              {error} - Showing supported platforms
            </p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Platforms</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">13</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">Connected</p>
          <p className="mt-2 text-3xl font-bold text-green-600">
            {integrations.filter(i => i.status === 'connected').length}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">Available</p>
          <p className="mt-2 text-3xl font-bold text-blue-600">
            {supportedPlatforms.length - integrations.length}
          </p>
        </div>
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {supportedPlatforms.map((platform) => {
          const integration = integrations.find(i => i.platform === platform.platform);
          const isConnected = integration?.status === 'connected';

          return (
            <div
              key={platform.platform}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center">
                  <span className="text-4xl mr-3">
                    {platformIcons[platform.platform] || '🔌'}
                  </span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {platform.name}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {platform.description}
                    </p>
                  </div>
                </div>
                {integration && getStatusIcon(integration.status)}
              </div>

              <div className="mt-4 flex items-center justify-between">
                {integration ? (
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(integration.status)}`}>
                    {integration.status}
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
                    Not Connected
                  </span>
                )}

                <button
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    isConnected
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {isConnected ? 'Configure' : 'Connect'}
                </button>
              </div>

              {integration?.last_synced_at && (
                <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                  Last synced: {new Date(integration.last_synced_at).toLocaleString()}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
