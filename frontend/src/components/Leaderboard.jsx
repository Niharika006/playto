import { useState, useEffect } from 'react';
import { fetchLeaderboard } from '../api';

/**
 * Leaderboard component showing top 5 users by karma in last 24 hours.
 * 
 * The data is calculated server-side via aggregation query:
 * - Filter KarmaTransaction where created_at >= now - 24h
 * - GROUP BY user_id
 * - SUM(points) as total_karma
 * - ORDER BY total_karma DESC
 * - LIMIT 5
 */
function Leaderboard() {
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadLeaderboard();
    // Refresh leaderboard every 60 seconds
    const interval = setInterval(loadLeaderboard, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadLeaderboard = async () => {
    try {
      const data = await fetchLeaderboard();
      setLeaders(data);
      setError(null);
    } catch (err) {
      console.error('Error loading leaderboard:', err);
      setError('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  // Medal colors for top 3
  const getMedalStyle = (rank) => {
    switch (rank) {
      case 1:
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 2:
        return 'bg-gray-100 text-gray-700 border-gray-300';
      case 3:
        return 'bg-orange-100 text-orange-800 border-orange-300';
      default:
        return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow sticky top-6">
      <div className="p-4 border-b">
        <h2 className="font-semibold text-gray-900 flex items-center">
          <svg className="w-5 h-5 mr-2 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clipRule="evenodd" />
          </svg>
          Top Karma (24h)
        </h2>
      </div>

      <div className="p-4">
        {loading ? (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
          </div>
        ) : error ? (
          <p className="text-red-500 text-sm text-center py-4">{error}</p>
        ) : leaders.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">
            No karma earned in the last 24 hours yet!
          </p>
        ) : (
          <ul className="space-y-2">
            {leaders.map((leader) => (
              <li 
                key={leader.user_id}
                className={`flex items-center justify-between p-3 rounded-lg border ${getMedalStyle(leader.rank)}`}
              >
                <div className="flex items-center space-x-3">
                  <span className="font-bold text-lg w-6">
                    {leader.rank === 1 && '🥇'}
                    {leader.rank === 2 && '🥈'}
                    {leader.rank === 3 && '🥉'}
                    {leader.rank > 3 && `#${leader.rank}`}
                  </span>
                  <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center border">
                    <span className="font-medium text-sm text-gray-700">
                      {leader.username?.[0]?.toUpperCase() || '?'}
                    </span>
                  </div>
                  <span className="font-medium">{leader.username}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="font-bold text-lg">{leader.total_karma}</span>
                  <span className="text-xs opacity-75">karma</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t">
        <p className="text-xs text-gray-500 text-center">
          Updated every minute • Post likes = +5 karma • Comment likes = +1 karma
        </p>
      </div>
    </div>
  );
}

export default Leaderboard;
