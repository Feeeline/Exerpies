import json
import os

from exerpy import ExergyAnalysis

model_path = r'C:\Users\Felin\Documents\Masterthesis\Code\Exerpy\exerpy\examples\asu_aspen\Doppelkolonne.bkp'

ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

# Discover power connections in the parsed model and use them for the test.
# Some Aspen files name power flows differently, so we pick available 'power' connections dynamically.
power_conns = ean.list_connections_by_kind('power')
if len(power_conns) >= 4:
    fuel = {"inputs": power_conns[:3], "outputs": [power_conns[3]]}
else:
    # Fallback: use whatever power connections exist; if none, pick first material streams as a best-effort fallback.
    material_conns = ean.list_connections_by_kind('material')
    fuel = {"inputs": material_conns[:3], "outputs": material_conns[3:4]}

# Select product and loss streams from available material streams (fall back to specific names if present)
material_conns = ean.list_connections_by_kind('material')
product = {"inputs": [], "outputs": [c for c in material_conns if c.endswith('32')][:1] or material_conns[31:32]}
loss = {"inputs": [], "outputs": [c for c in material_conns if c.endswith('28') or c.endswith('25')][:2]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)

# Export JSON in the same structure as examples/json_example/example.json
output_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "examples", "json_example", "aspen_luftzerlegung.json")
)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
export_data = ean._serialize()
json_payload = {
    "components": export_data.get("components", {}),
    "connections": export_data.get("connections", {}),
    "ambient_conditions": export_data.get("ambient_conditions", {}),
}
with open(output_path, "w", encoding="utf-8") as json_file:
    json.dump(json_payload, json_file, indent=4)

# Append concise exergy summaries to stdout for selected components
try:
    import math

    targets = [
        "D1", "D2", "D3", "D4",
        "LK1", "LK2", "PK1",
        "T1",
        "MIX1",
        "SPLIT1", "SPLIT2",
        "REB", "ZK1", "ZK2",
    ]

    # Build index: name -> (type, exergy_results)
    index = {}
    for comp_group, comps in json_payload.get("components", {}).items():
        for name, data in comps.items():
            index[name] = (data.get("type") or comp_group, data.get("exergy_results") or {})

    def fmt(val):
        if isinstance(val, float) and math.isnan(val):
            return "NaN"
        return f"{val}"

    print("\n==== Exergy Analysis Summary (selected components) ====")
    for t in targets:
        if t in index:
            ctype, results = index[t]
            EF = fmt(results.get("E_F"))
            EP = fmt(results.get("E_P"))
            ED = fmt(results.get("E_D"))
            eps = fmt(results.get("epsilon"))
            print(f"{t} [{ctype}] -> E_F={EF} W, E_P={EP} W, E_D={ED} W, epsilon={eps}")
        else:
            print(f"{t} [unknown] -> No exergy results available")
    print("==== End of Summary ====\n")
except Exception as e:
    # Do not fail the test run if summary formatting has issues; emit a hint.
    print(f"[warn] Failed to append exergy summaries: {e}")
