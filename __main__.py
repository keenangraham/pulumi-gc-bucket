import pulumi


from pulumi_gcp import storage


bucket = storage.Bucket(
    'test-pulumi-bucket',
    location='US-WEST1',
    force_destroy=True,
    soft_delete_policy={
        'retention_duration_seconds': 0,
    }
)


pulumi.export('bucket_name', bucket.url)
