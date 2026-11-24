# Direct Browser Uploads Presigned S3

This example demonstrates how to securely and efficiently upload files directly from a web browser to AWS S3 using presigned URLs. A lightweight Python backend generates a temporary, single-use URL for a specific S3 object, which the frontend then uses to perform a direct PUT request to S3, bypassing the backend server. This approach enhances security by keeping AWS credentials off the client and improves performance by offloading upload traffic from the application server.

## Language

`python`

## How to Run

1. Install `boto3`: `pip install boto3`
2. Set AWS Environment Variables:
   `export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"`
   `export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"`
   `export AWS_REGION="your-aws-region" # e.g., us-east-1`
   `export S3_BUCKET_NAME="your-unique-s3-bucket-name"`
   Ensure your AWS credentials have `s3:PutObject` permission for the specified bucket.
3. Configure S3 CORS: Add a CORS policy to your S3 bucket allowing `PUT` requests from `http://localhost:8000`. A minimal example is printed when the server starts.
4. Run the script: `python main.py`
5. Open in browser: Navigate to `http://localhost:8000`

## Original Article

This example accompanies the Turkish article: [Oyun Ürünü Görsel Yüklemelerinde Güvenli ve Verimli Bir Yaklaşım: Presigned URL'ler ile Doğrudan Tarayıcı Yüklemeleri](https://fatihsoysal.com/blog/oyun-urunu-gorsel-yuklemelerinde-guvenli-ve-verimli-bir-yaklasim-presigned-urller-ile-dogrudan-tarayici-yuklemeleri/).

## License

MIT — see [LICENSE](LICENSE).
