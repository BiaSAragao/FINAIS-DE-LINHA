import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def upload_imagem(file, nome_arquivo):
    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
        region_name="auto"
    )

    bucket = os.getenv("R2_BUCKET")
    caminho = f"itinerarios/{nome_arquivo}"

    s3.upload_fileobj(
        file,
        bucket,
        caminho,
        ExtraArgs={"ContentType": file.type}
    )

    return f"{os.getenv('R2_PUBLIC_URL')}/{caminho}"
