import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Feed from './components/Feed';
import Leaderboard from './components/Leaderboard';
import PostDetail from './components/PostDetail';
import AuthModal from './components/AuthModal';

function AppContent() {
  const [currentView, setCurrentView] = useState('feed');
  const [selectedPostId, setSelectedPostId] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  
  const { user, loading, logout } = useAuth();

  const handlePostClick = (postId) => {
    setSelectedPostId(postId);
    setCurrentView('post');
  };

  const handleBackToFeed = () => {
    setSelectedPostId(null);
    setCurrentView('feed');
  };

  const openLogin = () => {
    setAuthMode('login');
    setShowAuthModal(true);
  };

  const openRegister = () => {
    setAuthMode('register');
    setShowAuthModal(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 
            className="text-2xl font-bold text-indigo-600 cursor-pointer"
            onClick={handleBackToFeed}
          >
            Community Feed
          </h1>
          
          {/* Auth buttons */}
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-gray-700">
                  Hello, <span className="font-medium">{user.username}</span>
                </span>
                <button
                  onClick={logout}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={openLogin}
                  className="px-4 py-2 text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={openRegister}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Main Content Area */}
          <div className="flex-1">
            {currentView === 'feed' ? (
              <Feed onPostClick={handlePostClick} onAuthRequired={openLogin} />
            ) : (
              <PostDetail 
                postId={selectedPostId} 
                onBack={handleBackToFeed}
                onAuthRequired={openLogin}
              />
            )}
          </div>

          {/* Sidebar - Leaderboard */}
          <div className="w-80 flex-shrink-0">
            <Leaderboard />
          </div>
        </div>
      </main>

      {/* Auth Modal */}
      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        initialMode={authMode}
      />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
