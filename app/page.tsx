"use client"

import Link from 'next/link';
import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-12">
        {/* Navigation */}
        <nav className="flex justify-between items-center mb-12">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-200">
            Aha! Catcher
          </h1>
          <div>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors w-32">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <div className="flex items-center gap-4">
                <Link
                  href="/product"
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors w-32 text-center"
                >
                  Go to App
                </Link>
                <UserButton afterSignOutUrl="/" />
              </div>
            </SignedIn>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="text-center py-24">
          <h2 className="text-6xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-6">
            Capture Your
            <br />
            Aha! Moments
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-400 mb-12 max-w-2xl mx-auto">
            Record your spontaneous insights, get AI-powered summaries, and automatically save them to Notion
          </p>

          <SignedOut>
            <div className="flex flex-col items-center">
              <SignInButton mode="modal">
                <button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all transform hover:scale-105 w-48">
                  Sign In
                </button>
              </SignInButton>
              <p className="text-gray-500 mt-3 text-sm">It is free!</p>
            </div>
          </SignedOut>
          <SignedIn>
            <Link href="/product">
              <button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all transform hover:scale-105 w-48">
                Open App
              </button>
            </Link>
          </SignedIn>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-8 mt-16 max-w-5xl mx-auto">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
            <div className="text-4xl mb-4">🎤</div>
            <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-gray-200">Voice Recording</h3>
            <p className="text-gray-600 dark:text-gray-400">
              Click to record your thoughts instantly. No typing required.
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-gray-200">AI Transcription</h3>
            <p className="text-gray-600 dark:text-gray-400">
              Automatic transcription powered by OpenAI Whisper.
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
            <div className="text-4xl mb-4">📝</div>
            <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-gray-200">Notion Integration</h3>
            <p className="text-gray-600 dark:text-gray-400">
              Save directly to your Notion workspace with one click.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
