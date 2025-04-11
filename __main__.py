import pulumi


from pulumi_gcp import storage

from pulumi_gcp.storage import get_transfer_project_service_account
from pulumi_gcp.storage import BucketIAMMember


storage_transfer_service_account = get_transfer_project_service_account()


bucket = storage.Bucket(
    'test-pulumi-bucket',
    location='US-WEST1',
    force_destroy=True,
    soft_delete_policy={
        'retention_duration_seconds': 0,
    }
)


member = BucketIAMMember(
    'member',
    bucket=bucket.name,
    role='roles/storage.objectViewer',
    member=f'serviceAccount:{storage_transfer_service_account.email}',
)



pulumi.export('bucket_name', bucket.url)
pulumi.export('storage_transfer_service_account_email', storage_transfer_service_account.email)
pulumi.export('storage_transfer_service_account_subject_id', storage_transfer_service_account.subject_id)
