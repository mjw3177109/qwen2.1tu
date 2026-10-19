import unittest
from tools.qwen_v53_policy import PolicyError, validate_task_policy

P = [[20, 20], [120, 20], [120, 70], [20, 70]]
BOX = [0, 0, 160, 100]


class PolicyTests(unittest.TestCase):
    def code(self,job,expected,image_size=(400,300)):
        with self.assertRaises(PolicyError) as ctx:
            validate_task_policy(job,image_size)
        self.assertEqual(ctx.exception.code, expected)

    def test_missing_region_denies_legacy_whole_frame(self):
        self.code({"prompt":"Only modify the yellow hat"}, "NEEDS_REGION")

    def test_explicit_local_patch(self):
        self.assertEqual("local_patch", validate_task_policy(
            {"edit_mode":"local_patch","edit_region":{
                "mode":"patch","crop_box":BOX,"polygon":P}},(400,300)))

    def test_backward_compatible_scoped_v52(self):
        self.assertEqual("local_patch", validate_task_policy(
            {"edit_region":{"mode":"patch","crop_box":BOX,"polygon":P}},(400,300)))

    def test_full_redraw_requires_both_authorization_and_original_instruction(self):
        self.code({"edit_mode":"full_redraw"}, "FULL_REDRAW_NOT_AUTHORIZED")
        self.code({"edit_mode":"full_redraw","full_redraw_authorized":True},
                  "FULL_REDRAW_NOT_AUTHORIZED")
        self.assertEqual("full_redraw",validate_task_policy({
            "edit_mode":"full_redraw","full_redraw_authorized":True,
            "full_redraw_user_instruction":"用户要求整张图片转换为水彩风格，允许重新绘制所有内容"},(400,300)))

    def test_local_recolor_must_be_explicit_supported_transform(self):
        self.code({"edit_mode":"local_recolor","edit_region":{
            "mode":"recolor","polygon":P}}, "UNSUPPORTED_RECOLOR")
        self.assertEqual("local_recolor",validate_task_policy({
            "edit_mode":"local_recolor","edit_region":{
            "mode":"recolor","polygon":P,"color_transform":"white_to_safety_yellow"}},(400,300)))

    def test_out_of_bounds(self):
        self.code({"edit_mode":"local_patch","edit_region":{
            "mode":"patch","crop_box":[0,0,1000,100],"polygon":P}}, "INVALID_REGION")
        self.code({"edit_mode":"local_recolor","edit_region":{
            "mode":"recolor","polygon":[[399,290],[600,290],[600,310]],
            "color_transform":"white_to_safety_yellow"}}, "INVALID_REGION")

    def test_polygon_missing(self):
        self.code({"edit_mode":"local_patch","edit_region":{
            "mode":"patch","crop_box":BOX}}, "INVALID_REGION")

    def test_conflicting_full_redraw_and_local_region(self):
        self.code({"edit_mode":"full_redraw","full_redraw_authorized":True,
                   "full_redraw_user_instruction":"用户明确要求整图风格变化",
                   "edit_region":{"mode":"patch","crop_box":BOX,"polygon":P}},
                  "CONFLICTING_SCOPE")

    def test_no_edit_over_85_percent(self):
        self.code({"edit_mode":"local_recolor","edit_region":{
            "mode":"recolor","polygon":[[0,0],[400,0],[400,300],[0,300]],
            "color_transform":"white_to_safety_yellow"}}, "NEEDS_REGION")

    def test_invalid_values(self):
        self.code({"edit_mode":"local_patch","edit_region":{
            "mode":"patch","crop_box":BOX,"polygon":[[float("nan"),20],[120,20],[120,70]]}},
            "INVALID_REGION")


if __name__=="__main__":
    unittest.main()
