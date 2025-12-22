# Scripts

Utility scripts for development and testing.

## create_user.py

CLI tool for creating test users.

### Usage

```bash
# Create a regular user
uv run python scripts/create_user.py user@example.com password123

# Create an admin user
uv run python scripts/create_user.py admin@example.com adminpass --admin
```

### Requirements

- `.env` file must be configured with `JWT_SECRET_KEY`
- Password must be at least 8 characters

### Examples

```bash
# Create a test user for local development
uv run python scripts/create_user.py volunteer@shelter.org testpass123

# Create an admin user for testing admin features
uv run python scripts/create_user.py admin@shelter.org adminpass123 --admin

# Create multiple test users
for i in {1..5}; do
  uv run python scripts/create_user.py "test$i@example.com" "password123"
done
```

### Error Handling

- Validates password length (minimum 8 characters)
- Prevents duplicate email addresses
- Checks for required environment variables
- Provides clear error messages
