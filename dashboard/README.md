# pytrace Dashboard

React-based web dashboard for pytrace distributed tracing. Provides real-time visualization of traces, latency analysis, error tracking, and operations monitoring.

## Prerequisites

- Node.js 16+ and npm
- pytrace HTTP API server running (see [main README](../README.md) for setup instructions)

## Quick Start

### Installation

```bash
cd dashboard
npm install
```

### Development Server

Start the development server with hot module reloading:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173` by default.

### Building for Production

Create an optimized production build:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

## Testing

### Run All Tests

```bash
npm test
```

### Run Tests in UI Mode

Interactive test runner with visual interface:

```bash
npm run test:ui
```

### Generate Coverage Report

```bash
npm run test:coverage
```

Tests are located in the `tests/` directory and use vitest + React Testing Library.

## Features

- **Trace Explorer**: Browse and search distributed traces
- **Operations Dashboard**: Monitor service operations and request counts
- **Latency Analysis**: Visualize trace latencies and performance metrics
- **Error Analysis**: Track and analyze errors across services
- **Responsive Layout**: Optimized for desktop and tablet viewing

## API Integration

The dashboard connects to the pytrace HTTP API server.

### Configuration

Configure the API endpoint in `src/api/client.ts`:

```typescript
const api = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:5000'
})
```

Default endpoint: `http://localhost:5000`

### Environment Variables

Create a `.env` file to override API settings:

```env
VITE_API_URL=http://your-api-server:5000
```

## Project Structure

```
src/
  ├── components/       # React components (Dashboard, Trace Explorer, etc.)
  ├── api/             # API client configuration
  ├── types/           # TypeScript type definitions
  ├── App.tsx          # Main app component
  └── main.tsx         # Entry point

tests/
  └── components/      # Component unit tests
```

## Available Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm test` | Run tests once |
| `npm run test:ui` | Interactive test runner |
| `npm run test:coverage` | Generate coverage report |
| `npm run lint` | Lint TypeScript/React code |

## Technologies

- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Vitest**: Unit testing framework
- **React Testing Library**: Component testing utilities
- **Recharts**: Data visualization
- **Axios**: HTTP client
- **TanStack React Table**: Data table component

## Development Tips

- Check `TESTS_OVERVIEW.md` for detailed test documentation
- Use `npm run lint` to check code style before committing
- Tests must pass before deploying to production
- API responses are mocked in tests for faster, isolated test runs
