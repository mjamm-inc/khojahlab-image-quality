import shutil
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from automatic_intake import ImageIntake
ROOT=Path(__file__).resolve().parents[1]

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.incoming=self.base/'incoming'; self.incoming.mkdir()
    def put(self, fixture, name):
        shutil.copy2(ROOT/'demo_images'/fixture,self.incoming/name)
    def test_missing_reference_never_accepts(self):
        self.put('unchanged.png','capture.png')
        w=ImageIntake(self.incoming,self.base/'out',settle_s=0)
        self.assertEqual(w.scan_once()[0]['decision'],'REFERENCE_REQUIRED')
    def test_new_files_detected_and_restart_deduplicates(self):
        w=ImageIntake(self.incoming,self.base/'out',ROOT/'demo_images/unchanged.png',True,0)
        self.assertEqual(w.scan_once(),[])
        self.put('unchanged.png','capture.png')
        self.assertEqual(w.scan_once()[0]['decision'],'ACCEPT')
        self.assertEqual(w.scan_once(),[])
        restarted=ImageIntake(self.incoming,self.base/'out',ROOT/'demo_images/unchanged.png',True,0)
        self.assertEqual(restarted.scan_once(),[])
        self.put('dark_gain0.02.png','dark.png')
        r=restarted.scan_once()[0]
        self.assertEqual(r['decision'],'RETRY_REQUESTED')
        self.assertFalse(r['hardware_action_performed'])
        self.assertTrue((self.base/'out/measurements.csv').exists())
    def test_unconfirmed_reference_rejected(self):
        with self.assertRaises(ValueError):ImageIntake(self.incoming,self.base/'out',ROOT/'demo_images/unchanged.png')
    def test_invalid_file_does_not_crash_or_accept(self):
        (self.incoming/'broken.jpg').write_text('incomplete')
        w=ImageIntake(self.incoming,self.base/'out',settle_s=0)
        self.assertEqual(w.scan_once()[0]['decision'],'REVIEW_REQUIRED')
    def test_output_cannot_feed_back_into_input(self):
        with self.assertRaises(ValueError):ImageIntake(self.incoming,self.incoming/'results')

if __name__=='__main__':unittest.main()
