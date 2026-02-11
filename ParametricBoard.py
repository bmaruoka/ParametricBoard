import adsk.core, adsk.fusion, traceback

# Global reference to keep handlers in memory
handlers = []

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        # 1. Create a command definition
        cmdDef = ui.commandDefinitions.itemById('BoardGenCmd')
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition('BoardGenCmd', 'Build Surfboard', 'Create a parametric board')

        # 2. Connect the "Created" event
        onCommandCreated = BoardCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)

        # 3. Execute the command
        cmdDef.execute()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# --- UI CREATION ---
class BoardCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        eventArgs = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = eventArgs.command
        inputs = cmd.commandInputs

        # Add UI Sliders (ID, Label, Unit, Initial Value)
        inputs.addValueInput('len', 'Length', 'in', adsk.core.ValueInput.createByReal(72 * 2.54)) # Fusion uses cm internally
        inputs.addValueInput('width', 'Max Width', 'in', adsk.core.ValueInput.createByReal(20 * 2.54))
        inputs.addValueInput('n_rocker', 'Nose Rocker', 'in', adsk.core.ValueInput.createByReal(5 * 2.54))
        inputs.addValueInput('t_rocker', 'Tail Rocker', 'in', adsk.core.ValueInput.createByReal(2.5 * 2.54))
        inputs.addValueInput('t_nose', 'Nose Thickness', 'in', adsk.core.ValueInput.createByReal(0.5 * 2.54))
        inputs.addValueInput('t_tail', 'Tail Thickness', 'in', adsk.core.ValueInput.createByReal(0.75 * 2.54))
        inputs.addValueInput('rail_shape', 'Rail Apex (0=Bottom, 1=Top)', '', adsk.core.ValueInput.createByReal(0.4))
        inputs.addIntegerSliderCommandInput('slices', 'Number of Sections', 3, 15)

        # Connect the "Execute" handler
        onExecute = BoardExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)

# --- THE GENERATION LOGIC ---
class BoardExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            root = design.rootComponent
            
            # Get values from UI
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            inputs = eventArgs.command.commandInputs
            
            length = inputs.itemById('len').value
            max_w = inputs.itemById('width').value
            n_rock = inputs.itemById('n_rocker').value
            t_rock = inputs.itemById('t_rocker').value
            t_nose = inputs.itemById('t_nose').value
            t_tail = inputs.itemById('t_tail').value
            rail_shape = inputs.itemById('rail_shape').value # This will be a decimal 0.0 - 1.0
            num_slices = inputs.itemById('slices').valueOne     # This is an integer

            # Trigger the functions we built earlier
            draw_board_framework(root, length, max_w, n_rock, t_rock, t_nose, t_tail, rail_shape, num_slices)
            
        except:
            app.userInterface.messageBox('Execute Failed:\n{}'.format(traceback.format_exc()))
# --- MATH HELPER ---
def get_bezier_points(p0, p1, p2, p3, steps=20):
    points = adsk.core.ObjectCollection.create()
    for i in range(steps + 1):
        t = i / steps
        x = (1-t)**3 * p0.x + 3*(1-t)**2 * t * p1.x + 3*(1-t) * t**2 * p2.x + t**3 * p3.x
        y = (1-t)**3 * p0.y + 3*(1-t)**2 * t * p1.y + 3*(1-t) * t**2 * p2.y + t**3 * p3.y
        z = (1-t)**3 * p0.z + 3*(1-t)**2 * t * p1.z + 3*(1-t) * t**2 * p2.z + t**3 * p3.z
        points.add(adsk.core.Point3D.create(x, y, z))
    return points

def draw_board_framework(root, length, width, n_rock, t_rock, t_nose, t_tail, rail_shape, num_slices):
    sketches = root.sketches
    # 1. Clear old geometry (Optional: helps keep the file clean during testing)

    
    # --- 1. DRAW VISIBLE ROCKER PROFILE ---
    rocker_sk = sketches.add(root.xZConstructionPlane)
    rocker_sk.name = "MASTER_ROCKER"
    
    rp0 = adsk.core.Point3D.create(0, t_rock, 0)
    rp1 = adsk.core.Point3D.create(length * 0.3, 0, 0) 
    rp2 = adsk.core.Point3D.create(length * 0.7, 0, 0) 
    rp3 = adsk.core.Point3D.create(length, n_rock, 0)
    
    rocker_points = get_bezier_points(rp0, rp1, rp2, rp3)
    rocker_sk.sketchCurves.sketchFittedSplines.add(rocker_points)

    # --- 2. DRAW VISIBLE OUTLINE ---
    outline_sk = sketches.add(root.xYConstructionPlane)
    outline_sk.name = "MASTER_OUTLINE"
    
    op0 = adsk.core.Point3D.create(0, (width * 0.3), 0) # Tail width
    op1 = adsk.core.Point3D.create(length * 0.4, (width / 2), 0) # Wide point
    op2 = adsk.core.Point3D.create(length * 0.8, (width / 2), 0)
    op3 = adsk.core.Point3D.create(length, 0.001, 0) # Nose point
    
    outline_points = get_bezier_points(op0, op1, op2, op3)
    outline_sk.sketchCurves.sketchFittedSplines.add(outline_points)
    loft_sections = adsk.core.ObjectCollection.create()
    # 3. Create the Slices
    for i in range(num_slices + 1):
        t = i / num_slices
        curr_x = length * t
        
        # SAMPLE THE CURVES: 
        # We calculate the Y for Rocker and Y for Outline at this specific 't'
        rocker_sample = calculate_bezier_y(t, rp0, rp1, rp2, rp3)
        outline_sample = calculate_bezier_y(t, op0, op1, op2, op3)
        
        # Calculate Local Thickness (Interpolate between Tail -> Max -> Nose)
        # Assuming max thickness of 2.5" (6.35cm) in the middle
        max_thick = 6.35 
        if t < 0.5:
            local_thick = t_tail + (t * 2) * (max_thick - t_tail)
        else:
            local_thick = max_thick - ((t - 0.5) * 2) * (max_thick - t_nose)

        """ # 4. Create Plane and Sketch
        planes = root.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(root.yZConstructionPlane, adsk.core.ValueInput.createByReal(curr_x))
        plane = planes.add(plane_input)
        
        sketch = root.sketches.add(plane)
         """
        """ # Draw the cross-section
        # Origin of sketch is (0,0) which is on the stringer at the rocker height
        #p_bottom = adsk.core.Point3D.create(0, 0, 0)
        #p_rail = adsk.core.Point3D.create(0, outline_sample,local_thick * rail_shape)
        #p_deck = adsk.core.Point3D.create(0, 0, rocker_sample + local_thick)
        # 1. Bottom point sitting on the rocker line
        p_bottom = adsk.core.Point3D.create(0, rocker_sample, 0)
        
        # 2. Rail point: Out by 'outline_sample', up by rocker + tucked height
        p_rail = adsk.core.Point3D.create(outline_sample, rocker_sample + (local_thick * rail_shape), 0)
        
        # 3. Deck point: Back to center (0), up by rocker + total thickness
        p_deck = adsk.core.Point3D.create(0, rocker_sample + local_thick, 0)
        
        pts = adsk.core.ObjectCollection.create()
        pts.add(p_bottom)
        pts.add(p_rail)
        pts.add(p_deck)
        sketch.sketchCurves.sketchFittedSplines.add(pts) """
        # 4. Create Plane and Sketch
        planes = root.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(root.yZConstructionPlane, adsk.core.ValueInput.createByReal(curr_x))
        plane = planes.add(plane_input)
        
        sketch = root.sketches.add(plane)
        
        # --- THE FIX: WORLD-TO-SKETCH MAPPING ---
        # We define where these points should be in the 3D WORLD first.
        # World Axes: X = Length, Y = Width, Z = Height (Rocker/Thick)
        
        # Bottom Stringer Point
        p_bottom_world = adsk.core.Point3D.create(curr_x, 0, rocker_sample)
        
        # Rail Apex Point
        p_rail_world = adsk.core.Point3D.create(curr_x, outline_sample, rocker_sample + (local_thick * rail_shape))
        
        # Deck Stringer Point
        p_deck_world = adsk.core.Point3D.create(curr_x, 0, rocker_sample + local_thick)
        
        # Now we "Project" those 3D world points into the 2D sketch plane
        p_bottom = sketch.modelToSketchSpace(p_bottom_world)
        p_rail = sketch.modelToSketchSpace(p_rail_world)
        p_deck = sketch.modelToSketchSpace(p_deck_world)
        
        # 5. Draw the Spline using these transformed points
        pts = adsk.core.ObjectCollection.create()
        pts.add(p_bottom)
        pts.add(p_rail)
        pts.add(p_deck)
        sketch.sketchCurves.sketchFittedSplines.add(pts)

        # 6. Close the profile (Crucial for the Loft to recognize it as a shape)
        sketch.sketchCurves.sketchLines.addByTwoPoints(p_bottom, p_deck)
        
        if sketch.profiles.count > 0:
            loft_sections.add(sketch.profiles.item(0))

    # 5. Execute Loft
    if loft_sections.count > 1:
        loft_feats = root.features.loftFeatures
        loft_input = loft_feats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        for prof in loft_sections:
            loft_input.loftSections.add(prof)
        loft_feats.add(loft_input)

# Helper function to get the Y value at a specific T (0 to 1)
def calculate_bezier_y(t, p0, p1, p2, p3):
    return (1-t)**3 * p0.y + 3*(1-t)**2 * t * p1.y + 3*(1-t) * t**2 * p2.y + t**3 * p3.y