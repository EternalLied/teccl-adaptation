import json

# Load the schedule JSON
with open('teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json', 'r') as f:
    data = json.load(f)

flows = data['7-Flows']
epoch_links = {}

for flow in flows:
    # Parse flow string: "Chunk X from Y traveled over A->B with volume Z in epoch K"
    parts = flow.split()
    link = parts[5]  # "A->B" (parts[0]=Chunk, [1]=X, [2]=from, [3]=Y, [4]=traveled, [5]=over, [6]=A->B)
    if link == "over":
        link = parts[6]  # If "over" is separate, link is next
    epoch = int(parts[-1])  # K
    chunk = int(parts[1])  # X
    source = int(parts[3])  # Y
    
    key = (epoch, link)
    if key not in epoch_links:
        epoch_links[key] = []
    epoch_links[key].append((chunk, source, flow))

# Find duplicates
duplicates = {k: v for k, v in epoch_links.items() if len(v) > 1}

print(f"Total epoch-link pairs: {len(epoch_links)}")
print(f"Duplicate epoch-links: {len(duplicates)}")
print(f"\nFirst 10 duplicate cases:")

for i, (key, flows_list) in enumerate(sorted(duplicates.items())[:10]):
    epoch, link = key
    print(f"\n{i+1}. Epoch {epoch}, Link {link}: {len(flows_list)} flows")
    for chunk, source, flow in flows_list[:3]:  # Show first 3
        print(f"   - {flow}")
