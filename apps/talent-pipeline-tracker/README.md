This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Authentication (AUTH-02)

This app now requires a valid session for every route except `/login` and `/register`. Auth is backed by `services/brasaland-api` (JWT):

- `NEXT_PUBLIC_AUTH_API_URL` — base URL of `services/brasaland-api` (defaults to `http://127.0.0.1:8010`). Set it in `.env.local`.
- The JWT is stored in `localStorage` after login/register and sent as `Authorization: Bearer <token>` on calls to the auth API (`services/auth.ts`).
- `app/components/auth-guard.tsx` is a client-side guard (wrapped around all routes in `app/layout.tsx`) that redirects unauthenticated users to `/login`.
- `/account/profile` shows the authenticated user (email, role) and lets them edit their linked profile (`name`, `phone`, `address`).
- Logging out (header button) clears the token and redirects to `/login`.
- Any protected call to `services/brasaland-api` (via `lib/auth-fetch.ts`) that gets a `401` clears the stored token, which makes `AuthGuard` redirect to `/login` automatically.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
