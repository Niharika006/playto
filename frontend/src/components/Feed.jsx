import { useState, useEffect } from 'react';
import { fetchPosts, createPost, like, unlike } from '../api';
import { useAuth } from '../context/AuthContext';
import PostCard from './PostCard';

/**
 * Feed component displaying list of posts with ability to create new ones.
 */
function Feed({ onPostClick, onAuthRequired }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newPostBody, setNewPostBody] = useState('');
  const [creating, setCreating] = useState(false);
  
  const { user } = useAuth();

  // Fetch posts on mount
  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    try {
      setLoading(true);
      const data = await fetchPosts();
      // Handle paginated response
      setPosts(data.results || data);
      setError(null);
    } catch (err) {
      setError('Failed to load posts. Is the backend running?');
      console.error('Error loading posts:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePost = async (e) => {
    e.preventDefault();
    if (!newPostBody.trim()) return;
    
    if (!user) {
      onAuthRequired?.();
      return;
    }

    try {
      setCreating(true);
      const newPost = await createPost(newPostBody);
      setPosts([{ ...newPost, like_count: 0, comment_count: 0 }, ...posts]);
      setNewPostBody('');
      setError(null);
    } catch (err) {
      setError('Failed to create post.');
      console.error('Error creating post:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleLike = async (postId) => {
    if (!user) {
      onAuthRequired?.();
      return;
    }
    
    const post = posts.find(p => p.id === postId);
    if (!post) return;

    try {
      if (post.user_has_liked) {
        await unlike('post', postId);
        setPosts(posts.map(p => 
          p.id === postId 
            ? { ...p, like_count: p.like_count - 1, user_has_liked: false }
            : p
        ));
      } else {
        const result = await like('post', postId);
        if (result.success) {
          setPosts(posts.map(p => 
            p.id === postId 
              ? { ...p, like_count: p.like_count + 1, user_has_liked: true }
              : p
          ));
        }
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Create Post Form */}
      <div className="bg-white rounded-lg shadow p-4">
        {user ? (
          <form onSubmit={handleCreatePost}>
            <textarea
              value={newPostBody}
              onChange={(e) => setNewPostBody(e.target.value)}
              placeholder="What's on your mind?"
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              rows={3}
            />
            <div className="mt-3 flex justify-between items-center">
              <span className="text-sm text-gray-500">
                Posting as <span className="font-medium">{user.username}</span>
              </span>
              <button
                type="submit"
                disabled={creating || !newPostBody.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? 'Posting...' : 'Post'}
              </button>
            </div>
          </form>
        ) : (
          <div className="text-center py-4">
            <p className="text-gray-600 mb-3">Sign in to share your thoughts</p>
            <button
              onClick={onAuthRequired}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Sign In to Post
            </button>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Posts List */}
      {posts.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No posts yet. Be the first to post!
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map(post => (
            <PostCard
              key={post.id}
              post={post}
              onClick={() => onPostClick(post.id)}
              onLike={() => handleLike(post.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default Feed;
