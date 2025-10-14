# Quick Publish Guide

Fast reference for publishing updates to PyPI.

## First-Time Setup (Once)

```bash
# 1. Install tools
pip install build twine

# 2. Register on PyPI
# Visit: https://pypi.org/account/register/

# 3. Create API token
# Visit: https://pypi.org/manage/account/
# Create token → Copy it

# 4. Save token in ~/.pypirc
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
EOF

chmod 600 ~/.pypirc

# 5. Update pyproject.toml
# Replace YOUR-USERNAME with your GitHub username
# Replace "Your Name" with your actual name
```

## Every Release

```bash
# 1. Update version in pyproject.toml
#    Example: "0.2.0" → "0.2.1"

# 2. Clean, build, publish
cd /home/wangt/projects/personal/claude-goblin/claude-goblin-mod
rm -rf dist/
python -m build
python -m twine upload dist/*

# 3. Test installation
pip install --upgrade claude-goblin-mod
ccu --version
```

## Common Issues

| Error | Solution |
|-------|----------|
| "Filename already used" | Increment version in `pyproject.toml` |
| "Package name exists" | Choose different name in `pyproject.toml` |
| "403 Forbidden" | Check API token is correct |
| Build fails | Check `pyproject.toml` syntax |

## Version Numbering

- **0.2.0 → 0.2.1**: Bug fixes (patch)
- **0.2.0 → 0.3.0**: New features (minor)
- **0.2.0 → 1.0.0**: Breaking changes (major)
