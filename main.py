import http.server
import socketserver
import json
import urllib.parse
import os
import boto3
from botocore.exceptions import ClientError

# The HTML and JavaScript for the client-side upload form
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Presigned URL S3 Upload</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        input[type="file"] { margin-bottom: 10px; }
        button { padding: 10px 15px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        #status { margin-top: 20px; padding: 10px; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Direct S3 Upload with Presigned URL</h1>
        <p>Select an image file to upload directly to S3 using a presigned URL.</p>
        <input type="file" id="fileInput" accept="image/*">
        <button id="uploadButton">Upload to S3</button>
        <div id="status"></div>
    </div>

    <script>
        document.getElementById('uploadButton').addEventListener('click', async () => {
            const fileInput = document.getElementById('fileInput');
            const statusDiv = document.getElementById('status');
            const file = fileInput.files[0];

            if (!file) {
                statusDiv.className = 'error';
                statusDiv.textContent = 'Please select a file first.';
                return;
            }

            statusDiv.className = '';
            statusDiv.textContent = 'Requesting presigned URL...';

            try {
                // 1. Request a presigned URL from the backend server
                // The backend generates a URL that allows direct upload to S3 for a specific file.
                const presignResponse = await fetch('/presign', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        fileName: file.name,
                        fileType: file.type,
                    }),
                });

                if (!presignResponse.ok) {
                    const errorData = await presignResponse.json();
                    throw new Error(`Failed to get presigned URL: ${errorData.error || presignResponse.statusText}`);
                }

                const { presignedUrl, objectKey } = await presignResponse.json();
                statusDiv.textContent = `Presigned URL received. Uploading "${objectKey}" directly to S3...`;

                // 2. Use the presigned URL to upload the file directly to S3
                // The browser sends the file directly to S3, bypassing the backend server.
                const uploadResponse = await fetch(presignedUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': file.type,
                    },
                    body: file,
                });

                if (uploadResponse.ok) {
                    statusDiv.className = 'success';
                    statusDiv.innerHTML = `Successfully uploaded "${objectKey}" to S3!<br>\n                                           <a href="${presignedUrl.split('?')[0]}" target="_blank">View on S3 (if public)</a>`;
                } else {
                    const errorText = await uploadResponse.text();
                    throw new Error(`Direct S3 upload failed: ${uploadResponse.status} - ${errorText}`);
                }

            } catch (error) {
                console.error('Upload error:', error);
                statusDiv.className = 'error';
                statusDiv.textContent = `Upload failed: ${error.message}`;
            }
        });
    </script>
</body>
</html>
"""

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            # For other GET requests (e.g., favicons), just return 404
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/presign':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data)

            file_name = request_data.get('fileName')
            file_type = request_data.get('fileType')

            if not file_name or not file_type:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing fileName or fileType'}).encode('utf-8'))
                return

            # Generate a unique object key for S3 to avoid overwrites and organize files
            # In a real application, you might add user IDs, timestamps, or UUIDs.
            object_key = f"uploads/{os.path.basename(file_name)}"

            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.environ.get('AWS_REGION')
                )

                # Generate the presigned URL for a PUT operation
                # This URL allows a client to upload a file directly to S3 for a limited time.
                presigned_url = s3_client.generate_presigned_url(
                    ClientMethod='put_object',
                    Params={
                        'Bucket': os.environ.get('S3_BUCKET_NAME'),
                        'Key': object_key,
                        'ContentType': file_type
                    },
                    ExpiresIn=3600 # URL valid for 1 hour
                )

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'presignedUrl': presigned_url, 'objectKey': object_key}).encode('utf-8'))

            except ClientError as e:
                print(f"S3 Client Error: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Could not generate presigned URL: {e}'}).encode('utf-8'))
            except Exception as e:
                print(f"Server Error: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Internal server error: {e}'}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

PORT = 8000

if __name__ == "__main__":
    # Check for required environment variables
    required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']
    for var in required_env_vars:
        if not os.environ.get(var):
            print(f"Error: Environment variable '{var}' is not set.")
            print("Please set all required AWS environment variables before running the script.")
            exit(1)

    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Make sure your S3 bucket has appropriate CORS configuration for direct browser uploads.")
        print("Example CORS configuration for your S3 bucket:")
        print("""
[\n    {\n        "AllowedHeaders": ["*"],\n        "AllowedMethods": ["PUT"],\n        "AllowedOrigins": ["http://localhost:8000"],\n        "ExposeHeaders": []\n    }\n]\n        """)
        httpd.serve_forever()
