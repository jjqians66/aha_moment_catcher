"use client"

import { useUser } from '@clerk/nextjs';
import { useEffect, useState } from 'react';

export default function ProductPage() {
  const { isLoaded, isSignedIn } = useUser();
  const [iframeKey, setIframeKey] = useState(0);

  useEffect(() => {
    // Get Clerk session token to pass to HTML page
    const getToken = async () => {
      if (isSignedIn && typeof window !== 'undefined') {
        try {
          const clerk = (window as any).Clerk;
          if (clerk?.session) {
            const token = await clerk.session.getToken();
            // Store token in sessionStorage so product.html can access it
            sessionStorage.setItem('clerk_token', token || '');
            // Trigger iframe reload to pick up the token
            setIframeKey(prev => prev + 1);
          }
        } catch (error) {
          console.error('Error getting Clerk token:', error);
        }
      }
    };
    getToken();
  }, [isSignedIn]);

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
        <div className="text-xl text-gray-600">Please sign in to access the app</div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen">
      <iframe
        key={iframeKey}
        src="/product.html"
        className="w-full h-full border-0"
        title="Aha Catcher"
      />
    </div>
  );
}
