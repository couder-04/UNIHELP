# UniHelp benchmark comparison

- Before: `benchmarks/current.csv`
- After: `benchmarks/fixed.csv`
- Before rows: 54 (54 successful)
- After rows: 54 (54 successful)
- Shared query_ids: 18

% change is `(before - after) / before * 100`. A positive value means the after number is lower. This file does **not** label a change as an improvement.

All query_ids appear in both files.

## Independent aggregates (all rows in each file)

| Metric | Before | After | % change |
| --- | ---: | ---: | ---: |
| Mean LLM calls/request | 1.48 | 0.96 | 35.00% |
| Mean Executor LLM calls/request | 0.17 | 0.17 | 0.00% |
| Mean total tokens/request | 3832.3 | 1546.5 | 59.64% |
| Mean latency (ms) | 27394.1 | 5550.9 | 79.74% |
| P50 latency (ms) | 6145.5 | 2870.8 | 53.29% |
| P95 latency (ms) | 125947.4 | 25319.5 | 79.90% |
| Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Paired comparison (shared query_ids only)

| Metric | Before | After | % change |
| --- | ---: | ---: | ---: |
| Mean LLM calls/request | 1.48 | 0.96 | 35.00% |
| Mean Executor LLM calls/request | 0.17 | 0.17 | 0.00% |
| Mean total tokens/request | 3832.3 | 1546.5 | 59.64% |
| Mean latency (ms) | 27394.1 | 5550.9 | 79.74% |
| P50 latency (ms) | 6145.5 | 2870.8 | 53.29% |
| P95 latency (ms) | 125947.4 | 25319.5 | 79.90% |
| Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Query-type breakdown (paired query_ids)

| query_type | Metric | Before | After | % change |
| --- | --- | ---: | ---: | ---: |
| single | Mean LLM calls/request | 0.39 | 0.00 | 100.00% |
| single | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| single | Mean total tokens/request | 407.7 | 0.0 | 100.00% |
| single | Mean latency (ms) | 2231.9 | 4.8 | 99.79% |
| single | P50 latency (ms) | 6.0 | 0.2 | 96.67% |
| single | P95 latency (ms) | 13925.3 | 26.2 | 99.81% |
| single | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| multi_independent | Mean LLM calls/request | 2.89 | 1.00 | 65.38% |
| multi_independent | Mean Executor LLM calls/request | 1.00 | 1.00 | 0.00% |
| multi_independent | Mean total tokens/request | 11057.6 | 552.6 | 95.00% |
| multi_independent | Mean latency (ms) | 112885.2 | 3246.9 | 97.12% |
| multi_independent | P50 latency (ms) | 118320.4 | 3201.6 | 97.29% |
| multi_independent | P95 latency (ms) | 137879.3 | 4220.9 | 96.94% |
| multi_independent | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| multi_dependent | Mean LLM calls/request | 1.17 | 1.00 | 14.29% |
| multi_dependent | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| multi_dependent | Mean total tokens/request | 2523.8 | 2126.5 | 15.74% |
| multi_dependent | Mean latency (ms) | 8798.9 | 3886.4 | 55.83% |
| multi_dependent | P50 latency (ms) | 9593.8 | 3630.6 | 62.16% |
| multi_dependent | P95 latency (ms) | 12256.4 | 5056.8 | 58.74% |
| multi_dependent | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| ambiguous | Mean LLM calls/request | 2.56 | 2.67 | -4.35% |
| ambiguous | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| ambiguous | Mean total tokens/request | 5829.7 | 4224.0 | 27.54% |
| ambiguous | Mean latency (ms) | 29145.5 | 20455.3 | 29.82% |
| ambiguous | P50 latency (ms) | 7084.4 | 10832.3 | -52.90% |
| ambiguous | P95 latency (ms) | 111241.0 | 51263.2 | 53.92% |
| ambiguous | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| edge_* | Mean LLM calls/request | 1.42 | 1.08 | 23.53% |
| edge_* | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| edge_* | Mean total tokens/request | 2706.4 | 2313.8 | 14.51% |
| edge_* | Mean latency (ms) | 9003.1 | 5251.9 | 41.67% |
| edge_* | P50 latency (ms) | 6083.4 | 3474.8 | 42.88% |
| edge_* | P95 latency (ms) | 21475.7 | 13987.7 | 34.87% |
| edge_* | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Per-feature LLM calls (paired query_ids, avg/request)

| Feature | Before | After | % change |
| --- | ---: | ---: | ---: |
| Planner | 0.28 | 0.11 | 60.00% |
| Executor | 0.17 | 0.17 | 0.00% |
| Mess | 0.06 | 0.06 | 0.00% |
| Bus | 0.06 | 0.07 | -33.33% |
| Complaint | 0.30 | 0.28 | 6.25% |
| Room Booking | 0.11 | 0.11 | 0.00% |
| Attendance | 0.00 | 0.00 | 0.00% |
| Notice | 0.52 | 0.17 | 67.86% |
| Timetable | 0.00 | 0.00 | 0.00% |

## Notes

- Independent aggregates include unmatched query_ids; paired tables do not.
- Successful rows are those with `status == ok`.
- `cached_tokens` (when present in the CSVs) is LLM/provider caching, not application cache hits.
