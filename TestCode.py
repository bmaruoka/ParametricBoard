import math 
import adsk.core, adsk.fusion, adsk.cam, traceback

def get_bezier_coordinates(p0, p1, p2, p3, steps=20):
    """
    Calculates a list of points along a cubic Bezier curve.
    p0: Start Point (x, y)
    p1: Control Point 1
    p2: Control Point 2
    p3: End Point
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        # The Cubic Bezier Formula
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points

def generate_rocker_points(length, tail_rocker, nose_rocker):
    # p0: Tail (0, tail_rocker)
    # p3: Nose (length, nose_rocker)
    # Midpoint (Apex): (length/2, 0)
    
    # Simple setup: Two Bezier curves meeting at (length/2, 0)
    # This ensures the lowest point of the board is at the center.
    tail_curve = get_bezier_coordinates(
        (0, tail_rocker),        # Tail start
        (length*0.2, tail_rocker), # Tail handle (flatness)
        (length*0.4, 0),         # Transition handle
        (length*0.5, 0)          # Midpoint
    )
    
    nose_curve = get_bezier_coordinates(
        (length*0.5, 0),         # Midpoint
        (length*0.6, 0),         # Transition handle
        (length*0.8, nose_rocker), # Nose handle
        (length, nose_rocker)      # Nose tip
    )
    
    return tail_curve + nose_curve[1:] # Combine and remove duplicate midpoint

def generate_outline_points(length, max_width, tail_width, nose_width):
    half_max = max_width / 2
    half_tail = tail_width / 2
    half_nose = nose_width / 2

    # Curve from Tail to Wide Point
    back_half = get_bezier_coordinates(
        (0, half_tail),
        (length*0.2, half_tail * 1.2),
        (length*0.4, half_max),
        (length*0.5, half_max)
    )

    # Curve from Wide Point to Nose
    front_half = get_bezier_coordinates(
        (length*0.5, half_max),
        (length*0.6, half_max),
        (length*0.9, half_nose * 1.1),
        (length, half_nose)
    )

    return back_half + front_half[1:]

def draw_base_curves(root_comp, length, tail_rocker, nose_rocker, max_width, tail_width, nose_width):
    # 1. Create Rocker Sketch (XZ Plane)
    rocker_sketch = root_comp.sketches.add(root_comp.xZConstructionPlane)
    rocker_sketch.name = "Rocker_Profile"
    
    rocker_pts = generate_rocker_points(length, tail_rocker, nose_rocker)
    fusion_pts_rocker = adsk.core.ObjectCollection.create()
    for p in rocker_pts:
        fusion_pts_rocker.add(adsk.core.Point3D.create(p[0], p[1], 0))
    
    rocker_sketch.sketchCurves.sketchFittedSplines.add(fusion_pts_rocker)

    # 2. Create Outline Sketch (XY Plane)
    outline_sketch = root_comp.sketches.add(root_comp.xYConstructionPlane)
    outline_sketch.name = "Board_Outline"
    
    outline_pts = generate_outline_points(length, max_width, tail_width, nose_width)
    fusion_pts_outline = adsk.core.ObjectCollection.create()
    for p in outline_pts:
        # Note: In XY plane, Y is the width (z-axis in 3D world space)
        fusion_pts_outline.add(adsk.core.Point3D.create(p[0], p[1], 0))
    
    outline_sketch.sketchCurves.sketchFittedSplines.add(fusion_pts_outline)