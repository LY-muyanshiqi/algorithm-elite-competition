"""Blender MCP client tools"""
import socket, json, os, base64

MCP_HOST = 'localhost'
MCP_PORT = 9876
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def mcp_call(type_, params=None):
    cmd = {'type': type_}
    if params:
        cmd['params'] = params
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((MCP_HOST, MCP_PORT))
    s.settimeout(10)
    s.sendall((json.dumps(cmd) + '\n').encode('utf-8'))
    buffer = b''
    s.settimeout(15)
    try:
        while True:
            data = s.recv(65536)
            if not data: break
            buffer += data
    except socket.timeout: pass
    s.close()
    return json.loads(buffer.decode('utf-8'))

def screenshot(filepath, max_size=1200):
    return mcp_call('get_viewport_screenshot', {
        'filepath': filepath,
        'max_size': max_size,
        'format': 'PNG'
    })

def get_scene_info():
    return mcp_call('get_scene_info')

def execute_code(code):
    return mcp_call('execute_code', {'code': code})

if __name__ == '__main__':
    # 1. Screenshot
    sp = os.path.join(SCRIPT_DIR, 'viewport_screenshot.png')
    r = screenshot(sp)
    print('Screenshot:', r['status'], '-', r.get('result', {}))

    # 2. Test execute_code
    r = execute_code("print('Hello from Blender!')")
    print('\nExecute code test:', r['status'], '-', r.get('result', {}).get('output', r))

    # 3. Scene info
    r = get_scene_info()
    print('\nScene:', r['result']['name'], '- Objects:', r['result']['object_count'])
    for obj in r['result']['objects']:
        print(f'  [{obj["type"]}] {obj["name"]}')
