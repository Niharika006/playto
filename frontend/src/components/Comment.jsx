import { useState } from 'react';
import { like, unlike } from '../api';
import { formatDistanceToNow } from '../utils/date';

/**
 * Recursive Comment component for displaying threaded comments.
 * 
 * Performance note: This component renders the pre-built comment tree
 * from the API. The tree is constructed server-side in O(n) time,
 * so rendering here is also O(n) with no additional API calls.
 */
function Comment({ comment, onReply, depth = 0 }) {
  const [likeCount, setLikeCount] = useState(comment.like_count || 0);
  const [hasLiked, setHasLiked] = useState(comment.user_has_liked || false);

  // Limit visual nesting depth for readability
  const maxDepth = 4;
  const effectiveDepth = Math.min(depth, maxDepth);

  const handleLike = async () => {
    try {
      if (hasLiked) {
        await unlike('comment', comment.id);
        setLikeCount(prev => prev - 1);
        setHasLiked(false);
      } else {
        const result = await like('comment', comment.id);
        if (result.success) {
          setLikeCount(prev => prev + 1);
          setHasLiked(true);
        }
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  return (
    <div 
      className={`${effectiveDepth > 0 ? 'ml-6 pl-4 border-l-2 border-gray-200' : ''}`}
    >
      <div className="py-2">
        {/* Comment header */}
        <div className="flex items-center space-x-2 mb-1">
          <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
            <span className="text-gray-600 font-medium text-xs">
              {comment.author?.username?.[0]?.toUpperCase() || '?'}
            </span>
          </div>
          <span className="font-medium text-gray-900 text-sm">
            {comment.author?.username || 'Anonymous'}
          </span>
          <span className="text-xs text-gray-500">
            {formatDistanceToNow(comment.created_at)}
          </span>
        </div>

        {/* Comment body */}
        <p className="text-gray-800 text-sm pl-8 mb-2 whitespace-pre-wrap">
          {comment.body}
        </p>

        {/* Comment actions */}
        <div className="flex items-center space-x-4 text-xs text-gray-500 pl-8">
          <button 
            onClick={handleLike}
            className={`flex items-center space-x-1 hover:text-indigo-600 transition-colors ${
              hasLiked ? 'text-indigo-600' : ''
            }`}
          >
            <svg 
              className="w-4 h-4" 
              fill={hasLiked ? "currentColor" : "none"}
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
            <span>{likeCount}</span>
          </button>

          <button 
            onClick={() => onReply(comment.id)}
            className="hover:text-indigo-600 transition-colors"
          >
            Reply
          </button>
        </div>
      </div>

      {/* Nested children - recursive rendering */}
      {comment.children && comment.children.length > 0 && (
        <div className="mt-2">
          {comment.children.map(child => (
            <Comment 
              key={child.id} 
              comment={child} 
              onReply={onReply}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default Comment;
