#!/usr/bin/env python3
"""
Script pour initialiser MinIO avec les buckets et uploader les CSV
"""

import os
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv

# Charger les variables depuis .env
load_dotenv()


def main():
    # Configuration MinIO depuis .env
    client = Minio(
        os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123"),
        secure=False,
    )

    bucket_name = os.getenv("MINIO_BUCKET", "datasets")

    # Créer le bucket s'il n'existe pas
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✓ Bucket '{bucket_name}' créé avec succès")
        else:
            print(f"✓ Bucket '{bucket_name}' existe déjà")
    except S3Error as e:
        print(f"Erreur lors de la création du bucket: {e}")
        return

    # Upload des CSV du dossier datasets s'ils existent localement.
    csv_files = [
        "datasets/Taux_de_mortalite.csv",
        "datasets/effectifs.csv",
        "datasets/annuaire-des-entreprises-etablissements-10_04_2026.csv",
        "datasets/C03-ISD_Taux_de_mortalite.csv",
        "datasets/depenses.csv",
    ]

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                file_size = os.path.getsize(csv_file)
                object_name = f"raw/{os.path.basename(csv_file)}"
                print(f"Upload de {csv_file} ({file_size / (1024**3):.2f} GB)...")
                client.fput_object(bucket_name, object_name, csv_file)
                print(f"✓ {csv_file} uploadé avec succès")
            except S3Error as e:
                print(f"Erreur lors de l'upload de {csv_file}: {e}")
        else:
            print(f"⚠ Fichier {csv_file} non trouvé")


if __name__ == "__main__":
    main()
