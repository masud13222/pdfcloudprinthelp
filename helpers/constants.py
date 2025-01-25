import os

# Constants for file operations
DOWNLOAD_DIR = "downloads"  # Directory to store downloads

# Create downloads directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR) 