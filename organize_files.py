import os
import shutil

# Define the target directory structure
directory_structure = {
    "static": {
        "css": [],
        "js": []
    },
    "templates": ["base.html", "clients.html"],
    "api": ["endpoints.py"],
    "": ["app.py", "db.py", "scheduler.py"],
    "venv": [],  # Assume virtual environment already exists
}

# Source directory where all files are currently located
source_dir = "/home/brett/server-management"
# Destination directory (can be the same as source or a new one)
destination_dir = "/home/brett/server-management"

# Create the destination directory structure
def create_structure():
    print("Creating directory structure...")
    for folder, files in directory_structure.items():
        dir_path = os.path.join(destination_dir, folder)
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")

# Move files to the correct locations
def move_files():
    print("Organizing files...")
    for folder, files in directory_structure.items():
        target_folder = os.path.join(destination_dir, folder)
        for file_name in files:
            source_file = os.path.join(source_dir, file_name)
            target_file = os.path.join(target_folder, file_name)
            if os.path.exists(source_file):
                if os.path.exists(target_file):
                    print(f"Skipping {file_name}: Already exists in {target_folder}")
                else:
                    shutil.move(source_file, target_file)
                    print(f"Moved {file_name} to {target_folder}")
            else:
                print(f"Warning: {file_name} not found in {source_dir}")

# Copy venv if exists
def copy_venv():
    source_venv = os.path.join(source_dir, "venv")
    target_venv = os.path.join(destination_dir, "venv")
    if os.path.exists(source_venv):
        if os.path.exists(target_venv):
            print("Skipping virtual environment: Already exists.")
        else:
            print("Copying virtual environment...")
            shutil.copytree(source_venv, target_venv, dirs_exist_ok=True)
            print("Virtual environment copied.")
    else:
        print("Warning: venv not found in source directory.")

if __name__ == "__main__":
    # Confirm with the user
    print(f"Source directory: {source_dir}")
    print(f"Destination directory: {destination_dir}")
    confirm = input("Proceed with organizing files? (yes/no): ").strip().lower()
    if confirm == "yes":
        # Ensure destination directory exists
        os.makedirs(destination_dir, exist_ok=True)
        
        # Execute organization
        create_structure()
        move_files()
        copy_venv()
        print("File organization complete!")
    else:
        print("Operation canceled.")
