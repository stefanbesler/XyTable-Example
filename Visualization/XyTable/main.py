import pyads
import math
import numpy as np
from PIL import Image

from panda3d.core import Vec3, LVecBase4
from panda3d.core import GeomNode, VBase4, LVecBase4f
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import LineSegs
from panda3d.core import AntialiasAttrib
from panda3d.core import CardMaker
from panda3d.core import Texture, TransparencyAttrib
from panda3d.core import PNMImage
from panda3d.core import NodePath
from panda3d.core import WindowProperties

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.interval.IntervalGlobal import LerpPosInterval

class XYTableApp(ShowBase):
    def __init__(self):
        super().__init__()
        
        # Connect to PLC
        pyads.ads.open_port()
        netid = pyads.ads.get_local_address().netid
        pyads.ads.close_port()
        self.plc = pyads.Connection("127.0.0.1.1.1", 851)
        self.plc.open()
        
        self.setBackgroundColor(71./255., 91./255., 120./255., 1)

        # Disable default camera movement
        self.disableMouse()

        # Set the camera position and orientation (top-down view)
        self.camera.setPos(15, -15, 15)
        self.camera.lookAt(0, 0, 0)

        self.create_grid()
        self.y_rail = self.create_box(scale=(0.5, 32, 0.5), position=(-4.5, 0, 0), color=(42./255., 51./255., 75./255., 1))
        self.x_rail = self.create_box(scale=(20, 0.4, 0.4), position=(5, 10, 0), color=(42./255., 51./255., 75./255., 1))
        self.tool = self.create_box(scale=(0.5, 0.5, 0.5), position=(0, 0, 0), color=(218./255., 119./255., 109./255., 1))
        self.pen_tip = self.create_box(scale=(0.1, 0.1, 3.1), position=(0, 0, 0.5), color=(245./255., 241./255., 238./255., 1))
        self.pen_tip.reparentTo(self.tool)
        self.pen_down = False
        
        self.texture = self.create_texture()        
        
        self.updateTask = taskMgr.add(self.update, "update")

        self.pen_positions = []
        self.setup_lights()
        self.pen_z_position = 0.5

    def create_grid(self):
        
        def create_line(start, end, color):
            lines = LineSegs()
            lines.setThickness(0.1)
            lines.setColor(*color)
            lines.moveTo(start)
            lines.drawTo(end)
            line_node = lines.create()

            # Convert GeomNode to NodePath
            line_path = NodePath(line_node)
            line_path.reparentTo(self.render)
        
        grid_size = 20
        step = 1
        for x in range(-grid_size, grid_size + 1, step):
            create_line(start=Vec3(x, -grid_size, -2), end=Vec3(x, grid_size, -2), color=(202./255., 208./255., 222./255., 1))
        for y in range(-grid_size, grid_size + 1, step):
            create_line(start=Vec3(-grid_size, y, -2), end=Vec3(grid_size, y, -2), color=(202./255., 208./255., 222./255., 1))


    def create_box(self, scale, position, color):
        """Create a 3D box (primitive) with a given scale, position, and color."""
        box = self.loader.loadModel("models/misc/rgbCube")  # Built-in box primitive in Panda3D
        box.setScale(scale)
        box.setPos(position)
        box.setColor(color)
        box.reparentTo(self.render)
        return box
    
    def update(self, task):
        dt = globalClock.getDt()
        
        move_up = self.plc.read_by_name(f"ZGlobal.Com.Unit.XyTable.Publish.Equipment.PenUp.Enabled", pyads.PLCTYPE_BOOL)
        move_down = self.plc.read_by_name(f"ZGlobal.Com.Unit.XyTable.Publish.Equipment.PenDown.Enabled", pyads.PLCTYPE_BOOL)
        pen_down = self.plc.read_by_name(f"ZGlobal.Com.Unit.XyTable.Publish.Equipment.PenIsDown.Enabled", pyads.PLCTYPE_BOOL)
        
        if move_up:
            self.move_pen_up(dt)
        elif move_down:
            self.move_pen_down(dt)
            
        if pen_down and not self.pen_down:
            self.pen_positions.append([])
            
        self.pen_down = pen_down
        
        if pen_down:
            self.track_pen_path()

        x = (self.plc.read_by_name(f"ZGlobal.Com.Unit.XyTable.Publish.Equipment.AxisX.Base.ActualPosition", pyads.PLCTYPE_LREAL) - 70) / 10
        y = (self.plc.read_by_name(f"ZGlobal.Com.Unit.XyTable.Publish.Equipment.AxisY.Base.ActualPosition", pyads.PLCTYPE_LREAL)- 40) / 10
        self.move_rail(x)
        self.move_tool(y, x)
        
        return task.cont
    
    def move_rail(self, y):
        """Move the X-rail in the Y direction based on keyboard input."""
        
        current_pos = self.x_rail.getPos()
        self.x_rail.setPos(current_pos.x, y, current_pos.z)

    def move_tool(self, x, y):
        """Move the pen/tool along the X-axis (along the X-rail)."""
        
        current_pos = self.tool.getPos()
        self.tool.setPos(x, y, current_pos.z)


    def move_pen_down(self, dt):
        """Move the pen downwards with animation."""

        if self.pen_z_position > -0.75:  # Ensure we don't go too low
            self.animate_pen_position(self.pen_z_position, -0.75)
            self.pen_z_position = -0.75  # Update the current position


    def move_pen_up(self, dt):
        """Move the pen upwards with animation."""

        if self.pen_z_position < 0.75:  # Ensure we don't go too low
            self.animate_pen_position(self.pen_z_position, 0.75)
            self.pen_z_position = 0.75  # Update the current position

            
    def animate_pen_position(self, start_z, end_z):
        """Animate the pen's movement along the Z-axis."""
        duration = 0.5  # 1 second for the movement

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
        current_pen_pos = self.pen_tip.getPos(render) + Vec3(0, 0, -0.5)  # Adjust for the pen's tip position

        # Add the current pen position to the list of tracked positions
        if len(self.pen_positions[-1]) == 0 or (current_pen_pos - self.pen_positions[-1][-1]).length() > 1e-19:
            self.pen_positions[-1].append(current_pen_pos)

            # Draw lines representing the pen's path
            self.draw_pen_path()



    def create_texture(self, size = 64, radius=32):
        """Create a circular Gaussian texture."""
        
        pnm_image = PNMImage(size, size, 4)  # width, height, and 4 channels (RGBA)
        center = size // 2

        for i in range(size):
            for j in range(size):
                pnm_image.setXelA(j, i, 0)
                
        for i in range(size):
            for j in range(size):
                distance = np.sqrt((i - center) ** 2 + (j - center) ** 2)

                if distance <= radius:
                    pnm_image.setXel(j, i, 1, 1, 1)
                    pnm_image.setXelA(j, i, 1)
                
        pnm_image.write("test1.png")             

        img_texture = Texture("GaussianTexture")
        img_texture.load(pnm_image)
        
        img_texture.setMinfilter(Texture.FT_linear)
        img_texture.setMagfilter(Texture.FT_linear)
        img_texture.setWrapU(Texture.WM_clamp)
        img_texture.setWrapV(Texture.WM_clamp)        
        
        return img_texture

    def draw_pen_path(self):
        """Render the path drawn by the pen using cards for better visibility."""
        if hasattr(self, 'pen_path'):
            self.pen_path.removeNode()  # Remove the previous path

        # Create a new NodePath to store the pen path
        self.pen_path = NodePath("pen_path")
        self.pen_path.reparentTo(self.render)

        for i in range(len(self.pen_positions)):
            for j in range(len(self.pen_positions[i]) - 1):
                # Get start and end positions for each segment
                start_pos = self.pen_positions[i][j]
                end_pos = self.pen_positions[i][j + 1]
                
                card_maker = CardMaker('pen_segment_1')
                card_maker.setFrame(-0.1, 0.1, -0.1, 0.1)
                card = self.pen_path.attachNewNode(card_maker.generate())
                card.lookAt(Vec3(0, 0, -1))
                card.setPos(start_pos)
                card.setTexture(self.texture)
                card.setColor(218./255., 119./255., 109./255., 1)  # Pen path color
                            

    def setup_lights(self):
        """Set up basic lighting for the scene."""
        dlight = DirectionalLight("dlight")
        dlight_node = self.render.attachNewNode(dlight)
        dlight_node.setHpr(0, -60, 0)
        self.render.setLight(dlight_node)
        self.render.setAntialias(AntialiasAttrib.MLine)

        alight = AmbientLight("alight")
        alight.setColor(LVecBase4(0, 0, 0, 1))
        alight_node = self.render.attachNewNode(alight)
        self.render.setLight(alight_node)      

# Run the application
app = XYTableApp()
app.run()
