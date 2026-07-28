# Plugin Development

hw2c supports a plugin architecture for extending code generation with custom logic.

## Plugin Types

### 1. Builder Plugins

Builders generate code for specific hardware categories. Implement `generator/builders/base.py`:

```python
from generator.builders.base import BaseBuilder

class MyCustomBuilder(BaseBuilder):
    """Generate initialization code for a custom peripheral."""

    def build(self, context: dict) -> str:
        """Return generated C code string."""
        return self.render_template("my_custom.c.j2", context)
```

Register in `generator/builders/registry.py`:

```python
BUILDER_REGISTRY = {
    "gpio": GPIOBuilder,
    "i2c": I2CBuilder,
    "my_custom": MyCustomBuilder,
}
```

### 2. Validator Plugins

Add custom validation rules in `generator/validators/`:

```python
from generator.validators.base import BaseValidator

class PinConflictValidator(BaseValidator):
    """Check for pin function conflicts."""

    def validate(self, model: dict) -> list[str]:
        errors = []
        # Check each pin against pin database
        return errors
```

### 3. Context Plugins

Add custom context data to templates via `generator/context/`:

```python
from generator.context.base import BaseContext

class MyContext(BaseContext):
    def build(self, model: dict) -> dict:
        return {
            "my_var": self.extract_my_data(model),
        }
```

## Template Conventions

When creating templates for plugins, follow these conventions:

1. **Naming**: Use `drv_<name>.c.j2` for drivers, `test_<name>.c.j2` for tests
2. **Mock support**: Add `#ifdef TEST` guards for all HAL calls
3. **Header guards**: Use `__DRV_<NAME>_H` pattern
4. **Logging**: Use `log_debug()` / `log_error()` for diagnostics
5. **Error handling**: Return error codes, don't call `assert()` in production code

## Best Practices

- Keep plugins self-contained in their own subdirectory
- Add unit tests for plugin logic in `generator/tests/`
- Document plugin interface with type hints
- Use `generator.models.py` for shared Pydantic models
- Follow existing patterns in `generator/builders/` for consistency
