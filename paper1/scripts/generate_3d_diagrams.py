import os
import numpy as np
import plotly.graph_objects as go
import yaml

with open('config/parameters.yaml', 'r') as f:
    config = yaml.safe_load(f)

L = config['module_a']['geometry']['L']['value']
dm = config['module_a']['geometry']['dm']['value']
dw = config['module_a']['geometry']['dm']['value'] * 4 # Just for visual 
tm = config['module_a']['geometry']['tm']['value']

os.makedirs('figures', exist_ok=True)

# 2D Cross Section
fig = go.Figure()

# Outer Wall
theta = np.linspace(0, 2*np.pi, 100)
x_wall = dw/2 * np.cos(theta)
y_wall = dw/2 * np.sin(theta)
fig.add_trace(go.Scatter(x=x_wall, y=y_wall, mode='lines', line=dict(color='gray', width=4), name='Outer Wall', fill='toself', fillcolor='rgba(200,200,200,0.2)'))

# Membrane
x_mem = dm/2 * np.cos(theta)
y_mem = dm/2 * np.sin(theta)
fig.add_trace(go.Scatter(x=x_mem, y=y_mem, mode='lines', line=dict(color='blue', width=4), name='Membrane', fill='toself', fillcolor='rgba(100,150,255,0.4)'))

# Catalyst (scatter points in annulus)
r_cat = np.random.uniform(dm/2, dw/2, 500)
theta_cat = np.random.uniform(0, 2*np.pi, 500)
x_cat = r_cat * np.cos(theta_cat)
y_cat = r_cat * np.sin(theta_cat)
fig.add_trace(go.Scatter(x=x_cat, y=y_cat, mode='markers', marker=dict(color='green', size=3, opacity=0.6), name='Catalyst Pellets'))

fig.update_layout(
    title='2D Cross Section (Module A & B)',
    xaxis=dict(scaleanchor="y", scaleratio=1, showgrid=False, zeroline=False),
    yaxis=dict(showgrid=False, zeroline=False),
    template='plotly_white'
)
fig.write_image("figures/2d_cross_section.png")
fig.write_html("figures/2d_cross_section.html")

# 3D Diagram (Cutaway)
fig3 = go.Figure()

z_mesh = np.linspace(0, L, 50)
theta_mesh = np.linspace(0, np.pi, 30) # Only half cylinder for cutaway
Z, Theta = np.meshgrid(z_mesh, theta_mesh)

# Radial exaggeration for visibility
R_wall = (dw/2) * 5
R_mem = (dm/2) * 5

X_wall = R_wall * np.cos(Theta)
Y_wall = R_wall * np.sin(Theta)

X_mem = R_mem * np.cos(Theta)
Y_mem = R_mem * np.sin(Theta)

# Membrane layer
fig3.add_trace(go.Surface(x=Z, y=X_mem, z=Y_mem, colorscale='Blues', opacity=0.8, showscale=False, name="Zeolite Membrane"))

# Wall layer
fig3.add_trace(go.Surface(x=Z, y=X_wall, z=Y_wall, colorscale='Greys', opacity=0.3, showscale=False, name="Outer Wall"))

# Arrows
fig3.add_trace(go.Scatter3d(
    x=[-0.05, 0], y=[R_wall/2, R_wall/2], z=[0, 0],
    mode='lines+text', line=dict(color='red', width=5),
    text=["Feed In", ""], textposition="middle left"
))
fig3.add_trace(go.Scatter3d(
    x=[L+0.05, L], y=[0, 0], z=[0, 0],
    mode='lines+text', line=dict(color='blue', width=5),
    text=["Sweep In", ""], textposition="middle right"
))

fig3.update_layout(
    title="3D Reactor Cutaway (Radial Scale Exaggerated)",
    scene=dict(
        xaxis_title="Length (m)",
        yaxis_title="Radius (m)",
        zaxis_title="Radius (m)",
        aspectmode="data"
    ),
    template="plotly_white"
)
fig3.write_image("figures/3d_cutaway.png")
fig3.write_html("figures/3d_cutaway.html")

print("Generated figures.")
