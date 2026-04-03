#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2026 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    qt_async_image_loader.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Qt Async Image Loader - Threaded image loading using Qt signals and slots

Provides asynchronous image loading capabilities using Qt's native signals/slots
and QThreadPool for clean, Qt-idiomatic async operations.
"""

#  Python Standard Libraries
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict

#  Third-Party Libraries
import numpy as np
from qtpy.QtCore import QObject, QRunnable, QThreadPool, Signal, QTimer

#  Project Libraries
from pointy.core.image_loader import Image_Loader


class Image_Load_Task(QRunnable):
    """Runnable task for loading images in background threads."""

    def __init__(self, load_id: str, image_path: Path, loader: Image_Loader, async_loader):
        """Initialize image load task.

        Args:
            load_id: Unique identifier for this load
            image_path: Path to image file
            loader: Image loader instance
            async_loader: Reference to async loader for emitting signals
        """
        super().__init__()
        self.load_id = load_id
        self.image_path = image_path
        self.loader = loader
        self.async_loader = async_loader
        self.logger = logging.getLogger(__name__)

        # Auto-delete when done
        self.setAutoDelete(True)

    def run(self):
        """Execute the image loading task."""
        start_time = time.time()

        # Log thread info for debugging
        thread_id = threading.current_thread().ident
        self.logger.debug(f"Starting image load in thread {thread_id}: {self.image_path}")

        try:
            self.logger.debug(f"Loading image: {self.image_path}")
            loaded_image = self.loader.load(self.image_path)

            if loaded_image is None:
                raise ValueError(f"Failed to load image: {self.image_path}")

            load_time = time.time() - start_time
            self.logger.info(f"Image loaded: {self.image_path} ({load_time:.3f}s")

            # Emit completion signal directly from async loader
            self.logger.debug(f"Emitting load_completed signal for {self.load_id}")
            self.async_loader.load_completed.emit(self.load_id, loaded_image.data, load_time)

        except Exception as e:
            error_msg = str(e)
            load_time = time.time() - start_time
            self.logger.error(f"Image load failed: {self.image_path} - {error_msg}")

            # Emit failure signal directly from async loader
            self.logger.debug(f"Emitting load_failed signal for {self.load_id}")
            self.async_loader.load_failed.emit(self.load_id, str(self.image_path), error_msg, load_time)


class Qt_Async_Image_Loader(QObject):
    """Qt-based asynchronous image loader using signals and slots."""

    # Signals
    load_started = Signal(str, str)  # load_id, image_path
    load_progress = Signal(str, int)  # load_id, percentage (0-100)
    load_completed = Signal(str, object, float)  # load_id, image_data, load_time
    load_failed = Signal(str, str, str, float)  # load_id, image_path, error, load_time

    def __init__(self, max_workers: int = 2):
        """Initialize Qt async image loader.

        Args:
            max_workers: Maximum number of concurrent worker threads
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Thread pool for background loading
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max_workers)

        # Image loader instance
        self.image_loader = Image_Loader()

        # Track active loads
        self._active_loads: Dict[str, str] = {}  # load_id -> image_path

        # Statistics
        self._loads_completed = 0
        self._loads_failed = 0
        self._total_load_time = 0.0

    def load_image_async(self, image_path: str | Path) -> str:
        """Load an image asynchronously.

        Args:
            image_path: Path to image file

        Returns:
            Load ID for tracking the operation
        """
        image_path = Path(image_path)
        load_id = str(uuid.uuid4())

        self.logger.info(f"Starting async image load: {image_path} (ID: {load_id})")

        # Track active load
        self._active_loads[load_id] = str(image_path)

        # Emit started signal
        self.load_started.emit(load_id, str(image_path))

        # Create and submit task
        task = Image_Load_Task(load_id, image_path, self.image_loader, self)
        self.thread_pool.start(task)

        return load_id

    def is_load_active(self, load_id: str) -> bool:
        """Check if a load is still active.

        Args:
            load_id: Load ID to check

        Returns:
            True if load is active
        """
        return load_id in self._active_loads

    def get_active_loads(self) -> Dict[str, str]:
        """Get dictionary of active loads (load_id -> image_path)."""
        return self._active_loads.copy()

    def get_active_load_count(self) -> int:
        """Get number of active loads."""
        return len(self._active_loads)

    def cancel_all_loads(self):
        """Cancel all active loads."""
        self.logger.info(f"Cancelling {len(self._active_loads)} active loads")

        # Clear thread pool (this will cancel pending tasks)
        self.thread_pool.clear()

        # Clear active loads tracking
        self._active_loads.clear()

        self.logger.info("All loads cancelled")

    def shutdown(self):
        """Shutdown the async image loader."""
        self.logger.info("Shutting down Qt async image loader")

        # Cancel active loads
        self.cancel_all_loads()

        # Wait for thread pool to finish
        self.thread_pool.waitForDone(5000)  # 5 second timeout

        self.logger.info("Qt async image loader shutdown complete")

    def get_statistics(self) -> Dict[str, any]:
        """Get loader statistics."""
        avg_load_time = (self._total_load_time / self._loads_completed
                        if self._loads_completed > 0 else 0.0)

        return {
            'loads_completed': self._loads_completed,
            'loads_failed': self._loads_failed,
            'active_loads': len(self._active_loads),
            'max_workers': self.thread_pool.maxThreadCount(),
            'avg_load_time': avg_load_time,
            'total_load_time': self._total_load_time
        }

    # Internal slots for handling task completion
    def _on_load_completed(self, load_id: str, image_data: np.ndarray, load_time: float):
        """Handle load completion from task."""
        if load_id in self._active_loads:
            del self._active_loads[load_id]
            self._loads_completed += 1
            self._total_load_time += load_time

    def _on_load_failed(self, load_id: str, image_path: str, error: str, load_time: float):
        """Handle load failure from task."""
        if load_id in self._active_loads:
            del self._active_loads[load_id]
            self._loads_failed += 1


class Loading_Indicator_Widget(QObject):
    """Widget that shows loading indicators for async operations."""

    # Signals
    loading_started = Signal(str, str)  # load_id, image_path
    loading_finished = Signal(str)  # load_id

    def __init__(self, parent=None):
        """Initialize loading indicator widget.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # Track active loads
        self._active_loads: Dict[str, Dict[str, any]] = {}

        # Timer for updating loading animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(100)  # 10 FPS

        # Animation state
        self._animation_frame = 0

    def connect_to_loader(self, loader: Qt_Async_Image_Loader):
        """Connect to async image loader signals.

        Args:
            loader: Async image loader to monitor
        """
        loader.load_started.connect(self.on_load_started)
        loader.load_completed.connect(self.on_load_completed)
        loader.load_failed.connect(self.on_load_failed)

    def on_load_started(self, load_id: str, image_path: str):
        """Handle load started signal."""
        self._active_loads[load_id] = {
            'image_path': image_path,
            'start_time': time.time(),
            'progress': 0
        }

        self.loading_started.emit(load_id, image_path)
        self.logger.debug(f"Loading started: {image_path}")

    def on_load_completed(self, load_id: str, image_data: object, load_time: float):
        """Handle load completed signal."""
        if load_id in self._active_loads:
            del self._active_loads[load_id]
            self.loading_finished.emit(load_id)
            self.logger.debug(f"Loading completed: {load_id}")

    def on_load_failed(self, load_id: str, image_path: str, error: str, load_time: float):
        """Handle load failed signal."""
        if load_id in self._active_loads:
            del self._active_loads[load_id]
            self.loading_finished.emit(load_id)
            self.logger.debug(f"Loading failed: {image_path} - {error}")

    def _update_animation(self):
        """Update loading animation frame."""
        self._animation_frame = (self._animation_frame + 1) % 8
        # Update UI based on current frame and active loads

    def is_loading(self) -> bool:
        """Check if any loads are active."""
        return len(self._active_loads) > 0

    def get_active_loads(self) -> Dict[str, Dict[str, any]]:
        """Get information about active loads."""
        return self._active_loads.copy()

    def get_loading_text(self) -> str:
        """Get text to display during loading."""
        if not self._active_loads:
            return ""

        count = len(self._active_loads)
        if count == 1:
            load_id, info = next(iter(self._active_loads.items()))
            return f"Loading: {Path(info['image_path']).name}"
        else:
            return f"Loading {count} images..."

    def stop_animation(self):
        """Stop the loading animation."""
        self.animation_timer.stop()


# Example usage in a test image panel:
class Test_Image_Panel(QObject):
    """Example test image panel using async loading."""

    def __init__(self):
        super().__init__()

        # Create async loader
        self.async_loader = Qt_Async_Image_Loader(max_workers=2)

        # Create loading indicator
        self.loading_indicator = Loading_Indicator_Widget()
        self.loading_indicator.connect_to_loader(self.async_loader)

        # Connect signals
        self.async_loader.load_completed.connect(self.on_image_loaded)
        self.async_loader.load_failed.connect(self.on_load_failed)
        self.loading_indicator.loading_started.connect(self.show_loading_indicator)
        self.loading_indicator.loading_finished.connect(self.hide_loading_indicator)

    def load_image(self, image_path: str):
        """Load an image asynchronously."""
        load_id = self.async_loader.load_image_async(image_path)
        self.logger.info(f"Started image load: {load_id}")

    def on_image_loaded(self, load_id: str, image_data: object, load_time: float):
        """Handle successful image load."""
        self.display_image(image_data)
        self.logger.info(f"Image displayed: {load_id} ({load_time:.3f}s)")

    def on_load_failed(self, load_id: str, image_path: str, error: str, load_time: float):
        """Handle failed image load."""
        self.show_error_message(f"Failed to load {image_path}: {error}")
        self.logger.error(f"Load failed: {image_path} - {error}")

    def show_loading_indicator(self, load_id: str, image_path: str):
        """Show loading indicator."""
        # Show spinner, progress bar, etc.
        pass

    def hide_loading_indicator(self, load_id: str):
        """Hide loading indicator."""
        # Hide spinner, progress bar, etc.
        pass

    def display_image(self, image_data: object):
        """Display the loaded image."""
        # Update UI with image data
        pass

    def show_error_message(self, message: str):
        """Show error message to user."""
        # Display error dialog or status message
        pass
