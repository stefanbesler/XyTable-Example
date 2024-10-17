from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, LVecBase4
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import LineSegs
from direct.task import Task
from panda3d.core import NodePath
from direct.interval.IntervalGlobal import LerpPosInterval  # Correct import

class XYTableApp(ShowBase):
    def __init__(self):
        super().__init__()

        self.disableMouse()
        self.camera.setPos(15, -15, 15)
        self.camera.lookAt(0, 0, 0)

        self.create_grid()
        self.y_rail = self.create_box(scale=(0.2, 40, 0.2), position=(-4.5, 0, 0), color=(0.8, 0.8, 0.8, 1))
        self.x_rail = self.create_box(scale=(20, 0.2, 0.2), position=(5, 10, 0), color=(0.8, 0.8, 0.8, 1))
      
        self.tool = self.create_box(scale=(0.1, 1.5, 1.5), position=(0, 0, 0), color=(1, 0, 0, 1))
        self.tool.reparentTo(self.x_rail)  # Attach the tool to the X-axis rail

        self.pen_tip = self.create_box(scale=(0.1, 0.1, 3.1), position=(0, 0, 0.5), color=(0, 0, 1, 1))
        self.pen_tip.reparentTo(self.tool)

        # Setup key controls for movement
        self.accept("arrow_up", self.move_x_rail, [0, 0.1])
        self.accept("arrow_down", self.move_x_rail, [0, -0.1])
        self.accept("arrow_left", self.move_tool, [-0.1, 0])
        self.accept("arrow_right", self.move_tool, [0.1, 0])
        self.accept("d", self.move_pen_down)
        self.accept("u", self.move_pen_up)

        # Track the pen's path
        self.pen_positions = []

        # Lighting
        self.setup_lights()

        # Pen's initial Z-position
        self.pen_z_position = 0.5
        self.pen_down = False

    def create_grid(self):
        """Create the grid (table surface) for drawing."""
        grid_size = 20
        step = 1
        for x in range(-grid_size, grid_size + 1, step):
            self.create_line(start=Vec3(x, -grid_size, 0), end=Vec3(x, grid_size, 0), color=(0.5, 0.5, 0.5, 1))
        for y in range(-grid_size, grid_size + 1, step):
            self.create_line(start=Vec3(-grid_size, y, 0), end=Vec3(grid_size, y, 0), color=(0.5, 0.5, 0.5, 1))

    def create_line(self, start, end, color):
        """Create a line segment (primitive) to simulate grid lines."""
        lines = LineSegs()
        lines.setColor(*color)
        lines.moveTo(start)
        lines.drawTo(end)
        line_node = lines.create()

        # Convert GeomNode to NodePath
        line_path = NodePath(line_node)
        line_path.reparentTo(self.render)

    def create_box(self, scale, position, color):
        """Create a 3D box (primitive) with a given scale, position, and color."""
        box = self.loader.loadModel("models/misc/rgbCube")  # Built-in box primitive in Panda3D
        box.setScale(scale)
        box.setPos(position)
        box.setColor(color)
        box.reparentTo(self.render)
        return box

    def move_x_rail(self, dx, dy):
        """Move the X-rail in the Y direction based on keyboard input."""
        current_pos = self.x_rail.getPos()
        new_y = current_pos.y + dy

        # Keep the X-rail within the boundaries of the Y axis
        if -20 < new_y < 20:
            self.x_rail.setPos(current_pos.x, new_y, current_pos.z)

            # Track the pen position (drawing on the table)
            if self.pen_down:
                self.track_pen_path()

    def move_tool(self, dx, dy):
        """Move the pen/tool along the X-axis (along the X-rail)."""
        current_pos = self.tool.getPos()
        new_x = current_pos.x + dx

        # Keep the tool within the boundaries of the X axis
        if -5 < new_x < 5:
            self.tool.setPos(new_x, current_pos.y, current_pos.z)

            # Update the pen position (drawing on the table)
            if self.pen_down:
                self.track_pen_path()

    def move_pen_down(self):
        """Move the pen downwards with animation."""
        if self.pen_z_position > -1.5:  # Ensure we don't go too low
            self.animate_pen_position(self.pen_z_position, -0.5)
            self.pen_z_position = -0.5  # Update the current position
            self.pen_down = True
            self.pen_positions.append([])

    def move_pen_up(self):
        """Move the pen upwards with animation."""
        if self.pen_z_position < 1.5:  # Ensure we don't go too high
            self.animate_pen_position(self.pen_z_position, 0.5)
            self.pen_z_position = 0.5  # Update the current position
            self.pen_down = False

    def animate_pen_position(self, start_z, end_z):
        """Animate the pen's movement along the Z-axis."""
        duration = 1.0  # 1 second for the movement

        # Define the pen movement interval using LerpPosInterval
        pen_move_interval = LerpPosInterval(
            self.pen_tip, duration, 
            Vec3(self.pen_tip.getX(), self.pen_tip.getY(), end_z), 
            startPos=Vec3(self.pen_tip.getX(), self.pen_tip.getY(), start_z)
        )

        # Start the interval
        pen_move_interval.start()

    def track_pen_path(self):
        """Track the pen's position and draw a line as the tool moves."""
        current_pen_pos = self.tool.getPos(render) + Vec3(0, 0, -0.5)  # Adjust for the pen's tip position

        # Add the current pen position to the list of tracked positions
        if len(self.pen_positions[-1]) == 0 or (current_pen_pos - self.pen_positions[-1][-1]).length() > 0.05:
            self.pen_positions[-1].append(current_pen_pos)

            # Draw lines representing the pen's path
            self.draw_pen_path()

    def draw_pen_path(self):
        """Render the path drawn by the pen as it moves across the table."""
        if hasattr(self, 'pen_path'):
            self.pen_path.removeNode()  # Remove the previous path

        lines = LineSegs()
        lines.setColor(0, 0, 1, 1)  # Blue color for the pen path
        lines.setThickness(2.0)

        # Draw lines between each pair of positions
        for i in range(len(self.pen_positions)):
            for j in range(len(self.pen_positions[i]) - 1):
                lines.moveTo(self.pen_positions[i][j])
                lines.drawTo(self.pen_positions[i][j + 1])

        # Convert GeomNode to NodePath
        self.pen_path = NodePath(lines.create())
        self.pen_path.reparentTo(self.render)

    def setup_lights(self):
        """Set up basic lighting for the scene."""
        dlight = DirectionalLight("dlight")
        dlight_node = self.render.attachNewNode(dlight)
        dlight_node.setHpr(0, -60, 0)
        self.render.setLight(dlight_node)

        alight = AmbientLight("alight")
        alight.setColor(LVecBase4(0.5, 0.5, 0.5, 1))
        alight_node = self.render.attachNewNode(alight)
        self.render.setLight(alight_node)

# Run the application
app = XYTableApp()
app.run()
