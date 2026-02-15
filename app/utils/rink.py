import math

import plotly.graph_objects as go

# NHL rink dimensions (feet)
RINK_LENGTH = 200  # x: -100 to 100
RINK_WIDTH = 85  # y: -42.5 to 42.5
CORNER_RADIUS = 28

# Line positions
CENTER_LINE_X = 0
BLUE_LINE_X = 25
GOAL_LINE_X = 89

# Circle/dot positions
FACEOFF_CIRCLE_RADIUS = 15
CENTER_CIRCLE_RADIUS = 15
OZ_FACEOFF_X = 69
OZ_FACEOFF_Y = 22
NZ_FACEOFF_X = 20
NZ_FACEOFF_Y = 22

# Colors
ICE_COLOR = "#f0f5ff"
RED_LINE = "#c8102e"
BLUE_LINE = "#0033a0"
BOARD_COLOR = "#333333"
CREASE_COLOR = "#add8e6"


def _board_y_at(x):
    """Return the max y (half-width) of the rink at a given x coordinate.

    In the straight sections the width is RINK_WIDTH/2. In the corners,
    compute from the corner arc geometry.
    """
    half_l = RINK_LENGTH / 2
    half_w = RINK_WIDTH / 2
    r = CORNER_RADIUS
    corner_x = half_l - r  # x where the corner arc center sits

    abs_x = abs(x)
    if abs_x <= corner_x:
        return half_w
    # Inside the corner arc region
    dx = abs_x - corner_x
    if dx >= r:
        return half_w - r  # at the very end
    return (half_w - r) + math.sqrt(r * r - dx * dx)


def _arc_points(cx, cy, r, start_deg, end_deg, n=30):
    """Generate points along a circular arc."""
    angles = [
        math.radians(start_deg + (end_deg - start_deg) * i / n) for i in range(n + 1)
    ]
    xs = [cx + r * math.cos(a) for a in angles]
    ys = [cy + r * math.sin(a) for a in angles]
    return xs, ys


def _circle_points(cx, cy, r, n=60):
    """Generate points for a full circle."""
    return _arc_points(cx, cy, r, 0, 360, n)


def _rink_outline():
    """Build the rounded-rectangle rink boundary."""
    half_l = RINK_LENGTH / 2  # 100
    half_w = RINK_WIDTH / 2  # 42.5
    r = CORNER_RADIUS

    xs, ys = [], []

    # Bottom-right corner arc (270 -> 360)
    ax, ay = _arc_points(half_l - r, -(half_w - r), r, 270, 360)
    xs.extend(ax)
    ys.extend(ay)

    # Top-right corner arc (0 -> 90)
    ax, ay = _arc_points(half_l - r, half_w - r, r, 0, 90)
    xs.extend(ax)
    ys.extend(ay)

    # Top-left corner arc (90 -> 180)
    ax, ay = _arc_points(-(half_l - r), half_w - r, r, 90, 180)
    xs.extend(ax)
    ys.extend(ay)

    # Bottom-left corner arc (180 -> 270)
    ax, ay = _arc_points(-(half_l - r), -(half_w - r), r, 180, 270)
    xs.extend(ax)
    ys.extend(ay)

    # Close the shape
    xs.append(xs[0])
    ys.append(ys[0])

    return xs, ys


def _crease_points(cx, side=1):
    """Build NHL-style goal crease. side=1 for right net, side=-1 for left net.

    Shape: flat 8ft edge on goal line, straight sides extending 4.5ft out,
    then a top arc connecting the two sides.
    """
    gx = cx * side
    half_w = 4.0  # 4ft each side of center on goal line
    straight = 4.5  # straight sides extend 4.5ft from goal line
    top_r = 6.0  # radius of the large top arc

    if side == 1:
        d = -1  # crease extends in -x direction (toward center ice)
    else:
        d = 1  # crease extends in +x direction (toward center ice)

    xs, ys = [], []

    # Start at goal line, bottom side
    xs.append(gx)
    ys.append(-half_w)

    # Straight side out
    xs.append(gx + d * straight)
    ys.append(-half_w)

    # Top arc connecting the two straight sides
    # Center the arc on the goal line so total depth = top_r (6ft)
    arc_cx = gx
    half_angle = math.degrees(math.asin(half_w / top_r))
    if side == 1:
        ax, ay = _arc_points(arc_cx, 0, top_r, 180 + half_angle, 180 - half_angle, n=30)
    else:
        ax, ay = _arc_points(arc_cx, 0, top_r, -half_angle, half_angle, n=30)
    xs.extend(ax)
    ys.extend(ay)

    # Straight side back to goal line
    xs.append(gx + d * straight)
    ys.append(half_w)

    # Back to goal line, top side
    xs.append(gx)
    ys.append(half_w)

    # Close
    xs.append(xs[0])
    ys.append(ys[0])
    return xs, ys


def create_rink_figure(center_logo_url=None):
    """Create a Plotly figure of an NHL hockey rink (bird's-eye view).

    Parameters
    ----------
    center_logo_url : str, optional
        URL for a team logo to display at center ice.
    """
    fig = go.Figure()

    half_w = RINK_WIDTH / 2

    # --- Ice surface (filled rink outline) ---
    ox, oy = _rink_outline()
    fig.add_trace(
        go.Scatter(
            x=ox,
            y=oy,
            fill="toself",
            fillcolor=ICE_COLOR,
            line=dict(color=BOARD_COLOR, width=3),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --- Center line (red) ---
    fig.add_shape(
        type="line",
        x0=CENTER_LINE_X,
        y0=-half_w,
        x1=CENTER_LINE_X,
        y1=half_w,
        line=dict(color=RED_LINE, width=3),
    )

    # --- Blue lines ---
    for x in [BLUE_LINE_X, -BLUE_LINE_X]:
        fig.add_shape(
            type="line",
            x0=x,
            y0=-half_w,
            x1=x,
            y1=half_w,
            line=dict(color=BLUE_LINE, width=3),
        )

    # --- Goal lines (red, clipped to boards) ---
    for x in [GOAL_LINE_X, -GOAL_LINE_X]:
        board_y = _board_y_at(x)
        fig.add_shape(
            type="line",
            x0=x,
            y0=-board_y,
            x1=x,
            y1=board_y,
            line=dict(color=RED_LINE, width=2),
        )

    # --- Center ice circle ---
    cx_pts, cy_pts = _circle_points(0, 0, CENTER_CIRCLE_RADIUS)
    fig.add_trace(
        go.Scatter(
            x=cx_pts,
            y=cy_pts,
            mode="lines",
            line=dict(color=BLUE_LINE, width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --- Center ice dot ---
    fig.add_trace(
        go.Scatter(
            x=[0],
            y=[0],
            mode="markers",
            marker=dict(size=8, color=BLUE_LINE),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --- Faceoff circles (offensive/defensive zones) ---
    for fx in [OZ_FACEOFF_X, -OZ_FACEOFF_X]:
        for fy in [OZ_FACEOFF_Y, -OZ_FACEOFF_Y]:
            fc_x, fc_y = _circle_points(fx, fy, FACEOFF_CIRCLE_RADIUS)
            fig.add_trace(
                go.Scatter(
                    x=fc_x,
                    y=fc_y,
                    mode="lines",
                    line=dict(color=RED_LINE, width=1.5),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    # --- Faceoff dots ---
    # Center dot already added above
    # Offensive/defensive zone dots
    dot_xs, dot_ys = [], []
    for fx in [OZ_FACEOFF_X, -OZ_FACEOFF_X]:
        for fy in [OZ_FACEOFF_Y, -OZ_FACEOFF_Y]:
            dot_xs.append(fx)
            dot_ys.append(fy)
    # Neutral zone dots
    for fx in [NZ_FACEOFF_X, -NZ_FACEOFF_X]:
        for fy in [NZ_FACEOFF_Y, -NZ_FACEOFF_Y]:
            dot_xs.append(fx)
            dot_ys.append(fy)
    fig.add_trace(
        go.Scatter(
            x=dot_xs,
            y=dot_ys,
            mode="markers",
            marker=dict(size=6, color=RED_LINE),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # --- Goal creases ---
    for side in [1, -1]:
        crx, cry = _crease_points(GOAL_LINE_X, side)
        fig.add_trace(
            go.Scatter(
                x=crx,
                y=cry,
                fill="toself",
                fillcolor=CREASE_COLOR,
                line=dict(color=RED_LINE, width=1.5),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # --- Trapezoids behind nets ---
    for side in [1, -1]:
        gx = GOAL_LINE_X * side
        bx = 100 * side
        # Trapezoid: wider at boards, narrower at goal line
        trap_narrow = 11  # half-width at goal line
        trap_wide = 14  # half-width at boards (approximate)
        trap_x = [gx, bx, bx, gx, gx]
        trap_y = [trap_narrow, trap_wide, -trap_wide, -trap_narrow, trap_narrow]
        fig.add_shape(
            type="path",
            path=f"M {trap_x[0]},{trap_y[0]} L {trap_x[1]},{trap_y[1]} "
            f"L {trap_x[2]},{trap_y[2]} L {trap_x[3]},{trap_y[3]} Z",
            line=dict(color=RED_LINE, width=1.5),
        )

    # --- Center-ice logo ---
    if center_logo_url:
        fig.add_layout_image(
            source=center_logo_url,
            xref="x",
            yref="y",
            x=0,
            y=0,
            xanchor="center",
            yanchor="middle",
            sizex=22,
            sizey=22,
            opacity=0.3,
            layer="above",
        )

    # --- Layout ---
    fig.update_layout(
        xaxis=dict(
            range=[-105, 105],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            range=[-47, 47],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=150, t=10, b=10),
        height=400,
        legend=dict(
            x=1.02,
            y=1,
            xanchor="left",
            yanchor="top",
        ),
    )

    return fig
