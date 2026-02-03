import { formatDistanceToNow } from '../utils/date';

/**
 * PostCard component displaying a single post in the feed.
 */
function PostCard({ post, onClick, onLike }) {
  const handleLikeClick = (e) => {
    e.stopPropagation(); // Prevent triggering onClick
    onLike();
  };

  return (
    <div 
      className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="p-4">
        {/* Author and timestamp */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-indigo-600 font-medium text-sm">
                {post.author?.username?.[0]?.toUpperCase() || '?'}
              </span>
            </div>
            <span className="font-medium text-gray-900">
              {post.author?.username || 'Anonymous'}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {formatDistanceToNow(post.created_at)}
          </span>
        </div>

        {/* Post body */}
        <p className="text-gray-800 mb-4 whitespace-pre-wrap">
          {post.body}
        </p>

        {/* Actions */}
        <div className="flex items-center space-x-6 text-sm text-gray-500">
          <button 
            onClick={handleLikeClick}
            className={`flex items-center space-x-1 hover:text-indigo-600 transition-colors ${
              post.user_has_liked ? 'text-indigo-600' : ''
            }`}
          >
            <svg 
              className="w-5 h-5" 
              fill={post.user_has_liked ? "currentColor" : "none"}
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" 
              />
            </svg>
            <span>{post.like_count || 0}</span>
          </button>

          <div className="flex items-center space-x-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" 
              />
            </svg>
            <span>{post.comment_count || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PostCard;
