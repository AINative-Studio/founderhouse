# ZeroDB Integration Tests - Quick Start Guide

## 5-Minute Setup

### Step 1: Configure Credentials

Create or update `backend/.env` with your ZeroDB credentials:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add:

```bash
# ZeroDB Configuration (Required)
ZERODB_EMAIL=your-email@example.com
ZERODB_USERNAME=your-username
ZERODB_PASSWORD=your-password
ZERODB_API_KEY=your-api-key
ZERODB_PROJECT_ID=your-project-id
ZERODB_API_BASE_URL=https://api.ainative.studio

# Security (Required)
SECRET_KEY=your-secret-key-minimum-32-characters-for-security
```

**Don't have ZeroDB credentials?** Sign up at https://ainative.studio

### Step 2: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Run Tests

**Option A: Using the test runner (recommended)**

```bash
# Make script executable (first time only)
chmod +x tests/integration/run_tests.sh

# Run all tests
./tests/integration/run_tests.sh all

# Run specific category
./tests/integration/run_tests.sh memory
./tests/integration/run_tests.sh vector
./tests/integration/run_tests.sh auth

# Quick smoke test
./tests/integration/run_tests.sh quick
```

**Option B: Using pytest directly**

```bash
# Run all integration tests
pytest tests/integration/test_zerodb_integration.py -v -m integration

# Run specific test category
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations -v

# Run single test
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -v
```

---

## Test Runner Commands

The `run_tests.sh` script provides convenient shortcuts:

| Command | Description | Tests Run |
|---------|-------------|-----------|
| `all` | Run all integration tests | 64 tests |
| `auth` | Authentication tests | 5 tests |
| `memory` | Memory operations | 8 tests |
| `vector` | Vector operations | 12 tests |
| `table` | Table operations | 10 tests |
| `event` | Event operations | 6 tests |
| `admin` | Admin operations | 5 tests |
| `error` | Error handling | 10 tests |
| `edge` | Edge cases | 8 tests |
| `coverage` | Run with coverage report | All tests |
| `quick` | Quick smoke test | 5 tests |

---

## Understanding Test Output

### Successful Test
```
tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic PASSED

✓ Memory stored with ID: mem_abc123def456
```

### Failed Test
```
tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic FAILED

E   httpx.HTTPStatusError: 401 Unauthorized
```

### Test Summary
```
============================== ZERODB INTEGRATION TEST SUMMARY ==============================

Total Tests: 64

Tests by Category:
  - Authentication: 5 tests
  - Memory Operations: 8 tests
  - Vector Operations: 12 tests
  ...

Operations Covered:
  ✓ Memory: store_memory, search_memory, get_context
  ✓ Vector: store_vector, batch_upsert_vectors, search_vectors
  ...
```

---

## Common Issues

### Issue: Authentication Failed (401/500)

**Symptom**: `HTTPStatusError: 401 Unauthorized` or `500 Internal Server Error`

**Solution**:
1. Verify credentials in `.env` are correct
2. Ensure you're using the right username/password
3. Check that API key and project ID match
4. Test credentials manually: https://api.ainative.studio

### Issue: Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure you're in the backend directory
cd backend

# Verify Python path
python3 -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: No .env File

**Symptom**: Tests use default "test" credentials

**Solution**:
```bash
# Create .env from example
cd backend
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### Issue: Tests Hang or Timeout

**Symptom**: Tests don't complete or timeout

**Solution**:
1. Check internet connectivity
2. Verify ZeroDB API is accessible
3. Increase timeout in test configuration
4. Run single test to isolate issue

---

## What Gets Tested?

### Core Operations (17 operations)

**Memory (3)**:
- Store agent memory
- Search memories semantically
- Get conversation context

**Vector (5)**:
- Store embeddings (1536 dims)
- Batch upload vectors
- Semantic similarity search
- Retrieve vectors
- Delete vectors

**Table (5)**:
- Create NoSQL tables
- Insert data
- Query with filters
- Update rows
- Delete rows

**Event (2)**:
- Publish events
- Subscribe to topics

**Admin (2)**:
- Health checks
- Usage statistics

### Test Types (64 tests)

- **Happy Path**: Normal operations work correctly
- **Error Handling**: Invalid inputs handled properly
- **Edge Cases**: Boundary conditions tested
- **Isolation**: Data doesn't leak between tests
- **Performance**: Concurrent and rapid requests

---

## Next Steps

### View Detailed Results

```bash
# Generate HTML coverage report
./tests/integration/run_tests.sh coverage

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Tests

```bash
# Test only memory operations
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations -v

# Test specific function
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -v

# Test multiple categories
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations tests/integration/test_zerodb_integration.py::TestVectorOperations -v
```

### Debug Failed Tests

```bash
# Run with verbose output
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -vv -s

# Show local variables on failure
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -v -l

# Drop into debugger on failure
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -v --pdb
```

---

## Advanced Usage

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest tests/integration/test_zerodb_integration.py -n 4 -m integration
```

### Generate JSON Report

```bash
pytest tests/integration/test_zerodb_integration.py --json-report --json-report-file=test-report.json -m integration
```

### Run Only Failed Tests

```bash
# First run
pytest tests/integration/test_zerodb_integration.py -v -m integration

# Re-run only failures
pytest tests/integration/test_zerodb_integration.py -v -m integration --lf
```

### Watch for Changes

```bash
# Install pytest-watch
pip install pytest-watch

# Auto-run tests on file changes
ptw tests/integration/test_zerodb_integration.py -- -m integration
```

---

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/integration-tests.yml`:

```yaml
name: ZeroDB Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run integration tests
        env:
          ZERODB_USERNAME: ${{ secrets.ZERODB_USERNAME }}
          ZERODB_PASSWORD: ${{ secrets.ZERODB_PASSWORD }}
          ZERODB_API_KEY: ${{ secrets.ZERODB_API_KEY }}
          ZERODB_PROJECT_ID: ${{ secrets.ZERODB_PROJECT_ID }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
        run: |
          cd backend
          pytest tests/integration/ -v -m integration --json-report
```

---

## Best Practices

1. **Run before deployment** - Catch API issues early
2. **Monitor execution time** - Detect performance degradation
3. **Review failures immediately** - API changes affect integration
4. **Keep credentials secure** - Never commit .env files
5. **Use test runner** - Convenient and consistent
6. **Check coverage regularly** - Ensure comprehensive testing

---

## Getting Help

**For test issues**:
- Check this quick start guide
- Review the full [README.md](README.md)
- See [TEST_SUMMARY.md](TEST_SUMMARY.md) for details

**For ZeroDB issues**:
- Contact ZeroDB support
- Check API documentation at https://docs.ainative.studio
- Verify service status

**For pytest issues**:
- Pytest docs: https://docs.pytest.org
- asyncio mode: https://pytest-asyncio.readthedocs.io

---

**Ready to test?** Run `./tests/integration/run_tests.sh quick` to get started!
