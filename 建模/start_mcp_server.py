import bpy

def start_mcp():
    try:
        bpy.ops.blendermcp.start_server()
        print("MCP server started on port 9876")
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
    return 0.0

# Delay start to ensure full initialization
bpy.app.timers.register(start_mcp, first_interval=3.0)
print("MCP auto-start script loaded")
