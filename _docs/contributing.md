# Contributing Guide

This guide covers the development workflow, guidelines, and best practices for contributing to Bob Digital Investigator.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Code Style](#code-style)
3. [Git Workflow](#git-workflow)
4. [Testing](#testing)
5. [Pull Request Process](#pull-request-process)
6. [Adding New Features](#adding-new-features)
7. [Bug Reports](#bug-reports)
8. [Code Review](#code-review)

---

## Development Setup

### Prerequisites

- **Python 3.12+** - Backend development
- **Bun 1.2+** or **Node.js 20+** - Frontend development
- **Redis 7+** - Message broker and cache
- **PostgreSQL 17** - Database
- **Git** - Version control
- **Docker & Docker Compose** (optional) - Containerized development

### Clone Repository

```bash
git clone https://github.com/juanvictorqwerty/Bob-Digital-Investigator.git
cd Bob-Digital-Investigator
```

### Backend Setup

```bash
# Create virtual environment
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start Redis (in separate terminal)
redis-server

# Start Celery worker (in separate terminal)
celery -A _Project worker -l info

# Start Django server
python manage.py runserver
```

### Frontend Setup

```bash
cd client

# Install dependencies
bun install

# Start development server
bun run dev
```

### Docker Development (Alternative)

```bash
# Copy and configure .env
cp server/.env.example server/.env
# Edit server/.env

# Start all services
docker compose up --build

# View logs
docker compose logs -f
```

---

## Code Style

### Python (Backend)

**Style Guide:** PEP 8

**Tools:**
- **Black** - Code formatting
- **Flake8** - Linting
- **isort** - Import sorting
- **mypy** - Type checking (optional)

**Format Code:**
```bash
cd server
black .
flake8
isort .
```

**Naming Conventions:**
- **Variables/Functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

**Example:**
```python
# Good
def calculate_confidence_score(results: list[dict]) -> float:
    MAX_SCORE = 100
    total_score = 0
    return total_score / MAX_SCORE

# Bad
def CalculateConfidence(results):
    maxscore = 100
    total = 0
    return total / maxscore
```

### TypeScript (Frontend)

**Style Guide:** Airbnb TypeScript Style Guide

**Tools:**
- **ESLint** - Linting (flat config)
- **Prettier** - Code formatting

**Format Code:**
```bash
cd client
bun run lint
bun run format
```

**Naming Conventions:**
- **Variables/Functions:** `camelCase`
- **Components:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Files:** `kebab-case.tsx` for components, `camelCase.ts` for utilities

**Example:**
```typescript
// Good
interface SearchResult {
  id: string;
  verdict: string;
}

const calculateConfidence = (results: SearchResult[]): number => {
  const MAX_SCORE = 100;
  return results.length / MAX_SCORE;
};

// Bad
interface search_result {
  Id: string;
  Verdict: string;
}

const CalculateConfidence = (results) => {
  const maxscore = 100;
  return results.length / maxscore;
};
```

### Commit Messages

**Format:** `<type>(<scope>): <subject>`

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(robot): add support for Claude 3 Sonnet model
fix(reversewebsearch): handle empty search results gracefully
docs(api): update API reference with new endpoints
test(discover): add unit tests for research generator
refactor(data_processor): extract scoring logic into separate function
```

---

## Git Workflow

### Branch Naming

**Format:** `<type>/<description>`

**Examples:**
```
feature/add-claude-model
fix/backward-url-cors
docs/update-readme
refactor/extract-scoring-logic
```

### Workflow

1. **Create feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-new-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat(module): add new feature"
   ```

3. **Push to remote:**
   ```bash
   git push origin feature/my-new-feature
   ```

4. **Create Pull Request on GitHub**

5. **After approval, merge to main:**
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/my-new-feature
   ```

### Branch Protection

The `main` branch is protected:
- Requires PR approval
- Requires passing CI tests
- No direct pushes allowed

---

## Testing

### Backend Tests

**Framework:** Django test runner

**Run All Tests:**
```bash
cd server
python manage.py test
```

**Run Specific App Tests:**
```bash
python manage.py test authentication
python manage.py test reversewebsearch
python manage.py test robot
python manage.py test discover
```

**Run Specific Test:**
```bash
python manage.py test reversewebsearch.tests.TestDataProcessor
python manage.py test reversewebsearch.tests.TestDataProcessor.test_normalize_url
```

**With Coverage:**
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

**Test Structure:**
```python
from django.test import TestCase

class TestDataProcessor(TestCase):
    def setUp(self):
        # Setup test data
        pass

    def test_normalize_url(self):
        # Test code
        self.assertEqual(expected, actual)

    def test_score_result(self):
        # Test code
        self.assertGreater(score, 0)
```

### Frontend Tests

**Framework:** Bun test runner

**Run All Tests:**
```bash
cd client
bun test
```

**Run Specific Test:**
```bash
bun test src/__tests__/components/UploadCard.test.tsx
```

**With Coverage:**
```bash
bun test --coverage
```

**Test Structure:**
```typescript
import { describe, it, expect, beforeEach } from 'bun:test';

describe('UploadCard', () => {
  beforeEach(() => {
    // Setup
  });

  it('should upload image successfully', async () => {
    // Test code
    expect(result).toBeDefined();
  });

  it('should handle upload errors', async () => {
    // Test code
    expect(error).toBeDefined();
  });
});
```

### Writing Tests

**Guidelines:**
- Write tests for all new features
- Write tests for bug fixes
- Aim for >80% code coverage
- Test edge cases
- Mock external APIs
- Use descriptive test names

**Example:**
```python
# Good
def test_normalize_url_removes_utm_parameters(self):
    url = "https://example.com/page?utm_source=twitter"
    result = normalize_url(url)
    self.assertEqual(result, "https://example.com/page")

# Bad
def test_url(self):
    url = "https://example.com/page?utm_source=twitter"
    result = normalize_url(url)
    self.assertEqual(result, "https://example.com/page")
```

---

## Pull Request Process

### Before Creating PR

1. **Update your branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout feature/my-feature
   git rebase main
   ```

2. **Run tests:**
   ```bash
   # Backend
   cd server && python manage.py test

   # Frontend
   cd client && bun test
   ```

3. **Run linters:**
   ```bash
   # Backend
   black . && flake8

   # Frontend
   bun run lint
   ```

4. **Update documentation** if needed

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)

## Related Issues
Closes #123
```

### Review Process

1. **CI runs automatically** - Tests must pass
2. **Code review** - At least one approval required
3. **Address comments** - Make requested changes
4. **Merge** - Squash and merge to main

---

## Adding New Features

### Backend Feature

1. **Create model** (if needed):
   ```python
   # In models.py
   class NewFeature(models.Model):
       name = models.CharField(max_length=255)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

2. **Create serializer:**
   ```python
   # In serializers.py
   class NewFeatureSerializer(serializers.ModelSerializer):
       class Meta:
           model = NewFeature
           fields = '__all__'
   ```

3. **Create view:**
   ```python
   # In views.py
   class NewFeatureView(APIView):
       def post(self, request):
           # Implementation
           pass
   ```

4. **Add URL route:**
   ```python
   # In urls.py
   path('new-feature/', NewFeatureView.as_view(), name='new-feature')
   ```

5. **Write tests:**
   ```python
   # In tests.py
   class TestNewFeature(TestCase):
       def test_create_feature(self):
           # Test code
           pass
   ```

6. **Update API documentation** in `_docs/api-reference.md`

### Frontend Feature

1. **Create component:**
   ```typescript
   // In components/NewFeature.tsx
   export default function NewFeature() {
     return <div>New Feature</div>;
   }
   ```

2. **Add page route:**
   ```typescript
   // In app/new-feature/page.tsx
   import NewFeature from '@/components/NewFeature';
   export default function Page() {
     return <NewFeature />;
   }
   ```

3. **Add API integration:**
   ```typescript
   const response = await axios.post('/api/new-feature/', data, {
     headers: { Authorization: `Token ${token}` }
   });
   ```

4. **Write tests:**
   ```typescript
   // In __tests__/components/NewFeature.test.tsx
   describe('NewFeature', () => {
     it('should render correctly', () => {
       // Test code
     });
   });
   ```

5. **Update documentation** if needed

---

## Bug Reports

### Reporting a Bug

When reporting a bug, include:

1. **Description:** Clear description of the bug
2. **Steps to Reproduce:** Step-by-step instructions
3. **Expected Behavior:** What should happen
4. **Actual Behavior:** What actually happens
5. **Environment:**
   - OS: (e.g., Ubuntu 22.04)
   - Python/Bun version
   - Docker version (if using)
   - Browser (if frontend issue)
6. **Screenshots/Logs:** Visual evidence or error logs
7. **Additional Context:** Any other relevant information

### Bug Report Template

```markdown
## Description
Brief description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.12.3]
- Bun: [e.g., 1.2.6]
- Docker: [e.g., 24.0.7]

## Screenshots/Logs
[Add screenshots or error logs]

## Additional Context
Any other relevant information
```

---

## Code Review

### Review Checklist

**Functionality:**
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling implemented
- [ ] No security vulnerabilities

**Code Quality:**
- [ ] Follows style guide
- [ ] Well-named variables and functions
- [ ] No code duplication
- [ ] Appropriate comments

**Testing:**
- [ ] Tests included
- [ ] Tests pass
- [ ] Coverage adequate

**Documentation:**
- [ ] Code comments where needed
- [ ] README updated (if applicable)
- [ ] API docs updated (if applicable)

**Performance:**
- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] Caching used where appropriate

### Review Comments

**Be constructive:**
- ✅ "Consider using a dictionary here for O(1) lookup instead of O(n) list iteration"
- ❌ "This is slow"

**Be specific:**
- ✅ "This function could be split into two: one for validation, one for processing"
- ❌ "Refactor this"

**Ask questions:**
- ✅ "What happens if the API returns an empty array here?"
- ❌ "This will break"

---

## Development Tips

### Debugging

**Backend:**
```bash
# Use Django debugger
import pdb; pdb.set_trace()

# Or use IPython
from IPython import embed; embed()
```

**Frontend:**
```typescript
// Use console.log or debugger
console.log('Debug:', data);
debugger;
```

**Celery Tasks:**
```bash
# Run task synchronously for debugging
python manage.py shell
from reversewebsearch.tasks import run_reverse_search_pipeline
result = run_reverse_search_pipeline.apply(args=[...])
print(result.get())
```

### Database Migrations

**Create Migration:**
```bash
cd server
python manage.py makemigrations
```

**Apply Migration:**
```bash
python manage.py migrate
```

**Show Migrations:**
```bash
python manage.py showmigrations
```

### Environment Variables

**Never commit `.env` to git!**

Use `.env.example` as template:
```bash
cp .env.example .env
# Edit .env with your values
```

### Working with External APIs

**Always mock in tests:**
```python
from unittest.mock import patch

@patch('reversewebsearch.utils.requests.get')
def test_api_call(self, mock_get):
    mock_get.return_value.json.return_value = {...}
    # Test code
```

**Handle errors gracefully:**
```python
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    # Handle timeout
    pass
except requests.exceptions.RequestException:
    # Handle other errors
    pass
```

---

## Community

### Getting Help

- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** Questions and community chat
- **Documentation:** Check `_docs/` first

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect differing viewpoints

---

## License

By contributing, you agree that your contributions will be licensed under the project's [LICENSE](LICENSE) file.