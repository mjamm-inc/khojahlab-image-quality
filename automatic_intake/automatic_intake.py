"""Automatically evaluate new saved PNG/JPEG files. Does not operate hardware."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import time

from capture_quality import QualityConfig, assess, load_rgb, metrics, reference_metrics

EXTENSIONS = {'.png', '.jpg', '.jpeg'}

class ImageIntake:
    def __init__(self, incoming, output, reference=None, matched=False, settle_s=2.0):
        self.incoming, self.output = Path(incoming).resolve(), Path(output).resolve()
        if self.incoming == self.output or self.incoming in self.output.parents:
            raise ValueError('Output must be outside the incoming folder')
        self.incoming.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)
        if reference is not None and not matched:
            raise ValueError('Confirm matching reference conditions before full checks')
        self.config = QualityConfig()
        self.reference = load_rgb(reference) if reference else None
        self.reference_scores = reference_metrics(self.reference) if reference else None
        self.reference_path = Path(reference).resolve() if reference else None
        self.reference_hash = hashlib.sha256(Path(reference).read_bytes()).hexdigest() if reference else ''
        self.settle_s = float(settle_s)
        if self.settle_s < 0: raise ValueError('File stability wait must be nonnegative')
        self.seen = {}

    def scan_once(self):
        results = []
        for path in sorted(self.incoming.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS or path.resolve() == self.reference_path:
                continue
            try:
                stat = path.stat()
                signature = (stat.st_size, stat.st_mtime_ns)
                previous = self.seen.get(str(path))
                if not previous or previous[0] != signature:
                    self.seen[str(path)] = (signature, time.monotonic())
                    if self.settle_s: continue
                elif time.monotonic() - previous[1] < self.settle_s:
                    continue
                raw = path.read_bytes()
                if (path.stat().st_size, path.stat().st_mtime_ns) != signature: continue
                digest = hashlib.sha256(raw).hexdigest()
                identity = json.dumps([str(path), digest, self.reference_hash, self.config.__dict__], sort_keys=True)
                key = hashlib.sha256(identity.encode()).hexdigest()
                result_path = self.output / (key + '.json')
                if result_path.exists(): continue
                row = dict(source=str(path.relative_to(self.incoming)), sha256=digest,
                           reference_sha256=self.reference_hash or None,
                           scope='saved-image intake', hardware_action_performed=False)
                try:
                    rgb = load_rgb(path)
                    m = metrics(rgb)
                    if self.reference is None:
                        reasons = []
                        if m['mean_gray'] < self.config.min_mean: reasons.append('LOW_LIGHT')
                        if m['mean_gray'] > self.config.max_mean or m['white_fraction'] > self.config.max_white_fraction: reasons.append('OVEREXPOSED')
                        row.update(metrics=m, decision='RETRY_REQUESTED' if reasons else 'REFERENCE_REQUIRED', reasons=reasons or ['MATCHED_REFERENCE_REQUIRED'])
                    elif rgb.shape != self.reference.shape:
                        row.update(metrics=m, decision='REFERENCE_REQUIRED', reasons=['REFERENCE_SHAPE_MISMATCH'])
                    else:
                        assessment = assess(rgb, self.reference_scores)
                        row.update(metrics=assessment['metrics'], decision='ACCEPT' if assessment['passed'] else 'RETRY_REQUESTED', reasons=assessment['reasons'])
                except (OSError, ValueError, TypeError) as exc:
                    row.update(metrics={}, decision='REVIEW_REQUIRED', reasons=['IMAGE_READ_OR_FORMAT_ERROR'], error_type=type(exc).__name__)
                temporary = result_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(row, indent=2))
                os.replace(temporary, result_path)
                results.append(row)
            except OSError:
                continue  # Retry files still being written on the next scan.
        self.write_summary()
        return results

    def write_summary(self):
        rows = [json.loads(p.read_text()) for p in sorted(self.output.glob('*.json'))]
        tmp = self.output / 'measurements.csv.tmp'
        with tmp.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['source','sha256','decision','reasons','mean_gray','white_fraction','relative_edge','hardware_action_performed'])
            writer.writeheader()
            for r in rows:
                m = r['metrics']
                writer.writerow(dict(source=r['source'], sha256=r['sha256'], decision=r['decision'], reasons=';'.join(r['reasons']), mean_gray=m.get('mean_gray',''), white_fraction=m.get('white_fraction',''), relative_edge=m.get('relative_edge',''), hardware_action_performed=False))
        os.replace(tmp, self.output / 'measurements.csv')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--incoming', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--reference')
    parser.add_argument('--confirm-matched-reference', action='store_true')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--poll-seconds', type=float, default=2)
    parser.add_argument('--file-stability-seconds', type=float, default=2)
    args = parser.parse_args()
    if args.poll_seconds <= 0: parser.error('poll-seconds must be positive')
    worker = ImageIntake(args.incoming, args.output, args.reference, args.confirm_matched_reference, args.file_stability_seconds)
    try:
        while True:
            for row in worker.scan_once(): print(json.dumps(row), flush=True)
            if not args.watch:
                # Observe stable files once more rather than silently skipping a new batch.
                time.sleep(args.file_stability_seconds)
                for row in worker.scan_once(): print(json.dumps(row), flush=True)
                break
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        print('Image intake stopped. Results remain in the output folder.')

if __name__ == '__main__': main()
