bl_info = {
    "name": "Import LEGO Digital Designer",
    "description": "Import LEGO Digital Designer scenes in .lxf and .lxfml formats",
    "author": "123 <123@gmail.com>",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "File > Import",
    "warning": "Alpha",
    "wiki_url": "https://github.com/",
    "tracker_url": "https://github.com/",
    "category": "Import-Export"
    }

import bpy
import mathutils
from bpy_extras.io_utils import (
        ImportHelper,
        orientation_helper,
        axis_conversion,
        )








#!/usr/bin/env python
# pylddlib version 0.4.9.7
# based on pyldd2obj version 0.4.8 - Copyright (c) 2019 by jonnysp
#
# Updates:
# 0.4.9.7 corrected bug of incorrectly parsing the primitive xml file, specifically with comments. Add support LDDLIFTREE envirnment variable to set location of db.lif.
# 0.4.9.6 preliminary Linux support
# 0.4.9.5 corrected bug of incorrectly Bounding / GeometryBounding parsing the primitive xml file.
# 0.4.9.4 improved lif.db checking for crucial files (because of the infamous botched 4.3.12 LDD Windows update).
# 0.4.9.3 improved Windows and Python 3 compatibility
# 0.4.9.2 changed handling of material = 0 for a part. Now a 0 will choose the 1st material (the base material of a part) and not the previous material of the subpart before. This will fix "Chicken Helmet Part 11262". It may break other parts and this change needs further regression.
# 0.4.9.1 improved custom2DField handling, fixed decorations bug, improved material assignments handling
# 0.4.9 updates to support reading extracted db.lif from db folder
#
# License: MIT License
#

import os
import platform
import sys
import math
import struct
import zipfile
from xml.dom import minidom
import uuid
import random
import time

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf-8')

PRIMITIVEPATH = '/Primitives/'
GEOMETRIEPATH = PRIMITIVEPATH + 'LOD0/'
DECORATIONPATH = '/Decorations/'
MATERIALNAMESPATH = '/MaterialNames/'

LOGOONSTUDSCONNTYPE = {"0:4", "0:4:1", "0:4:2", "0:4:33", "2:4:1", "2:4:34"}

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
        (a, b, c, d, e, f, g, h, i, x, y, z) = map(float, node.getAttribute('transformation').split(','))
        self.matrix = Matrix3D(n11=a,n12=b,n13=c,n14=0,n21=d,n22=e,n23=f,n24=0,n31=g,n32=h,n33=i,n34=0,n41=x,n42=y,n43=z,n44=1)

class Part:
    def __init__(self, node):
        self.isGrouped = False
        self.GroupIDX = 0
        self.Bones = []
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        self.materials = list(map(str, node.getAttribute('materials').split(',')))

        lastm = '0'
        for i, m in enumerate(self.materials):
            if (m == '0'):
                # self.materials[i] = lastm
                self.materials[i] = self.materials[0] #in case of 0 choose the 'base' material
            else:
                lastm = m
        if node.hasAttribute('decoration'):
            self.decoration = list(map(str,node.getAttribute('decoration').split(',')))
        for childnode in node.childNodes:
            if childnode.nodeName == 'Bone':
                self.Bones.append(Bone(node=childnode))

class Brick:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        self.Parts = []
        for childnode in node.childNodes:
            if childnode.nodeName == 'Part':
                self.Parts.append(Part(node=childnode))

class SceneCamera:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        (a, b, c, d, e, f, g, h, i, x, y, z) = map(float, node.getAttribute('transformation').split(','))
        self.matrix = Matrix3D(n11=a,n12=b,n13=c,n14=0,n21=d,n22=e,n23=f,n24=0,n31=g,n32=h,n33=i,n34=0,n41=x,n42=y,n43=z,n44=1)
        self.fieldOfView = float(node.getAttribute('fieldOfView'))
        self.distance = float(node.getAttribute('distance'))

class Scene:
    def __init__(self, file):
        self.Bricks = []
        self.Scenecamera = []
        self.Groups = []

        if file.endswith('.lxfml'):
            with open(file, "rb") as file:
                data = file.read()
        elif file.endswith('.lxf'):
            zf = zipfile.ZipFile(file, 'r')
            data = zf.read('IMAGE100.LXFML')
        else:
            return

        xml = minidom.parseString(data)
        self.Name = xml.firstChild.getAttribute('name')

        for node in xml.firstChild.childNodes:
            if node.nodeName == 'Meta':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'BrickSet':
                        self.Version = str(childnode.getAttribute('version'))
            elif node.nodeName == 'Cameras':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Camera':
                        self.Scenecamera.append(SceneCamera(node=childnode))
            elif node.nodeName == 'Bricks':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Brick':
                        self.Bricks.append(Brick(node=childnode))
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

        print('Scene "'+ self.Name + '" Brickversion: ' + str(self.Version))

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
    def __init__(self, designID, database):
        self.designID = designID
        self.Parts = {}
        self.maxGeoBounding = -1
        self.studsFields2D = []

        GeometryLocation = os.path.normpath('{0}{1}{2}'.format(GEOMETRIEPATH, designID,'.g'))
        GeometryCount = 0
        while str(GeometryLocation) in database.filelist:
            self.Parts[GeometryCount] = GeometryReader(data=database.filelist[GeometryLocation].read())
            GeometryCount += 1
            GeometryLocation = os.path.normpath('{0}{1}{2}{3}'.format(GEOMETRIEPATH, designID,'.g',GeometryCount))

        primitive = Primitive(data = database.filelist[os.path.normpath(PRIMITIVEPATH + designID + '.xml')].read())
        self.Partname = primitive.Designname
        self.studsFields2D = primitive.Fields2D
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
            elif node.nodeName == 'Decoration':
                self.Decoration = {"faces": node.getAttribute('faces'), "subMaterialRedirectLookupTable": node.getAttribute('subMaterialRedirectLookupTable')}

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
    def __init__(self, data):
        self.Materials = {}
        xml = minidom.parseString(data)
        for node in xml.firstChild.childNodes:
            if node.nodeName == 'Material':
                self.Materials[node.getAttribute('MatID')] = Material(node.getAttribute('MatID'),r=int(node.getAttribute('Red')), g=int(node.getAttribute('Green')), b=int(node.getAttribute('Blue')), a=int(node.getAttribute('Alpha')), mtype=str(node.getAttribute('MaterialType')))

    def setLOC(self, loc):
        for key in loc.values:
            if key in self.Materials:
                self.Materials[key].name = loc.values[key].replace(" ", "_")

    def getMaterialbyId(self, mid):
        return self.Materials[mid]

class Materials:
    def __init__(self, data):
        self.MaterialsRi = {}
        material_id_dict = {}
        #with open('lego_colors.csv', 'r') as csvfile:
        #    reader = csv.reader(csvfile, delimiter=',')
        #    next(csvfile) # skip the first row
        #    for row in reader:
        #        material_id_dict[row[0]] = row[6], row[7], row[8], row[9]

        xml = minidom.parseString(data)
        for node in xml.firstChild.childNodes:
            if node.nodeName == 'Material':
                usecsvcolors = False
                if usecsvcolors == True:
                    self.MaterialsRi[node.getAttribute('MatID')] = MaterialRi(materialId=node.getAttribute('MatID'), r=int(material_id_dict[node.getAttribute('MatID')][0]), g=int(material_id_dict[node.getAttribute('MatID')][1]), b=int(material_id_dict[node.getAttribute('MatID')][2]), materialType=str(material_id_dict[node.getAttribute('MatID')][3]))
                elif usecsvcolors == False:
                    self.MaterialsRi[node.getAttribute('MatID')] = MaterialRi(materialId=node.getAttribute('MatID'),r=int(node.getAttribute('Red')), g=int(node.getAttribute('Green')), b=int(node.getAttribute('Blue')), a=int(node.getAttribute('Alpha')), materialType=str(node.getAttribute('MaterialType')))

    def setLOC(self, loc):
        for key in loc.values:
            if key in self.MaterialsRi:
                self.MaterialsRi[key].name = loc.values[key]

    def getMaterialRibyId(self, mid):
        return self.MaterialsRi[mid]

class MaterialRi:
    def __init__(self, materialId, r, g, b, a, materialType):
        self.name = ''
        self.materialType = materialType
        self.materialId = materialId
        self.r = self.sRGBtoLinear(r)
        self.g = self.sRGBtoLinear(g)
        self.b = self.sRGBtoLinear(b)
        self.a = self.sRGBtoLinear(a)

    # convert from sRGB luma to linear light: https://entropymine.com/imageworsener/srgbformula/
    def sRGBtoLinear(self, rgb):
        rgb = float(rgb) / 255
        if (rgb <= 0.0404482362771082):
            lin = float(rgb / 12.92)
        else:
            lin = float(pow((rgb + 0.055) / 1.055, 2.4))
        return round(lin, 9)

    # convert from linear light to sRGB luma
    def lineartosRGB(self, linear):
        if (linear <= 0.00313066844250063):
            rgb = float(linear * 12.92)
        else:
            rgb = float((1.055 * pow(linear, (1.0 / 2.4)) - 0.055))
        return round(rgb, 5)

    def string(self, decorationId):
        texture_strg = ''
        ref_strg = ''

        if decorationId != None and decorationId != '0':
        # We have decorations
            rgb_or_dec_str = '<../diffuseColor_texture.outputs:rgb>'
            ref_strg = '.connect'
            matId_or_decId = '{0}_{1}'.format(self.materialId, decorationId)

            texture_strg = '''
                def Shader "stAttrReader"
                {{
                    uniform token info:id = "UsdPrimvarReader_float2"
                    token inputs:varname = "st"
                    float2 outputs:result
                }}
                def Shader "diffuseColor_texture"
                {{
                    uniform token info:id = "UsdUVTexture"
                    asset inputs:file = @{0}.png@
                    float2 inputs:st.connect = <../stAttrReader.outputs:result>
                    float3 outputs:rgb
                }}
            '''.format(decorationId, round(random.random(), 3))

        else:
        # We don't have decorations
            rgb_or_dec_str = '({0}, {1}, {2})'.format(self.r, self.g, self.b)
            matId_or_decId = self.materialId

        if self.materialType == 'Transparent':
            #bxdf_mat_str = texture_strg +
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

class DBinfo:
    def __init__(self, data):
        xml = minidom.parseString(data)
        self.Version = xml.getElementsByTagName('Bricks')[0].attributes['version'].value
        print('DB Version: ' + str(self.Version))

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
        self.dbinfo = None

        try:
            os.path.isdir(self.location)
        except Exception as e:
            self.initok = False
            print("db folder read FAIL")
            return
        else:
            self.parse()
            if self.fileexist(os.path.join(self.location,'Materials.xml')) and self.fileexist(os.path.join(self.location, 'info.xml')) and self.fileexist(os.path.normpath(os.path.join(self.location, MATERIALNAMESPATH, 'EN/localizedStrings.loc'))):
                self.dbinfo = DBinfo(data=self.filelist[os.path.join(self.location,'info.xml')].read())
                print("DB folder OK.")
                self.initok = True
            else:
                print("DB folder ERROR")

    def fileexist(self, filename):
        return filename in self.filelist

    def parse(self):
        for path, subdirs, files in os.walk(self.location):
            for name in files:
                entryName = os.path.join(path, name)
                self.filelist[entryName] = DBFolderFile(name=entryName, handle=entryName)

class LIFReader:
    def __init__(self, file):
        self.packedFilesOffset = 84
        self.filelist = {}
        self.initok = False
        self.location = file
        self.dbinfo = None

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
                if self.fileexist(os.path.normpath('/Materials.xml')) and self.fileexist(os.path.normpath('/info.xml')) and self.fileexist(os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')):
                    self.dbinfo = DBinfo(data=self.filelist[os.path.normpath('/info.xml')].read())
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

        if self.database.initok and self.database.fileexist(os.path.join(dbfolderlocation,'Materials.xml')) and self.database.fileexist(os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')):
            self.allMaterials = Materials(data=self.database.filelist[os.path.normpath(os.path.join(dbfolderlocation,'Materials.xml'))].read());
            self.allMaterials.setLOC(loc=LOCReader(data=self.database.filelist[os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')].read()))

    def LoadDatabase(self,databaselocation):
        self.database = LIFReader(file=databaselocation)

        if self.database.initok and self.database.fileexist(os.path.normpath('/Materials.xml')) and self.database.fileexist(os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')):
            self.allMaterials = Materials(data=self.database.filelist[os.path.normpath('/Materials.xml')].read());
            self.allMaterials.setLOC(loc=LOCReader(data=self.database.filelist[os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')].read()))

    def LoadScene(self,filename):
        if self.database.initok:
            self.scene = Scene(file=filename)

    def Export(self,filename, useLogoStuds, useLDDCamera):
        invert = Matrix3D()
        #invert.n33 = -1 #uncomment to invert the Z-Axis

        indexOffset = 1
        textOffset = 1
        usedmaterials = []
        geometriecache = {}
        writtenribs = []
        #usedgeo = [] not used currently

        start_time = time.time()


        total = len(self.scene.Bricks)
        current = 0
        currentpart = 0

        # miny used for floor plane later
        miny = 1000

        #useplane = cl.useplane
        #usenormal = cl.usenormal
        uselogoonstuds = useLogoStuds
        useLDDCamera = useLDDCamera
        #fstop = cl.args.fstop
        #fov =  cl.args.fov

        global_matrix = axis_conversion(from_forward='-Z', from_up='Y', to_forward='Y',to_up='Z').to_4x4()
        #col = bpy.data.collections.get("Collection")
        scene_col = bpy.data.collections.new(self.scene.Name)
        bpy.context.scene.collection.children.link(scene_col)
        col = bpy.data.collections.new("LOD_0")
        scene_col.children.link(col)

        if useLDDCamera == True:
            for cam in self.scene.Scenecamera:
                camera_data = bpy.data.cameras.new(name='Cam_{0}'.format(cam.refID))
                camera_object = bpy.data.objects.new('Cam_{0}'.format(cam.refID), camera_data)
                transform_matrix = mathutils.Matrix(((cam.matrix.n11, cam.matrix.n21, cam.matrix.n31, cam.matrix.n41),(cam.matrix.n12, cam.matrix.n22, cam.matrix.n32, cam.matrix.n42),(cam.matrix.n13, cam.matrix.n23, cam.matrix.n33, cam.matrix.n43),(cam.matrix.n14, cam.matrix.n24, cam.matrix.n34, cam.matrix.n44)))
                camera_object.matrix_world = global_matrix @ transform_matrix
                #bpy.context.scene.collection.objects.link(camera_object)
                col.objects.link(camera_object)
                camera_object.data.lens_unit = 'FOV'
                camera_object.data.angle = math.radians(25)

        for bri in self.scene.Bricks:
            current += 1

            for pa in bri.Parts:
                currentpart += 1

                if pa.designID not in geometriecache:
                    geo = Geometry(designID=pa.designID, database=self.database)
                    progress(current ,total , "(" + geo.designID + ") " + geo.Partname, ' ')
                    geometriecache[pa.designID] = geo

                else:
                    geo = geometriecache[pa.designID]
                    progress(current ,total , "(" + geo.designID + ") " + geo.Partname ,'-')

                # n11=a, n21=d, n31=g, n41=x,
                # n12=b, n22=e, n32=h, n42=y,
                # n13=c, n23=f, n33=i, n43=z,
                # n14=0, n24=0, n34=0, n44=1

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

                if hasattr(pa, 'decoration'):
                    decoration_string = '_' + '_'.join(pa.decoration)
                    written_obj = written_obj + decoration_string

                if (len(pa.Bones) > flexflag):
                    # Flex parts are "unique". Ensure they get a unique filename
                    written_obj = written_obj + "_" + uniqueId

                brick_object = bpy.data.objects.new("brick{0}_{1}".format(currentpart, written_obj), None)
                #bpy.context.scene.collection.objects.link(brick_object)
                col.objects.link(brick_object)
                brick_object.empty_display_size = 1.25
                brick_object.empty_display_type = 'PLAIN_AXES'
                #out.write('''
                #def "brick{0}_{1}" (
                # add references = @./{2}/{1}.usda@ {{\n'''.format(currentpart, written_obj, assetsDir))

                if not (len(pa.Bones) > flexflag):
                # Flex parts don't need to be moved, but non-flex parts need
                    transform_matrix = mathutils.Matrix(((n11, n21, n31, n41),(n12, n22, n32, n42),(n13, n23, n33, n43),(n14, n24, n34, n44)))

                    # Random Scale for brick seams
                    scalefact = (geo.maxGeoBounding - 0.000 * random.uniform(0.0, 1.000)) / geo.maxGeoBounding

                    # miny used for floor plane later
                    if miny > float(n42):
                        miny = n42

                #op = open(written_obj + ".usda", "w+")
                #op.write('''#usda 1.0 string name = "brick_{0}"{{\n'''.format(written_obj))

                # transform -------------------------------------------------------
                decoCount = 0
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
                            #gop.write('\t\tnormal3f[] normals = [')
                            for normal in geo.Parts[part].outnormals:
                                i =0
                                #gop.write('{0}({1}, {2}, {3})'.format(fmt, normal.x, normal.y, normal.z))

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
                    except IndexError:
                        print('WARNING: {0}.g{1} has NO material assignment in lxf. Replaced with color 9. Fix {0}.xml faces values.'.format(pa.designID, part))
                        materialCurrentPart = '9'

                    lddmatri = self.allMaterials.getMaterialRibyId(materialCurrentPart)
                    matname = materialCurrentPart

                    deco = '0'
                    if hasattr(pa, 'decoration') and len(geo.Parts[part].textures) > 0:
                        if decoCount < len(pa.decoration):
                            deco = pa.decoration[decoCount]
                        decoCount += 1

                    extfile = ''
                    if not deco == '0':
                    #    extfile = deco + '.png'
                    #    matname += "_" + deco
                        decofilename = DECORATIONPATH + deco + '.png'

                        mat = bpy.data.materials.new(name=deco + '.png')
                        mat.use_nodes = True
                        bsdf = mat.node_tree.nodes["Principled BSDF"]
                        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
                        texImage.image = bpy.data.images.load(os.path.normpath(decofilename))
                        mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])

                        mesh.materials.append(mat)

                        # Assign it to object
                        #if geo_obj.data.materials:
                        #    geo_obj.data.materials[0] = mat
                        #else:
                        #    geo_obj.data.materials.append(mat)


                    #    if not os.path.isfile(os.path.join(assetsDir, extfile)) and self.database.fileexist(decofilename):
                    #        with open(os.path.join(assetsDir, extfile), "wb") as f:
                    #            f.write(self.database.filelist[decofilename].read())
                    #            f.close()

                    if not matname in usedmaterials:
                    #    usedmaterials.append(matname)
                    #    outmat = open(os.path.join(assetsDir,"material_" + matname + ".usda"), "w+")

                    #    if not deco == '0':
                    #        outmat.write(lddmatri.string(deco))

                    #    else:
                    #        outmat.write(lddmatri.string(None))
                        mesh.materials.append(lddmatri.string(None))
                    #    outmat.close()

                    #op.write('\n\t\tcolor3f[] primvars:displayColor = [({0}, {1}, {2})]\n'.format(lddmatri.r, lddmatri.g, lddmatri.b))
                    #op.write('\t\trel material:binding = <Material{0}/material_{0}a>\n'.format(matname))
                    #op.write('''\t\tdef "Material{0}" (add references = @./material_{0}.usda@'''.format(matname))

                    #gop.write('\n\t\tcolor3f[] primvars:displayColor = [(1, 0, 0)]\n')

                    if len(geo.Parts[part].textures) > 0:

                        mesh.uv_layers.new(do_init=False)
                        uv_layer = mesh.uv_layers.active.data

                        #gop.write('\n\t\tfloat2[] primvars:st = [')
                        uvs = []
                        for text in geo.Parts[part].textures:
                            uv = [text.x, (-1) * text.y]
                            #gop.write('{0}({1}, {2})'.format(fmt, text.x, (-1) * text.y))
                            uvs.append(uv)

                        #gop.write('\t\tint[] primvars:st:indices = [')

                        for poly in mesh.polygons:
                            #print("Polygon index: %d, length: %d" % (poly.index, poly.loop_total))

                            # range is used here to show how the polygons reference loops,
                            # for convenience 'poly.loop_indices' can be used instead.
                            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                                #print("    Vertex: %d" % mesh.loops[loop_index].vertex_index)
                                uv_layer[loop_index].uv = uvs[mesh.loops[loop_index].vertex_index]
                                #print("    UV: %r" % uv_layer[loop_index].uv)

                        #for face in geo.Parts[part].faces:
                            #gop.write('{0}{1},{2},{3}'.format(fmt, face.a, face.b, face.c))
                            #out.write(face.string("f",indexOffset,textOffset))

                    #gop.close()

                #Logo on studs
                if uselogoonstuds == True: # write logo on studs in case flag True

                    if 'logoonstuds' not in geometriecache:
                        #Basically the .usda logo from LegoToRHD - without the disk
                        faceVertexCounts = [3, 4, 4, 4, 4, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 4, 3, 3, 4, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 4, 3, 3, 4, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 3, 3, 4, 4, 4, 4, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 4, 3, 3, 4, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 4, 3, 3, 4, 4, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3]
                        faceVertexIndices = [0, 1, 2, 3, 0, 2, 4, 5, 3, 4, 6, 7, 8, 9, 10, 11, 7, 10, 12, 13, 14, 15, 14, 16, 17, 15, 16, 18, 19, 17, 18, 20, 19, 20, 21, 22, 21, 23, 24, 21, 24, 22, 23, 0, 3, 23, 3, 24, 24, 3, 5, 11, 25, 7, 7, 25, 13, 8, 11, 26, 25, 25, 26, 14, 25, 14, 13, 26, 27, 16, 14, 27, 28, 18, 16, 28, 29, 30, 28, 30, 18, 18, 30, 20, 29, 31, 30, 30, 31, 21, 30, 21, 20, 29, 1, 23, 31, 31, 23, 21, 1, 0, 23, 2, 32, 33, 4, 4, 33, 34, 6, 32, 35, 33, 33, 35, 36, 33, 36, 34, 35, 37, 38, 36, 37, 39, 40, 38, 39, 41, 42, 39, 42, 40, 40, 42, 43, 41, 44, 42, 42, 44, 45, 42, 45, 43, 44, 46, 45, 45, 46, 47, 46, 9, 47, 32, 48, 35, 48, 49, 37, 35, 49, 50, 39, 37, 50, 51, 41, 50, 41, 39, 51, 44, 41, 51, 12, 52, 44, 44, 52, 46, 12, 10, 52, 52, 10, 46, 46, 10, 9, 53, 54, 55, 55, 54, 56, 57, 58, 56, 53, 59, 60, 53, 55, 59, 55, 58, 59, 53, 61, 62, 53, 62, 54, 54, 62, 63, 64, 65, 66, 67, 66, 68, 66, 65, 68, 61, 69, 62, 62, 69, 70, 63, 62, 70, 71, 72, 73, 74, 71, 73, 75, 76, 74, 75, 77, 78, 79, 80, 79, 81, 82, 80, 81, 83, 84, 82, 83, 85, 84, 85, 86, 87, 86, 88, 89, 86, 89, 87, 88, 71, 74, 88, 74, 89, 89, 74, 76, 67, 90, 66, 66, 90, 78, 64, 67, 91, 90, 90, 91, 79, 90, 79, 78, 91, 92, 81, 79, 92, 93, 83, 81, 93, 94, 95, 93, 95, 83, 83, 95, 85, 94, 96, 95, 95, 96, 86, 95, 86, 85, 94, 72, 88, 96, 96, 88, 86, 72, 71, 88, 73, 97, 98, 75, 75, 98, 99, 77, 97, 100, 98, 98, 100, 101, 98, 101, 99, 100, 102, 103, 101, 102, 104, 105, 103, 104, 106, 107, 104, 107, 105, 105, 107, 108, 106, 109, 107, 107, 109, 110, 107, 110, 108, 109, 111, 110, 110, 111, 112, 111, 59, 58, 111, 58, 112, 97, 113, 100, 113, 114, 102, 100, 114, 115, 104, 102, 115, 116, 106, 115, 106, 104, 116, 109, 106, 116, 117, 109, 109, 117, 111, 117, 60, 59, 117, 59, 111, 118, 119, 120, 121, 122, 123, 124, 122, 121, 123, 121, 120, 123, 125, 126, 127, 125, 127, 128, 128, 127, 129, 130, 131, 128, 132, 133, 134, 132, 135, 133, 135, 136, 133, 137, 135, 138, 138, 139, 136, 121, 122, 140, 128, 141, 125, 138, 125, 141, 137, 131, 130, 140, 122, 142, 143, 144, 142, 144, 135, 135, 144, 121, 118, 144, 143, 118, 121, 144, 142, 132, 145, 142, 135, 132, 133, 136, 134, 126, 146, 127, 127, 146, 147, 127, 147, 129, 123, 120, 124, 148, 149, 150, 151, 151, 150, 152, 153, 149, 154, 150, 150, 154, 155, 150, 155, 152, 320, 324, 321, 158, 159, 160, 158, 151, 159, 151, 153, 157, 159, 151, 158, 148, 160, 159, 161, 159, 162, 161, 159, 157, 162, 163, 164, 165, 166, 167, 164, 163, 168, 169, 167, 166, 170, 171, 172, 173, 174, 175, 171, 170, 176, 177, 178, 178, 177, 179, 180, 180, 179, 181, 182, 182, 181, 183, 183, 184, 185, 185, 186, 187, 185, 184, 186, 187, 166, 163, 187, 186, 166, 186, 168, 166, 174, 170, 188, 170, 173, 176, 188, 174, 188, 189, 188, 178, 189, 188, 176, 178, 189, 178, 180, 190, 190, 180, 182, 191, 191, 192, 193, 191, 182, 192, 182, 183, 192, 193, 192, 194, 192, 185, 194, 192, 183, 185, 193, 194, 187, 165, 194, 185, 187, 165, 187, 163, 164, 167, 195, 196, 167, 169, 197, 195, 196, 195, 198, 195, 199, 198, 195, 197, 199, 198, 199, 200, 201, 201, 200, 202, 203, 203, 204, 205, 203, 202, 204, 202, 206, 204, 205, 204, 207, 204, 208, 207, 204, 206, 208, 207, 208, 209, 208, 210, 209, 209, 210, 172, 196, 198, 211, 211, 198, 201, 212, 212, 201, 203, 213, 213, 205, 214, 213, 203, 205, 214, 205, 207, 214, 207, 215, 175, 207, 209, 215, 175, 215, 171, 215, 209, 171, 209, 172, 171, 216, 217, 218, 217, 219, 218, 220, 219, 221, 216, 222, 223, 216, 223, 217, 217, 223, 221, 216, 224, 225, 216, 218, 224, 218, 226, 224, 227, 228, 229, 230, 231, 228, 228, 231, 229, 225, 224, 232, 224, 233, 232, 226, 233, 224, 234, 235, 236, 237, 238, 235, 234, 239, 240, 238, 237, 241, 242, 243, 243, 242, 244, 245, 245, 244, 246, 247, 247, 246, 248, 248, 249, 250, 250, 251, 252, 250, 249, 251, 252, 237, 234, 252, 251, 237, 251, 239, 237, 230, 228, 253, 228, 227, 241, 253, 230, 253, 254, 253, 243, 254, 253, 241, 243, 254, 243, 245, 255, 255, 245, 247, 256, 256, 257, 258, 256, 247, 257, 247, 248, 257, 258, 257, 259, 257, 250, 259, 257, 248, 250, 258, 259, 252, 236, 259, 250, 252, 236, 252, 234, 235, 238, 260, 261, 238, 240, 262, 260, 261, 260, 263, 260, 264, 263, 260, 262, 264, 263, 264, 265, 266, 266, 265, 267, 268, 268, 269, 270, 268, 267, 269, 267, 271, 269, 270, 269, 272, 269, 273, 272, 269, 271, 273, 272, 273, 274, 273, 275, 274, 274, 221, 223, 274, 275, 221, 261, 263, 276, 276, 263, 266, 277, 277, 266, 268, 278, 278, 270, 279, 278, 268, 270, 279, 270, 272, 279, 272, 280, 272, 274, 280, 280, 223, 222, 280, 274, 223, 281, 282, 283, 284, 285, 286, 287, 285, 287, 282, 282, 287, 283, 288, 290, 289, 288, 289, 291, 291, 289, 292, 293, 291, 294, 295, 296, 297, 295, 297, 298, 298, 297, 299, 300, 298, 301, 301, 299, 302, 282, 303, 285, 291, 304, 288, 301, 288, 304, 300, 294, 285, 303, 293, 305, 306, 307, 305, 298, 306, 303, 282, 306, 281, 307, 306, 281, 306, 282, 305, 308, 295, 305, 295, 298, 297, 296, 299, 290, 309, 289, 289, 309, 310, 289, 310, 292, 287, 286, 283, 311, 312, 313, 314, 312, 315, 316, 313, 314, 313, 317, 313, 318, 317, 313, 316, 318, 315, 320, 319, 319, 320, 321, 322, 323, 324, 322, 324, 312, 315, 312, 320, 312, 311, 322, 323, 325, 324, 324, 325, 326, 324, 326, 321, 120, 119, 284, 283, 114, 113, 276, 277, 60, 117, 280, 222, 48, 32, 196, 211, 155, 154, 317, 318, 94, 93, 256, 258, 92, 91, 254, 255, 72, 94, 258, 236, 142, 145, 308, 305, 118, 143, 307, 281, 29, 28, 191, 193, 134, 136, 299, 296, 160, 161, 325, 323, 40, 43, 206, 202, 291, 293, 304, 68, 65, 229, 231, 84, 85, 248, 246, 154, 149, 314, 317, 87, 89, 251, 249, 89, 76, 239, 251, 116, 115, 278, 279, 12, 51, 214, 175, 162, 157, 321, 326, 128, 131, 294, 291, 54, 63, 226, 218, 110, 112, 275, 273, 156, 152, 316, 319, 108, 110, 273, 271, 138, 136, 299, 301, 73, 72, 236, 235, 152, 155, 318, 316, 105, 108, 271, 267, 135, 137, 300, 298, 80, 82, 244, 242, 99, 101, 264, 262, 146, 309, 290, 126, 6, 34, 197, 169, 49, 48, 211, 212, 78, 80, 242, 241, 97, 73, 235, 261, 149, 148, 311, 314, 26, 11, 174, 189, 47, 9, 172, 210, 124, 120, 283, 286, 145, 132, 295, 308, 24, 5, 168, 186, 122, 124, 286, 285, 148, 158, 322, 311, 147, 310, 309, 146, 139, 138, 301, 302, 141, 128, 291, 304, 53, 60, 222, 216, 56, 58, 221, 219, 131, 122, 285, 294, 28, 27, 190, 191, 67, 68, 231, 230, 19, 20, 183, 181, 51, 50, 213, 214, 131, 294, 292, 129, 82, 84, 246, 244, 17, 19, 181, 179, 27, 26, 189, 190, 15, 17, 179, 177, 103, 105, 267, 265, 129, 292, 310, 147, 56, 54, 218, 219, 36, 38, 200, 199, 9, 8, 173, 172, 112, 58, 221, 275, 130, 128, 291, 293, 113, 97, 261, 276, 22, 24, 186, 184, 8, 13, 176, 173, 20, 22, 184, 183, 5, 6, 169, 168, 58, 55, 217, 221, 11, 12, 175, 174, 138, 135, 298, 301, 158, 160, 323, 322, 132, 134, 296, 295, 115, 114, 277, 278, 58, 57, 220, 221, 125, 288, 301, 138, 136, 135, 298, 299, 45, 47, 210, 208, 1, 29, 193, 165, 56, 63, 226, 219, 63, 70, 233, 226, 137, 141, 304, 300, 32, 2, 164, 196, 2, 1, 165, 164, 64, 78, 241, 227, 34, 36, 199, 197, 85, 87, 249, 248, 136, 139, 302, 299, 101, 103, 265, 264, 65, 64, 227, 229, 13, 15, 177, 176, 128, 129, 292, 291, 117, 116, 279, 280, 91, 67, 230, 254, 324, 320, 312, 70, 69, 232, 233, 69, 61, 225, 232, 57, 56, 219, 220, 161, 162, 326, 325, 121, 140, 303, 282, 119, 118, 281, 284, 76, 77, 240, 239, 43, 45, 208, 206, 61, 53, 216, 225, 126, 290, 288, 125, 93, 92, 255, 256, 50, 49, 212, 213, 55, 56, 219, 217, 143, 142, 305, 307, 38, 40, 202, 200, 77, 99, 262, 240, 140, 130, 293, 303, 156, 319, 321, 157, 294, 291, 292, 218, 219, 226, 221, 219, 217, 298, 299, 301, 303, 306, 293, 300, 306, 298, 304, 293, 306, 306, 300, 304, 315, 319, 316]
                        points = [(-0.126506, 0.046228, 0.075507), (-0.134361, 0.039157, 0.083265), (-0.090418, 0.046228, -0.059231), (-0.113374, 0.048396, 0.079049), (-0.077275, 0.048396, -0.055701), (-0.105936, 0.039157, 0.081055), (-0.069836, 0.039157, -0.053695), (-0.185774, 0.048396, 0.059649), (-0.198906, 0.040054888, 0.056107), (-0.162818, 0.040054888, -0.078631), (-0.149674, 0.048396, -0.075102), (-0.17896, 0.039157, 0.071314), (-0.142236, 0.039157, -0.073095), (-0.200103, 0.040054888, 0.074099), (-0.186642, 0.049156, 0.086793), (-0.196634, 0.042985, 0.092562), (-0.177001, 0.049156, 0.097788), (-0.184026, 0.042985, 0.106944), (-0.163886, 0.049156, 0.104255), (-0.166872, 0.042985, 0.115401), (-0.148141, 0.041675918, 0.113971), (-0.133057, 0.048394, 0.104651), (-0.129202, 0.039157, 0.111329), (-0.128247, 0.048394, 0.08796), (-0.117444, 0.03836843, 0.096248), (-0.186602, 0.048394, 0.072324), (-0.176649, 0.042985, 0.081024), (-0.169977, 0.042985, 0.088632), (-0.160899, 0.042985, 0.093109), (-0.150926, 0.039157, 0.092829), (-0.149917, 0.048394, 0.100471), (-0.139865, 0.046228, 0.09286), (-0.089688, 0.046228, -0.070384), (-0.076187, 0.048394, -0.07216), (-0.068545, 0.039157, -0.073169), (-0.08563, 0.049156, -0.085383), (-0.075638, 0.042985, -0.091152), (-0.09527, 0.049156, -0.096378), (-0.088246, 0.042985, -0.105534), (-0.108386, 0.049156, -0.102845), (-0.105399, 0.042985, -0.113991), (-0.121825, 0.046228, -0.095043), (-0.123601, 0.048394, -0.108544), (-0.12461, 0.039157, -0.116186), (-0.134434, 0.048394, -0.09496), (-0.141242, 0.04017304, -0.106752), (-0.151613, 0.048394, -0.092371), (-0.157727, 0.039157, -0.097066), (-0.095623, 0.042985, -0.079614), (-0.102294, 0.042985, -0.087222), (-0.111373, 0.042985, -0.091699), (-0.130578, 0.039157, -0.088282), (-0.140809, 0.046228, -0.084082), (-0.043134, 0.03949214, -0.009144999), (-0.039351, 0.049157, 0.003355), (-0.049413, 0.048396, -0.001429), (-0.055641, 0.046228, 0.012193), (-0.065789, 0.04355, 0.008846), (-0.044308, 0.040733308, -0.07311), (-0.034301, 0.049157, -0.07636), (-0.023186, 0.042984, -0.07311), (-0.015586, 0.039157, -0.009145), (-0.015586, 0.048396, -0.001429), (-0.015586, 0.046228, 0.012193), (-0.078912, 0.046228, 0.056102), (-0.073138, 0.04355, 0.04753), (-0.06578, 0.048396, 0.059644), (-0.05896, 0.039157, 0.071314), (-0.062551, 0.04355, 0.050385), (-0.005791, 0.04355, -0.002136), (-0.005791, 0.04355, 0.008846), (-0.006506, 0.046228, 0.075507), (-0.014361, 0.039157, 0.083265), (0.029582, 0.046228, -0.059231), (0.006626, 0.048396, 0.079049), (0.042726, 0.048396, -0.055701), (0.014064, 0.039157, 0.081055), (0.050164, 0.039157, -0.053695), (-0.080103, 0.046228, 0.074099), (-0.066642, 0.049156, 0.086793), (-0.076634, 0.042985, 0.092562), (-0.057001, 0.049156, 0.097788), (-0.064026, 0.042985, 0.106944), (-0.043886, 0.049156, 0.104255), (-0.046872, 0.042985, 0.115401), (-0.028141, 0.040727776, 0.113971), (-0.013058, 0.048394, 0.104651), (-0.009202, 0.039157, 0.111329), (-0.008248, 0.048394, 0.08796), (0.002557, 0.037882198, 0.096248), (-0.066602, 0.048394, 0.072324), (-0.056649, 0.042985, 0.081024), (-0.049977, 0.042985, 0.088632), (-0.040899, 0.042985, 0.093109), (-0.030927, 0.039157, 0.092829), (-0.029917, 0.048394, 0.100471), (-0.019865, 0.046228, 0.09286), (0.030312, 0.046228, -0.070384), (0.043813, 0.048394, -0.07216), (0.051455, 0.039157, -0.073169), (0.03437, 0.049156, -0.085383), (0.044363, 0.042985, -0.091152), (0.02473, 0.049156, -0.096378), (0.031754, 0.042985, -0.105534), (0.011614, 0.049156, -0.102845), (0.014601, 0.042985, -0.113991), (-0.001825, 0.046228, -0.095043), (-0.003601, 0.048394, -0.108544), (-0.00461, 0.039157, -0.116186), (-0.014434, 0.048394, -0.09496), (-0.021242, 0.039360024, -0.106752), (-0.031613, 0.048394, -0.092371), (-0.037727, 0.039157, -0.097066), (0.024378, 0.042985, -0.079614), (0.017706, 0.042985, -0.087222), (0.008627, 0.042985, -0.091699), (-0.010578, 0.039157, -0.088282), (-0.020809, 0.040078178, -0.084082), (0.086914, 0.03940685, 0.114693), (0.026423, 0.04355, 0.11565), (0.023075, 0.046228, 0.105855), (0.077689, 0.049157, 0.105855), (0.077689, 0.042984, 0.094306), (0.031914, 0.048396, 0.101071), (0.023075, 0.039157, 0.097016), (0.104534, 0.039875723, -0.0081939995), (0.076914, 0.039157, -0.009145), (0.076914, 0.048396, -0.001429), (0.104534, 0.049157, 0.003355), (0.076914, 0.046228, 0.012193), (0.110484, 0.049157, 0.015855), (0.097984, 0.046228, 0.012193), (0.141914, 0.038789246, -0.115694), (0.086914, 0.048396, -0.108929), (0.078075, 0.039157, -0.112984), (0.141913, 0.049157, -0.104145), (0.078075, 0.03978615, -0.104145), (0.138639, 0.049157, -0.091645), (0.126139, 0.043286618, -0.095307), (0.081423, 0.04355, -0.09435), (0.090189, 0.049157, 0.093355), (0.117034, 0.049157, -0.009145), (0.153463, 0.03945926, -0.104145), (0.095753, 0.039157, 0.114693), (0.091698, 0.048396, 0.105855), (0.150753, 0.039157, -0.112984), (0.067119, 0.04355, -0.002136), (0.067119, 0.04355, 0.008846), (0.259414, 0.039157, -0.104145), (0.204414, 0.039157, 0.105855), (0.196698, 0.048396, 0.105855), (0.251698, 0.048396, -0.104145), (0.183075, 0.03879879, 0.105855), (0.240877, 0.048396, -0.099361), (0.197405, 0.038682904, 0.11565), (0.186423, 0.038682904, 0.11565), (0.2348, 0.037732825, -0.091645), (0.191914, 0.039692704, -0.095307), (0.246914, 0.038630664, -0.112984), (0.191914, 0.048396, -0.108929), (0.191914, 0.039157, -0.116645), (0.182119, 0.04355, -0.109637), (0.182119, 0.04355, -0.098654), (-0.12543, 0.058638, 0.074911), (-0.089341, 0.058638, -0.059827), (-0.133284, 0.051567, 0.082669), (-0.112298, 0.060806, 0.078453), (-0.076198, 0.060806, -0.056297), (-0.104859, 0.051567, 0.080459), (-0.068759, 0.051567, -0.054291), (-0.184697, 0.060806, 0.059053), (-0.148598, 0.060806, -0.075697), (-0.161741, 0.058638, -0.079227), (-0.19783, 0.058638, 0.055511), (-0.177883, 0.051567, 0.070718), (-0.141159, 0.051567, -0.073691), (-0.199026, 0.058638, 0.073504), (-0.195557, 0.055395, 0.091966), (-0.185565, 0.061566, 0.086198), (-0.182949, 0.055395, 0.106349), (-0.175925, 0.061566, 0.097192), (-0.165796, 0.055395, 0.114805), (-0.162809, 0.061566, 0.103659), (-0.147065, 0.058638, 0.113376), (-0.128125, 0.051567, 0.110734), (-0.131981, 0.060804, 0.104056), (-0.116367, 0.058638, 0.095653), (-0.127171, 0.060804, 0.087365), (-0.185525, 0.060804, 0.071728), (-0.175572, 0.055395, 0.080428), (-0.168901, 0.055395, 0.088036), (-0.159822, 0.055395, 0.092513), (-0.14884, 0.060804, 0.099875), (-0.14985, 0.051567, 0.092233), (-0.138788, 0.058638, 0.092264), (-0.07511, 0.060804, -0.072755), (-0.088611, 0.058638, -0.07098), (-0.067468, 0.051567, -0.073765), (-0.084553, 0.061566, -0.085979), (-0.074561, 0.055395, -0.091748), (-0.087169, 0.055395, -0.10613), (-0.094194, 0.061566, -0.096974), (-0.104323, 0.055395, -0.114587), (-0.107309, 0.061566, -0.103441), (-0.122524, 0.060804, -0.109139), (-0.120748, 0.058638, -0.095639), (-0.123534, 0.051567, -0.116782), (-0.133357, 0.060804, -0.095556), (-0.140165, 0.058638, -0.107348), (-0.150537, 0.060804, -0.092966), (-0.15665, 0.051567, -0.097662), (-0.094546, 0.055395, -0.08021), (-0.101218, 0.055395, -0.087818), (-0.110296, 0.055395, -0.092295), (-0.129501, 0.051567, -0.088878), (-0.139733, 0.058638, -0.084678), (-0.042057, 0.058638, -0.009741), (-0.048336, 0.060806, -0.002025), (-0.038274, 0.061567, 0.002759), (-0.054564, 0.058638, 0.011598), (-0.064712, 0.05596, 0.00825), (-0.043231, 0.058638, -0.073706), (-0.02211, 0.055394, -0.073706), (-0.033224, 0.061567, -0.076956), (-0.014509, 0.060806, -0.002025), (-0.014509, 0.051567, -0.009741), (-0.014509, 0.058638, 0.011598), (-0.077835, 0.058638, 0.055506), (-0.064703, 0.060806, 0.059048), (-0.072061, 0.05596, 0.046934), (-0.057883, 0.051567, 0.070718), (-0.061474, 0.05596, 0.04979), (-0.004714, 0.05596, -0.002732), (-0.004714, 0.05596, 0.00825), (-0.00543, 0.058638, 0.074911), (0.030659, 0.058638, -0.059827), (-0.013284, 0.051567, 0.082669), (0.007702, 0.060806, 0.078453), (0.043803, 0.060806, -0.056297), (0.015141, 0.051567, 0.080459), (0.051241, 0.051567, -0.054291), (-0.079026, 0.058638, 0.073504), (-0.075557, 0.055395, 0.091966), (-0.065565, 0.061566, 0.086198), (-0.062949, 0.055395, 0.106349), (-0.055925, 0.061566, 0.097192), (-0.045796, 0.055395, 0.114805), (-0.042809, 0.061566, 0.103659), (-0.027065, 0.058638, 0.113376), (-0.008125, 0.051567, 0.110734), (-0.011981, 0.060804, 0.104056), (0.003633, 0.058638, 0.095653), (-0.007171, 0.060804, 0.087365), (-0.065525, 0.060804, 0.071728), (-0.055572, 0.055395, 0.080428), (-0.0489, 0.055395, 0.088036), (-0.039822, 0.055395, 0.092513), (-0.02884, 0.060804, 0.099875), (-0.02985, 0.051567, 0.092233), (-0.018788, 0.058638, 0.092264), (0.04489, 0.060804, -0.072755), (0.031389, 0.058638, -0.07098), (0.052532, 0.051567, -0.073765), (0.035447, 0.061566, -0.085979), (0.045439, 0.055395, -0.091748), (0.032831, 0.055395, -0.10613), (0.025807, 0.061566, -0.096974), (0.015678, 0.055395, -0.114587), (0.012691, 0.061566, -0.103441), (-0.002524, 0.060804, -0.109139), (-0.000748, 0.058638, -0.095639), (-0.003533, 0.051567, -0.116782), (-0.013357, 0.060804, -0.095556), (-0.020165, 0.058638, -0.107348), (-0.030537, 0.060804, -0.092966), (-0.03665, 0.051567, -0.097662), (0.025454, 0.055395, -0.08021), (0.018782, 0.055395, -0.087818), (0.009704, 0.055395, -0.092295), (-0.009501, 0.051567, -0.088878), (-0.019733, 0.058638, -0.084678), (0.087991, 0.058638, 0.114098), (0.078766, 0.061567, 0.105259), (0.024152, 0.058638, 0.105259), (0.0275, 0.05596, 0.115054), (0.078766, 0.055394, 0.093711), (0.024152, 0.051567, 0.09642), (0.032991, 0.060806, 0.100475), (0.105611, 0.055394, -0.008789), (0.077991, 0.060806, -0.002025), (0.077991, 0.051567, -0.009741), (0.105611, 0.061567, 0.002759), (0.077991, 0.058638, 0.011598), (0.111561, 0.061567, 0.015259), (0.099061, 0.058638, 0.011598), (0.142991, 0.055394, -0.116289), (0.079152, 0.051567, -0.11358), (0.087991, 0.060806, -0.109525), (0.14299, 0.061567, -0.10474), (0.079152, 0.058638, -0.104741), (0.139716, 0.061567, -0.092241), (0.127216, 0.058638, -0.095902), (0.0825, 0.05596, -0.094946), (0.091266, 0.061567, 0.092759), (0.118111, 0.061567, -0.009741), (0.15454, 0.055394, -0.104741), (0.092775, 0.060806, 0.105259), (0.09683, 0.051567, 0.114098), (0.15183, 0.051567, -0.11358), (0.068196, 0.05596, -0.002732), (0.068196, 0.05596, 0.00825), (0.260491, 0.051567, -0.104741), (0.252775, 0.060806, -0.104741), (0.197775, 0.060806, 0.105259), (0.205491, 0.051567, 0.105259), (0.241954, 0.060806, -0.099957), (0.184152, 0.058638, 0.105259), (0.198482, 0.05596, 0.115054), (0.1875, 0.05596, 0.115054), (0.235877, 0.058638, -0.092241), (0.232216, 0.061567, -0.104741), (0.192991, 0.058638, -0.095902), (0.247991, 0.058638, -0.11358), (0.192991, 0.051567, -0.117241), (0.192991, 0.060806, -0.109525), (0.183196, 0.05596, -0.110232), (0.183196, 0.05596, -0.09925)]
                        edges = []
                        faces = []
                        for fc in faceVertexCounts:
                            face = []
                            for x in range(fc):
                                single_f = faceVertexIndices.pop(0)
                                face.append(single_f)
                            faces.append(face)

                        logo_mesh = bpy.data.meshes.new('Logo')
                        logo_mesh.from_pydata(points, edges, faces)
                        for f in logo_mesh.polygons:
                            f.use_smooth = True
                        geometriecache['logoonstuds'] = logo_mesh

                    else:
                        logo_mesh = geometriecache['logoonstuds'].copy()
                        logo_mesh.materials.clear()

                    logo_mesh.materials.append(lddmatri.string(None))

                    a = 0
                    for studs in geo.studsFields2D:
                        a += 1
                        if studs.type == 23:
                            for i in range(len(studs.custom2DField)):
                                for j in range(len(studs.custom2DField[0])):
                                    if studs.custom2DField[i][j] in LOGOONSTUDSCONNTYPE: #Valid Connection type which are "allowed" for logo on stud
                                        #logo_transform_matrix = mathutils.Matrix(((studs.matrix.n11, studs.matrix.n21, studs.matrix.n31, studs.matrix.n41),(studs.matrix.n12, studs.matrix.n22, studs.matrix.n32, studs.matrix.n42),(studs.matrix.n13, studs.matrix.n23, studs.matrix.n33, studs.matrix.n43),(studs.matrix.n14, studs.matrix.n24, studs.matrix.n34, studs.matrix.n44)))
                                        logo_obj = bpy.data.objects.new(logo_mesh.name, logo_mesh)
                                        logo_obj.parent = brick_object
                                        col.objects.link(logo_obj)

                                        logo_transform_matrix = mathutils.Matrix(((studs.matrix.n11, studs.matrix.n21, studs.matrix.n31, -1 * studs.matrix.n41 + j * 0.4 - 0.02),(studs.matrix.n12, studs.matrix.n22, studs.matrix.n32, -1 * studs.matrix.n42 + 0.14),(studs.matrix.n13, studs.matrix.n23, studs.matrix.n33, -1 * studs.matrix.n43 + i * 0.4 - 0),(studs.matrix.n14, studs.matrix.n24, studs.matrix.n34, studs.matrix.n44)))
                                        logo_obj.matrix_world = logo_transform_matrix
                                        logo_obj.scale = (0.80, 0.80, 0.80)

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
            #out.write('''def Mesh "GroundPlane_1"'''.format(miny))

        sys.stdout.write('%s\r' % ('                                                                                                 '))
        print("--- %s seconds ---" % (time.time() - start_time))


def setDBFolderVars(dbfolderlocation):
    global PRIMITIVEPATH
    global GEOMETRIEPATH
    global DECORATIONPATH
    global MATERIALNAMESPATH
    PRIMITIVEPATH = dbfolderlocation + '/Primitives/'
    GEOMETRIEPATH = dbfolderlocation + '/Primitives/LOD0/'
    DECORATIONPATH = dbfolderlocation + '/Decorations/'
    MATERIALNAMESPATH = dbfolderlocation + '/MaterialNames/'

def FindDatabase():
    lddliftree = os.getenv('LDDLIFTREE')
    if lddliftree is not None:
        if os.path.isdir(str(lddliftree)): #LDDLIFTREE points to folder
            return str(lddliftree)
        elif os.path.isfile(str(lddliftree)): #LDDLIFTREE points to file (should be db.lif)
            return str(lddliftree)

    else: #Env variable LDDLIFTREE not set. Check for default locations per different platform.
        if platform.system() == 'Darwin':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        elif platform.system() == 'Windows':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        elif platform.system() == 'Linux':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        else:
            print('Your OS {0} is not supported yet.'.format(platform.system()))
            os._exit()

def progress(count, total, status='', suffix = ''):
    bar_len = 40
    filled_len = int(round(bar_len * count / float(total)))
    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write('Progress: [%s] %s%s %s %s\r' % (bar, percents, '%', suffix, '                                                 '))
    sys.stdout.write('Progress: [%s] %s%s %s %s\r' % (bar, percents, '%', suffix, status))
    sys.stdout.flush()

def main():
    print("- - - pylddlib - - -")
    print("          _ ")
    print("         [_]")
    print("       /|   |\\")
    print("      ()'---' C")
    print("        | | |")
    print("        [=|=]")
    print("")
    print("- - - - - - - - - - - -")
    try:
        lxf_filename = sys.argv[1]
        obj_filename = sys.argv[2]
    except Exception as e:
        print("Missing Paramenter:" + sys.argv[0] + " infile.lfx exportname (without extension)")
        return

    converter = Converter()
    if os.path.isdir(FindDatabase()):
        print("Found DB folder. Will use this instead of db.lif!")
        setDBFolderVars(dbfolderlocation = FindDatabase())
        converter.LoadDBFolder(dbfolderlocation = FindDatabase())
        converter.LoadScene(filename=lxf_filename)
        converter.Export(filename=obj_filename)

    elif os.path.isfile(FindDatabase()):
        print("Found db.lif. Will use this.")
        converter.LoadDatabase(databaselocation = FindDatabase())
        converter.LoadScene(filename=lxf_filename)
        converter.Export(filename=obj_filename)
    else:
        print("no LDD database found please install LEGO-Digital-Designer")


def convertldd_data(context, filepath, lddLIFPath, useLogoStuds, useLDDCamera):

    converter = Converter()
    if os.path.isdir(lddLIFPath):
        print("Found DB folder. Will use this instead of db.lif!")
        setDBFolderVars(dbfolderlocation = lddLIFPath)
        converter.LoadDBFolder(dbfolderlocation = lddLIFPath)

    elif os.path.isfile(lddLIFPath):
        print("Found db.lif. Will use this.")
        converter.LoadDatabase(databaselocation = lddLIFPath)

    if (os.path.isdir(lddLIFPath) or os.path.isfile(lddLIFPath)):
        converter.LoadScene(filename=filepath)
        converter.Export(filename=filepath, useLogoStuds=useLogoStuds, useLDDCamera=useLDDCamera)

    else:
        print("no LDD database found please install LEGO-Digital-Designer")

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

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

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    lddLIFPath: StringProperty(
        name="",
        description="Full filepath to the LDD db folder / db.lif file",
        default=FindDatabase(),
    )

    useLogoStuds: BoolProperty(
        name="Show 'LEGO' logo on studs",
        description="Shows the LEGO logo on each stud (at the expense of some extra geometry and import time)",
        default=False,
    )

    useLDDCamera: BoolProperty(
        name="Import camera(s)",
        description="Import camera(s) from LEGO Digital Designer",
        default=False,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        return convertldd_data(context, self.filepath, self.lddLIFPath, self.useLogoStuds, self.useLDDCamera)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportLDDOps.bl_idname, text="LEGO Digital Designer (.lxf/.lxfml)")


def register():
    bpy.utils.register_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.importldd('INVOKE_DEFAULT')
