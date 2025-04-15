import json

from pulumi import Output
from pulumi import export
from pulumi import Config

from pulumi_docker import Image

from pulumi_gcp import storage

from pulumi_gcp.storage import get_transfer_project_service_account
from pulumi_gcp.storage import BucketIAMMember

from pulumi_gcp.artifactregistry import Repository
from pulumi_gcp.artifactregistry import RepositoryIamMember

from pulumi_gcp.serviceaccount import Account

from pulumi_gcp.compute import Instance

from pulumi_gcp.secretmanager import SecretVersion


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
    image_name=repo_url.apply(lambda url: f'{url}/custom-python312:v0.0.7'),
    registry={
        'server': repo_url.apply(lambda url: f'{url}'),
    },
)


compute_service_account = Account(
    'compute-sa',
)


compute_object_user = BucketIAMMember(
    'compute-object-user',
    bucket=bucket.name,
    role='roles/storage.objectUser',
    member=Output.concat("serviceAccount:", compute_service_account.email),
)


compute_bucket_reader = BucketIAMMember(
    'compute-bucket-reader',
    bucket=bucket.name,
    role='roles/storage.bucketReader',
    member=Output.concat("serviceAccount:", compute_service_account.email),
)


image_pull_permission = RepositoryIamMember(
    'image-pull-permission',
    repository=docker_registry.id,
    location=docker_registry.location,
    role="roles/artifactregistry.reader",
    member=Output.concat("serviceAccount:", compute_service_account.email),
)


test_secret = SecretVersion.get(
    resource_name='test-secret',
    id='projects/99884963860/secrets/test-secret/versions/1',
)


container_def = Output.all(
    image=image.base_image_name,
    secret_value=test_secret.secret_data
).apply(
    lambda args: json.dumps({
        "spec": {
            "containers": [
                {
                    "name": "test-container-1",
                    "image": args['image'],
                    "env": [
                        {"name": "ATHING", "value": "fromdef"},
                        {"name": "IMAGENAME", "value": args['image']},
                        {"name": "a", "value": json.loads(args['secret_value'])['a']},
                        {"name": "b", "value": json.loads(args['secret_value'])['secret']},
                    ],
                    "stdin": True,
                    "tty": True
                }
            ],
            "restartPolicy": "Always"
        }
    })
)


compute_instance = Instance(
    resource_name='test-vm-with-container',
    boot_disk={
        'initialize_params': {
            'image': 'projects/cos-cloud/global/images/cos-stable-117-18613-164-98',
            'size': 32,
        }
    },
    machine_type='e2-medium',
    zone='us-west1-a',
    network_interfaces=[
        {
            'network': 'default',
            'access_configs': [{}]
        }
    ],
    metadata={
        'gce-container-declaration': container_def
    },
    service_account={
        'email': compute_service_account.email,
        'scopes': ['cloud-platform'],
    },
    allow_stopping_for_update=True,
)

export('bucket_name', bucket.url)
export('storage_transfer_service_account_email', storage_transfer_service_account.email)
export('storage_transfer_service_account_subject_id', storage_transfer_service_account.subject_id)
export('docker_registry_id', docker_registry.id)
export("imageName", image.base_image_name)
export('compute_service_account_email', compute_service_account.email)
