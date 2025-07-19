# Security Scan Results (2025-07-19)

## Bandit
```
Working... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
Run started:2025-07-19 23:36:29.391603

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 6448
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 29
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 3
		High: 26
Files skipped (0):
```

## pip-audit
```
{"dependencies": [], "fixes": []}
```

## npm audit
```
{
  "info": 0,
  "low": 0,
  "moderate": 3,
  "high": 2,
  "critical": 0,
  "total": 5
}
```

## cargo audit
```
{"database":{"advisory-count":792,"last-commit":"babf308081c6c1ad21495aa3128957b14146e7cb","last-updated":"2025-07-18T21:48:13+02:00"},"lockfile":{"dependency-count":1},"settings":{"target_arch":[],"target_os":[],"severity":null,"ignore":[],"informational_warnings":["unmaintained","unsound","notice"]},"vulnerabilities":{"found":false,"count":0,"list":[]},"warnings":{}}```

## govulncheck
```
No vulnerabilities found.
```

Dependency-Check was not executed due to missing tool installation (network restrictions).
