# ===========================
# Robot2: Conveyor -> (YOLO via RoboDK Camera Snapshot) -> PalletB / Reject
#   - good   : skip (do not pick)
#   - bad    : place to PalletB grid
#   - defect : place to Reject grid
#   - seen_parts: already processed Part excluded
# ===========================

import os, sys

# --- Torch DLL path fix (RoboDK embedded) ---
TORCH_LIB = r"C:\RoboDK\Python-Embedded\Lib\site-packages\torch\lib"
if os.path.isdir(TORCH_LIB):
    try:
        os.add_dll_directory(TORCH_LIB)
    except Exception:
        pass
    os.environ["PATH"] = TORCH_LIB + ";" + os.environ.get("PATH", "")

# OpenMP/Intel MKL 충돌 완화 (WinError 1114 대응)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

os.environ.setdefault("MKL_SERVICE_FORCE_INTEL", "1")
os.environ.setdefault("MKL_THREADING_LAYER", "GNU")

import numpy as np
import cv2
from ultralytics import YOLO

import torch
from robodk import robolink, robomath
from math import pi
import time


# ---------------------------
# User settings (ABS PATH)
# ---------------------------
MODEL_PATH = r"C:\Users\USER\Desktop\svg\svg\best2.pt"   # ✅ 절대경로로 변경
YOLO_DEVICE = -1        # GPU: 0, CPU: -1 (환경에 따라 0이 안되면 -1)
YOLO_IMGSZ  = 640
CONF_THRES  = 0.25

# ✅ RoboDK Camera Item 이름(스테이션에 Camera 아이템이 있어야 함)
CAM_NAME = "Camera 1"   # 예: Station Tree에서 Camera 이름을 InspectCamB로 만들기

# ---------------------------
# RoboDK init
# ---------------------------
RDK = robolink.Robolink()

APPROACH = 100
PART_KEYWORD = "Part"

# -------------------------
# Station items (Robot B)
# -------------------------
robot = RDK.Item("UR10 B", robolink.ITEM_TYPE_ROBOT)
tool  = RDK.Item("GripperB", robolink.ITEM_TYPE_TOOL)

frame_urbaseb     = RDK.Item("UR10 Base B", robolink.ITEM_TYPE_FRAME)     # Reject 기준 프레임
frame_pallet_good = RDK.Item("PalletB", robolink.ITEM_TYPE_FRAME)
frame_conv        = RDK.Item("ConveyorReference", robolink.ITEM_TYPE_FRAME)
frame_conv_moving = RDK.Item("MovingRef", robolink.ITEM_TYPE_FRAME)

# Targets
target_good_safe = RDK.Item("PalletApproachB", robolink.ITEM_TYPE_TARGET)

target_bad_safe  = RDK.Item("RejectApproachB", robolink.ITEM_TYPE_TARGET)
target_bad_put0  = RDK.Item("Put RejectB", robolink.ITEM_TYPE_TARGET)     # Reject “원점 기준(모서리+축 정렬)” 타겟

target_conv_safe = RDK.Item("ConvApproachB", robolink.ITEM_TYPE_TARGET)
target_conv      = RDK.Item("Get Conveyor", robolink.ITEM_TYPE_TARGET)
target_inspect   = RDK.Item("InspectPartB", robolink.ITEM_TYPE_TARGET)

# Camera item
cam_item = RDK.Item(CAM_NAME, robolink.ITEM_TYPE_CAMERA)
if not cam_item.Valid():
    raise Exception(f'Camera "{CAM_NAME}" not found. Create a RoboDK Camera item with this name.')

# -------------------------
# Parameters
# -------------------------
SIZE_BOX = RDK.getParam("SizeBox")
SIZE_PALLET = RDK.getParam("SizePallet")

SIZE_BOX_XYZ = [float(x.replace(" ", "")) for x in SIZE_BOX.split(",")]
SIZE_PALLET_XYZ = [float(x.replace(" ", "")) for x in SIZE_PALLET.split(",")]

SIZE_BOX_Z = SIZE_BOX_XYZ[2]
SIZE_BAD_PALLET_XYZ = SIZE_PALLET_XYZ[:]  # Reject도 동일 격자 가정

# -------------------------
# YOLO load (once)
# -------------------------
if not os.path.exists(MODEL_PATH):
    raise Exception(f"YOLO model not found: {MODEL_PATH}")

model = YOLO(MODEL_PATH)
print("[YOLO] model loaded:", MODEL_PATH)
print("[YOLO] class names:", model.names)

# -------------------------
# Helpers
# -------------------------
def box_calc(size_xyz, pallet_xyz):
    """Grid positions: x->y->z, returns cell-center coordinates"""
    sx, sy, sz = size_xyz
    px, py, pz = pallet_xyz
    out = []
    for h in range(int(pz)):
        for j in range(int(py)):
            for i in range(int(px)):
                out.append([(i + 0.5) * sx, (j + 0.5) * sy, (h + 0.5) * sz])
    return out

def safe_set_parent_static(child, new_parent):
    """Keep absolute pose while reparenting (prevent teleport)."""
    if not (child and child.Valid() and new_parent and new_parent.Valid()):
        return
    if hasattr(child, "setParentStatic"):
        child.setParentStatic(new_parent)
        return
    pose_abs = child.PoseAbs()
    child.setParent(new_parent)
    child.setPoseAbs(pose_abs)

def TCP_On_Part(part_item):
    if part_item is None or not part_item.Valid():
        return False
    tool.DetachAll(0)
    safe_set_parent_static(part_item, tool)
    tool.RDK().RunProgram("TCP_On()")
    return True

def TCP_Off_Part(part_item, leave_parent):
    if part_item is None or not part_item.Valid():
        return False
    safe_set_parent_static(part_item, leave_parent)
    tool.RDK().RunProgram("TCP_Off()")
    return True

# ----------------- camera detection (existing, with seen) -----------------
camera_ref_conv = target_conv.PoseAbs()

all_objects_names = RDK.ItemList(robolink.ITEM_TYPE_OBJECT, True)
check_objects = []
for nm in all_objects_names:
    if PART_KEYWORD in nm:
        check_objects.append(RDK.Item(nm, robolink.ITEM_TYPE_OBJECT))

if len(check_objects) == 0:
    raise Exception(f"No parts found. Name objects with keyword: {PART_KEYWORD}")

seen_parts = set()

def WaitPartCamera(seen_set):
    """
    Return: (part_item, TX, TY, RZ[rad])
    - Excludes already processed parts (seen_set)
    """
    if RDK.RunMode() == robolink.RUNMODE_SIMULATE:
        while True:
            for part in check_objects:
                if not part.Valid():
                    continue

                nm = part.Name()
                if nm in seen_set:
                    continue

                part_pose = robomath.invH(camera_ref_conv) * part.PoseAbs()
                tx, ty, tz, rx, ry, rz_deg = robomath.pose_2_xyzrpw(part_pose)
                rz = rz_deg * pi / 180.0

                # detection window (tune if needed)
                if abs(tx) < 400 and ty < 50 and abs(tz) < 400:
                    print(f"[CAM-DETECT] {nm} | TX,TY,RZ={tx:.1f},{ty:.1f},{rz:.3f}")
                    seen_set.add(nm)  # ✅ mark processed
                    return part, tx, ty, rz

            time.sleep(0.005)
    else:
        RDK.RunProgram("WaitPartCamera")

    return None, 0, 0, 0

# ----------------- YOLO via RoboDK Camera Snapshot -----------------
def snapshot_to_frame(camera_item):
    """
    Repo-style:
      bytes_img = RDK.Cam2D_Snapshot("", cam_item)
      frame = cv2.imdecode(np.frombuffer(bytes_img, np.uint8), cv2.IMREAD_COLOR)
    """
    bytes_img = RDK.Cam2D_Snapshot("", camera_item)
    if bytes_img is None:
        return None
    nparr = np.frombuffer(bytes_img, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame


def yolo_classify_from_camera(camera_item, show=True):
    """
    YOLO로 카메라 이미지 분류 후, OpenCV 창에 시각화
    - 클래스별 색상: good/ok=초록, bad/ng=노랑, defect/fail=빨강
    - Confidence 표시, 배경 박스 포함
    - show=False 시 화면 표시 생략
    """
    frame = snapshot_to_frame(camera_item)

    if frame is None:
        print("[YOLO] snapshot None -> good")
        return "good"

    # YOLO 예측
    results = model.predict(
        source=frame,
        imgsz=YOLO_IMGSZ,
        conf=CONF_THRES,
        device=YOLO_DEVICE,
        verbose=False
    )

    r0 = results[0]
    boxes = r0.boxes

    if boxes is None or len(boxes) == 0:
        if show:
            cv2.imshow("YOLO Inspect", frame)
            cv2.waitKey(30)
        return "good"

    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    clss  = boxes.cls.cpu().numpy().astype(int)

    # 가장 높은 confidence 박스 선택 (최종 판정용)
    best_idx = int(confs.argmax())
    best_cls_id = int(clss[best_idx])
    best_conf = float(confs[best_idx])
    best_name = str(model.names.get(best_cls_id, "")).strip().lower()

    print(f"[YOLO] {best_name} ({best_conf:.2f})")

    # -----------------------------
    # 시각화
    # -----------------------------
    if show:
        annotated = frame.copy()

        for box, conf, cls_id in zip(xyxy, confs, clss):
            x1, y1, x2, y2 = map(int, box)
            name = str(model.names.get(cls_id, "")).strip().lower()

            # 클래스별 색상
            if name in ["good", "ok", "pass"]:
                color = (0, 255, 0)       # 초록
            elif name in ["bad", "ng"]:
                color = (0, 255, 255)     # 노랑
            elif name in ["defect", "defective", "fail"]:
                color = (0, 0, 255)       # 빨강
            else:
                color = (200, 200, 200)   # 회색

            # 1️⃣ 바운딩 박스
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # 2️⃣ 라벨 + Confidence
            label = f"{name.upper()} {conf*100:.1f}%"

            (tw, th), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                2
            )

            # 3️⃣ 배경 박스
            cv2.rectangle(
                annotated,
                (x1, y1 - th - baseline - 6),
                (x1 + tw + 6, y1),
                color,
                -1
            )

            # 4️⃣ 텍스트
            cv2.putText(
                annotated,
                label,
                (x1 + 3, y1 - baseline - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        # 🔵 최종 판정 좌측 상단
        decision_text = f"FINAL: {best_name.upper()} ({best_conf*100:.1f}%)"
        cv2.rectangle(annotated, (10, 10), (500, 60), (50, 50, 50), -1)
        cv2.putText(
            annotated,
            decision_text,
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2
        )

        # 창 표시
        cv2.imshow("YOLO Inspect", annotated)
        cv2.waitKey(1)  # 1ms: 비동기 갱신, 화면 멈추지 않음

    # -----------------------------
    # 최종 클래스 반환
    # -----------------------------
    if best_name in ["good", "ok", "pass"]:
        return "good"
    if best_name in ["bad", "ng"]:
        return "bad"
    if best_name in ["defect", "defective", "fail"]:
        return "defect"

    return "good"

# --------------------------
# PROGRAM START
# --------------------------

good_positions = box_calc(SIZE_BOX_XYZ, SIZE_PALLET_XYZ)      # PalletB 적재(=bad)
bad_positions  = box_calc(SIZE_BOX_XYZ, SIZE_BAD_PALLET_XYZ)  # Reject 적재(=defect)

i_good = 0  # PalletB index
i_bad  = 0  # Reject index

# TCP
tool_xyzrpw = tool.PoseTool() * robomath.transl(0, 0, SIZE_BOX_Z / 2)
tool_tcp = robot.AddTool(tool_xyzrpw, "TCP B")
robot.setPoseTool(tool_tcp)

while True:

    if i_good >= len(good_positions) and i_bad >= len(bad_positions):
        print("[DONE] Both pallets full.")
        break

    # 1) Inspect position (camera view stabilized)
    robot.setPoseFrame(frame_conv)
    robot.MoveJ(target_inspect)

    # 2) Detect new part (seen excluded)
    part_item, CAM_TX, CAM_TY, CAM_RZ = WaitPartCamera(seen_parts)
    if part_item is None or not part_item.Valid():
        continue

    # 3) YOLO classify (repo-style snapshot)
    ycls = yolo_classify_from_camera(cam_item, show=True)
    print(f"[DECISION] {part_item.Name()} -> {ycls}")

    # 4) good -> skip (do not pick)
    if ycls == "good":
        continue

    # 5) bad/defect -> pick from conveyor
    CAM_TY = CAM_TY - 50

    # normalize RZ to [-pi/2, +pi/2]
    if CAM_RZ > pi / 2:
        CAM_RZ -= pi
    elif CAM_RZ < -pi / 2:
        CAM_RZ += pi

    pick_pose = target_conv.Pose() * robomath.transl(CAM_TX, CAM_TY, -SIZE_BOX_Z / 2) * robomath.rotz(CAM_RZ)
    pick_app  = pick_pose * robomath.transl(0, 0, -APPROACH)

    robot.MoveL(pick_pose)

    ok_pick = TCP_On_Part(part_item)
    robot.MoveL(pick_app)

    if (not ok_pick) or (len(tool.Childs()) == 0):
        # pick 실패 시 다시 감지 가능하게 하고 싶으면 아래 1줄 활성화
        # seen_parts.discard(part_item.Name())
        continue

    robot.MoveJ(target_conv_safe)

    RZ_PLACE = 0.0

    # -------------------------
    # YOLO 'bad' -> PalletB grid
    # -------------------------
    if ycls == "bad":
        if i_good >= len(good_positions):
            print("[WARN] PalletB full -> drop back to conveyor")
            TCP_Off_Part(part_item, frame_conv_moving if frame_conv_moving.Valid() else frame_conv)
            robot.MoveJ(target_conv_safe)
            continue

        robot.setPoseFrame(frame_pallet_good)

        x, y, z = good_positions[i_good]
        i_good += 1

        place_pose = robomath.transl(x, y, z) * robomath.rotx(pi) * robomath.rotz(RZ_PLACE)
        place_app  = place_pose * robomath.transl(0, 0, -(APPROACH + SIZE_BOX_Z))

        robot.MoveJ(target_good_safe)
        robot.MoveJ(place_app)
        robot.MoveL(place_pose)

        TCP_Off_Part(part_item, frame_pallet_good)

        robot.MoveL(place_app)
        robot.MoveJ(target_good_safe)
        continue

    # -------------------------
    # YOLO 'defect' -> Reject grid
    # -------------------------
    if ycls == "defect":
        if i_bad >= len(bad_positions):
            print("[WARN] Reject full -> drop back to conveyor")
            TCP_Off_Part(part_item, frame_conv_moving if frame_conv_moving.Valid() else frame_conv)
            robot.MoveJ(target_conv_safe)
            continue

        robot.setPoseFrame(frame_urbaseb)

        x, y, z = bad_positions[i_bad]
        i_bad += 1

        put_pose = target_bad_put0.Pose() * robomath.transl(x, y, z) * robomath.rotz(RZ_PLACE)
        put_app  = put_pose * robomath.transl(0, 0, -(APPROACH + SIZE_BOX_Z))

        robot.MoveJ(target_bad_safe)
        robot.MoveJ(put_app)
        robot.MoveL(put_pose)

        TCP_Off_Part(part_item, frame_urbaseb)

        robot.MoveL(put_app)
        robot.MoveJ(target_bad_safe)
        continue

    # Unknown class -> drop back
    print("[WARN] Unknown class -> drop back to conveyor")
    TCP_Off_Part(part_item, frame_conv_moving if frame_conv_moving.Valid() else frame_conv)
    robot.MoveJ(target_conv_safe)
