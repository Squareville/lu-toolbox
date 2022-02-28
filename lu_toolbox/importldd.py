# based on pyldd2obj by jonnysp and lxfml import pligin by stnng

import bpy
import mathutils
from bpy_extras.io_utils import (
        ImportHelper,
        orientation_helper,
        axis_conversion,
        )

import os
import platform
import sys
import math
import time
import struct
import zipfile
from xml.dom import minidom
import uuid
import random
import time

from .materials import *

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, AddonPreferences

class ImportLDDPreferences(AddonPreferences):
    bl_idname = __package__
    lufilepath: StringProperty(
        name="LU Brick DB",
        subtype='FILE_PATH')

    lddfilepath: StringProperty(
        name="LDD Brick DB",
        subtype='FILE_PATH')

    ldrawfilepath: StringProperty(
        name="LDraw Brick DB",
        subtype='FILE_PATH')

    def draw(self, context):
        self.layout.label(text="Brick DB file paths\nPreference Order:LU > LDD > LDraw")
        self.layout.prop(self, "lufilepath")
        self.layout.prop(self, "lddfilepath")
        self.layout.prop(self, "ldrawfilepath")


class ImportLDDOps(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_description  = "Import LEGO Digital Designer scenes (.lxf/.lxfml)"
    bl_idname = "import_scene.importldd"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import LDD scene"

    # ImportHelper mixin class uses this
    filename_ext = ".lxf"

    filter_glob: StringProperty(
        default="*.lxf;*.lxfml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    renderLOD0: BoolProperty(
        name="LOD0",
        description="Render LOD0",
        default=True,
    )

    renderLOD1: BoolProperty(
        name="LOD1",
        description="Render LOD1",
        default=True,
    )

    renderLOD2: BoolProperty(
        name="LOD2",
        description="Render LOD2",
        default=True,
    )

    def execute(self, context):
        return convertldd_data(
            self,
            context,
            self.filepath,
            self.renderLOD0,
            self.renderLOD1,
            self.renderLOD2
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
    self.layout.operator(ImportLDDOps.bl_idname, text="LU-Toolbox: LEGO Digital Designer (.lxf/.lxfml)")

def convertldd_data(self, context, filepath, renderLOD0, renderLOD1, renderLOD2):

    preferences = context.preferences
    addon_prefs = preferences.addons[__package__].preferences
    lufilepath = addon_prefs.lufilepath
    lddfilepath = addon_prefs.lddfilepath
    ldrawfilepath = addon_prefs.ldrawfilepath

    primaryBrickDBPath = None

    if lufilepath:
        primaryBrickDBPath = lufilepath
    elif lddfilepath:
        primaryBrickDBPath = lddfilepath
    elif ldrawfilepath:
        primaryBrickDBPath = ldrawfilepath
    else:
        self.report({'ERROR'}, 'ERROR: Please define a Brick DB Path in the Addon Preferences')
        return {'FINISHED'}

    converter = Converter()

    if os.path.isdir(primaryBrickDBPath):
        self.report({'INFO'}, 'Found DB folder.')
        start = time.process_time()
        setDBFolderVars(dbfolderlocation = primaryBrickDBPath)
        converter.LoadDBFolder(dbfolderlocation = primaryBrickDBPath)
        end = time.process_time()
        self.report({'INFO'}, f'Time taken to load Brick DB: {end - start} seconds')

    elif os.path.isfile(primaryBrickDBPath):
        self.report({'INFO'}, 'Found db.lif. Will use this.')
        start = time.process_time()
        converter.LoadDatabase(databaselocation = primaryBrickDBPath)
        end = time.process_time()
        self.report({'INFO'}, f'Time taken to load Brick DB: {end - start} seconds')

    lods = []

    # Try to use LU's LODS
    try:
        if (
            os.path.isdir(primaryBrickDBPath)
            and next((f for f in converter.database.filelist.keys() if f.startswith(os.path.join(converter.database.location, 'brickprimitives'))), None)
        ):
            converter.LoadScene(filename=filepath)
            col = bpy.data.collections.new(converter.scene.Name)
            bpy.context.scene.collection.children.link(col)

            if renderLOD0:
                start = time.process_time()
                converter.Export(filename=filepath, lod='0', parent_collection=col)
                end = time.process_time()
                self.report({'INFO'}, f'Time taken to Load LOD0: {end - start} seconds')
            if renderLOD1:
                start = time.process_time()
                converter.Export(filename=filepath, lod='1', parent_collection=col)
                end = time.process_time()
                self.report({'INFO'}, f'Time taken to Load LOD1: {end - start} seconds')
            if renderLOD2:
                start = time.process_time()
                converter.Export(filename=filepath, lod='2', parent_collection=col)
                end = time.process_time()
                self.report({'INFO'}, f'Time taken to Load LOD2: {end - start} seconds')

        elif (os.path.isdir(primaryBrickDBPath) or os.path.isfile(primaryBrickDBPath)):
            start = time.process_time()
            converter.LoadScene(filename=filepath)
            converter.Export(filename=filepath)
            end = time.process_time()
            self.report({'INFO'}, f'Time taken to Load Model: {end - start} seconds')
    except Exception as e:
        self.report({'ERROR'}, str(sys.exc_info()[2]))

    return {'FINISHED'}


PRIMITIVEPATH = '/Primitives/'
GEOMETRIEPATH = PRIMITIVEPATH + 'LOD0/'

class Matrix3D:
    def __init__(self, n11=1,n12=0,n13=0,n14=0,n21=0,n22=1,n23=0,n24=0,n31=0,n32=0,n33=1,n34=0,n41=0,n42=0,n43=0,n44=1):
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
        return '[{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}]'.format(self.n11, self.n12, self.n13,self.n14,self.n21, self.n22, self.n23,self.n24,self.n31, self.n32, self.n33,self.n34,self.n41, self.n42, self.n43,self.n44)

    def rotate(self,angle=0,axis=0):
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
    def __init__(self, x=0,y=0,z=0):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return '[{0},{1},{2}]'.format(self.x, self.y,self.z)

    def string(self,prefix = "v"):
        return '{0} {1:f} {2:f} {3:f}\n'.format(prefix ,self.x , self.y, self.z)

    def transformW(self,matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z
        self.x = x
        self.y = y
        self.z = z

    def transform(self,matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z + matrix.n41
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z + matrix.n42
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z + matrix.n43
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Point3D(x=self.x,y=self.y,z=self.z)

class Point2D:
    def __init__(self, x=0,y=0):
        self.x = x
        self.y = y
    def __str__(self):
        return '[{0},{1}]'.format(self.x, self.y * -1)
    def string(self,prefix="t"):
        return '{0} {1:f} {2:f}\n'.format(prefix , self.x, self.y * -1 )
    def copy(self):
        return Point2D(x=self.x,y=self.y)

class Face:
    def __init__(self,a=0,b=0,c=0):
        self.a = a
        self.b = b
        self.c = c
    def string(self,prefix="f", indexOffset=0 ,textureoffset=0):
        if textureoffset == 0:
            return prefix + ' {0}//{0} {1}//{1} {2}//{2}\n'.format(self.a + indexOffset, self.b + indexOffset, self.c + indexOffset)
        else:
            return prefix + ' {0}/{3}/{0} {1}/{4}/{1} {2}/{5}/{2}\n'.format(self.a + indexOffset, self.b + indexOffset, self.c + indexOffset,self.a + textureoffset, self.b + textureoffset, self.c + textureoffset)
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
            self.matrix = Matrix3D(n11=a,n12=b,n13=c,n14=0,n21=d,n22=e,n23=f,n24=0,n31=g,n32=h,n33=i,n34=0,n41=x,n42=y,n43=z,n44=1)
        elif node.hasAttribute('angle'):
            raise Exception("Cannot Properly import Old LDD Save formats")
            new_matrix = mathutils.Quaternion(
                (
                    float(node.getAttribute('ax')),
                    float(node.getAttribute('ay')),
                    float(node.getAttribute('az'))
                ),
                math.radians(
                    float(node.getAttribute('angle'))
                )
            ).to_matrix().to_4x4()
            new_matrix[3].xyz = float(node.getAttribute('tx')), float(node.getAttribute('ty')), float(node.getAttribute('tz'))
            self.matrix = Matrix3D(
                n11=new_matrix[0][0],
                n12=new_matrix[0][1],
                n13=new_matrix[0][2],
                n14=new_matrix[0][3],
                n21=new_matrix[1][0],
                n22=new_matrix[1][1],
                n23=new_matrix[1][2],
                n24=new_matrix[1][3],
                n31=new_matrix[2][0],
                n32=new_matrix[2][1],
                n33=new_matrix[2][2],
                n34=new_matrix[2][3],
                n41=new_matrix[3][0],
                n42=new_matrix[3][1],
                n43=new_matrix[3][2],
                n44=new_matrix[3][3],
            )
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
            lastm = '0'
            for i, m in enumerate(self.materials):
                if (m == '0'):
                    # self.materials[i] = lastm
                    self.materials[i] = self.materials[0] #in case of 0 choose the 'base' material
                else:
                    lastm = m
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

        # print(f'Scene "{self.Name}" Brickversion: {self.Version}')

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
                self.positions.append(Point3D(x=self.readFloat(),y= self.readFloat(),z=self.readFloat()))

            for i in range(0, self.valueCount):
                 self.normals.append(Point3D(x=self.readFloat(),y= self.readFloat(),z=self.readFloat()))

            if (options & 3) == 3:
                self.texCount = self.valueCount
                for i in range(0, self.valueCount):
                    self.textures.append(Point2D(x=self.readFloat(), y=self.readFloat()))

            for i in range(0, self.faceCount):
                self.faces.append(Face(a=self.readInt(),b=self.readInt(),c=self.readInt()))

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

    def read_Int(self,_offset):
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

        if lod == None:
            geompath = GEOMETRIEPATH
        else:
            geompath = os.path.join(database.location, 'brickprimitives', 'lod' + lod + '/')

        GeometryLocation = os.path.normpath('{0}{1}{2}'.format(geompath, designID,'.g'))
        GeometryCount = 0
        while str(GeometryLocation) in database.filelist:
            self.Parts[GeometryCount] = GeometryReader(data=database.filelist[GeometryLocation].read())
            GeometryCount += 1
            GeometryLocation = os.path.normpath(f'{geompath}{designID}.g{GeometryCount}')

        primitive = Primitive(data = database.filelist[os.path.normpath(PRIMITIVEPATH + designID + '.xml')].read())
        self.Partname = primitive.Designname
        try:
            geoBoundingList = [abs(float(primitive.Bounding['minX']) - float(primitive.Bounding['maxX'])), abs(float(primitive.Bounding['minY']) - float(primitive.Bounding['maxY'])), abs(float(primitive.Bounding['minZ']) - float(primitive.Bounding['maxZ']))]
            geoBoundingList.sort()
            self.maxGeoBounding = geoBoundingList[-1]
        except KeyError as e:
            print('\nBounding errror in part {0}: {1}\n'.format(designID, e))

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
    def __init__(self,boneId=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        self.boneId = boneId
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0,axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
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
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0, axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z

        self.matrix = rotationMatrix
        self.custom2DField = []

        #The height and width are always double the number of studs. The contained text is a 2D array that is always height + 1 and width + 1.
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
        return '[type="{0}" transform="{1}" custom2DField="{2}"]'.format(self.type, self.matrix, self.custom2DField)

class CollisionBox:
    def __init__(self, sX=0, sY=0, sZ=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0, axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z

        self.matrix = rotationMatrix
        self.corner = Point3D(x=sX,y=sY,z=sZ)
        self.positions = []

        self.positions.append(Point3D(x=0, y=0, z=0))
        self.positions.append(Point3D(x=sX, y=0, z=0))
        self.positions.append(Point3D(x=0, y=sY, z=0))
        self.positions.append(Point3D(x=sX, y=sY, z=0))
        self.positions.append(Point3D(x=0, y=0, z=sZ))
        self.positions.append(Point3D(x=0, y=sY, z=sZ))
        self.positions.append(Point3D(x=sX ,y=0, z=sZ))
        self.positions.append(Point3D(x=sX ,y=sY, z=sZ))

    def __str__(self):
        return '[0,0,0] [{0},0,0] [0,{1},0] [{0},{1},0] [0,0,{2}] [0,{1},{2}] [{0},0,{2}] [{0},{1},{2}]'.format(self.corner.x, self.corner.y, self.corner.z)

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
                        self.Bones.append(Bone2(boneId=int(node.getAttribute('boneId')), angle=float(node.getAttribute('angle')), ax=float(node.getAttribute('ax')), ay=float(node.getAttribute('ay')), az=float(node.getAttribute('az')), tx=float(node.getAttribute('tx')), ty=float(node.getAttribute('ty')), tz=float(node.getAttribute('tz'))))
            elif node.nodeName == 'Annotations':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Annotation' and childnode.hasAttribute('designname'):
                        self.Designname = childnode.getAttribute('designname')
            elif node.nodeName == 'Collision':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Box':
                        self.CollisionBoxes.append(CollisionBox(sX=float(childnode.getAttribute('sX')), sY=float(childnode.getAttribute('sY')), sZ=float(childnode.getAttribute('sZ')), angle=float(childnode.getAttribute('angle')), ax=float(childnode.getAttribute('ax')), ay=float(childnode.getAttribute('ay')), az=float(childnode.getAttribute('az')), tx=float(childnode.getAttribute('tx')), ty=float(childnode.getAttribute('ty')), tz=float(childnode.getAttribute('tz'))))
            elif node.nodeName == 'PhysicsAttributes':
                self.PhysicsAttributes = {"inertiaTensor": node.getAttribute('inertiaTensor'),"centerOfMass": node.getAttribute('centerOfMass'),"mass": node.getAttribute('mass'),"frictionType": node.getAttribute('frictionType')}
            elif node.nodeName == 'Bounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.Bounding = {"minX": childnode.getAttribute('minX'), "minY": childnode.getAttribute('minY'), "minZ": childnode.getAttribute('minZ'), "maxX": childnode.getAttribute('maxX'), "maxY": childnode.getAttribute('maxY'), "maxZ": childnode.getAttribute('maxZ')}
            elif node.nodeName == 'GeometryBounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.GeometryBounding = {"minX": childnode.getAttribute('minX'), "minY": childnode.getAttribute('minY'), "minZ": childnode.getAttribute('minZ'), "maxX": childnode.getAttribute('maxX'), "maxY": childnode.getAttribute('maxY'), "maxZ": childnode.getAttribute('maxZ')}
            elif node.nodeName == 'Connectivity':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Custom2DField':
                        self.Fields2D.append(Field2D(type=int(childnode.getAttribute('type')), width=int(childnode.getAttribute('width')), height=int(childnode.getAttribute('height')), angle=float(childnode.getAttribute('angle')), ax=float(childnode.getAttribute('ax')), ay=float(childnode.getAttribute('ay')), az=float(childnode.getAttribute('az')), tx=float(childnode.getAttribute('tx')), ty=float(childnode.getAttribute('ty')), tz=float(childnode.getAttribute('tz')), field2DRawData=str(childnode.firstChild.data)))


class LOCReader:
    def __init__(self, data):
        self.offset = 0
        self.values = {}
        self.data = data
        if sys.version_info < (3, 0):
            if ord(self.data[0]) == 50 and ord(self.data[1]) == 0:
                self.offset += 2
                while self.offset < len(self.data):
                    key = self.NextString().replace('Material', '')
                    value = self.NextString()
                    self.values[key] = value
        else:
            if int(self.data[0]) == 50 and int(self.data[1]) == 0:
                self.offset += 2
                while self.offset < len(self.data):
                    key = self.NextString().replace('Material', '')
                    value = self.NextString()
                    self.values[key] = value

    def NextString(self):
        out = ''
        if sys.version_info < (3, 0):
            t = ord(self.data[self.offset])
            self.offset += 1
            while not t == 0:
                out = '{0}{1}'.format(out,chr(t))
                t = ord(self.data[self.offset])
                self.offset += 1
        else:
            t = int(self.data[self.offset])
            self.offset += 1
            while not t == 0:
                out = '{0}{1}'.format(out,chr(t))
                t = int(self.data[self.offset])
                self.offset += 1
        return out


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
        texture_strg = ''
        ref_strg = ''

        rgb_or_dec_str = '({0}, {1}, {2})'.format(self.r, self.g, self.b)
        matId_or_decId = self.materialId

        if self.materialType == 'Transparent':
            bxdf_mat_str = '''#usda 1.0
                (
                    defaultPrim = "material_{0}"
                )
                def Xform "material_{0}" (
                    assetInfo = {{
                        asset identifier = @material_{0}.usda@
                        string name = "material_{0}"
                    }}
                    kind = "component"
                )
                {{
                    def Material "material_{0}a"
                    {{

                        token outputs:surface.connect = <surfaceShader.outputs:surface>
                {1}
                        def Shader "surfaceShader"
                        {{
                            uniform token info:id = "UsdPreviewSurface"
                            color3f inputs:diffuseColor{3} = {2}
                            float inputs:metallic = 0
                            float inputs:roughness = 0
                            float inputs:opacity = 0.2
                            token outputs:surface
                        }}

                    }}
                }}\n'''.format(matId_or_decId, texture_strg, rgb_or_dec_str, ref_strg, round(random.random(), 3))

        elif self.materialType == 'Metallic':
            bxdf_mat_str = '''#usda 1.0
                (
                    defaultPrim = "material_{0}"
                )
                def Xform "material_{0}" (
                    assetInfo = {{
                        asset identifier = @material_{0}.usda@
                        string name = "material_{0}"
                    }}
                    kind = "component"
                )
                {{
                    def Material "material_{0}a"
                    {{

                        token outputs:surface.connect = <surfaceShader.outputs:surface>
                {1}
                        def Shader "surfaceShader"
                        {{
                            uniform token info:id = "UsdPreviewSurface"
                            color3f inputs:diffuseColor{3} = {2}
                            float inputs:metallic = 1
                            float inputs:roughness = 0
                            token outputs:surface
                        }}

                    }}
                }}\n'''.format(matId_or_decId, texture_strg, rgb_or_dec_str, ref_strg, round(random.random(), 3))

        else:
            bxdf_mat_str = '''#usda 1.0
                (
                    defaultPrim = "material_{0}"
                )
                def Xform "material_{0}" (
                    assetInfo = {{
                        asset identifier = @material_{0}.usda@
                        string name = "material_{0}"
                    }}
                    kind = "component"
                )
                {{
                    def Material "material_{0}a"
                    {{

                        token outputs:surface.connect = <surfaceShader.outputs:surface>
                {1}
                        def Shader "surfaceShader"
                        {{
                            uniform token info:id = "UsdPreviewSurface"
                            color3f inputs:diffuseColor{3} = {2}
                            float inputs:metallic = 0
                            float inputs:roughness = 0
                            token outputs:surface
                        }}

                    }}
                }}\n'''.format(matId_or_decId, texture_strg, rgb_or_dec_str, ref_strg, round(random.random(), 3))

        material = bpy.data.materials.new(matId_or_decId)
        material.diffuse_color = (self.r, self.g, self.b, self.a)

        #return bxdf_mat_str
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

class LIFFile:
    def __init__(self, name, offset, size, handle):
        self.handle = handle
        self.name = name
        self.offset = offset
        self.size = size

    def read(self):
        self.handle.seek(self.offset, 0)
        return self.handle.read(self.size)

class DBFolderReader:
    def __init__(self, folder):
        self.filelist = {}
        self.initok = False
        self.location = folder

        try:
            os.path.isdir(self.location)
        except Exception as e:
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
        if not os.path.exists(os.path.join(self.location,"Assemblies")) and \
                os.path.exists(os.path.join(self.location,"brickdb.zip")):
            print("Found brickdb.zip without uzipped files")
            with zipfile.ZipFile(os.path.join(self.location,"brickdb.zip"), 'r') as zip_ref:
                print("Extracting brickdb.zip")
                zip_ref.extractall(self.location)
        extentions = ('.g', '.g1', '.g2', '.g3', '.g4', '.xml')
        for path, subdirs, files in os.walk(self.location):
            files = filter(lambda file: file.endswith(extentions), files)
            for name in files:
                entryName = os.path.join(path, name)
                self.filelist[entryName] = DBFolderFile(name=entryName, handle=entryName)

class LIFReader:
    def __init__(self, file):
        self.packedFilesOffset = 84
        self.filelist = {}
        self.initok = False
        self.location = file

        try:
            self.filehandle = open(self.location, "rb")
            self.filehandle.seek(0, 0)
        except Exception as e:
            self.initok = False
            print("Database FAIL")
            return
        else:
            if self.filehandle.read(4).decode() == "LIFF":
                self.parse(prefix='', offset=self.readInt(offset=72) + 64)
                if len(self.filelist) > 1:
                    print("Database OK.")
                    self.initok = True
                else:
                    print("Database ERROR")
            else:
                print("Database FAIL")
                self.initok = False

    def fileexist(self,filename):
        return filename in self.filelist

    def parse(self, prefix='', offset=0):
        if prefix == '':
            offset += 36
        else:
            offset += 4

        count = self.readInt(offset=offset)

        for i in range(0, count):
            offset += 4
            entryType = self.readShort(offset=offset)
            offset += 6

            entryName = '{0}{1}'.format(prefix,'/');
            self.filehandle.seek(offset + 1, 0)
            if sys.version_info < (3, 0):
                t = ord(self.filehandle.read(1))
            else:
                t = int.from_bytes(self.filehandle.read(1), byteorder='big')

            while not t == 0:
                entryName ='{0}{1}'.format(entryName,chr(t))
                self.filehandle.seek(1, 1)
                if sys.version_info < (3, 0):
                    t = ord(self.filehandle.read(1))
                else:
                    t = int.from_bytes(self.filehandle.read(1), byteorder='big')

                offset += 2

            offset += 6
            self.packedFilesOffset += 20

            if entryType == 1:
                offset = self.parse(prefix=entryName, offset=offset)
            elif entryType == 2:
                fileSize = self.readInt(offset=offset) - 20
                self.filelist[os.path.normpath(entryName)] = LIFFile(name=entryName, offset=self.packedFilesOffset, size=fileSize, handle=self.filehandle)
                offset += 24
                self.packedFilesOffset += fileSize

        return offset

    def readInt(self, offset=0):
        self.filehandle.seek(offset, 0)
        if sys.version_info < (3, 0):
            return int(struct.unpack('>i', self.filehandle.read(4))[0])
        else:
            return int.from_bytes(self.filehandle.read(4), byteorder='big')

    def readShort(self, offset=0):
        self.filehandle.seek(offset, 0)
        if sys.version_info < (3, 0):
            return int(struct.unpack('>h', self.filehandle.read(2))[0])
        else:
            return int.from_bytes(self.filehandle.read(2), byteorder='big')

class Converter:
    def LoadDBFolder(self, dbfolderlocation):
        self.database = DBFolderReader(folder=dbfolderlocation)

        if self.database.initok:
            self.allMaterials = Materials()

    def LoadDatabase(self,databaselocation):
        self.database = LIFReader(file=databaselocation)

        if self.database.initok:
            self.allMaterials = Materials()

    def LoadScene(self,filename):
        if self.database.initok:
            self.scene = Scene(file=filename)

    def Export(self, filename, lod=None, parent_collection=None):
        invert = Matrix3D()

        indexOffset = 1
        textOffset = 1
        usedmaterials = []
        geometriecache = {}
        writtenribs = []

        start_time = time.time()


        total = len(self.scene.Bricks)
        current = 0
        currentpart = 0

        miny = 1000

        global_matrix = axis_conversion(from_forward='-Z', from_up='Y', to_forward='Y',to_up='Z').to_4x4()
        if lod != None:
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
                except Exception as e:
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

                if (len(pa.Bones) > flexflag):
                    # Flex parts are "unique". Ensure they get a unique filename
                    written_obj = written_obj + "_" + uniqueId

                brick_object = bpy.data.objects.new("brick{0}_{1}".format(currentpart, written_obj), None)
                col.objects.link(brick_object)
                brick_object.empty_display_size = 1.25
                brick_object.empty_display_type = 'PLAIN_AXES'


                if not (len(pa.Bones) > flexflag):
                # Flex parts don't need to be moved, but non-flex parts need
                    transform_matrix = mathutils.Matrix(((n11, n21, n31, n41),(n12, n22, n32, n42),(n13, n23, n33, n43),(n14, n24, n34, n44)))

                    # Random Scale for brick seams
                    scalefact = (geo.maxGeoBounding - 0.000 * random.uniform(0.0, 1.000)) / geo.maxGeoBounding

                    # miny used for floor plane later
                    if miny > float(n42):
                        miny = n42



                # transform -------------------------------------------------------
                last_color = 0
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
                                    p.transform( invert * b.matrix)

                            # normals
                            for k, n in enumerate(geo.Parts[part].outnormals):
                                if (geo.Parts[part].bonemap[k] == i):
                                    n.transformW( invert * b.matrix)

                    if "geo{0}".format(written_geo) not in geometriecache:

                        mesh = bpy.data.meshes.new("geo{0}".format(written_geo))

                        verts = []
                        for point in geo.Parts[part].outpositions:
                            single_vert = mathutils.Vector([point.x, point.y, point.z])
                            verts.append(single_vert)

                        usenormal = False
                        if usenormal == True: # write normals in case flag True
                            # WARNING: SOME PARTS MAY HAVE BAD NORMALS. FOR EXAMPLE MAYBE PART: (85861) PL.ROUND 1X1 W. THROUGHG. HOLE
                            for normal in geo.Parts[part].outnormals:
                                i = 0

                        faces = []
                        for face in geo.Parts[part].faces:
                            single_face = [face.a , face.b, face.c]
                            faces.append(single_face)

                        edges = []
                        mesh.from_pydata(verts, edges, faces)
                        for f in mesh.polygons:
                            f.use_smooth = True
                        geometriecache["geo{0}".format(written_geo)] = mesh

                    else:
                        mesh = geometriecache["geo{0}".format(written_geo)].copy()
                        mesh.materials.clear()

                    geo_obj = bpy.data.objects.new(mesh.name, mesh)
                    geo_obj.parent = brick_object
                    col.objects.link(geo_obj)

                    #try catch here for possible problems in materials assignment of various g, g1, g2, .. files in lxf file
                    try:
                        materialCurrentPart = pa.materials[part]
                        last_color = pa.materials[part]
                    except IndexError:
                        # print(
                        #     f'WARNING: {pa.designID}.g{part} has NO material assignment in lxf. \
                        #     Replaced with color {last_color}. Fix {pa.designID}.xml faces values.'
                        # )
                        materialCurrentPart = last_color

                    lddmatri = self.allMaterials.getMaterialRibyId(materialCurrentPart)
                    matname = materialCurrentPart

                    if not matname in usedmaterials:
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

                if not (len(pa.Bones) > flexflag):
                    #Transform (move) only non-flex parts
                    brick_object.matrix_world =  global_matrix @ transform_matrix
                    brick_object.scale = (scalefact, scalefact, scalefact)

                else:
                    #Flex parts need only to be aligned the Blender coordinate system
                    brick_object.matrix_world = global_matrix

                # -----------------------------------------------------------------

                # Reset index for each part
                indexOffset = 1
                textOffset = 1

        useplane = True
        if useplane == True: # write the floor plane in case True
            i = 0

        sys.stdout.write('%s\r' % ('                                                                                                 '))
        print("--- %s seconds ---" % (time.time() - start_time))


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
