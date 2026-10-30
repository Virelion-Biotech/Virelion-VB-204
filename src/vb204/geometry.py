"""Layer 1: parameterized design-space manifests; not a mesh generator."""
from __future__ import annotations
from typing import Any
from .plan import load_program

GEOMETRY_FIELDS = {"thickness_mm", "alignment", "cell_density_per_mm3", "matrix_stiffness_kpa", "vascular_void_fraction", "interface_contact_area_mm2"}

def validate_geometry_spec(architecture: str, parameters: dict[str, Any]) -> dict[str, Any]:
    arch = next((a for a in load_program()["architectures"] if a["id"] == architecture), None)
    if arch is None:
        raise ValueError(f"Unknown architecture {architecture!r}; expected A, B, C or D")
    unknown = set(parameters) - GEOMETRY_FIELDS
    if unknown:
        raise ValueError(f"Unknown geometry fields: {', '.join(sorted(unknown))}")
    required = {"thickness_mm", "alignment", "cell_density_per_mm3", "vascular_void_fraction", "interface_contact_area_mm2"}
    if architecture in {"B", "C", "D"}:
        required.add("matrix_stiffness_kpa")
    missing = required - set(parameters)
    if missing:
        raise ValueError("Geometry specification is incomplete; missing: " + ", ".join(sorted(missing)))
    for key in required - {"alignment"}:
        value = parameters[key]
        if value is None or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a sourced numeric value")
        if value < 0:
            raise ValueError(f"{key} must be non-negative")
    if parameters["thickness_mm"] <= 0 or parameters["cell_density_per_mm3"] <= 0 or parameters["interface_contact_area_mm2"] <= 0:
        raise ValueError("thickness, cell density and interface contact area must be positive")
    if not 0 <= parameters["vascular_void_fraction"] < 1:
        raise ValueError("vascular_void_fraction must be in [0, 1)")
    if parameters["alignment"] not in {"isotropic", "anisotropic"}:
        raise ValueError("alignment must be 'isotropic' or 'anisotropic'")
    return {
        "schema_version": "vb204-geometry-spec-v1",
        "architecture": architecture,
        "architecture_name": arch["name"],
        "parameters": dict(parameters),
        "provenance_required": True,
        "geometry_status": "PARAMETER_SPEC_ONLY_MESH_NOT_GENERATED",
        "warning": "Every numerical value must have source, species, units and uncertainty in the run manifest. This function does not generate anatomical meshes."
    }
