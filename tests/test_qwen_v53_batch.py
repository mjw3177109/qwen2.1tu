"""V5.3 batch intake regression tests. All images are synthetic byte fixtures."""
import io
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.qwen_batch_ingest import prepare_batch, BatchValidationError, submit_batch

PROMPT="Only modify the worker's helmet color."
PATCH={"mode":"patch","crop_box":[0,0,160,120],
       "polygon":[[20,20],[120,20],[120,80],[20,80]],"feather":2}
RECOLOR={"mode":"recolor","polygon":[[20,20],[120,20],[120,80],[20,80]],
         "color_transform":"white_to_safety_yellow"}
IMAGE_BYTES=b"synthetic-original-image-for-policy-tests"

def zip_batch(items):
    handle=TemporaryDirectory()
    location=Path(handle.name)/"batch.zip"
    with zipfile.ZipFile(location,'w') as z:
        for name,body in items.items():
            z.writestr(name,body if isinstance(body,bytes) else
                       json.dumps(body,ensure_ascii=False) if isinstance(body,dict) else body)
    return handle,location

class BatchGate(unittest.TestCase):
    def files(self,region=None):
        f={"sources/SH001.jpg":IMAGE_BYTES,"prompts/SH001.txt":PROMPT}
        if region:
            f["regions/SH001.json"]=region
        return f

    def test_missing_geometry_reject_before_submission(self):
        handle,path=zip_batch(self.files())
        with handle:
            with self.assertRaisesRegex(BatchValidationError,"NEEDS_REGION"):
                prepare_batch(path)

    def test_patch_per_image_region(self):
        handle,path=zip_batch(self.files(PATCH))
        with handle:
            plan=prepare_batch(path)
        self.assertEqual(plan['count'],1)
        job=plan['jobs'][0]
        self.assertEqual(job['edit_mode'],'local_patch')
        self.assertEqual(job['edit_region'],PATCH)
        dry=submit_batch(plan,'mjw3177109/qwen2.1tu','',dry_run=True)
        self.assertEqual(dry['submitted'],1)

    def test_recolor_accepts_explicit_transform(self):
        handle,path=zip_batch(self.files(RECOLOR))
        with handle:
            job=prepare_batch(path)['jobs'][0]
        self.assertEqual(job['edit_mode'],'local_recolor')

    def test_full_redraw_requires_approval_and_instruction(self):
        csv_data=(
            "source,prompt,edit_mode,full_redraw_authorized,full_redraw_user_instruction\n"
            'sources/SH001.jpg,Convert entire photo to oil painting,full_redraw,true,用户明确要求整张工厂图片进行油画风格重绘\n'
        )
        items={"sources/SH001.jpg":IMAGE_BYTES,"batch.csv":csv_data}
        handle,path=zip_batch(items)
        with handle:
            job=prepare_batch(path)['jobs'][0]
        self.assertTrue(job['full_redraw_authorized'])
        self.assertEqual(job['edit_mode'],'full_redraw')
        items['batch.csv']=csv_data.replace(',true,',',false,')
        handle,path=zip_batch(items)
        with handle:
            with self.assertRaises(BatchValidationError):
                prepare_batch(path)

    def test_reject_region_name_mismatch(self):
        items=self.files(PATCH)
        items["regions/SH002.json"]=items.pop("regions/SH001.json")
        handle,path=zip_batch(items)
        with handle:
            with self.assertRaises(BatchValidationError):
                prepare_batch(path)

if __name__=='__main__':
    unittest.main()
