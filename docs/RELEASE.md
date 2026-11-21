# Release Verification (`legends-youtube`)

Run all offline release, packaging, and knowledge-attachment checks from the repository root:

```bash
python scripts/check_release.py
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/smoke_installed_resources.py
```

When `legends-empire` is available locally, verify synthetic vault attachment, repeat attachment noop, upstream update preservation, and local-edit conflict refusal:

```bash
python scripts/verify_knowledge_attachment.py --empire-source ../legends-empire-public
```
