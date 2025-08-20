# Task List

1. ✅ Analyze repository structure and current functionality
Reviewed README, main.py, and usernames.txt
2. ✅ Design integration with Oxylabs Real-Time Crawler API
Integrated via OxylabsClient using source=universal posting to /v1/queries, parsing status_code.
3. ✅ Refactor main.py to use Oxylabs API with async aiohttp
Refactored with aiohttp, Oxylabs client, fallback to direct client
4. ✅ Add CLI options, environment variable support, and username validation
Added argparse flags, OXYLABS_USERNAME/PASSWORD env vars, and username validation
5. ✅ Add retry and backoff logic, concurrency semaphore, and robust response parsing
Semaphore-controlled concurrency, exponential backoff, flexible response parsing
6. ⏳ Update README with new usage instructions and Oxylabs setup

7. ⏳ Add requirements.txt and .gitignore

8. ⏳ Smoke test locally (without real Oxylabs call), verify script runs

9. ⏳ Commit changes to git with clear message


