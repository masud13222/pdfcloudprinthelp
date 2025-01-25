from pyrogram.types import Message
import asyncio
from typing import Dict, List
import os

from .constants import DOWNLOAD_DIR

class PDFMerger:
    def __init__(self):
        self.pdf_files: List[Dict] = []  # Store file info
        self.required_files: int = 0
        self.collecting = False
        self.downloaded_files: List[str] = []  # Track downloaded files
    
    def reset(self):
        """Reset the merger state and clean downloaded files."""
        # Clean downloaded files
        for file_path in self.downloaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            
        self.pdf_files = []
        self.downloaded_files = []
        self.required_files = 0
        self.collecting = False

# Global state
user_states: Dict[int, PDFMerger] = {}
status_messages: Dict[int, Message] = {}
message_locks: Dict[int, asyncio.Lock] = {}
last_progress_update: Dict[int, float] = {} 