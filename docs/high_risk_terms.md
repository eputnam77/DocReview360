# High Risk Terms Configuration

Certain words in a document can signal potential legal or compliance issues. The
quality module checks text against a configurable list of high risk terms.

## Default terms

The package ships with a JSON file:

```json
[
  "urgent",
  "guarantee",
  "liability"
]
```

`docreview360.quality` loads this list when imported.

## Customising the list

Create your own JSON file and load it at runtime:

```python
from docreview360 import quality

quality.initialize_high_risk_terms("custom_terms.json")
quality.high_risk_warnings("Hazard ahead!")
```

This example tells the module to use the contents of
`custom_terms.json` for future checks.
