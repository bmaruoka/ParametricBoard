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

            # Trigger the functions we built earlier
            draw_board_framework(root, length, max_w, n_rock, t_rock)
            
        except:
            app.userInterface.messageBox('Execute Failed:\n{}'.format(traceback.format_exc()))

def draw_board_framework(root, length, width, n_rock, t_rock):
    """Placeholder for the Bezier functions from our previous step"""
    sketches = root.sketches
    # Create Rocker Sketch
    rocker_sketch = sketches.add(root.xZConstructionPlane)
    rocker_sketch.name = "Rocker"
    
    # Example: Simple line just to prove the UI works
    p1 = adsk.core.Point3D.create(0, t_rock, 0)
    p2 = adsk.core.Point3D.create(length, n_rock, 0)
    rocker_sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)