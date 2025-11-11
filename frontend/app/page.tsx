'use client';

import { useEffect, useState } from 'react';
import { api, type HealthStatus } from '@/lib/api';
import { Activity, Database, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'unhealthy':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case 'degraded':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Activity className="w-5 h-5 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-center">
          <XCircle className="w-5 h-5 text-red-600 mr-2" />
          <p className="text-red-800 dark:text-red-300">{error}</p>
        </div>
        <button
          onClick={fetchHealth}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Monitor your AI Chief of Staff system status
          </p>
        </div>
        <button
          onClick={fetchHealth}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* API Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">API Status</p>
              <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {health?.status || 'Unknown'}
              </p>
            </div>
            <div className={`p-3 rounded-full ${getStatusColor(health?.status || 'unknown')}`}>
              {getStatusIcon(health?.status || 'unknown')}
            </div>
          </div>
          <div className="mt-4">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(health?.status || 'unknown')}`}>
              {health?.environment || 'Unknown'}
            </span>
          </div>
        </div>

        {/* Database Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Database</p>
              <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {health?.database?.status || 'Unknown'}
              </p>
            </div>
            <div className={`p-3 rounded-full ${getStatusColor(health?.database?.status || 'unknown')}`}>
              <Database className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {health?.database?.database || 'Not connected'}
            </p>
            {health?.database?.error && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                {health.database.error}
              </p>
            )}
          </div>
        </div>

        {/* Version Info */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Version</p>
              <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {health?.version || 'Unknown'}
              </p>
            </div>
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
              <Activity className="w-5 h-5 text-blue-600 dark:text-blue-300" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Last checked: {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Endpoints</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">67</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Integrations</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">13</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Test Coverage</p>
          <p className="mt-2 text-2xl font-bold text-green-600">81%</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Sprints Complete</p>
          <p className="mt-2 text-2xl font-bold text-blue-600">3/6</p>
        </div>
      </div>

      {/* Feature Status */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Feature Status
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {[
            { name: 'Core Infrastructure', status: 'complete', sprint: 1 },
            { name: 'MCP Integration Framework', status: 'complete', sprint: 2 },
            { name: 'Meeting Intelligence', status: 'complete', sprint: 3 },
            { name: 'Insights & Briefings', status: 'pending', sprint: 4 },
            { name: 'Voice & Orchestration', status: 'pending', sprint: 5 },
            { name: 'Production Ready', status: 'pending', sprint: 6 },
          ].map((feature) => (
            <div key={feature.name} className="px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {feature.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Sprint {feature.sprint}</p>
              </div>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  feature.status === 'complete'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {feature.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
