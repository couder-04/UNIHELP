# UniHelp benchmark comparison

- Before: `benchmarks/current.csv`
- After: `benchmarks/phase1.csv`
- Before rows: 54 (54 successful)
- After rows: 54 (54 successful)
- Shared query_ids: 18

% change is `(before - after) / before * 100`. A positive value means the after number is lower. This file does **not** label a change as an improvement.

All query_ids appear in both files.

## Independent aggregates (all rows in each file)

| Metric | Before | After | % change |
| --- | ---: | ---: | ---: |
| Mean LLM calls/request | 1.48 | 1.22 | 17.50% |
| Mean Executor LLM calls/request | 0.17 | 0.17 | 0.00% |
| Mean total tokens/request | 3832.3 | 1794.9 | 53.16% |
| Mean latency (ms) | 27394.1 | 5786.1 | 78.88% |
| P50 latency (ms) | 6145.5 | 3798.8 | 38.19% |
| P95 latency (ms) | 125947.4 | 17365.0 | 86.21% |
| Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Paired comparison (shared query_ids only)

| Metric | Before | After | % change |
| --- | ---: | ---: | ---: |
| Mean LLM calls/request | 1.48 | 1.22 | 17.50% |
| Mean Executor LLM calls/request | 0.17 | 0.17 | 0.00% |
| Mean total tokens/request | 3832.3 | 1794.9 | 53.16% |
| Mean latency (ms) | 27394.1 | 5786.1 | 78.88% |
| P50 latency (ms) | 6145.5 | 3798.8 | 38.19% |
| P95 latency (ms) | 125947.4 | 17365.0 | 86.21% |
| Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Query-type breakdown (paired query_ids)

| query_type | Metric | Before | After | % change |
| --- | --- | ---: | ---: | ---: |
| single | Mean LLM calls/request | 0.39 | 0.50 | -28.57% |
| single | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| single | Mean total tokens/request | 407.7 | 552.1 | -35.43% |
| single | Mean latency (ms) | 2231.9 | 2832.0 | -26.89% |
| single | P50 latency (ms) | 6.0 | 4.7 | 21.67% |
| single | P95 latency (ms) | 13925.3 | 16356.4 | -17.46% |
| single | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| multi_independent | Mean LLM calls/request | 2.89 | 1.67 | 42.31% |
| multi_independent | Mean Executor LLM calls/request | 1.00 | 1.00 | 0.00% |
| multi_independent | Mean total tokens/request | 11057.6 | 1241.6 | 88.77% |
| multi_independent | Mean latency (ms) | 112885.2 | 6744.9 | 94.02% |
| multi_independent | P50 latency (ms) | 118320.4 | 3152.3 | 97.34% |
| multi_independent | P95 latency (ms) | 137879.3 | 15857.9 | 88.50% |
| multi_independent | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| multi_dependent | Mean LLM calls/request | 1.17 | 1.00 | 14.29% |
| multi_dependent | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| multi_dependent | Mean total tokens/request | 2523.8 | 2142.7 | 15.10% |
| multi_dependent | Mean latency (ms) | 8798.9 | 8587.0 | 2.41% |
| multi_dependent | P50 latency (ms) | 9593.8 | 7908.6 | 17.56% |
| multi_dependent | P95 latency (ms) | 12256.4 | 16706.1 | -36.31% |
| multi_dependent | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| ambiguous | Mean LLM calls/request | 2.56 | 2.67 | -4.35% |
| ambiguous | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| ambiguous | Mean total tokens/request | 5829.7 | 4196.2 | 28.02% |
| ambiguous | Mean latency (ms) | 29145.5 | 11293.5 | 61.25% |
| ambiguous | P50 latency (ms) | 7084.4 | 5807.1 | 18.03% |
| ambiguous | P95 latency (ms) | 111241.0 | 33511.1 | 69.88% |
| ambiguous | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |
| edge_* | Mean LLM calls/request | 1.42 | 1.00 | 29.41% |
| edge_* | Mean Executor LLM calls/request | 0.00 | 0.00 | 0.00% |
| edge_* | Mean total tokens/request | 2706.4 | 2099.2 | 22.44% |
| edge_* | Mean latency (ms) | 9003.1 | 3967.3 | 55.93% |
| edge_* | P50 latency (ms) | 6083.4 | 4146.9 | 31.83% |
| edge_* | P95 latency (ms) | 21475.7 | 6867.8 | 68.02% |
| edge_* | Mean estimated cost/request | 0.000000 | 0.000000 | 0.00% |

## Per-feature LLM calls (paired query_ids, avg/request)

| Feature | Before | After | % change |
| --- | ---: | ---: | ---: |
| Planner | 0.28 | 0.11 | 60.00% |
| Executor | 0.17 | 0.17 | 0.00% |
| Mess | 0.06 | 0.06 | 0.00% |
| Bus | 0.06 | 0.06 | 0.00% |
| Complaint | 0.30 | 0.28 | 6.25% |
| Room Booking | 0.11 | 0.11 | 0.00% |
| Attendance | 0.00 | 0.00 | 0.00% |
| Notice | 0.52 | 0.44 | 14.29% |
| Timetable | 0.00 | 0.00 | 0.00% |

## Notes

- Independent aggregates include unmatched query_ids; paired tables do not.
- Successful rows are those with `status == ok`.
- `cached_tokens` (when present in the CSVs) is LLM/provider caching, not application cache hits.
