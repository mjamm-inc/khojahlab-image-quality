# Connection to the existing scan workflow

Reviewed source, read-only: https://github.com/khojah-lab/realtime-organoid-XYZ/tree/607a15c6c8a414e3ef3de94876b8458e8dea6b38

`services/scanner.py` currently calls `capture_fresh_bgr_frame()` in `take_scan_photo`,
encodes a JPEG and passes it to `storage_manager.capture`. Six-well navigation waits
1 second after movement; the circular scan uses its configured settling delay.
`hardware/camera.py` already bounds frame requests and recovers its pipeline.
The new policy adds content checks after a fresh frame arrives. Do not claim the
existing timeout/recovery implementation as Mariam's new contribution.

## Proposed insertion

1. Keep the current scan lock, target position, LED behavior and movement waits.
2. Resolve a verified reference and ROI keyed to well/tile, optics, image dimensions,
   exposure and white balance. If unavailable, log REVIEW_REQUIRED. Do not silently
   treat the first incoming image as a valid focus reference.
3. Call `capture_checked_bgr` from `integration/scanner_adapter.py` after the move.
4. Persist the complete quality log regardless of ACCEPT/ESCALATE/CANCELLED.
5. Encode and save the accepted image through the existing storage manager.
   Keep failed raw frames, if retained, in a separately identified diagnostic store.
6. If no image is accepted, record an unresolved quality failure for that target.
   Do not increment a successful accepted-capture count. Do not move to another target
   during a retry cycle. Preserve scan cancellation and the existing LED cleanup.

The adapter uses max_age_sec=0 to request a new stream sequence, rather than reusing
a recently buffered frame on an immediate retry. It converts BGR to RGB for assessment
and returns BGR for the existing JPEG encoder. The import is deferred to avoid
initializing hardware when inspecting or testing the independent module.

## Deployment validation required

The adapter is supplied as an example, not an applied patch. The scanner does not
currently provide the verified reference registry, quality-log storage and acceptance
status UI described above. Integration must implement and test those dependencies.
No live hardware imports were executed in this build.

On the actual Pi, verify cancellation, fresh frames on each attempt, error handling,
failure log persistence, image/metadata correspondence and no concurrent stage motion.
Measure end-to-end added time there. The recorded processing time is from the build
computer, not the Pi. Keep initial motion waits unchanged until controlled settling
experiments support a different value.

For physical validation, compare accepted/flagged frames against blinded technical
review for fixed bead targets over repeated real stage moves. Report false accepts,
unnecessary retries, unresolved targets, time per well and repeated-run variability.
Reserve independent physical runs for validation after selecting settings. Organoid
image usability and health interpretation require additional validation next quarter.
