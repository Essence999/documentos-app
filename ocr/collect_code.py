import logging
from pathlib import Path


def collect_app_code(directories: list[str] | None = None) -> dict[str, str]:
    """
    Collect Python code from specified directories.

    Args:
        directories: Optional list of directories to scan. If None, scans 'app' directory.

    Returns:
        Dictionary mapping file paths to their contents.
    """
    # Use default if no directories specified
    if directories is None:
        directories = ['app']

    code_dictionary: dict[str, str] = {}

    # Process each directory
    for base_dir in directories:
        dir_path = Path(base_dir)

        # Check if directory exists
        if not dir_path.exists():
            logging.info(f"Directory '{base_dir}' not found.")
            continue

        # Use rglob to recursively find all .py files without nested loops
        for file_path in dir_path.rglob('*.py'):
            # Filter out __init__.py
            if file_path.name == '__init__.py':
                continue

            # Create the key using as_posix() to ensure forward slashes
            relative_path = file_path.as_posix()

            try:
                # read_text() avoids the need for a 'with open()' block
                code_dictionary[relative_path] = file_path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError) as e:
                logging.info(f'Error reading {file_path}: {e}')

    return code_dictionary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    result = collect_app_code(['app'])
    logging.info(f'Found {len(result)} files:')
    for path in result:
        logging.info(f' - {path}')

    with Path('collected_code.txt').open('w', encoding='utf-8') as out_file:
        for path, code in result.items():
            out_file.write(f'# File: {path}\n')
            out_file.write(code)
            out_file.write('\n\n')
