from pulumi import Output
from pulumi import export
from pulumi import Config

from pulumi_docker import Image

from pulumi_gcp import storage

from pulumi_gcp.storage import get_transfer_project_service_account
from pulumi_gcp.storage import BucketIAMMember
from pulumi_gcp.artifactregistry import Repository


storage_transfer_service_account = get_transfer_project_service_account()


bucket = storage.Bucket(
    'test-pulumi-bucket',
    location='us-west1',
    force_destroy=True,
    soft_delete_policy={
        'retention_duration_seconds': 0,
    }
)

gc_project = Config('gcp').require('project')

member = BucketIAMMember(
    'member',
    bucket=bucket.name,
    role='roles/storage.objectViewer',
    member=f'serviceAccount:{storage_transfer_service_account.email}',
)


docker_registry = Repository(
    'test-repo-pulumi',
    location='us-west1',
    repository_id='some-repo',
    format='DOCKER'
)

repo_url = Output.concat(
    docker_registry.location,
    '-docker.pkg.dev/',
    gc_project,
    '/',
    docker_registry.repository_id,
)


image = Image(
    "custom-python",
    build={
        'context': './docker/python/',
        'dockerfile':'./docker/python/Dockerfile',
        'platform': 'linux/amd64',
    },
    image_name=repo_url.apply(lambda url: f'{url}/custom-python312:v0.0.1'),
    registry={
        'server': repo_url.apply(lambda url: f'{url}'),
    },
)


export('bucket_name', bucket.url)
export('storage_transfer_service_account_email', storage_transfer_service_account.email)
export('storage_transfer_service_account_subject_id', storage_transfer_service_account.subject_id)
export('docker_registry_id', docker_registry.id)
export("imageName", image.base_image_name)
