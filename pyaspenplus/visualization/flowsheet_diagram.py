"""Simple flowsheet diagram renderer using Matplotlib.

Draws blocks as rectangles and streams as arrows, giving a quick visual
overview of the process topology without needing Aspen Plus open.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False

if TYPE_CHECKING:
    from pyaspenplus.models.flowsheet import Flowsheet


def draw_flowsheet(
    flowsheet: "Flowsheet",
    *,
    figsize: tuple[int, int] = (14, 8),
    title: str = "Process Flowsheet",
    save_path: str | None = None,
) -> Any:
    """Render a simple flowsheet diagram from a :class:`Flowsheet`.

    Blocks are arranged left-to-right using a topological sort.
    Streams are drawn as arrows between blocks.

    Returns ``(fig, ax)``.
    """
    if not _MPL_AVAILABLE:
        raise ImportError("matplotlib is required. Install with: pip install matplotlib")

    blocks = flowsheet.blocks
    streams = flowsheet.streams

    # Assign positions: simple left-to-right layout
    positions: dict[str, tuple[float, float]] = {}
    _assign_positions(flowsheet, positions)

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)

    block_w, block_h = 1.8, 0.9

    # Block type -> color
    type_colors = {
        "reactor": "#FF6B6B",
        "heater": "#FFB347",
        "heatx": "#FFB347",
        "mheatx": "#FFB347",
        "flash2": "#77DD77",
        "flash3": "#77DD77",
        "sep": "#77DD77",
        "sep2": "#77DD77",
        "radfrac": "#6B9BD2",
        "dstwu": "#6B9BD2",
        "mixer": "#C4A7E7",
        "fsplit": "#C4A7E7",
        "compr": "#A0D2DB",
        "pump": "#A0D2DB",
    }

    for blk in blocks:
        if blk.name not in positions:
            continue
        x, y = positions[blk.name]

        btype_lower = blk.block_type.lower()
        color = "#D9D9D9"
        for key, c in type_colors.items():
            if key in btype_lower:
                color = c
                break

        rect = mpatches.FancyBboxPatch(
            (x - block_w / 2, y - block_h / 2),
            block_w,
            block_h,
            boxstyle="round,pad=0.1",
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
        )
        ax.add_patch(rect)

        ax.text(x, y + 0.1, blk.name, ha="center", va="center",
                fontsize=10, fontweight="bold")
        ax.text(x, y - 0.2, blk.block_type, ha="center", va="center",
                fontsize=8, color="gray")

    # Draw streams as arrows
    for stream in streams:
        src = stream.source_block
        dst = stream.dest_block
        if src in positions and dst in positions:
            x1, y1 = positions[src]
            x2, y2 = positions[dst]
            ax.annotate(
                "",
                xy=(x2 - block_w / 2 - 0.1, y2),
                xytext=(x1 + block_w / 2 + 0.1, y1),
                arrowprops=dict(
                    arrowstyle="->",
                    color="#333333",
                    lw=1.5,
                    connectionstyle="arc3,rad=0.1",
                ),
            )
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 + 0.3
            ax.text(mid_x, mid_y, stream.name, ha="center", fontsize=8,
                    color="#555555", fontstyle="italic")

    # Feed/product streams without both endpoints
    for stream in streams:
        if stream.source_block and stream.source_block not in positions:
            if stream.dest_block in positions:
                x, y = positions[stream.dest_block]
                ax.annotate(
                    stream.name,
                    xy=(x - block_w / 2 - 0.1, y),
                    xytext=(x - block_w / 2 - 1.5, y),
                    arrowprops=dict(arrowstyle="->", color="green", lw=1.5),
                    fontsize=8,
                    color="green",
                )
        if stream.dest_block and stream.dest_block not in positions:
            if stream.source_block in positions:
                x, y = positions[stream.source_block]
                ax.annotate(
                    stream.name,
                    xy=(x + block_w / 2 + 1.5, y),
                    xytext=(x + block_w / 2 + 0.1, y),
                    arrowprops=dict(arrowstyle="->", color="blue", lw=1.5),
                    fontsize=8,
                    color="blue",
                )

    ax.autoscale()
    margin = 2.0
    ax.set_xlim(ax.get_xlim()[0] - margin, ax.get_xlim()[1] + margin)
    ax.set_ylim(ax.get_ylim()[0] - margin, ax.get_ylim()[1] + margin)
    ax.axis("off")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight")

    return fig, ax


def _assign_positions(flowsheet: "Flowsheet", positions: dict[str, tuple[float, float]]) -> None:
    """Assign 2D positions via a simple layered layout (topological ordering)."""
    blocks = flowsheet.blocks
    if not blocks:
        return

    # Build adjacency from outlet->inlet connectivity
    name_to_idx = {b.name: i for i, b in enumerate(blocks)}
    in_degree = {b.name: 0 for b in blocks}
    adj: dict[str, list[str]] = {b.name: [] for b in blocks}

    for b in blocks:
        for outlet_name in b.outlet_streams:
            for other in blocks:
                if outlet_name in other.inlet_streams and other.name != b.name:
                    adj[b.name].append(other.name)
                    in_degree[other.name] += 1

    # Kahn's algorithm for topological layers
    layers: list[list[str]] = []
    queue = [name for name, deg in in_degree.items() if deg == 0]

    visited: set[str] = set()
    while queue:
        layers.append(list(queue))
        visited.update(queue)
        next_queue: list[str] = []
        for node in queue:
            for neighbour in adj[node]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0 and neighbour not in visited:
                    next_queue.append(neighbour)
        queue = next_queue

    # Place any remaining (cyclic) blocks in the last layer
    remaining = [b.name for b in blocks if b.name not in visited]
    if remaining:
        layers.append(remaining)

    x_spacing, y_spacing = 3.5, 2.0
    for col, layer in enumerate(layers):
        for row, name in enumerate(layer):
            y_offset = -(len(layer) - 1) / 2 * y_spacing + row * y_spacing
            positions[name] = (col * x_spacing, y_offset)
