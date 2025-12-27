'use client';

import { useEffect, useState } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import Link from 'next/link';

interface Insight {
  id: string;
  title: string;
  transcript: string;
  summary: string | null;
  created_at: string;
  tags: string[];
  user_id: string;
}

export default function NotesPage() {
  const { getToken } = useAuth();
  const { isLoaded, isSignedIn } = useUser();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchInsights() {
      if (!isSignedIn) {
        setLoading(false);
        return;
      }

      try {
        const token = await getToken();
        if (!token) {
          setError('Not authenticated');
          setLoading(false);
          return;
        }

        const response = await fetch('/api/insights', {
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Failed to fetch: ${response.status}`);
        }

        const data = await response.json();
        setInsights(data.insights || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching insights:', err);
        setError(err instanceof Error ? err.message : 'Failed to load insights');
      } finally {
        setLoading(false);
      }
    }

    if (isLoaded) {
      fetchInsights();
    }
  }, [isLoaded, isSignedIn, getToken]);

  const handleDelete = async (insightId: string) => {
    // Confirmation dialog
    if (!confirm('Are you sure you want to delete this insight? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingId(insightId);
      const token = await getToken();
      if (!token) {
        setError('Not authenticated');
        return;
      }

      const response = await fetch(`/api/insights/${insightId}`, {
        method: 'DELETE',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to delete: ${response.status}`);
      }

      // Remove the deleted insight from the list
      setInsights(prev => prev.filter(insight => insight.id !== insightId));
      setError(null);
    } catch (err) {
      console.error('Error deleting insight:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete insight');
    } finally {
      setDeletingId(null);
    }
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="text-xl text-gray-600 mb-4">Please sign in to view your notes</div>
          <Link href="/" className="text-blue-600 hover:underline">Go to home</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Navigation */}
        <nav className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">📚 My Insights</h1>
          <div className="flex gap-4">
            <Link
              href="/product"
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors"
            >
              Record New
            </Link>
            <Link
              href="/"
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 px-6 rounded-lg transition-colors"
            >
              Home
            </Link>
          </div>
        </nav>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="text-gray-600">Loading your insights...</div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && insights.length === 0 && (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">No insights yet</h2>
            <p className="text-gray-600 mb-6">Start recording your Aha! moments to see them here.</p>
            <Link
              href="/product"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-8 rounded-lg transition-colors"
            >
              Record Your First Insight
            </Link>
          </div>
        )}

        {/* Insights List */}
        {!loading && !error && insights.length > 0 && (
          <div className="space-y-4">
            {insights.map((insight) => (
              <div
                key={insight.id}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow relative"
              >
                <div className="flex justify-between items-start mb-3">
                  <h2 className="text-xl font-bold text-gray-800 pr-4">{insight.title}</h2>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="text-sm text-gray-500">
                      {new Date(insight.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    <button
                      onClick={() => handleDelete(insight.id)}
                      disabled={deletingId === insight.id}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-1 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                      title="Delete this insight"
                    >
                      {deletingId === insight.id ? (
                        <span className="flex items-center gap-1">
                          <span className="animate-spin">⏳</span>
                          Deleting...
                        </span>
                      ) : (
                        '🗑️ Delete'
                      )}
                    </button>
                  </div>
                </div>

                <div className="mb-3">
                  <p className="text-gray-700 whitespace-pre-wrap">{insight.transcript}</p>
                </div>

                {insight.summary && (
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border-l-4 border-blue-500">
                    <h3 className="font-semibold text-gray-800 mb-2">🔍 Research Summary</h3>
                    <div
                      className="text-gray-700 prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: insight.summary }}
                    />
                  </div>
                )}

                {insight.tags && insight.tags.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {insight.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="bg-gray-100 text-gray-700 text-sm px-3 py-1 rounded-full"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

