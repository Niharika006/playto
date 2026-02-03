import { useState, useEffect } from 'react';
import { fetchPost, createComment, like, unlike } from '../api';
import { useAuth } from '../context/AuthContext';
import { formatDistanceToNow } from '../utils/date';
import Comment from './Comment';

/**
 * PostDetail component displaying a single post with its threaded comments.
 */
function PostDetail({ postId, onBack, onAuthRequired }) {
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newComment, setNewComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState(null);
  
  const { user } = useAuth();

  useEffect(() => {
    loadPost();
  }, [postId]);

  const loadPost = async () => {
    try {
      setLoading(true);
      const data = await fetchPost(postId);
      setPost(data);
      setError(null);
    } catch (err) {
      setError('Failed to load post');
      console.error('Error loading post:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    
    if (!user) {
      onAuthRequired?.();
      return;
    }

    try {
      setSubmitting(true);
      await createComment(postId, newComment, replyingTo);
      setNewComment('');
      setReplyingTo(null);
      setError(null);
      // Reload post to get updated comments
      await loadPost();
    } catch (err) {
      setError('Failed to post comment.');
      console.error('Error posting comment:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleLikePost = async () => {
    if (!post) return;
    
    if (!user) {
      onAuthRequired?.();
      return;
    }

    try {
      if (post.user_has_liked) {
        await unlike('post', post.id);
        setPost({ ...post, like_count: post.like_count - 1, user_has_liked: false });
      } else {
        const result = await like('post', post.id);
        if (result.success) {
          setPost({ ...post, like_count: post.like_count + 1, user_has_liked: true });
        }
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  const handleReply = (commentId) => {
    setReplyingTo(commentId);
    // Focus the comment input
    document.getElementById('comment-input')?.focus();
  };

  const cancelReply = () => {
    setReplyingTo(null);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error || 'Post not found'}
        <button 
          onClick={onBack}
          className="ml-4 underline hover:no-underline"
        >
          Back to feed
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to feed
      </button>

      {/* Post */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-indigo-600 font-medium">
                {post.author?.username?.[0]?.toUpperCase() || '?'}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-900 block">
                {post.author?.username || 'Anonymous'}
              </span>
              <span className="text-sm text-gray-500">
                {formatDistanceToNow(post.created_at)}
              </span>
            </div>
          </div>
        </div>

        <p className="text-gray-800 text-lg mb-4 whitespace-pre-wrap">
          {post.body}
        </p>

        <div className="flex items-center space-x-6 text-sm text-gray-500 pt-4 border-t">
          <button 
            onClick={handleLikePost}
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
            <span>{post.like_count || 0} likes</span>
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
            <span>{post.comments?.length || 0} comments</span>
          </div>
        </div>
      </div>

      {/* Comment Form */}
      <div className="bg-white rounded-lg shadow p-4">
        {user ? (
          <form onSubmit={handleSubmitComment}>
            {replyingTo && (
              <div className="mb-2 flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                <span className="text-sm text-gray-600">
                  Replying to comment...
                </span>
                <button 
                  type="button" 
                  onClick={cancelReply}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Cancel
                </button>
              </div>
            )}
            <textarea
              id="comment-input"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder={replyingTo ? "Write a reply..." : "Write a comment..."}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              rows={2}
            />
            <div className="mt-2 flex justify-between items-center">
              <span className="text-sm text-gray-500">
                Commenting as <span className="font-medium">{user.username}</span>
              </span>
              <button
                type="submit"
                disabled={submitting || !newComment.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Posting...' : (replyingTo ? 'Reply' : 'Comment')}
              </button>
            </div>
          </form>
        ) : (
          <div className="text-center py-4">
            <p className="text-gray-600 mb-3">Sign in to join the conversation</p>
            <button
              onClick={onAuthRequired}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Sign In to Comment
            </button>
          </div>
        )}
      </div>

      {/* Comments Tree */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-gray-900">
            Comments ({post.comments?.length || 0})
          </h2>
        </div>
        <div className="p-4">
          {post.comments && post.comments.length > 0 ? (
            <div className="space-y-4">
              {post.comments.map(comment => (
                <Comment 
                  key={comment.id} 
                  comment={comment} 
                  onReply={handleReply}
                  depth={0}
                />
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No comments yet. Be the first to comment!
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default PostDetail;
