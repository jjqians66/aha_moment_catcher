import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher([
  '/',              // Landing page is public
  '/sign-in(.*)',   // Sign-in pages
  '/sign-up(.*)',   // Sign-up pages
  '/api/webhooks(.*)',  // Webhooks (if needed)
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes (Next.js API routes, not Python)
    '/(api|trpc)(.*)',
  ],
};
