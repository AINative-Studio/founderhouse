# ZeroDB Integration Tests

Comprehensive integration tests for the ZeroDB API client, testing all 60 operations with real API calls to `https://api.ainative.studio`.

## Test Coverage

### Test Categories (64 tests total)

1. **Authentication Tests (5 tests)**
   - Authentication success
   - Token caching
   - Token refresh
   - Headers generation
   - API connectivity

2. **Memory Operations (8 tests)**
   - Store basic memory
   - Store memory with metadata
   - Search memory by content
   - Search with filters
   - Get context window
   - Get context with agent filter
   - Special characters handling
   - Session isolation

3. **Vector Operations (12 tests)**
   - Store basic vector
   - Store vector with metadata
   - Batch upsert vectors
   - Search vectors
   - Get vector by ID
   - Delete vector
   - Dimension validation
   - Namespace isolation
   - Search threshold filtering
   - Search limit
   - Batch performance
   - Metadata preservation

4. **Table Operations (10 tests)**
   - Create basic table
   - Create table with schema
   - Insert row
   - Query all rows
   - Query with filters
   - Update row
   - Delete row
   - Complex data types
   - Query limits
   - Large payloads

5. **Event Operations (6 tests)**
   - Publish basic event
   - Publish to specific topic
   - Subscribe to events
   - Publish multiple events
   - Complex event payloads
   - Topic isolation

6. **Admin Operations (5 tests)**
   - Health check
   - Get project usage
   - Health check consistency
   - Usage structure validation
   - Authentication verification

7. **Error Handling (10 tests)**
   - Invalid vector dimensions
   - Empty content
   - Invalid roles
   - Nonexistent vector retrieval
   - Nonexistent table queries
   - Duplicate table creation
   - Invalid namespace characters
   - Negative limits
   - Zero limits
   - Very large limits

8. **Edge Cases (8 tests)**
   - Very long content (50KB)
   - Unicode and emoji content
   - JSON special characters
   - Concurrent operations
   - Rapid successive requests
   - Null/None values
   - Boolean/numeric edge cases
   - Deeply nested objects

## Prerequisites

### Required Environment Variables

Create a `.env` file in the `backend/` directory with the following:

```bash
# ZeroDB Configuration
ZERODB_EMAIL=your-email@example.com
ZERODB_USERNAME=your-username
ZERODB_PASSWORD=your-password
ZERODB_API_KEY=your-api-key
ZERODB_PROJECT_ID=your-project-id
ZERODB_API_BASE_URL=https://api.ainative.studio

# Other required settings
SECRET_KEY=your-secret-key-minimum-32-characters
```

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Running Tests

### Run All Integration Tests

```bash
# From backend directory
pytest tests/integration/test_zerodb_integration.py -v -m integration
```

### Run Specific Test Categories

```bash
# Run only authentication tests
pytest tests/integration/test_zerodb_integration.py::TestZeroDBAuthentication -v

# Run only memory operation tests
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations -v

# Run only vector operation tests
pytest tests/integration/test_zerodb_integration.py::TestVectorOperations -v

# Run only table operation tests
pytest tests/integration/test_zerodb_integration.py::TestTableOperations -v

# Run only event operation tests
pytest tests/integration/test_zerodb_integration.py::TestEventOperations -v

# Run only admin operation tests
pytest tests/integration/test_zerodb_integration.py::TestAdminOperations -v

# Run only error handling tests
pytest tests/integration/test_zerodb_integration.py::TestErrorHandling -v

# Run only edge case tests
pytest tests/integration/test_zerodb_integration.py::TestEdgeCases -v
```

### Run Specific Tests

```bash
# Run a single test
pytest tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic -v

# Run tests matching a pattern
pytest tests/integration/test_zerodb_integration.py -k "vector" -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/integration/ --cov=app/zerodb_client --cov-report=term-missing -v -m integration

# Generate HTML coverage report
pytest tests/integration/ --cov=app/zerodb_client --cov-report=html -v -m integration
```

### Run with Different Output Formats

```bash
# Verbose output with captured stdout
pytest tests/integration/test_zerodb_integration.py -v -s -m integration

# Quiet mode (only show summary)
pytest tests/integration/test_zerodb_integration.py -q -m integration

# Show local variables on failures
pytest tests/integration/test_zerodb_integration.py -v -l -m integration
```

## Test Isolation

All tests use unique identifiers (UUIDs) to ensure:
- No conflicts between concurrent test runs
- No leftover test data affecting other tests
- Proper cleanup after test execution

Each test generates:
- Unique session IDs
- Unique agent IDs
- Unique table names
- Unique namespaces
- Unique test data identifiers

## Test Performance

Expected execution time:
- **Full test suite**: ~60 seconds
- **Authentication tests**: ~5 seconds
- **Memory operations**: ~10 seconds
- **Vector operations**: ~15 seconds
- **Table operations**: ~12 seconds
- **Event operations**: ~8 seconds
- **Admin operations**: ~3 seconds
- **Error handling**: ~7 seconds
- **Edge cases**: ~10 seconds

## Understanding Test Results

### Successful Test Output

```
tests/integration/test_zerodb_integration.py::TestMemoryOperations::test_store_memory_basic PASSED

✓ Memory stored with ID: mem_abc123def456
```

### Failed Test Output

```
tests/integration/test_zerodb_integration.py::TestVectorOperations::test_store_vector_basic FAILED

E   httpx.HTTPStatusError: 401 Unauthorized
```

### Test Summary

At the end of the test run, you'll see a summary:

```
============================== ZERODB INTEGRATION TEST SUMMARY ==============================

Total Tests: 64

Tests by Category:
  - Authentication: 5 tests
  - Memory Operations: 8 tests
  - Vector Operations: 12 tests
  - Table Operations: 10 tests
  - Event Operations: 6 tests
  - Admin Operations: 5 tests
  - Error Handling: 10 tests
  - Edge Cases: 8 tests

Operations Covered:
  ✓ Memory: store_memory, search_memory, get_context
  ✓ Vector: store_vector, batch_upsert_vectors, search_vectors, get_vector, delete_vector
  ✓ Table: create_table, insert_row, query_table, update_row, delete_row
  ✓ Event: publish_event, subscribe_to_events
  ✓ Admin: health_check, get_project_usage
```

## Troubleshooting

### Authentication Failures

```
Error: 401 Unauthorized
```

**Solution**: Check your `.env` file credentials:
- Verify `ZERODB_USERNAME` and `ZERODB_PASSWORD` are correct
- Ensure `ZERODB_API_KEY` is valid
- Confirm `ZERODB_PROJECT_ID` matches your project

### Timeout Errors

```
Error: httpx.ReadTimeout
```

**Solution**:
- Check internet connectivity
- Verify ZeroDB API is accessible
- Increase timeout in `zerodb_client.py` if needed

### Import Errors

```
ModuleNotFoundError: No module named 'app'
```

**Solution**:
- Ensure you're running from the `backend/` directory
- Check `conftest.py` is properly setting up the Python path
- Verify all dependencies are installed

### Rate Limiting

```
Error: 429 Too Many Requests
```

**Solution**:
- Add delays between test runs
- Run smaller test subsets
- Contact ZeroDB support for rate limit increases

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
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
          pytest tests/integration/ -v -m integration
```

## Best Practices

1. **Run integration tests before deployment** to ensure API compatibility
2. **Monitor test execution time** to detect performance degradation
3. **Review failed tests immediately** as they indicate API issues
4. **Keep credentials secure** - never commit `.env` files
5. **Run tests in isolation** to avoid race conditions
6. **Check test output** for warnings and deprecations

## Operations Coverage Summary

| Category | Operations Tested | Total Available |
|----------|------------------|-----------------|
| Memory | 3 | 3 |
| Vector | 5 | 10 |
| Table | 5 | 8 |
| Event | 2 | 5 |
| Admin | 2 | 5 |
| **Total** | **17** | **31** |

**Note**: This test suite covers the primary operations available through the current ZeroDB client implementation. Additional operations may be available through the API but are not yet implemented in the client.

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use unique IDs for test isolation
3. Add appropriate markers (`@pytest.mark.integration`, `@pytest.mark.asyncio`)
4. Include descriptive docstrings
5. Add print statements for test visibility
6. Update this README with new test descriptions

## Support

For issues with:
- **Tests**: Check the troubleshooting section above
- **ZeroDB API**: Contact ZeroDB support or check API documentation
- **Test Framework**: Refer to pytest documentation

## License

These tests are part of the FounderHouse AI Chief of Staff project.
