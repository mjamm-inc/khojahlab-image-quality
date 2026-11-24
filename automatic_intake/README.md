# Automatic image intake

Automatically check newly saved PNG/JPEG files. This Python tool runs on your computer or the Pi after installation. GitHub Pages does not execute it. It does not operate a camera, move motors, persist browser uploads or execute retake requests.

## Run without a reference

Install Python 3.10+ and run these commands from this folder:

```
python3 -m pip install -r requirements.txt
python3 automatic_intake.py --incoming incoming --output quality_results --watch
```

Put original images into `incoming`. Leave the process running. Once each file is stable for two seconds, it writes a JSON result and updates `quality_results/measurements.csv`. The two-second wait concerns file writes, not camera settling. Press Ctrl+C to stop.

Without a verified reference, illumination failures return RETRY_REQUESTED. Other images return REFERENCE_REQUIRED, not ACCEPT. Invalid files return REVIEW_REQUIRED. These are software decisions only.

For a one-time batch, omit --watch.

## Full reference-based checks

Use a suitable reference from the same target/field, camera, focus plane, magnification, image dimensions and compatible illumination/exposure. Use a separate input folder/process per matching acquisition context. Do not use a bead reference for organoid images or mix unrelated scenes under one reference.

```
python3 automatic_intake.py --incoming incoming --output quality_results --reference /path/to/reference.png --confirm-matched-reference --watch
```

The confirmation flag is an operator assertion, not proof of matching conditions. A mismatched reference can make detail decisions misleading. Acceptance means passing configured engineering checks, not biological suitability.

## Reproducible software demonstration

The included demo images use a real-camera source crop and an intentionally darkened test fixture. They are computational test inputs, not new physical measurements.

```
python3 -m unittest discover -s tests -v
```

Five intake tests cover missing references, detection of new files, restart deduplication, bounded scope without hardware actions, invalid images and output-folder feedback prevention. The existing separate controller suite adds 12 tests, for 17 across the development module.

## DSC connection

DSC can write fresh captures to a mounted intake folder to automate saved-file checks. For physical retakes, connect the existing scanner callback to CapturePolicy/run_capture_cycle and log every attempt. The existing scanner adapter is an undeployed example in the main meeting source package. Verify callbacks, stage ownership, matching references and capture timeouts on the Pi before deployment. Folder intake alone does not perform a bounded live capture cycle.

## Assistance and attribution

Developed with AI implementation and testing assistance based on Mariam's requested design. No human quality labels or physical-retake results were fabricated. Existing lab images and preprocessing retain their attribution. The accompanying meeting package contains the broader assistance and source documentation.
