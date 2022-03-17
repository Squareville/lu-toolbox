[![blender](https://img.shields.io/badge/blender-2.93.7-success)](https://download.blender.org/release/Blender2.93/)
[![gpl](https://img.shields.io/github/license/30350n/lu-toolbox)](https://github.com/30350n/lu-toolbox/blob/master/LICENSE)
# LEGO Universe Toolbox
A Blender Add-on which adds a bunch of useful tools to prepare models for use in LEGO Universe.

## Features

 * Custom LEGO Exchange Format (.lxf/.lxfml) Importer.
 * Automatic model preparation with many useful processes.
 * Custom, helpful workflow for baking materials, lighting, ambient occlusion, alpha, and more to vertex colors.
 * Automatic pathtraced hidden surface removal to clean out model interiors of unseen geometry.
 * Many options and toggles to fit a variety of artist workflows.

<hr>

![banner](images/banner.png)

## Installation

1. Download the latest release from [here](https://github.com/Squareville/lu-toolbox/releases/latest).
2. Start Blender and navigate to "Edit -> Preferences -> Add-ons"
3. (optional) If you already have an older version of the add-on installed, disable it, remove it and restart blender.
4. Hit "Install" and select the zip archive you downloaded.
5. In the Add-on's preferences, set `Brick DB` to your LU client res folder or extracted Brick DB

After installation you can find the add-on in the right sidepanel (N-panel) of the 3D Viewport.

#### Blender Version

The minimum compatible Blender version for LU Toolbox v2.0 is Blender 3.1.

## Documentation

- [DLU - Asset Creation Guide](https://docs.google.com/document/d/15YDtHg3-i3Pn6HTEFkpAjKsvUF6u49ZsQam5b614YRw) by [cdmpants](https://github.com/cdmpants)

### LEGO Exchange Format Importer (.lxf/.lxfml)

This importer is derived from [sttng's ImportLDD Add-on](https://github.com/sttng/ImportLDD) with a few changes:

 * Support for importing one or multiple LODs at a time
 * Enchanced Brick DB handling:
   * Support for defining a path to any Brick DB via Add-on Preferences
   * Direct support for using LU's brick db without needing to extract it manually
     * You can use the `client/res/` folder directly as a Brick DB source
     * the `brickdb.zip` will automatically be unzipped for you if it's not already
 * Dropped support for using LDD's `db.lif` directly since it doesn't provide LODs
 * Consolidated color support for LU's color palette:
   * Colors outside of LU's supported palette will be coerced to the closest color
   * Please report any instances of missing colors so that they can be added
 * Missing data handling:
   * Bricks missing from brick database will be skipped
   * Completely missing colors will be set to black (Color ID 26)
   * Color missing from secondary brick geo files is handled correctly
 * Overwrite Scene Option:
   * Delete all objects and collections from Blender scene before importing.

## Screenshots

<div float="left">
    <img src="images/blender.PNG" width="52.5%" />
    <img src="images/windmill.png" width="35%" />
    <img src="images/castle.png" width="35%" />
    <img src="images/mech.png" width="23.33%" />
</div>
