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
#    File:    histogram_manager.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Histogram Manager - Centralized histogram computation and caching

Provides efficient histogram computation with caching and performance optimization
for image data analysis in the Pointy-McPointface application.
"""

#  Python Standard Libraries
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from hashlib import md5

#  Third-Party Libraries
import numpy as np


@dataclass
class Histogram_Cache_Entry:
    """Cache entry for computed histograms."""
    histogram: np.ndarray
    bins: int
    data_hash: str
    computation_time: float
    timestamp: float


class Histogram_Manager:
    """Manages histogram computation with caching and performance optimization."""

    def __init__(self, cache_size: int = 50, cache_ttl: float = 300.0):
        """Initialize histogram manager.

        Args:
            cache_size: Maximum number of histograms to cache
            cache_ttl: Time-to-live for cache entries in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl

        # Cache storage
        self._cache: Dict[str, Histogram_Cache_Entry] = {}
        self._cache_access_order: list[str] = []

        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_computations = 0

    def compute_histogram(self, image_data: np.ndarray,
                          bit_depth: int | None = None,
                          force_recompute: bool = False) -> Tuple[np.ndarray, int]:
        """Compute histogram for image data with caching.

        Args:
            image_data: Image data as numpy array
            bit_depth: Image bit depth for optimal bin calculation
            force_recompute: Force recomputation even if cached

        Returns:
            Tuple of (histogram, num_bins)
        """
        start_time = time.time()

        # Generate cache key
        data_hash = self._compute_data_hash(image_data)
        bins = self._calculate_optimal_bins(image_data, bit_depth)
        cache_key = f"{data_hash}_{bins}"

        # Check cache
        if not force_recompute and cache_key in self._cache:
            cache_entry = self._cache[cache_key]

            # Check if cache entry is still valid
            if time.time() - cache_entry.timestamp < self.cache_ttl:
                self._cache_hits += 1
                self._update_cache_order(cache_key)
                self.logger.debug(f"Histogram cache hit: {time.time() - start_time:.3f}s")
                return cache_entry.histogram, bins

        # Compute histogram
        self._cache_misses += 1
        self._total_computations += 1

        histogram = self._compute_histogram_internal(image_data, bins)

        # Cache result
        cache_entry = Histogram_Cache_Entry(
            histogram=histogram,
            bins=bins,
            data_hash=data_hash,
            computation_time=time.time() - start_time,
            timestamp=time.time()
        )

        self._add_to_cache(cache_key, cache_entry)

        computation_time = time.time() - start_time
        self.logger.info(f"Histogram computed: {computation_time:.3f}s, bins: {bins}")

        return histogram, bins

    def _compute_histogram_internal(self, image_data: np.ndarray, bins: int) -> np.ndarray:
        """Internal histogram computation."""
        # Handle different image formats
        if len(image_data.shape) == 2:
            # Grayscale image
            histogram, _ = np.histogram(image_data.flatten(), bins=bins, range=(0, bins))
        elif len(image_data.shape) == 3:
            # RGB image - compute luminance histogram
            # Convert to grayscale using standard weights
            if image_data.shape[2] >= 3:
                # Use first 3 channels (typically RGB)
                rgb_data = image_data[:, :, :3]
                # Standard RGB to grayscale conversion
                grayscale = np.dot(rgb_data[..., :3], [0.299, 0.587, 0.114])
                histogram, _ = np.histogram(grayscale.flatten(), bins=bins, range=(0, bins))
            else:
                # Fallback to first channel
                histogram, _ = np.histogram(image_data[:, :, 0].flatten(), bins=bins, range=(0, bins))
        else:
            raise ValueError(f"Unsupported image shape: {image_data.shape}")

        return histogram.astype(np.int64)

    def _calculate_optimal_bins(self, image_data: np.ndarray, bit_depth: int | None) -> int:
        """Calculate optimal number of histogram bins."""
        if bit_depth is not None:
            max_pixel = (2 ** bit_depth) - 1
            return min(256, max_pixel + 1)

        # Auto-determine from data
        data_min = int(np.min(image_data))
        data_max = int(np.max(image_data))
        data_range = data_max - data_min

        # Use reasonable defaults
        if data_range <= 255:
            return 256
        elif data_range <= 65535:
            return 256
        else:
            return 256

    def _compute_data_hash(self, image_data: np.ndarray) -> str:
        """Compute hash of image data for cache key."""
        # Sample data for hashing (avoid hashing entire large arrays)
        sample_size = min(1000, image_data.size)
        sample_indices = np.random.choice(image_data.size, sample_size, replace=False)
        sample_data = image_data.flatten()[sample_indices]

        # Create hash
        hash_input = f"{image_data.shape}_{sample_data.tobytes()}"
        return md5(hash_input.encode()).hexdigest()[:16]

    def _add_to_cache(self, cache_key: str, entry: Histogram_Cache_Entry):
        """Add entry to cache with LRU eviction."""
        # Remove oldest if cache is full
        if len(self._cache) >= self.cache_size:
            oldest_key = self._cache_access_order.pop(0)
            del self._cache[oldest_key]

        self._cache[cache_key] = entry
        self._cache_access_order.append(cache_key)

    def _update_cache_order(self, cache_key: str):
        """Update cache access order for LRU."""
        if cache_key in self._cache_access_order:
            self._cache_access_order.remove(cache_key)
        self._cache_access_order.append(cache_key)

    def clear_cache(self):
        """Clear all cached histograms."""
        self._cache.clear()
        self._cache_access_order.clear()
        self.logger.info("Histogram cache cleared")

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'cache_size': len(self._cache),
            'max_cache_size': self.cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': hit_rate,
            'total_computations': self._total_computations
        }

    def invalidate_cache_for_data(self, image_data: np.ndarray):
        """Invalidate cache entries for specific image data."""
        data_hash = self._compute_data_hash(image_data)
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(data_hash)]

        for key in keys_to_remove:
            del self._cache[key]
            self._cache_access_order.remove(key)

        if keys_to_remove:
            self.logger.debug(f"Invalidated {len(keys_to_remove)} cache entries")


class Histogram_Manager_Factory:
    """Factory for creating histogram manager instances."""

    @staticmethod
    def create_manager(cache_size: int = 50, cache_ttl: float = 300.0) -> Histogram_Manager:
        """Create a new histogram manager with specified configuration.

        Args:
            cache_size: Maximum number of histograms to cache
            cache_ttl: Time-to-live for cache entries in seconds

        Returns:
            Configured Histogram_Manager instance
        """
        return Histogram_Manager(cache_size, cache_ttl)
