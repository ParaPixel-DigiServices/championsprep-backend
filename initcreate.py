"""
Create all necessary __init__.py files for the project.
Run this script from the project root directory.
"""

import os
from pathlib import Path

# Directories that need __init__.py files
directories = [
    "app",
    "app/api",
    "app/api/v1",
    "app/api/v1/endpoints",
    "app/core",
    "app/db",
    "app/models",
    "app/services",
]

def create_init_files():
    """Create __init__.py files in all necessary directories."""
    project_root = Path(__file__).parent
    
    created = []
    already_exists = []
    
    for directory in directories:
        dir_path = project_root / directory
        init_file = dir_path / "__init__.py"
        
        # Create directory if it doesn't exist
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py if it doesn't exist
        if not init_file.exists():
            init_file.write_text('"""Package initialization."""\n')
            created.append(str(init_file.relative_to(project_root)))
        else:
            already_exists.append(str(init_file.relative_to(project_root)))
    
    print("=" * 70)
    print("__init__.py File Creation Summary")
    print("=" * 70)
    
    if created:
        print(f"\n✅ Created {len(created)} files:")
        for file in created:
            print(f"   - {file}")
    
    if already_exists:
        print(f"\n📝 Already existed ({len(already_exists)} files):")
        for file in already_exists:
            print(f"   - {file}")
    
    print("\n" + "=" * 70)
    print("✨ All __init__.py files are in place!")
    print("=" * 70)

if __name__ == "__main__":
    create_init_files()