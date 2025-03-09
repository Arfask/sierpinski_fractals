import os
import time
import math
import cst.interface
from cst.interface import ProjectType

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
cst_path = r'CST FILE PATH'
cst_project = 'Sierpinski_Triangle'  # Project file name without .cst
project_path = os.path.join(cst_path, cst_project + '.cst')

# Fractal / Antenna parameters
base_size = 176  # Base side length in mm
height = 0.35      # Conductor thickness (mm)
iterations = 4     # Number of fractal iterations

# Names used in CST
base_component = "Main_Antenna"
subtract_component = "Subtract_Temp"

# ---------------------------------------------------------------------
# Set up CST environment and open/create project
# ---------------------------------------------------------------------
mycst = cst.interface.DesignEnvironment()
os.makedirs(cst_path, exist_ok=True)

try:
    mycstproject = mycst.open_project(project_path)
except Exception as e:
    print(f"Error opening project: {e}")
    mycstproject = mycst.new_project(ProjectType.Microwave)
    mycstproject.save(project_path)

model3d = mycstproject.model3d

# Create the subtraction component explicitly in case it doesn't exist
model3d.add_to_history("Create_Subtract_Component", f'Component.New "{subtract_component}"')

# ---------------------------------------------------------------------
# Helper function for Sierpinski midpoints
# ---------------------------------------------------------------------
def midpoint(x1, y1, x2, y2):
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

# ---------------------------------------------------------------------
# Recursive Sierpinski function
# ---------------------------------------------------------------------
def create_sierpinski_subtraction(level, A, B, C, model3d, thickness, subtract_comp, fractal_names):
    """
    Subtracts the 'inverted' triangle (formed by the midpoints of A,B,C),
    then recurses on each of the 3 corner triangles that remain.

    :param level: current recursion level
    :param A, B, C: (x, y) corners of the current (upright) equilateral triangle
    :param model3d: CST model3d interface
    :param thickness: conductor thickness for extrusion
    :param subtract_comp: component name for storing sub-triangle shapes
    :param fractal_names: list in which to store all sub-triangle names
    """
    if level == 0:
        return

    # Midpoints of each side
    MAB = midpoint(A[0], A[1], B[0], B[1])
    MBC = midpoint(B[0], B[1], C[0], C[1])
    MCA = midpoint(C[0], C[1], A[0], A[1])

    # The "hole" triangle in the center, formed by these midpoints
    unique_name = f"Sierpinski_L{level}_X{(A[0]+B[0]+C[0])/3.0:.4f}_Y{(A[1]+B[1]+C[1])/3.0:.4f}"

    # 1) Create the "inverted" triangle polygon
    model3d.add_to_history(
        f"Create_{unique_name}",
        f'''With Polygon
            .Reset
            .Name "{unique_name}_Curve"
            .Curve "FractalCurve"
            .Point "{MAB[0]}", "{MAB[1]}"
            .Point "{MBC[0]}", "{MBC[1]}"
            .Point "{MCA[0]}", "{MCA[1]}"
            .Point "{MAB[0]}", "{MAB[1]}"   ' close the polygon
            .Create
        End With'''
    )

    # 2) Extrude that polygon so we can subtract it from the main antenna
    model3d.add_to_history(
        f"Extrude_{unique_name}",
        f'''With ExtrudeCurve
            .Reset
            .Name "{unique_name}"
            .Component "{subtract_comp}"
            .Material "PEC"
            .Thickness "{thickness}"
            .Twistangle "0.0"
            .Taperangle "0.0"
            .DeleteProfile "True"
            .Curve "FractalCurve:{unique_name}_Curve"
            .Create
        End With'''
    )

    # Record the shape name for the subsequent boolean subtraction
    fractal_names.append(unique_name)

    # 3) Recurse on the three corner sub-triangles
    create_sierpinski_subtraction(level - 1, A, MAB, MCA, model3d, thickness, subtract_comp, fractal_names)
    create_sierpinski_subtraction(level - 1, B, MBC, MAB, model3d, thickness, subtract_comp, fractal_names)
    create_sierpinski_subtraction(level - 1, C, MCA, MBC, model3d, thickness, subtract_comp, fractal_names)

# ---------------------------------------------------------------------
# Create Main Base Triangle
# ---------------------------------------------------------------------
base_triangle_name = "Base_Shape"
base_height = base_size * math.sqrt(3) / 2.0  # height of equilateral triangle

# 1) Define the 2D polygon for the large base triangle
model3d.add_to_history(
    "Create_Base_Polygon",
    f'''With Polygon
        .Reset
        .Name "{base_triangle_name}_Curve"
        .Curve "MainCurve"
        .LineTo "{-base_size/2}", "0"
        .LineTo "{ base_size/2}", "0"
        .LineTo "0", "{ base_height}"
        .LineTo "{-base_size/2}", "0"
        .Create
    End With'''
)

# 2) Extrude that polygon to create a 3D PEC shape
model3d.add_to_history(
    "Extrude_Base",
    f'''With ExtrudeCurve
        .Reset
        .Name "{base_triangle_name}"
        .Component "{base_component}"
        .Material "PEC"
        .Thickness "{height}"
        .Twistangle "0.0"
        .Taperangle "0.0"
        .DeleteProfile "False"
        .Curve "MainCurve:{base_triangle_name}_Curve"
        .Create
    End With'''
)

# ---------------------------------------------------------------------
# Generate the Sierpinski subtractions
# ---------------------------------------------------------------------
fractal_shape_names = []

# Coordinates of the base triangle's corners:
A = (-base_size / 2.0, 0.0)
B = ( base_size / 2.0, 0.0)
C = (0.0, base_height)

# Call the recursive function
create_sierpinski_subtraction(iterations, A, B, C,
                              model3d, height,
                              subtract_component,
                              fractal_shape_names)

# ---------------------------------------------------------------------
# Perform Boolean subtractions from the main antenna shape
# ---------------------------------------------------------------------
for shape_name in fractal_shape_names:
    model3d.add_to_history(
        f"Subtract_{shape_name}",
        f'''
        With Solid
            .Subtract "{base_component}:{base_triangle_name}", "{subtract_component}:{shape_name}"
        End With
        '''
    )

# ---------------------------------------------------------------------
# Finalize project
# ---------------------------------------------------------------------
time.sleep(3)  # small delay if needed
mycstproject.save()
mycstproject.close()
mycst.close()
