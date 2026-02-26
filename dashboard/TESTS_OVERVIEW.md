# Dashboard TDD - Failing Tests Written

## Test Structure (All Failing - Ready to Implement)

### Components & Tests Created

1. **Dashboard (Main Component)**
   - ✗ Render main dashboard with all sections
   - ✗ Navigation tabs for different views
   - ✗ Switch between tabs
   - ✗ Responsive layout on mobile
   - ✗ Auto-refresh data periodically
   - ✗ Handle API errors gracefully

2. **TraceExplorer Component**
   - ✗ Render trace explorer
   - ✗ Search input for trace ID
   - ✗ Operation name filter
   - ✗ Time range picker
   - ✗ Display trace list with spans
   - ✗ Filter traces by search input
   - ✗ Expand span to show attributes and events

3. **LatencyAnalysis Component**
   - ✗ Render latency analysis
   - ✗ Duration histogram chart
   - ✗ Display percentile metrics (p50, p95, p99)
   - ✗ Slowest operations list
   - ✗ Filter by operation name

4. **ErrorAnalysis Component**
   - ✗ Render error analysis
   - ✗ Error rate over time chart
   - ✗ Error count by operation
   - ✗ Recent errors with stack traces
   - ✗ Calculate and display error rates

5. **OperationsDashboard Component**
   - ✗ Render operations dashboard
   - ✗ Table of all operations with stats
   - ✗ Sort operations by different columns
   - ✗ Display operation statistics
   - ✗ Filter operations by name

## Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx (to implement)
│   │   ├── Dashboard.test.tsx (failing tests)
│   │   ├── TraceExplorer.tsx (to implement)
│   │   ├── TraceExplorer.test.tsx (failing tests)
│   │   ├── LatencyAnalysis.tsx (to implement)
│   │   ├── LatencyAnalysis.test.tsx (failing tests)
│   │   ├── ErrorAnalysis.tsx (to implement)
│   │   ├── ErrorAnalysis.test.tsx (failing tests)
│   │   ├── OperationsDashboard.tsx (to implement)
│   │   └── OperationsDashboard.test.tsx (failing tests)
│   ├── types/
│   │   └── index.ts (type definitions)
│   ├── test/
│   │   └── setup.ts (test configuration)
│   ├── App.tsx
│   ├── App.css
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
└── README.md
```

## Next Steps (Implementation)

1. Install dependencies: `npm install`
2. Run tests: `npm test` (all will fail)
3. Implement components one by one to make tests pass
4. Follow TDD: Each test drives the implementation

## Key Features to Implement

- [ ] Trace Explorer with search and filtering
- [ ] Latency Analysis with percentile charts
- [ ] Error Analysis with trend visualization
- [ ] Operations Dashboard with statistics
- [ ] Navigation between tabs
- [ ] API integration with mock/axios
- [ ] Error handling and loading states
- [ ] Responsive mobile design
- [ ] Auto-refresh functionality

## API Endpoints Used

- `GET /api/spans` - List spans with filters
- `GET /api/traces/{trace_id}` - Get specific trace
- `GET /api/operations` - Get operation statistics
- `GET /api/metrics/latency` - Latency percentiles
- `GET /api/errors` - Error statistics and recent errors
