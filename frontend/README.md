# AI Chief of Staff - Frontend

Modern Next.js frontend for the AI Chief of Staff API.

## Features

- **Dashboard**: System health monitoring and feature status
- **Integrations**: View and manage 13 platform integrations
- **Meetings**: Browse meeting recordings and AI-generated summaries
- **Briefings**: Morning briefs, evening wraps, and investor updates
- **Responsive Design**: Works on desktop and mobile
- **Dark Mode**: Automatic dark mode support

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Lucide Icons

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Backend API running on port 9000

### Installation

```bash
# Install dependencies
npm install
# or
bun install
```

### Development

```bash
# Start development server
npm run dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## API Connection

The frontend connects to the backend API at `http://127.0.0.1:9000` by default.

To change this, set the `NEXT_PUBLIC_API_URL` environment variable:

```bash
NEXT_PUBLIC_API_URL=https://your-api-url.com
```

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── page.tsx            # Dashboard (home)
│   ├── integrations/       # Integrations page
│   ├── meetings/           # Meetings page
│   ├── briefings/          # Briefings page
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Global styles
├── components/             # React components
│   └── Navigation.tsx      # Main navigation
├── lib/                    # Utilities
│   └── api.ts              # API client
└── public/                 # Static assets
```

## Available Pages

- `/` - Dashboard with system health
- `/integrations` - Platform integrations management
- `/meetings` - Meeting recordings and summaries
- `/briefings` - Daily briefs and reports
- `/insights` - Analytics and trends (coming soon)
- `/settings` - Application settings (coming soon)

## Development Notes

- The frontend uses Next.js 14 App Router
- All pages are client-side rendered (`'use client'`)
- API calls are made directly from components (no SSR for simplicity)
- Error handling includes graceful fallbacks

## License

Proprietary - AI Native Studio
