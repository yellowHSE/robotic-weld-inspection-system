from robodk import robolink
from robodk import robomath
RDK = robolink.Robolink()

from robodk import *
from robolink import *
from random import uniform

APPROACH = 100

robot               = RDK.Item('UR10 A', robolink.ITEM_TYPE_ROBOT)
tool                = RDK.Item('GripperA', robolink.ITEM_TYPE_TOOL)
frame_pallet        = RDK.Item('PalletA', robolink.ITEM_TYPE_FRAME)
frame_conv          = RDK.Item('ConveyorReference', robolink.ITEM_TYPE_FRAME)
frame_conv_moving   = RDK.Item('MovingRef', robolink.ITEM_TYPE_FRAME)

target_pallet_safe  = RDK.Item('PalletApproachA', robolink.ITEM_TYPE_TARGET)
target_conv_safe    = RDK.Item('ConvApproachA', robolink.ITEM_TYPE_TARGET)
target_conv         = RDK.Item('Put Conveyor', robolink.ITEM_TYPE_TARGET)

SIZE_BOX = RDK.getParam('SizeBox')
SIZE_PALLET = RDK.getParam('SizePallet')
SIZE_BOX_XYZ = [float(x.replace(' ','')) for x in SIZE_BOX.split(',')]
SIZE_PALLET_XYZ = [float(x.replace(' ','')) for x in SIZE_PALLET.split(',')]
SIZE_BOX_Z = SIZE_BOX_XYZ[2]

def box_calc(size_xyz, pallet_xyz):
    sx, sy, sz = size_xyz
    px, py, pz = pallet_xyz
    xyz_list = []
    for h in range(int(pz)):
        for j in range(int(py)):
            for i in range(int(px)):
                xyz_list.append([(i+0.5)*sx, (j+0.5)*sy, (h+0.5)*sz])
    return xyz_list

def find_part_item_by_index(i):
    return RDK.Item(f'Part {i+1}', robolink.ITEM_TYPE_OBJECT)

def find_weld_item_by_index(i):
    return RDK.Item(f'Weld_{i+1}', robolink.ITEM_TYPE_OBJECT)

def safe_set_parent_static(child, new_parent):
    """부모 변경 시 텔레포트 방지: 절대좌표 유지."""
    if not (child and child.Valid() and new_parent and new_parent.Valid()):
        return
    if hasattr(child, 'setParentStatic'):
        child.setParentStatic(new_parent)
        return
    pose_abs = child.PoseAbs()
    child.setParent(new_parent)
    child.setPoseAbs(pose_abs)

def reparent_weld_to_part(i, part_item):
    """Weld_i 를 Part i의 child로 보장 (상자와 같이 이동/회전)."""
    weld = find_weld_item_by_index(i)
    if weld.Valid():
        safe_set_parent_static(weld, part_item)
        try:
            weld.setVisible(True, False)
        except:
            pass

def TCP_On_Box(i):
    """
    Part i(상자)를 tool에 정확히 attach.
    Weld_i는 Part의 child이므로 같이 따라오게 보장.
    """
    part_item = find_part_item_by_index(i)
    if not part_item.Valid():
        raise Exception(f'Part {i+1} not found')

    reparent_weld_to_part(i, part_item)

    safe_set_parent_static(part_item, tool)

    tool.RDK().RunMessage('Set air valve on')
    tool.RDK().RunProgram('TCP_On()')

def TCP_Off_Box(i, leave_parent):
    """
    tool에 붙어있는 Part i를 leave_parent 아래로 내려놓음.
    """
    part_item = find_part_item_by_index(i)
    if not part_item.Valid():
        raise Exception(f'Part {i+1} not found')

    safe_set_parent_static(part_item, leave_parent)

    tool.RDK().RunMessage('Set air valve off')
    tool.RDK().RunProgram('TCP_Off()')

# ----------------------- START -----------------------

parts_positions = box_calc(SIZE_BOX_XYZ, SIZE_PALLET_XYZ)

tool_xyzrpw = tool.PoseTool() * robomath.transl(0, 0, SIZE_BOX_Z/2)
tool_tcp = robot.AddTool(tool_xyzrpw, 'TCP A')
robot.setPoseTool(tool_tcp)

nparts = len(parts_positions)
i = nparts - 1

while i >= 0:

    # ----------- pick from pallet -----------
    robot.setPoseFrame(frame_pallet)

    part_position_i = parts_positions[i]
    target_i = robomath.transl(part_position_i) * robomath.rotx(pi)
    target_i_app = target_i * robomath.transl(0, 0, -(APPROACH + SIZE_BOX_Z))

    robot.MoveJ(target_pallet_safe)
    robot.MoveJ(target_i_app)
    robot.MoveL(target_i)

    TCP_On_Box(i)

    robot.MoveL(target_i_app)
    robot.MoveJ(target_pallet_safe)

    # ----------- place on conveyor -----------
    robot.setPoseFrame(frame_conv)

    target_conv_pose = target_conv.Pose() * robomath.transl(0, 0, -SIZE_BOX_Z/2)
    target_conv_app  = target_conv_pose * robomath.transl(0, 0, -APPROACH)

    robot.MoveJ(target_conv_safe)
    robot.MoveJ(target_conv_app)

    TX = 0
    place_pose = target_conv_pose * robomath.transl(TX, 0, 0)
    robot.MoveL(place_pose)

    TCP_Off_Box(i, frame_conv_moving)
    
    robot.MoveL(target_conv_app)

    pause(5)

    robot.MoveJ(target_conv_safe)

    i -= 1