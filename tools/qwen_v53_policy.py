"""Fail-closed scope policy for Qwen-Image-2.1 editor V5.3.

A prompt (including words like 'only') is not a pixel mask. Geometry is
required before any local model inference. Entire-frame redraw is opt-in.
This file does NOT infer bounding boxes from text.
"""
from __future__ import annotations

import math
from typing import Any


class PolicyError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


MODES = {"local_patch", "local_recolor", "full_redraw"}
RECOLOR_TRANSFORMS = {"white_to_safety_yellow"}


def require_number(x: Any) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise PolicyError("INVALID_REGION", "坐标必须是有限数值")
    return float(x)


def polygon_area(points: list) -> float:
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1] -
                   points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points))) / 2.0)


def validate_task_policy(job: dict, image_size: tuple[int, int] | None = None) -> str:
    """Return authorized mode, or raise PolicyError before inference.

    image_size: ORIGINAL uploaded source image dimensions, not downscaled crop.
    """
    mode = job.get("edit_mode")
    region = job.get("edit_region")
    if mode is None:
        # Backwards-compatible V5.2 jobs with an actual polygon still remain safe.
        if isinstance(region, dict) and region.get("mode") == "patch":
            mode = "local_patch"
        elif isinstance(region, dict) and region.get("mode") == "recolor":
            mode = "local_recolor"
        else:
            raise PolicyError(
                "NEEDS_REGION",
                "没有经过确认的原图编辑范围；请添加 edit_region 的 crop_box 和 polygon，"
                "或在用户确实要求整图重绘时显式授权 full_redraw。禁止默认整图缩小重绘。"
            )

    if mode not in MODES:
        raise PolicyError("INVALID_EDIT_MODE", "edit_mode 必须为 local_patch/local_recolor/full_redraw")

    if mode == "full_redraw":
        if region is not None:
            raise PolicyError("CONFLICTING_SCOPE", "整图重绘不能混用局部 edit_region")
        if job.get("full_redraw_authorized") is not True:
            raise PolicyError("FULL_REDRAW_NOT_AUTHORIZED", "整图重绘需要 full_redraw_authorized=true")
        instruction = job.get("full_redraw_user_instruction", "")
        if not isinstance(instruction, str) or len(instruction.strip()) < 8:
            raise PolicyError("FULL_REDRAW_NOT_AUTHORIZED",
                              "必须填写用户明确要求全图重绘的原始指令（至少8字），不能仅由模型猜测")
        return mode

    if not isinstance(region, dict):
        raise PolicyError("NEEDS_REGION", "局部编辑必须有原图像素坐标的 edit_region")
    if region.get("mode") != ("patch" if mode == "local_patch" else "recolor"):
        raise PolicyError("INVALID_REGION", "edit_region.mode 与 edit_mode 不一致")
    polygon = region.get("polygon")
    if not isinstance(polygon, list) or not (3 <= len(polygon) <= 500):
        raise PolicyError("INVALID_REGION", "必须提供3至500个点组成的 polygon")

    pts = []
    for pt in polygon:
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise PolicyError("INVALID_REGION", "polygon 点必须是[x,y]")
        pts.append((require_number(pt[0]), require_number(pt[1])))
    if polygon_area(pts) < 8:
        raise PolicyError("INVALID_REGION", "polygon 面积太小或退化")

    feather = require_number(region.get("feather", 1.5))
    if not (0 <= feather <= 32):
        raise PolicyError("INVALID_REGION", "feather 必须为0到32像素")

    if mode == "local_patch":
        box = region.get("crop_box")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            raise PolicyError("NEEDS_REGION", "局部 Qwen 编辑必须提供 crop_box=[x0,y0,x1,y1]")
        x0, y0, x1, y1 = [require_number(i) for i in box]
        if not all(float(i).is_integer() for i in (x0, y0, x1, y1)):
            raise PolicyError("INVALID_REGION", "crop_box 必须是原图整数像素坐标")
        if x0 < 0 or y0 < 0 or x0 >= x1 or y0 >= y1:
            raise PolicyError("INVALID_REGION", "crop_box 无效")
        if not all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
            raise PolicyError("INVALID_REGION", "polygon 必须在 crop_box 内")
    else:
        if region.get("color_transform") not in RECOLOR_TRANSFORMS:
            raise PolicyError("UNSUPPORTED_RECOLOR",
                              "V5.3 CPU recolor 当前只支持明确指定 white_to_safety_yellow")
        if region.get("crop_box") is not None:
            raise PolicyError("INVALID_REGION", "local_recolor 不需要 crop_box，避免坐标混淆")

    if image_size is not None:
        if len(image_size) != 2 or any(not isinstance(v,int) or v <= 0 for v in image_size):
            raise PolicyError("INVALID_REGION", "原图宽高无效")
        w,h = image_size
        if not all(0 <= x <= w and 0 <= y <= h for x,y in pts):
            raise PolicyError("INVALID_REGION", "polygon 超出原图实际尺寸")
        if polygon_area(pts) >= w*h*0.85:
            raise PolicyError("NEEDS_REGION", "选区覆盖超85%画面，请人工确认局部范围或显式选择整图重绘")
        if mode == "local_patch" and (x1 > w or y1 > h):
            raise PolicyError("INVALID_REGION", "crop_box 超出原图实际尺寸")
    return mode
