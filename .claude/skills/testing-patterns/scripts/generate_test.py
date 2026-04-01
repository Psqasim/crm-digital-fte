#!/usr/bin/env python3
"""
Test Template Generator - Creates test files from templates

Usage:
    generate_test.py <module_name> --path <output_path>
    generate_test.py TaskManager --path tests/unit/test_task_manager.py
    generate_test.py StorageAgent --path tests/unit/test_storage.py --async

Examples:
    python scripts/generate_test.py TaskManager --path tests/unit/
    python scripts/generate_test.py ApiClient --path tests/integration/ --async
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime


SYNC_TEST_TEMPLATE = '''"""
Tests for {class_name}

Generated on {date}
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class Test{class_name}:
    """Test suite for {class_name}."""

    @pytest.fixture
    def {fixture_name}(self):
        """Create {class_name} instance for testing."""
        # TODO: Initialize with proper dependencies
        return {class_name}()

    # ==================== Happy Path Tests ====================

    def test_{method_name}_success(self, {fixture_name}):
        """Test successful {method_name} operation."""
        # Arrange
        # TODO: Set up test data

        # Act
        # TODO: Call the method
        result = {fixture_name}.{method_name}()

        # Assert
        # TODO: Verify the result
        assert result is not None

    def test_{method_name}_with_valid_input(self, {fixture_name}):
        """Test {method_name} with valid input data."""
        # Arrange
        input_data = {{}}  # TODO: Add valid test data

        # Act
        result = {fixture_name}.{method_name}(input_data)

        # Assert
        assert result is not None

    # ==================== Edge Case Tests ====================

    def test_{method_name}_empty_input(self, {fixture_name}):
        """Test {method_name} handles empty input."""
        # Arrange
        input_data = {{}}

        # Act & Assert
        # TODO: Decide expected behavior for empty input
        result = {fixture_name}.{method_name}(input_data)
        assert result is not None

    def test_{method_name}_none_input(self, {fixture_name}):
        """Test {method_name} handles None input."""
        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            {fixture_name}.{method_name}(None)

    # ==================== Error Handling Tests ====================

    def test_{method_name}_raises_on_invalid_input(self, {fixture_name}):
        """Test {method_name} raises appropriate error for invalid input."""
        # Arrange
        invalid_input = "invalid"

        # Act & Assert
        with pytest.raises(ValueError, match=".*"):
            {fixture_name}.{method_name}(invalid_input)

    def test_{method_name}_handles_dependency_failure(self, {fixture_name}):
        """Test {method_name} handles dependency failures gracefully."""
        # Arrange
        with patch.object({fixture_name}, "_dependency", side_effect=Exception("Dependency failed")):
            # Act & Assert
            with pytest.raises(Exception):
                {fixture_name}.{method_name}()

    # ==================== Integration Points ====================

    def test_{method_name}_calls_dependency(self, {fixture_name}):
        """Test {method_name} correctly calls external dependencies."""
        # Arrange
        mock_dependency = Mock()
        {fixture_name}._dependency = mock_dependency

        # Act
        {fixture_name}.{method_name}()

        # Assert
        mock_dependency.assert_called_once()
'''


ASYNC_TEST_TEMPLATE = '''"""
Async Tests for {class_name}

Generated on {date}
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.asyncio
class Test{class_name}:
    """Async test suite for {class_name}."""

    @pytest.fixture
    def {fixture_name}(self):
        """Create {class_name} instance for testing."""
        # TODO: Initialize with proper dependencies
        return {class_name}()

    # ==================== Happy Path Tests ====================

    async def test_{method_name}_success(self, {fixture_name}):
        """Test successful async {method_name} operation."""
        # Arrange
        # TODO: Set up test data

        # Act
        result = await {fixture_name}.{method_name}()

        # Assert
        assert result is not None

    async def test_{method_name}_with_valid_input(self, {fixture_name}):
        """Test async {method_name} with valid input data."""
        # Arrange
        input_data = {{}}  # TODO: Add valid test data

        # Act
        result = await {fixture_name}.{method_name}(input_data)

        # Assert
        assert result is not None

    # ==================== Concurrent Operation Tests ====================

    async def test_{method_name}_concurrent_calls(self, {fixture_name}):
        """Test multiple concurrent {method_name} calls."""
        import asyncio

        # Arrange
        tasks = [
            {fixture_name}.{method_name}()
            for _ in range(10)
        ]

        # Act
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert
        for result in results:
            assert not isinstance(result, Exception)

    # ==================== Error Handling Tests ====================

    async def test_{method_name}_raises_on_invalid_input(self, {fixture_name}):
        """Test async {method_name} raises appropriate error."""
        # Arrange
        invalid_input = None

        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            await {fixture_name}.{method_name}(invalid_input)

    async def test_{method_name}_handles_async_dependency_failure(self, {fixture_name}):
        """Test {method_name} handles async dependency failures."""
        # Arrange
        mock_dependency = AsyncMock(side_effect=Exception("Async failure"))
        {fixture_name}._dependency = mock_dependency

        # Act & Assert
        with pytest.raises(Exception, match="Async failure"):
            await {fixture_name}.{method_name}()

    # ==================== Timeout Tests ====================

    async def test_{method_name}_respects_timeout(self, {fixture_name}):
        """Test {method_name} completes within timeout."""
        import asyncio

        # Act & Assert
        try:
            result = await asyncio.wait_for(
                {fixture_name}.{method_name}(),
                timeout=5.0
            )
            assert result is not None
        except asyncio.TimeoutError:
            pytest.fail("{method_name} timed out")
'''


def to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def generate_test_file(class_name: str, output_path: Path, is_async: bool) -> Path:
    """Generate a test file from template."""
    fixture_name = to_snake_case(class_name)
    method_name = "process"  # Default method name

    template = ASYNC_TEST_TEMPLATE if is_async else SYNC_TEST_TEMPLATE

    content = template.format(
        class_name=class_name,
        fixture_name=fixture_name,
        method_name=method_name,
        date=datetime.now().strftime("%Y-%m-%d")
    )

    # Determine output file path
    if output_path.is_dir():
        output_file = output_path / f"test_{to_snake_case(class_name)}.py"
    else:
        output_file = output_path

    # Create parent directories if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    output_file.write_text(content)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate test file templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("class_name",
                        help="Name of the class to test (e.g., TaskManager)")
    parser.add_argument("--path", "-p", type=str, required=True,
                        help="Output path for the test file")
    parser.add_argument("--async", "-a", dest="is_async", action="store_true",
                        help="Generate async test template")

    args = parser.parse_args()

    output_path = Path(args.path)

    # Generate the test file
    generated_file = generate_test_file(
        args.class_name,
        output_path,
        args.is_async
    )

    print(f"Generated test file: {generated_file}")
    print("\nNext steps:")
    print(f"1. Add import for {args.class_name} from your source module")
    print("2. Update fixture to properly initialize the class")
    print("3. Replace TODO comments with actual test logic")
    print("4. Run: pytest", generated_file)


if __name__ == "__main__":
    main()
