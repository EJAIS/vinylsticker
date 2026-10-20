"""
Background worker for lazy tracklist loading.

Fetches tracklists for all 7" releases that don't have one cached yet.
Runs after the collection is loaded into the UI so it doesn't block interaction.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from modules.discogs_cache import DiscogsCache
from modules.discogs_client import DiscogsClient, DiscogsRequestCancelled
from modules.logger import get_logger

logger = get_logger()


class TracklistLoaderThread(QThread):
    """
    Fetches tracklists in the background after the collection is loaded.
    Emits progress and updates the cache incrementally.

    Rate limiting is handled globally by DiscogsClient — no additional sleep
    is added here.  Setting the client's cancel event aborts a pending wait.
    """

    progress        = pyqtSignal(int, int)   # current, total
    tracklist_ready = pyqtSignal(int, list)  # discogs_id, tracks
    loading_done    = pyqtSignal()
    error           = pyqtSignal(str)        # per-item error message (non-fatal)

    def __init__(
        self,
        client: DiscogsClient,
        cache: DiscogsCache,
        pending_ids: list[int],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._client      = client
        self._cache       = cache
        self._pending_ids = pending_ids
        self._cancelled   = False

    def cancel(self) -> None:
        """Request cancellation. The thread will stop after the current fetch."""
        self._cancelled = True

    def run(self) -> None:
        total   = len(self._pending_ids)
        skipped = 0
        logger.info(f"Tracklist lazy loader started: {total} releases pending")

        for i, discogs_id in enumerate(self._pending_ids):
            if self._cancelled:
                logger.info(
                    f"Tracklist loading cancelled by user after {i}/{total} releases"
                )
                break

            rid = int(discogs_id)  # guard against string IDs from API

            # Pre-flight: re-check cache in case another run already stored it
            existing = self._cache.get_release(rid)
            if existing and existing.get("tracklist_fetched"):
                logger.debug(
                    f"Tracklist already cached — skipping API call: "
                    f"discogs_id={rid}"
                )
                skipped += 1
                self.progress.emit(i + 1, total)
                continue

            logger.debug(
                f"Fetching tracklist {i + 1}/{total}: discogs_id={rid}"
            )

            try:
                result = self._client.fetch_tracklist(rid)
                tracks = result["tracks"]
                self._cache.update_tracklist(rid, tracks)
                self.tracklist_ready.emit(rid, tracks)
                logger.debug(
                    f"Tracklist OK: discogs_id={rid} — {len(tracks)} tracks found"
                )
            except DiscogsRequestCancelled:
                self._cancelled = True
                logger.debug(
                    f"Tracklist loader stopped after {i}/{total} releases"
                )
                return
            except Exception as exc:
                logger.warning(
                    f"Tracklist fetch failed — skipping: "
                    f"discogs_id={rid}: {type(exc).__name__}: {exc}"
                )
                self.error.emit(str(exc))

            self.progress.emit(i + 1, total)

        if not self._cancelled:
            logger.info(
                f"Tracklist loading complete: "
                f"{total - skipped} fetched, {skipped} skipped (already cached)"
            )

        self.loading_done.emit()
