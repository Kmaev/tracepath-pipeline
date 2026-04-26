import json
import os
from collections import defaultdict
from typing import Any

from pxr import Usd, UsdGeom, Sdf, Ar


# USD Scene Initialization From Template
def configure_xform(prim: Usd.Prim, kind: str | None = None) -> UsdGeom.Xform:
    """
    Configure an Xform prim, if kind set kind and asset name.

    Returns:
        UsdGeom.Xform
    """
    xform = UsdGeom.Xform(prim)
    if kind:
        model_api = Usd.ModelAPI(xform)
        model_api.SetKind(kind)
        model_api.SetAssetName(prim.GetName())

    return xform


def create_prim(stage: Usd.Stage, parent_path: str, prim: dict[str, Any]) -> None:
    """Create a prim and its children on the stage from dictionary template"""
    path = f"{parent_path}/{prim['name']}"
    prim_type = prim["type"]
    prim_kind = prim.get("kind")

    usd_prim = stage.DefinePrim(path, prim_type)

    if usd_prim.IsA(UsdGeom.Xform):
        configure_xform(usd_prim, prim_kind)

    for child in prim.get("children", []):
        create_prim(stage, path, child)


def create_scene_from_json(template_path: str, stage_output_path: str) -> None:
    """Create a USD stage from a JSON template and save it."""
    with open(template_path, "r") as f:
        root_prim = json.load(f)

    stage = Usd.Stage.CreateNew(stage_output_path)
    create_prim(stage, "", root_prim)
    stage.GetRootLayer().Save()


# TraceReset Helper Function to preview USD stage layer composition
def find_usd_layer(usd_file_path: str) -> Sdf.Layer:
    """
    Open and return a USD layer from the given file path.

    Returns:
        Sdf.Layer
    """
    if not os.path.isfile(usd_file_path):
        raise FileNotFoundError(f"USD file not found: {usd_file_path}")

    layer = Sdf.Layer.FindOrOpen(usd_file_path)
    if layer is None:
        raise RuntimeError(f"Failed to open USD layer: {usd_file_path}")
    return layer


def walk_layer_stack(layer: Sdf.Layer, visited=None, composition_graph=None) -> defaultdict[str: list[str]]:
    """
    Traverse the sublayer stack and build a composition graph.

    Returns:
        defaultdict[str: list[str]]: Composition graph representing parent → child layer relationships.
    """
    if visited is None:
        visited = set()

    if composition_graph is None:
        composition_graph = defaultdict(list)
    layer_id = layer.identifier

    if layer_id in visited:
        return composition_graph

    visited.add(layer_id)

    resolver = Ar.GetResolver()
    ctx = resolver.CreateDefaultContextForAsset(layer.resolvedPath)

    with Ar.ResolverContextBinder(ctx):
        for sublayer_path in layer.subLayerPaths:
            identifier = resolver.CreateIdentifier(
                sublayer_path,
                layer.resolvedPath
            )
            resolved = resolver.Resolve(identifier)

            if not resolved:
                continue

            sublayer = Sdf.Layer.FindOrOpen(resolved)
            if not sublayer:
                continue

            composition_graph[layer_id].append(sublayer.identifier)

            walk_layer_stack(sublayer, visited, composition_graph)
    return composition_graph
