"""Image acceptance policy for saved RGB camera frames.

No camera, motor, network or server imports. ACCEPT means passes these engineering
checks, not biological usability. A reference must be chosen at matching ROI/scale.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import json
import time

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, laplace


@dataclass(frozen=True)
class QualityConfig:
    min_mean: float = 20.0
    max_mean: float = 235.0
    max_white_fraction: float = 0.20
    min_relative_edge: float = 0.55
    smoothing_sigma: float = 0.8
    max_residual_floor: float = 3.0
    max_residual_reference_factor: float = 2.5
    max_attempts: int = 3  # includes first capture
    max_elapsed_s: float = 10.0
    analysis_size: int = 256
    preserve_aspect: bool = True

    def __post_init__(self):
        values = [self.min_mean, self.max_mean, self.max_white_fraction,
                  self.min_relative_edge, self.smoothing_sigma, self.max_elapsed_s,
                  self.max_residual_floor,self.max_residual_reference_factor]
        if not all(np.isfinite(x) for x in values):
            raise ValueError('Configuration values must be finite')
        if not 0 <= self.min_mean < self.max_mean <= 255:
            raise ValueError('Invalid brightness range')
        if not 0 <= self.max_white_fraction <= 1 or not 0 < self.min_relative_edge <= 1:
            raise ValueError('Invalid quality fraction')
        if self.smoothing_sigma < 0 or self.max_elapsed_s <= 0:
            raise ValueError('Invalid smoothing or time budget')
        if self.max_residual_floor <= 0 or self.max_residual_reference_factor < 1:
            raise ValueError('Invalid high-frequency residual limits')
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ValueError('max_attempts must be a positive integer')
        if type(self.analysis_size) is not int or self.analysis_size < 16:
            raise ValueError('analysis_size must be an integer >=16')
        if type(self.preserve_aspect) is not bool:
            raise ValueError('preserve_aspect must be boolean')


def load_rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB')).copy()


def metrics(rgb, config=QualityConfig(), roi=None):
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[2] != 3 or a.dtype != np.uint8 or min(a.shape[:2]) < 16:
        raise ValueError('Expected uint8 RGB image, height and width >=16')
    if roi is not None:
        if len(roi) != 4 or any(type(v) is not int for v in roi):
            raise ValueError('ROI must have four integer values')
        x, y, w, h = roi
        if min(x,y) < 0 or min(w,h) < 16 or x+w > a.shape[1] or y+h > a.shape[0]:
            raise ValueError('ROI outside image bounds or smaller than 16 pixels')
        a = a[y:y+h, x:x+w]
    size=(config.analysis_size,config.analysis_size)
    if config.preserve_aspect:
        scale=config.analysis_size/max(a.shape[:2])
        size=(max(1,round(a.shape[1]*scale)),max(1,round(a.shape[0]*scale)))
    a = np.asarray(Image.fromarray(a).resize(size, Image.Resampling.LANCZOS), dtype=float)
    g = a @ np.array([.299,.587,.114])
    mean = float(g.mean())
    smoothed = gaussian_filter(g, config.smoothing_sigma, mode='reflect')
    edge = float(np.var(laplace(smoothed, mode='reflect')) / max(mean*mean, 1.0))
    return dict(mean_gray=mean, white_fraction=float((g >= 250).mean()),
                normalized_edge=edge, fine_residual=float(np.median(np.abs(g-smoothed))/.67449),
                analysis_size=config.analysis_size,analysis_width=size[0],analysis_height=size[1])


def reference_metrics(reference, config=QualityConfig(), roi=None):
    m = metrics(reference, config, roi)
    if m['mean_gray'] < config.min_mean or m['mean_gray'] > config.max_mean or m['white_fraction'] > config.max_white_fraction:
        raise ValueError('Reference fails illumination checks')
    if m['normalized_edge'] < 1e-9:
        raise ValueError('Reference has insufficient edge content')
    return m


def assess(rgb, reference, config=QualityConfig(), roi=None):
    """Reference is a metrics dict already validated by reference_metrics."""
    if rgb is None:
        return dict(passed=False,reasons=['FRAME_UNAVAILABLE'],metrics={})
    try:
        m = metrics(rgb, config, roi)
    except (ValueError, TypeError, OSError) as exc:
        return dict(passed=False,reasons=['INVALID_IMAGE'],metrics={},detail=str(exc))
    reasons = []
    if m['mean_gray'] < config.min_mean:
        reasons.append('LOW_LIGHT')
    if m['mean_gray'] > config.max_mean or m['white_fraction'] > config.max_white_fraction:
        reasons.append('OVEREXPOSED')
    denominator = reference.get('normalized_edge',0)
    if not np.isfinite(denominator) or denominator < 1e-9:
        raise ValueError('Invalid reference edge score')
    m['relative_edge'] = m['normalized_edge']/denominator
    if m['relative_edge'] < config.min_relative_edge:
        reasons.append('LOW_RELATIVE_EDGE')
    # This flags unusually large fine residuals, which may be noise OR texture.
    # It is not a calibrated sensor-noise estimate and requires matched scene content.
    if m['fine_residual'] > max(config.max_residual_floor,
                               config.max_residual_reference_factor*reference.get('fine_residual',0)):
        reasons.append('EXCESS_FINE_RESIDUAL')
    return dict(passed=not reasons,reasons=reasons,metrics=m)


class CapturePolicy:
    """One policy instance per well/tile/timepoint. No automatic reference updates."""
    def __init__(self, reference, capture_id, config=QualityConfig(), roi=None):
        if not isinstance(capture_id,str) or not capture_id.strip():
            raise ValueError('A nonempty capture ID is required')
        self.config=config
        self.roi=roi
        self.reference=reference_metrics(reference,config,roi)
        self.reference_shape=np.asarray(reference).shape
        self.capture_id=capture_id
        self.history=[]
        self.finished=False
        self.last_elapsed=-1.0

    def evaluate(self, rgb, elapsed_s):
        if self.finished:
            raise RuntimeError('Capture cycle is already finished')
        if not np.isfinite(elapsed_s) or elapsed_s < 0 or elapsed_s < self.last_elapsed:
            raise ValueError('Elapsed time must be nonnegative, finite and monotonic')
        self.last_elapsed=float(elapsed_s)
        attempt=len(self.history)+1
        if rgb is not None and np.asarray(rgb).shape != self.reference_shape:
            result=dict(passed=False,reasons=['REFERENCE_SHAPE_MISMATCH'],metrics={})
        else:
            result=assess(rgb,self.reference,self.config,self.roi)
        if elapsed_s >= self.config.max_elapsed_s:
            result['reasons'].append('TIME_BUDGET_EXCEEDED')
            decision='ESCALATE'
        elif result['passed']:
            decision='ACCEPT'
        elif attempt >= self.config.max_attempts:
            decision='ESCALATE'
        else:
            decision='RETRY'
        row=dict(capture_id=self.capture_id,attempt=attempt,elapsed_s=float(elapsed_s),
                 decision=decision,**result)
        if 'TIME_BUDGET_EXCEEDED' in row['reasons']:
            row['passed']=False
        self.history.append(row)
        self.finished=decision in {'ACCEPT','ESCALATE'}
        return row


def run_capture_cycle(capture_fn: Callable, reference, capture_id, config=QualityConfig(),
                      roi=None, cancel_fn=lambda:False, clock=time.monotonic):
    """Call a supplied capture function. Does not move a stage or restart a camera.

    capture_fn must itself have a timeout. This loop cannot interrupt a blocked
    callback. The existing lab camera owns its own timeout/recovery behavior.
    Only the accepted frame is returned for downstream storage. Log all history.
    """
    policy=CapturePolicy(reference,capture_id,config,roi)
    started=clock()
    while not policy.finished:
        if cancel_fn():
            policy.history.append(dict(capture_id=capture_id,decision='CANCELLED',
                                       attempt=len(policy.history),elapsed_s=clock()-started,
                                       passed=False,reasons=['OPERATOR_CANCELLED'],metrics={}))
            return None,policy.history
        if clock()-started >= config.max_elapsed_s:
            policy.evaluate(None,clock()-started)
            return None,policy.history
        try:
            rgb=capture_fn()
        except Exception as exc:
            rgb=None
            capture_error=type(exc).__name__
        else:
            capture_error=None
        row=policy.evaluate(rgb,clock()-started)
        if capture_error:
            row['capture_error_type']=capture_error
        if row['decision']=='ACCEPT':
            return rgb,policy.history
    return None,policy.history


def save_log(path, history, config=QualityConfig()):
    Path(path).write_text(json.dumps(dict(config=asdict(config),attempts=history),indent=2))
