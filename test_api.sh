#!/bin/bash

echo "Testing CodeGraph API endpoints..."
echo

echo "1. Health check:"
curl -s http://localhost:8000/health | jq .
echo

echo "2. Database statistics:"
curl -s http://localhost:8000/stats | jq .
echo

echo "3. List snapshots:"
curl -s http://localhost:8000/snapshots | jq .
echo

echo "4. Get graph (limited):"
curl -s "http://localhost:8000/graph?limit=5" | jq '.nodes | length, .edges | length'
echo

echo "5. Validate conservation laws:"
curl -s http://localhost:8000/validate | jq '.total_violations, .errors, .warnings'
echo

echo "All tests complete!"
