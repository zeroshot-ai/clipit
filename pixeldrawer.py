from DrawingInterface import DrawingInterface

import pydiffvg
import torch
import skimage
import skimage.io
import random
import ttools.modules
import argparse
import math
import torchvision
import torchvision.transforms as transforms
import numpy as np
import PIL.Image
from PIL import ImageFile, Image, PngImagePlugin

pydiffvg.set_print_timing(False)

class PixelDrawer(DrawingInterface):
    num_rows = 45
    num_cols = 45*3
    end_num_rows = 80
    end_num_cols = 80*3
    color_vars = []
    do_mono = False
    pixels = []

    def __init__(self, width, height, do_mono, shape=None):
        super(DrawingInterface, self).__init__()

        self.canvas_width = width
        self.canvas_height = height
        self.do_mono = do_mono
        
        
        if shape is not None:
            self.end_num_rows, self.end_num_cols = shape

    def set_shapes(self, shape=None):
        print("setting shape", shape)
        if shape is not None:
            self.num_rows, self.num_cols = shape
            
    def load_model(self, config_path, checkpoint_path, device):
        # gamma = 1.0

        # Use GPU if available
        pydiffvg.set_use_gpu(torch.cuda.is_available())
        device = torch.device('cuda')
        pydiffvg.set_device(device)

        canvas_width, canvas_height = self.canvas_width, self.canvas_height
        num_rows, num_cols = self.end_num_rows, self.end_num_cols
        cell_width = canvas_width / num_cols
        cell_height = canvas_height / num_rows

        # Initialize Random Pixels
        shapes = []
        shape_groups = []
        colors = []
        for r in range(num_rows):
            cur_y = r * cell_height
            for c in range(num_cols):
                cur_x = c * cell_width
                if self.do_mono:
                    mono_color = random.random()
                    cell_color = torch.tensor([mono_color, mono_color, mono_color, 1.0])
                else:
                    cell_color = torch.tensor([random.random(), random.random(), random.random(), 1.0])
                colors.append(cell_color)
                p0 = [cur_x, cur_y]
                p1 = [cur_x+cell_width, cur_y+cell_height]
                path = pydiffvg.Rect(p_min=torch.tensor(p0), p_max=torch.tensor(p1))
                shapes.append(path)
                path_group = pydiffvg.ShapeGroup(shape_ids = torch.tensor([len(shapes) - 1]), stroke_color = None, fill_color = cell_color)
                shape_groups.append(path_group)

        # Just some diffvg setup
        scene_args = pydiffvg.RenderFunction.serialize_scene(\
            canvas_width, canvas_height, shapes, shape_groups)
        render = pydiffvg.RenderFunction.apply
        img = render(canvas_width, canvas_height, 2, 2, 0, None, *scene_args)

        for group in shape_groups:
            group.fill_color.requires_grad = True
            self.color_vars.append(group.fill_color)

        # Optimizers
        # points_optim = torch.optim.Adam(points_vars, lr=1.0)
        # width_optim = torch.optim.Adam(stroke_width_vars, lr=0.1)
        color_optim = torch.optim.Adam(self.color_vars, lr=0.02)

        self.img = img
        self.shapes = shapes 
        self.shape_groups  = shape_groups
        self.opts = [color_optim]
        
        self.synth(0)
        
        pimg = self.to_image()
        pimg.save("start.png")
        
    def get_opts(self):
        return self.opts

    def rand_init(self, toksX, toksY):
        # TODO
        pass

    def init_from_tensor(self, init_tensor):
        print("init tensor")
        canvas_width, canvas_height = self.canvas_width, self.canvas_height
        num_rows, num_cols = self.end_num_rows, self.end_num_cols
        
        cell_width = canvas_width / num_cols
        cell_height = canvas_height / num_rows

        # Initialize Random Pixels
        shapes = []
        shape_groups = []
        colors = []
        for r in range(num_rows):
            cur_y = r * cell_height
            for c in range(num_cols):
                cur_x = c * cell_width
                if self.do_mono:
                    mono_color = random.random()
                    cell_color = torch.tensor([mono_color, mono_color, mono_color, 1.0])
                else:
                    try:
                        cell_color = torch.tensor([init_tensor[0][0][int(cur_y)][int(cur_x)], init_tensor[0][1][int(cur_y)][int(cur_x)], init_tensor[0][2][int(cur_y)][int(cur_x)], 1])
                    except BaseException as error:
                        mono_color = random.random()
                        cell_color = torch.tensor([mono_color, mono_color, mono_color, 1.0])
                cell_color.requires_grad = True
                self.color_vars.append(cell_color)
                colors.append(cell_color)
                p0 = [cur_x, cur_y]
                p1 = [cur_x+cell_width, cur_y+cell_height]
                path = pydiffvg.Rect(p_min=torch.tensor(p0), p_max=torch.tensor(p1))
                shapes.append(path)
                path_group = pydiffvg.ShapeGroup(shape_ids = torch.tensor([len(shapes) - 1]), stroke_color = None, fill_color = cell_color)
                shape_groups.append(path_group)

        # Just some diffvg setup
        scene_args = pydiffvg.RenderFunction.serialize_scene(\
            canvas_width, canvas_height, shapes, shape_groups)
        render = pydiffvg.RenderFunction.apply
        img = render(canvas_width, canvas_height, 2, 2, 0, None, *scene_args)

        # Optimizers
        # points_optim = torch.optim.Adam(points_vars, lr=1.0)
        # width_optim = torch.optim.Adam(stroke_width_vars, lr=0.1)
        color_optim = torch.optim.Adam(self.color_vars, lr=0.02)
        print("self.color_vars", self.color_vars)
        self.img = img
        self.shapes = shapes
        self.shape_groups  = shape_groups
        self.opts = [color_optim]

        print("from_image_shape", img.shape)

        #self.synth(0)
        #pimg = self.to_image()
        #pimg.save("init.png")
        #self.half_shape()
        print("self.color_vars_half", self.color_vars)

        
    def reapply_from_tensor(self, new_tensor):
        # TODO
        pass
    
    def half_shape(self):
        print("half_shape")
        self.set_shapes((int(self.end_num_rows/2), int(self.end_num_cols/2)))
        
        canvas_width, canvas_height = self.canvas_width, self.canvas_height
        num_rows, num_cols = self.num_rows, self.num_cols

        cell_width = canvas_width / num_cols
        cell_height = canvas_height / num_rows

        # Initialize Random Pixels
        shapes = []
        shape_groups = []
        colors = []
        i = 0
        for r in range(self.num_rows):
            cur_y = r * cell_height
            for c in range(self.num_cols):
                cur_x = c * cell_width
                p0 = [cur_x, cur_y]
                p1 = [cur_x+cell_width, cur_y+cell_height]
                path = pydiffvg.Rect(p_min=torch.tensor(p0), p_max=torch.tensor(p1))
                shapes.append(path)
                self.color_vars[i].requires_grad = True
                path_group = pydiffvg.ShapeGroup(shape_ids = torch.tensor([len(shapes) - 1]), stroke_color = None, fill_color = self.color_vars[i])
                shape_groups.append(path_group)
                i = i+2
            i = i+2

        # Just some diffvg setup
        scene_args = pydiffvg.RenderFunction.serialize_scene(\
            canvas_width, canvas_height, shapes, shape_groups)
        render = pydiffvg.RenderFunction.apply
        img = render(canvas_width, canvas_height, 2, 2, 0, None, *scene_args)

        print("self.color_vars", self.color_vars[0])
        
        self.img = img
        self.shapes = shapes 
        self.shape_groups  = shape_groups
        #self.synth(0)
        print("from_image_shape", img.shape)

        #pimg = self.to_image()
        #pimg.save("scale.png")

    def full_shape(self):
        print("full_shape")
        canvas_width, canvas_height = self.canvas_width, self.canvas_height
        num_rows, num_cols = self.end_num_rows, self.end_num_cols

        cell_width = canvas_width / num_cols
        cell_height = canvas_height / num_rows

        # Initialize Random Pixels
        shapes = []
        shape_groups = []
        colors = []
        i = 0
        for r in range(num_rows):
            cur_y = r * cell_height
            for c in range(num_cols):
                cur_x = c * cell_width
                p0 = [cur_x, cur_y]
                p1 = [cur_x+cell_width, cur_y+cell_height]
                path = pydiffvg.Rect(p_min=torch.tensor(p0), p_max=torch.tensor(p1))
                shapes.append(path)
                self.color_vars[i].requires_grad = True
                path_group = pydiffvg.ShapeGroup(shape_ids = torch.tensor([len(shapes) - 1]), stroke_color = None, fill_color = self.color_vars[i])
                shape_groups.append(path_group)

        # Just some diffvg setup
        scene_args = pydiffvg.RenderFunction.serialize_scene(\
            canvas_width, canvas_height, shapes, shape_groups)
        render = pydiffvg.RenderFunction.apply
        img = render(canvas_width, canvas_height, 2, 2, 0, None, *scene_args)

        self.img = img
        self.shapes = shapes 
        self.shape_groups  = shape_groups

        print("from_image_shape", img.shape)

        #self.synth(0)
        #pimg = self.to_image()
        #pimg.save("scale2.png")

    def get_z_from_tensor(self, ref_tensor):
        return None

    def get_num_resolutions(self):
        # TODO
        return 5

    def synth(self, cur_iteration):
        print("synth")
        render = pydiffvg.RenderFunction.apply
        scene_args = pydiffvg.RenderFunction.serialize_scene(\
            self.canvas_width, self.canvas_height, self.shapes, self.shape_groups)
        img = render(self.canvas_width, self.canvas_height, 2, 2, cur_iteration, None, *scene_args)
        img = img[:, :, 3:4] * img[:, :, :3] + torch.ones(img.shape[0], img.shape[1], 3, device = pydiffvg.get_device()) * (1 - img[:, :, 3:4])
        img = img[:, :, :3]
        img = img.unsqueeze(0)
        img = img.permute(0, 3, 1, 2) # NHWC -> NCHW
        self.img = img
        return img
    
    @torch.no_grad()
    def to_svg(self):
        pydiffvg.save_svg("./output.svg", self.canvas_width, self.canvas_height, self.shapes, self.shape_groups)
        
    @torch.no_grad()
    def to_image(self):
        img = self.img.detach().cpu().numpy()[0]
        print("to_image_shape", img.shape)
        img = np.transpose(img, (1, 2, 0))
        img = np.clip(img, 0, 1)
        img = np.uint8(img * 254)
        # img = np.repeat(img, 4, axis=0)
        # img = np.repeat(img, 4, axis=1)
        pimg = PIL.Image.fromarray(img, mode="RGB")
        return pimg

    def clip_z(self):
        print("self.color_varsz1", self.color_vars[0])
        with torch.no_grad():
            for group in self.shape_groups:
                group.fill_color.data[:3].clamp_(0.0, 1.0)
                group.fill_color.data[3].clamp_(1.0, 1.0)
                if self.do_mono:
                    avg_amount = torch.mean(group.fill_color.data[:3])
                    group.fill_color.data[:3] = avg_amount
        print("self.color_varsz2", self.color_vars[0])
                

    def get_z(self):
        return None

    def get_z_copy(self):
        return None
