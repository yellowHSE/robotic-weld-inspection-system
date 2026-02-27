from robodk import robolink, robomath
from robodk import *
from robolink import *
from random import randint

RDK = robolink.Robolink()

frame_pallet = RDK.Item('PalletA', robolink.ITEM_TYPE_FRAME)

SIZE_BOX = RDK.getParam('SizeBox')
SIZE_PALLET = RDK.getParam('SizePallet')
SIZE_BOX_XYZ = [float(x.replace(' ','')) for x in SIZE_BOX.split(',')]
SIZE_PALLET_XYZ = [float(x.replace(' ','')) for x in SIZE_PALLET.split(',')]
SIZE_BOX_Z = SIZE_BOX_XYZ[2]

def box_calc(size_xyz, pallet_xyz):
    sx, sy, sz = size_xyz
    px, py, pz = pallet_xyz
    out = []
    for h in range(int(pz)):
        for j in range(int(py)):
            for i in range(int(px)):
                out.append([(i+0.5)*sx, (j+0.5)*sy, (h+0.5)*sz])
    return out

def cleanup_prefix(prefixes):
    objs = RDK.ItemList(robolink.ITEM_TYPE_OBJECT, False)
    for it in objs:
        try:
            if not it.Valid(): 
                continue
            for p in prefixes:
                if it.Name().startswith(p):
                    it.Delete()
                    break
        except:
            continue

def parts_setup_with_weld(frame, positions, size_xyz,
                          box_template='box100mm',
                          weld_tpl_prefix='WeldTpl_',
                          weld_tpl_count=9,
                          weld_ratio=0.8,
                          z_gap=3,
                          choose_mode='cycle',   # 'cycle' or 'random'
                          hide_weld_templates=True):
    sx, sy, sz = size_xyz

    box_tpl = RDK.Item(box_template, robolink.ITEM_TYPE_OBJECT)
    if not box_tpl.Valid():
        raise Exception(f'Box template "{box_template}" not found.')

    # Weld templates cache
    weld_tpls = []
    for k in range(1, weld_tpl_count+1):
        nm = f'{weld_tpl_prefix}{k:02d}'
        it = RDK.Item(nm, robolink.ITEM_TYPE_OBJECT)
        if not it.Valid():
            raise Exception(f'Weld template "{nm}" not found.')
        weld_tpls.append(it)

    if hide_weld_templates:
        for it in weld_tpls:
            try: it.setVisible(False, False)
            except: pass

    # cleanup previous
    cleanup_prefix(['Part ', 'Weld_'])

    for i, pos in enumerate(positions):
        # box
        box_tpl.Copy()
        part = frame.Paste()
        part.Scale([sx/100.0, sy/100.0, sz/100.0])
        part.setName(f'Part {i+1}')
        part.setPose(robomath.transl(pos))
        part.setVisible(True, False)

        # select weld template
        if choose_mode == 'random':
            tpl = weld_tpls[randint(0, weld_tpl_count-1)]
        else:  # cycle
            tpl = weld_tpls[i % weld_tpl_count]

        # weld instance
        tpl.Copy()
        weld = frame.Paste()
        weld.setName(f'Weld_{i+1}')
        weld.setParent(part)
        weld.setPose(robomath.transl([0, 0, sz/2.0 + z_gap]))

        # scale to top face
        wx = (weld_ratio * sx) / 100.0
        wy = (weld_ratio * sy) / 100.0
        weld.Scale([wx, wy, 1.0])

        try: weld.setVisible(True, False)
        except: pass

RDK.Render(False)
parts_positions = box_calc(SIZE_BOX_XYZ, SIZE_PALLET_XYZ)

parts_setup_with_weld(
    frame_pallet,
    parts_positions,
    SIZE_BOX_XYZ,
    box_template='box100mm',
    weld_tpl_prefix='WeldTpl_',
    weld_tpl_count=8,
    weld_ratio=0.8,
    z_gap=2.0,
    choose_mode='cycle',
    hide_weld_templates=True
)

RDK.Render(True)
