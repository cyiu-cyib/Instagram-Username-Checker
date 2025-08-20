# Instagram Username Checker (Oxylabs-enabled)

An asynchronous tool that checks if an Instagram username is available using the Oxylabs Real-Time Crawler API, with a fallback to direct requests.

## About
- Uses Oxylabs Real-Time Crawler to request https://www.instagram.com/<username>/ and treats HTTP 404 as available, anything else as unavailable.
- Fallback mode (when no Oxylabs credentials provided) performs direct HTTP GET requests. This can be less accurate and subject to rate limits.
- Results: available usernames are appended to hits.txt (or a custom output file).

This tool is for educational purposes only.

## Installation
- Python 3.9+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage
- Put usernames (one per line) in usernames.txt, or generate programmatically.
- Run with Oxylabs credentials via env vars or CLI flags.

```bash
# Using environment variables
export OXYLABS_USERNAME="your_user"
export OXYLABS_PASSWORD="your_pass"
python main.py -i usernames.txt -o hits.txt -c 50 --timeout 45

# Or via flags
python main.py --oxylabs-username your_user --oxylabs-password your_pass -c 50
```

Arguments:
- -i/--input: path to input usernames file (default usernames.txt)
- -o/--output: path for available usernames (default hits.txt)
- -c/--concurrency: number of concurrent checks (default 20)
- --retries: retry attempts on transient errors (default 3)
- --timeout: request timeout seconds (default 30)
- --oxylabs-username/--oxylabs-password: Oxylabs credentials (or use env vars)

## Username generation
To generate all 3- and 4-letter lowercase combinations in usernames.txt:

```python
import itertools, string
with open('usernames.txt', 'w') as f:
    for n in (3, 4):
        for combo in itertools.product(string.ascii_lowercase, repeat=n):
            f.write(''.join(combo) + '\n')
```

Note: This creates 17,576 (3-letter) + 456,976 (4-letter) = 474,552 usernames.

## Notes
- Only characters [A-Za-z0-9._] are considered valid; names starting/ending with '.' are skipped.
- Available usernames are appended to the output file.
