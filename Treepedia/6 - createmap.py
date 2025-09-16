import geopandas as gpd
import folium
import branca.colormap as cm
import matplotlib.pyplot as plt
import numpy as np
import base64
from io import BytesIO

# Load shapefile
gdf = gpd.read_file(r"C:\Users\alana\PycharmProjects\Treepedia_Public\Treepedia\spatial-data\GreenViewRes.shp")

# Convert CRS to WGS84 (lat/lon) if needed
if gdf.crs and gdf.crs.to_epsg() != 4326:
    gdf = gdf.to_crs(epsg=4326)

# Centre map
m = folium.Map(location=[-33.8688, 151.2093], zoom_start=15, tiles="cartodbpositron")

# Stats
avg_gvi = gdf["greenView"].mean()
med_gvi = gdf["greenView"].median()
values = gdf["greenView"].dropna()

# Colormap
colormap = cm.linear.RdYlGn_11.scale(values.min(), values.max())
colormap.caption = "Green View Index"
colormap.position = "bottomright"  # keep legend away from summary box
colormap.add_to(m)

# Add points
for _, row in gdf.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=4,
        color=None,
        fill=True,
        fill_opacity=0.7,
        fill_color=colormap(row.greenView),
        popup=f"GVI: {row.greenView:.2f}"
    ).add_to(m)

# --- Gradient histogram ---
fig, ax = plt.subplots(figsize=(4.5, 2.5))
n, bins, patches = ax.hist(values, bins=30, edgecolor="black")

bin_centers = 0.5 * (bins[:-1] + bins[1:])
for c, p in zip(bin_centers, patches):
    p.set_facecolor(colormap(c))

ax.axvline(avg_gvi, color="blue", linestyle="--", linewidth=2, label=f"Mean {avg_gvi:.1f}%")
ax.axvline(med_gvi, color="purple", linestyle=":", linewidth=2, label=f"Median {med_gvi:.1f}%")

ax.set_xlabel("Green View Index (%)")
ax.set_ylabel("Frequency")
ax.legend(fontsize=8)

buf = BytesIO()
plt.tight_layout()
plt.savefig(buf, format="png", dpi=100)
plt.close(fig)
hist_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

# Dynamic color for % value
gvi_color = colormap(avg_gvi)

# --- Floating summary box (top-left, pinned) ---
summary_html = f"""
<div style="position: fixed;
            top: 20px; left: 50px; width: 280px; max-width: 280px;
            background-color: white; border:2px solid black; z-index:9999;
            font-size:14px; padding: 13px; box-shadow: 3px 3px 8px rgba(0,0,0,0.4);">
<b style="font-size:14px;">🌳 Sydney CBD Green View Index</b><br>
<span style="font-size:30px; color:{gvi_color};"><b>{avg_gvi:.1f}%</b></span><br><br>
<img src="data:image/png;base64,{hist_base64}" width="100%">
</div>
"""
m.get_root().html.add_child(folium.Element(summary_html))

# Save map
m.save("Sydney_GVI.html")

print("Average GVI:", avg_gvi)
print("Median GVI:", med_gvi)



