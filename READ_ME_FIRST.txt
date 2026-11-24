MARIAM — MEETING PACKAGE

1. Open START_HERE.html in Chrome after unzipping this folder.
   The redesigned Capture Studio includes bead and organoid galleries, year/date
   filters, search, brightness sorting and image inspection. Use the collection
   tabs to switch between current-system evidence and archival applicability.
2. Demonstrate the controller replay (saved-image simulation, not a live retake).
3. Open REVIEW_REAL_IMAGES.html, complete the 48-image review, and export the JSON.
   This is the compact review. The full archive package includes all 606 previews.
4. Keep the exported JSON; the static PDF will not update automatically.

WHAT IS HERE
Working offline interfaces and image previews: top-level HTML files.
Report: Mariam_Acquisition_Deliverable.pdf.
Actual numerical measurements, source inventories and computational results:
measurements_and_results/.
Python implementation, tests, evaluation scripts and integration example:
source_code/.
Run the tests from source_code: python3 -m unittest discover -s tests -v
Core dependencies: python3 -m pip install -r requirements.txt

WHAT IS COMPLETE
- Offline image-quality acceptance and bounded retry/escalation logic.
- Numerical measurements for 606 prototype JPEG files.
- 448/606 (73.9%) fall below the provisional brightness threshold of 20/255.
  This is a screen result, NOT validated accuracy or proof all 448 are unusable.
- 20 original/corrected archival organoid pairs; median paired brightness change
  +57.6/255. The preprocessing belongs to the team, not this module.
- Software behavioral testing and computational replay.

WHAT IS STILL PENDING
- Your Good/Bad/Unsure review and reference verification, then agreement analysis.
- Team source review and live camera integration; no physical retake verified.
- A controlled move-and-stop experiment before claiming an optimal settling delay.
- Prospective validation on next-quarter organoid captures.

WHAT TO SAY
My earlier bead experiments exposed acquisition-quality problems. Building on the
quality checks in my proposal, I developed an offline module that checks a capture,
accepts it or requests another attempt, and flags repeated failures. I measured
its screening outputs on our prototype images and am completing the manual-review
comparison. Archival organoid images provide a separate applicability demonstration.
The live camera connection remains the next integration step.

GITHUB, IN PLAIN LANGUAGE
A branch is a separate version of the shared project for developing your changes.
Push means uploading saved code changes to GitHub. Merge means combining reviewed
changes into the shared main version. A branch alone does not connect this module
to the camera. Deployment and hardware integration are separate steps.

RECOMMENDED HANDOFF
Keep this standalone demo for the meeting. Put source_code in a clearly named module
folder on your own feature branch, such as mariam/capture-acceptance. Ask the team to
review the integration adapter and tests before merging. Do not overwrite main or
claim deployment. No push or deployment has been performed by this package.

Ricki's message supports the individual-branch workflow; it does not explicitly
certify zero overlap. His processed-image source is on Data_Preprocessing_clean,
High_quality_image_23&24, separate from the earlier main-branch code inspection.

Raw source ZIPs are not duplicated in this compact package. Retain the original
uploads. Source inventories document the measured files. All AI assistance is
described in source_code/AI_USE.md.
