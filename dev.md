
## Development

```bash
git clone https://github.com/yourname/fastapi-class-router
cd fastapi-class-router
pip install -e ".[dev]"
pytest
```

---

## Publishing to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

---

## License

MIT