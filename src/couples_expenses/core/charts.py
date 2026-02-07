"""Canvas-based chart drawing helpers for Toga Canvas widgets."""

import math


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def draw_pie_chart(
    canvas,
    data: dict[str, int],
    color_map: dict[str, str],
    width: int,
    height: int,
) -> None:
    """Draw a pie chart on a Toga Canvas.

    data: label -> value (cents).
    color_map: label -> hex colour.
    """
    canvas.clear()
    total = sum(data.values())

    if total == 0:
        with canvas.Fill(color="#333333") as fill_ctx:
            fill_ctx.write_text("No data", x=width // 2 - 30, y=height // 2)
        return

    cx, cy = width // 2, height // 2
    radius = min(cx, cy) - 30
    start_angle = 0.0
    legend_y = 10

    for label, value in data.items():
        sweep = (value / total) * 2 * math.pi
        end_angle = start_angle + sweep

        r, g, b = _hex_to_rgb(color_map.get(label, "#999999"))

        # Draw pie slice
        with canvas.Fill(color=f"rgb({r},{g},{b})") as fill_ctx:
            fill_ctx.move_to(cx, cy)
            # Approximate arc with line segments
            steps = max(int(sweep / 0.05), 4)
            for i in range(steps + 1):
                angle = start_angle + sweep * i / steps
                px = cx + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                fill_ctx.line_to(px, py)
            fill_ctx.line_to(cx, cy)

        # Legend entry
        with canvas.Fill(color=f"rgb({r},{g},{b})") as fill_ctx:
            fill_ctx.rect(width - 140, legend_y, 12, 12)
        with canvas.Fill(color="#333333") as fill_ctx:
            pct = value / total * 100
            fill_ctx.write_text(
                f"{label} ({pct:.0f}%)", x=width - 122, y=legend_y + 11
            )
        legend_y += 20

        start_angle = end_angle


def draw_bar_chart(
    canvas,
    data: dict[str, int],
    color_map: dict[str, str],
    width: int,
    height: int,
) -> None:
    """Draw a simple vertical bar chart on a Toga Canvas."""
    canvas.clear()
    total = sum(data.values())

    if total == 0:
        with canvas.Fill(color="#333333") as fill_ctx:
            fill_ctx.write_text("No data", x=width // 2 - 30, y=height // 2)
        return

    max_val = max(data.values()) if data else 1
    n = len(data)
    if n == 0:
        return

    margin_left = 20
    margin_bottom = 40
    margin_top = 20
    bar_area_w = width - margin_left - 20
    bar_area_h = height - margin_top - margin_bottom
    bar_w = max(bar_area_w // (n * 2), 20)
    gap = (bar_area_w - bar_w * n) // (n + 1) if n > 0 else 0

    x = margin_left + gap
    for label, value in data.items():
        bar_h = int((value / max_val) * bar_area_h) if max_val > 0 else 0
        y = margin_top + bar_area_h - bar_h

        r, g, b = _hex_to_rgb(color_map.get(label, "#999999"))
        with canvas.Fill(color=f"rgb({r},{g},{b})") as fill_ctx:
            fill_ctx.rect(x, y, bar_w, bar_h)

        # Amount above bar
        with canvas.Fill(color="#333333") as fill_ctx:
            fill_ctx.write_text(
                f"\u20aa{value / 100:.0f}", x=x, y=y - 5
            )

        # Label below bar
        with canvas.Fill(color="#333333") as fill_ctx:
            fill_ctx.write_text(label, x=x, y=height - margin_bottom + 15)

        x += bar_w + gap
