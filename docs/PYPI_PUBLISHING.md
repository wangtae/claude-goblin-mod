# Publishing claude-goblin-mod to PyPI

This guide explains how to publish your fork to PyPI so users can install it with:

```bash
pip install claude-goblin-mod
```

## Prerequisites

1. **PyPI Account**: Register at [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. **TestPyPI Account** (recommended for testing): Register at [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/)
3. **API Token**: Create an API token on PyPI (Account Settings → API tokens)

## Step 1: Complete Package Configuration

Before publishing, update the TODOs in [pyproject.toml](../pyproject.toml):

```toml
[project]
name = "claude-goblin-mod"
version = "0.2.0"
authors = [
    {name = "Your Name"},  # ← Replace with your name
    {name = "Kurt Buhler"}  # Original author credit
]

[project.urls]
Homepage = "https://github.com/YOUR-USERNAME/claude-goblin-mod"  # ← Replace
Repository = "https://github.com/YOUR-USERNAME/claude-goblin-mod"  # ← Replace
Issues = "https://github.com/YOUR-USERNAME/claude-goblin-mod/issues"  # ← Replace
```

## Step 2: Install Build Tools

```bash
# Install build and upload tools
pip install build twine
```

## Step 3: Build the Package

```bash
# From the project root (where pyproject.toml is located)
cd /home/wangt/projects/personal/claude-goblin/claude-goblin-mod

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build
```

This creates two files in the `dist/` directory:
- `claude-goblin-mod-0.2.0.tar.gz` (source distribution)
- `claude-goblin-mod-0.2.0-py3-none-any.whl` (wheel distribution)

## Step 4: Test on TestPyPI (Recommended)

Before publishing to the real PyPI, test on TestPyPI:

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: <your TestPyPI API token>
```

Then test the installation:

```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ claude-goblin-mod

# Test the installation
ccu --version
ccu usage
```

If everything works, uninstall the test version:

```bash
pip uninstall claude-goblin-mod
```

## Step 5: Publish to PyPI

Once testing is successful, publish to the real PyPI:

```bash
# Upload to PyPI
python -m twine upload dist/*

# You'll be prompted for:
# Username: __token__
# Password: <your PyPI API token>
```

## Step 6: Verify Installation

After publishing, anyone can install your package:

```bash
pip install claude-goblin-mod
```

## Using API Tokens

For security, use API tokens instead of passwords:

### Create a PyPI API Token

1. Go to [https://pypi.org/manage/account/](https://pypi.org/manage/account/)
2. Navigate to "API tokens"
3. Click "Add API token"
4. Choose scope:
   - **Project-specific** (recommended): Only allows uploads to `claude-goblin-mod`
   - **Account-wide**: Allows uploads to all your projects
5. Copy the token (it starts with `pypi-`)

### Save Token in `.pypirc`

Create `~/.pypirc` to avoid entering credentials each time:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TESTPYPI-TOKEN-HERE
```

**Security**: Set restrictive permissions:

```bash
chmod 600 ~/.pypirc
```

## Updating the Package

When you make changes and want to release a new version:

1. **Update version** in [pyproject.toml](../pyproject.toml):
   ```toml
   version = "0.2.1"  # Increment version
   ```

2. **Rebuild and republish**:
   ```bash
   rm -rf dist/
   python -m build
   python -m twine upload dist/*
   ```

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Major** (1.0.0): Breaking changes
- **Minor** (0.2.0): New features, backward compatible
- **Patch** (0.2.1): Bug fixes, backward compatible

## Legal Considerations for Forks

Since this is a fork of the original `claude-goblin` project:

### 1. License Compliance

The original project uses the MIT License. You must:

- ✅ Keep the original MIT License file
- ✅ Credit the original author (Kurt Buhler) in `pyproject.toml`
- ✅ Link to the original project in README and project URLs
- ✅ Include copyright notice from the original

### 2. Package Naming

- ✅ Use a different name (`claude-goblin-mod`) to avoid confusion
- ✅ Clearly indicate this is a fork in the description
- ❌ Don't claim it as entirely your own work

### 3. Attribution in README

Your [README.md](../README.md) already includes:

```markdown
> **⚠️ FORK NOTICE**: This is a modified version of [claude-goblin](https://github.com/data-goblin/claude-goblin)
> by Kurt Buhler. If you want the original version, install `claude-goblin` instead.
```

This is good! Keep it prominent.

## Troubleshooting

### Error: "Filename has already been used"

This means you're trying to upload the same version again. You must increment the version number in `pyproject.toml`.

### Error: "Invalid distribution"

Check that your package builds correctly:

```bash
python -m build
# Look for errors in the output
```

### Error: "Package name already exists"

If `claude-goblin-mod` is already taken on PyPI, you'll need to choose a different name:

- `claude-goblin-wangt`
- `claude-goblin-enhanced`
- `claude-goblin-multi-pc`

Update the `name` field in `pyproject.toml` accordingly.

### Error: "403 Forbidden"

Check that:
- Your API token is correct and active
- You have permission to upload to the package (for updates)

## Continuous Integration (Optional)

For automatic publishing on GitHub releases, create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
```

Then add your PyPI API token as a GitHub secret named `PYPI_API_TOKEN`.

## Summary Checklist

Before publishing:

- [ ] Update `pyproject.toml` with your name and GitHub username
- [ ] Test the build: `python -m build`
- [ ] Upload to TestPyPI and test installation
- [ ] Create PyPI API token
- [ ] Upload to PyPI: `python -m twine upload dist/*`
- [ ] Test installation: `pip install claude-goblin-mod`
- [ ] Update README with installation instructions

After publishing:

- [ ] Tag the release on GitHub
- [ ] Announce the fork (if desired)
- [ ] Monitor for issues and bug reports

## Resources

- [PyPI Documentation](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
- [MIT License](https://opensource.org/licenses/MIT)
