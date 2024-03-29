# based on pyldd2obj by jonnysp and lxfml import plugin by sttng
# modified by aronwk-aaron to work better with LU-Toolbox
import bpy, bmesh
import mathutils
from bpy_extras.io_utils import (
    ImportHelper,
    axis_conversion,
)

import os
import sys
import math
import time
import struct
import zipfile
from xml.dom import minidom
import uuid
import random
import numpy as np

from .materials import (
    MATERIALS_OPAQUE,
    MATERIALS_TRANSPARENT,
    MATERIALS_METALLIC,
    MATERIALS_GLOW
)

from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator, AddonPreferences


class ImportLDDPreferences(AddonPreferences):
    bl_idname = __package__
    brickdbpath: StringProperty(
        name="Brick DB",
        subtype='FILE_PATH'
    )

    def draw(self, context):
        self.layout.label(text="Path to Brick DB (or luclient/res/)")
        self.layout.prop(self, "brickdbpath")


class ImportLDDOps(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_description = "Import LEGO Digital Designer scenes (.lxf/.lxfml)"
    bl_idname = "import_scene.importldd"
    bl_label = "Import LDD scene"

    # ImportHelper mixin class uses this
    filename_ext = ".lxf"

    filter_glob: StringProperty(
        default="*.lxf;*.lxfml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    importLOD0: BoolProperty(
        name="LOD0",
        description="Import LOD0",
        default=True,
    )

    importLOD1: BoolProperty(
        name="LOD1",
        description="Import LOD1",
        default=False,
    )

    importLOD2: BoolProperty(
        name="LOD2",
        description="Import LOD2",
        default=True,
    )

    importLOD3: BoolProperty(
        name="LOD3",
        description="Import LOD3",
        default=True,
    )

    overwriteScene: BoolProperty(
        name="Overwrite Scene",
        description="Delete all objects and collections from Blender scene before importing.",
        default=True,
    )

    useNormals: BoolProperty(
        name="Use Normals",
        description="Use normals when importing geometry",
        default=True,
    )

    def execute(self, context):
        return convertldd_data(
            self,
            context,
            self.filepath,
            self.importLOD0,
            self.importLOD1,
            self.importLOD2,
            self.importLOD3,
            self.overwriteScene,
            self.useNormals
        )


def register():
    bpy.utils.register_class(ImportLDDOps)
    bpy.utils.register_class(ImportLDDPreferences)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportLDDOps)
    bpy.utils.unregister_class(ImportLDDPreferences)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportLDDOps.bl_idname, text="LEGO Exchange Format (.lxf/.lxfml)")


def convertldd_data(self, context, filepath, importLOD0, importLOD1, importLOD2, importLOD3, overwriteScene, useNormals):

    preferences = context.preferences
    addon_prefs = preferences.addons[__package__].preferences
    brickdbpath = addon_prefs.brickdbpath

    primaryBrickDBPath = None

    if brickdbpath:
        primaryBrickDBPath = brickdbpath
    else:
        self.report({'ERROR'}, 'ERROR: Please define a Brick DB Path in the Addon Preferences')
        return {'FINISHED'}

    converter = Converter()

    if os.path.isdir(primaryBrickDBPath):
        self.report({'INFO'}, 'Found DB folder.')
        start = time.process_time()
        setDBFolderVars(dbfolderlocation=primaryBrickDBPath)
        converter.LoadDBFolder(dbfolderlocation=primaryBrickDBPath)
        end = time.process_time()
        self.report({'INFO'}, f'Time taken to load Brick DB: {end - start} seconds')

    try:
        if overwriteScene:
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)

            bpy.ops.outliner.orphans_purge()

            for c in context.scene.collection.children:
                context.scene.collection.children.unlink(c)

        converter.LoadScene(filename=filepath)
        col = bpy.data.collections.new(converter.scene.Name)
        bpy.context.scene.collection.children.link(col)

        if importLOD0:
            start = time.process_time()
            converter.Export(
                filename=filepath,
                lod='0',
                parent_collection=col,
                useNormals=useNormals
            )
            end = time.process_time()
            self.report({'INFO'}, f'Time taken to Load LOD0: {end - start} seconds')
        if importLOD1:
            start = time.process_time()
            converter.Export(
                filename=filepath,
                lod='1',
                parent_collection=col,
                useNormals=useNormals
            )
            end = time.process_time()
            self.report({'INFO'}, f'Time taken to Load LOD1: {end - start} seconds')
        if importLOD2:
            start = time.process_time()
            converter.Export(
                filename=filepath,
                lod='2',
                parent_collection=col,
                useNormals=useNormals
            )
            end = time.process_time()
            self.report({'INFO'}, f'Time taken to Load LOD2: {end - start} seconds')
        LOD3_exists = False
        if importLOD3:
            for dirpath, dirnames, filenames in os.walk(primaryBrickDBPath):
                for dirname in dirnames:
                    if dirname == "lod3":
                        LOD3_exists = True
            if LOD3_exists:
                start = time.process_time()
                converter.Export(
                    filename=filepath,
                    lod='3',
                    parent_collection=col,
                    useNormals=useNormals
                )
                end = time.process_time()
                self.report({'INFO'}, f'Time taken to Load LOD3: {end - start} seconds')
            else:
                self.report({'INFO'}, f'LOD3 does not exist, skipping')
    except Exception as e:
        self.report({'ERROR'}, str(e))

    return {'FINISHED'}


PRIMITIVEPATH = '/Primitives/'
GEOMETRIEPATH = PRIMITIVEPATH + 'LOD0/'


class Matrix3D:
    def __init__(
            self,
            n11=1, n12=0, n13=0, n14=0,
            n21=0, n22=1, n23=0, n24=0,
            n31=0, n32=0, n33=1, n34=0,
            n41=0, n42=0, n43=0, n44=1):
        self.n11 = n11
        self.n12 = n12
        self.n13 = n13
        self.n14 = n14
        self.n21 = n21
        self.n22 = n22
        self.n23 = n23
        self.n24 = n24
        self.n31 = n31
        self.n32 = n32
        self.n33 = n33
        self.n34 = n34
        self.n41 = n41
        self.n42 = n42
        self.n43 = n43
        self.n44 = n44

    def __str__(self):
        return f"[{self.n11}, {self.n12}, {self.n13}, {self.n14}, \
            {self.n21}, {self.n22}, {self.n23}, {self.n24}, \
            {self.n31}, {self.n32}, {self.n33}, {self.n34}, \
            {self.n41}, {self.n42}, {self.n43}, {self.n44}]"

    def rotate(self, angle=0, axis=0):
        c = math.cos(angle)
        s = math.sin(angle)
        t = 1 - c

        tx = t * axis.x
        ty = t * axis.y
        tz = t * axis.z

        sx = s * axis.x
        sy = s * axis.y
        sz = s * axis.z

        self.n11 = c + axis.x * tx
        self.n12 = axis.y * tx + sz
        self.n13 = axis.z * tx - sy
        self.n14 = 0

        self.n21 = axis.x * ty - sz
        self.n22 = c + axis.y * ty
        self.n23 = axis.z * ty + sx
        self.n24 = 0

        self.n31 = axis.x * tz + sy
        self.n32 = axis.y * tz - sx
        self.n33 = c + axis.z * tz
        self.n34 = 0

        self.n41 = 0
        self.n42 = 0
        self.n43 = 0
        self.n44 = 1

    def __mul__(self, other):
        return Matrix3D(
            self.n11 * other.n11 + self.n21 * other.n12 + self.n31 * other.n13 + self.n41 * other.n14,
            self.n12 * other.n11 + self.n22 * other.n12 + self.n32 * other.n13 + self.n42 * other.n14,
            self.n13 * other.n11 + self.n23 * other.n12 + self.n33 * other.n13 + self.n43 * other.n14,
            self.n14 * other.n11 + self.n24 * other.n12 + self.n34 * other.n13 + self.n44 * other.n14,
            self.n11 * other.n21 + self.n21 * other.n22 + self.n31 * other.n23 + self.n41 * other.n24,
            self.n12 * other.n21 + self.n22 * other.n22 + self.n32 * other.n23 + self.n42 * other.n24,
            self.n13 * other.n21 + self.n23 * other.n22 + self.n33 * other.n23 + self.n43 * other.n24,
            self.n14 * other.n21 + self.n24 * other.n22 + self.n34 * other.n23 + self.n44 * other.n24,
            self.n11 * other.n31 + self.n21 * other.n32 + self.n31 * other.n33 + self.n41 * other.n34,
            self.n12 * other.n31 + self.n22 * other.n32 + self.n32 * other.n33 + self.n42 * other.n34,
            self.n13 * other.n31 + self.n23 * other.n32 + self.n33 * other.n33 + self.n43 * other.n34,
            self.n14 * other.n31 + self.n24 * other.n32 + self.n34 * other.n33 + self.n44 * other.n34,
            self.n11 * other.n41 + self.n21 * other.n42 + self.n31 * other.n43 + self.n41 * other.n44,
            self.n12 * other.n41 + self.n22 * other.n42 + self.n32 * other.n43 + self.n42 * other.n44,
            self.n13 * other.n41 + self.n23 * other.n42 + self.n33 * other.n43 + self.n43 * other.n44,
            self.n14 * other.n41 + self.n24 * other.n42 + self.n34 * other.n43 + self.n44 * other.n44
        )


class Point3D:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return '[{0},{1},{2}]'.format(self.x, self.y, self.z)

    def string(self, prefix="v"):
        return '{0} {1:f} {2:f} {3:f}\n'.format(prefix, self.x, self.y, self.z)

    def transformW(self, matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z
        self.x = x
        self.y = y
        self.z = z

    def transform(self, matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z + matrix.n41
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z + matrix.n42
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z + matrix.n43
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Point3D(x=self.x, y=self.y, z=self.z)


class Point2D:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __str__(self):
        return '[{0},{1}]'.format(self.x, self.y * -1)

    def string(self, prefix="t"):
        return '{0} {1:f} {2:f}\n'.format(prefix, self.x, self.y * -1)

    def copy(self):
        return Point2D(x=self.x, y=self.y)


class Face:
    def __init__(self, a=0, b=0, c=0):
        self.a = a
        self.b = b
        self.c = c

    def string(self, prefix="f", indexOffset=0, textureoffset=0):
        if textureoffset == 0:
            return prefix + ' {0}//{0} {1}//{1} {2}//{2}\n'.format(
                self.a + indexOffset,
                self.b + indexOffset,
                self.c + indexOffset
            )
        else:
            return prefix + ' {0}/{3}/{0} {1}/{4}/{1} {2}/{5}/{2}\n'.format(
                self.a + indexOffset,
                self.b + indexOffset,
                self.c + indexOffset,
                self.a + textureoffset,
                self.b + textureoffset,
                self.c + textureoffset
            )

    def __str__(self):
        return '[{0},{1},{2}]'.format(self.a, self.b, self.c)


class Group:
    def __init__(self, node):
        self.partRefs = node.getAttribute('partRefs').split(',')


class Bone:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        if node.hasAttribute('transformation'):
            (a, b, c, d, e, f, g, h, i, x, y, z) = map(float, node.getAttribute('transformation').split(','))
            self.matrix = Matrix3D(
                n11=a, n12=b, n13=c, n14=0,
                n21=d, n22=e, n23=f, n24=0,
                n31=g, n32=h, n33=i, n34=0,
                n41=x, n42=y, n43=z, n44=1
            )
        elif node.hasAttribute('angle'):
            # raise Exception("Cannot Properly import Old LDD Save formats")
            rotationMatrix = Matrix3D()
            rotationMatrix.rotate(
                angle=float(node.getAttribute('angle')) * math.pi / 180.0,
                axis=Point3D(
                    x=float(node.getAttribute('ax')),
                    y=float(node.getAttribute('ay')),
                    z=float(node.getAttribute('az'))
                )
            )
            p = Point3D(
                x=float(node.getAttribute('tx')),
                y=float(node.getAttribute('ty')),
                z=float(node.getAttribute('tz'))
            )
            p.transformW(rotationMatrix)
            rotationMatrix.n41 = p.x
            rotationMatrix.n42 = p.y
            rotationMatrix.n43 = p.z
            self.matrix = rotationMatrix
        else:
            raise Exception(f"Bone/Part {self.refID} transformation not supported")


class Part:
    def __init__(self, node):
        self.isGrouped = False
        self.GroupIDX = 0
        self.Bones = []
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        if node.hasAttribute('materials'):
            self.materials = list(map(str, node.getAttribute('materials').split(',')))
            for childnode in node.childNodes:
                if childnode.nodeName == 'Bone':
                    self.Bones.append(Bone(node=childnode))
            for i, m in enumerate(self.materials):
                if (m == '0'):
                    # self.materials[i] = lastm
                    self.materials[i] = self.materials[0]  # in case of 0 choose the 'base' material
        elif node.hasAttribute('materialID'):
            self.materials = [str(node.getAttribute('materialID'))]
            self.Bones.append(Bone(node=node))
        else:
            raise Exception("Not valid Part")


class Brick:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        self.Parts = []
        for childnode in node.childNodes:
            if childnode.nodeName == 'Part':
                self.Parts.append(Part(node=childnode))


class Scene:
    def __init__(self, file):
        self.Bricks = []
        self.Groups = []
        self.Version = "Unknown"
        self.Name = "Unknown"

        if file.endswith('.lxfml'):
            with open(file, "rb") as file:
                data = file.read()
        elif file.endswith('.lxf'):
            zf = zipfile.ZipFile(file, 'r')
            data = zf.read('IMAGE100.LXFML')
        else:
            return

        xml = minidom.parseString(data)
        try:
            self.Name = xml.firstChild.getAttribute('name')
        except Exception as e:
            print(f"ERROR: {e}")
        for node in xml.firstChild.childNodes:
            if node.nodeName == 'Meta':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'BrickSet':
                        try:
                            self.Version = str(childnode.getAttribute('version'))
                        except Exception as e:
                            print(f"ERROR: {e}")
            elif node.nodeName == 'Bricks':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Brick':
                        self.Bricks.append(Brick(node=childnode))
            elif node.nodeName == 'Scene':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Model':
                        for childnode2 in childnode.childNodes:
                            if childnode2.nodeName == 'Group':
                                self.Bricks.append(Brick(node=childnode2))
            elif node.nodeName == 'GroupSystems':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'GroupSystem':
                        for childnode in childnode.childNodes:
                            if childnode.nodeName == 'Group':
                                self.Groups.append(Group(node=childnode))

        for i in range(len(self.Groups)):
            for brick in self.Bricks:
                for part in brick.Parts:
                    if part.refID in self.Groups[i].partRefs:
                        part.isGrouped = True
                        part.GroupIDX = i


class GeometryReader:
    def __init__(self, data):
        self.offset = 0
        self.data = data
        self.positions = []
        self.normals = []
        self.textures = []
        self.faces = []
        self.bonemap = {}
        self.texCount = 0
        self.outpositions = []
        self.outnormals = []

        if self.readInt() == 1111961649:
            self.valueCount = self.readInt()
            self.indexCount = self.readInt()
            self.faceCount = int(self.indexCount / 3)
            options = self.readInt()

            for i in range(0, self.valueCount):
                self.positions.append(
                    Point3D(x=self.readFloat(), y=self.readFloat(), z=self.readFloat())
                )

            for i in range(0, self.valueCount):
                self.normals.append(
                    Point3D(x=self.readFloat(), y=self.readFloat(), z=self.readFloat())
                )

            if (options & 3) == 3:
                self.texCount = self.valueCount
                for i in range(0, self.valueCount):
                    self.textures.append(Point2D(x=self.readFloat(), y=self.readFloat()))

            for i in range(0, self.faceCount):
                self.faces.append(Face(a=self.readInt(), b=self.readInt(), c=self.readInt()))

            if (options & 48) == 48:
                num = self.readInt()
                self.offset += (num * 4) + (self.indexCount * 4)
                num = self.readInt()
                self.offset += (3 * num * 4) + (self.indexCount * 4)

            bonelength = self.readInt()
            self.bonemap = [0] * self.valueCount

            if (bonelength > self.valueCount) or (bonelength > self.faceCount):
                datastart = self.offset
                self.offset += bonelength
                for i in range(0, self.valueCount):
                    boneoffset = self.readInt() + 4
                    self.bonemap[i] = self.read_Int(datastart + boneoffset)

    def read_Int(self, _offset):
        if sys.version_info < (3, 0):
            return int(struct.unpack_from('i', self.data, _offset)[0])
        else:
            return int.from_bytes(self.data[_offset:_offset + 4], byteorder='little')

    def readInt(self):
        if sys.version_info < (3, 0):
            ret = int(struct.unpack_from('i', self.data, self.offset)[0])
        else:
            ret = int.from_bytes(self.data[self.offset:self.offset + 4], byteorder='little')
        self.offset += 4
        return ret

    def readFloat(self):
        ret = float(struct.unpack_from('f', self.data, self.offset)[0])
        self.offset += 4
        return ret


class Geometry:
    def __init__(self, designID, database, lod):
        self.designID = designID
        self.Parts = {}
        self.maxGeoBounding = -1

        if lod is None:
            geompath = GEOMETRIEPATH
        else:
            geompath = os.path.join(database.location, 'brickprimitives', 'lod' + lod + '/')

        GeometryLocation = os.path.normpath('{0}{1}{2}'.format(geompath, designID, '.g'))
        GeometryCount = 0
        while str(GeometryLocation) in database.filelist:
            self.Parts[GeometryCount] = GeometryReader(data=database.filelist[GeometryLocation].read())
            GeometryCount += 1
            GeometryLocation = os.path.normpath(f'{geompath}{designID}.g{GeometryCount}')

        primitive = Primitive(data=database.filelist[os.path.normpath(PRIMITIVEPATH + designID + '.xml')].read())
        self.Partname = primitive.Designname
        try:
            geoBoundingList = [
                abs(float(primitive.Bounding['minX']) - float(primitive.Bounding['maxX'])),
                abs(float(primitive.Bounding['minY']) - float(primitive.Bounding['maxY'])),
                abs(float(primitive.Bounding['minZ']) - float(primitive.Bounding['maxZ']))
            ]
            geoBoundingList.sort()
            self.maxGeoBounding = geoBoundingList[-1]
        except KeyError as e:
            print(f'\nBounding errror in part {designID}: {e}\n')

        # preflex
        for part in self.Parts:
            # transform
            for i, b in enumerate(primitive.Bones):
                # positions
                for j, p in enumerate(self.Parts[part].positions):
                    if (self.Parts[part].bonemap[j] == i):
                        self.Parts[part].positions[j].transform(b.matrix)
                # normals
                for k, n in enumerate(self.Parts[part].normals):
                    if (self.Parts[part].bonemap[k] == i):
                        self.Parts[part].normals[k].transformW(b.matrix)

    def valuecount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].valueCount
        return count

    def facecount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].faceCount
        return count

    def texcount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].texCount
        return count


class Bone2:
    def __init__(self, boneId=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        self.boneId = boneId
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(
            angle=(-angle * math.pi / 180.0),
            axis=Point3D(x=ax, y=ay, z=az)
        )
        p = Point3D(x=tx, y=ty, z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z
        self.matrix = rotationMatrix


class Field2D:
    def __init__(self, type=0, width=0, height=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0, field2DRawData='none'):
        self.type = type
        self.field2DRawData = field2DRawData
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(
            angle=(-angle * math.pi / 180.0),
            axis=Point3D(x=ax, y=ay, z=az)
        )
        p = Point3D(x=tx, y=ty, z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z

        self.matrix = rotationMatrix
        self.custom2DField = []

        # The height and width are always double the number of studs.
        # The contained text is a 2D array that is always height + 1 and width + 1.
        rows_count = height + 1
        cols_count = width + 1
        # creation looks reverse
        # create an array of "cols_count" cols, for each of the "rows_count" rows
        # all elements are initialized to 0
        self.custom2DField = [[0 for j in range(cols_count)] for i in range(rows_count)]
        custom2DFieldString = field2DRawData.replace('\r', '').replace('\n', '').replace(' ', '')
        custom2DFieldArr = custom2DFieldString.strip().split(',')

        k = 0
        for i in range(rows_count):
            for j in range(cols_count):
                self.custom2DField[i][j] = custom2DFieldArr[k]
                k += 1

    def __str__(self):
        return f'[type="{self.type}" transform="{self.matrix}" custom2DField="{self.custom2DField}"]'


class CollisionBox:
    def __init__(self, sX=0, sY=0, sZ=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(
            angle=(-angle * math.pi / 180.0),
            axis=Point3D(x=ax, y=ay, z=az)
        )
        p = Point3D(x=tx, y=ty, z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z

        self.matrix = rotationMatrix
        self.corner = Point3D(x=sX, y=sY, z=sZ)
        self.positions = []

        self.positions.append(Point3D(x=0, y=0, z=0))
        self.positions.append(Point3D(x=sX, y=0, z=0))
        self.positions.append(Point3D(x=0, y=sY, z=0))
        self.positions.append(Point3D(x=sX, y=sY, z=0))
        self.positions.append(Point3D(x=0, y=0, z=sZ))
        self.positions.append(Point3D(x=0, y=sY, z=sZ))
        self.positions.append(Point3D(x=sX, y=0, z=sZ))
        self.positions.append(Point3D(x=sX, y=sY, z=sZ))

    def __str__(self):
        return f'[0,0,0] \
            [{self.corner.x},0,0] \
            [0,{self.corner.y},0] \
            [{self.corner.x},{self.corner.y},0] \
            [0,0,{self.corner.z}] \
            [0,{self.corner.y},{self.corner.z}] \
            [{self.corner.x},0,{2}] \
            [{self.corner.x},{1},{2}]'


class Primitive:
    def __init__(self, data):
        self.Designname = ''
        self.Bones = []
        self.Fields2D = []
        self.CollisionBoxes = []
        self.PhysicsAttributes = {}
        self.Bounding = {}
        self.GeometryBounding = {}

        xml = minidom.parseString(data)
        root = xml.documentElement

        for node in root.childNodes:
            if node.__class__.__name__.lower() == 'comment':
                self.comment = node[0].nodeValue
            if node.nodeName == 'Flex':
                for node in node.childNodes:
                    if node.nodeName == 'Bone':
                        self.Bones.append(
                            Bone2(
                                boneId=int(node.getAttribute('boneId')),
                                angle=float(node.getAttribute('angle')),
                                ax=float(node.getAttribute('ax')),
                                ay=float(node.getAttribute('ay')),
                                az=float(node.getAttribute('az')),
                                tx=float(node.getAttribute('tx')),
                                ty=float(node.getAttribute('ty')),
                                tz=float(node.getAttribute('tz'))
                            )
                        )
            elif node.nodeName == 'Annotations':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Annotation' and childnode.hasAttribute('designname'):
                        self.Designname = childnode.getAttribute('designname')
            elif node.nodeName == 'Collision':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Box':
                        self.CollisionBoxes.append(
                            CollisionBox(
                                sX=float(childnode.getAttribute('sX')),
                                sY=float(childnode.getAttribute('sY')),
                                sZ=float(childnode.getAttribute('sZ')),
                                angle=float(childnode.getAttribute('angle')),
                                ax=float(childnode.getAttribute('ax')),
                                ay=float(childnode.getAttribute('ay')),
                                az=float(childnode.getAttribute('az')),
                                tx=float(childnode.getAttribute('tx')),
                                ty=float(childnode.getAttribute('ty')),
                                tz=float(childnode.getAttribute('tz'))
                            )
                        )
            elif node.nodeName == 'PhysicsAttributes':
                self.PhysicsAttributes = {
                    "inertiaTensor": node.getAttribute('inertiaTensor'),
                    "centerOfMass": node.getAttribute('centerOfMass'),
                    "mass": node.getAttribute('mass'),
                    "frictionType": node.getAttribute('frictionType')
                }
            elif node.nodeName == 'Bounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.Bounding = {
                            "minX": childnode.getAttribute('minX'),
                            "minY": childnode.getAttribute('minY'),
                            "minZ": childnode.getAttribute('minZ'),
                            "maxX": childnode.getAttribute('maxX'),
                            "maxY": childnode.getAttribute('maxY'),
                            "maxZ": childnode.getAttribute('maxZ')
                        }
            elif node.nodeName == 'GeometryBounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.GeometryBounding = {
                            "minX": childnode.getAttribute('minX'),
                            "minY": childnode.getAttribute('minY'),
                            "minZ": childnode.getAttribute('minZ'),
                            "maxX": childnode.getAttribute('maxX'),
                            "maxY": childnode.getAttribute('maxY'),
                            "maxZ": childnode.getAttribute('maxZ')
                        }
            elif node.nodeName == 'Connectivity':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Custom2DField':
                        self.Fields2D.append(
                            Field2D(
                                type=int(childnode.getAttribute('type')),
                                width=int(childnode.getAttribute('width')),
                                height=int(childnode.getAttribute('height')),
                                angle=float(childnode.getAttribute('angle')),
                                ax=float(childnode.getAttribute('ax')),
                                ay=float(childnode.getAttribute('ay')),
                                az=float(childnode.getAttribute('az')),
                                tx=float(childnode.getAttribute('tx')),
                                ty=float(childnode.getAttribute('ty')),
                                tz=float(childnode.getAttribute('tz')),
                                field2DRawData=str(childnode.firstChild.data)
                            )
                        )


class Materials:
    def __init__(self):
        self.MaterialsRi = {}
        self.loadColors(MATERIALS_OPAQUE, "shinyPlastic")
        self.loadColors(MATERIALS_TRANSPARENT, "Transparent")
        self.loadColors(MATERIALS_METALLIC, "Metallic")
        self.loadColors(MATERIALS_GLOW, "Glow")

    def loadColors(self, data, materialType):
        for color in data:
            if color not in self.MaterialsRi:
                self.MaterialsRi[color] = MaterialRi(
                    materialId=color,
                    r=data[color][0],
                    g=data[color][1],
                    b=data[color][2],
                    a=data[color][3],
                    materialType=materialType
                )

    def getMaterialRibyId(self, mid):
        if mid in self.MaterialsRi:
            return self.MaterialsRi[mid]
        else:
            print(f"Material {mid} does not exist")
            return self.MaterialsRi["26"]


class MaterialRi:
    def __init__(self, materialId, r, g, b, a, materialType):
        self.materialType = materialType
        self.materialId = materialId
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def string(self, decorationId):

        matId_or_decId = self.materialId

        material = bpy.data.materials.new(matId_or_decId)
        material.diffuse_color = (self.r, self.g, self.b, self.a)

        return material


class DBFolderFile:
    def __init__(self, name, handle):
        self.handle = handle
        self.name = name

    def read(self):
        reader = open(self.handle, "rb")
        try:
            filecontent = reader.read()
            reader.close()
            return filecontent
        finally:
            reader.close()


class DBFolderReader:
    def __init__(self, folder):
        self.filelist = {}
        self.initok = False
        self.location = folder

        try:
            os.path.isdir(self.location)
        except Exception:
            self.initok = False
            print("db folder read FAIL")
            return
        else:
            self.parse()
            if len(self.filelist) > 1:
                print("DB folder OK.")
                self.initok = True
            else:
                raise Exception("DB folder ERROR")

    def fileexist(self, filename):
        return filename in self.filelist

    def parse(self):
        if not os.path.exists(os.path.join(self.location, "Assemblies")) and \
                os.path.exists(os.path.join(self.location, "brickdb.zip")):
            print("Found brickdb.zip without uzipped files")
            with zipfile.ZipFile(os.path.join(self.location, "brickdb.zip"), 'r') as zip_ref:
                print("Extracting brickdb.zip")
                zip_ref.extractall(self.location)
        extentions = ('.g', '.g1', '.g2', '.g3', '.g4', '.xml')
        for path, subdirs, files in os.walk(self.location):
            files = filter(lambda file: file.endswith(extentions), files)
            for name in files:
                entryName = os.path.join(path, name)
                self.filelist[entryName] = DBFolderFile(name=entryName, handle=entryName)


class Converter:

    def LoadDBFolder(self, dbfolderlocation):
        self.database = DBFolderReader(folder=dbfolderlocation)

        if self.database.initok:
            self.allMaterials = Materials()

    def LoadScene(self, filename):
        if self.database.initok:
            self.scene = Scene(file=filename)

    def Export(self, filename, lod=None, parent_collection=None, useNormals=True):
        invert = Matrix3D()
        usedmaterials = []
        geometriecache = {}
        current = 0
        currentpart = 0

        miny = 1000

        global_matrix = axis_conversion(from_forward='-Z', from_up='Y', to_forward='Y', to_up='Z').to_4x4()
        if lod is not None:
            col = bpy.data.collections.new(self.scene.Name + '_LOD_' + lod)
        else:
            col = bpy.data.collections.new(self.scene.Name)

        if parent_collection:
            parent_collection.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)

        for bri in self.scene.Bricks:
            current += 1

            for pa in bri.Parts:
                currentpart += 1
                try:
                    if pa.designID not in geometriecache:
                        geo = Geometry(designID=pa.designID, database=self.database, lod=lod)
                        geometriecache[pa.designID] = geo
                    else:
                        geo = geometriecache[pa.designID]
                except Exception:
                    print(f'WARNING: Missing geo for {pa.designID}')
                    continue

                # Read out 1st Bone matrix values
                ind = 0
                n11 = pa.Bones[ind].matrix.n11
                n12 = pa.Bones[ind].matrix.n12
                n13 = pa.Bones[ind].matrix.n13
                n14 = pa.Bones[ind].matrix.n14
                n21 = pa.Bones[ind].matrix.n21
                n22 = pa.Bones[ind].matrix.n22
                n23 = pa.Bones[ind].matrix.n23
                n24 = pa.Bones[ind].matrix.n24
                n31 = pa.Bones[ind].matrix.n31
                n32 = pa.Bones[ind].matrix.n32
                n33 = pa.Bones[ind].matrix.n33
                n34 = pa.Bones[ind].matrix.n34
                n41 = pa.Bones[ind].matrix.n41
                n42 = pa.Bones[ind].matrix.n42
                n43 = pa.Bones[ind].matrix.n43
                n44 = pa.Bones[ind].matrix.n44

                # Only parts with more then 1 bone are flex parts and for these we need to undo the transformation later
                flexflag = 1
                uniqueId = str(uuid.uuid4().hex)
                material_string = '_' + '_'.join(pa.materials)
                written_obj = geo.designID + material_string
                brick_name = f"brick_{currentpart}_{written_obj}"

                if (len(pa.Bones) > flexflag):
                    # Flex parts are "unique". Ensure they get a unique filename
                    written_obj = written_obj + "_" + uniqueId
                    part_matrix = global_matrix
                else:
                    # Flex parts don't need to be moved, but non-flex parts need
                    transform_matrix = mathutils.Matrix(
                        (
                            (n11, n21, n31, n41),
                            (n12, n22, n32, n42),
                            (n13, n23, n33, n43),
                            (n14, n24, n34, n44)
                        )
                    )

                    # Random Scale for brick seams
                    scalefact = (geo.maxGeoBounding - 0.000 * random.uniform(0.0, 1.000)) / geo.maxGeoBounding

                    scale_matrix = mathutils.Matrix.Scale(scalefact, 4)
                    part_matrix = global_matrix @ transform_matrix @ scale_matrix

                    # miny used for floor plane later
                    if miny > float(n42):
                        miny = n42

                last_color = 0
                geo_meshes = []
                for part in geo.Parts:

                    written_geo = str(geo.designID) + '_' + str(part)

                    geo.Parts[part].outpositions = [elem.copy() for elem in geo.Parts[part].positions]
                    geo.Parts[part].outnormals = [elem.copy() for elem in geo.Parts[part].normals]

                    # translate / rotate only parts with more then 1 bone. This are flex parts
                    if (len(pa.Bones) > flexflag):

                        written_geo = written_geo + '_' + uniqueId
                        for i, b in enumerate(pa.Bones):
                            # positions
                            for j, p in enumerate(geo.Parts[part].outpositions):
                                if (geo.Parts[part].bonemap[j] == i):
                                    p.transform(invert * b.matrix)

                            # normals
                            for k, n in enumerate(geo.Parts[part].outnormals):
                                if (geo.Parts[part].bonemap[k] == i):
                                    n.transformW(invert * b.matrix)

                    if "geo{0}".format(written_geo) not in geometriecache:

                        mesh = bpy.data.meshes.new("geo{0}".format(written_geo))

                        verts = []
                        for point in geo.Parts[part].outpositions:
                            single_vert = mathutils.Vector([point.x, point.y, point.z])
                            verts.append(single_vert)

                        normals = []
                        for point in geo.Parts[part].outnormals:
                            single_norm = mathutils.Vector([point.x, point.y, point.z])
                            normals.append(single_norm)

                        faces = []
                        for face in geo.Parts[part].faces:
                            single_face = [face.a, face.b, face.c]
                            faces.append(single_face)

                        edges = []
                        mesh.from_pydata(verts, edges, faces)

                        for f in mesh.polygons:
                            f.use_smooth = True

                        if useNormals:
                            mesh.calc_normals_split()
                            mesh.normals_split_custom_set_from_vertices(normals)
                            mesh.use_auto_smooth = True

                        geometriecache["geo{0}".format(written_geo)] = mesh.copy()

                    else:
                        mesh = geometriecache["geo{0}".format(written_geo)].copy()
                        mesh.materials.clear()

                    geo_meshes.append(mesh)

                    # try catch here for possible problems in materials assignment of various g, g1, g2, .. files in lxf file
                    try:
                        materialCurrentPart = pa.materials[part]
                        last_color = pa.materials[part]
                    except IndexError:
                        materialCurrentPart = last_color

                    lddmatri = self.allMaterials.getMaterialRibyId(materialCurrentPart)
                    matname = materialCurrentPart

                    if matname not in usedmaterials:
                        mesh.materials.append(lddmatri.string(None))

                    if len(geo.Parts[part].textures) > 0:

                        mesh.uv_layers.new(do_init=False)
                        uv_layer = mesh.uv_layers.active.data

                        uvs = []
                        for text in geo.Parts[part].textures:
                            uv = [text.x, (-1) * text.y]
                            uvs.append(uv)
                        for poly in mesh.polygons:
                            # range is used here to show how the polygons reference loops,
                            # for convenience 'poly.loop_indices' can be used instead.
                            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                                uv_layer[loop_index].uv = uvs[mesh.loops[loop_index].vertex_index]

                used_materials = []
                used_material_indices = {}
                bm = bmesh.new()
                for mesh in geo_meshes:
                    index_remapping = np.empty(len(mesh.materials), dtype=int)
                    for i, material in enumerate(mesh.materials):
                        mat_name = material.name.rsplit(".", 1)[0]
                        if (index := used_material_indices.get(mat_name)) is not None:
                            index_remapping[i] = index
                            bpy.data.materials.remove(material)
                        else:
                            index_remapping[i] = len(used_material_indices)
                            used_material_indices[mat_name] = index_remapping[i]
                            used_materials.append(material)

                    material_indices = np.empty(len(mesh.polygons), dtype=int)
                    mesh.polygons.foreach_get("material_index", material_indices)
                    remapped_indices = index_remapping[material_indices]
                    mesh.polygons.foreach_set("material_index", remapped_indices)

                    bm.from_mesh(mesh)
                    bpy.data.meshes.remove(mesh)

                brick_mesh = bpy.data.meshes.new(brick_name)
                bm.to_mesh(brick_mesh)
                for material in used_materials:
                    brick_mesh.materials.append(material)

                if useNormals:
                    brick_mesh.use_auto_smooth = True

                brick_obj = bpy.data.objects.new(brick_name, brick_mesh)
                brick_obj.matrix_world = part_matrix
                col.objects.link(brick_obj)

        for mesh in geometriecache.values():
            if type(mesh) == bpy.types.Mesh:
                bpy.data.meshes.remove(mesh)

        useplane = True
        if useplane is True:  # write the floor plane in case True
            i = 0


def setDBFolderVars(dbfolderlocation):
    global PRIMITIVEPATH
    global GEOMETRIEPATH
    global MATERIALNAMESPATH
    PRIMITIVEPATH = dbfolderlocation + '/Primitives/'
    GEOMETRIEPATH = dbfolderlocation + '/Primitives/LOD0/'
    MATERIALNAMESPATH = dbfolderlocation + '/MaterialNames/'


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.importldd('INVOKE_DEFAULT')
