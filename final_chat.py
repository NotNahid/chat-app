import http.server
import socketserver
import cgi
import os
import urllib.parse
import threading # <--- MULTI-TASKING ENABLED

PORT = 8080
UPLOAD_DIR = 'uploads'
messages = []

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 1. THREADING SERVER (Fixes the "Traffic Jam" issue)
class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ChatHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve Uploads
        if self.path.startswith('/uploads/'):
            super().do_GET()
            return

        # Serve Main Page
        if self.path == '/' or self.path.startswith('/?'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Heavy Duty Chat</title>
                <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
                <style>
                    body { background: #000; color: white; font-family: -apple-system, sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
                    header { background: #1c1c1e; padding: 15px; text-align: center; border-bottom: 1px solid #333; font-weight: bold; color: #f5f5f5; position: relative; }
                    
                    /* PROGRESS BAR */
                    #progress-container { position: absolute; bottom: 0; left: 0; width: 100%; height: 4px; background: transparent; }
                    #progress-bar { width: 0%; height: 100%; background: #00e676; transition: width 0.2s; }

                    #chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
                    
                    /* BUBBLES */
                    .msg { max-width: 80%; padding: 10px 15px; border-radius: 20px; font-size: 16px; word-wrap: break-word; }
                    .msg.me { align-self: flex-end; background: #0b84ff; color: white; border-bottom-right-radius: 5px; }
                    .msg.other { align-self: flex-start; background: #26262a; color: white; border-bottom-left-radius: 5px; }
                    .meta { font-size: 11px; margin-bottom: 4px; opacity: 0.6; display: block; }
                    
                    /* MEDIA */
                    img, video { max-width: 100%; border-radius: 10px; margin-top: 5px; display: block; }
                    audio { width: 100%; margin-top: 5px; }
                    
                    /* DOWNLOAD BUTTON */
                    .dl-btn { 
                        display: inline-block; margin-top: 8px; padding: 6px 12px; 
                        background: rgba(255,255,255,0.2); color: white; text-decoration: none; 
                        border-radius: 15px; font-size: 12px; font-weight: bold; 
                    }
                    .dl-btn:hover { background: rgba(255,255,255,0.3); }

                    /* INPUT AREA */
                    #input-area { background: #1c1c1e; padding: 10px; display: flex; align-items: center; gap: 10px; border-top: 1px solid #333; }
                    .file-upload { cursor: pointer; color: #0b84ff; font-size: 24px; padding: 5px; transform: rotate(45deg); }
                    input[type="file"] { display: none; }
                    #message { flex: 1; background: #2c2c2e; border: 1px solid #3a3a3c; color: white; padding: 12px; border-radius: 20px; outline: none; }
                    #username { width: 60px; background: #2c2c2e; border: none; color: #888; padding: 5px; text-align: center; border-radius: 5px; }
                    button { background: #0b84ff; color: white; border: none; padding: 10px 15px; border-radius: 50%; font-weight: bold; cursor: pointer; }
                </style>
                <script>
                    let lastMsgCount = 0;

                    // UPLOAD WITH PROGRESS BAR
                    function sendMessage(event) {
                        event.preventDefault();
                        const form = document.getElementById('chat-form');
                        const formData = new FormData(form);
                        const fileInput = document.getElementById('file');
                        const msgInput = document.getElementById('message');

                        if (!msgInput.value && fileInput.files.length === 0) return;

                        // Use XHR for Progress Tracking
                        const xhr = new XMLHttpRequest();
                        xhr.open('POST', '/send', true);
                        
                        // Track Upload Progress
                        xhr.upload.onprogress = function(e) {
                            if (e.lengthComputable) {
                                const percent = (e.loaded / e.total) * 100;
                                document.getElementById('progress-bar').style.width = percent + '%';
                            }
                        };

                        xhr.onload = function() {
                            if (xhr.status === 200) {
                                // Reset UI
                                document.getElementById('progress-bar').style.width = '0%';
                                msgInput.value = '';
                                fileInput.value = '';
                                fetchMessages();
                            }
                        };

                        xhr.send(formData);
                    }

                    function fetchMessages() {
                        const currentUser = document.getElementById('username').value;
                        fetch('/get_messages?user=' + encodeURIComponent(currentUser))
                            .then(response => response.text())
                            .then(html => {
                                const chatBox = document.getElementById('chat-box');
                                if (html.length !== lastMsgCount) {
                                    chatBox.innerHTML = html;
                                    chatBox.scrollTop = chatBox.scrollHeight;
                                    lastMsgCount = html.length;
                                }
                            });
                    }
                    setInterval(fetchMessages, 1000);
                </script>
            </head>
            <body>
                <header>
                    Heavy Duty Chat
                    <div id="progress-container"><div id="progress-bar"></div></div>
                </header>
                
                <div id="chat-box"></div>

                <form id="chat-form" onsubmit="sendMessage(event)" enctype="multipart/form-data">
                    <div id="input-area">
                        <input type="text" id="username" name="username" value="Me" required>
                        <label for="file" class="file-upload">📎</label>
                        <input type="file" id="file" name="file">
                        <input type="text" id="message" name="message" placeholder="Type a message..." autocomplete="off">
                        <button type="submit">↑</button>
                    </div>
                </form>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        # API: Get Messages
        elif self.path.startswith('/get_messages'):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            current_user = params.get('user', [''])[0]

            self.send_response(200)
            self.end_headers()
            
            chat_html = ""
            for msg in messages:
                is_me = (msg['user'] == current_user)
                css_class = "me" if is_me else "other"
                
                content = ""
                # Handle File Types
                if msg['file']:
                    ft = msg['file_type']
                    fpath = f'/uploads/{msg["file"]}'
                    # The "Download" Button for everyone
                    dl_button = f'<a href="{fpath}" download class="dl-btn">⬇️ Save {msg["file"]}</a>'
                    
                    if ft == 'image':
                        content += f'<img src="{fpath}">{dl_button}'
                    elif ft == 'video':
                        content += f'<video controls src="{fpath}"></video>{dl_button}'
                    elif ft == 'audio':
                        content += f'<audio controls src="{fpath}"></audio>{dl_button}'
                    else:
                        content += f'<a href="{fpath}" download class="file-link">📄 {msg["file"]}</a>'
                
                if msg['text']:
                    content += f"<div>{msg['text']}</div>"

                chat_html += f"""
                <div class="msg {css_class}">
                    <span class="meta">{msg['user']} • {msg['time']}</span>
                    {content}
                </div>
                """
            self.wfile.write(chat_html.encode('utf-8'))

        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/send':
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            user = form.getvalue("username")
            text = form.getvalue("message")
            filename = None
            file_type = None
            
            if "file" in form and form["file"].filename:
                file_item = form["file"]
                fn = os.path.basename(file_item.filename)
                save_path = os.path.join(UPLOAD_DIR, fn)
                
                # Write file in chunks (Good for Large Files)
                with open(save_path, 'wb') as f:
                    while True:
                        chunk = file_item.file.read(100000) # Read 100KB at a time
                        if not chunk: break
                        f.write(chunk)
                
                filename = fn
                fn_lower = fn.lower()
                if fn_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')): file_type = 'image'
                elif fn_lower.endswith(('.mp4', '.mov', '.webm', '.ogg')): file_type = 'video'
                elif fn_lower.endswith(('.mp3', '.wav', '.m4a')): file_type = 'audio'
                else: file_type = 'file'

            if text or filename:
                timestamp = datetime.now().strftime("%H:%M")
                messages.append({'time': timestamp, 'user': user, 'text': text, 'file': filename, 'file_type': file_type})

            self.send_response(200)
            self.end_headers()

print(f"🚀 Threaded Server LIVE on port {PORT}...")
# USE THE THREADED SERVER HERE
with ThreadingSimpleServer(("", PORT), ChatHandler) as httpd:
    httpd.serve_forever()
