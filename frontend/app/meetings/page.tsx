'use client';

import { Video, Calendar, Users, Clock } from 'lucide-react';

export default function MeetingsPage() {
  // Demo meetings data
  const meetings = [
    {
      id: '1',
      title: 'Weekly Team Standup',
      source: 'zoom',
      date: '2025-11-10T10:00:00',
      duration: 30,
      participants: 8,
      status: 'completed',
      hasSummary: true,
    },
    {
      id: '2',
      title: 'Investor Update Call',
      source: 'zoom',
      date: '2025-11-09T14:00:00',
      duration: 45,
      participants: 3,
      status: 'completed',
      hasSummary: true,
    },
    {
      id: '3',
      title: 'Product Roadmap Discussion',
      source: 'zoom',
      date: '2025-11-08T11:00:00',
      duration: 60,
      participants: 12,
      status: 'completed',
      hasSummary: false,
    },
  ];

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'zoom':
        return '🎥';
      case 'fireflies':
        return '🔥';
      case 'otter':
        return '🦦';
      default:
        return '📹';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Meetings</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            View and manage meeting recordings and summaries
          </p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
          Ingest Meeting
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Meetings</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{meetings.length}</p>
            </div>
            <Video className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">This Week</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">2</p>
            </div>
            <Calendar className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Duration</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">45m</p>
            </div>
            <Clock className="w-8 h-8 text-yellow-600" />
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Participants</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">23</p>
            </div>
            <Users className="w-8 h-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Meetings List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Meetings
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {meetings.map((meeting) => (
            <div key={meeting.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4">
                  <span className="text-3xl">{getSourceIcon(meeting.source)}</span>
                  <div>
                    <h3 className="text-base font-medium text-gray-900 dark:text-white">
                      {meeting.title}
                    </h3>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                      <span className="flex items-center">
                        <Calendar className="w-4 h-4 mr-1" />
                        {new Date(meeting.date).toLocaleDateString()}
                      </span>
                      <span className="flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        {meeting.duration} min
                      </span>
                      <span className="flex items-center">
                        <Users className="w-4 h-4 mr-1" />
                        {meeting.participants} participants
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {meeting.hasSummary ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
                      Summarized
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
                      Pending
                    </span>
                  )}
                  <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                    View
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
