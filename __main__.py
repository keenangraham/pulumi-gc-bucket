import pulumi


from pulumi_gcp import storage
from pulumi_gcp.storage import get_transfer_project_service_account


service_transfer_service_account = get_transfer_project_service_account()


bucket = storage.Bucket(
    'test-pulumi-bucket',
    location='US-WEST1',
    force_destroy=True,
    soft_delete_policy={
        'retention_duration_seconds': 0,
    }
)


pulumi.export('bucket_name', bucket.url)
pulumi.export('storage_transfer_service_account_email', service_transfer_service_account.email)
pulumi.export('storage_transfer_service_account_subject_id', service_transfer_service_account.subject_id)
