import os
import cst.interface
from cst.interface import ProjectType
import time

# Configuration
cst_path = r'CST PATH FILE'
cst_project = 'Sierpinski_Level'
project_path = os.path.join(cst_path, cst_project + '.cst')

# Parameters
base_size = 50       # Level 0 size (mm)
height = 0.35        # Conductor thickness (mm)
iterations = 3       # Number of fractal iterations
base_component = "Main_Antenna"
subtract_component = "Subtract_Temp"

# CST Environment Setup
mycst = cst.interface.DesignEnvironment()
os.makedirs(cst_path, exist_ok=True)

try:
    mycstproject = mycst.open_project(project_path)
except Exception as e:
    print(f"Error opening project: {e}")
    mycstproject = mycst.new_project(ProjectType.Microwave)
    mycstproject.save(project_path)

model3d = mycstproject.model3d

# List to store fractal shape names
fractal_shape_names = []

# Unique Name Generator
def generate_unique_name(level, x, y):
    return f"Sub_L{level}_X{x:.4f}_Y{y:.4f}"

# Create subtraction component explicitly
model3d.add_to_history("Create_Subtract_Component", f'Component.New "{subtract_component}"')

# Modified Fractal Generator
def create_subtraction_squares(level, x_center, y_center, current_size):
    if level < 0:
        return
    
    sub_size = current_size / 3
    offset = sub_size
    
    # Create center square to subtract
    x_pos = x_center
    y_pos = y_center
    unique_name = generate_unique_name(level, x_pos, y_pos)
    
    model3d.add_to_history(
        f"Create_{unique_name}", 
        f'''With Brick
            .Reset
            .Name "{unique_name}"
            .Component "{subtract_component}"
            .Material "Vacuum"
            .Xrange "{x_pos - sub_size/2:.6f}", "{x_pos + sub_size/2:.6f}"
            .Yrange "{y_pos - sub_size/2:.6f}", "{y_pos + sub_size/2:.6f}"
            .Zrange "0", "{height}"
            .Create
        End With'''
    )
    
    # Add the shape name to the list
    fractal_shape_names.append(unique_name)
    
    # Recursive call for surrounding squares
    if level > 0:
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                if i == 0 and j == 0:
                    continue
                x_new = x_center + i * offset
                y_new = y_center + j * offset
                create_subtraction_squares(level-1, x_new, y_new, sub_size)

# Main Structure Creation
# Create base square
base_brick = "Base_Shape"
model3d.add_to_history("Create_Base", f'''With Brick
    .Reset
    .Name "{base_brick}"
    .Component "{base_component}"
    .Material "PEC"
    .Xrange "{-base_size/2}", "{base_size/2}"
    .Yrange "{-base_size/2}", "{base_size/2}"
    .Zrange "0", "{height}"
    .Create
End With''')

# Generate subtraction pattern
create_subtraction_squares(iterations, 0, 0, base_size)

# Replace the subtraction part with this:
time.sleep(5)  # Keep the delay

# Perform Boolean subtraction: Subtract all fractal shapes from the base shape
for shape_name in fractal_shape_names:
    model3d.add_to_history(f"Subtract_{shape_name}", f'''
        With Solid
            .Subtract "{base_component}:{base_brick}", "{subtract_component}:{shape_name}"
        End With
    ''')

# Finalize
mycstproject.save()
mycstproject.close()
mycst.close()
