# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pywidget",
#     "anywidget",
#     "marimo>=0.20.4",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Heat Index Forecast

    A small `pywidget` example inspired by the New York Times heat-index graphic.

    Type a city and press **Enter** to load a new forecast. This version stays
    focused on three teaching ideas: synced traitlets, browser-side API calls,
    and hand-built SVG.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import traitlets
    from pywidget import PyWidget

    return PyWidget, mo, traitlets


@app.cell
def _(PyWidget, mo, traitlets):
    class HeatIndexWidget(PyWidget):
        latitude = traitlets.Float(34.0522).tag(sync=True)
        longitude = traitlets.Float(-118.2437).tag(sync=True)
        location_name = traitlets.Unicode("Los Angeles, Calif.").tag(sync=True)

        async def render(self, el, model):
            import datetime as dt
            import json
            from urllib.parse import quote

            from pyodide.http import pyfetch  # pyright: ignore[reportMissingImports]

            width, height = 760, 420
            left, top = 56, 18
            plot_width, plot_height = 684, 330
            y_min, y_max = 40.0, 130.0

            def escape_html(text):
                return (
                    str(text)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )

            def format_temp(temp):
                return f"{int(round(temp))}\N{DEGREE SIGN}"

            def scale_y(temp):
                return top + plot_height - ((temp - y_min) / (y_max - y_min)) * plot_height

            def set_status(message):
                status = el.querySelector("#status")
                if status:
                    status.textContent = message

            async def fetch_forecast(lat, lon):
                url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}"
                    f"&longitude={lon}"
                    "&hourly=apparent_temperature"
                    "&temperature_unit=fahrenheit"
                    "&forecast_days=7"
                    "&timezone=auto"
                )
                response = await pyfetch(url)
                if not response.ok:
                    raise RuntimeError(f"Forecast request failed ({response.status})")
                return json.loads(await response.string())

            async def search_city(query):
                url = (
                    "https://geocoding-api.open-meteo.com/v1/search"
                    f"?name={quote(query)}"
                    "&count=1"
                    "&language=en"
                    "&format=json"
                )
                response = await pyfetch(url)
                if not response.ok:
                    raise RuntimeError(f"Search request failed ({response.status})")
                payload = json.loads(await response.string())
                results = payload.get("results", [])
                if not results:
                    raise RuntimeError("No matching city found")
                return results[0]

            def build_chart(forecast, location_name):
                hourly = forecast.get("hourly", {})
                times = hourly.get("time", [])
                temps = hourly.get("apparent_temperature", [])

                if not times or not temps:
                    return '<div class="empty">No forecast data available.</div>'

                samples = []
                days = []
                for index, (time_str, temp) in enumerate(zip(times, temps)):
                    day = dt.datetime.fromisoformat(time_str).date().isoformat()
                    if not days or days[-1]["date"] != day:
                        if len(days) == 7:
                            break
                        days.append({"date": day, "items": []})
                    item = {"index": index, "date": day, "temp": float(temp)}
                    days[-1]["items"].append(item)
                    samples.append(item)

                if not samples:
                    return '<div class="empty">No forecast data available.</div>'

                max_index = max(samples[-1]["index"], 1)

                def scale_x(index):
                    return left + (index / max_index) * plot_width

                polyline = " ".join(
                    f"{scale_x(item['index']):.2f},{scale_y(item['temp']):.2f}"
                    for item in samples
                )

                bands = "".join(
                    (
                        f'<rect x="{left}" y="{scale_y(high):.2f}" width="{plot_width}" '
                        f'height="{(scale_y(low) - scale_y(high)):.2f}" fill="{color}" />'
                        f'<text x="{left + 10}" y="{scale_y(high) + 18:.2f}" class="band">{label}</text>'
                    )
                    for label, low, high, color in [
                        ("CAUTION", 80.0, 90.0, "#f5ecc8"),
                        ("EXTREME CAUTION", 90.0, 103.0, "#f3dfab"),
                        ("DANGER", 103.0, 130.0, "#edc0aa"),
                    ]
                )
                grid = "".join(
                    f'<line x1="{left}" y1="{scale_y(tick):.2f}" x2="{left + plot_width}" '
                    f'y2="{scale_y(tick):.2f}" class="grid" />'
                    for tick in (40.0, 60.0, 80.0, 100.0, 120.0)
                )
                y_labels = "".join(
                    f'<text x="{left - 8}" y="{scale_y(tick) + 4:.2f}" class="axis">{format_temp(tick)}</text>'
                    for tick in (40.0, 60.0, 80.0, 100.0, 120.0)
                )

                day_lines = []
                day_labels = []
                temp_labels = []
                for day in days:
                    items = day["items"]
                    start_x = scale_x(items[0]["index"])
                    end_x = scale_x(items[-1]["index"])
                    center_x = (start_x + end_x) / 2
                    day_lines.append(
                        f'<line x1="{start_x:.2f}" y1="{top}" x2="{start_x:.2f}" y2="{top + plot_height}" class="grid" />'
                    )
                    day_name = dt.date.fromisoformat(day["date"]).strftime("%a.")[:4]
                    day_labels.append(
                        f'<text x="{center_x:.2f}" y="{height - 12}" class="day">{day_name}</text>'
                    )
                    for item, offset in (
                        (max(items, key=lambda sample: sample["temp"]), -12),
                        (min(items, key=lambda sample: sample["temp"]), 20),
                    ):
                        x = scale_x(item["index"])
                        y = scale_y(item["temp"])
                        temp_labels.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" class="dot" />')
                        temp_labels.append(
                            f'<text x="{x:.2f}" y="{y + offset:.2f}" class="value">{format_temp(item["temp"])}</text>'
                        )

                day_lines.append(
                    f'<line x1="{left + plot_width:.2f}" y1="{top}" x2="{left + plot_width:.2f}" y2="{top + plot_height}" class="grid" />'
                )

                return f"""
                <svg viewBox="0 0 {width} {height}" class="chart-svg" aria-label="Heat index forecast for {escape_html(location_name)}">
                    {bands}
                    {grid}
                    {''.join(day_lines)}
                    <polyline points="{polyline}" class="line" />
                    {''.join(temp_labels)}
                    {y_labels}
                    {''.join(day_labels)}
                </svg>
                """

            async def load_forecast():
                set_status("Loading forecast...")
                forecast = await fetch_forecast(model.get("latitude"), model.get("longitude"))
                chart = el.querySelector("#chart")
                if chart:
                    chart.innerHTML = build_chart(forecast, model.get("location_name"))
                set_status("")

            async def search_and_reload(query):
                query = query.strip()
                if not query:
                    return
                set_status("Searching...")
                try:
                    result = await search_city(query)
                    model.set("latitude", float(result["latitude"]))
                    model.set("longitude", float(result["longitude"]))
                    model.set(
                        "location_name",
                        ", ".join(
                            part
                            for part in (
                                result.get("name", query),
                                result.get("admin1") or result.get("country_code") or "",
                            )
                            if part
                        ),
                    )
                    model.save_changes()
                    await load_forecast()
                except Exception as err:
                    set_status(str(err))

            el.innerHTML = f"""
            <style>
                .heat-index {{ font-family: system-ui, sans-serif; color: #1d1d1d; max-width: 760px; }}
                .heat-index h2 {{ font: 22px Georgia, serif; margin: 0 0 12px; }}
                .search {{ width: 100%; box-sizing: border-box; border: 1px solid #d0d0d0; border-radius: 12px; padding: 14px 16px; font-size: 18px; }}
                .hint, .meta {{ font-size: 12px; color: #777; }}
                .chart {{ min-height: 420px; margin: 10px 0; }}
                .chart-svg {{ width: 100%; display: block; }}
                .grid {{ stroke: #d8d1c2; stroke-dasharray: 1.5 3; stroke-width: 1; }}
                .line {{ fill: none; stroke: #555; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }}
                .dot {{ fill: #555; stroke: white; stroke-width: 1.5; }}
                .value {{ font-size: 14px; text-anchor: middle; fill: #4f4f4f; }}
                .band {{ font-size: 10px; letter-spacing: 0.08em; fill: #8e7867; }}
                .axis {{ font-size: 11px; text-anchor: end; fill: #9a9a9a; }}
                .day {{ font-size: 12px; text-anchor: middle; fill: #888; }}
                .empty {{ min-height: 360px; display: flex; align-items: center; justify-content: center; color: #777; }}
            </style>
            <div class="heat-index">
                <h2>Heat index forecast for...</h2>
                <input
                    id="search"
                    class="search"
                    type="text"
                    value="{escape_html(model.get('location_name'))}"
                    placeholder="Type a city and press Enter"
                />
                <div class="hint">Tip: try Phoenix, Miami, or Las Vegas.</div>
                <div id="chart" class="chart"></div>
                <div class="meta">
                    <div>Source: Open-Meteo apparent temperature data and NOAA heat-risk thresholds.</div>
                    <div id="status"></div>
                </div>
            </div>
            """

            search_input = el.querySelector("#search")

            def on_keydown(event):
                if event.key == "Enter":
                    event.preventDefault()
                    import asyncio

                    asyncio.ensure_future(search_and_reload(event.target.value))

            search_input.addEventListener("keydown", create_proxy(on_keydown))

            try:
                await load_forecast()
            except Exception as err:
                chart = el.querySelector("#chart")
                if chart:
                    chart.innerHTML = f'<div class="empty">{escape_html(err)}</div>'

        async def update(self, el, model):
            await render(el, model)  # pyright: ignore[reportUndefinedVariable]

    widget = mo.ui.anywidget(HeatIndexWidget())
    widget
    return


if __name__ == "__main__":
    app.run()
